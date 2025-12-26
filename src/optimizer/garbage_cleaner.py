"""
Garbage Cleaner — Find and move temporary/old files.
Separates garbage cleanup from Deep Clean (which handles heavy files).
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import shutil
import os


# Patterns for garbage files
GARBAGE_PATTERNS: Set[str] = {
    # Temp files
    "*.tmp", "*.temp", "*.bak", "*.old", "*.backup",
    "*.swp", "*.swo",  # Vim swap
    "*~",  # Backup files
    
    # Log files (old)
    "*.log.old", "*.log.1", "*.log.2", "*.log.bak",
    
    # System files
    ".DS_Store", "Thumbs.db", "desktop.ini", "ehthumbs.db",
    
    # Python
    "*.pyc", "*.pyo",
    
    # IDE
    "*.sublime-workspace",
}

# Directories to skip
SKIP_DIRS: Set[str] = {
    "venv", ".venv", "env", ".env",
    "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    ".git", ".svn", ".hg",
    ".idea", ".vscode",
    "_data", "_venvs", "_artifacts",
}

# Max age for log files (in days)
LOG_MAX_AGE_DAYS = 30


@dataclass
class GarbageFile:
    """Represents a garbage file to be cleaned."""
    path: Path
    relative_path: str
    size_bytes: int
    reason: str  # Why it's garbage
    age_days: Optional[int] = None


@dataclass
class GarbageCleanResult:
    """Result of garbage cleaning operation."""
    project_path: Path
    garbage_dir: Path
    files_found: List[GarbageFile] = field(default_factory=list)
    files_moved: List[GarbageFile] = field(default_factory=list)
    files_failed: List[Tuple[str, str]] = field(default_factory=list)
    
    @property
    def total_size(self) -> int:
        return sum(f.size_bytes for f in self.files_found)
    
    @property
    def moved_size(self) -> int:
        return sum(f.size_bytes for f in self.files_moved)
    
    @property
    def success_count(self) -> int:
        return len(self.files_moved)


def is_old_log(file_path: Path, max_age_days: int = LOG_MAX_AGE_DAYS) -> bool:
    """Check if a log file is older than max_age_days."""
    if not file_path.suffix == ".log":
        return False
    
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.days > max_age_days
    except (OSError, IOError):
        return False


def get_file_age_days(file_path: Path) -> Optional[int]:
    """Get file age in days."""
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return (datetime.now() - mtime).days
    except (OSError, IOError):
        return None


def scan_garbage(
    project_path: Path,
    include_old_logs: bool = True,
    log_max_age: int = LOG_MAX_AGE_DAYS
) -> List[GarbageFile]:
    """
    Scan project for garbage files.
    
    Args:
        project_path: Project root
        include_old_logs: If True, include log files older than log_max_age
        log_max_age: Max age for log files in days
    
    Returns:
        List of garbage files found
    """
    project_path = project_path.resolve()
    garbage_files = []
    
    for root, dirs, files in os.walk(project_path):
        # Filter out skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        
        root_path = Path(root)
        
        for file_name in files:
            file_path = root_path / file_name
            reason = None
            
            # Check against patterns
            for pattern in GARBAGE_PATTERNS:
                if file_path.match(pattern):
                    reason = f"Matches pattern: {pattern}"
                    break
            
            # Check for old logs
            if reason is None and include_old_logs and is_old_log(file_path, log_max_age):
                reason = f"Log file older than {log_max_age} days"
            
            if reason:
                try:
                    garbage_files.append(GarbageFile(
                        path=file_path,
                        relative_path=str(file_path.relative_to(project_path)),
                        size_bytes=file_path.stat().st_size,
                        reason=reason,
                        age_days=get_file_age_days(file_path)
                    ))
                except (OSError, IOError):
                    continue
    
    # Sort by size (largest first)
    garbage_files.sort(key=lambda x: x.size_bytes, reverse=True)
    
    return garbage_files


def clean_garbage(
    project_path: Path,
    dry_run: bool = False,
    include_old_logs: bool = True,
    log_max_age: int = LOG_MAX_AGE_DAYS
) -> GarbageCleanResult:
    """
    Find and move garbage files to garbage directory.
    
    Args:
        project_path: Project root
        dry_run: If True, don't actually move files
        include_old_logs: Include old log files
        log_max_age: Max age for logs in days
    
    Returns:
        GarbageCleanResult with statistics
    """
    from .heavy_mover import get_garbage_dir
    
    project_path = project_path.resolve()
    garbage_dir = get_garbage_dir(project_path, create=not dry_run)
    
    result = GarbageCleanResult(
        project_path=project_path,
        garbage_dir=garbage_dir
    )
    
    # Scan for garbage
    result.files_found = scan_garbage(
        project_path, 
        include_old_logs=include_old_logs,
        log_max_age=log_max_age
    )
    
    if dry_run:
        return result
    
    # Move files
    for gf in result.files_found:
        try:
            # Preserve directory structure
            dest_path = garbage_dir / gf.relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(gf.path), str(dest_path))
            result.files_moved.append(gf)
            
        except Exception as e:
            result.files_failed.append((gf.relative_path, str(e)))
    
    return result


def format_garbage_report(result: GarbageCleanResult, dry_run: bool = False) -> str:
    """Format garbage clean result as readable report."""
    lines = []
    
    lines.append("╔══════════════════════════════════════════════════════════════════╗")
    if dry_run:
        lines.append("║  🗑️  GARBAGE SCAN — Preview (Dry Run)                           ║")
    else:
        lines.append("║  🗑️  GARBAGE CLEAN — Files Moved                                ║")
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    
    lines.append(f"║  Project: {result.project_path.name:<55}║")
    
    total_kb = result.total_size / 1024
    lines.append(f"║  Garbage Found: {len(result.files_found)} files ({total_kb:.1f} KB){' '*(35-len(f'{total_kb:.1f}'))}║")
    
    if result.files_found:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append("║  FILES:                                                          ║")
        
        for i, gf in enumerate(result.files_found[:10]):
            prefix = "└─" if i == min(len(result.files_found), 10) - 1 else "├─"
            size_str = f"{gf.size_bytes/1024:.1f}KB"
            path_str = gf.relative_path[:40]
            lines.append(f"║  {prefix} {path_str:<40} {size_str:>8}    ║")
        
        if len(result.files_found) > 10:
            lines.append(f"║  ... and {len(result.files_found) - 10} more files{' '*45}║")
    
    if not dry_run:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        moved_kb = result.moved_size / 1024
        lines.append(f"║  ✅ Moved: {len(result.files_moved)} files ({moved_kb:.1f} KB){' '*(39-len(f'{moved_kb:.1f}'))}║")
        lines.append(f"║  📁 Location: {str(result.garbage_dir.name):<51}║")
        
        if result.files_failed:
            lines.append(f"║  ❌ Failed: {len(result.files_failed)} files{' '*46}║")
    
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    if dry_run:
        lines.append("║  💡 Run without --dry-run to move these files                   ║")
    else:
        garbage_name = str(result.garbage_dir.name)[:40]
        lines.append(f"║  💡 Review and delete: {garbage_name:<40}║")
    lines.append("╚══════════════════════════════════════════════════════════════════╝")
    
    return "\n".join(lines)

