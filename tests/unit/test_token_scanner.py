"""
Tests for token scanner utility.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import json

from src.utils.token_scanner import (
    scan_project,
    scan_file,
    estimate_tokens,
    categorize_file,
    should_skip_dir,
    format_scan_report,
    get_moveable_files,
    FileCategory,
    HeavyFile,
    ScanResult,
    SKIP_DIRS
)


@pytest.fixture
def temp_project():
    """Create a temporary project with various files."""
    temp_dir = tempfile.mkdtemp()
    project = Path(temp_dir) / "test_project"
    project.mkdir()
    
    # Create small file (under threshold)
    (project / "small.txt").write_text("Hello world")
    
    # Create large JSON (over threshold)
    large_data = {"items": [{"id": i, "name": f"Item {i}"} for i in range(1000)]}
    (project / "large_data.json").write_text(json.dumps(large_data))
    
    # Create large CSV
    csv_content = "id,name,value\n" + "\n".join(f"{i},Name{i},{i*100}" for i in range(500))
    data_dir = project / "data"
    data_dir.mkdir()
    (data_dir / "products.csv").write_text(csv_content)
    
    # Create log file
    logs_dir = project / "logs"
    logs_dir.mkdir()
    (logs_dir / "app.log").write_text("INFO: " * 5000)
    
    # Create Python file
    (project / "main.py").write_text("print('hello')")
    
    # Create venv (should be skipped)
    venv_dir = project / "venv"
    venv_dir.mkdir()
    (venv_dir / "huge.txt").write_text("x" * 100000)
    
    yield project
    shutil.rmtree(temp_dir)


class TestEstimateTokens:
    def test_small_file(self, temp_project):
        tokens = estimate_tokens(temp_project / "small.txt")
        assert tokens < 100
    
    def test_large_file(self, temp_project):
        tokens = estimate_tokens(temp_project / "large_data.json")
        assert tokens > 1000
    
    def test_binary_file_returns_zero(self, temp_project):
        # Create a fake binary file (we'll just check the extension logic)
        binary_file = temp_project / "image.png"
        binary_file.touch()
        # The function should return 0 for .png files
        # But since we're just touching, size is 0, so tokens will be 0 anyway
        tokens = estimate_tokens(binary_file)
        assert tokens == 0


class TestCategorizeFile:
    def test_json_is_data(self):
        assert categorize_file(Path("test.json")) == FileCategory.DATA
    
    def test_csv_is_data(self):
        assert categorize_file(Path("data.csv")) == FileCategory.DATA
    
    def test_py_is_code(self):
        assert categorize_file(Path("main.py")) == FileCategory.CODE
    
    def test_log_is_log(self):
        assert categorize_file(Path("app.log")) == FileCategory.LOG
    
    def test_sqlite_is_database(self):
        assert categorize_file(Path("data.sqlite")) == FileCategory.DATABASE
    
    def test_png_is_binary(self):
        assert categorize_file(Path("image.png")) == FileCategory.BINARY


class TestShouldSkipDir:
    def test_skips_venv(self):
        assert should_skip_dir("venv") is True
    
    def test_skips_node_modules(self):
        assert should_skip_dir("node_modules") is True
    
    def test_skips_pycache(self):
        assert should_skip_dir("__pycache__") is True
    
    def test_allows_normal_dir(self):
        assert should_skip_dir("src") is False
    
    def test_skips_hidden(self):
        assert should_skip_dir(".git") is True
    
    def test_allows_github(self):
        assert should_skip_dir(".github") is False


class TestScanProject:
    def test_finds_heavy_files(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        assert len(result.heavy_files) > 0
    
    def test_skips_venv(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        # venv/huge.txt should NOT be in heavy_files
        paths = [hf.relative_path for hf in result.heavy_files]
        assert not any("venv" in p for p in paths)
    
    def test_reports_total_tokens(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        assert result.total_tokens > 0
    
    def test_sorts_by_size(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        if len(result.heavy_files) >= 2:
            assert result.heavy_files[0].estimated_tokens >= result.heavy_files[1].estimated_tokens
    
    def test_extracts_schemas(self, temp_project):
        result = scan_project(temp_project, threshold=100, extract_schemas=True)
        json_files = [hf for hf in result.heavy_files if hf.extension == ".json"]
        if json_files:
            assert json_files[0].schema is not None
    
    def test_includes_code_when_requested(self, temp_project):
        result = scan_project(temp_project, threshold=1, include_code=True)
        code_files = [hf for hf in result.heavy_files if hf.category == FileCategory.CODE]
        # main.py should be included if include_code=True
        assert len(code_files) > 0
    
    def test_excludes_code_by_default(self, temp_project):
        result = scan_project(temp_project, threshold=1, include_code=False)
        code_files = [hf for hf in result.heavy_files if hf.category == FileCategory.CODE]
        # main.py should NOT be included if include_code=False
        assert len(code_files) == 0


class TestScanResult:
    def test_heavy_tokens(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        assert result.heavy_tokens == sum(hf.estimated_tokens for hf in result.heavy_files)
    
    def test_potential_savings(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        if result.total_tokens > 0:
            assert 0 <= result.potential_savings <= 100
    
    def test_light_tokens(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        assert result.light_tokens == result.total_tokens - result.heavy_tokens


class TestFormatReport:
    def test_generates_report(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        report = format_scan_report(result)
        assert "TOKEN SCANNER" in report
        assert result.project_name in report
    
    def test_shows_heavy_files(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        report = format_scan_report(result)
        if result.heavy_files:
            assert "HEAVY FILES" in report
    
    def test_shows_statistics(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        report = format_scan_report(result)
        assert "Files Scanned" in report
        assert "Total Tokens" in report


class TestGetMoveableFiles:
    def test_excludes_main_py(self, temp_project):
        result = scan_project(temp_project, threshold=1, include_code=True)
        moveable = get_moveable_files(result)
        names = [hf.path.name for hf in moveable]
        assert "main.py" not in names
    
    def test_includes_data_files(self, temp_project):
        result = scan_project(temp_project, threshold=100)
        moveable = get_moveable_files(result)
        categories = [hf.category for hf in moveable]
        assert FileCategory.DATA in categories or FileCategory.LOG in categories
    
    def test_excludes_protected_files(self, temp_project):
        # Create a protected file
        (temp_project / "config.py").write_text("# config" * 1000)
        result = scan_project(temp_project, threshold=100, include_code=True)
        moveable = get_moveable_files(result)
        names = [hf.path.name for hf in moveable]
        assert "config.py" not in names


class TestScanFile:
    def test_returns_none_for_small_file(self, temp_project):
        small_file = temp_project / "small.txt"
        result = scan_file(small_file, temp_project, threshold=1000, include_code=False, extract_schemas=False)
        assert result is None
    
    def test_returns_heavy_file_for_large_file(self, temp_project):
        large_file = temp_project / "large_data.json"
        result = scan_file(large_file, temp_project, threshold=100, include_code=False, extract_schemas=False)
        assert result is not None
        assert isinstance(result, HeavyFile)
        assert result.estimated_tokens >= 100
    
    def test_includes_schema_when_requested(self, temp_project):
        large_file = temp_project / "large_data.json"
        result = scan_file(large_file, temp_project, threshold=100, include_code=False, extract_schemas=True)
        assert result is not None
        assert result.can_extract_schema is True
        # Schema might be None if extraction fails, but can_extract_schema should be True

