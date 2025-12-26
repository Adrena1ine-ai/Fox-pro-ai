"""
🦊 Fox Pro AI — AST Skeleton Generator

Generates compact code skeletons from Python files.
Preserves structure, signatures, docstrings — removes implementation.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
from datetime import datetime


@dataclass
class FunctionSkeleton:
    """Skeleton of a function/method."""
    name: str
    args: str                      # "(self, user_id: int, amount: float = 0)"
    returns: Optional[str]         # "-> bool" or None
    docstring: Optional[str]       # First line only
    decorators: List[str]          # ["@staticmethod", "@property"]
    is_async: bool = False
    line_number: int = 0


@dataclass  
class ClassSkeleton:
    """Skeleton of a class."""
    name: str
    bases: List[str]               # ["BaseHandler", "Mixin"]
    docstring: Optional[str]
    methods: List[FunctionSkeleton] = field(default_factory=list)
    class_variables: List[str] = field(default_factory=list)  # ["MAX_RETRIES = 3"]
    line_number: int = 0


@dataclass
class FileSkeleton:
    """Skeleton of a Python file."""
    path: Path
    relative_path: str
    original_tokens: int
    skeleton_tokens: int
    
    imports: List[str] = field(default_factory=list)          # ["from typing import List"]
    constants: List[str] = field(default_factory=list)        # ["API_URL = ..."]
    classes: List[ClassSkeleton] = field(default_factory=list)
    functions: List[FunctionSkeleton] = field(default_factory=list)
    
    # Dependencies
    imports_from: Set[str] = field(default_factory=set)       # {"database", "config"}
    used_by: Set[str] = field(default_factory=set)            # Files that import this


@dataclass
class ProjectSkeleton:
    """Skeleton of entire project."""
    project_path: Path
    project_name: str
    files: List[FileSkeleton] = field(default_factory=list)
    total_original_tokens: int = 0
    total_skeleton_tokens: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def reduction_percent(self) -> int:
        if self.total_original_tokens == 0:
            return 0
        return int((1 - self.total_skeleton_tokens / self.total_original_tokens) * 100)


def extract_skeleton(file_path: Path, project_path: Path) -> Optional[FileSkeleton]:
    """
    Extract skeleton from a Python file using AST.
    
    Args:
        file_path: Path to .py file
        project_path: Project root for relative paths
        
    Returns:
        FileSkeleton or None if parsing fails
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError) as e:
        return None
    
    # Estimate tokens (rough: chars / 4)
    original_tokens = len(content) // 4
    
    skeleton = FileSkeleton(
        path=file_path,
        relative_path=str(file_path.relative_to(project_path)),
        original_tokens=original_tokens,
        skeleton_tokens=0  # Calculate later
    )
    
    for node in ast.walk(tree):
        # We'll process top-level nodes only
        pass
    
    # Process top-level nodes
    for node in ast.iter_child_nodes(tree):
        # Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                skeleton.imports.append(f"import {alias.name}")
                skeleton.imports_from.add(alias.name.split('.')[0])
                
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = ', '.join(a.name for a in node.names)
            skeleton.imports.append(f"from {module} import {names}")
            if module:
                skeleton.imports_from.add(module.split('.')[0])
        
        # Constants (top-level assignments with UPPER_CASE names)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    skeleton.constants.append(f"{target.id} = ...")
        
        # Classes
        elif isinstance(node, ast.ClassDef):
            class_skel = _extract_class(node)
            skeleton.classes.append(class_skel)
        
        # Top-level functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_skel = _extract_function(node)
            skeleton.functions.append(func_skel)
    
    # Calculate skeleton tokens
    skeleton.skeleton_tokens = _estimate_skeleton_tokens(skeleton)
    
    return skeleton


