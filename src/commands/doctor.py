"""
🦊 Fox Pro AI v4.0 — Doctor Command

Unified diagnostics and optimization.

Modes:
    report  — Only show diagnostics (default)
    fix     — Fix issues automatically  
    full    — Full optimization (Deep Clean + everything)
    restore — Restore files from external storage
"""

from __future__ import annotations

import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime

from ..core.constants import COLORS, VERSION
from ..core.paths import (
    get_external_root,
    get_external_data_dir,
    get_external_venvs_dir,
    get_external_garbage_dir,
    ensure_external_structure,
    load_manifest,
    external_exists,
)


# ══════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════

@dataclass
class Issue:
    """Diagnostic issue."""
    severity: str  # CRITICAL, WARNING, SUGGESTION
    category: str  # venv, pycache, tokens, garbage, etc.
    description: str
    path: Optional[Path] = None
    size_bytes: int = 0
    tokens: int = 0
    fix_action: Optional[str] = None


@dataclass 
class DoctorReport:
    """Doctor diagnostic report."""
    project_path: Path
    project_name: str
    scan_time: datetime = field(default_factory=datetime.now)
    
    # Metrics
    total_files: int = 0
    total_size_mb: float = 0
    total_tokens: int = 0
    
    # Issues
    issues: List[Issue] = field(default_factory=list)
    
    # External storage
    external_exists: bool = False
    external_files: int = 0
    external_tokens: int = 0
    
    @property
    def critical_count(self) -> int:
        return len([i for i in self.issues if i.severity == "CRITICAL"])
    
    @property
    def warning_count(self) -> int:
        return len([i for i in self.issues if i.severity == "WARNING"])
    
    @property
    def suggestion_count(self) -> int:
        return len([i for i in self.issues if i.severity == "SUGGESTION"])


