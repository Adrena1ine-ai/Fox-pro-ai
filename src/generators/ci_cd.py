"""
CI/CD file generator (GitHub Actions)
"""

from __future__ import annotations

from pathlib import Path

from ..core.file_utils import create_file
from ..core.constants import COLORS


def generate_ci_workflow(project_dir: Path, project_name: str) -> None:
    """Generate .github/workflows/ci.yml"""
    content = f"""# CI - {project_name}
# Runs on push and pull request

name: CI

on:
  push:
    branches: [main, master, develop]
  pull_request:
    branches: [main, master]

env:
  PYTHON_VERSION: "3.12"

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ env.PYTHON_VERSION }}}}
      
      - name: Install ruff
        run: pip install ruff
      
      - name: Run ruff
        run: ruff check .

  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ env.PYTHON_VERSION }}}}
          cache: pip
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  check-repo:
    name: Check repo clean
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check no venv in repo
        run: |
          if [ -d "venv" ] || [ -d ".venv" ]; then
            echo "ERROR: venv found in repository!"
            exit 1
          fi
          echo "Repo is clean"

  build:
    name: Build Docker
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: docker build -t {project_name}:${{{{ github.sha }}}} .
      
      # Uncomment to push to registry
      # - name: Login to Docker Hub
      #   uses: docker/login-action@v3
      #   with:
      #     username: ${{{{ secrets.DOCKER_USERNAME }}}}
      #     password: ${{{{ secrets.DOCKER_PASSWORD }}}}
      #
      # - name: Push image
      #   run: |
      #     docker tag {project_name}:${{{{ github.sha }}}} username/{project_name}:latest
      #     docker push username/{project_name}:latest
"""
    workflows_dir = project_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    create_file(workflows_dir / "ci.yml", content)


def generate_cd_workflow(project_dir: Path, project_name: str) -> None:
    """Generate .github/workflows/cd.yml (deploy)"""
    content = f"""# CD - {project_name}
# Auto deploy on push to main

name: CD

on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

env:
  PYTHON_VERSION: "3.12"

jobs:
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      # === Option 1: Deploy via SSH ===
      # - name: Deploy via SSH
      #   uses: appleboy/ssh-action@v1.0.3
      #   with:
      #     host: ${{{{ secrets.SERVER_HOST }}}}
      #     username: ${{{{ secrets.SERVER_USER }}}}
      #     key: ${{{{ secrets.SSH_PRIVATE_KEY }}}}
      #     script: |
      #       cd /opt/{project_name}
      #       git pull origin main
      #       docker-compose up -d --build
      
      # === Option 2: Deploy to Railway/Render/Fly.io ===
      # - name: Deploy to Railway
      #   uses: bervProject/railway-deploy@main
      #   with:
      #     railway_token: ${{{{ secrets.RAILWAY_TOKEN }}}}
      
      # === Option 3: Deploy to VPS via Docker ===
      # - name: Build and push
      #   run: |
      #     docker build -t ghcr.io/${{{{ github.repository }}}}:latest .
      #     echo ${{{{ secrets.GITHUB_TOKEN }}}} | docker login ghcr.io -u ${{{{ github.actor }}}} --password-stdin
      #     docker push ghcr.io/${{{{ github.repository }}}}:latest
      
      - name: Placeholder
        run: echo "Configure your deployment in .github/workflows/cd.yml"
"""
    workflows_dir = project_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    create_file(workflows_dir / "cd.yml", content)


def generate_dependabot(project_dir: Path) -> None:
    """Generate .github/dependabot.yml"""
    content = """# Dependabot - automatic dependency updates

version: 2

updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    commit-message:
      prefix: "deps"
    labels:
      - "dependencies"
      - "python"
    
  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    commit-message:
      prefix: "ci"
    labels:
      - "dependencies"
      - "ci"
    
  # Docker
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    commit-message:
      prefix: "docker"
    labels:
      - "dependencies"
      - "docker"
"""
    create_file(project_dir / ".github" / "dependabot.yml", content)


def generate_pre_commit_config(project_dir: Path, project_name: str) -> None:
    """Generate .pre-commit-config.yaml"""
    content = f"""# Pre-commit hooks - {project_name}
# Install: pip install pre-commit && pre-commit install

repos:
  # Check that venv is not in project
  - repo: local
    hooks:
      - id: check-repo-clean
        name: Check repo is clean (no venv)
        entry: ./scripts/check_repo_clean.sh
        language: script
        pass_filenames: false
        always_run: true

  # Standard checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: debug-statements
      - id: detect-private-key

  # Python formatting & linting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.4
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # Type checking (optional)
  # - repo: https://github.com/pre-commit/mirrors-mypy
  #   rev: v1.9.0
  #   hooks:
  #     - id: mypy
  #       additional_dependencies: [types-all]
"""
    create_file(project_dir / ".pre-commit-config.yaml", content)


def generate_ci_files(project_dir: Path, project_name: str) -> None:
    """
    Create all CI/CD files
    
    Args:
        project_dir: Project path
        project_name: Project name
    """
    print(f"\n{COLORS.colorize('CI/CD...', COLORS.CYAN)}")
    
    generate_ci_workflow(project_dir, project_name)
    generate_cd_workflow(project_dir, project_name)
    generate_dependabot(project_dir)
    generate_pre_commit_config(project_dir, project_name)
