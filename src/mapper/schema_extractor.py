"""
Schema Extractor — Extract structure from data files without loading full content.
Used by Deep Clean & Bridge to create navigation maps.
"""

from __future__ import annotations

import ast
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _infer_type(value: Any) -> str:
    """Infer JSON type from Python value."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    return "unknown"


def _extract_structure(obj: Any, depth: int, max_depth: int) -> Dict[str, Any]:
    """Recursively extract structure without values."""
    if depth >= max_depth:
        return {"type": _infer_type(obj), "truncated": True}
    
    if isinstance(obj, dict):
        return {
            "type": "object",
            "keys": {k: _extract_structure(v, depth + 1, max_depth) for k, v in obj.items()}
        }
    elif isinstance(obj, list):
        if not obj:
            return {"type": "array", "items": "empty"}
        # Sample first item for structure
        return {
            "type": "array",
            "length": len(obj),
            "items": _extract_structure(obj[0], depth + 1, max_depth)
        }
    else:
        return {"type": _infer_type(obj)}


def extract_json_schema(file_path: Path, max_depth: int = 3) -> Dict[str, Any]:
    """
    Extract JSON structure without values.
    
    Example:
        Input: {"users": [{"name": "John", "age": 30}], "config": {"debug": true}}
        Output: {
            "type": "object",
            "keys": {
                "users": {"type": "array", "items": {"type": "object", "keys": {"name": "string", "age": "number"}}},
                "config": {"type": "object", "keys": {"debug": "boolean"}}
            }
        }
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return _extract_structure(data, 0, max_depth)
    except Exception as e:
        return {"error": str(e)}


def _infer_csv_type(values: List[str]) -> str:
    """Infer column type from sample values."""
    for val in values:
        if not val:
            continue
        try:
            int(val)
            return "int"
        except ValueError:
            pass
        try:
            float(val)
            return "float"
        except ValueError:
            pass
    return "str"


def extract_csv_schema(file_path: Path, sample_rows: int = 5) -> Dict[str, Any]:
    """
    Extract CSV structure: headers, types, row count.
    
    Example:
        Input: id,name,price,stock
               1,Apple,1.50,100
        Output: {
            "columns": ["id", "name", "price", "stock"],
            "types": {"id": "int", "name": "str", "price": "float", "stock": "int"},
            "row_count": 1000,
            "sample": [{"id": 1, "name": "Apple", "price": 1.50, "stock": 100}]
        }
    """
    try:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            columns = reader.fieldnames or []
            
            # Read sample rows
            rows = []
            row_count = 0
            for i, row in enumerate(reader):
                row_count += 1
                if i < sample_rows:
                    rows.append(row)
            
            # Infer types from sample
            types = {}
            for col in columns:
                sample_values = [row.get(col, '') for row in rows if col in row]
                types[col] = _infer_csv_type(sample_values)
            
            return {
                "columns": list(columns),
                "types": types,
                "row_count": row_count,
                "sample": rows[:sample_rows] if rows else []
            }
    except Exception as e:
        return {"error": str(e)}


def extract_sqlite_schema(file_path: Path) -> Dict[str, Any]:
    """
    Extract SQLite database schema.
    
    Example:
        Output: {
            "tables": {
                "users": {
                    "columns": [
                        {"name": "id", "type": "INTEGER", "pk": True},
                        {"name": "email", "type": "TEXT", "nullable": False}
                    ],
                    "row_count": 5000
                }
            }
        }
    """
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {}
        
        for (table_name,) in cursor.fetchall():
            # Get columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row[1],
                    "type": row[2],
                    "nullable": not row[3],
                    "pk": bool(row[5])
                })
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            tables[table_name] = {
                "columns": columns,
                "row_count": row_count
            }
        
        conn.close()
        return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}


def extract_yaml_schema(file_path: Path, max_depth: int = 3) -> Dict[str, Any]:
    """
    Extract YAML structure (similar to JSON).
    """
    if not HAS_YAML:
        return {"error": "PyYAML not installed"}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return _extract_structure(data, 0, max_depth)
    except Exception as e:
        return {"error": str(e)}


