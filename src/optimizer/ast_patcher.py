"""
AST Patcher — Automatically patch Python code to use config_paths bridges.
The most critical part of Deep Clean — modifies user code safely.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple


@dataclass
class PatchLocation:
    """Location of a patch in source code."""
    file: Path
    line: int
    col: int
    original: str          # Original code snippet
    patched: str           # Patched code snippet
    pattern_type: str      # "open", "path", "pandas", "sqlite", etc.


@dataclass
class PatchResult:
    """Result of patching a single file."""
    file: Path
    success: bool
    patches: List[PatchLocation] = field(default_factory=list)
    error: Optional[str] = None
    backup_path: Optional[Path] = None
    original_content: str = ""
    patched_content: str = ""


@dataclass
class DynamicPathWarning:
    """Warning about dynamic path that can't be auto-patched."""
    file: Path
    line: int
    code: str           # The actual code snippet
    path_prefix: str    # e.g., "data" from f"data/{user_id}"
    pattern_type: str   # "f-string", "concat", "join", "format"


@dataclass
class PatchReport:
    """Result of patching entire project."""
    project_path: Path
    files_scanned: int
    files_patched: int
    total_patches: int
    results: List[PatchResult] = field(default_factory=list)
    import_added_to: List[Path] = field(default_factory=list)
    errors: List[Tuple[Path, str]] = field(default_factory=list)
    dynamic_path_warnings: List[DynamicPathWarning] = field(default_factory=list)


class PathPatcher(ast.NodeTransformer):
    """
    AST transformer that replaces file path strings with get_path() calls.
    """
    
    def __init__(self, moved_files: Set[str]):
        self.moved_files = moved_files
        self.patches: List[PatchLocation] = []
        self.needs_import = False
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for comparison."""
        return path.replace("\\", "/").strip("./")
    
    def _is_moved_file(self, path: str) -> bool:
        """Check if path refers to a moved file."""
        normalized = self._normalize_path(path)
        # Check exact match or if any moved file matches
        for moved in self.moved_files:
            if normalized == self._normalize_path(moved) or normalized.endswith(moved):
                return True
        return False
    
    def _create_get_path_call(self, path: str) -> ast.Call:
        """Create AST node for get_path("path") call."""
        normalized = self._normalize_path(path)
        return ast.Call(
            func=ast.Name(id='get_path', ctx=ast.Load()),
            args=[ast.Constant(value=normalized)],
            keywords=[]
        )
    
    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Visit function/method calls and patch file paths."""
        self.generic_visit(node)  # Process children first
        
        # Check for open() calls
        if isinstance(node.func, ast.Name) and node.func.id == 'open':
            if node.args and isinstance(node.args[0], ast.Constant):
                path = node.args[0].value
                if isinstance(path, str) and self._is_moved_file(path):
                    # Replace first argument with get_path() call
                    node.args[0] = self._create_get_path_call(path)
                    self.needs_import = True
                    normalized = self._normalize_path(path)
                    self.patches.append(PatchLocation(
                        file=Path(),  # Set later
                        line=node.lineno,
                        col=node.col_offset,
                        original=f'open("{path}"',
                        patched=f'open(get_path("{normalized}"',
                        pattern_type="open"
                    ))
        
        # Check for Path() calls
        elif isinstance(node.func, ast.Name) and node.func.id == 'Path':
            if node.args and isinstance(node.args[0], ast.Constant):
                path = node.args[0].value
                if isinstance(path, str) and self._is_moved_file(path):
                    # Replace entire Path() with get_path()
                    new_node = self._create_get_path_call(path)
                    self.needs_import = True
                    normalized = self._normalize_path(path)
                    self.patches.append(PatchLocation(
                        file=Path(),
                        line=node.lineno,
                        col=node.col_offset,
                        original=f'Path("{path}")',
                        patched=f'get_path("{normalized}")',
                        pattern_type="path"
                    ))
                    return new_node
        
        # Check for method calls (pd.read_csv, sqlite3.connect, etc.)
        elif isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            
            # pandas read methods
            if method_name in ["read_csv", "read_json", "read_excel", "read_parquet", "read_pickle"]:
                if node.args and isinstance(node.args[0], ast.Constant):
                    path = node.args[0].value
                    if isinstance(path, str) and self._is_moved_file(path):
                        node.args[0] = self._create_get_path_call(path)
                        self.needs_import = True
                        normalized = self._normalize_path(path)
                        self.patches.append(PatchLocation(
                            file=Path(),
                            line=node.lineno,
                            col=node.col_offset,
                            original=f'{method_name}("{path}")',
                            patched=f'{method_name}(get_path("{normalized}"))',
                            pattern_type="pandas"
                        ))
            
            # sqlite3.connect
            elif method_name == "connect":
                if node.args and isinstance(node.args[0], ast.Constant):
                    path = node.args[0].value
                    if isinstance(path, str) and self._is_moved_file(path):
                        node.args[0] = self._create_get_path_call(path)
                        self.needs_import = True
                        normalized = self._normalize_path(path)
                        self.patches.append(PatchLocation(
                            file=Path(),
                            line=node.lineno,
                            col=node.col_offset,
                            original=f'connect("{path}")',
                            patched=f'connect(get_path("{normalized}"))',
                            pattern_type="sqlite"
                        ))
        
        return node


