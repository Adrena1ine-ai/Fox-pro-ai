"""
🦊 Fox Pro AI — Integration Tests

Tests the full cycle: Scan → Move → Bridge → Patch → Map
"""

import pytest
import json
import shutil
from pathlib import Path


@pytest.fixture
def realistic_project(tmp_path):
    """
    Create a realistic project for testing.
    
    Structure:
        project/
        ├── venv/                    # venv inside (problem!)
        │   └── pyvenv.cfg
        ├── data/
        │   └── products.json        # Heavy file
        ├── src/
        │   ├── __init__.py
        │   └── main.py              # Uses products.json
        ├── __pycache__/
        └── temp.tmp                 # Garbage
    """
    project = tmp_path / "test_project"
    project.mkdir()
    
    # venv (problem)
    venv = project / "venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("home = /usr/bin/python3")
    (venv / "lib").mkdir()
    
    # data with heavy file
    data = project / "data"
    data.mkdir()
    
    # products.json (~5000 tokens)
    products = [{"id": i, "name": f"Product {i}", "price": 10.0 * i} for i in range(500)]
    (data / "products.json").write_text(json.dumps(products, indent=2))
    
    # src
    src = project / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    
    (src / "main.py").write_text('''
import json
from pathlib import Path

def load_products():
    with open("data/products.json") as f:
        return json.load(f)

if __name__ == "__main__":
    products = load_products()
    print(f"Loaded {len(products)} products")
''')
    
    # __pycache__
    pycache = project / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-311.pyc").write_bytes(b"\x00" * 100)
    
    # Garbage
    (project / "temp.tmp").write_text("temporary")
    
    return project


class TestDoctorReport:
    """Test doctor --report mode."""
    
    def test_diagnose_finds_venv(self, realistic_project):
        """Should find venv inside project."""
        from src.commands.doctor import diagnose
        
        report = diagnose(realistic_project)
        
        venv_issues = [i for i in report.issues if i.category == "venv"]
        assert len(venv_issues) > 0, "Should find venv issue"
    
    def test_diagnose_finds_pycache(self, realistic_project):
        """Should find __pycache__ directories."""
        from src.commands.doctor import diagnose
        
        report = diagnose(realistic_project)
        
        pycache_issues = [i for i in report.issues if i.category == "pycache"]
        assert len(pycache_issues) > 0, "Should find pycache issue"
    
    def test_diagnose_suggests_cursorignore(self, realistic_project):
        """Should suggest creating .cursorignore."""
        from src.commands.doctor import diagnose
        
        report = diagnose(realistic_project)
        
        config_issues = [i for i in report.issues if i.category == "config"]
        assert len(config_issues) > 0, "Should suggest .cursorignore"


class TestDoctorFix:
    """Test doctor --fix mode."""
    
    def test_fix_creates_cursorignore(self, realistic_project):
        """Should create .cursorignore file."""
        from src.commands.doctor import diagnose, fix_issues
        
        report = diagnose(realistic_project)
        fix_issues(realistic_project, report)
        
        assert (realistic_project / ".cursorignore").exists(), \
            "Should create .cursorignore"
    
    def test_fix_removes_pycache(self, realistic_project):
        """Should remove __pycache__ directories."""
        from src.commands.doctor import diagnose, fix_issues
        
        assert (realistic_project / "__pycache__").exists(), "Precondition: pycache exists"
        
        report = diagnose(realistic_project)
        fix_issues(realistic_project, report)
        
        assert not (realistic_project / "__pycache__").exists(), \
            "Should remove __pycache__"


