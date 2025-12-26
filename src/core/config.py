"""
Configuration management
"""

from __future__ import annotations

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Any

from .constants import IDE_CONFIGS, TEMPLATES, CLEANUP_LEVELS


@dataclass
class Config:
    """Main Toolkit config"""
    version: str = "3.0.0"
    
    # Paths
    venvs_path: str = "../_venvs"
    data_path: str = "../_data"
    artifacts_path: str = "../_artifacts"
    
    # Defaults
    default_template: str = "bot"
    default_ide: str = "all"
    include_docker: bool = True
    include_ci: bool = True
    include_git: bool = True
    
    # Plugins
    plugins_dir: str = "~/.fox_pro_ai/plugins"
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> Config:
        """Load config from file"""
        if path is None:
            path = Path(__file__).parent.parent.parent / "toolkit.yaml"
        
        if not path.exists():
            return cls()
        
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            return cls(
                version=data.get("version", "3.0.0"),
                venvs_path=data.get("paths", {}).get("venvs", "../_venvs"),
                data_path=data.get("paths", {}).get("data", "../_data"),
                artifacts_path=data.get("paths", {}).get("artifacts", "../_artifacts"),
                default_template=data.get("defaults", {}).get("template", "bot"),
                default_ide=data.get("defaults", {}).get("ide", "all"),
                include_docker=data.get("defaults", {}).get("docker", True),
                include_ci=data.get("defaults", {}).get("ci", True),
                include_git=data.get("defaults", {}).get("git", True),
                plugins_dir=data.get("plugins_dir", "~/.fox_pro_ai/plugins"),
            )
        except Exception:
            return cls()
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save config to file"""
        if path is None:
            path = Path(__file__).parent.parent.parent / "toolkit.yaml"
        
        data = {
            "version": self.version,
            "paths": {
                "venvs": self.venvs_path,
                "data": self.data_path,
                "artifacts": self.artifacts_path,
            },
            "defaults": {
                "template": self.default_template,
                "ide": self.default_ide,
                "docker": self.include_docker,
                "ci": self.include_ci,
                "git": self.include_git,
            },
            "plugins_dir": self.plugins_dir,
        }
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def get_template(self, name: str) -> Optional[dict]:
        """Get template by name"""
        return TEMPLATES.get(name)
    
    def get_ide_config(self, name: str) -> Optional[dict]:
        """Get IDE config"""
        return IDE_CONFIGS.get(name)
    
    def get_cleanup_level(self, name: str) -> Optional[dict]:
        """Get cleanup level"""
        return CLEANUP_LEVELS.get(name)


# === Global state ===

_config: Optional[Config] = None
_current_ide: str = "all"
_current_ai_targets: list[str] = ["cursor", "copilot", "claude", "windsurf"]
_current_language: str = "en"


def get_config() -> Config:
    """Get global config"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def set_default_ide(ide: str, ai_targets: list[str]) -> None:
    """Set IDE for current session"""
    global _current_ide, _current_ai_targets
    _current_ide = ide
    _current_ai_targets = ai_targets


def get_default_ide() -> str:
    """Get current IDE"""
    return _current_ide


def get_default_ai_targets() -> list[str]:
    """Get AI targets for current IDE"""
    return _current_ai_targets.copy()


# === Language settings ===

def get_language() -> str:
    """Get current language code (always 'en' now)."""
    return "en"


def set_language(lang: str) -> None:
    """Set current language (no-op, English only now)."""
    pass


def is_first_run() -> bool:
    """Check if this is the first run (no user config exists)."""
    user_config_path = Path.home() / ".fox_pro_ai" / "config.yaml"
    return not user_config_path.exists()