def _apply_patches_to_source(source: str, patches: List[PatchLocation]) -> str:
    """
    Apply patches to source code while preserving formatting.
    
    Instead of using ast.unparse() which loses formatting,
    we do string replacement at specific locations.
    """
    lines = source.split('\n')
    
    # Sort patches by line (descending) to apply from bottom up
    # This prevents line number shifts from affecting later patches
    sorted_patches = sorted(patches, key=lambda p: (p.line, p.col), reverse=True)
    
    for patch in sorted_patches:
        line_idx = patch.line - 1  # Convert to 0-indexed
        if 0 <= line_idx < len(lines):
            line = lines[line_idx]
            # Find and replace the original pattern
            lines[line_idx] = _patch_line(line, patch)
    
    return '\n'.join(lines)


def _patch_line(line: str, patch: PatchLocation) -> str:
    """Patch a single line based on pattern type."""
    if patch.pattern_type == "open":
        # Match open("path") or open('path')
        # Extract the path from original
        try:
            path_match = re.search(r'["\']([^"\']+)["\']', patch.original)
            if path_match:
                original_path = path_match.group(1)
                # Find the path string and replace it with get_path() call
                # Match the quoted path string
                pattern = rf'["\']{re.escape(original_path)}["\']'
                normalized = patch.patched.split('"')[1]
                replacement = f'get_path("{normalized}")'
                return re.sub(pattern, replacement, line, count=1)
        except Exception:
            pass
    
    elif patch.pattern_type == "path":
        # Match Path("path") or Path('path')
        try:
            path_match = re.search(r'["\']([^"\']+)["\']', patch.original)
            if path_match:
                original_path = path_match.group(1)
                # Match Path("path") and replace entire call
                pattern = rf'Path\s*\(\s*["\']{re.escape(original_path)}["\']\s*\)'
                normalized = patch.patched.split('"')[1]
                replacement = f'get_path("{normalized}")'
                return re.sub(pattern, replacement, line, count=1)
        except Exception:
            pass
    
    elif patch.pattern_type in ["pandas", "sqlite"]:
        # Match method("path")
        try:
            path_match = re.search(r'["\']([^"\']+)["\']', patch.original)
            if path_match:
                original_path = path_match.group(1)
                # Find the path string and wrap it
                pattern = rf'["\']{re.escape(original_path)}["\']'
                normalized = patch.patched.split('"')[1]
                replacement = f'get_path("{normalized}")'
                return re.sub(pattern, replacement, line, count=1)
        except Exception:
            pass
    
    return line


def add_import_statement(source: str) -> str:
    """
    Add 'from config_paths import get_path' if not present.
    
    Rules:
    - Add after other imports
    - Don't duplicate if already exists
    - Preserve file structure
    """
    import_line = "from config_paths import get_path"
    
    # Check if already imported
    if import_line in source or "from config_paths import" in source:
        return source
    
    lines = source.split('\n')
    
    # Find the best place to insert import
    # After other imports, before code
    insert_idx = 0
    in_docstring = False
    docstring_char = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Handle module docstrings
        if i == 0 and (stripped.startswith('"""') or stripped.startswith("'''")):
            docstring_char = stripped[:3]
            in_docstring = True
            if stripped.count(docstring_char) >= 2:
                in_docstring = False
            continue
        
        if in_docstring:
            if docstring_char in stripped:
                in_docstring = False
            continue
        
        # Track imports
        if stripped.startswith("import ") or stripped.startswith("from "):
            insert_idx = i + 1
        elif stripped and not stripped.startswith("#"):
            # First non-import, non-comment, non-empty line
            break
    
    # Insert import
    lines.insert(insert_idx, import_line)
    
    return '\n'.join(lines)


