"""
Fox Trace Map Generator — Create navigation map for AI assistants.
Generates AST_FOX_TRACE.md that describes moved files without their data.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..optimizer.heavy_mover import MovedFile
from ..scanner.token_scanner import FileCategory
from .schema_extractor import schema_to_markdown


@dataclass
class FileUsage:
    """Where a moved file is used in the codebase."""
    file: Path              # Python file that uses it
    line: int               # Line number
    context: str            # Code snippet showing usage
    usage_type: str         # "read", "write", "connect", etc.


@dataclass
class TracedFile:
    """Complete trace information for a moved file."""
    original_path: str
    external_path: str
    category: str
    estimated_tokens: int
    schema: Optional[Dict[str, Any]] = None
    schema_markdown: str = ""
    usages: List[FileUsage] = field(default_factory=list)
    description: str = ""


@dataclass  
class FoxTraceMap:
    """Complete navigation map for project."""
    project_name: str
    generated_at: str
    total_moved_files: int
    total_tokens_saved: int
    traced_files: List[TracedFile] = field(default_factory=list)


def _detect_usage_type(line: str) -> str:
    """Detect how a file is being used."""
    line_lower = line.lower()
    
    if "read_csv" in line_lower or "read_json" in line_lower or "read_excel" in line_lower:
        return "read (pandas)"
    elif "to_csv" in line_lower or "to_json" in line_lower or "to_excel" in line_lower:
        return "write (pandas)"
    elif "json.load" in line_lower:
        return "read (json)"
    elif "json.dump" in line_lower:
        return "write (json)"
    elif "open(" in line_lower:
        if "'w'" in line or '"w"' in line or "'a'" in line or '"a"' in line:
            return "write"
        return "read"
    elif "connect" in line_lower:
        return "connect (database)"
    elif "path" in line_lower:
        return "path reference"
    
    return "reference"


def find_file_usages(
    project_path: Path,
    file_path: str,
    exclude_dirs: Optional[Set[str]] = None,
    show_progress: bool = False
) -> List[FileUsage]:
    """
    Find all places where a file path is referenced in Python code.
    
    Args:
        project_path: Project root
        file_path: Relative path to search for (e.g., "data/products.json")
        exclude_dirs: Directories to skip
        show_progress: If True, show progress dots
    
    Returns:
        List of FileUsage showing where file is used
    """
    exclude_dirs = exclude_dirs or {"venv", ".venv", "__pycache__", "node_modules", ".git"}
    usages = []
    
    # Normalize path for searching
    search_patterns = [
        file_path,
        file_path.replace("/", "\\\\"),  # Windows paths
        file_path.replace("\\", "/"),     # Unix paths
    ]
    
    # Get all Python files first for progress tracking
    all_py_files = list(project_path.rglob("*.py"))
    total_files = len([f for f in all_py_files if not any(exc in f.parts for exc in exclude_dirs)])
    
    processed = 0
    for py_file in all_py_files:
        # Skip excluded dirs
        if any(exc in py_file.parts for exc in exclude_dirs):
            continue
        
        processed += 1
        if show_progress and processed % 50 == 0:
            print(f"   Scanning... {processed}/{total_files} files", end="\r", flush=True)
        
        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                for pattern in search_patterns:
                    if pattern in line:
                        # Determine usage type
                        usage_type = _detect_usage_type(line)
                        
                        usages.append(FileUsage(
                            file=py_file,
                            line=i,
                            context=line.strip()[:100],
                            usage_type=usage_type
                        ))
                        break  # Don't duplicate for same line
                        
        except Exception:
            continue
    
    if show_progress:
        print(f"   Scanning... {processed}/{total_files} files done" + " " * 20)
    
    return usages


def generate_file_description(traced_file: TracedFile) -> str:
    """
    Generate human-readable description of a file.
    
    Example:
        "Products catalog (JSON) containing 1,500 items with fields: 
        id, name, price, category. Used by handlers/buy.py and api/products.py"
    """
    parts = []
    
    # File type description
    cat_descriptions = {
        "data": "Data file",
        "database": "Database",
        "log": "Log file",
        "config": "Configuration",
    }
    parts.append(cat_descriptions.get(traced_file.category, "File"))
    
    # Format info
    ext = Path(traced_file.original_path).suffix.lower()
    format_names = {
        ".json": "(JSON)",
        ".csv": "(CSV)",
        ".sqlite": "(SQLite)",
        ".db": "(Database)",
        ".yaml": "(YAML)",
        ".yml": "(YAML)",
        ".xml": "(XML)",
    }
    if ext in format_names:
        parts.append(format_names[ext])
    
    # Schema info
    if traced_file.schema:
        schema = traced_file.schema.get("schema", {})
        if "columns" in schema:
            parts.append(f"with {len(schema['columns'])} columns")
        elif "keys" in schema:
            parts.append(f"with {len(schema['keys'])} fields")
        elif "tables" in schema:
            parts.append(f"with {len(schema['tables'])} tables")
    
    # Usage info
    if traced_file.usages:
        files_using = set(u.file.stem for u in traced_file.usages)
        if len(files_using) <= 3:
            parts.append(f"used by {', '.join(files_using)}")
        else:
            parts.append(f"used by {len(files_using)} files")
    
    return " ".join(parts)


def generate_fox_trace_map(
    project_path: Path,
    moved_files: List[MovedFile],
    show_progress: bool = True
) -> FoxTraceMap:
    """
    Generate complete Fox Trace Map.
    
    Process:
    1. For each moved file:
       - Get schema from schema_extractor
       - Find all usages in codebase
       - Generate description
    2. Compile into FoxTraceMap
    
    Args:
        project_path: Path to project root
        moved_files: List of moved files
        show_progress: If True, show progress indicators
    """
    project_path = project_path.resolve()
    
    trace_map = FoxTraceMap(
        project_name=project_path.name,
        generated_at=datetime.now().isoformat(),
        total_moved_files=len(moved_files),
        total_tokens_saved=sum(mf.estimated_tokens for mf in moved_files)
    )
    
    total = len(moved_files)
    for idx, mf in enumerate(moved_files, 1):
        if show_progress:
            print(f"   Processing {idx}/{total}: {mf.original_relative[:50]}...", end="\r", flush=True)
        
        # Find usages
        usages = find_file_usages(project_path, mf.original_relative, show_progress=False)
        
        # Generate schema markdown
        if mf.schema:
            schema_md = schema_to_markdown(mf.schema)
        else:
            schema_md = "_Schema not available_"
        
        traced = TracedFile(
            original_path=mf.original_relative,
            external_path=str(mf.external_path),
            category=mf.category.value if hasattr(mf.category, 'value') else str(mf.category),
            estimated_tokens=mf.estimated_tokens,
            schema=mf.schema,
            schema_markdown=schema_md,
            usages=usages
        )
        
        traced.description = generate_file_description(traced)
        trace_map.traced_files.append(traced)
    
    if show_progress:
        print(f"   Processed {total}/{total} files" + " " * 50)
    
    return trace_map


def write_fox_trace_md(
    trace_map: FoxTraceMap,
    output_path: Path
) -> Path:
    """
    Write AST_FOX_TRACE.md file.
    
    Format:
    # 🦊 Fox Trace Map — Project Navigation
    
    > This file helps AI assistants understand external data without loading it.
    > Generated by Fox Pro AI Deep Clean.
    
    ## Summary
    - Files moved: 12
    - Tokens saved: 4.8M
    - External storage: ../project_data/
    
    ## External Files
    
    ### 📦 data/products.json
    
    **Location:** `../project_data/data/products.json`
    **Category:** Data (JSON)
    **Tokens:** ~50,000
    **Bridge:** `from config_paths import get_path; get_path("data/products.json")`
    
    **Schema:**
    ```json
    {
      "type": "array",
      "items": {
        "id": "integer",
        "name": "string",
        "price": "number",
        "category": "string"
      },
      "length": 1500
    }
    ```
    
    **Used in:**
    - `handlers/buy.py:45` — `data = json.load(open(get_path("data/products.json")))`
    - `api/products.py:23` — `products = load_products()`
    
    ---
    
    ### 📊 data/users.csv
    ...
    """
    lines = []
    
    # Header
    lines.append("# 🦊 Fox Trace Map — External Data Navigation")
    lines.append("")
    lines.append("> **This file helps AI assistants understand external data without loading it.**")
    lines.append(f"> Generated by Fox Pro AI Deep Clean at {trace_map.generated_at}")
    lines.append(">")
    lines.append("> Instead of loading 5MB of data, AI reads this 5KB map!")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary
    tokens_str = f"{trace_map.total_tokens_saved/1_000_000:.1f}M" if trace_map.total_tokens_saved >= 1_000_000 else f"{trace_map.total_tokens_saved/1_000:.0f}K"
    
    lines.append("## 📊 Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Files Moved | {trace_map.total_moved_files} |")
    lines.append(f"| Tokens Saved | ~{tokens_str} |")
    lines.append(f"| External Storage | `../{trace_map.project_name}_data/` |")
    lines.append(f"| Bridge File | `config_paths.py` |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Quick reference table
    lines.append("## 🗂️ Quick Reference")
    lines.append("")
    lines.append("| File | Type | Tokens | Used By |")
    lines.append("|------|------|--------|---------|")
    
    for tf in trace_map.traced_files:
        tokens = f"{tf.estimated_tokens/1_000:.0f}K"
        used_by = ", ".join(set(u.file.stem for u in tf.usages[:3]))
        if len(tf.usages) > 3:
            used_by += f" +{len(tf.usages)-3}"
        if not used_by:
            used_by = "-"
        lines.append(f"| `{tf.original_path}` | {tf.category} | {tokens} | {used_by} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # How to access
    lines.append("## 🔗 How to Access External Files")
    lines.append("")
    lines.append("```python")
    lines.append("from config_paths import get_path, get_schema")
    lines.append("")
    lines.append("# Get file path")
    lines.append('path = get_path("data/products.json")')
    lines.append("")
    lines.append("# Load file")
    lines.append('with open(get_path("data/products.json")) as f:')
    lines.append("    data = json.load(f)")
    lines.append("")
    lines.append("# Get schema (structure without data)")
    lines.append('schema = get_schema("data/products.json")')
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Detailed file sections
    lines.append("## 📦 External Files (Detailed)")
    lines.append("")
    
    for tf in trace_map.traced_files:
        # File header
        icon = {
            "data": "📦",
            "database": "🗄️",
            "log": "📋",
            "config": "⚙️",
        }.get(tf.category.lower(), "📄")
        
        lines.append(f"### {icon} {tf.original_path}")
        lines.append("")
        
        # Metadata
        tokens = f"{tf.estimated_tokens/1_000:.0f}K"
        lines.append(f"**Category:** {tf.category.title()}")
        lines.append(f"**Tokens:** ~{tokens}")
        lines.append(f"**External:** `../{trace_map.project_name}_data/{tf.original_path}`")
        lines.append("")
        
        # Access pattern
        lines.append("**Access:**")
        lines.append("```python")
        lines.append(f'from config_paths import get_path')
        lines.append(f'path = get_path("{tf.original_path}")')
        lines.append("```")
        lines.append("")
        
        # Schema
        if tf.schema and tf.schema_markdown:
            lines.append("**Schema (structure only, no data):**")
            lines.append("")
            lines.append(tf.schema_markdown)
            lines.append("")
        
        # Usages
        if tf.usages:
            lines.append("**Used in:**")
            lines.append("")
            for usage in tf.usages[:10]:
                rel_path = usage.file.name
                lines.append(f"- `{rel_path}:{usage.line}` — `{usage.context[:60]}...`")
            if len(tf.usages) > 10:
                lines.append(f"- _...and {len(tf.usages) - 10} more references_")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # Footer
    lines.append("## 💡 Tips for AI Assistants")
    lines.append("")
    lines.append("1. **Don't ask for file contents** — Use the schema above to understand structure")
    lines.append("2. **Use `get_path()`** — All moved files are accessed via config_paths")
    lines.append("3. **Check schema first** — Know what fields exist before writing code")
    lines.append(f"4. **Files are external** — They exist in `../{trace_map.project_name}_data/`, not in project folder")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Fox Pro AI v3.6.0 — Fox Trace Map*")
    
    # Write file
    content = "\n".join(lines)
    output_file = output_path / "AST_FOX_TRACE.md"
    output_file.write_text(content, encoding="utf-8")
    
    return output_file


def generate_cursor_context(trace_map: FoxTraceMap) -> str:
    """
    Generate compact context for Cursor's .cursorrules.
    
    This goes into .cursor/rules/external_data.md
    
    Format:
    # External Data Files
    
    These files are stored externally to save tokens. 
    Use `from config_paths import get_path` to access them.
    
    | File | Schema | Used By |
    |------|--------|---------|
    | data/products.json | {id, name, price} | buy.py, products.py |
    | data/users.csv | id, name, email, created | auth.py, users.py |
    """
    lines = []
    
    lines.append("# External Data Files")
    lines.append("")
    lines.append("These files are stored externally to save tokens.")
    lines.append("Use `from config_paths import get_path` to access them.")
    lines.append("")
    lines.append("| File | Schema | Tokens |")
    lines.append("|------|--------|--------|")
    
    for tf in trace_map.traced_files:
        # Compact schema representation
        if tf.schema and "schema" in tf.schema:
            schema_info = tf.schema["schema"]
            if "columns" in schema_info:
                schema_str = ", ".join(schema_info["columns"][:5])
                if len(schema_info["columns"]) > 5:
                    schema_str += "..."
            elif "keys" in schema_info:
                keys = list(schema_info["keys"].keys())[:5]
                schema_str = ", ".join(keys)
                if len(schema_info["keys"]) > 5:
                    schema_str += "..."
            else:
                schema_str = tf.category
        else:
            schema_str = tf.category
        
        tokens = f"{tf.estimated_tokens/1_000:.0f}K"
        lines.append(f"| `{tf.original_path}` | {schema_str} | {tokens} |")
    
    lines.append("")
    lines.append("**Access pattern:**")
    lines.append("```python")
    lines.append("from config_paths import get_path")
    lines.append('data = open(get_path("file.json")).read()')
    lines.append("```")
    
    return "\n".join(lines)


def write_cursor_rules(
    trace_map: FoxTraceMap,
    project_path: Path
) -> Path:
    """Write external data rules to .cursor/rules/external_data.md"""
    cursor_rules = project_path / ".cursor" / "rules"
    cursor_rules.mkdir(parents=True, exist_ok=True)
    
    content = generate_cursor_context(trace_map)
    output_file = cursor_rules / "external_data.md"
    output_file.write_text(content, encoding="utf-8")
    
    return output_file

