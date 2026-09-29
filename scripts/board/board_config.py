"""Single config module for the live board (#2). Every other board file imports from here.

The board is described in standards/22-live-board.md.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

# DEV fallbacks live here and nowhere else.
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765
_BOARD_SUBDIR = Path(".claude") / "board"
# Machine-wide list of projects that have a board — runtime data, outside every repository.
_DEFAULT_REGISTRY = Path.home() / ".cache" / "claude-board" / "projects.json"

HOST = os.environ.get("BOARD_HOST", _DEFAULT_HOST)
PORT = int(os.environ.get("BOARD_PORT", _DEFAULT_PORT))
REGISTRY = Path(os.environ.get("BOARD_REGISTRY", _DEFAULT_REGISTRY))
PROJECT_ID_PATTERN = r"^[0-9a-f]{10}$"

# A decision asked on the board: how long the Stop hook waits for the user's click.
# 0 turns the wait off. Capped below the Stop hook's 900 s timeout in the settings block.
_DEFAULT_DECISION_WAIT_S = 180
_MAX_DECISION_WAIT_S = 840


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default  # a typo in the env must not break every hook call


DECISION_WAIT_S = max(0, min(_int_env("BOARD_DECISION_WAIT", _DEFAULT_DECISION_WAIT_S),
                             _MAX_DECISION_WAIT_S))
DECISION_POLL_S = 1.0
CHOICE_MAX = 64
NOTE_MAX = 500
API_VERSION = 2  # 2 = one server for every registered project


def project_root(start: str) -> Path:
    """The MAIN checkout of the repository `start` is in, so every worktree of a
    project writes to one board. Outside a repository, `start` itself."""
    try:
        common = subprocess.run(
            ["git", "-C", start, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return Path(start)
    return Path(common).parent


def board_dir(cwd: str | None = None) -> Path:
    """BOARD_DIR wins; otherwise <main checkout>/.claude/board.
    CLAUDE_PROJECT_DIR is set for hooks; the CLI falls back to the current directory."""
    explicit = os.environ.get("BOARD_DIR")
    if explicit:
        return Path(explicit)
    start = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
    return project_root(start) / _BOARD_SUBDIR


EVENTS_FILE = "events.jsonl"
CONTROL_FILE = "control.json"
ACK_FILE = "control_ack.json"

AGENT_TOOL = "Agent"
TASK_TAG_PATTERN = r"\[(T-\d+)\]"
TASK_ID_PATTERN = r"^T-\d+$"
ROLE_PATTERN = r"^[a-z0-9][a-z0-9:_-]{0,63}$"


class TaskStatus:
    PLANNED = "planned"
    RUNNING = "running"
    AGENT_DONE = "agent_done"   # the agent returned; the orchestrator has not closed the task yet
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"
    REMOVED = "removed"
    NEEDS_DECISION = "needs_decision"  # Claude asked the user; the board shows the choices
    ALL = (PLANNED, RUNNING, AGENT_DONE, WAITING, DONE, FAILED, REMOVED, NEEDS_DECISION)


class AgentStatus:
    STARTING = "starting"
    RUNNING = "running"
    DONE = "done"
    DENIED = "denied"


class ControlAction:
    REMOVE_TASK = "remove_task"
    RESTORE_TASK = "restore_task"
    DISABLE_ROLE = "disable_role"
    ENABLE_ROLE = "enable_role"
    DECIDE = "decide"
    ALL = (REMOVE_TASK, RESTORE_TASK, DISABLE_ROLE, ENABLE_ROLE, DECIDE)


class DecisionChoice:
    """The two choices a decision offers when Claude named no options of its own."""
    CONTINUE = "continue"
    REJECT = "reject"
    DEFAULTS = (CONTINUE, REJECT)
