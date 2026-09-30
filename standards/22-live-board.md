# 22 — The live board (OPT-IN per project)

A local page that shows, while Claude works, which task is where, which agent is
running on it, what finished — and lets the user **remove a task** or **switch an
agent off**. It is an **extra view**: the status table in the reply stays mandatory
(`00-working-method.md` §10). Nothing is published; the page is served on
`127.0.0.1` only.

Code: `scripts/board/` (auto-start, CLI, hooks, server, registry, state folding,
cost parsing, session views, API, icons, browser app) · skill: `skills/board-plan/` · tests:
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
| Cost (`board_cost.py`) | Parses Claude Code transcripts incrementally to read tokens and cost (prices from `board_config.py`); caches to avoid re-parsing | automatic, once per API call |
| Sessions (`board_sessions.py`) | Computes per-session/per-task cost, context use, projections (estimates carrying their basis) | automatic, once per API request |
| Controls (`board_api.py`) | Validates and applies user controls: task queue, skill run, mode switch, fail-closed; writes `.claude/mode` for selections | the user, via the page |
| App (`board_app.py`, `board_open.py`) | Web app manifest, drawn icons (no binary files), service worker, and the command to open as a Chrome app window | on-demand, or via browser Install menu |
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
3. The skill ships in the `adyusuf` plugin (`/adyusuf:board-plan`, `standards/00` §7a) — no link of its own.
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

## 2b. The Merge column

Each task can carry its commit(s): `board.py set T-n --commit <sha>[,<sha>]`. The page then
shows, per task, whether **every** one of them is in `origin/dev`, `origin/test` and
`origin/prod` — read live from the project's git (`scripts/board/board_merge.py`; the branch
names and the remote are in `board_config.py`). A branch that does not exist is left out; an
unknown commit counts as not merged. It is **as of the project's last `git fetch`** — the
board never fetches; branch tips are re-read at most every 10 s.

## 2c. Sessions, cost and context

**Cost:** measured from Claude Code transcripts (`board_cost.py`), **never estimated**.
The sole source of prices is `board_config.py` (pricing table cached 25/09/2026 from the
claude-api skill); a model not listed there shows **"cannot be measured"** in the UI, never
a guess. Tokens are read incrementally — each call parses only the bytes added since the
previous read, and a half-written last line waits for the next read. Subagent transcripts
may record output_tokens at stream start, so agent cost may be undercounted; the board
shows this as a note when subagents are active.

The hook records the paths to Claude Code's own transcript files (`transcript_path` on
`UserPromptSubmit`/`Stop`, `agent_transcript_path` on `SubagentStop`). Subagent transcripts
are found in `<session-transcript-path-without-.jsonl>/subagents/agent-<id>.jsonl`. The cost
cache holds one `Transcript` object per path (thread-safe) and updates in place.

**Agents:** every row of the Agent activity table carries its own tokens (in / out / cache
read / cache write) and cost, read from that agent's transcript (the `SubagentStop` path, else
`<session>/subagents/agent-<id>.jsonl`); a running agent shows its cost so far, read
incrementally. A row whose agent id or transcript is not known yet says "cannot be measured
yet" and is left out of the total row, which counts the measured agents and names how many
are not. The roles panel adds each role's cost. Rows for resumed / Workflow agents exist only
once T-2 opens them on `SubagentStart`, so their cost column depends on it.

**Context:** the last main-thread call's input + cache read + cache write tokens, set against
the model's window size. The board shows **"context warn" at ≥80%** — a UX reminder, never a
block. Compacting the context (`/compact`) is the user's own command in Claude Code; neither
Claude nor a hook can trigger it, and the board shows a warning, never a fake button.

**Sessions:** visible on the board for up to 24 hours after their last activity; state is
**busy** (from `UserPromptSubmit` to `Stop`) or **idle**. Sessions with no transcript file
yet show orchestration cost as **"cannot be measured"**; the agents row counts only measured
subagent files.

**Projections** (task and session): each is an **ESTIMATE** carrying its basis.
- **Task:** spent by its agents + (spent ÷ elapsed hours from the earlier of task start or
  first agent message) × the task's own remaining ETA minutes. Agents that ran before the
  task was marked running are real; their cost must not inflate the rate.
- **Session:** spent + $/h over the last 3600 s × remaining ETA hours of open tasks (those
  with an ETA; tasks without are counted and named, not included in the estimate).

| What is measured | Signal | When updated |
|---|---|---|
| Tokens (input, output, cache read, cache write 5m, cache write 1h) | `message.usage` in transcript | parsed by `/api/state` (page polls every 1.5 s) |
| Cost per model | pricing table in `board_config.py` | on every `/api/state`; only the bytes added since the last read are parsed |
| Task spent cost | all agents' transcripts by `agent_links` or [T-n] tag | per-session view, once per /api/state |
| Task projection | task start/first agent msg, ETA, spent, rate | estimated, per-session view |
| Session total cost | orchestration + all subagents | per-session view, once per /api/state |
| Session projection | $/h over last 3600 s, open task ETA | estimated, per-session view |
| Context use | main thread's last call's input+cache | per-session view, once per /api/state |

