# Анализ функции get_moveable_files()

## Полная функция (текущая версия)

```python
def get_moveable_files(
    result: ScanResult,
    exclude_paths: Set[str] | None = None,
    verbose: bool = True,
    debug: bool = False
) -> List[HeavyFile]:
    """
    Get files that can be safely moved to external storage.
    
    Args:
        result: ScanResult with heavy files
        exclude_paths: Set of relative paths to exclude (already moved files)
        verbose: If True, show why files are skipped
        debug: If True, show detailed debug output for each skipped file
    
    Excludes:
    - Python code files (.py) - project code should stay
    - Core config files that must stay in project
    - Files already in external dirs (checking path START, not substring)
    - Files in exclude_paths (already moved)
    """
    exclude_paths = exclude_paths or set()
    moveable = []
    skipped_reasons = {"py": 0, "config": 0, "already_moved": 0, "external_dir": 0}
    
    # Files that should NOT be moved (config files)
    protected_names = {
        "pyproject.toml", "package.json", "requirements.txt",
        "setup.py", "setup.cfg",
        ".env", ".env.example",
        "README.md", "CLAUDE.md", ".cursorrules",
        "config_paths.py",  # Bridge file must stay
    }
    
    # External dir patterns (must be at START of path, not substring!)
    external_dir_patterns = ["_venvs/", "_data/", "_artifacts/", "_logs/", "_fox/"]
    
    for hf in result.heavy_files:
        # DEBUG: показать почему пропускается
        if debug:
            print(f"     DEBUG: Checking {hf.relative_path} ({hf.estimated_tokens} tokens)")
        
        # Пропускаем уже перемещённые
        if hf.relative_path in exclude_paths:
            skipped_reasons["already_moved"] += 1
            if debug:
                print(f"     DEBUG: skip already_moved: {hf.relative_path}")
            continue
        
        # Не перемещаем Python файлы (код проекта)
        if hf.path.suffix == '.py':
            skipped_reasons["py"] += 1
            if debug:
                print(f"     DEBUG: skip .py: {hf.relative_path}")
            continue
        
        # Не перемещаем конфиги
        if hf.path.name.lower() in protected_names:
            skipped_reasons["config"] += 1
            if debug:
                print(f"     DEBUG: skip config: {hf.relative_path}")
            continue
        
        # Skip files already in external dirs (FIX: check path START, not substring!)
        # Normalize path separators for cross-platform compatibility
        normalized_path = hf.relative_path.replace("\\", "/")
        is_in_external = any(normalized_path.startswith(pattern) for pattern in external_dir_patterns)
        
        if is_in_external:
            skipped_reasons["external_dir"] += 1
            if debug:
                print(f"     DEBUG: skip external_dir: {hf.relative_path} (matches pattern)")
            continue
        
        # Всё остальное с >1000 токенов — перемещаем
        if debug:
            print(f"     DEBUG: ✅ MOVABLE: {hf.relative_path}")
        moveable.append(hf)
    
    if verbose and any(skipped_reasons.values()):
        print(f"\n  ⏭️  Skipped from moving:")
        if skipped_reasons["py"]:
            print(f"     {skipped_reasons['py']} .py files (source code)")
        if skipped_reasons["config"]:
            print(f"     {skipped_reasons['config']} config files")
        if skipped_reasons["already_moved"]:
            print(f"     {skipped_reasons['already_moved']} already moved")
        if skipped_reasons["external_dir"]:
            print(f"     {skipped_reasons['external_dir']} in external dirs")
    
    return moveable
```

## Анализ возможных причин бага

### ✅ ИСПРАВЛЕНО: Проверка на "_data" в пути

**Было (БАГ):**
```python
if any(external in hf.relative_path for external in ["_venvs", "_data", "_artifacts", "_logs", "_fox"]):
```

**Проблема:**
- `"_data" in "webapp\v2\family_data.json"` → `True` ❌
- Файл `family_data.json` ошибочно считался в external dir

**Стало (ИСПРАВЛЕНО):**
```python
normalized_path = hf.relative_path.replace("\\", "/")
is_in_external = any(normalized_path.startswith(pattern) for pattern in ["_venvs/", "_data/", "_artifacts/", "_logs/", "_fox/"])
```

**Теперь:**
- `"webapp/v2/family_data.json".startswith("_data/")` → `False` ✅
- Проверка только для путей вида `_data/some_file.json`

### 🔍 Другие возможные причины

#### 1. Файл уже в manifest (exclude_paths)

**Проверка:**
```python
if hf.relative_path in exclude_paths:
    skipped_reasons["already_moved"] += 1
    continue
```

**Как проверить:**
- Посмотреть `FaberlicFamilyBot_fox/manifest.json`
- Проверить есть ли там `"webapp/v2/family_data.json"` в поле `"original"`

**Решение:**
- Если файл в manifest, но физически не перемещён → удалить запись из manifest
- Или удалить `FaberlicFamilyBot_fox` папку и запустить заново

#### 2. Разные форматы пути (/ vs \)

**Проблема:**
- Windows: `webapp\v2\family_data.json`
- Linux/Mac: `webapp/v2/family_data.json`
- В exclude_paths может быть другой формат

**Решение:**
- Функция нормализует пути: `normalized_path = hf.relative_path.replace("\\", "/")`
- Но exclude_paths тоже нужно нормализовать!

**Потенциальный баг:**
```python
# Если exclude_paths содержит "webapp\\v2\\family_data.json" (Windows)
# А hf.relative_path = "webapp/v2/family_data.json" (нормализован)
# То проверка не сработает!
```

**Нужно исправить:**
```python
# Нормализовать exclude_paths тоже
normalized_exclude = {p.replace("\\", "/") for p in exclude_paths}
if normalized_path in normalized_exclude:
    ...
```

#### 3. Проверка parent директории

**Текущая проверка:**
- Проверяет только начало пути
- Не проверяет parent директории

**Если проблема:**
- Нужно проверить все части пути: `any(part in external_patterns for part in path.parts)`

## Рекомендации для диагностики

1. **Включить debug:**
   ```python
   moveable = get_moveable_files(scan_result, exclude_paths=already_moved_paths, verbose=True, debug=True)
   ```

2. **Проверить manifest:**
   ```bash
   cat FaberlicFamilyBot_fox/manifest.json | grep family_data
   ```

3. **Проверить config_paths.py:**
   ```bash
   cat config_paths.py | grep family_data
   ```

4. **Проверить exclude_paths:**
   - Добавить print в doctor.py перед вызовом get_moveable_files:
   ```python
   print(f"DEBUG: exclude_paths = {already_moved_paths}")
   ```

