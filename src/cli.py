#!/usr/bin/env python3
"""
🦊 Fox Pro AI v4.0 — CLI

Unified command-line interface.
One command to rule them all: fox doctor
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

from .core.constants import VERSION, COLORS, FOX_BANNER, TOOL_NAME


def print_banner():
    """Print Fox Pro AI banner."""
    print(FOX_BANNER)


def cmd_doctor(args: argparse.Namespace) -> int:
    """
    Doctor command — diagnose and optimize project.
    
    Modes:
        --report     Only show diagnostics (default)
        --fix        Fix issues automatically
        --full       Full optimization (Deep Clean + everything)
        --restore    Restore from external storage
    """
    from .commands.doctor import run_doctor
    
    project_path = Path(args.path).resolve()
    
    if not project_path.exists():
        print(COLORS.error(f"Project not found: {project_path}"))
        return 1
    
    return run_doctor(
        project_path=project_path,
        mode=args.mode,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_create(args: argparse.Namespace) -> int:
    """Create new project."""
    from .commands.create import run_create
    
    return run_create(
        name=args.name,
        path=Path(args.path) if args.path else Path.cwd(),
        template=args.template,
        ai_targets=args.ai or ["all"],
        docker=not args.no_docker,
        ci=not args.no_ci,
        git=not args.no_git,
    )


def cmd_status(args: argparse.Namespace) -> int:
    """Show project status."""
    from .commands.status import run_status
    
    project_path = Path(args.path).resolve()
    return run_status(project_path)


def cmd_menu(args: argparse.Namespace) -> int:
    """Run interactive menu."""
    from .menu import run_menu
    return run_menu()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="fox",
        description=f"🦊 {TOOL_NAME} v{VERSION} — Professional AI-Native Development Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"🦊 {TOOL_NAME} v{VERSION}",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # ═══════════════════════════════════════════════════════════
    # DOCTOR - Main command
    # ═══════════════════════════════════════════════════════════
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Diagnose and optimize project",
        description="🩺 Doctor — Diagnose and optimize your project for AI",
    )
    doctor_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project path (default: current directory)",
    )
    
    mode_group = doctor_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--report",
        dest="mode",
        action="store_const",
        const="report",
        default="report",
        help="Only show diagnostics (default)",
    )
    mode_group.add_argument(
        "--fix",
        dest="mode",
        action="store_const",
        const="fix",
        help="Fix issues automatically",
    )
    mode_group.add_argument(
        "--full",
        dest="mode",
        action="store_const",
        const="full",
        help="Full optimization (Deep Clean)",
    )
    mode_group.add_argument(
        "--restore",
        dest="mode",
        action="store_const",
        const="restore",
        help="Restore files from external storage",
    )
    
    doctor_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    doctor_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    doctor_parser.set_defaults(func=cmd_doctor)
    
    # ═══════════════════════════════════════════════════════════
    # CREATE - Create new project
    # ═══════════════════════════════════════════════════════════
    create_parser = subparsers.add_parser(
        "create",
        help="Create new AI-Native project",
        description="🆕 Create — Generate new project from template",
    )
    create_parser.add_argument(
        "name",
        help="Project name",
    )
    create_parser.add_argument(
        "--path",
        default=None,
        help="Base path (default: current directory)",
    )
    create_parser.add_argument(
        "-t", "--template",
        default="bot",
        choices=["bot", "webapp", "fastapi", "parser", "full", "monorepo"],
        help="Project template (default: bot)",
    )
    create_parser.add_argument(
        "--ai",
        nargs="+",
        choices=["cursor", "copilot", "claude", "windsurf", "all"],
        help="AI targets (default: all)",
    )
    create_parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Skip Docker files",
    )
    create_parser.add_argument(
        "--no-ci",
        action="store_true",
        help="Skip CI/CD files",
    )
    create_parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip Git initialization",
    )
    create_parser.set_defaults(func=cmd_create)
    
    # ═══════════════════════════════════════════════════════════
    # STATUS - Show project status
    # ═══════════════════════════════════════════════════════════
    status_parser = subparsers.add_parser(
        "status",
        help="Show project optimization status",
        description="📊 Status — Show project optimization metrics",
    )
    status_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project path (default: current directory)",
    )
    status_parser.set_defaults(func=cmd_status)
    
    # ═══════════════════════════════════════════════════════════
    # MENU - Interactive menu
    # ═══════════════════════════════════════════════════════════
    menu_parser = subparsers.add_parser(
        "menu",
        help="Run interactive menu",
        description="📋 Menu — Interactive project management",
    )
    menu_parser.set_defaults(func=cmd_menu)
    
    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        # No command — show menu
        print_banner()
        print(f"\nUsage: fox <command> [options]")
        print(f"\nCommands:")
        print(f"  {COLORS.CYAN}doctor{COLORS.END}  🩺 Diagnose and optimize project")
        print(f"  {COLORS.CYAN}create{COLORS.END}  🆕 Create new project")
        print(f"  {COLORS.CYAN}status{COLORS.END}  📊 Show project status")
        print(f"  {COLORS.CYAN}menu{COLORS.END}    📋 Interactive menu")
        print(f"\nExamples:")
        print(f"  fox doctor ./myproject --report")
        print(f"  fox doctor ./myproject --full")
        print(f"  fox create mybot --template bot")
        print(f"\nRun 'fox <command> --help' for more info.")
        return 0
    
    # Run command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print(f"\n{COLORS.warning('Cancelled by user')}")
        return 130
    except Exception as e:
        print(COLORS.error(f"Error: {e}"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
