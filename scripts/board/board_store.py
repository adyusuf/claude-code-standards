"""Append-only event log + pure fold into board state, plus the control file."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from board_config import (ACK_FILE, CONTROL_FILE, EVENTS_FILE, AgentStatus,
                          ControlAction, TaskStatus)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_event(bdir: Path, event: dict) -> None:
    bdir.mkdir(parents=True, exist_ok=True)
    event = {"ts": now_iso(), **event}
    line = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
    # One O_APPEND write per event keeps parallel sessions from interleaving lines.
    fd = os.open(bdir / EVENTS_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def read_events(bdir: Path) -> list[dict]:
    path = bdir / EVENTS_FILE
    if not path.exists():
        return []
    events = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"board: skipping corrupt event line {n}: {exc}", file=sys.stderr)
    return events


def _task(state: dict, tid: str) -> dict:
    return state["tasks"].setdefault(tid, {
        "id": tid, "title": tid, "branch": "", "role": "", "note": "",
        "status": TaskStatus.PLANNED, "agents": [], "updated": None,
        "options": [], "decision": None, "commits": [],
    })


def _refresh_task_after_agent(state: dict, tid: str | None, ts: str) -> None:
    if not tid or tid not in state["tasks"]:
        return
    task = state["tasks"][tid]
    if task["status"] in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.REMOVED):
        return
    live = [a for a in task["agents"]
            if state["agents"][a]["status"] in (AgentStatus.STARTING, AgentStatus.RUNNING)]
    task["status"] = TaskStatus.RUNNING if live else TaskStatus.AGENT_DONE
    task["updated"] = ts


def fold(events: list[dict], control: dict | None = None) -> dict:
    state = {"mode": None, "roles": None, "tasks": {}, "agents": {}, "sessions": {},
             "last_event": None}
    by_agent_id: dict[str, str] = {}
    for ev in events:
        kind, ts = ev.get("type"), ev.get("ts")
        state["last_event"] = ts
        sid = ev.get("session")
        if sid:
            sess = state["sessions"].setdefault(sid, {"id": sid, "turn_open": True, "last": ts})
            sess["last"] = ts
            sess["turn_open"] = kind != "turn_stop"
        if kind == "plan":
            state["mode"] = ev.get("mode")
            state["roles"] = list(ev.get("roles", []))
        elif kind == "task_add":
            t = _task(state, ev["id"])
            for k in ("title", "branch", "role", "note", "commits"):
                if ev.get(k) is not None:
                    t[k] = ev[k]
            t["updated"] = ts
        elif kind == "task_set":
            t = _task(state, ev["id"])
            for k in ("status", "note", "branch", "role", "title", "options", "commits"):
                if ev.get(k) is not None:
                    t[k] = ev[k]
            t["updated"] = ts
        elif kind in ("agent_pre", "agent_denied"):
            key = ev["tool_use_id"]
            denied = kind == "agent_denied"
            state["agents"][key] = {
                "key": key, "agent_id": None, "type": ev.get("agent_type", ""),
                "task": ev.get("task"), "description": ev.get("description", ""),
                "background": bool(ev.get("background")), "session": sid,
                "status": AgentStatus.DENIED if denied else AgentStatus.STARTING,
                "reason": ev.get("reason"), "started": ts, "ended": ts if denied else None,
            }
            if ev.get("task") and not denied:
                t = _task(state, ev["task"])
                t["agents"].append(key)
                if not t["role"]:
                    t["role"] = ev.get("agent_type", "")
                _refresh_task_after_agent(state, ev["task"], ts)
        elif kind == "agent_post":
            a = state["agents"].get(ev["tool_use_id"])
            if not a or a["status"] == AgentStatus.DENIED:  # a denied spawn never comes alive
                continue
            if ev.get("launched") and ev.get("agent_id"):
                a["agent_id"] = ev["agent_id"]
                a["status"] = AgentStatus.RUNNING
                by_agent_id[ev["agent_id"]] = a["key"]
            else:
                a["status"], a["ended"] = AgentStatus.DONE, ts
            _refresh_task_after_agent(state, a["task"], ts)
        elif kind == "agent_stop":
            key = by_agent_id.get(ev.get("agent_id", ""))
            if key:
                a = state["agents"][key]
                a["status"], a["ended"] = AgentStatus.DONE, ts
                _refresh_task_after_agent(state, a["task"], ts)
    for tid in (control or {}).get("removed_tasks", []):
        if tid in state["tasks"]:
            state["tasks"][tid]["status"] = TaskStatus.REMOVED
    for tid, decision in (control or {}).get("decisions", {}).items():
        # A decision counts only for the question it answered: once Claude asks
        # again (a later task_set), the old answer no longer shows as the reply.
        task = state["tasks"].get(tid)
        if task and (task["updated"] or "") <= decision.get("ts", ""):
            task["decision"] = decision
    return state


# ---- control file (written by the board server, read by the hook) ----

def empty_control() -> dict:
    return {"version": 0, "removed_tasks": [], "disabled_roles": [], "changes": [], "decisions": {}}


def read_control(bdir: Path) -> dict:
    path = bdir / CONTROL_FILE
    if not path.exists():
        return empty_control()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"board: unreadable control file, treating as empty: {exc}", file=sys.stderr)
        return empty_control()
    return {**empty_control(), **data}


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(tmp, path)


def apply_control(bdir: Path, action: str, value: str,
                  choice: str | None = None, note: str | None = None) -> dict:
    ctl = read_control(bdir)
    if action == ControlAction.DECIDE:
        return _decide(bdir, ctl, value, choice, note)
    lists = {ControlAction.REMOVE_TASK: ("removed_tasks", True),
             ControlAction.RESTORE_TASK: ("removed_tasks", False),
             ControlAction.DISABLE_ROLE: ("disabled_roles", True),
             ControlAction.ENABLE_ROLE: ("disabled_roles", False)}
    if action not in lists:
        raise ValueError(f"unknown action: {action}")
    field, add = lists[action]
    items = set(ctl[field])
    items.add(value) if add else items.discard(value)
    ctl[field] = sorted(items)
    ctl["version"] += 1
    ctl["changes"] = (ctl["changes"] + [{"v": ctl["version"], "action": action,
                                         "value": value, "ts": now_iso()}])[-50:]
    atomic_write(bdir / CONTROL_FILE, ctl)
    return ctl


def _decide(bdir: Path, ctl: dict, tid: str, choice: str | None, note: str | None) -> dict:
    if not choice:
        raise ValueError("a decision needs a choice")
    ctl["version"] += 1
    decision = {"choice": choice, "note": note or "", "ts": now_iso(), "v": ctl["version"]}
    ctl["decisions"][tid] = decision
    ctl["changes"] = (ctl["changes"] + [{"v": ctl["version"], "action": ControlAction.DECIDE,
                                         "value": tid, "choice": choice, "note": note or "",
                                         "ts": decision["ts"]}])[-50:]
    atomic_write(bdir / CONTROL_FILE, ctl)
    return ctl


def _acks(bdir: Path) -> dict:
    ack_path = bdir / ACK_FILE
    try:
        return json.loads(ack_path.read_text(encoding="utf-8")) if ack_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def peek_changes(bdir: Path, session: str) -> list[dict]:
    """Control changes this session has not been told about yet — without marking them."""
    seen = _acks(bdir).get(session, 0)
    return [c for c in read_control(bdir)["changes"] if c["v"] > seen]


def unseen_changes(bdir: Path, session: str) -> list[dict]:
    """Control changes this session has not been told about yet; marks them as seen."""
    fresh = peek_changes(bdir, session)
    if fresh:
        acks = _acks(bdir)
        acks[session] = max(c["v"] for c in fresh)
        atomic_write(bdir / ACK_FILE, acks)
    return fresh
