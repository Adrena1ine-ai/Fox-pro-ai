"""
AI config generator (.cursorrules, copilot-instructions.md, CLAUDE.md)
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

from ..core.file_utils import create_file
from ..core.constants import COLORS


def get_common_rules(project_name: str, date: str) -> str:
    """Common rules for all AI assistants"""
    return f"""# Project: {project_name}
# Generated: {date}

## FIRST ACTION

Read `_AI_INCLUDE/` - all project rules are there.

## FORBIDDEN

- Do NOT create venv/, .venv/ inside project -> use ../_venvs/
- Do NOT read large files fully (logs, csv, sqlite)
- Do NOT duplicate existing files

## CORRECT ACTIONS

```bash
# Activate venv
source ../_venvs/{project_name}-venv/bin/activate

# Read data
head -10 data/file.csv
tail -50 logs/bot.log
sqlite3 database/app.sqlite3 ".schema"
```

## Context Switcher

```bash
python scripts/context.py bot   # Focus on bot
python scripts/context.py all   # Show all
```
"""


def generate_cursor_rules(project_dir: Path, project_name: str, date: str) -> None:
    """Generate .cursorrules"""
    content = get_common_rules(project_name, date)
    create_file(project_dir / ".cursorrules", content)


def generate_cursor_ignore(project_dir: Path, project_name: str, date: str) -> None:
    """Generate .cursorignore"""
    content = f"""# Cursor Ignore - {project_name}
# Generated: {date}

# Environments
venv/
.venv/
**/.venv*/
**/site-packages/

# Python
**/__pycache__/
**/*.pyc
**/*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Logs & Data
logs/
*.log
**/*.csv
**/*.jsonl
**/*.db
**/*.sqlite
**/*.sqlite3

# Frontend
node_modules/
dist/
build/
.next/

# Playwright
**/playwright/driver/

# IDE & Git
.git/
.idea/
*.swp
"""
    create_file(project_dir / ".cursorignore", content)


def generate_copilot_instructions(project_dir: Path, project_name: str, date: str) -> None:
    """Generate .github/copilot-instructions.md"""
    content = f"""# Copilot Instructions - {project_name}

{get_common_rules(project_name, date)}

## Additional for Copilot

- Use type hints in Python code
- Prefer async/await for I/O operations
- Follow project structure in _AI_INCLUDE/
- Use pydantic for data validation
"""
    (project_dir / ".github").mkdir(exist_ok=True)
    create_file(project_dir / ".github" / "copilot-instructions.md", content)


def generate_claude_md(project_dir: Path, project_name: str, date: str) -> None:
    """Generate CLAUDE.md"""
    content = f"""# Claude Instructions - {project_name}

{get_common_rules(project_name, date)}

## Additional for Claude

- Check file existence before working with files
- Use view tool to read _AI_INCLUDE/
- Propose changes via str_replace
- Do not read large files fully
"""
    create_file(project_dir / "CLAUDE.md", content)


def generate_windsurf_rules(project_dir: Path, project_name: str, date: str) -> None:
    """Generate .windsurfrules"""
    content = get_common_rules(project_name, date)
    create_file(project_dir / ".windsurfrules", content)


def generate_ai_include(project_dir: Path, project_name: str, date: str) -> None:
    """Generate _AI_INCLUDE/"""
    ai_dir = project_dir / "_AI_INCLUDE"
    ai_dir.mkdir(exist_ok=True)
    
    # PROJECT_CONVENTIONS.md
    conventions = f"""# Project Conventions - {project_name}
# This file is read by AI. Humans can read it too.

## Source code (read/edit freely)
bot/, handlers/, utils/, api/, webapp/, parser/, database/ - *.py files

## Never create venv inside repo
Do NOT create: venv/, .venv/, */.venv*/
Use external: ../_venvs/{project_name}-venv

Create via: ./scripts/bootstrap.sh

## Artifacts
- Logs: logs/ (gitignored)
- Data: data/ (gitignored)
- Heavy: ../_data/{project_name}/

## Before creating any file
1. Check _AI_INCLUDE/WHERE_IS_WHAT.md
2. Verify file doesn't exist
3. Use correct directory
"""
    create_file(ai_dir / "PROJECT_CONVENTIONS.md", conventions)
    
    # WHERE_IS_WHAT.md
    where_is_what = f"""# Where Is What - {project_name}

## Code Structure
```
bot/handlers/     - command handlers
bot/keyboards/    - keyboards
bot/utils/        - utilities
webapp/           - Mini App (HTML/JS/CSS)
scripts/          - helper scripts
database/         - DB operations
api/              - API server
```

## Data (DON'T read fully)
```
logs/             -> tail -50 logs/bot.log
data/             -> head -10 data/file.csv
database/*.db     -> sqlite3 ... ".schema"
```

## Virtual Environment
Location: ../_venvs/{project_name}-venv/
Activate: source ../_venvs/{project_name}-venv/bin/activate
"""
    create_file(ai_dir / "WHERE_IS_WHAT.md", where_is_what)


def generate_ai_configs(
    project_dir: Path,
    project_name: str,
    ai_targets: list[str],
    date: str = None
) -> None:
    """
    Create all AI configs
    
    Args:
        project_dir: Project path
        project_name: Project name
        ai_targets: AI list (cursor, copilot, claude, windsurf)
        date: Date (default today)
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n{COLORS.colorize('AI configs...', COLORS.CYAN)}")
    
    # Cursor
    if "cursor" in ai_targets:
        generate_cursor_rules(project_dir, project_name, date)
        generate_cursor_ignore(project_dir, project_name, date)
    
    # Copilot
    if "copilot" in ai_targets:
        generate_copilot_instructions(project_dir, project_name, date)
    
    # Claude
    if "claude" in ai_targets:
        generate_claude_md(project_dir, project_name, date)
    
    # Windsurf
    if "windsurf" in ai_targets:
        generate_windsurf_rules(project_dir, project_name, date)
    
    # _AI_INCLUDE always
    print(f"\n{COLORS.colorize('_AI_INCLUDE/...', COLORS.CYAN)}")
    generate_ai_include(project_dir, project_name, date)