@dataclass
class FixResult:
    """Result of fix operation."""
    success: bool
    message: str
    files_moved: int = 0
    files_patched: int = 0
    tokens_saved: int = 0
    errors: List[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# DIAGNOSIS
# ══════════════════════════════════════════════════════════════

def diagnose(project_path: Path, verbose: bool = False) -> DoctorReport:
    """
    Diagnose project for AI optimization issues.
    
    Checks:
        - Virtual environments inside project
        - __pycache__ directories
        - node_modules
        - Heavy files (>1000 tokens)
        - Garbage files (*.tmp, *.bak, etc.)
        - Missing .cursorignore
    """
    project_path = Path(project_path).resolve()
    report = DoctorReport(
        project_path=project_path,
        project_name=project_path.name,
    )
    
    # Check external storage
    report.external_exists = external_exists(project_path)
    if report.external_exists:
        manifest = load_manifest(project_path)
        report.external_files = len(manifest.get("files", []))
        report.external_tokens = sum(f.get("tokens", 0) for f in manifest.get("files", []))
    
    # Scan project
    _scan_for_issues(project_path, report, verbose)
    
    return report


def _scan_for_issues(project_path: Path, report: DoctorReport, verbose: bool):
    """Scan project for issues."""
    
    skip_dirs = {
        ".git", ".svn", ".hg",
        ".idea", ".vscode",
    }
    
    # Directories to detect as issues (not skip!)
    issue_dirs = {
        "venv", ".venv", "env",
        "node_modules",
        "__pycache__", ".pytest_cache", ".mypy_cache",
    }
    
    total_files = 0
    total_size = 0
    
    # Track already reported directories to avoid duplicates
    reported_dirs = set()
    
    for item in project_path.rglob("*"):
        rel_path = item.relative_to(project_path)
        
        # Skip hidden directories (except issue_dirs)
        if any(part.startswith(".") and part not in issue_dirs for part in rel_path.parts[:-1]):
            continue
        
        # Skip .git, .idea, etc.
        if any(part in skip_dirs for part in rel_path.parts):
            continue
        
        # Check for venv inside project (FIRST, before counting)
        if item.is_dir() and item.name in {"venv", ".venv", "env"}:
            if item not in reported_dirs:
                # Verify it's actually a venv
                if (item / "pyvenv.cfg").exists() or (item / "bin" / "activate").exists() or (item / "Scripts" / "activate").exists():
                    size = _get_dir_size(item)
                    report.issues.append(Issue(
                        severity="CRITICAL",
                        category="venv",
                        description=f"Virtual environment inside project: {rel_path}",
                        path=item,
                        size_bytes=int(size * 1024 * 1024),
                        fix_action="move_venv",
                    ))
                    reported_dirs.add(item)
            continue  # Don't scan inside venv
        
        # Check for __pycache__
        if item.is_dir() and item.name == "__pycache__":
            if item not in reported_dirs:
                report.issues.append(Issue(
                    severity="WARNING",
                    category="pycache",
                    description=f"Python cache: {rel_path}",
                    path=item,
                    fix_action="delete",
                ))
                reported_dirs.add(item)
            continue  # Don't scan inside pycache
        
        # Check for node_modules
        if item.is_dir() and item.name == "node_modules":
            if item not in reported_dirs:
                size = _get_dir_size(item)
                report.issues.append(Issue(
                    severity="CRITICAL",
                    category="node_modules",
                    description=f"Node modules inside project: {rel_path} ({size:.1f}MB)",
                    path=item,
                    size_bytes=int(size * 1024 * 1024),
                    fix_action="add_to_cursorignore",
                ))
                reported_dirs.add(item)
            continue  # Don't scan inside node_modules
        
        # Check for .pytest_cache, .mypy_cache
        if item.is_dir() and item.name in {".pytest_cache", ".mypy_cache"}:
            continue  # Skip these silently
        
        # Count files (only those not in issue directories)
        if item.is_file():
            # Skip files inside issue directories
            if any(part in issue_dirs for part in rel_path.parts[:-1]):
                continue
            
            total_files += 1
            try:
                size = item.stat().st_size
                total_size += size
            except (OSError, PermissionError):
                continue
    
    report.total_files = total_files
    report.total_size_mb = total_size / (1024 * 1024)
    
    # Estimate tokens (rough: bytes / 4)
    report.total_tokens = total_size // 4
    
    # Check for .cursorignore
    cursorignore = project_path / ".cursorignore"
    if not cursorignore.exists():
        report.issues.append(Issue(
            severity="SUGGESTION",
            category="config",
            description="Missing .cursorignore file",
            fix_action="create_cursorignore",
        ))
    
    # Check for heavy files using token scanner
    try:
        from ..scanner.token_scanner import scan_project as token_scan
        
        scan_result = token_scan(
            project_path=project_path,
            threshold=1000,
            show_progress=False,
        )
        
        report.total_tokens = scan_result.total_tokens
        
        for heavy_file in scan_result.heavy_files:
            report.issues.append(Issue(
                severity="WARNING",
                category="heavy_file",
                description=f"Heavy file ({heavy_file.estimated_tokens:,} tokens): {heavy_file.path.name}",
                path=heavy_file.path,
                tokens=heavy_file.estimated_tokens,
                fix_action="move_to_external",
            ))
    except ImportError:
        pass  # Token scanner not available


def _get_dir_size(path: Path) -> float:
    """Get directory size in MB."""
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except (PermissionError, OSError):
        pass
    return total / (1024 * 1024)


# ══════════════════════════════════════════════════════════════
# FIX OPERATIONS
# ══════════════════════════════════════════════════════════════

def fix_issues(project_path: Path, report: DoctorReport, dry_run: bool = False) -> FixResult:
    """Fix issues found in report."""
    result = FixResult(success=True, message="")
    
    for issue in report.issues:
        if issue.fix_action == "move_venv":
            _fix_venv(project_path, issue, result, dry_run)
        elif issue.fix_action == "delete":
            _fix_delete(issue, result, dry_run)
        elif issue.fix_action == "add_to_cursorignore":
            _fix_cursorignore(project_path, issue, result, dry_run)
        elif issue.fix_action == "create_cursorignore":
            _create_cursorignore(project_path, result, dry_run)
    
    if result.errors:
        result.success = False
        result.message = f"Completed with {len(result.errors)} errors"
    else:
        result.message = f"Fixed {result.files_moved} issues"
    
    return result


def _fix_venv(project_path: Path, issue: Issue, result: FixResult, dry_run: bool):
    """Move venv to external storage."""
    if not issue.path:
        return
    
    external_venvs = get_external_venvs_dir(project_path)
    target = external_venvs / "main"
    
    if dry_run:
        print(f"  Would move: {issue.path} → {target}")
        return
    
    try:
        ensure_external_structure(project_path)
        if target.exists():
            # Add timestamp suffix
            target = external_venvs / f"main_{int(datetime.now().timestamp())}"
        shutil.move(str(issue.path), str(target))
        result.files_moved += 1
        print(COLORS.success(f"Moved venv → {target.relative_to(project_path.parent)}"))
    except Exception as e:
        result.errors.append(f"Failed to move venv: {e}")


def _fix_delete(issue: Issue, result: FixResult, dry_run: bool):
    """Delete directory."""
    if not issue.path:
        return
    
    if dry_run:
        print(f"  Would delete: {issue.path}")
        return
    
    try:
        shutil.rmtree(issue.path)
        result.files_moved += 1
        print(COLORS.success(f"Deleted {issue.path.name}"))
    except Exception as e:
        result.errors.append(f"Failed to delete {issue.path}: {e}")


def _fix_cursorignore(project_path: Path, issue: Issue, result: FixResult, dry_run: bool):
    """Add path to .cursorignore."""
    cursorignore = project_path / ".cursorignore"
    entry = issue.path.name if issue.path else ""
    
    if not entry:
        return
    
    if dry_run:
        print(f"  Would add to .cursorignore: {entry}")
        return
    
    try:
        existing = cursorignore.read_text() if cursorignore.exists() else ""
        if entry not in existing:
            with open(cursorignore, "a") as f:
                f.write(f"\n# Added by Fox Pro AI\n{entry}/\n")
            print(COLORS.success(f"Added {entry} to .cursorignore"))
    except Exception as e:
        result.errors.append(f"Failed to update .cursorignore: {e}")


def _create_cursorignore(project_path: Path, result: FixResult, dry_run: bool):
    """Create .cursorignore file."""
    cursorignore = project_path / ".cursorignore"
    
    if dry_run:
        print("  Would create .cursorignore")
        return
    
    content = """# 🦊 Fox Pro AI — Cursor Ignore
# Files and directories to exclude from Cursor AI context

# Virtual environments
venv/
.venv/
env/

# Dependencies
node_modules/

# Cache
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/

# Build
dist/
build/
*.egg-info/

# IDE
.idea/
.vscode/

# External storage (Fox Pro AI)
*_fox/
"""
    try:
        cursorignore.write_text(content)
        print(COLORS.success("Created .cursorignore"))
    except Exception as e:
        result.errors.append(f"Failed to create .cursorignore: {e}")


# ══════════════════════════════════════════════════════════════
# FULL OPTIMIZATION (Deep Clean)
# ══════════════════════════════════════════════════════════════

def full_optimization(project_path: Path, dry_run: bool = False) -> FixResult:
    """
    Full optimization — Deep Clean.
    
    Steps:
        1. Scan for heavy files
        2. Move to external storage
        3. Generate bridge (config_paths.py)
        4. Patch code (AST)
        5. Generate trace map
        6. Clean garbage
    """
    from ..scanner.token_scanner import scan_project as token_scan, get_moveable_files
    from ..optimizer.heavy_mover import move_heavy_files
    from ..optimizer.ast_patcher import patch_project
    from ..optimizer.garbage_cleaner import scan_garbage, clean_garbage
    from ..mapper.fox_trace_map import generate_fox_trace_map
    
    result = FixResult(success=True, message="")
    project_path = Path(project_path).resolve()
    
    print(f"\n{COLORS.BOLD}🦊 Fox Pro AI — Full Optimization{COLORS.END}\n")
    print(f"Project: {project_path.name}")
    print(f"{'─' * 50}\n")
    
    # Step 1: Scan
    print(f"{COLORS.CYAN}[1/6] Scanning project...{COLORS.END}")
    try:
        scan_result = token_scan(
            project_path=project_path,
            threshold=1000,
            show_progress=True,
        )
        print(f"  Found {len(scan_result.heavy_files)} heavy files")
        print(f"  Total tokens: {scan_result.total_tokens:,}")
    except Exception as e:
        result.errors.append(f"Scan failed: {e}")
        result.success = False
        return result
    
    # Step 2: Move
    print(f"\n{COLORS.CYAN}[2/6] Moving heavy files...{COLORS.END}")
    moveable = get_moveable_files(scan_result)
    move_result = None  # Initialize for later checks
    
    if not moveable:
        print("  No files to move")
    elif dry_run:
        for f in moveable:
            print(f"  Would move: {f.path.name} ({f.estimated_tokens:,} tokens)")
    else:
        try:
            move_result = move_heavy_files(project_path, moveable)
            result.files_moved = len(move_result.moved_files)
            result.tokens_saved = sum(f.estimated_tokens for f in move_result.moved_files)
            print(f"  ✅ Moved {result.files_moved} files")
            
            # Show symlinks created
            if move_result.symlinks_created:
                print(f"  ✅ Created {len(move_result.symlinks_created)} symlinks for dynamic paths")
        except Exception as e:
            result.errors.append(f"Move failed: {e}")
    
    # Step 3: Bridge
    print(f"\n{COLORS.CYAN}[3/6] Generating bridge...{COLORS.END}")
    if not dry_run and moveable:
        # Bridge is already generated by move_heavy_files
        # Just check if it exists
        bridge_path = project_path / "config_paths.py"
        if bridge_path.exists():
            print(f"  ✅ Created config_paths.py")
        elif move_result and move_result.config_paths_file:
            print(f"  ✅ Created config_paths.py")
        else:
            print(f"  ⚠ Bridge not created (move may have failed)")
    else:
        print("  Skipped (dry run or no files)")
    
    # Step 4: Patch
    print(f"\n{COLORS.CYAN}[4/6] Patching code...{COLORS.END}")
    if not dry_run and moveable:
        try:
            # Convert HeavyFile list to set of path strings
            moved_paths = {hf.relative_path for hf in moveable}
            
            patch_report = patch_project(project_path, moved_paths)
            result.files_patched = patch_report.files_patched
            print(f"  ✅ Patched {result.files_patched} files")
            
            if patch_report.dynamic_path_warnings:
                # Check if symlinks were created
                symlinks_ok = move_result and move_result.symlinks_created
                
                if symlinks_ok:
                    print(f"\n  {COLORS.CYAN}ℹ Dynamic paths detected — covered by symlinks:{COLORS.END}")
                else:
                    print(f"\n  {COLORS.YELLOW}⚠ Dynamic paths found (need manual fix or symlinks):{COLORS.END}")
                
                # Group by file
                by_file = {}
                for warn in patch_report.dynamic_path_warnings:
                    file_key = str(warn.file.relative_to(project_path))
                    if file_key not in by_file:
                        by_file[file_key] = []
                    by_file[file_key].append(warn)
                
                # Show first 5 files
                for file_path, warns in list(by_file.items())[:5]:
                    print(f"    📄 {file_path}")
                    for w in warns[:3]:  # Max 3 per file
                        print(f"       L{w.line}: {w.code[:60]}")
                    if len(warns) > 3:
                        print(f"       ... and {len(warns) - 3} more")
                
                if len(by_file) > 5:
                    print(f"    ... and {len(by_file) - 5} more files")
                
                # Show instruction if no symlinks
                if not symlinks_ok:
                    print(f"\n  {COLORS.CYAN}💡 Quick fix — add at top of affected files:{COLORS.END}")
                    print(f"     from config_paths import get_path")
                    print(f"     DATA = get_path(\"data\")  # or your prefix")
                    print(f"")
                    print(f"     Then replace \"data/\" with f\"{{DATA}}/\"")
        except Exception as e:
            result.errors.append(f"Patching failed: {e}")
    else:
        print("  Skipped (dry run or no files)")
    
    # Step 5: Map
    print(f"\n{COLORS.CYAN}[5/6] Generating trace map...{COLORS.END}")
    if not dry_run and move_result and move_result.moved_files:
        try:
            generate_fox_trace_map(project_path, move_result.moved_files)
            print(f"  ✅ Created AST_FOX_TRACE.md")
        except Exception as e:
            result.errors.append(f"Map generation failed: {e}")
    else:
        print("  Skipped (dry run or no moved files)")
    
    # Step 6: Garbage
    print(f"\n{COLORS.CYAN}[6/6] Cleaning garbage...{COLORS.END}")
    try:
        garbage = scan_garbage(project_path)
        if garbage:
            if dry_run:
                print(f"  Would clean {len(garbage)} garbage files")
            else:
                clean_garbage(project_path, garbage)
                print(f"  Cleaned {len(garbage)} garbage files")
        else:
            print("  No garbage found")
    except Exception as e:
        result.errors.append(f"Garbage clean failed: {e}")
    
    # Summary
    print(f"\n{'─' * 50}")
    if result.errors:
        result.success = False
        result.message = f"Completed with {len(result.errors)} errors"
        print(f"{COLORS.YELLOW}⚠ {result.message}{COLORS.END}")
        for err in result.errors:
            print(f"  • {err}")
    else:
        result.message = "Full optimization completed!"
        print(f"{COLORS.GREEN}✅ {result.message}{COLORS.END}")
        print(f"   Moved: {result.files_moved} files")
        print(f"   Patched: {result.files_patched} files")
        print(f"   Tokens saved: {result.tokens_saved:,}")
    
    return result


# ══════════════════════════════════════════════════════════════
# RESTORE
# ══════════════════════════════════════════════════════════════

def restore_files(project_path: Path, dry_run: bool = False) -> FixResult:
    """Restore files from external storage."""
    from ..optimizer.heavy_mover import restore_files as do_restore
    
    result = FixResult(success=True, message="")
    project_path = Path(project_path).resolve()
    
    if not external_exists(project_path):
        result.success = False
        result.message = "No external storage found"
        return result
    
    try:
        restore_result = do_restore(project_path, dry_run=dry_run)
        result.files_moved = restore_result.files_restored
        result.message = f"Restored {result.files_moved} files"
    except Exception as e:
        result.success = False
        result.errors.append(str(e))
        result.message = f"Restore failed: {e}"
    
    return result


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def run_doctor(
    project_path: Path,
    mode: str = "report",
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """
    Run doctor command.
    
    Args:
        project_path: Path to project
        mode: report, fix, full, restore
        dry_run: Don't make changes
        verbose: Verbose output
        
    Returns:
        Exit code (0 = success)
    """
    project_path = Path(project_path).resolve()
    
    print(f"\n{COLORS.BOLD}🩺 Fox Pro AI Doctor v{VERSION}{COLORS.END}")
    print(f"Project: {project_path.name}")
    
    if dry_run:
        print(f"{COLORS.YELLOW}(dry run — no changes will be made){COLORS.END}")
    
    print()
    
    # Restore mode
    if mode == "restore":
        result = restore_files(project_path, dry_run)
        print(result.message)
        return 0 if result.success else 1
    
    # Full optimization mode
    if mode == "full":
        result = full_optimization(project_path, dry_run)
        return 0 if result.success else 1
    
    # Diagnose
    report = diagnose(project_path, verbose)
    
    # Print report
    _print_report(report)
    
    # Fix mode
    if mode == "fix" and report.issues:
        print(f"\n{COLORS.CYAN}Fixing issues...{COLORS.END}\n")
        result = fix_issues(project_path, report, dry_run)
        print(f"\n{result.message}")
        return 0 if result.success else 1
    
    # Report mode — just show issues
    if report.critical_count > 0:
        print(f"\n💡 Run '{COLORS.CYAN}fox doctor --fix{COLORS.END}' to fix issues")
        print(f"   Or '{COLORS.CYAN}fox doctor --full{COLORS.END}' for full optimization")
    
    return 0


def _print_report(report: DoctorReport):
    """Print diagnostic report."""
    # Summary
    print(f"📊 {COLORS.BOLD}Project Summary{COLORS.END}")
    print(f"   Files: {report.total_files:,}")
    print(f"   Size: {report.total_size_mb:.1f} MB")
    print(f"   Tokens: {report.total_tokens:,}")
    
    if report.external_exists:
        print(f"\n📦 {COLORS.BOLD}External Storage{COLORS.END}")
        print(f"   Files: {report.external_files}")
        print(f"   Tokens: {report.external_tokens:,}")
    
    # Issues
    if not report.issues:
        print(f"\n{COLORS.GREEN}✅ No issues found!{COLORS.END}")
        return
    
    print(f"\n🔍 {COLORS.BOLD}Issues Found{COLORS.END}")
    print(f"   {COLORS.RED}Critical: {report.critical_count}{COLORS.END}")
    print(f"   {COLORS.YELLOW}Warning: {report.warning_count}{COLORS.END}")
    print(f"   {COLORS.CYAN}Suggestion: {report.suggestion_count}{COLORS.END}")
    
    print()
    
    # List issues by severity
    for severity, color in [("CRITICAL", COLORS.RED), ("WARNING", COLORS.YELLOW), ("SUGGESTION", COLORS.CYAN)]:
        issues = [i for i in report.issues if i.severity == severity]
        if issues:
            for issue in issues[:10]:  # Limit output
                icon = "🔴" if severity == "CRITICAL" else "🟡" if severity == "WARNING" else "💡"
                print(f"  {icon} {color}{issue.description}{COLORS.END}")
            
            if len(issues) > 10:
                print(f"     ... and {len(issues) - 10} more")
