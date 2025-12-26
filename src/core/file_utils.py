"""
File utilities
"""

from __future__ import annotations

import os
import stat
import shutil
from pathlib import Path

from .constants import COLORS


def create_file(
    path: Path, 
    content: str, 
    executable: bool = False,
    quiet: bool = False
) -> None:
    """
    Create file with content
    
    Args:
        path: File path
        content: Content
        executable: Make executable
        quiet: Don't print message
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Add newline at end if not present
    if content and not content.endswith("\n"):
        content = content + "\n"
    path.write_text(content, encoding="utf-8")
    
    if executable:
        make_executable(path)
    
    if not quiet:
        rel_path = path.name if len(str(path)) > 50 else path
        print(f"  {COLORS.success(str(rel_path))}")


def make_executable(path: Path) -> None:
    """Make file executable"""
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def copy_template(
    src: Path, 
    dst: Path, 
    context: dict,
    executable: bool = False
) -> None:
    """
    Copy template with variable substitution
    
    Args:
        src: Source template file
        dst: Target path
        context: Variables dictionary for substitution
        executable: Make executable
    """
    if not src.exists():
        return
    
    content = src.read_text(encoding="utf-8")
    
    # Variable substitution {{variable}}
    for key, value in context.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))
        content = content.replace(f"{{{key}}}", str(value))
    
    create_file(dst, content, executable=executable)


def get_dir_size(path: Path) -> float:
    """Get directory size in MB"""
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except (PermissionError, OSError):
        pass
    return total / (1024 * 1024)


def remove_dir(path: Path) -> bool:
    """Safely remove directory"""
    try:
        if path.exists():
            shutil.rmtree(path)
        return True
    except Exception:
        return False


def copy_dir(src: Path, dst: Path) -> bool:
    """Copy directory"""
    try:
        shutil.copytree(src, dst)
        return True
    except Exception:
        return False


def move_dir(src: Path, dst: Path) -> bool:
    """Move directory"""
    try:
        shutil.move(str(src), str(dst))
        return True
    except Exception:
        return False
