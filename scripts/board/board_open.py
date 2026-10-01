#!/usr/bin/env python3
"""Launcher: runs board_open.py of the claude-monitor install (see board_launcher.py)."""
import sys

import board_launcher

if __name__ == "__main__":
    sys.exit(board_launcher.main("board_open.py"))
