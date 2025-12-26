"""
English localization for CLI
"""

MESSAGES = {
    # General
    "welcome": "FOX PRO AI",
    "goodbye": "Goodbye!",
    "invalid_choice": "Invalid choice",
    "continue": "Continue? (Y/n): ",
    "yes": "y",
    "no": "n",
    "success": "Success!",
    "error": "Error",
    "warning": "Warning",
    "info": "Info",
    
    # IDE selection
    "select_ide": "Which IDE will you use?",
    "ide_cursor": "Cursor (AI-first IDE)",
    "ide_copilot": "VS Code + GitHub Copilot",
    "ide_claude": "VS Code + Claude",
    "ide_windsurf": "Windsurf",
    "ide_all": "All (universal)",
    "ide_selected": "Selected:",
    "choose_1_to_n": "Choose (1-{n}) [{default}]: ",
    
    # Main menu
    "current_ide": "IDE:",
    "what_to_do": "What would you like to do?",
    "menu_create": "Create new project",
    "menu_cleanup": "Cleanup existing project",
    "menu_migrate": "Migrate project",
    "menu_health": "Health check",
    "menu_update": "Update project",
    "menu_change_ide": "Change IDE",
    "menu_exit": "Exit",
    "choose_0_to_n": "Choose (0-{n}): ",
    
    # Create project
    "create_title": "CREATE NEW PROJECT",
    "enter_project_name": "Project name: ",
    "invalid_project_name": "Invalid name! Use only: a-z, 0-9, _, -",
    "enter_project_path": "Path (Enter = current): ",
    "select_template": "Select template:",
    "template_bot": "Telegram Bot (aiogram)",
    "template_webapp": "Telegram Mini App",
    "template_fastapi": "REST API (FastAPI)",
    "template_parser": "Web Scraper",
    "template_full": "Full (all modules)",
    "template_monorepo": "Monorepo",
    "include_docker": "Include Docker? (Y/n): ",
    "include_ci": "Include CI/CD? (Y/n): ",
    "include_git": "Initialize Git? (Y/n): ",
    "creating_project": "Creating project...",
    "project_created": "Project created!",
    "project_path": "Path:",
    "next_steps": "Next steps:",
    "step_cd": "cd {path}",
    "step_bootstrap": "./scripts/bootstrap.sh",
    "step_activate": "source ../_venvs/{name}-venv/bin/activate",
    "step_env": "cp .env.example .env",
    
    # Cleanup
    "cleanup_title": "CLEANUP PROJECT",
    "enter_path": "Project path: ",
    "path_not_exists": "Path does not exist!",
    "analyzing": "Analyzing...",
    "no_issues": "No issues found!",
    "issues_found": "Found {n} issue(s):",
    "select_cleanup_level": "Select cleanup level:",
    "level_safe": "Safe (analysis only)",
    "level_medium": "Medium (backup + move venv)",
    "level_full": "Full (+ restructure)",
    "cleanup_complete": "Cleanup complete!",
    "cleanup_cancelled": "Cleanup cancelled",
    
    # Issues
    "issue_venv_inside": "venv inside project",
    "issue_site_packages": "site-packages in project",
    "issue_large_logs": "Large log files",
    "issue_large_data": "Large data folder",
    "issue_pycache": "__pycache__ folders",
    "issue_no_ai_config": "Missing AI config files",
    "issue_no_gitignore": "Missing .gitignore",
    
    # Migrate
    "migrate_title": "MIGRATE PROJECT",
    "migrating": "Adding Fox Pro AI to project...",
    "migrate_complete": "Migration complete!",
    "migrate_files_added": "Added files:",
    
    # Health check
    "health_title": "HEALTH CHECK",
    "checking": "Checking...",
    "check_passed": "PASSED",
    "check_failed": "FAILED",
    "check_warning": "WARNING",
    "all_checks_passed": "All checks passed!",
    "some_checks_failed": "Some checks failed",
    
    # Check items
    "check_venv_outside": "venv outside project",
    "check_no_venv_inside": "No venv inside project",
    "check_gitignore": ".gitignore exists",
    "check_env": ".env or .env.example exists",
    "check_requirements": "requirements.txt exists",
    "check_ai_include": "_AI_INCLUDE/ exists",
    "check_cursorrules": ".cursorrules exists",
    "check_cursorignore": ".cursorignore exists",
    "check_bootstrap": "bootstrap.sh exists",
    
    # Update
    "update_title": "UPDATE PROJECT",
    "current_version": "Current version:",
    "latest_version": "Latest version:",
    "already_latest": "Already up to date!",
    "updating": "Updating...",
    "update_complete": "Updated to v{version}!",
    
    # Dashboard
    "dashboard_deps_missing": "Dashboard dependencies not installed!",
    "dashboard_install": "Install with:",
    
    # CLI help
    "cli_description": "Fox Pro AI - Professional AI-Native Development Toolkit",
    "cli_create_help": "Create new project",
    "cli_cleanup_help": "Cleanup existing project",
    "cli_migrate_help": "Add toolkit to existing project",
    "cli_health_help": "Check project configuration",
    "cli_update_help": "Update project to latest version",
    "cli_dashboard_help": "Open Web Dashboard",
    "cli_arg_name": "Project name",
    "cli_arg_path": "Path to project",
    "cli_arg_template": "Project template",
    "cli_arg_level": "Cleanup level",
    "cli_arg_no_docker": "Without Docker",
    "cli_arg_no_ci": "Without CI/CD",
    "cli_arg_no_git": "Without Git",
    "cli_arg_host": "Host (default: 127.0.0.1)",
    "cli_arg_port": "Port (default: 8080)",
    "cli_arg_no_browser": "Don't open browser",
}
