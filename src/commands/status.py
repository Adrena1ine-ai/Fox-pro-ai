"""
🦊 Fox Pro AI — Status Command

Show project optimization status.
"""

from __future__ import annotations

from pathlib import Path

from ..core.constants import COLORS
from ..core.paths import external_exists, load_manifest, get_external_root


def run_status(project_path: Path) -> int:
    """Show project status."""
    project_path = Path(project_path).resolve()
    
    print(f"\n📊 {COLORS.BOLD}Project Status{COLORS.END}")
    print(f"   Path: {project_path}")
    print()
    
    # Check external storage
    if external_exists(project_path):
        manifest = load_manifest(project_path)
        files = manifest.get("files", [])
        total_tokens = sum(f.get("tokens", 0) for f in files)
        
        print(f"📦 {COLORS.GREEN}External storage: Active{COLORS.END}")
        print(f"   Location: {get_external_root(project_path)}")
        print(f"   Files: {len(files)}")
        print(f"   Tokens saved: {total_tokens:,}")
    else:
        print(f"📦 {COLORS.YELLOW}External storage: Not configured{COLORS.END}")
        print(f"   Run 'fox doctor --full' to optimize")
    
    # Check key files
    print(f"\n📁 {COLORS.BOLD}Key Files{COLORS.END}")
    
    files_to_check = [
        (".cursorignore", "Cursor ignore file"),
        ("config_paths.py", "Path bridge"),
        ("AST_FOX_TRACE.md", "Trace map"),
    ]
    
    for filename, description in files_to_check:
        filepath = project_path / filename
        if filepath.exists():
            print(f"   ✅ {filename} — {description}")
        else:
            print(f"   ❌ {filename} — {description}")
    
    return 0
