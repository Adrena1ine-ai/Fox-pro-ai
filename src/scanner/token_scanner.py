"""
Token Scanner — Find heavy files that exceed token threshold.
Used by Deep Clean to identify files for external storage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class FileCategory(Enum):
    """Categories of files for different handling."""
    DATA = "data"           # JSON, CSV, YAML data files
    DATABASE = "database"   # SQLite, DB files
    CODE = "code"           # Python, JS, etc.
    LOG = "log"             # Log files
    BINARY = "binary"       # Images, archives, etc.
    CONFIG = "config"       # Configuration files
    UNKNOWN = "unknown"


@dataclass
class HeavyFile:
    """Represents a file that exceeds token threshold."""
    path: Path
    relative_path: str
    size_bytes: int
    estimated_tokens: int
    category: FileCategory
    extension: str
    can_extract_schema: bool = False
    schema: Optional[Dict] = None
    
    @property
    def size_human(self) -> str:
        """Human-readable size."""
        size = self.size_bytes
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    
    @property
    def tokens_human(self) -> str:
        """Human-readable token count."""
        if self.estimated_tokens >= 1_000_000:
            return f"{self.estimated_tokens/1_000_000:.1f}M"
        elif self.estimated_tokens >= 1_000:
            return f"{self.estimated_tokens/1_000:.1f}K"
        return str(self.estimated_tokens)


@dataclass
class ScanResult:
    """Result of scanning a project for heavy files."""
    project_path: Path
    project_name: str
    total_files_scanned: int
    total_tokens: int
    heavy_files: List[HeavyFile] = field(default_factory=list)
    skipped_dirs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def heavy_tokens(self) -> int:
        """Total tokens in heavy files."""
        return sum(f.estimated_tokens for f in self.heavy_files)
    
    @property
    def light_tokens(self) -> int:
        """Tokens in files under threshold."""
        return self.total_tokens - self.heavy_tokens
    
    @property
    def potential_savings(self) -> float:
        """Percentage of tokens that can be moved out."""
        if self.total_tokens == 0:
            return 0
        return (self.heavy_tokens / self.total_tokens) * 100


# Directories to always skip
SKIP_DIRS: Set[str] = {
    "venv", ".venv", "venv_gate", "env", ".env",
    "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git", ".svn", ".hg",
    ".idea", ".vscode", ".cursor",
    "dist", "build", "*.egg-info",
    "_venvs", "_data", "_artifacts", "_logs",  # Our external dirs
}

# Extensions that can have schema extracted
SCHEMA_EXTENSIONS: Set[str] = {".json", ".csv", ".sqlite", ".sqlite3", ".db", ".yaml", ".yml"}

# Extensions to skip entirely (binary)
BINARY_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".rar", ".7z", ".bz2",
    ".exe", ".dll", ".so", ".dylib",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pyc", ".pyo", ".pyd",
}


def categorize_file(file_path: Path) -> FileCategory:
    """Determine file category based on extension and name."""
    ext = file_path.suffix.lower()
    name = file_path.name.lower()
    
    # Check by extension
    if ext in {".json", ".csv", ".yaml", ".yml", ".xml", ".jsonl"}:
        return FileCategory.DATA
    elif ext in {".sqlite", ".sqlite3", ".db"}:
        return FileCategory.DATABASE
    elif ext in {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h"}:
        return FileCategory.CODE
    elif ext == ".log" or name.endswith(".log"):
        return FileCategory.LOG
    elif ext in BINARY_EXTENSIONS:
        return FileCategory.BINARY
    elif ext in {".ini", ".toml", ".cfg", ".conf", ".env"}:
        return FileCategory.CONFIG
    
    # Check by name
    if "log" in name:
        return FileCategory.LOG
    
    return FileCategory.UNKNOWN


def estimate_tokens(file_path: Path) -> int:
    """
    Estimate token count for a file.
    Uses ~4 characters per token approximation.
    For binary files, returns 0.
    """
    try:
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            return 0
        
        size = file_path.stat().st_size
        
        # For text files, estimate based on size
        # Binary files within text (base64, etc.) have higher char/token ratio
        return size // 4
        
    except (OSError, IOError):
        return 0


def should_skip_dir(dir_name: str) -> bool:
    """Check if directory should be skipped."""
    return dir_name in SKIP_DIRS or (dir_name.startswith(".") and dir_name != ".github")


def scan_file(
    file_path: Path,
    project_root: Path,
    threshold: int,
    include_code: bool,
    extract_schemas: bool
) -> Optional[HeavyFile]:
    """
    Scan single file and return HeavyFile if exceeds threshold.
    
    Returns None if:
    - File is under threshold
    - File is binary
    - File is code and include_code=False
    """
    tokens = estimate_tokens(file_path)
    
    # Under threshold - skip
    if tokens < threshold:
        return None
    
    category = categorize_file(file_path)
    
    # Skip code unless requested
    if category == FileCategory.CODE and not include_code:
        return None
    
    # Skip binary
    if category == FileCategory.BINARY:
        return None
    
    # Create HeavyFile
    try:
        relative = file_path.relative_to(project_root)
    except ValueError:
        # File is outside project root
        return None
    
    can_extract = file_path.suffix.lower() in SCHEMA_EXTENSIONS
    
    heavy = HeavyFile(
        path=file_path,
        relative_path=str(relative),
        size_bytes=file_path.stat().st_size,
        estimated_tokens=tokens,
        category=category,
        extension=file_path.suffix.lower(),
        can_extract_schema=can_extract
    )
    
    # Extract schema if possible
    if extract_schemas and can_extract:
        try:
            from .schema_extractor import extract_schema
            heavy.schema = extract_schema(file_path)
        except Exception:
            pass
    
    return heavy


def scan_project(
    project_path: Path,
    threshold: int = 1000,
    include_code: bool = False,
    extract_schemas: bool = True,
    show_progress: bool = False
) -> ScanResult:
    """
    Scan project for files exceeding token threshold.
    
    Args:
        project_path: Path to project root
        threshold: Token threshold (default 1000)
        include_code: If True, include .py files in heavy list (default False)
        extract_schemas: If True, extract schema for data files (default True)
    
    Returns:
        ScanResult with list of heavy files and statistics
    """
    project_path = project_path.resolve()
    result = ScanResult(
        project_path=project_path,
        project_name=project_path.name,
        total_files_scanned=0,
        total_tokens=0
    )
    
    # Walk through project
    try:
        for root, dirs, files in os.walk(project_path):
            # Filter out skip directories
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]
            
            # Track skipped directories
            all_items = set(os.listdir(root))
            for item in all_items:
                item_path = Path(root) / item
                if item_path.is_dir() and should_skip_dir(item) and item not in dirs:
                    rel_skip = item_path.relative_to(project_path)
                    result.skipped_dirs.append(str(rel_skip))
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                try:
                    # Skip binary files entirely
                    if file_path.suffix.lower() in BINARY_EXTENSIONS:
                        continue
                    
                    result.total_files_scanned += 1
                    
                    # Show progress every 20 files
                    if show_progress and result.total_files_scanned % 20 == 0:
                        print(f"\r   Scanning... {result.total_files_scanned} files", end="", flush=True)
                    
                    tokens = estimate_tokens(file_path)
                    result.total_tokens += tokens
                    
                    # Check if heavy
                    heavy_file = scan_file(
                        file_path, project_path, threshold, 
                        include_code, extract_schemas
                    )
                    
                    if heavy_file:
                        result.heavy_files.append(heavy_file)
                        
                except Exception as e:
                    result.errors.append(f"{file_path}: {str(e)}")
    except Exception as e:
        result.errors.append(f"Scan error: {str(e)}")
        if show_progress:
            print()  # New line after error
    
    # Sort heavy files by tokens (descending)
    result.heavy_files.sort(key=lambda x: x.estimated_tokens, reverse=True)
    
    if show_progress:
        print(f"\r   Scanned {result.total_files_scanned} files (done)" + " " * 30)
    
    return result


def format_scan_report(result: ScanResult) -> str:
    """
    Format scan result as readable report.
    
    Example output:
    ╔══════════════════════════════════════════════════════════════╗
    ║  🔍 TOKEN SCANNER — Heavy Files Report                       ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Project: my_bot                                             ║
    ║  Total Tokens: 5.2M                                          ║
    ║  Heavy Files: 12 (4.8M tokens, 92%)                          ║
    ║  Light Files: 45 (0.4M tokens, 8%)                           ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  HEAVY FILES:                                                ║
    ║  ├─ data/products.json      DATA      2.1M tokens            ║
    ║  ├─ data/users.csv          DATA      1.5M tokens            ║
    ║  ├─ logs/app.log            LOG       0.8M tokens            ║
    ║  └─ cache/responses.json    DATA      0.4M tokens            ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  💡 Run `doctor --deep-clean` to move these files            ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    lines = []
    
    # Header
    lines.append("╔══════════════════════════════════════════════════════════════════╗")
    lines.append("║  🔍 TOKEN SCANNER — Heavy Files Report                           ║")
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    
    # Summary
    total_str = f"{result.total_tokens/1_000_000:.1f}M" if result.total_tokens >= 1_000_000 else f"{result.total_tokens/1_000:.0f}K"
    heavy_str = f"{result.heavy_tokens/1_000_000:.1f}M" if result.heavy_tokens >= 1_000_000 else f"{result.heavy_tokens/1_000:.0f}K"
    light_str = f"{result.light_tokens/1_000_000:.1f}M" if result.light_tokens >= 1_000_000 else f"{result.light_tokens/1_000:.0f}K"
    
    lines.append(f"║  Project: {result.project_name:<55}║")
    lines.append(f"║  Files Scanned: {result.total_files_scanned:<49}║")
    lines.append(f"║  Total Tokens: {total_str:<50}║")
    lines.append(f"║  Heavy Files: {len(result.heavy_files)} ({heavy_str} tokens, {result.potential_savings:.0f}%){' '*(30-len(heavy_str))}║")
    lines.append(f"║  Light Files: {result.total_files_scanned - len(result.heavy_files)} ({light_str} tokens, {100-result.potential_savings:.0f}%){' '*(30-len(light_str))}║")
    
    if result.heavy_files:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append("║  HEAVY FILES (sorted by size):                                   ║")
        
        top_files = result.heavy_files[:15]
        for i, hf in enumerate(top_files):
            prefix = "└─" if i == len(top_files) - 1 else "├─"
            cat = hf.category.value.upper()[:4]
            path_str = hf.relative_path[:35]
            if len(hf.relative_path) > 35:
                path_str = path_str[:32] + "..."
            tokens_str = hf.tokens_human
            line = f"║  {prefix} {path_str:<35} {cat:<6} {tokens_str:>8} tokens"
            # Pad to 67 chars total
            padding = 67 - len(line) + 1
            lines.append(line + " " * padding + "║")
        
        if len(result.heavy_files) > 15:
            remaining = len(result.heavy_files) - 15
            lines.append(f"║  ... and {remaining} more files{' '*45}║")
    
    if result.errors:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  ⚠️  Errors: {len(result.errors)} files could not be scanned{' '*30}║")
    
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    lines.append("║  💡 Run `doctor --deep-clean` to move heavy files externally     ║")
    lines.append("╚══════════════════════════════════════════════════════════════════╝")
    
    return "\n".join(lines)


def get_moveable_files(result: ScanResult) -> List[HeavyFile]:
    """
    Get files that can be safely moved to external storage.
    
    Excludes:
    - Core code files (main.py, __init__.py, etc.)
    - Config files that must stay in project
    - Files already in external dirs
    """
    moveable = []
    
    # Files that should NOT be moved
    protected_names = {
        "main.py", "__init__.py", "__main__.py",
        "config.py", "settings.py", "constants.py",
        "requirements.txt", "pyproject.toml", "setup.py",
        ".env", ".env.example",
        "README.md", "CLAUDE.md", ".cursorrules",
        "config_paths.py",  # Bridge file must stay
    }
    
    for hf in result.heavy_files:
        # Skip protected files
        if hf.path.name.lower() in protected_names:
            continue
        
        # Skip files already in external dirs
        if any(external in hf.relative_path for external in ["_venvs", "_data", "_artifacts", "_logs"]):
            continue
        
        # Skip code files (unless they're pure data)
        if hf.category == FileCategory.CODE:
            # Check if it's a data-heavy Python file (large dicts)
            if not hf.can_extract_schema:
                continue
        
        moveable.append(hf)
    
    return moveable

