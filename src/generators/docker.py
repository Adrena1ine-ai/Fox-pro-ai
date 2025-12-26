"""
Docker file generator
"""

from __future__ import annotations

from pathlib import Path

from ..core.file_utils import create_file
from ..core.constants import COLORS


def generate_dockerfile(project_dir: Path, project_name: str, template: str) -> None:
    """Generate Dockerfile"""
    
    # Determine run command based on template
    cmd_map = {
        "bot": 'CMD ["python", "bot/main.py"]',
        "webapp": 'CMD ["python", "-m", "http.server", "8000", "--directory", "webapp"]',
        "fastapi": 'CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]',
        "parser": 'CMD ["python", "parser/main.py"]',
        "full": 'CMD ["python", "bot/main.py"]',
    }
    
    cmd = cmd_map.get(template, 'CMD ["python", "main.py"]')
    
    # Extra packages for different templates
    extra_packages = ""
    if template in ["parser", "full"]:
        extra_packages = """
# Playwright (if needed)
# RUN pip install playwright && playwright install chromium --with-deps
"""
    
    content = f"""# Dockerfile - {project_name}
# Build: docker build -t {project_name} .
# Run: docker run -d --env-file .env {project_name}

FROM python:3.12-slim

# Metadata
LABEL maintainer="your@email.com"
LABEL version="1.0.0"
LABEL description="{project_name}"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Working directory
WORKDIR /app

# Install system dependencies (if needed)
# RUN apt-get update && apt-get install -y --no-install-recommends \\
#     gcc \\
#     && rm -rf /var/lib/apt/lists/*
{extra_packages}
# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create non-privileged user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (if needed)
# EXPOSE 8000

# Run command
{cmd}
"""
    create_file(project_dir / "Dockerfile", content)


def generate_docker_compose(project_dir: Path, project_name: str, template: str) -> None:
    """Generate docker-compose.yml"""
    
    # Extra services
    extra_services = ""
    
    if template in ["bot", "full", "fastapi"]:
        extra_services = f"""
  # Redis (uncomment if needed)
  # redis:
  #   image: redis:7-alpine
  #   restart: unless-stopped
  #   volumes:
  #     - redis_data:/data

  # PostgreSQL (uncomment if needed)
  # postgres:
  #   image: postgres:16-alpine
  #   restart: unless-stopped
  #   environment:
  #     POSTGRES_USER: ${{POSTGRES_USER:-{project_name}}}
  #     POSTGRES_PASSWORD: ${{POSTGRES_PASSWORD:-secret}}
  #     POSTGRES_DB: ${{POSTGRES_DB:-{project_name}}}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
"""

    volumes_section = """
# volumes:
#   redis_data:
#   postgres_data:
""" if extra_services else ""

    # Ports
    ports = ""
    if template in ["webapp", "fastapi"]:
        ports = """
    ports:
      - "8000:8000"
"""

    content = f"""# Docker Compose - {project_name}
# Start: docker-compose up -d
# Logs: docker-compose logs -f
# Stop: docker-compose down

version: "3.8"

services:
  {project_name}:
    build: .
    container_name: {project_name}
    restart: unless-stopped
    env_file:
      - .env
{ports}
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    # depends_on:
    #   - redis
    #   - postgres
{extra_services}
{volumes_section}
"""
    create_file(project_dir / "docker-compose.yml", content)


def generate_dockerignore(project_dir: Path, project_name: str) -> None:
    """Generate .dockerignore"""
    content = f"""# Docker Ignore - {project_name}

# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
venv/
.venv/
env/
.env.local

# IDE
.idea/
.vscode/
*.swp
*.swo

# Tests
.pytest_cache/
.coverage
htmlcov/
.tox/

# Logs (mounted as volume)
logs/
*.log

# Data (mounted as volume)
data/
*.db
*.sqlite3

# Docker
Dockerfile
docker-compose*.yml
.docker/

# Documentation
docs/
*.md
!README.md

# AI configs (not needed in container)
_AI_INCLUDE/
.cursorrules
.cursorignore
CLAUDE.md
.windsurfrules
"""
    create_file(project_dir / ".dockerignore", content)


def generate_docker_files(project_dir: Path, project_name: str, template: str) -> None:
    """
    Create all Docker files
    
    Args:
        project_dir: Project path
        project_name: Project name
        template: Project template
    """
    print(f"\n{COLORS.colorize('Docker...', COLORS.CYAN)}")
    
    generate_dockerfile(project_dir, project_name, template)
    generate_docker_compose(project_dir, project_name, template)
    generate_dockerignore(project_dir, project_name)
