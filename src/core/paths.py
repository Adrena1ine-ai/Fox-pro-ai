"""
🦊 Fox Pro AI — Unified Path System

Single source of truth for all external paths.
All modules MUST use these functions.

External structure:
    ../PROJECT_NAME_fox/
    ├── data/           # Heavy data files (Deep Clean)
    ├── venvs/          # Virtual environments
    ├── logs/           # Archived logs
    ├── garbage/        # Garbage for deletion
    └── manifest.json   # External storage manifest
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


# ══════════════════════════════════════════════════════════════
# PATH FUNCTIONS
# ══════════════════════════════════════════════════════════════

def get_external_root(project_path: Path) -> Path:
    """
    Get root of external storage.
    
    project/          → ../project_fox/
    /home/user/mybot/ → /home/user/mybot_fox/
    
    Args:
        project_path: Path to project directory
        
    Returns:
        Path to external storage root
    """
    project_path = Path(project_path).resolve()
    project_name = project_path.name
    return project_path.parent / f"{project_name}_fox"


def get_external_data_dir(project_path: Path) -> Path:
    """Get directory for heavy data files."""
    return get_external_root(project_path) / "data"


def get_external_venvs_dir(project_path: Path) -> Path:
    """Get directory for virtual environments."""
    return get_external_root(project_path) / "venvs"


def get_external_logs_dir(project_path: Path) -> Path:
    """Get directory for archived logs."""
    return get_external_root(project_path) / "logs"


def get_external_garbage_dir(project_path: Path) -> Path:
    """Get directory for garbage (files to delete)."""
    return get_external_root(project_path) / "garbage"


def get_manifest_path(project_path: Path) -> Path:
    """Get path to external storage manifest."""
    return get_external_root(project_path) / "manifest.json"


# ══════════════════════════════════════════════════════════════
# STRUCTURE CREATION
# ══════════════════════════════════════════════════════════════

def ensure_external_structure(project_path: Path) -> Path:
    """
    Create external storage structure if not exists.
    
    Args:
        project_path: Path to project directory
        
    Returns:
        Path to external root
    """
    external_root = get_external_root(project_path)
    
    # Create all directories
    (external_root / "data").mkdir(parents=True, exist_ok=True)
    (external_root / "venvs").mkdir(parents=True, exist_ok=True)
    (external_root / "logs").mkdir(parents=True, exist_ok=True)
    (external_root / "garbage").mkdir(parents=True, exist_ok=True)
    
    # Create manifest if not exists
    manifest_path = get_manifest_path(project_path)
    if not manifest_path.exists():
        manifest = {
            "version": "4.0.0",
            "project_name": project_path.name,
            "created_at": datetime.now().isoformat(),
            "files": [],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))
    
    return external_root


# ══════════════════════════════════════════════════════════════
# MANIFEST OPERATIONS
# ══════════════════════════════════════════════════════════════

def load_manifest(project_path: Path) -> Dict[str, Any]:
    """Load manifest from external storage."""
    manifest_path = get_manifest_path(project_path)
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return {"version": "4.0.0", "files": []}


def save_manifest(project_path: Path, manifest: Dict[str, Any]) -> None:
    """Save manifest to external storage."""
    manifest_path = get_manifest_path(project_path)
    manifest["updated_at"] = datetime.now().isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2))


def add_to_manifest(
    project_path: Path,
    original_path: str,
    external_path: str,
    file_type: str = "data",
    tokens: int = 0,
) -> None:
    """Add file to manifest."""
    manifest = load_manifest(project_path)
    
    # Remove if exists
    manifest["files"] = [
        f for f in manifest.get("files", [])
        if f.get("original") != original_path
    ]
    
    # Add new entry
    manifest["files"].append({
        "original": original_path,
        "external": external_path,
        "type": file_type,
        "tokens": tokens,
        "moved_at": datetime.now().isoformat(),
    })
    
    save_manifest(project_path, manifest)


# ══════════════════════════════════════════════════════════════
# LEGACY MIGRATION
# ══════════════════════════════════════════════════════════════

# Old path formats from v3.x
LEGACY_PATHS = {
    "_data": "data",
    "_venvs": "venvs",
    "_logs": "logs",
    "_FOR_DELETION": "garbage",
    "_garbage_for_removal": "garbage",
    "_artifacts": "data",
}


def detect_legacy_external(project_path: Path) -> Optional[Path]:
    """
    Detect legacy external storage format.
    
    Returns:
        Path to legacy external dir or None
    """
    project_path = Path(project_path).resolve()
    parent = project_path.parent
    project_name = project_path.name
    
    # Check old formats
    legacy_patterns = [
        parent / f"{project_name}_data",      # v3.5+ Deep Clean
        parent / "_data" / project_name,       # v3.0 Doctor
        parent / f"_data",                     # v2.x
    ]
    
    for legacy_path in legacy_patterns:
        if legacy_path.exists():
            return legacy_path
    
    return None


def migrate_legacy_to_v4(project_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """
    Migrate legacy external storage to v4 format.
    
    Args:
        project_path: Path to project
        dry_run: If True, only report what would be done
        
    Returns:
        Migration report
    """
    import shutil
    
    project_path = Path(project_path).resolve()
    legacy_path = detect_legacy_external(project_path)
    
    if not legacy_path:
        return {"status": "no_legacy", "migrated": []}
    
    report = {
        "status": "migrated" if not dry_run else "dry_run",
        "legacy_path": str(legacy_path),
        "new_path": str(get_external_root(project_path)),
        "migrated": [],
    }
    
    if dry_run:
        # Just list what would be migrated
        for item in legacy_path.rglob("*"):
            if item.is_file():
                report["migrated"].append(str(item.relative_to(legacy_path)))
        return report
    
    # Create new structure
    new_root = ensure_external_structure(project_path)
    
    # Move files
    for item in legacy_path.iterdir():
        if item.is_dir():
            # Map old dir names to new
            new_name = LEGACY_PATHS.get(item.name, item.name)
            target = new_root / new_name
            
            if target.exists():
                # Merge contents
                for sub_item in item.rglob("*"):
                    if sub_item.is_file():
                        rel = sub_item.relative_to(item)
                        target_file = target / rel
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(sub_item), str(target_file))
                        report["migrated"].append(str(rel))
            else:
                shutil.move(str(item), str(target))
                report["migrated"].append(item.name)
    
    # Remove empty legacy dir
    try:
        legacy_path.rmdir()
    except OSError:
        pass  # Not empty, leave it
    
    return report


# ══════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════

def is_external_path(path: Path, project_path: Path) -> bool:
    """Check if path is in external storage."""
    path = Path(path).resolve()
    external_root = get_external_root(project_path)
    return str(path).startswith(str(external_root))


def get_relative_external_path(path: Path, project_path: Path) -> Optional[str]:
    """Get path relative to external root."""
    path = Path(path).resolve()
    external_root = get_external_root(project_path)
    
    if str(path).startswith(str(external_root)):
        return str(path.relative_to(external_root))
    return None


def external_exists(project_path: Path) -> bool:
    """Check if external storage exists for project."""
    return get_external_root(project_path).exists()