def _extract_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionSkeleton:
    """Extract function skeleton."""
    # Arguments
    args_parts = []
    
    # Regular args
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            try:
                arg_str += f": {ast.unparse(arg.annotation)}"
            except (AttributeError, ValueError):
                # Fallback for older Python or complex annotations
                arg_str += ": ..."
        args_parts.append(arg_str)
    
    # Default values (simplified)
    if node.args.defaults:
        # Match defaults to args (from the end)
        num_defaults = len(node.args.defaults)
        num_args = len(node.args.args)
        for i, default in enumerate(node.args.defaults):
            arg_idx = num_args - num_defaults + i
            if arg_idx < len(args_parts):
                try:
                    default_str = ast.unparse(default)
                    if len(default_str) > 20:
                        default_str = "..."
                    args_parts[arg_idx] += f" = {default_str}"
                except (AttributeError, ValueError):
                    pass
    
    # *args
    if node.args.vararg:
        args_parts.append(f"*{node.args.vararg.arg}")
    
    # **kwargs  
    if node.args.kwarg:
        args_parts.append(f"**{node.args.kwarg.arg}")
    
    args_str = f"({', '.join(args_parts)})"
    
    # Return type
    returns = None
    if node.returns:
        try:
            returns = f"-> {ast.unparse(node.returns)}"
        except (AttributeError, ValueError):
            returns = "-> ..."
    
    # Docstring (first line only)
    docstring = None
    if (node.body and isinstance(node.body[0], ast.Expr) and 
        isinstance(node.body[0].value, ast.Constant) and
        isinstance(node.body[0].value.value, str)):
        doc = node.body[0].value.value.strip()
        docstring = doc.split('\n')[0][:100]  # First line, max 100 chars
    elif (node.body and isinstance(node.body[0], ast.Expr) and
          isinstance(node.body[0].value, ast.Str)):  # Python < 3.8
        doc = node.body[0].value.s.strip()
        docstring = doc.split('\n')[0][:100]
    
    # Decorators
    decorators = []
    for d in node.decorator_list:
        try:
            decorators.append(f"@{ast.unparse(d)}")
        except (AttributeError, ValueError):
            decorators.append("@...")
    
    return FunctionSkeleton(
        name=node.name,
        args=args_str,
        returns=returns,
        docstring=docstring,
        decorators=decorators,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        line_number=node.lineno
    )


def _extract_class(node: ast.ClassDef) -> ClassSkeleton:
    """Extract class skeleton."""
    # Base classes
    bases = []
    for b in node.bases:
        try:
            bases.append(ast.unparse(b))
        except (AttributeError, ValueError):
            bases.append("...")
    
    # Docstring
    docstring = None
    if (node.body and isinstance(node.body[0], ast.Expr) and
        isinstance(node.body[0].value, ast.Constant) and
        isinstance(node.body[0].value.value, str)):
        doc = node.body[0].value.value.strip()
        docstring = doc.split('\n')[0][:100]
    elif (node.body and isinstance(node.body[0], ast.Expr) and
          isinstance(node.body[0].value, ast.Str)):  # Python < 3.8
        doc = node.body[0].value.s.strip()
        docstring = doc.split('\n')[0][:100]
    
    # Methods and class variables
    methods = []
    class_vars = []
    
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_extract_function(item))
        elif isinstance(item, ast.Assign):
            # Class variables
            for target in item.targets:
                if isinstance(target, ast.Name):
                    class_vars.append(f"{target.id} = ...")
    
    return ClassSkeleton(
        name=node.name,
        bases=bases,
        docstring=docstring,
        methods=methods,
        class_variables=class_vars,
        line_number=node.lineno
    )


def _estimate_skeleton_tokens(skeleton: FileSkeleton) -> int:
    """Estimate tokens in skeleton representation."""
    tokens = 0
    
    # Imports: ~5 tokens each
    tokens += len(skeleton.imports) * 5
    
    # Constants: ~3 tokens each
    tokens += len(skeleton.constants) * 3
    
    # Functions: ~15 tokens each (name + args + return + docstring)
    tokens += len(skeleton.functions) * 15
    
    # Classes: ~20 + methods
    for cls in skeleton.classes:
        tokens += 20
        tokens += len(cls.methods) * 12
        tokens += len(cls.class_variables) * 3
    
    return tokens


def generate_project_skeleton(
    project_path: Path,
    min_tokens: int = 500,
    show_progress: bool = True
) -> ProjectSkeleton:
    """
    Generate skeleton for entire project.
    
    Args:
        project_path: Project root
        min_tokens: Only include files with > min_tokens
        show_progress: Show progress during scan
        
    Returns:
        ProjectSkeleton
    """
    project_path = project_path.resolve()
    
    skeleton = ProjectSkeleton(
        project_path=project_path,
        project_name=project_path.name
    )
    
    # Find all .py files
    py_files = []
    skip_dirs = {'venv', '.venv', 'env', '__pycache__', 'node_modules', '.git', '.tox', 'dist', 'build', '_fox', '_venvs', '_data'}
    
    for py_file in project_path.rglob('*.py'):
        if any(skip in py_file.parts for skip in skip_dirs):
            continue
        py_files.append(py_file)
    
    total = len(py_files)
    
    for idx, py_file in enumerate(py_files, 1):
        if show_progress and idx % 10 == 0:
            print(f"   Processing {idx}/{total}...", end='\r', flush=True)
        
        file_skel = extract_skeleton(py_file, project_path)
        if file_skel and file_skel.original_tokens >= min_tokens:
            skeleton.files.append(file_skel)
            skeleton.total_original_tokens += file_skel.original_tokens
            skeleton.total_skeleton_tokens += file_skel.skeleton_tokens
    
    if show_progress:
        print(f"   Processed {total} files" + " " * 20)
    
    # Sort by original tokens (largest first)
    skeleton.files.sort(key=lambda f: f.original_tokens, reverse=True)
    
    return skeleton


