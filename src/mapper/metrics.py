"""
🦊 Fox Pro AI — Metrics Utilities

Functions for parsing ignore patterns and checking file visibility.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import List, Set, Optional


def parse_cursorignore(project_path: Path) -> Set[str]:
    """
    Parse .cursorignore file and return set of ignore patterns.
    
    Args:
        project_path: Path to project root
        
    Returns:
        Set of ignore patterns
    """
    patterns = set()
    
    cursorignore = project_path / ".cursorignore"
    if not cursorignore.exists():
        return patterns
    
    try:
        content = cursorignore.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            patterns.add(line)
    except Exception:
        pass
    
    return patterns


def should_ignore(
    path: Path,
    root_path: Path,
    patterns: Set[str],
) -> bool:
    """
    Check if path should be ignored based on patterns.
    
    Args:
        path: Path to check
        root_path: Project root path
        patterns: Set of ignore patterns
        
    Returns:
        True if path should be ignored
    """
    if not patterns:
        return False
    
    try:
        rel_path = path.relative_to(root_path)
        rel_str = str(rel_path).replace("\\", "/")
    except ValueError:
        return False
    
    for pattern in patterns:
        # Normalize pattern
        pattern = pattern.rstrip("/")
        
        # Check if pattern matches
        if fnmatch.fnmatch(rel_str, pattern):
            return True
        if fnmatch.fnmatch(rel_str, pattern + "/*"):
            return True
        
        # Check each path component
        for part in rel_path.parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    
    return False


def get_file_stats(project_path: Path) -> dict:
    """
    Get basic file statistics for project.
    
    Args:
        project_path: Path to project
        
    Returns:
        Dict with file counts and sizes
    """
    stats = {
        "total_files": 0,
        "total_size_bytes": 0,
        "python_files": 0,
        "json_files": 0,
        "other_files": 0,
    }
    
    ignore_patterns = parse_cursorignore(project_path)
    
    for path in project_path.rglob("*"):
        if path.is_file():
            if should_ignore(path, project_path, ignore_patterns):
                continue
            
            stats["total_files"] += 1
            
            try:
                stats["total_size_bytes"] += path.stat().st_size
            except (OSError, PermissionError):
                pass
            
            suffix = path.suffix.lower()
            if suffix == ".py":
                stats["python_files"] += 1
            elif suffix == ".json":
                stats["json_files"] += 1
            else:
                stats["other_files"] += 1
    
    return stats