def extract_python_dict_schema(file_path: Path) -> Dict[str, Any]:
    """
    Extract large dict/list literals from Python files using AST.
    
    Example:
        Input: DATA = {"key1": [...1000 items...], "key2": {...}}
        Output: {
            "variables": {
                "DATA": {"type": "dict", "keys": ["key1", "key2"], "estimated_tokens": 50000}
            }
        }
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        variables = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        
                        # Check if value is a dict or list
                        if isinstance(node.value, ast.Dict):
                            keys = []
                            for k in node.value.keys:
                                if isinstance(k, ast.Constant):
                                    keys.append(str(k.value))
                                elif isinstance(k, ast.Str):  # Python < 3.8
                                    keys.append(k.s)
                            
                            # Estimate size
                            try:
                                # Try to unparse and estimate
                                code = ast.unparse(node.value)
                                estimated_tokens = len(code) // 4
                            except:
                                estimated_tokens = 0
                            
                            variables[var_name] = {
                                "type": "dict",
                                "keys": keys,
                                "estimated_tokens": estimated_tokens
                            }
                        elif isinstance(node.value, ast.List):
                            try:
                                code = ast.unparse(node.value)
                                estimated_tokens = len(code) // 4
                            except:
                                estimated_tokens = 0
                            
                            variables[var_name] = {
                                "type": "list",
                                "length": len(node.value.elts),
                                "estimated_tokens": estimated_tokens
                            }
        
        return {"variables": variables}
    except Exception as e:
        return {"error": str(e)}


def estimate_tokens(file_path: Path) -> int:
    """Estimate tokens (roughly 4 chars per token)."""
    try:
        size = file_path.stat().st_size
        return size // 4
    except:
        return 0


def extract_schema(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Auto-detect file type and extract schema.
    
    Returns:
        {
            "file": "data.json",
            "type": "json",
            "size_bytes": 102400,
            "estimated_tokens": 25000,
            "schema": {...extracted schema...}
        }
    """
    if not file_path.exists():
        return None
    
    suffix = file_path.suffix.lower()
    size_bytes = file_path.stat().st_size
    estimated_tokens = estimate_tokens(file_path)
    
    schema = None
    file_type = "unknown"
    
    if suffix == ".json":
        file_type = "json"
        schema = extract_json_schema(file_path)
    elif suffix in [".csv", ".tsv"]:
        file_type = "csv"
        schema = extract_csv_schema(file_path)
    elif suffix in [".db", ".sqlite", ".sqlite3"]:
        file_type = "sqlite"
        schema = extract_sqlite_schema(file_path)
    elif suffix in [".yaml", ".yml"]:
        file_type = "yaml"
        schema = extract_yaml_schema(file_path)
    elif suffix == ".py":
        file_type = "python"
        schema = extract_python_dict_schema(file_path)
    
    if schema is None:
        return None
    
    return {
        "file": file_path.name,
        "type": file_type,
        "size_bytes": size_bytes,
        "estimated_tokens": estimated_tokens,
        "schema": schema
    }