def skeleton_to_markdown(skeleton: ProjectSkeleton) -> str:
    """
    Convert project skeleton to Markdown format.
    
    Output format optimized for AI consumption.
    """
    lines = []
    
    # Header
    lines.append(f"# 🦊 AST Code Map: {skeleton.project_name}")
    lines.append("")
    lines.append(f"Generated: {skeleton.generated_at}")
    lines.append(f"Files: {len(skeleton.files)}")
    lines.append(f"Original: {skeleton.total_original_tokens:,} tokens")
    lines.append(f"Skeleton: {skeleton.total_skeleton_tokens:,} tokens")
    lines.append(f"**Reduction: {skeleton.reduction_percent}%**")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Table of contents
    lines.append("## 📁 Files")
    lines.append("")
    for f in skeleton.files:
        tokens_str = f"{f.original_tokens/1000:.1f}K" if f.original_tokens >= 1000 else str(f.original_tokens)
        lines.append(f"- `{f.relative_path}` ({tokens_str} → {f.skeleton_tokens} tokens)")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Each file
    for file_skel in skeleton.files:
        lines.append(f"## 📄 {file_skel.relative_path}")
        lines.append("")
        lines.append(f"Original: {file_skel.original_tokens:,} tokens → Skeleton: {file_skel.skeleton_tokens} tokens")
        lines.append("")
        
        # Imports
        if file_skel.imports:
            lines.append("### Imports")
            lines.append("```python")
            for imp in file_skel.imports[:15]:  # Max 15 imports
                lines.append(imp)
            if len(file_skel.imports) > 15:
                lines.append(f"# ... and {len(file_skel.imports) - 15} more")
            lines.append("```")
            lines.append("")
        
        # Constants
        if file_skel.constants:
            lines.append("### Constants")
            lines.append("```python")
            for const in file_skel.constants:
                lines.append(const)
            lines.append("```")
            lines.append("")
        
        # Classes
        for cls in file_skel.classes:
            bases_str = f"({', '.join(cls.bases)})" if cls.bases else ""
            lines.append(f"### class {cls.name}{bases_str}")
            if cls.docstring:
                lines.append(f"> {cls.docstring}")
            lines.append("")
            
            if cls.class_variables:
                lines.append("**Class variables:**")
                for cv in cls.class_variables:
                    lines.append(f"- `{cv}`")
                lines.append("")
            
            if cls.methods:
                lines.append("**Methods:**")
                lines.append("```python")
                for method in cls.methods:
                    prefix = "async " if method.is_async else ""
                    ret = f" {method.returns}" if method.returns else ""
                    for dec in method.decorators:
                        lines.append(dec)
                    lines.append(f"{prefix}def {method.name}{method.args}{ret}")
                    if method.docstring:
                        lines.append(f'    """{method.docstring}"""')
                lines.append("```")
                lines.append("")
        
        # Top-level functions
        if file_skel.functions:
            lines.append("### Functions")
            lines.append("```python")
            for func in file_skel.functions:
                prefix = "async " if func.is_async else ""
                ret = f" {func.returns}" if func.returns else ""
                for dec in func.decorators:
                    lines.append(dec)
                lines.append(f"{prefix}def {func.name}{func.args}{ret}")
                if func.docstring:
                    lines.append(f'    """{func.docstring}"""')
                lines.append("")
            lines.append("```")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def generate_ast_code_map(project_path: Path, output_path: Path = None) -> Tuple[Path, ProjectSkeleton]:
    """
    Main entry point: generate AST_CODE_MAP.md for project.
    
    Args:
        project_path: Project root
        output_path: Where to save (default: project_path/AST_CODE_MAP.md)
        
    Returns:
        Tuple of (Path to generated file, ProjectSkeleton)
    """
    if output_path is None:
        output_path = project_path / "AST_CODE_MAP.md"
    
    print(f"  Generating AST skeleton...")
    skeleton = generate_project_skeleton(project_path, min_tokens=500)
    
    print(f"  Writing AST_CODE_MAP.md...")
    markdown = skeleton_to_markdown(skeleton)
    output_path.write_text(markdown, encoding='utf-8')
    
    return output_path, skeleton