class TestExternalPaths:
    """Test unified external path system."""
    
    def test_external_root_format(self, realistic_project):
        """External root should follow new format: project_fox/"""
        from src.core.paths import get_external_root
        
        external = get_external_root(realistic_project)
        
        assert external.name == "test_project_fox", \
            f"External should be 'test_project_fox', got '{external.name}'"
    
    def test_ensure_structure_creates_dirs(self, realistic_project):
        """Should create all external directories."""
        from src.core.paths import ensure_external_structure, get_external_root
        
        external = ensure_external_structure(realistic_project)
        
        assert (external / "data").exists(), "Should create data/"
        assert (external / "venvs").exists(), "Should create venvs/"
        assert (external / "logs").exists(), "Should create logs/"
        assert (external / "garbage").exists(), "Should create garbage/"
        assert (external / "manifest.json").exists(), "Should create manifest.json"
    
    def test_manifest_operations(self, realistic_project):
        """Should save and load manifest correctly."""
        from src.core.paths import (
            ensure_external_structure,
            add_to_manifest,
            load_manifest,
        )
        
        ensure_external_structure(realistic_project)
        
        add_to_manifest(
            realistic_project,
            original_path="data/products.json",
            external_path="data/data/products.json",
            file_type="data",
            tokens=5000,
        )
        
        manifest = load_manifest(realistic_project)
        
        assert len(manifest["files"]) == 1, "Should have one file"
        assert manifest["files"][0]["original"] == "data/products.json"
        assert manifest["files"][0]["tokens"] == 5000


class TestTokenScanner:
    """Test token scanner module."""
    
    def test_scan_finds_heavy_files(self, realistic_project):
        """Should find heavy JSON file."""
        from src.scanner.token_scanner import scan_project
        
        result = scan_project(
            project_path=realistic_project,
            threshold=1000,
            show_progress=False,
        )
        
        assert result.total_tokens > 0, "Should count tokens"
        
        heavy_names = [f.path.name for f in result.heavy_files]
        assert "products.json" in heavy_names, "Should find products.json as heavy"


class TestDynamicPathDetection:
    """Test dynamic path detection."""
    
    def test_detects_fstring_paths(self, tmp_path):
        """Should detect f-string dynamic paths."""
        from src.optimizer.ast_patcher import detect_dynamic_paths
        
        # Create test file with dynamic path
        test_file = tmp_path / "test.py"
        test_file.write_text('''
user_id = 123
with open(f"data/{user_id}.json") as f:
    data = json.load(f)
''')
        
        warnings = detect_dynamic_paths(tmp_path, {"data/users.json"})
        
        assert len(warnings) > 0, "Should detect f-string path"
        assert warnings[0].pattern_type == "f-string"
    
    def test_detects_concat_paths(self, tmp_path):
        """Should detect concatenation paths."""
        from src.optimizer.ast_patcher import detect_dynamic_paths
        
        test_file = tmp_path / "test.py"
        test_file.write_text('''
filename = "users.json"
path = "data/" + filename
''')
        
        warnings = detect_dynamic_paths(tmp_path, {"data/users.json"})
        
        assert len(warnings) > 0, "Should detect concat path"
        assert warnings[0].pattern_type == "concat"
    
    def test_detects_join_paths(self, tmp_path):
        """Should detect os.path.join paths."""
        from src.optimizer.ast_patcher import detect_dynamic_paths
        
        test_file = tmp_path / "test.py"
        test_file.write_text('''
import os
path = os.path.join("data", filename)
''')
        
        warnings = detect_dynamic_paths(tmp_path, {"data/users.json"})
        
        assert len(warnings) > 0, "Should detect join path"
        assert warnings[0].pattern_type == "join"


class TestCLI:
    """Test CLI commands."""
    
    def test_cli_version(self, tmp_path):
        """CLI should show version."""
        import subprocess
        import sys
        import os
        
        project_root = Path(__file__).parent.parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        result = subprocess.run(
            [sys.executable, "-m", "src", "--version"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env=env,
        )
        
        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert "4.0.0" in result.stdout
    
    def test_cli_doctor_report(self, realistic_project):
        """CLI doctor --report should work."""
        import subprocess
        import sys
        import os
        
        project_root = Path(__file__).parent.parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        result = subprocess.run(
            [sys.executable, "-m", "src", "doctor", str(realistic_project), "--report"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env=env,
        )
        
        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert "Doctor" in result.stdout or "Project" in result.stdout


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_external(tmp_path):
    """Clean up external directories after tests."""
    yield
    
    # Clean up any external directories created
    for item in tmp_path.parent.iterdir():
        if item.name.endswith("_fox"):
            shutil.rmtree(item, ignore_errors=True)
