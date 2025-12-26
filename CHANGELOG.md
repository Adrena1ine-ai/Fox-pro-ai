# Changelog

All notable changes to Fox Pro AI will be documented in this file.

## [4.0.0] - 2025-12-26

### 🚀 Major Release — Complete Architecture Rewrite

This release is a complete rewrite with unified architecture and clean codebase.

### ✨ Added

- **Unified `fox doctor` command** — one command for all operations
  - `--report` — show diagnostics (safe, no changes)
  - `--fix` — fix issues automatically
  - `--full` — full optimization (Deep Clean)
  - `--restore` — restore from backup
  - `--dry-run` — preview changes

- **Unified path format** — all external storage in `../project_fox/`
  - `data/` — heavy data files
  - `venvs/` — virtual environments
  - `logs/` — archived logs
  - `garbage/` — files for deletion
  - `manifest.json` — storage manifest

- **New `src/core/paths.py`** — single source of truth for paths
- **Integration tests** — full cycle testing
- **Clean modular architecture**:
  - `src/core/` — constants, config, paths, utilities
  - `src/scanner/` — token scanning
  - `src/optimizer/` — move, patch, clean
  - `src/mapper/` — trace maps, schemas
  - `src/generators/` — project generation
  - `src/commands/` — CLI commands

### 🔄 Changed

- Simplified CLI: 5 cleanup commands → 1 `fox doctor` command
- Unified external path format: 4 formats → 1 format
- Reduced codebase: ~15000 lines → ~8700 lines
- Improved token scanning with tiktoken support

### ❌ Removed

- `fox architect` — merged into `fox doctor --full`
- `fox cleanup` — merged into `fox doctor --fix`
- `fox migrate` — merged into `fox doctor`
- `fox health` — merged into `fox doctor --report`
- Legacy path formats (`_data`, `_venvs`, `_FOR_DELETION`, etc.)

### 🐛 Fixed

- Fixed config_paths.py fallback for new files
- Fixed duplicate import handling in AST patcher
- Fixed path inconsistencies between modules

---

## [3.6.0] - 2025-12-25

### Added
- Deep Clean with automatic code patching
- Fox Trace Map (AST-based context extraction)
- Garbage Clean (temp files removal)
- 240+ tests

### Changed
- Improved token scanning accuracy
- Better error messages

---

## [3.5.0] - 2025-12-20

### Added
- Project generator with 6 templates
- Multi-IDE support (Cursor, Copilot, Claude, Windsurf)
- Doctor command with auto-fix

---

## [3.0.0] - 2025-12-15

### Added
- Initial public release
- Basic project structure generation
- Cursor configuration support