def schema_to_markdown(schema: Dict[str, Any]) -> str:
    """
    Convert schema dict to human-readable Markdown.
    
    Example output:
        ## data.json (JSON, ~25K tokens)
        
        Structure:
        ```
        {
          users: Array<{name: string, age: number}>,
          config: {debug: boolean, api_key: string}
        }
        ```
    """
    if not schema:
        return "## Invalid schema"
    
    file_name = schema.get("file", "unknown")
    file_type = schema.get("type", "unknown")
    tokens = schema.get("estimated_tokens", 0)
    size_bytes = schema.get("size_bytes", 0)
    
    # Format tokens
    if tokens >= 1_000_000:
        token_str = f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        token_str = f"{tokens / 1_000:.1f}K"
    else:
        token_str = str(tokens)
    
    # Format size
    if size_bytes >= 1_000_000:
        size_str = f"{size_bytes / 1_000_000:.1f}MB"
    elif size_bytes >= 1_000:
        size_str = f"{size_bytes / 1_000:.1f}KB"
    else:
        size_str = f"{size_bytes}B"
    
    lines = [
        f"## {file_name} ({file_type.upper()}, ~{token_str} tokens, {size_str})",
        ""
    ]
    
    schema_data = schema.get("schema", {})
    
    if "error" in schema_data:
        lines.append(f"**Error:** {schema_data['error']}")
        return "\n".join(lines)
    
    # Format based on type
    if file_type == "json" or file_type == "yaml":
        lines.append("**Structure:**")
        lines.append("```")
        lines.append(_format_json_schema(schema_data))
        lines.append("```")
    elif file_type == "csv":
        columns = schema_data.get("columns", [])
        types = schema_data.get("types", {})
        row_count = schema_data.get("row_count", 0)
        
        lines.append(f"**Columns:** {len(columns)}")
        lines.append(f"**Rows:** {row_count}")
        lines.append("")
        lines.append("| Column | Type |")
        lines.append("|--------|------|")
        for col in columns:
            col_type = types.get(col, "unknown")
            lines.append(f"| `{col}` | `{col_type}` |")
    elif file_type == "sqlite":
        tables = schema_data.get("tables", {})
        lines.append(f"**Tables:** {len(tables)}")
        lines.append("")
        for table_name, table_info in tables.items():
            lines.append(f"### {table_name}")
            lines.append(f"**Rows:** {table_info.get('row_count', 0)}")
            lines.append("")
            lines.append("| Column | Type | Nullable | PK |")
            lines.append("|--------|------|----------|----|")
            for col in table_info.get("columns", []):
                lines.append(
                    f"| `{col['name']}` | `{col['type']}` | "
                    f"{'Yes' if col['nullable'] else 'No'} | "
                    f"{'Yes' if col.get('pk', False) else 'No'} |"
                )
            lines.append("")
    elif file_type == "python":
        variables = schema_data.get("variables", {})
        lines.append(f"**Variables:** {len(variables)}")
        lines.append("")
        for var_name, var_info in variables.items():
            var_type = var_info.get("type", "unknown")
            if var_type == "dict":
                keys = var_info.get("keys", [])
                tokens = var_info.get("estimated_tokens", 0)
                lines.append(f"- `{var_name}`: dict with keys: {', '.join(keys[:10])}")
                if len(keys) > 10:
                    lines.append(f"  ... and {len(keys) - 10} more keys")
                if tokens > 0:
                    lines.append(f"  Estimated tokens: {tokens}")
            elif var_type == "list":
                length = var_info.get("length", 0)
                tokens = var_info.get("estimated_tokens", 0)
                lines.append(f"- `{var_name}`: list with {length} items")
                if tokens > 0:
                    lines.append(f"  Estimated tokens: {tokens}")
    
    return "\n".join(lines)


def _format_json_schema(schema: Dict[str, Any], indent: int = 0) -> str:
    """Format JSON schema structure as readable text."""
    lines = []
    prefix = "  " * indent
    
    if schema.get("type") == "object":
        lines.append("{")
        for key, value in schema.get("keys", {}).items():
            value_type = value.get("type", "unknown")
            if value_type == "array":
                items = value.get("items", {})
                if isinstance(items, dict) and items.get("type") == "object":
                    lines.append(f"{prefix}  {key}: Array<{{...}}>")
                else:
                    lines.append(f"{prefix}  {key}: Array<{items.get('type', 'unknown')}>")
            elif value_type == "object":
                lines.append(f"{prefix}  {key}: {{...}}")
            else:
                lines.append(f"{prefix}  {key}: {value_type}")
        lines.append(prefix + "}")
    elif schema.get("type") == "array":
        items = schema.get("items", {})
        items_type = items.get("type", "unknown")
        if items_type == "object":
            lines.append("Array<{...}>")
        else:
            lines.append(f"Array<{items_type}>")
    else:
        lines.append(schema.get("type", "unknown"))
    
    return "\n".join(lines)