def patch_file(
    file_path: Path,
    moved_files: Set[str],
    dry_run: bool = False,
    create_backup: bool = True
) -> PatchResult:
    """
    Patch a single Python file to use config_paths.
    
    Process:
    1. Read file
    2. Parse AST (validate syntax)
    3. Find all path references
    4. Filter to only moved files
    5. Generate patched source
    6. Validate patched syntax
    7. Add import if needed
    8. Write file (unless dry_run)
    
    Args:
        file_path: Path to Python file
        moved_files: Set of file paths that were moved
        dry_run: If True, don't write changes
        create_backup: If True, create .bak file
    
    Returns:
        PatchResult with all changes made
    """
    result = PatchResult(file=file_path, success=False)
    
    try:
        # Read original content
        result.original_content = file_path.read_text(encoding="utf-8")
        
        # Parse AST to validate syntax
        try:
            tree = ast.parse(result.original_content)
        except SyntaxError as e:
            result.error = f"Syntax error in original: {e}"
            return result
        
        # Apply transformer
        patcher = PathPatcher(moved_files)
        new_tree = patcher.visit(tree)
        
        # If no patches, return early
        if not patcher.patches:
            result.success = True
            result.patched_content = result.original_content
            return result
        
        # Fix missing line numbers
        ast.fix_missing_locations(new_tree)
        
        # Generate new source
        # Note: ast.unparse() loses formatting, so we use a different approach
        result.patched_content = _apply_patches_to_source(
            result.original_content,
            patcher.patches
        )
        
        # Add import if needed
        if patcher.needs_import:
            result.patched_content = add_import_statement(result.patched_content)
        
        # Validate new syntax
        try:
            ast.parse(result.patched_content)
        except SyntaxError as e:
            result.error = f"Syntax error after patching: {e}"
            return result
        
        # Update patches with file path
        for patch in patcher.patches:
            patch.file = file_path
        result.patches = patcher.patches
        
        # Write changes (unless dry_run)
        if not dry_run:
            # Create backup
            if create_backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                backup_path.write_text(result.original_content, encoding="utf-8")
                result.backup_path = backup_path
            
            # Write patched content
            file_path.write_text(result.patched_content, encoding="utf-8")
        
        result.success = True
        
    except Exception as e:
        result.error = str(e)
    
    return result


def patch_project(
    project_path: Path,
    moved_files: Set[str],
    dry_run: bool = False,
    exclude_patterns: Optional[List[str]] = None
) -> PatchReport:
    """
    Patch all Python files in project.
    
    Args:
        project_path: Project root
        moved_files: Set of file paths that were moved
        dry_run: If True, don't write changes
        exclude_patterns: Glob patterns to exclude (e.g., ["test_*.py"])
    
    Returns:
        PatchReport with all changes
    """
    project_path = project_path.resolve()
    exclude_patterns = exclude_patterns or []
    
    # Default excludes
    default_excludes = [
        "config_paths.py",  # Don't patch our own bridge!
        "test_*.py",        # Don't patch tests by default
        "*_test.py",
        "conftest.py",
        "setup.py",
    ]
    exclude_patterns.extend(default_excludes)
    
    report = PatchReport(
        project_path=project_path,
        files_scanned=0,
        files_patched=0,
        total_patches=0
    )
    
    # Find all Python files
    for py_file in project_path.rglob("*.py"):
        # Skip excluded patterns
        if any(py_file.match(pattern) for pattern in exclude_patterns):
            continue
        
        # Skip venv, __pycache__, etc.
        if any(part in py_file.parts for part in ["venv", ".venv", "__pycache__", "node_modules", ".git"]):
            continue
        
        report.files_scanned += 1
        
        try:
            result = patch_file(py_file, moved_files, dry_run=dry_run)
            report.results.append(result)
            
            if result.patches:
                report.files_patched += 1
                report.total_patches += len(result.patches)
                if result.patched_content and "from config_paths import" in result.patched_content:
                    report.import_added_to.append(py_file)
            
            if result.error:
                report.errors.append((py_file, result.error))
                
        except Exception as e:
            report.errors.append((py_file, str(e)))
    
    # Detect dynamic paths that can't be auto-patched
    report.dynamic_path_warnings = detect_dynamic_paths(project_path, moved_files)
    
    return report


