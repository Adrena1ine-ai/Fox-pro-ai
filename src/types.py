"""
Types for Fox Pro AI
"""

from __future__ import annotations

from typing import TypedDict, Literal, TypeAlias, Protocol
from pathlib import Path


# ======================================
# Type Aliases
# ======================================

TemplateName: TypeAlias = Literal["bot", "webapp", "fastapi", "parser", "full", "monorepo"]
IDEName: TypeAlias = Literal["cursor", "vscode_copilot", "vscode_claude", "windsurf", "all"]
AITarget: TypeAlias = Literal["cursor", "copilot", "claude", "windsurf"]
CleanupLevel: TypeAlias = Literal["safe", "medium", "full"]
IssueSeverity: TypeAlias = Literal["error", "warning", "info"]
IssueType: TypeAlias = Literal["venv", "cache", "logs", "data", "config"]


# ======================================
# TypedDicts
# ======================================

class TemplateConfig(TypedDict):
    """Project template configuration"""
    name: str
    description: str
    modules: list[str]
    icon: str


class IDEConfig(TypedDict):
    """IDE configuration"""
    name: str
    icon: str
    files: list[str]
    ai_targets: list[AITarget]


class CleanupLevelConfig(TypedDict):
    """Cleanup level configuration"""
    name: str
    description: str
    actions: list[str]


class ProjectContext(TypedDict, total=False):
    """Project context for templates"""
    project_name: str
    date: str
    python_version: str
    template: TemplateName
    ai_targets: list[AITarget]
    include_docker: bool
    include_ci: bool
    include_git: bool


class IssueDict(TypedDict):
    """Project issue"""
    type: IssueType
    severity: IssueSeverity
    path: Path | None
    size_mb: float
    message: str
    fix_action: str


class HealthCheckResult(TypedDict):
    """Health check result"""
    passed: bool
    errors: int
    warnings: int
    checks: list[dict[str, str | bool]]


# ======================================
# Callable Types
# ======================================

class GeneratorFunc(Protocol):
    """Protocol for generator functions"""
    def __call__(self, project_dir: Path, project_name: str, *args: object) -> None:
        ...


class CommandFunc(Protocol):
    """Protocol for interactive commands"""
    def __call__(self) -> None:
        ...
