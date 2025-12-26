"""
Script generator (bootstrap, health_check, context.py)
"""

from __future__ import annotations

from pathlib import Path

from ..core.file_utils import create_file
from ..core.constants import COLORS


def generate_bootstrap_sh(project_dir: Path, project_name: str) -> None:
    """Generate bootstrap.sh"""
    content = f"""#!/usr/bin/env bash
# Bootstrap - {project_name}
# Creates venv OUTSIDE project

set -euo pipefail

PROJ="$(basename "$PWD")"
VENV_DIR="../_venvs/${{PROJ}}-venv"

echo "Bootstrap: $PROJ"
echo "Venv: $VENV_DIR"

# Create venv folder
mkdir -p "../_venvs"

# Create venv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and update pip
source "$VENV_DIR/bin/activate"
pip install -U pip wheel setuptools --quiet

# Install dependencies
if [ -f requirements.txt ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt --quiet
fi

# Install dev dependencies if exist
if [ -f requirements-dev.txt ]; then
    echo "Installing dev dependencies..."
    pip install -r requirements-dev.txt --quiet
fi

echo ""
echo "Done!"
echo "Activate: source $VENV_DIR/bin/activate"
"""
    create_file(project_dir / "scripts" / "bootstrap.sh", content, executable=True)


def generate_bootstrap_ps1(project_dir: Path, project_name: str) -> None:
    """Generate bootstrap.ps1 (Windows)"""
    content = f"""# Bootstrap - {project_name} (Windows)
# Creates venv OUTSIDE project

$ErrorActionPreference = "Stop"

$Proj = Split-Path -Leaf (Get-Location)
$VenvDir = "../_venvs/$Proj-venv"

Write-Host "Bootstrap: $Proj"
Write-Host "Venv: $VenvDir"

# Create venv folder
New-Item -ItemType Directory -Force -Path "../_venvs" | Out-Null

# Create venv if not exists
if (-not (Test-Path $VenvDir)) {{
    Write-Host "Creating venv..."
    python -m venv $VenvDir
}}

# Activate
& "$VenvDir/Scripts/Activate.ps1"
pip install -U pip wheel setuptools --quiet

# Install dependencies
if (Test-Path "requirements.txt") {{
    Write-Host "Installing dependencies..."
    pip install -r requirements.txt --quiet
}}

Write-Host ""
Write-Host "Done!"
Write-Host "Activate: $VenvDir/Scripts/Activate.ps1"
"""
    create_file(project_dir / "scripts" / "bootstrap.ps1", content)


def generate_check_repo_clean(project_dir: Path) -> None:
    """Generate check_repo_clean.sh"""
    content = """#!/usr/bin/env bash
# Check repo is clean (no venv inside)
# Used in pre-commit hook

set -euo pipefail

bad=0

# Check forbidden folders
for p in venv .venv env .env; do
    if [ -d "$p" ] && [ -f "$p/bin/python" -o -f "$p/Scripts/python.exe" ]; then
        echo "ERROR: Virtual environment '$p' found in repo!"
        echo "   Move it to: ../_venvs/$(basename $PWD)-venv"
        bad=1
    fi
done

# Check site-packages
if find . -path "*/site-packages" -prune -print 2>/dev/null | grep -q .; then
    echo "ERROR: site-packages found inside repo!"
    bad=1
fi

# Check large files
large_files=$(find . -type f -size +10M 2>/dev/null | grep -v ".git" | head -5)
if [ -n "$large_files" ]; then
    echo "WARNING: Large files (>10MB) found:"
    echo "$large_files"
fi

if [ $bad -eq 0 ]; then
    echo "Repo is clean!"
fi

exit $bad
"""
    create_file(project_dir / "scripts" / "check_repo_clean.sh", content, executable=True)


def generate_health_check(project_dir: Path, project_name: str) -> None:
    """Generate health_check.sh"""
    content = f"""#!/usr/bin/env bash
# Health Check - {project_name}

set -euo pipefail

echo "Health Check: {project_name}"
echo "========================================"
echo ""

PROJ="$(basename "$PWD")"
VENV_DIR="../_venvs/${{PROJ}}-venv"
errors=0
warnings=0

# 1. Check venv
echo "Virtual Environment:"
if [ -d "$VENV_DIR" ]; then
    echo "   [OK] Venv exists: $VENV_DIR"
else
    echo "   [ERROR] Venv missing: $VENV_DIR"
    echo "      Run: ./scripts/bootstrap.sh"
    errors=$((errors + 1))
fi

# 2. Check venv NOT in project
for p in venv .venv; do
    if [ -d "$p" ]; then
        echo "   [ERROR] Forbidden: $p in project!"
        errors=$((errors + 1))
    fi
done

# 3. Check .env
echo ""
echo "Configuration:"
if [ -f ".env" ]; then
    echo "   [OK] .env exists"
else
    echo "   [WARN] .env missing"
    if [ -f ".env.example" ]; then
        echo "      Run: cp .env.example .env"
    fi
    warnings=$((warnings + 1))
fi

# 4. Check requirements
if [ -f "requirements.txt" ]; then
    echo "   [OK] requirements.txt exists"
else
    echo "   [WARN] requirements.txt missing"
    warnings=$((warnings + 1))
fi

# 5. Check _AI_INCLUDE
echo ""
echo "AI Configuration:"
if [ -d "_AI_INCLUDE" ]; then
    echo "   [OK] _AI_INCLUDE/ exists"
else
    echo "   [ERROR] _AI_INCLUDE/ missing"
    errors=$((errors + 1))
fi

# 6. Check AI configs
for f in ".cursorrules" ".github/copilot-instructions.md" "CLAUDE.md"; do
    if [ -f "$f" ]; then
        echo "   [OK] $f"
    fi
done

# 7. Check Docker
echo ""
echo "Docker:"
if [ -f "Dockerfile" ]; then
    echo "   [OK] Dockerfile exists"
else
    echo "   [INFO] No Dockerfile"
fi

if [ -f "docker-compose.yml" ]; then
    echo "   [OK] docker-compose.yml exists"
fi

# 8. Check CI/CD
echo ""
echo "CI/CD:"
if [ -f ".github/workflows/ci.yml" ]; then
    echo "   [OK] GitHub Actions configured"
else
    echo "   [INFO] No CI/CD configured"
fi

# 9. Check Git
echo ""
echo "Git:"
if [ -d ".git" ]; then
    echo "   [OK] Git repository initialized"
    branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo "   Branch: $branch"
else
    echo "   [WARN] Not a git repository"
    echo "      Run: git init"
    warnings=$((warnings + 1))
fi

# Summary
echo ""
echo "========================================"
if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    echo "[OK] All checks passed!"
elif [ $errors -eq 0 ]; then
    echo "[WARN] $warnings warning(s), no errors"
else
    echo "[ERROR] $errors error(s), $warnings warning(s)"
fi

exit $errors
"""
    create_file(project_dir / "scripts" / "health_check.sh", content, executable=True)