## 2d. Sending work to a session

**Queuing a task:** the user writes a task on the board (text field, max 1000 chars),
picks a session and taps **Send**. The control enters `control.json`'s `changes` list and
the hook delivers it via `PostToolUse` `additionalContext`:

| Session state | Delivery | Notes |
|---|---|---|
| Busy (turn in progress) | After the session's next main-thread tool call | same turn; subagent tool calls never consume it |
| Idle (turn ended) | Only inside the Stop hook's wait window (while a needs_decision question is unanswered, ≤180 s) or when the user types a new message | other sessions never see the notice |
| At Stop | The Stop hook blocks (`{"decision":"block","reason":…}`) and the turn continues with the queued task | no wait needed; the turn keeps going |

**Running a skill:** the page's skill picker sends `POST /api/control` `run_skill` to the
server (not `board.py`). The control text becomes `"invoke the /<skill> skill"` and
delivery follows the same rules as queued tasks.

**Switching mode:** the user picks a mode letter (A–E) and confirms. The control writes
`<project root>/.claude/mode` with the new letter and records a `mode_set` event with
`"by": "board"` in the event log. This **selection is the approval per #27** — no chat
approval needed. The mode-change notice goes to every session and asks Claude (not the user)
to re-declare the plan: `board.py plan --mode <X> --roles <that mode's role set>`.

**Validation (fail-closed):** every control is validated server-side before writing:
- `queue_task`: the target session must exist in the folded state
- `run_skill`: the skill must be in the list built from `~/.claude/skills/` (plain
  `<dir>/SKILL.md` and plugins' `<name>/skills/<dir>/SKILL.md` and
  `<name>/commands/<name>.md`)
- `set_mode`: the mode letter must match A–E
- Text and JSON fields are checked for control characters; queued task text is limited to
  1000 chars

**Unreached sessions:** `control.json` keeps the last 50 changes. A session that never runs
a hook again (e.g. it crashes before the next tool call) can have its queued tasks fall out
of the list. A queued item is bound to ONE session id: another or a new session never receives
it. This is **by design**: the control file is a delivery channel, not permanent storage; the
user re-sends from the board. The panel lists what is still undelivered per session ("queued").

**Irreversible work:** a queued task or mode switch are not approval. A task that says
"deploy to prod" or "run DROP" still needs explicit chat approval — the board is a local
file channel, not an approval channel. Link: the existing §3 rule "A board decision steers
the work; it is not an approval."

## 2e. App mode

The board is a web app: it can be installed via the browser's **Install** menu to run as its
own window, or opened via `python3 ~/.claude/scripts/board/board_open.py` which:
1. Ensures the server is up (via `board_ensure.py`, no blocking)
2. Tries to open it in a Chrome app window (`--app=<url>`; no tabs, no address bar)
3. Falls back to the default browser if Chrome is not found or the command fails

**Web app manifest** (`/manifest.webmanifest`): name, short name, theme colour, background
colour, scope, display mode, and icons.

**Icons:** drawn at 192×192 and 512×512 PNG (via `board_app.py`), and as SVG. They show the
theme colour (blue) with three white columns (the board's three-column layout). **No binary
files in the repository** — icons are generated on request from the server.

**Service worker** (`/sw.js`): caches nothing. The board is ephemeral and always fresh; a
stale cache would be worse than a reload.

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
- **Cost and projections are measured or labelled.** An unpriced model shows
  **"cannot be measured"** in the cost column, never a guess. A projection always
  carries its basis (the rate and ETA it rests on) so the figure is not opaque.

## 4. Cost (measured 29/09/2026)

The hooks and the server cost **no tokens** while silent. What enters the context:

| Item | Size | ≈ tokens (chars/4, estimate) | When |
|---|---|---|---|
| Skill description | 186 chars | ~46 | listed in every session |
| `SKILL.md` body | 2,380 chars | ~595 | loaded when planning |
| `board.py add` call | 191 chars | ~48 | once per task |
| `board.py set` call | 80 chars | ~20 | per status change |
| Board-change reminder (2 changes) | 203 chars | ~51 | when the user changes a control |
| Queued task notice (measured 30/09/2026) | 303 chars (with text "add a changelog entry for T-23") | ~76 | when a task is queued for the session |
| Mode-change notice (measured 30/09/2026) | 346 chars (mode C) | ~87 | when mode is switched on the board |
| Deny reason | 115 chars | ~29 | per denied agent call |
| Decision reminder (one decision with a note) | 253 chars | ~63 | per decision |
| Auto-start line (`SessionStart`) | 69 chars | ~17 | once per session |

A 7-task hour ≈ 1,800–2,000 new tokens (estimate); every added token is then
re-read from cache on later calls. Hook latency: **65 ms median** per tool call
(20 runs, no-op `PostToolUse`).
