"""CLI Claude uses to write the plan onto the live board (standards/22-live-board.md).

  B=~/.claude/scripts/board/board.py
  python3 $B plan --mode B --roles analyst,test-writer,doc-writer
  python3 $B add T-1 "F-063 trusted proxies" --branch fix/f063 --role developer
  python3 $B set T-1 --status waiting --note "tests later"
  python3 $B set T-1 --commit 3e2e5e2,5d3067f     # the Merge column reads these from git
  python3 $B set T-2 --status needs_decision --note "Split the PR?" --options "split|keep one"
  python3 $B list
Agents are linked to a task by putting "[T-1]" in the Agent tool's description.
"""
from __future__ import annotations

import argparse
import re
import sys

from board_config import (CHOICE_MAX, COMMIT_PATTERN, ROLE_PATTERN, TASK_ID_PATTERN, TaskStatus,
                          board_dir)
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


def _options(value: str) -> list[str]:
    options = [o.strip() for o in value.split("|") if o.strip()]
    if not options or any(len(o) > CHOICE_MAX for o in options):
        raise argparse.ArgumentTypeError(f"options: 'a|b|c', each 1-{CHOICE_MAX} characters")
    return options


def _commits(value: str) -> list[str]:
    commits = [c.strip().lower() for c in value.split(",") if c.strip()]
    if not commits or not all(re.match(COMMIT_PATTERN, c) for c in commits):
        raise argparse.ArgumentTypeError("commits: 'sha[,sha]', each 7-40 hex characters")
    return commits


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
    add.add_argument("--commit", dest="commits", type=_commits, help="the task's commit(s): 'sha[,sha]'")
    st = sub.add_parser("set")
    st.add_argument("id", type=_task_id)
    st.add_argument("--status", choices=TaskStatus.ALL)
    st.add_argument("--note")
    st.add_argument("--branch")
    st.add_argument("--role")
    st.add_argument("--title")
    st.add_argument("--commit", dest="commits", type=_commits, help="the task's commit(s): 'sha[,sha]'")
    st.add_argument("--options", type=_options, help="choices for a needs_decision task: 'a|b'")
    sub.add_parser("list")
    return p


def run(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    bdir = board_dir()
    if args.cmd == "plan":
        append_event(bdir, {"type": "plan", "mode": args.mode, "roles": args.roles})
    elif args.cmd == "add":
        append_event(bdir, {"type": "task_add", "id": args.id, "title": args.title,
                            "branch": args.branch, "role": args.role, "note": args.note,
                            **({"commits": args.commits} if args.commits else {})})
    elif args.cmd == "set":
        fields = {k: getattr(args, k) for k in ("status", "note", "branch", "role", "title", "options",
                                               "commits")
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
