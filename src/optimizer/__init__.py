"""Optimizer module - move, patch, clean."""

from .heavy_mover import move_heavy_files, restore_files
from .ast_patcher import patch_project, revert_patches
from .garbage_cleaner import scan_garbage, clean_garbage
