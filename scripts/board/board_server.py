"""Local board server: serves board.html, the folded state, and accepts control changes.

  python3 ~/.claude/scripts/board/board_server.py [--dir <project>/.claude/board]
Binds to localhost only. Standard library, no dependencies.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from board_config import (HOST, PORT, ROLE_PATTERN, TASK_ID_PATTERN, ControlAction,
                          board_dir)
from board_store import apply_control, fold, read_control, read_events

STATIC = {"/": ("board.html", "text/html; charset=utf-8"),
          "/board_ui.js": ("board_ui.js", "text/javascript; charset=utf-8")}
MAX_BODY = 4096


def validate_control(body: dict) -> tuple[str, str]:
    action, value = body.get("action"), body.get("value")
    if action not in ControlAction.ALL or not isinstance(value, str):
        raise ValueError("invalid action")
    task_actions = (ControlAction.REMOVE_TASK, ControlAction.RESTORE_TASK)
    pattern = TASK_ID_PATTERN if action in task_actions else ROLE_PATTERN
    if not re.match(pattern, value):
        raise ValueError("invalid value")
    return action, value


def make_handler(bdir: Path):
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
            if self.path in STATIC:
                name, ctype = STATIC[self.path]
                self._send(200, Path(__file__).with_name(name).read_bytes(), ctype)
            elif self.path == "/api/state":
                control = read_control(bdir)
                state = fold(read_events(bdir), control)
                state["control"] = {k: control[k] for k in ("removed_tasks", "disabled_roles")}
                self._json(200, state)
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/control":
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
                action, value = validate_control(json.loads(self.rfile.read(length)))
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})
            ctl = apply_control(bdir, action, value)
            self._json(200, {"version": ctl["version"]})

        def log_message(self, fmt, *args):  # keep request noise out; errors still go to stderr
            if args and str(args[1]).startswith(("4", "5")):
                super().log_message(fmt, *args)

    return Handler


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", help="board directory (default: from board_config)")
    args = p.parse_args()
    bdir = Path(args.dir) if args.dir else board_dir()
    server = ThreadingHTTPServer((HOST, PORT), make_handler(bdir))
    print(f"board: http://{HOST}:{PORT}  (data: {bdir})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
