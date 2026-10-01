"""Launcher for the live board, which lives in its own repository (claude-monitor).

The board's hooks and CLI are wired into `.claude/settings.json` files as
`python3 "$HOME/.claude/scripts/board/<script>"` — a stable path that stays valid in every project.
The scripts at that path are thin launchers: each runs the same-named script of the claude-monitor
install, in the same process, with the same arguments and standard input.

Where the install is: `$CLAUDE_MONITOR_HOME`, otherwise `~/ClaudeCode/claude-monitor` (the one default,
here). It is a git clone: `git clone https://github.com/adyusuf/claude-monitor.git <that path>`.

Not installed is never an error that stops Claude Code. The two scripts that run from hooks exit 0
(`board_ensure.py` says so in one line, which Claude Code adds to the session context; `board_hook.py`
stays silent, it runs on every tool call); the command-line ones exit 2 with the clone command.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HOME_ENV = "CLAUDE_MONITOR_HOME"
DEFAULT_HOME = Path("~/ClaudeCode/claude-monitor")
REPO_URL = "https://github.com/adyusuf/claude-monitor.git"
APP_SUBDIR = Path("scripts") / "board"

# What a launcher does when the install is missing: stay quiet (hook on every tool call), say one
# line on stdout (session start), or fail with the clone command (a command a person typed).
SILENT, HINT, FAIL = "silent", "hint", "fail"
ON_MISSING = {
    "board_hook.py": SILENT,
    "board_ensure.py": HINT,
    "board.py": FAIL,
    "board_open.py": FAIL,
    "board_server.py": FAIL,
}
EXIT_MISSING = 2


def monitor_home() -> Path:
    return Path(os.environ.get(HOME_ENV) or DEFAULT_HOME).expanduser()


def target(script: str) -> Path:
    return monitor_home() / APP_SUBDIR / script


def missing_text(script: str) -> str:
    return (f"claude-monitor is not installed at {monitor_home()} (the live board is off): "
            f"git clone {REPO_URL} {monitor_home()}   # or set {HOME_ENV}")


def main(script: str) -> int:
    """Runs the monitor's `script` in place of this process; returns only when it cannot."""
    path = target(script)
    if path.is_file():
        os.execv(sys.executable, [sys.executable, str(path), *sys.argv[1:]])
    mode = ON_MISSING.get(script, FAIL)
    if mode == HINT:
        print(f"Live board: {missing_text(script)}")
        return 0
    if mode == SILENT:
        return 0
    print(f"board: {missing_text(script)}", file=sys.stderr)
    return EXIT_MISSING
