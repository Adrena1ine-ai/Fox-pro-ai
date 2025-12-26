"""
🧠 Context Map Generator — AST-based project mapping
Replaces regex with Python's ast module for accurate code analysis
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from dataclasses import dataclass, field

from .metrics import parse_cursorignore, should_ignore


# Directories to always exclude
EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "_AI_ARCHIVE", ".pytest_cache"}

# Extensions to parse
PARSEABLE_EXTENSIONS = {".py"}


@dataclass
class FunctionInfo:
    """Information about a function"""
    name: str
    args: list[str] = field(default_factory=list)
    returns: str | None = None
    is_async: bool = False
    docstring: str | None = None


@dataclass
class ClassInfo:
    """Information about a class"""
    name: str
    bases: list[str] = field(default_factory=list)
    docstring: str | None = None
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """Information about a module"""
    path: Path
    docstring: str | None = None
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    has_error: bool = False
    error_message: str | None = None


def extract_docstring(node: ast.AST) -> str | None:
    """Extract first line of docstring from a node"""
    docstring = ast.get_docstring(node)
    if docstring:
        first_line = docstring.split('\n')[0].strip()
        return first_line[:80] + "..." if len(first_line) > 80 else first_line
    return None


def extract_function_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
    """Extract function information from AST node"""
    # Get argument names
    args = []
    for arg in node.args.args:
        args.append(arg.arg)
    
    # Get return annotation
    returns = None
    if node.returns:
        try:
            returns = ast.unparse(node.returns)
        except Exception:
            returns = "..."
    
    return FunctionInfo(
        name=node.name,
        args=args,
        returns=returns,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        docstring=extract_docstring(node)
    )


def extract_class_info(node: ast.ClassDef) -> ClassInfo:
    """Extract class information from AST node"""
    # Get base classes
    bases = []
    for base in node.bases:
        try:
            bases.append(ast.unparse(base))
        except Exception:
            bases.append("...")
    
    # Get methods
    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(extract_function_info(item))
    
    return ClassInfo(
        name=node.name,
        bases=bases,
        docstring=extract_docstring(node),
        methods=methods
    )


def parse_python_file(file_path: Path) -> ModuleInfo:
    """
    Parse a Python file and extract structure using AST
    
    Args:
        file_path: Path to Python file
        
    Returns:
        ModuleInfo with extracted information
    """
    module = ModuleInfo(path=file_path)
    
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(file_path))
        
        # Module docstring
        module.docstring = extract_docstring(tree)
        
        # Walk top-level nodes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                module.classes.append(extract_class_info(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                module.functions.append(extract_function_info(node))
        
    except SyntaxError as e:
        module.has_error = True
        module.error_message = f"SyntaxError: {e.msg} at line {e.lineno}"
    except Exception as e:
        module.has_error = True
        module.error_message = str(e)
    
    return module


def format_function(func: FunctionInfo, indent: int = 0) -> str:
    """Format function info as markdown"""
    prefix = "  " * indent
    async_prefix = "async " if func.is_async else ""
    args_str = ", ".join(func.args[:3])
    if len(func.args) > 3:
        args_str += ", ..."
    
    returns_str = f" → {func.returns}" if func.returns else ""
    line = f"{prefix}  ƒ `{async_prefix}{func.name}({args_str}){returns_str}`"
    
    if func.docstring:
        line += f" — {func.docstring}"
    
    return line


def format_class(cls: ClassInfo, indent: int = 0) -> list[str]:
    """Format class info as markdown lines"""
    prefix = "  " * indent
    bases_str = f"({', '.join(cls.bases)})" if cls.bases else ""
    
    lines = []
    line = f"{prefix}  📦 `{cls.name}{bases_str}`"
    if cls.docstring:
        line += f" — {cls.docstring}"
    lines.append(line)
    
    # Add methods (limit to first 5)
    for method in cls.methods[:5]:
        if not method.name.startswith("_") or method.name in ("__init__", "__call__"):
            lines.append(format_function(method, indent + 1))
    
    if len(cls.methods) > 5:
        lines.append(f"{prefix}    ... +{len(cls.methods) - 5} more methods")
    
    return lines


def generate_map(root_path: Path) -> str:
    """
    Generate project context map using AST analysis
    
    Args:
        root_path: Path to project root
        
    Returns:
        Markdown formatted context map
    """
    root_path = Path(root_path).resolve()
    
    # Parse ignore patterns
    ignore_patterns = parse_cursorignore(root_path)
    
    # Output lines
    lines = [
        "# 🗺️ PROJECT CONTEXT MAP",
        "",
        "> Auto-generated using AST analysis. AI: Read this to understand code structure.",
        ""
    ]
    
    total_files = 0
    total_classes = 0
    total_functions = 0
    errors = 0
    
    # Walk directory
    for dirpath, dirnames, filenames in os.walk(root_path):
        current = Path(dirpath)
        
        # Filter directories
        dirnames[:] = [
            d for d in dirnames 
            if d not in EXCLUDE_DIRS
            and not (ignore_patterns and should_ignore(current / d, root_path, ignore_patterns))
        ]
        dirnames.sort()
        
        # Process files
        for filename in sorted(filenames):
            file_path = current / filename
            
            # Skip ignored files
            if ignore_patterns and should_ignore(file_path, root_path, ignore_patterns):
                continue
            
            rel_path = file_path.relative_to(root_path)
            
            # Add all files to map
            total_files += 1
            lines.append(f"- `{rel_path}`")
            
            # Parse Python files
            if file_path.suffix in PARSEABLE_EXTENSIONS:
                module = parse_python_file(file_path)
                
                if module.has_error:
                    errors += 1
                    lines.append(f"  ⚠️ {module.error_message}")
                    continue
                
                # Add classes
                for cls in module.classes:
                    total_classes += 1
                    lines.extend(format_class(cls))
                
                # Add top-level functions
                for func in module.functions:
                    total_functions += 1
                    lines.append(format_function(func))
        
        lines.append("")  # Empty line between directories
    
    # Statistics
    lines.append("---")
    lines.append(f"**Stats:** {total_files} files | {total_classes} classes | {total_functions} functions")
    if errors > 0:
        lines.append(f"**Warnings:** {errors} files with syntax errors (skipped)")
    
    # Estimate tokens
    content = "\n".join(lines)
    tokens = len(content) // 4
    lines.append(f"**Map size:** ~{tokens} tokens")
    
    return "\n".join(lines)


def write_context_map(root_path: Path, output_file: str = "CURRENT_CONTEXT_MAP.md") -> bool:
    """
    Generate and write context map to file
    
    Args:
        root_path: Path to project root
        output_file: Output filename
        
    Returns:
        True if successful
    """
    try:
        content = generate_map(root_path)
        output_path = Path(root_path) / output_file
        output_path.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False

