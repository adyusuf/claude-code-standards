# 22 — The live board (OPT-IN per project)

A local page that shows, while Claude works, which task is where, which agent is
running on it, what finished — and lets the user **remove a task** or **switch an
agent off**. It is an **extra view**: the status table in the reply stays mandatory
(`00-working-method.md` §10). Nothing is published; the page is served on
`127.0.0.1` only.

Code: `scripts/board/` · skill: `skills/board-plan/` · tests:
`scripts/tests/test_board.py`, `scripts/tests/board_ui.test.js`.

## 1. How it works

| Piece | What it does | Who drives it |
|---|---|---|
| Hooks (`board_hook.py`) | Record every `Agent` start and finish; deny an agent that is switched off, a call for a removed task, or a role outside the declared mode set; tell Claude about board changes | Claude Code, automatically |
| CLI (`board.py`) | Writes the plan: mode + role set, one row per task, the semantic status (`done`, `waiting`, `failed`) | Claude, per the `board-plan` skill |
| Server (`board_server.py`) | Serves the page and the folded state; takes the user's controls (same-origin JSON only, validated) | the user starts it |
| Page (`board.html`, `board_ui.js`) | Polls every 1.5 s; Turkish first, English switch; dates `dd/mm/yyyy` | the user's browser |

Data lives in `<main checkout>/.claude/board/` — the **main** checkout, so every
worktree of the project writes to one board. `events.jsonl` is append-only;
`control.json` holds the user's controls. Both are created `0600` and are runtime
data: add `.claude/board/` to the project's `.gitignore`.

Measured against Claude Code 2.1.281 (read from the binary, not the docs, whose
summary was wrong twice): the tool is `Agent`; a background call's `PostToolUse`
carries `tool_response.status == "async_launched"` and `agentId`, which binds the
call to its `SubagentStop.agent_id`; `UserPromptSubmit` carries `prompt`.

## 2. Enabling it in a project

1. Merge this block into the project's `.claude/settings.json` (committed):

```json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "Agent", "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "PostToolUse": [{ "matcher": "*", "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "SubagentStop": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "Stop": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }]
  }
}
```

   `|| true` is deliberate: a missing or broken hook must never block a session
   (a missing file exits 2, which Claude Code would read as a BLOCK). The hook
   itself also logs its errors to stderr and lets the call through.
2. Add `.claude/board/` to `.gitignore`.
3. Link the skill once per machine: `ln -s <repo>/skills/board-plan ~/.claude/skills/board-plan`.
4. Start a NEW session (hooks are read at session start), then run the server:
   `python3 ~/.claude/scripts/board/board_server.py` and open `http://127.0.0.1:8765`.
   `BOARD_DIR`, `BOARD_HOST`, `BOARD_PORT` override the defaults (single source:
   `scripts/board/board_config.py`).

## 3. Permanent rules

- ⚠️ **The board is an extra view, never the report.** The table in the reply
  stays the deliverable, and its figures come from `board.py list`, not memory.
- ⚠️ **No published board.** Artifact dashboards and hosted pages stay out of the
  flow (`00-working-method.md` §10); the board binds to localhost only.
- ⚠️ **`agent_done` is not `done`.** The hooks mark that an agent returned; only the
  orchestrator closes a task, after auditing it (#28).
- ⚠️ **A removed task or a switched-off agent is obeyed, never routed around.** No
  retrying a denied call under another role. A running agent for a removed task
  is stopped (`TaskStop`) — the hook cannot stop it, only block new calls.
- **The role set on the board is copied from the mode file**, not from memory; the
  hook denies anything outside it (#27).
- **Progress percentages are not shown.** They cannot be measured; states and
  elapsed time can (`00-working-method.md` §10b).

## 4. Cost (measured 29/09/2026)

The hooks and the server cost **no tokens** while silent. What enters the context:

| Item | Size | ≈ tokens (chars/4, estimate) | When |
|---|---|---|---|
| Skill description | 186 chars | ~46 | listed in every session |
| `SKILL.md` body | 2,380 chars | ~595 | loaded when planning |
| `board.py add` call | 191 chars | ~48 | once per task |
| `board.py set` call | 80 chars | ~20 | per status change |
| Board-change reminder (2 changes) | 203 chars | ~51 | when the user changes a control |
| Deny reason | 115 chars | ~29 | per denied agent call |

A 7-task hour ≈ 1,800–2,000 new tokens (estimate); every added token is then
re-read from cache on later calls. Hook latency: **65 ms median** per tool call
(20 runs, no-op `PostToolUse`).