def generate_context_switcher(project_dir: Path) -> None:
    """Generate context.py (Context Switcher)"""
    content = '''#!/usr/bin/env python3
"""
Context Switcher - hides/shows modules from AI
Solves the problem when AI struggles with large projects

Usage:
    python scripts/context.py bot     # Only sees bot/
    python scripts/context.py webapp  # Only sees webapp/
    python scripts/context.py all     # Sees everything
    python scripts/context.py status  # Show current mode
"""

import sys
from pathlib import Path

# Base exclusions (always hidden)
BASE_IGNORE = """
# === ALWAYS IGNORED ===
venv/
.venv/
**/__pycache__/
.git/
logs/
*.log
**/*.csv
**/*.jsonl
**/*.sqlite3
**/*.db
node_modules/
dist/
build/
.next/
**/playwright/driver/
"""

# Modules that can be hidden
MODULES = {
    "bot": ["bot/", "handlers/", "keyboards/"],
    "webapp": ["webapp/", "frontend/", "static/"],
    "parser": ["parser/", "scrapers/"],
    "api": ["api/", "routes/"],
    "db": ["database/", "models/", "migrations/"],
}


def get_current_mode() -> str:
    """Determine current mode from .cursorignore"""
    ignore_file = Path(".cursorignore")
    if not ignore_file.exists():
        return "unknown"
    
    content = ignore_file.read_text()
    for line in content.split("\\n"):
        if line.startswith("# MODE:"):
            return line.replace("# MODE:", "").strip().lower()
    
    return "custom"


def update_ignore(mode: str) -> None:
    """Update .cursorignore for mode"""
    lines = [BASE_IGNORE.strip(), "", f"# MODE: {mode.upper()}", ""]
    
    if mode == "all":
        lines.append("# All modules visible")
    else:
        # Hide all modules except selected
        for module_name, paths in MODULES.items():
            if module_name != mode:
                lines.append(f"# Hidden: {module_name}")
                lines.extend(paths)
        lines.append(f"# Active: {mode}")
    
    Path(".cursorignore").write_text("\\n".join(lines), encoding="utf-8")


def show_status() -> None:
    """Show current status"""
    mode = get_current_mode()
    
    print("Context Switcher Status")
    print("=" * 40)
    print(f"Current mode: {mode.upper()}")
    print()
    
    if mode == "all":
        print("All modules are visible to AI")
    elif mode in MODULES:
        print(f"Visible: {mode}")
        hidden = [m for m in MODULES if m != mode]
        print(f"Hidden: {', '.join(hidden)}")
    else:
        print("Custom or unknown configuration")
    
    print()
    print("Available modes:")
    for m in MODULES:
        print(f"  {m:8} - focus on {m}")
    print(f"  {'all':8} - show everything")


def main():
    if len(sys.argv) < 2:
        show_status()
        print()
        print("Usage: python scripts/context.py <mode>")
        sys.exit(0)
    
    mode = sys.argv[1].lower()
    
    if mode == "status":
        show_status()
        sys.exit(0)
    
    if mode not in [*MODULES.keys(), "all"]:
        print(f"Unknown mode: {mode}")
        print(f"Available: {', '.join(MODULES.keys())}, all")
        sys.exit(1)
    
    update_ignore(mode)
    
    print(f"Mode: {mode.upper()}")
    if mode != "all":
        visible = MODULES.get(mode, [])
        hidden = [m for m in MODULES if m != mode]
        print(f"   Visible: {', '.join(visible)}")
        print(f"   Hidden: {', '.join(hidden)}")
    else:
        print("   All modules visible")


if __name__ == "__main__":
    main()
'''
    create_file(project_dir / "scripts" / "context.py", content, executable=True)


def generate_scripts(project_dir: Path, project_name: str) -> None:
    """
    Create all scripts
    
    Args:
        project_dir: Project path
        project_name: Project name
    """
    print(f"\n{COLORS.colorize('Scripts...', COLORS.CYAN)}")
    
    scripts_dir = project_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    generate_bootstrap_sh(project_dir, project_name)
    generate_bootstrap_ps1(project_dir, project_name)
    generate_check_repo_clean(project_dir)
    generate_health_check(project_dir, project_name)
    generate_context_switcher(project_dir)
