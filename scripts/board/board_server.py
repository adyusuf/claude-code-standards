"""Local board server — ONE server for every project registered on this machine.

  python3 ~/.claude/scripts/board/board_server.py [--port N] [--dir <project>/.claude/board]
Serves board.html, the project list, each project's folded state, and takes the
user's controls. Binds to localhost only. Standard library, no dependencies.
Started automatically by board_ensure.py (SessionStart hook, standards/22-live-board.md).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from board_config import (API_VERSION, CHOICE_MAX, HOST, NOTE_MAX, PORT, PROJECT_ID_PATTERN,
                          REGISTRY, ROLE_PATTERN, TASK_ID_PATTERN, ControlAction, DecisionChoice)
from board_registry import load, project_id, summary
from board_store import apply_control, fold, read_control, read_events

STATIC = {"/": ("board.html", "text/html; charset=utf-8"),
          "/board_ui.js": ("board_ui.js", "text/javascript; charset=utf-8")}
MAX_BODY = 4096


def validate_control(body: dict) -> tuple[str, str]:
    action, value = body.get("action"), body.get("value")
    if action not in ControlAction.ALL or not isinstance(value, str):
        raise ValueError("invalid action")
    task_actions = (ControlAction.REMOVE_TASK, ControlAction.RESTORE_TASK, ControlAction.DECIDE)
    pattern = TASK_ID_PATTERN if action in task_actions else ROLE_PATTERN
    if not re.match(pattern, value):
        raise ValueError("invalid value")
    project = body.get("project")
    if project is not None and not (isinstance(project, str) and re.match(PROJECT_ID_PATTERN, project)):
        raise ValueError("invalid project")
    return action, value


CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def decision_fields(body: dict) -> tuple[str, str]:
    """The user's choice and optional note for a decide action, validated server-side (#7)."""
    choice, note = body.get("choice"), body.get("note", "")
    if not isinstance(choice, str) or not 0 < len(choice.strip()) <= CHOICE_MAX \
            or CONTROL_CHARS.search(choice):
        raise ValueError("invalid choice")
    if not isinstance(note, str) or len(note) > NOTE_MAX or CONTROL_CHARS.search(note):
        raise ValueError("invalid note")
    return choice.strip(), note.strip()


def boards(registry: Path, extra_dir: Path | None) -> dict:
    """Registered boards, plus the one named with --dir (kept for backward compatibility)."""
    found = load(registry)
    if extra_dir is not None:
        root = extra_dir.resolve().parent.parent
        entry = {"id": project_id(root), "name": root.name, "root": str(root),
                 "dir": str(extra_dir.resolve()), "registered": None}
        found.setdefault(entry["id"], entry)
    return found


def pick(found: dict, wanted: str | None) -> dict | None:
    """The requested board; without one, the most recently active (the pre-v2 behaviour)."""
    if wanted:
        return found.get(wanted)
    if not found:
        return None
    return max(found.values(), key=lambda e: summary(e)["last_event"] or "")


def make_handler(registry: Path | None = None, extra_dir: Path | None = None):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def do_GET(self):
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            if url.path in STATIC:
                name, ctype = STATIC[url.path]
                return self._send(200, Path(__file__).with_name(name).read_bytes(), ctype)
            if url.path == "/api/info":
                return self._json(200, {"version": API_VERSION})
            found = boards(registry, extra_dir)
            if url.path == "/api/projects":
                items = sorted((summary(e) for e in found.values()),
                               key=lambda s: s["last_event"] or "", reverse=True)
                return self._json(200, items)
            if url.path == "/api/state":
                entry = pick(found, (query.get("p") or [None])[0])
                if entry is None:
                    return self._json(404, {"error": "unknown project"})
                bdir = Path(entry["dir"])
                control = read_control(bdir)
                state = fold(read_events(bdir), control)
                state["control"] = {k: control[k] for k in ("removed_tasks", "disabled_roles")}
                state["project"] = entry["id"]
                state["decision_defaults"] = list(DecisionChoice.DEFAULTS)
                return self._json(200, state)
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if urlsplit(self.path).path != "/api/control":
                return self._json(404, {"error": "not found"})
            # Same-origin only: a foreign page cannot send JSON here without a preflight we never answer.
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                return self._json(403, {"error": "cross-origin request refused"})
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._json(415, {"error": "json required"})
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._json(400, {"error": "bad body size"})
            try:
                body = json.loads(self.rfile.read(length))
                action, value = validate_control(body)
                choice, note = decision_fields(body) if action == ControlAction.DECIDE else (None, None)
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})
            entry = pick(boards(registry, extra_dir), body.get("project"))
            if entry is None:
                return self._json(404, {"error": "unknown project"})
            ctl = apply_control(Path(entry["dir"]), action, value, choice, note)
            self._json(200, {"version": ctl["version"]})

        def log_message(self, fmt, *args):  # keep request noise out; errors still go to stderr
            if args and str(args[1]).startswith(("4", "5")):
                super().log_message(fmt, *args)

    return Handler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--dir", help="also show this board directory (optional)")
    args = p.parse_args(argv)
    extra = Path(args.dir) if args.dir else None
    server = ThreadingHTTPServer((HOST, args.port), make_handler(REGISTRY, extra))
    print(f"board: http://{HOST}:{args.port}  (registry: {REGISTRY})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
