#!/usr/bin/env python3
"""
🦊 Fox Pro AI v4.0

Entry point for running without installation.
Usage: python main.py doctor ./project --report
"""

from src.cli import main

if __name__ == "__main__":
    exit(main())
