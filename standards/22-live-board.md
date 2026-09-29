# 22 — The live board (OPT-IN per project)

A local page that shows, while Claude works, which task is where, which agent is
running on it, what finished — and lets the user **remove a task** or **switch an
agent off**. It is an **extra view**: the status table in the reply stays mandatory
(`00-working-method.md` §10). Nothing is published; the page is served on
`127.0.0.1` only.

Code: `scripts/board/` · skill: `skills/board-plan/` · tests:
`scripts/tests/test_board*.py`, `scripts/tests/board_ui.test.js`.

**One page for every project:** `http://127.0.0.1:8765`, one tab per project. It
comes up by itself when a Claude session starts in any project that enables the board.

## 1. How it works

| Piece | What it does | Who drives it |
|---|---|---|
| Hooks (`board_hook.py`) | Record every `Agent` start and finish; deny an agent that is switched off, a call for a removed task, or a role outside the declared mode set; tell Claude about board changes | Claude Code, automatically |
| CLI (`board.py`) | Writes the plan: mode + role set, one row per task, the semantic status (`done`, `waiting`, `failed`) | Claude, per the `board-plan` skill |
| Auto-start (`board_ensure.py`) | On `SessionStart`: registers the project, starts the server if nothing answers, says where the board is — never blocks a session | Claude Code, automatically |
| Registry (`board_registry.py`) | The machine-wide list of boards: `~/.cache/claude-board/projects.json` (id, name, path — runtime data, outside every repository) | the auto-start |
| Server (`board_server.py`) | ONE server for every registered project: the tabs, each project's state, the user's controls (same-origin JSON only, validated) | the auto-start |
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
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_ensure.py\" || true" }] }],
    "PreToolUse": [{ "matcher": "Agent", "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "PostToolUse": [{ "matcher": "*", "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "SubagentStop": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "Stop": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true", "timeout": 900 }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }]
  }
}
```

   `|| true` is deliberate: a missing or broken hook must never block a session
   (a missing file exits 2, which Claude Code would read as a BLOCK). The hook
   itself also logs its errors to stderr and lets the call through.
2. Add `.claude/board/` to `.gitignore`.
3. Link the skill once per machine: `ln -s <repo>/skills/board-plan ~/.claude/skills/board-plan`.
4. Open `http://127.0.0.1:8765`. A running session picked up a newly added
   `.claude/settings.json` without a restart (measured 29/09/2026, Claude Code 2.1.281:
   its Stop hook delivered a board decision in the same session), but `SessionStart` —
   the auto-start — only runs when a session starts. If the board stays silent, start a
   new session. The server is started by the `SessionStart` hook and keeps
   running after the session ends; after a reboot the next session starts it again.
   By hand, if ever needed: `python3 ~/.claude/scripts/board/board_ensure.py < /dev/null`.
   `BOARD_DIR`, `BOARD_HOST`, `BOARD_PORT`, `BOARD_REGISTRY` override the defaults
   (single source: `scripts/board/board_config.py`). The server's own log is
   `~/.cache/claude-board/server.log`.
5. If the auto-start reports an **older** board server on the port (one project per
   server, before 29/09/2026), stop that process once; the next session starts the
   one-for-all server.

## 2a. Decisions asked on the board

When a task needs the user's answer, Claude puts the question on the board:
`board.py set T-n --status needs_decision --note "<question>" [--options "a|b"]`.
The page shows the choices (without options: **Continue / Reject**) and a note field.

| When the user clicks | How it reaches Claude |
|---|---|
| While Claude is working | as a reminder after its next tool call |
| After Claude ended its turn with an open question | the `Stop` hook waits up to `BOARD_DECISION_WAIT` seconds (default **180**, `0` = no wait, capped at 840 — the Stop hook's `timeout` is 900) and, on a click, keeps the turn going with the decision |
| After the wait ran out | at the start of the next turn |

While the Stop hook waits, the session shows as busy; a message typed in the chat
queues until the wait ends. Only a decision prolongs a turn; other board changes wait
for the next one. In modes C/D/E a subagent's tool call never consumes a notice meant
for the orchestrator.

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
- ⚠️ **A board decision steers the work; it is not an approval.** Anything that needs
  the user's explicit approval in the chat — `test`/`prod` promotion (#26), a deploy,
  deleting data, sending anything outward — still needs it there. The board is a local
  file channel; a click on it never stands in for that approval.
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
| Decision reminder (one decision with a note) | 253 chars | ~63 | per decision |
| Auto-start line (`SessionStart`) | 69 chars | ~17 | once per session |

A 7-task hour ≈ 1,800–2,000 new tokens (estimate); every added token is then
re-read from cache on later calls. Hook latency: **65 ms median** per tool call
(20 runs, no-op `PostToolUse`).
