"""Core module - constants, config, utilities."""

from .constants import VERSION, COLORS, TEMPLATES, IDE_CONFIGS, TOOL_NAME, FOX_BANNER
from .config import get_config, get_default_ide, set_default_ide, get_default_ai_targets
from .file_utils import create_file, make_executable, copy_template
from .paths import (
    get_external_root,
    get_external_data_dir,
    get_external_venvs_dir,
    get_external_logs_dir,
    get_external_garbage_dir,
    ensure_external_structure,
)