def detect_dynamic_paths(
    project_path: Path,
    moved_files: Set[str]
) -> List[DynamicPathWarning]:
    """
    Detect dynamic paths that can't be automatically patched.
    
    Looks for patterns like:
    - f"data/{user_id}.json"
    - "data/" + filename
    - os.path.join("data", name)
    - "data/{}".format(var)
    
    Args:
        project_path: Project root
        moved_files: Set of moved file paths
        
    Returns:
        List of DynamicPathWarning
    """
    warnings = []
    
    # Extract unique prefixes from moved files (e.g., "data" from "data/users.json")
    moved_prefixes = set()
    for mf in moved_files:
        parts = Path(mf).parts
        if parts:
            moved_prefixes.add(parts[0])
    
    if not moved_prefixes:
        return warnings
    
    # Build regex patterns for each prefix
    # Escape special characters in prefixes
    prefix_pattern = "|".join(re.escape(p) for p in moved_prefixes)
    
    patterns = [
        # f-strings: f"data/{var}" or f"data/{user_id}.json"
        (rf'f["\']({prefix_pattern})/\{{[^}}]+\}}', "f-string"),
        
        # Concatenation: "data/" + var or "data/" + str(var)
        (rf'["\']({prefix_pattern})/["\']\s*\+', "concat"),
        
        # os.path.join: os.path.join("data", var)
        (rf'os\.path\.join\s*\(\s*["\']({prefix_pattern})["\']', "join"),
        
        # Path concatenation: Path("data") / var
        (rf'Path\s*\(\s*["\']({prefix_pattern})["\']\s*\)\s*/', "path-concat"),
        
        # .format(): "data/{}.json".format(var)
        (rf'["\']({prefix_pattern})/[^"\']*\{{\}}[^"\']*["\']\.format', "format"),
    ]
    
    # Scan Python files
    for py_file in project_path.rglob("*.py"):
        # Skip venv, __pycache__, etc.
        if any(part in py_file.parts for part in ["venv", ".venv", "__pycache__", "node_modules", ".git"]):
            continue
        
        # Skip config_paths.py
        if py_file.name == "config_paths.py":
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                for pattern, pattern_type in patterns:
                    match = re.search(pattern, line)
                    if match:
                        # Extract the prefix that matched
                        path_prefix = match.group(1) if match.groups() else ""
                        
                        warnings.append(DynamicPathWarning(
                            file=py_file,
                            line=line_num,
                            code=line.strip()[:80],  # Truncate long lines
                            path_prefix=path_prefix,
                            pattern_type=pattern_type
                        ))
                        break  # One warning per line
                        
        except Exception:
            continue
    
    return warnings


def format_patch_report(report: PatchReport) -> str:
    """Format patch report."""
    lines = []
    
    lines.append("╔══════════════════════════════════════════════════════════════════╗")
    lines.append("║  🔧 AST PATCHER — Code Refactoring Report                        ║")
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    lines.append(f"║  Project: {report.project_path.name:<55}║")
    lines.append(f"║  Files Scanned: {report.files_scanned:<49}║")
    lines.append(f"║  Files Patched: {report.files_patched:<49}║")
    lines.append(f"║  Total Patches: {report.total_patches:<49}║")
    
    if report.results:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append("║  PATCHES APPLIED:                                                ║")
        
        for result in report.results:
            if result.patches:
                rel_path = result.file.relative_to(report.project_path)
                path_str = str(rel_path)[:60]
                lines.append(f"║  📄 {path_str:<60}║")
                for patch in result.patches[:5]:
                    orig_short = patch.original[:40]
                    patched_short = patch.patched[:40]
                    lines.append(f"║     L{patch.line}: {orig_short:<43}║")
                    lines.append(f"║        → {patched_short:<43}║")
                if len(result.patches) > 5:
                    lines.append(f"║     ... and {len(result.patches) - 5} more patches{' '*35}║")
    
    if report.errors:
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  ⚠️  ERRORS ({len(report.errors)}):{' '*50}║")
        for path, error in report.errors[:5]:
            path_short = path.name[:30]
            error_short = error[:45]
            lines.append(f"║  {path_short:<30}: {error_short:<47}║")
    
    lines.append("╠══════════════════════════════════════════════════════════════════╣")
    lines.append("║  💡 Backup files created: *.py.bak                               ║")
    lines.append("║  💡 Revert: toolkit doctor --revert-patches                      ║")
    lines.append("╚══════════════════════════════════════════════════════════════════╝")
    
    return "\n".join(lines)


def revert_patches(project_path: Path) -> int:
    """
    Revert patches by restoring .bak files.
    
    Returns:
        Number of files reverted
    """
    reverted = 0
    
    for bak_file in project_path.rglob("*.py.bak"):
        original = bak_file.with_suffix("")  # Remove .bak
        if original.suffix == ".py":
            # Restore original
            original.write_text(bak_file.read_text(encoding="utf-8"), encoding="utf-8")
            bak_file.unlink()
            reverted += 1
    
    return reverted

