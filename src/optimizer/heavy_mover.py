"""
Heavy Mover — Move heavy files to external storage and generate bridges.
The core of the "Deep Clean & Bridge" system.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..scanner.token_scanner import FileCategory, HeavyFile, ScanResult

try:
    from ..core.constants import VERSION
except ImportError:
    VERSION = "3.4.0"


@dataclass
class MovedFile:
    """Record of a moved file."""
    original_path: Path          # Original location in project
    original_relative: str       # Relative to project root
    external_path: Path          # New location in external storage
    external_relative: str       # Relative to external root
    size_bytes: int
    estimated_tokens: int
    category: FileCategory
    schema: Optional[Dict] = None
    moved_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MoveResult:
    """Result of moving heavy files."""
    project_path: Path
    project_name: str
    external_dir: Path
    moved_files: List[MovedFile] = field(default_factory=list)
    failed_files: List[Tuple[str, str]] = field(default_factory=list)  # (path, error)
    symlinks_created: List[Tuple[str, str]] = field(default_factory=list)  # (link, target)
    config_paths_file: Optional[Path] = None
    manifest_file: Optional[Path] = None
    
    @property
    def total_moved_tokens(self) -> int:
        return sum(mf.estimated_tokens for mf in self.moved_files)
    
    @property
    def success_count(self) -> int:
        return len(self.moved_files)
    
    @property
    def failed_count(self) -> int:
        return len(self.failed_files)


def get_external_dir(project_path: Path, create: bool = True) -> Path:
    """
    Get external storage directory for project.
    
    Supports both old and new path formats for backward compatibility:
    - NEW: ../PROJECT_NAME_data/
    - OLD: ../_data/PROJECT_NAME/LARGE_TOKENS/
    
    Logic:
    1. If OLD path exists and has files → use OLD (backward compat)
    2. Otherwise → use NEW path
    
    Args:
        project_path: Path to project root
        create: If True, create directory if not exists
    
    Returns:
        Path to external storage directory
    """
    project_path = project_path.resolve()
    project_name = project_path.name
    
    # New simplified path
    new_path = project_path.parent / f"{project_name}_data"
    
    # Old path (for backward compatibility)
    old_path = project_path.parent / "_data" / project_name / "LARGE_TOKENS"
    
    # Check if old path exists and has content
    if old_path.exists():
        # Check if it has files (not just empty dirs)
        try:
            has_files = any(old_path.rglob("*"))
            if has_files:
                return old_path  # Use old path for existing projects
        except (OSError, PermissionError):
            pass  # If we can't check, use new path
    
    # Use new path for new projects
    if create:
        new_path.mkdir(parents=True, exist_ok=True)
    
    return new_path


def get_manifest_path(project_path: Path) -> Optional[Path]:
    """
    Find manifest.json in either old or new external storage.
    
    Returns:
        Path to manifest.json or None if not found
    """
    project_path = project_path.resolve()
    project_name = project_path.name
    
    # Check new path first
    new_manifest = project_path.parent / f"{project_name}_data" / "manifest.json"
    if new_manifest.exists():
        return new_manifest
    
    # Check old path
    old_manifest = project_path.parent / "_data" / project_name / "LARGE_TOKENS" / "manifest.json"
    if old_manifest.exists():
        return old_manifest
    
    return None


def move_heavy_files(
    project_path: Path,
    heavy_files: List[HeavyFile],
    dry_run: bool = False
) -> MoveResult:
    """
    Move heavy files to external storage.
    
    Args:
        project_path: Path to project root
        heavy_files: List of HeavyFile from token_scanner
        dry_run: If True, only simulate (don't actually move)
    
    Returns:
        MoveResult with list of moved files and any errors
    
    Process:
        1. Create external directory structure
        2. Move each file, preserving relative structure
        3. Generate manifest.json
        4. Generate config_paths.py
    """
    project_path = project_path.resolve()
    external_dir = get_external_dir(project_path, create=not dry_run)
    
    result = MoveResult(
        project_path=project_path,
        project_name=project_path.name,
        external_dir=external_dir
    )
    
    total = len(heavy_files)
    for idx, hf in enumerate(heavy_files, 1):
        try:
            # Show progress
            if not dry_run and idx % 5 == 0:
                print(f"   Moving files... {idx}/{total}", end="\r", flush=True)
            
            # Calculate destination path (preserve structure)
            dest_path = external_dir / hf.relative_path
            
            if not dry_run:
                # Create parent directories
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(str(hf.path), str(dest_path))
            
            # Record move
            moved = MovedFile(
                original_path=hf.path,
                original_relative=hf.relative_path,
                external_path=dest_path,
                external_relative=str(dest_path.relative_to(external_dir)),
                size_bytes=hf.size_bytes,
                estimated_tokens=hf.estimated_tokens,
                category=hf.category,
                schema=hf.schema
            )
            result.moved_files.append(moved)
            
        except Exception as e:
            result.failed_files.append((hf.relative_path, str(e)))
    
    if not dry_run and total > 0:
        print(f"   Moved {total}/{total} files" + " " * 30)
    
    if not dry_run and result.moved_files:
        # Generate config_paths.py
        result.config_paths_file = generate_config_paths(
            project_path, result.moved_files, external_dir
        )
        
        # Generate manifest.json
        # Note: original_tokens should be passed from caller (from scan_result.total_tokens BEFORE moving)
        result.manifest_file = generate_manifest(
            project_path, result.moved_files, external_dir, original_tokens=None
        )
        
        # Update .cursorignore to exclude moved files
        update_cursorignore(project_path, result.moved_files, external_dir)
        
        # Create symlinks for dynamic path support
        result.symlinks_created = create_symlinks(
            project_path, result.moved_files, external_dir
        )
    
    return result


def create_symlinks(
    project_path: Path,
    moved_files: List[MovedFile],
    external_dir: Path
) -> List[Tuple[str, str]]:
    """
    Create symlinks from original directories to external storage.
    
    This allows dynamic paths like f"data/{user_id}.json" to work
    without code changes.
    
    Args:
        project_path: Path to project root
        moved_files: List of moved files
        external_dir: Path to external storage
        
    Returns:
        List of (link_path, target_path) tuples
        
    Note:
        On Windows, symlinks require either:
        - Running as Administrator, OR
        - Developer Mode enabled in Settings
        If neither, symlinks will fail silently and config_paths.py
        will be the only bridge.
    """
    import platform
    
    symlinks = []
    
    # Find unique top-level directories that were moved
    moved_dirs = set()
    for mf in moved_files:
        # Get first component of path (e.g., "data" from "data/users.json")
        parts = Path(mf.original_relative).parts
        if len(parts) > 1:  # Has directory component
            moved_dirs.add(parts[0])
    
    for dir_name in moved_dirs:
        link_path = project_path / dir_name
        target_path = external_dir / dir_name
        
        # Skip if target doesn't exist
        if not target_path.exists():
            continue
        
        # Skip if original directory still exists with files
        if link_path.exists() and not link_path.is_symlink():
            # Check if directory is empty or has only subdirs that were moved
            remaining_files = list(link_path.rglob("*"))
            remaining_files = [f for f in remaining_files if f.is_file()]
            if remaining_files:
                continue  # Directory has remaining files, don't replace
            
            # Remove empty directory
            try:
                shutil.rmtree(link_path)
            except Exception:
                continue
        
        # Skip if symlink already exists
        if link_path.is_symlink():
            continue
        
        # Create symlink
        try:
            # Use relative path for portability
            rel_target = os.path.relpath(target_path, link_path.parent)
            link_path.symlink_to(rel_target)
            symlinks.append((str(link_path.relative_to(project_path)), rel_target))
        except OSError as e:
            # Symlink creation failed
            # Common on Windows without admin/Developer Mode
            if platform.system() == "Windows":
                # Don't spam warnings, just note it once
                if not symlinks and dir_name == list(moved_dirs)[0]:
                    print(f"  ⚠ Symlinks require Admin or Developer Mode on Windows")
                    print(f"    Dynamic paths will need manual fix or use config_paths.py")
            # This is not critical, config_paths.py will still work
            pass
    
    return symlinks


def generate_config_paths(
    project_path: Path,
    moved_files: List[MovedFile],
    external_dir: Path
) -> Path:
    """
    Generate config_paths.py with bridges to external files.
    
    Output file structure:
    ```python
    # Auto-generated by Fox Pro AI Deep Clean
    # DO NOT EDIT — regenerate with `fox doctor --deep-clean`
    
    from pathlib import Path
    
    # External storage location
    EXTERNAL_DATA = Path(__file__).parent.parent / "PROJECT_data"
    
    # File mappings (original name → external path)
    FILES_MAP = {
        "data/products.json": EXTERNAL_DATA / "data/products.json",
        "logs/app.log": EXTERNAL_DATA / "logs/app.log",
    }
    
    # Helper function
    def get_path(original: str) -> Path:
        '''Get external path for original file location.'''
        if original in FILES_MAP:
            return FILES_MAP[original]
        raise FileNotFoundError(f"No external mapping for: {original}")
    
    # Schemas (structure without data)
    SCHEMAS = {
        "data/products.json": {
            "type": "json",
            "schema": {"type": "object", "keys": {...}}
        },
    }
    ```
    """
    project_name = project_path.name
    
    # Build file mappings
    mappings = []
    schemas = []
    
    for mf in moved_files:
        # Use forward slashes for consistency
        orig_key = mf.original_relative.replace("\\", "/")
        # Escape backslashes in path strings
        escaped_path = orig_key.replace("\\", "\\\\")
        mappings.append(f'    "{orig_key}": EXTERNAL_DATA / "{escaped_path}",')
        
        if mf.schema:
            # Convert JSON to Python-compatible format
            schema_str = json.dumps(mf.schema, indent=8, ensure_ascii=False)
            # Replace JSON booleans with Python booleans
            schema_str = schema_str.replace("true", "True").replace("false", "False").replace("null", "None")
            schemas.append(f'    "{orig_key}": {schema_str},')
    
    # Generate Python code
    code = f'''"""
Auto-generated by Fox Pro AI Deep Clean
DO NOT EDIT — regenerate with `fox doctor --deep-clean`

Generated: {datetime.now().isoformat()}
Project: {project_name}
Files moved: {len(moved_files)}
"""
from pathlib import Path

# External storage location
# Relative to project root: ../{project_name}_data/
EXTERNAL_DATA = Path(__file__).parent.parent / "{project_name}_data"

# File mappings (original relative path → external Path)
FILES_MAP = {{
{chr(10).join(mappings)}
}}


def get_path(original: str) -> Path:
    """
    Get external path for original file location.
    
    Usage:
        from config_paths import get_path
        data = json.load(open(get_path("data/products.json")))
    
    Args:
        original: Original relative path (e.g., "data/products.json")
    
    Returns:
        Path to file in external storage
    
    Raises:
        FileNotFoundError: If no mapping exists
    """
    # Normalize path separators
    normalized = original.replace("\\\\", "/")
    
    if normalized in FILES_MAP:
        return FILES_MAP[normalized]
    
    raise FileNotFoundError(
        f"No external mapping for: {{original}}\\n"
        f"Available files: {{list(FILES_MAP.keys())}}"
    )


def exists(original: str) -> bool:
    """Check if file exists in external storage."""
    try:
        return get_path(original).exists()
    except FileNotFoundError:
        return False


def list_files() -> list:
    """List all files in external storage."""
    return list(FILES_MAP.keys())


# Schemas (structure without data, for AI context)
SCHEMAS = {{
{chr(10).join(schemas) if schemas else "    # No schemas extracted"}
}}


def get_schema(original: str) -> dict:
    """Get schema for a file (structure without data)."""
    normalized = original.replace("\\\\", "/")
    return SCHEMAS.get(normalized, {{}})
'''
    
    # Write file
    config_path = project_path / "config_paths.py"
    config_path.write_text(code, encoding="utf-8")
    
    return config_path


def generate_manifest(
    project_path: Path,
    moved_files: List[MovedFile],
    external_dir: Path,
    original_tokens: Optional[int] = None
) -> Path:
    """
    Generate manifest.json in external directory.
    
    Contains full record of what was moved for recovery.
    
    Structure:
    {
        "project": "my_bot",
        "created": "2024-12-24T12:00:00",
        "toolkit_version": "3.4",
        "original_tokens": 5000000,  # Total tokens before optimization
        "files": [
            {
                "original": "data/products.json",
                "external": "data/products.json",
                "tokens": 50000,
                "category": "data",
                "schema": {...}
            }
        ]
    }
    """
    manifest = {
        "project": project_path.name,
        "project_path": str(project_path),
        "external_dir": str(external_dir),
        "created": datetime.now().isoformat(),
        "toolkit_version": VERSION,
        "total_files": len(moved_files),
        "total_tokens": sum(mf.estimated_tokens for mf in moved_files),
        "files": [
            {
                "original": mf.original_relative,
                "external": mf.external_relative,
                "size_bytes": mf.size_bytes,
                "tokens": mf.estimated_tokens,
                "category": mf.category.value,
                "schema": mf.schema,
                "moved_at": mf.moved_at
            }
            for mf in moved_files
        ]
    }
    
    # Add original_tokens if provided (for tracking optimization effectiveness)
    if original_tokens is not None:
        manifest["original_tokens"] = original_tokens
    
    manifest_path = external_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    return manifest_path


def restore_files(
    project_path: Path,
    manifest_path: Optional[Path] = None
) -> int:
    """
    Restore moved files back to original locations.
    
    Args:
        project_path: Path to project root
        manifest_path: Path to manifest.json (auto-detect if None)
    
    Returns:
        Number of files restored
    """
    project_path = project_path.resolve()
    
    # Find manifest with compatibility check
    if manifest_path is None:
        manifest_path = get_manifest_path(project_path)
    
    if manifest_path is None or not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest not found. Checked:\n"
            f"  - ../{project_path.name}_data/manifest.json\n"
            f"  - ../_data/{project_path.name}/LARGE_TOKENS/manifest.json"
        )
    
    # Load manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    external_dir = Path(manifest["external_dir"])
    
    restored = 0
    for file_info in manifest["files"]:
        external_path = external_dir / file_info["external"]
        original_path = project_path / file_info["original"]
        
        if external_path.exists():
            # Create parent directories
            original_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move back
            shutil.move(str(external_path), str(original_path))
            restored += 1
    
    # Remove config_paths.py
    config_paths = project_path / "config_paths.py"
    if config_paths.exists():
        config_paths.unlink()
    
    # Remove Deep Clean section from .cursorignore
    cursorignore_path = project_path / ".cursorignore"
    if cursorignore_path.exists():
        content = cursorignore_path.read_text(encoding="utf-8")
        if "# Deep Clean - moved files" in content:
            lines = content.split('\n')
            new_lines = []
            skip_section = False
            for line in lines:
                if "# Deep Clean - moved files" in line:
                    skip_section = True
                elif skip_section and line.strip() and not line.strip().startswith("#"):
                    continue
                elif skip_section and (not line.strip() or (line.strip().startswith("#") and "Deep Clean" not in line and "External storage" not in line)):
                    skip_section = False
                    if line.strip() and not line.strip().startswith("# Deep Clean") and "External storage" not in line:
                        new_lines.append(line)
                else:
                    if not skip_section:
                        new_lines.append(line)
            cursorignore_path.write_text('\n'.join(new_lines).rstrip() + '\n', encoding="utf-8")
    
    return restored


def update_cursorignore(
    project_path: Path,
    moved_files: List[MovedFile],
    external_dir: Path
) -> None:
    """
    Update .cursorignore to exclude moved files from Cursor indexing.
    
    This is critical: even though files are moved, Cursor will still index
    them if they're not in .cursorignore, wasting tokens.
    
    Args:
        project_path: Project root
        moved_files: List of moved files
        external_dir: External storage directory
    """
    cursorignore_path = project_path / ".cursorignore"
    
    # Read existing content
    existing_content = ""
    if cursorignore_path.exists():
        existing_content = cursorignore_path.read_text(encoding="utf-8")
    
    # Check if Deep Clean section already exists
    if "# Deep Clean - moved files" in existing_content:
        # Remove old Deep Clean section
        lines = existing_content.split('\n')
        new_lines = []
        skip_section = False
        for line in lines:
            if "# Deep Clean - moved files" in line:
                skip_section = True
            elif skip_section and line.strip() and not line.strip().startswith("#"):
                # Continue skipping until next section or empty line
                continue
            elif skip_section and (not line.strip() or (line.strip().startswith("#") and "Deep Clean" not in line)):
                # End of Deep Clean section
                skip_section = False
                if line.strip() and not line.strip().startswith("# Deep Clean"):
                    new_lines.append(line)
            else:
                if not skip_section:
                    new_lines.append(line)
        existing_content = '\n'.join(new_lines).rstrip()
    
    # Build new section
    new_section = "\n\n# Deep Clean - moved files\n"
    new_section += "# Files moved to external storage (excluded from Cursor indexing)\n"
    new_section += "# Generated by: toolkit doctor --deep-clean\n"
    
    # Add external storage directory pattern
    external_relative = None
    try:
        if external_dir.is_relative_to(project_path.parent):
            external_relative = external_dir.relative_to(project_path.parent)
        else:
            # Try to construct relative path
            external_relative = Path(f"../{project_path.name}_data")
    except Exception:
        external_relative = Path(f"../{project_path.name}_data")
    
    new_section += f"# External storage: {external_relative}\n"
    new_section += "\n"
    
    # Add individual file paths (for files in root)
    root_files = [mf for mf in moved_files if "/" not in mf.original_relative.replace("\\", "/") and "\\" not in mf.original_relative]
    if root_files:
        for mf in root_files:
            path = mf.original_relative.replace("\\", "/")
            new_section += f"{path}\n"
    
    # Add directory patterns for moved files
    dirs_with_moved = set()
    for mf in moved_files:
        parts = mf.original_relative.replace("\\", "/").split("/")
        if len(parts) > 1:
            dir_path = "/".join(parts[:-1])
            dirs_with_moved.add(dir_path)
    
    # Add directory patterns (if directories are mostly empty after move)
    for dir_path in sorted(dirs_with_moved):
        dir_full_path = project_path / dir_path
        if dir_full_path.exists():
            files_in_dir = [f for f in dir_full_path.rglob("*") if f.is_file()]
            # If directory is empty or has very few files, add pattern
            if len(files_in_dir) <= 2:
                new_section += f"{dir_path}/*\n"
    
    # Add external storage directory
    new_section += f"\n# External storage directory\n"
    new_section += f"{external_relative}/\n"
    
    # Combine
    final_content = existing_content.rstrip() + new_section
    
    # Write back
    cursorignore_path.write_text(final_content, encoding="utf-8")


def format_move_report(result: MoveResult) -> str:
    """
    Format move result as readable report.
    
    Example:
    ╔══════════════════════════════════════════════════════════════════╗
    ║  📦 DEEP CLEAN — Files Moved to External Storage                 ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║  Project: my_bot                                                 ║
    ║  External: ../my_bot_data/                                       ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║  ✅ MOVED (12 files, 4.8M tokens):                               ║
    ║  ├─ data/products.json        →  my_bot_data/data/products.json  ║
    ║  ├─ data/users.csv            →  my_bot_data/data/users.csv      ║
    ║  └─ logs/app.log              →  my_bot_data/logs/app.log        ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║  📄 Generated:                                                   ║
    ║  ├─ config_paths.py (bridge to external files)                   ║
    ║  └─ manifest.json (recovery info)                                ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║  💡 Update imports: from config_paths import FILES_MAP, get_path ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    lines = []
    
    lines.append("╔══════════════════════════════════════════════════════════════════╗")
    lines.append("║  📦 DEEP CLEAN — Files Moved to External Storage                 ║")
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    
    lines.append(f"║  Project: {result.project_name:<55}║")
    
    # Show external path relative to project
    ext_rel = f"../{result.project_name}_data/"
    lines.append(f"║  External: {ext_rel:<54}║")
    
    if result.moved_files:
        total_tokens = result.total_moved_tokens
        tokens_str = f"{total_tokens/1_000_000:.1f}M" if total_tokens >= 1_000_000 else f"{total_tokens/1_000:.0f}K"
        
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  ✅ MOVED ({len(result.moved_files)} files, {tokens_str} tokens):{' '*(35-len(tokens_str))}║")
        
        for i, mf in enumerate(result.moved_files[:10]):
            prefix = "└─" if i == min(len(result.moved_files), 10) - 1 else "├─"
            orig = mf.original_relative[:25]
            if len(mf.original_relative) > 25:
                orig = orig[:22] + "..."
            dest = f"{result.project_name}_data/{mf.external_relative}"[:30]
            if len(f"{result.project_name}_data/{mf.external_relative}") > 30:
                dest = dest[:27] + "..."
            line = f"║  {prefix} {orig:<25} → {dest:<30}"
            padding = 67 - len(line) + 1
            lines.append(line + " " * padding + "║")
        
        if len(result.moved_files) > 10:
            lines.append(f"║  ... and {len(result.moved_files) - 10} more files{' '*45}║")
    
    if result.failed_files:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  ❌ FAILED ({len(result.failed_files)} files):{' '*44}║")
        for path, error in result.failed_files[:5]:
            path_short = path[:30]
            error_short = error[:25]
            lines.append(f"║  ├─ {path_short:<30}: {error_short:<25}{' '*5}║")
    
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    lines.append("║  📄 Generated:                                                   ║")
    if result.config_paths_file:
        lines.append("║  ├─ config_paths.py (bridge to external files)                   ║")
    if result.manifest_file:
        lines.append("║  ├─ manifest.json (recovery info)                                ║")
    lines.append("║  └─ .cursorignore (updated to exclude moved files)                ║")
    
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    lines.append("║  💡 Update imports: from config_paths import get_path            ║")
    lines.append("║  💡 Restore files:  toolkit doctor --restore                     ║")
    lines.append("╚══════════════════════════════════════════════════════════════════╝")
    
    return "\n".join(lines)


def get_garbage_dir(project_path: Path) -> Path:
    """
    Get garbage directory for project.
    
    Structure:
        ../PROJECT_NAME_garbage_for_removal/
    
    Creates directory if not exists.
    """
    project_path = project_path.resolve()
    project_name = project_path.name
    garbage_dir = project_path.parent / f"{project_name}_garbage_for_removal"
    garbage_dir.mkdir(parents=True, exist_ok=True)
    return garbage_dir


def find_garbage_files(project_path: Path) -> List[Path]:
    """
    Find garbage files that can be safely moved to garbage directory.
    
    Garbage patterns:
    - Temporary files: *.tmp, *.temp, *.bak, *.old, *.backup
    - Old logs: *.log.old, *.log.* (rotated logs)
    - Cache: *.cache, *.pyc (if not in __pycache__)
    - OS files: .DS_Store, Thumbs.db, desktop.ini
    - Old backups: *_backup.*, *_old.*, *.bak
    - Temporary directories: tmp/, temp/, .tmp/
    """
    project_path = project_path.resolve()
    garbage_files = []
    
    # File patterns
    patterns = [
        "*.tmp",
        "*.temp",
        "*.bak",
        "*.old",
        "*.backup",
        "*.cache",
        "*.log.old",
        "*.log.*",  # Rotated logs
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        "*_backup.*",
        "*_old.*",
        "*~",  # Editor backup files
        "*.swp",  # Vim swap files
        "*.swo",  # Vim swap files
    ]
    
    # Directory patterns (to move entire directories)
    dir_patterns = [
        "tmp",
        "temp",
        ".tmp",
        ".temp",
    ]
    
    # Find files matching patterns
    for pattern in patterns:
        try:
            for file in project_path.rglob(pattern):
                if file.is_file():
                    # Skip if in venv, .git, node_modules, or already in garbage
                    rel_path = str(file.relative_to(project_path))
                    if any(skip in rel_path for skip in ["venv", ".git", "node_modules", "garbage", "__pycache__"]):
                        continue
                    garbage_files.append(file)
        except Exception:
            pass  # Skip if there's an error
    
    # Find directories matching patterns
    for dir_pattern in dir_patterns:
        try:
            for dir_path in project_path.rglob(dir_pattern):
                if dir_path.is_dir():
                    # Skip if in venv, .git, node_modules, or already in garbage
                    rel_path = str(dir_path.relative_to(project_path))
                    if any(skip in rel_path for skip in ["venv", ".git", "node_modules", "garbage", "__pycache__"]):
                        continue
                    # Only add if it's a direct match (not a subdirectory)
                    if dir_path.name == dir_pattern:
                        garbage_files.append(dir_path)
        except Exception:
            pass
    
    # Find old log files (older than 30 days)
    try:
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for log_file in project_path.rglob("*.log"):
            if log_file.is_file():
                rel_path = str(log_file.relative_to(project_path))
                if any(skip in rel_path for skip in ["venv", ".git", "node_modules", "garbage"]):
                    continue
                
                # Check if file is old
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        garbage_files.append(log_file)
                except Exception:
                    pass
    except Exception:
        pass
    
    return list(set(garbage_files))  # Remove duplicates


@dataclass
class GarbageMoveResult:
    """Result of moving garbage files."""
    project_path: Path
    project_name: str
    garbage_dir: Path
    moved_files: List[Path] = field(default_factory=list)
    moved_dirs: List[Path] = field(default_factory=list)
    failed: List[Tuple[str, str]] = field(default_factory=list)  # (path, error)
    total_size: int = 0
    
    @property
    def success_count(self) -> int:
        return len(self.moved_files) + len(self.moved_dirs)
    
    @property
    def failed_count(self) -> int:
        return len(self.failed)


def move_garbage_files(
    project_path: Path,
    dry_run: bool = False
) -> GarbageMoveResult:
    """
    Move garbage files to garbage directory.
    
    Args:
        project_path: Path to project root
        dry_run: If True, only simulate (don't actually move)
    
    Returns:
        GarbageMoveResult with list of moved files and any errors
    """
    project_path = project_path.resolve()
    garbage_dir = get_garbage_dir(project_path)
    
    result = GarbageMoveResult(
        project_path=project_path,
        project_name=project_path.name,
        garbage_dir=garbage_dir
    )
    
    # Find garbage files
    print(f"   🔍 Scanning for garbage files...", end="", flush=True)
    garbage_files = find_garbage_files(project_path)
    print(f" found {len(garbage_files)} items")
    
    if not garbage_files:
        return result
    
    # Move files and directories
    for idx, item in enumerate(garbage_files, 1):
        try:
            if idx % 10 == 0:
                print(f"   Moving... {idx}/{len(garbage_files)}", end="\r", flush=True)
            
            rel_path = item.relative_to(project_path)
            dest_path = garbage_dir / rel_path
            
            if not dry_run:
                # Create parent directories
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file or directory
                if item.is_file():
                    size = item.stat().st_size
                    shutil.move(str(item), str(dest_path))
                    result.moved_files.append(item)
                    result.total_size += size
                elif item.is_dir():
                    size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    shutil.move(str(item), str(dest_path))
                    result.moved_dirs.append(item)
                    result.total_size += size
            else:
                # Dry run - just record
                if item.is_file():
                    size = item.stat().st_size
                    result.moved_files.append(item)
                    result.total_size += size
                elif item.is_dir():
                    size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    result.moved_dirs.append(item)
                    result.total_size += size
        
        except Exception as e:
            result.failed.append((str(item), str(e)))
    
    if not dry_run and garbage_files:
        print(f"   Moved {len(garbage_files)}/{len(garbage_files)} items" + " " * 30)
    
    return result


def format_garbage_report(result: GarbageMoveResult, dry_run: bool = False) -> str:
    """
    Format garbage move result as readable report.
    """
    lines = []
    
    mode = "DRY RUN" if dry_run else "COMPLETE"
    lines.append("╔══════════════════════════════════════════════════════════════════╗")
    lines.append(f"║  🗑️  GARBAGE CLEAN — {mode:<48}║")
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    
    lines.append(f"║  Project: {result.project_name:<55}║")
    
    # Show garbage path relative to project
    garbage_rel = f"../{result.project_name}_garbage_for_removal/"
    lines.append(f"║  Garbage: {garbage_rel:<54}║")
    
    if result.moved_files or result.moved_dirs:
        size_mb = result.total_size / (1024 * 1024)
        size_str = f"{size_mb:.1f}MB" if size_mb >= 1 else f"{result.total_size / 1024:.1f}KB"
        
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  ✅ MOVED ({result.success_count} items, {size_str}):{' '*(40-len(size_str))}║")
        
        # Show first 10 files
        for i, file in enumerate(result.moved_files[:10]):
            prefix = "└─" if i == min(len(result.moved_files), 10) - 1 and not result.moved_dirs else "├─"
            rel = str(file.relative_to(result.project_path))[:50]
            if len(str(file.relative_to(result.project_path))) > 50:
                rel = rel[:47] + "..."
            lines.append(f"║  {prefix} {rel:<50}║")
        
        # Show directories
        for i, dir_path in enumerate(result.moved_dirs[:5]):
            prefix = "└─" if i == len(result.moved_dirs) - 1 else "├─"
            rel = str(dir_path.relative_to(result.project_path))[:50]
            if len(str(dir_path.relative_to(result.project_path))) > 50:
                rel = rel[:47] + "..."
            lines.append(f"║  {prefix} {rel}/ (directory){' '*(37-len(rel))}║")
        
        if len(result.moved_files) + len(result.moved_dirs) > 15:
            remaining = len(result.moved_files) + len(result.moved_dirs) - 15
            lines.append(f"║  ... and {remaining} more items{' '*45}║")
    
    if result.failed:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  ❌ FAILED ({len(result.failed)} items):{' '*44}║")
        for path, error in result.failed[:5]:
            path_short = path[:30]
            error_short = error[:25]
            lines.append(f"║  ├─ {path_short:<30}: {error_short:<25}{' '*5}║")
    
    if dry_run:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append("║  Run without --dry-run to apply changes                       ║")
    
    lines.append("╚══════════════════════════════════════════════════════════════════╝")
    
    return "\n".join(lines)

