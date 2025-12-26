"""
🦊 Fox Pro AI — Create Command

Create new AI-Native project from template.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..core.constants import COLORS


def run_create(
    name: str,
    path: Path,
    template: str = "bot",
    ai_targets: List[str] = None,
    docker: bool = True,
    ci: bool = True,
    git: bool = True,
) -> int:
    """Create new project."""
    from ..generators import (
        generate_ai_configs,
        generate_project_files,
        generate_scripts,
        generate_docker_files,
        generate_ci_cd,
        init_git_repo,
    )
    
    ai_targets = ai_targets or ["all"]
    project_dir = path / name
    
    if project_dir.exists():
        print(COLORS.error(f"Directory already exists: {project_dir}"))
        return 1
    
    print(f"\n🆕 Creating project: {COLORS.CYAN}{name}{COLORS.END}")
    print(f"   Template: {template}")
    print(f"   Path: {project_dir}\n")
    
    try:
        # Create directory
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate files
        generate_project_files(project_dir, name, template)
        generate_scripts(project_dir, name, template)
        generate_ai_configs(project_dir, name, ai_targets)
        
        if docker:
            generate_docker_files(project_dir, name, template)
        
        if ci:
            generate_ci_cd(project_dir, name)
        
        if git:
            init_git_repo(project_dir)
        
        print(f"\n{COLORS.GREEN}✅ Project created successfully!{COLORS.END}")
        print(f"\nNext steps:")
        print(f"  cd {name}")
        print(f"  ./scripts/bootstrap.sh")
        
        return 0
        
    except Exception as e:
        print(COLORS.error(f"Failed to create project: {e}"))
        return 1
