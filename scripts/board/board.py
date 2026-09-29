"""CLI Claude uses to write the plan onto the live board (standards/22-live-board.md).

  B=~/.claude/scripts/board/board.py
  python3 $B plan --mode B --roles analyst,test-writer,doc-writer
  python3 $B add T-1 "F-063 trusted proxies" --branch fix/f063 --role developer
  python3 $B set T-1 --status waiting --note "tests later"
  python3 $B list
Agents are linked to a task by putting "[T-1]" in the Agent tool's description.
"""
from __future__ import annotations

import argparse
import re
import sys

from board_config import ROLE_PATTERN, TASK_ID_PATTERN, TaskStatus, board_dir
from board_store import append_event, fold, read_control, read_events


def _task_id(value: str) -> str:
    if not re.match(TASK_ID_PATTERN, value):
        raise argparse.ArgumentTypeError(f"task id must look like T-1, got {value!r}")
    return value


def _roles(value: str) -> list[str]:
    roles = [r.strip() for r in value.split(",") if r.strip()]
    bad = [r for r in roles if not re.match(ROLE_PATTERN, r)]
    if bad:
        raise argparse.ArgumentTypeError(f"invalid role name(s): {', '.join(bad)}")
    return roles


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="board")
    sub = p.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--mode", required=True)
    plan.add_argument("--roles", type=_roles, default=[])
    add = sub.add_parser("add")
    add.add_argument("id", type=_task_id)
    add.add_argument("title")
    add.add_argument("--branch", default="")
    add.add_argument("--role", default="")
    add.add_argument("--note", default="")
    st = sub.add_parser("set")
    st.add_argument("id", type=_task_id)
    st.add_argument("--status", choices=TaskStatus.ALL)
    st.add_argument("--note")
    st.add_argument("--branch")
    st.add_argument("--role")
    st.add_argument("--title")
    sub.add_parser("list")
    return p


def run(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    bdir = board_dir()
    if args.cmd == "plan":
        append_event(bdir, {"type": "plan", "mode": args.mode, "roles": args.roles})
    elif args.cmd == "add":
        append_event(bdir, {"type": "task_add", "id": args.id, "title": args.title,
                            "branch": args.branch, "role": args.role, "note": args.note})
    elif args.cmd == "set":
        fields = {k: getattr(args, k) for k in ("status", "note", "branch", "role", "title")
                  if getattr(args, k) is not None}
        if not fields:
            print("board set: nothing to change", file=sys.stderr)
            return 2
        append_event(bdir, {"type": "task_set", "id": args.id, **fields})
    elif args.cmd == "list":
        state = fold(read_events(bdir), read_control(bdir))
        for t in state["tasks"].values():
            print(f"{t['id']}\t{t['status']}\t{t['role']}\t{t['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
