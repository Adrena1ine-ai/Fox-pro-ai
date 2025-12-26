"""
Auto-generate PROJECT_STATUS.md from actual codebase state.
Scans commands, utilities, generators, and tests to build accurate status.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional


def scan_commands(src_path: Path) -> List[Dict[str, str]]:
    """
    Scan src/commands/ and return list of implemented commands.
    Parses AST to find cmd_* functions and their docstrings.
    """
    commands = []
    commands_dir = src_path / "commands"
    
    if not commands_dir.exists():
        return commands
    
    for py_file in commands_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("cmd_"):
                    cmd_name = node.name.replace("cmd_", "")
                    docstring = ast.get_docstring(node) or "No description"
                    commands.append({
                        "name": cmd_name,
                        "file": py_file.name,
                        "description": docstring.split("\n")[0]
                    })
        except SyntaxError:
            continue
    
    return commands


def scan_utilities(src_path: Path) -> List[Dict[str, str]]:
    """Scan src/utils/ for utility modules."""
    utils = []
    utils_dir = src_path / "utils"
    
    if not utils_dir.exists():
        return utils
    
    for py_file in utils_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content)
            module_doc = ast.get_docstring(tree) or py_file.stem.replace("_", " ").title()
            
            utils.append({
                "name": py_file.stem,
                "file": f"src/utils/{py_file.name}",
                "description": module_doc.split("\n")[0]
            })
        except SyntaxError:
            continue
    
    return utils


def scan_generators(src_path: Path) -> List[Dict[str, str]]:
    """Scan src/generators/ for generator modules."""
    generators = []
    gen_dir = src_path / "generators"
    
    if not gen_dir.exists():
        return generators
    
    for py_file in gen_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content)
            module_doc = ast.get_docstring(tree) or py_file.stem.replace("_", " ").title()
            
            generators.append({
                "name": py_file.stem,
                "file": f"src/generators/{py_file.name}",
                "description": module_doc.split("\n")[0]
            })
        except SyntaxError:
            continue
    
    return generators


def run_tests(project_root: Path) -> Tuple[int, int]:
    """Run pytest and return (passed, total)."""
    try:
        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=no", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=project_root
        )
        
        output = result.stdout + result.stderr
        
        # Parse "X passed" or "X passed, Y failed"
        for line in output.split("\n"):
            if "passed" in line:
                match = re.search(r"(\d+)\s+passed", line)
                if match:
                    passed = int(match.group(1))
                    # Check for failed
                    failed_match = re.search(r"(\d+)\s+failed", line)
                    failed = int(failed_match.group(1)) if failed_match else 0
                    return passed, passed + failed
        
        return 0, 0
    except Exception:
        return 0, 0


def check_file_exists(project_root: Path, filepath: str) -> bool:
    """Check if a file exists in project."""
    return (project_root / filepath).exists()


def get_version(project_root: Path) -> str:
    """Get current version from constants.py."""
    constants_file = project_root / "src" / "core" / "constants.py"
    if constants_file.exists():
        content = constants_file.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if "VERSION" in line and "=" in line and not line.strip().startswith("#"):
                # Extract version string
                try:
                    version = line.split("=")[1].strip().strip('"\'')
                    return version
                except IndexError:
                    continue
    return "3.3"


def parse_technical_spec(project_root: Path) -> Dict:
    """Parse TECHNICAL_SPECIFICATION.md to extract phase information."""
    spec_file = project_root / "TECHNICAL_SPECIFICATION.md"
    phases = {}
    current_phase = None
    
    if not spec_file.exists():
        return phases
    
    try:
        content = spec_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        for i, line in enumerate(lines):
            # Detect phase headers
            if line.startswith("### Phase"):
                # Extract phase number and name
                match = re.search(r"Phase (\d+):\s*(.+?)\s*\[", line)
                if match:
                    phase_num = int(match.group(1))
                    phase_name = match.group(2).strip()
                    status_match = re.search(r"\[([^\]]+)\]", line)
                    status = status_match.group(1) if status_match else "UNKNOWN"
                    phases[phase_num] = {
                        "name": phase_name,
                        "status": status,
                        "items": []
                    }
                    current_phase = phase_num
            
            # Detect checklist items
            elif current_phase and line.strip().startswith("- ["):
                item_text = line.strip()
                is_completed = "[x]" in item_text or "[X]" in item_text
                item_desc = re.sub(r"^-\s*\[[xX\s]\]\s*", "", item_text)
                phases[current_phase]["items"].append({
                    "description": item_desc,
                    "completed": is_completed
                })
    
    except Exception:
        pass
    
    return phases


def check_manifesto_compliance(project_root: Path) -> Dict[str, bool]:
    """Check if project follows principles from first manifesto.md."""
    manifesto_file = project_root / "first manifesto.md"
    compliance = {
        "venv_outside": False,
        "cursorignore_exists": False,
        "ai_include_exists": False,
        "bootstrap_exists": False
    }
    
    if not manifesto_file.exists():
        return compliance
    
    # Check for venv outside (no venv in project root)
    venv_dirs = ["venv", ".venv", "venv_gate"]
    compliance["venv_outside"] = not any(
        (project_root / v).exists() for v in venv_dirs
    )
    
    # Check for .cursorignore
    compliance["cursorignore_exists"] = (project_root / ".cursorignore").exists()
    
    # Check for _AI_INCLUDE
    compliance["ai_include_exists"] = (project_root / "_AI_INCLUDE").exists()
    
    # Check for bootstrap scripts
    compliance["bootstrap_exists"] = (
        (project_root / "scripts" / "bootstrap.sh").exists() or
        (project_root / "scripts" / "bootstrap.ps1").exists()
    )
    
    return compliance


def generate_status_md(project_root: Path, skip_tests: bool = False) -> str:
    """
    Generate complete PROJECT_STATUS.md content.
    Includes roadmap progress from TECHNICAL_SPECIFICATION.md and manifesto compliance.
    
    Args:
        project_root: Path to project root
        skip_tests: If True, don't run pytest (faster)
    """
    src_path = project_root / "src"
    version = get_version(project_root)
    
    commands = scan_commands(src_path)
    utilities = scan_utilities(src_path)
    generators = scan_generators(src_path)
    
    # Parse roadmap from TECHNICAL_SPECIFICATION.md
    phases = parse_technical_spec(project_root)
    
    # Check manifesto compliance
    compliance = check_manifesto_compliance(project_root)
    
    if skip_tests:
        passed, total = 0, 0
        test_status = "Skipped (use --run-tests to include)"
    else:
        passed, total = run_tests(project_root)
        if total > 0:
            test_status = f"{passed}/{total} passed ({int(passed/total*100)}%)"
        else:
            test_status = "No tests found or pytest not available"
    
    # Determine current phase
    current_phase_num = 0
    current_phase_name = "Unknown"
    for phase_num in sorted(phases.keys(), reverse=True):
        phase = phases[phase_num]
        if "COMPLETED" in phase["status"]:
            current_phase_num = phase_num
            current_phase_name = phase["name"]
            break
    
    # Calculate phase progress
    phase_progress = {}
    for phase_num, phase in phases.items():
        total_items = len(phase["items"])
        completed = sum(1 for item in phase["items"] if item["completed"])
        if total_items > 0:
            progress_pct = int((completed / total_items) * 100)
        else:
            progress_pct = 100 if "COMPLETED" in phase["status"] else 0
        phase_progress[phase_num] = {
            "completed": completed,
            "total": total_items,
            "percent": progress_pct,
            "status": phase["status"]
        }
    
    # Build markdown
    lines = [
        f"# 📊 Project Status — Fox Pro AI v{version}",
        "",
        "> ⚡ Auto-generated from codebase. Do not edit manually.",
        f"> 🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 🗺️ Current Development Phase",
        "",
        f"**Phase {current_phase_num}: {current_phase_name}**",
        "",
        f"*Status: {phases.get(current_phase_num, {}).get('status', 'Unknown')}*",
        "",
        "---",
        "",
        "## 📦 Roadmap Progress (from TECHNICAL_SPECIFICATION.md)",
        "",
    ]
    
    # Show phases with progress
    for phase_num in sorted(phases.keys()):
        phase = phases[phase_num]
        progress = phase_progress.get(phase_num, {})
        status_icon = "✅" if "COMPLETED" in phase["status"] else "🔄" if "PLANNED" in phase["status"] or "IN PROGRESS" in phase["status"] else "⬜"
        
        lines.append(f"### Phase {phase_num}: {phase['name']} {status_icon}")
        
        if progress.get("total", 0) > 0:
            lines.append(f"- Progress: {progress['completed']}/{progress['total']} items ({progress['percent']}%)")
        else:
            lines.append(f"- Status: {phase['status']}")
        
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "## ✅ Implemented Commands",
        "",
    ])
    
    # Commands table
    if commands:
        lines.append("| Command | Description |")
        lines.append("|---------|-------------|")
        for cmd in sorted(commands, key=lambda x: x["name"]):
            lines.append(f"| `{cmd['name']}` | {cmd['description']} |")
    else:
        lines.append("_No commands found_")
    
    lines.extend([
        "",
        "---",
        "",
        "## 🛠️ Utilities",
        "",
    ])
    
    for util in utilities:
        lines.append(f"- [x] `{util['file']}` — {util['description']}")
    
    if not utilities:
        lines.append("_No utilities found_")
    
    lines.extend([
        "",
        "---",
        "",
        "## 🏭 Generators",
        "",
    ])
    
    for gen in generators:
        lines.append(f"- [x] `{gen['file']}` — {gen['description']}")
    
    if not generators:
        lines.append("_No generators found_")
    
    lines.extend([
        "",
        "---",
        "",
        "## 📋 Manifesto Compliance (first manifesto.md)",
        "",
    ])
    
    # Show compliance status
    compliance_items = [
        ("venv_outside", "Virtual environments outside project"),
        ("cursorignore_exists", ".cursorignore configured"),
        ("ai_include_exists", "_AI_INCLUDE directory exists"),
        ("bootstrap_exists", "Bootstrap scripts available"),
    ]
    
    lines.append("| Principle | Status |")
    lines.append("|-----------|--------|")
    for key, desc in compliance_items:
        status = "✅" if compliance.get(key, False) else "❌"
        lines.append(f"| {desc} | {status} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## 📁 Documentation Status",
        "",
    ])
    
    docs = [
        ("README.md", "Project overview"),
        ("TECHNICAL_SPECIFICATION.md", "Roadmap (Strategy)"),
        ("first manifesto.md", "Project constitution"),
        ("PROMPTS_LIBRARY.md", "Curated prompts for AI"),
        ("TRADEOFFS.md", "Architectural decisions"),
        ("CLAUDE.md", "Claude AI instructions"),
        ("CONTRIBUTING.md", "Contribution guide"),
        ("_AI_INCLUDE/WHERE_THINGS_LIVE.md", "Location guide"),
        ("_AI_INCLUDE/PROJECT_CONVENTIONS.md", "Project conventions"),
        (".cursor/rules/project.md", "Cursor project rules"),
    ]
    
    lines.append("| Document | Status |")
    lines.append("|----------|--------|")
    for doc_path, desc in docs:
        exists = check_file_exists(project_root, doc_path)
        status = "✅" if exists else "❌"
        lines.append(f"| `{doc_path}` | {status} {desc} |")
    
    lines.extend([
        "",
        "---",
        "",
        "## 📈 Test Coverage",
        "",
        "```",
        f"Tests: {test_status}",
        "```",
        "",
        "---",
        "",
        "## 📊 Quick Stats",
        "",
        f"- **Commands:** {len(commands)}",
        f"- **Utilities:** {len(utilities)}",
        f"- **Generators:** {len(generators)}",
        f"- **Version:** {version}",
        f"- **Current Phase:** Phase {current_phase_num}",
        "",
        "---",
        "",
        "## 🔗 Quick Links",
        "",
        "| Document | Purpose |",
        "|----------|---------|",
        "| `TECHNICAL_SPECIFICATION.md` | Roadmap (Strategy) |",
        "| `first manifesto.md` | Constitution (Principles) |",
        "| `_AI_INCLUDE/WHERE_THINGS_LIVE.md` | Rules (Tactics) |",
        "| `CURRENT_CONTEXT_MAP.md` | Auto-generated structure |",
        "| `.cursor/rules/project.md` | Cursor rules |",
        "",
        "---",
        "",
        f"*Auto-generated by Fox Pro AI v{version} — Status Generator*",
        f"*Synced with TECHNICAL_SPECIFICATION.md and first manifesto.md*",
    ])
    
    return "\n".join(lines)


def update_status(project_root: Path, skip_tests: bool = False) -> Path:
    """
    Generate and write PROJECT_STATUS.md.
    
    Returns:
        Path to the generated file
    """
    content = generate_status_md(project_root, skip_tests=skip_tests)
    status_file = project_root / "PROJECT_STATUS.md"
    status_file.write_text(content, encoding="utf-8")
    return status_file

