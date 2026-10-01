# 22 — The live board (per project, or for every project from the user settings)

A local page that shows, while Claude works, which task is where, which agent is
running on it, what finished — and lets the user **remove a task** or **switch an
agent off**. It is an **extra view**: the status table in the reply stays mandatory
(`00-working-method.md` §10). Nothing is published; the page is served on
`127.0.0.1` only.

**The application lives in its own repository, `claude-monitor`**
(<https://github.com/adyusuf/claude-monitor>, public). This document covers what stays
here: how it is brought up on a machine, how it is wired into projects and how it is used
while working. Its design, code and tests are in that repository (`docs/live-board.md`);
the skill is `skills/board-plan/`.

## 0. Bringing it up on a machine

1. Clone it once: `git clone https://github.com/adyusuf/claude-monitor.git ~/ClaudeCode/claude-monitor`
   (another location: set `CLAUDE_MONITOR_HOME`).
2. Nothing else. The hooks and the CLI are called at a stable path,
   `~/.claude/scripts/board/<script>.py`; the scripts there are **launchers**
   (`scripts/board/board_launcher.py`) that run the same-named script of the clone, with the same
   arguments and standard input. A project's committed `.claude/settings.json` therefore never
   changes when the application does, and updating the board is `git pull` in the clone.
3. **Not installed is harmless:** `board_hook.py` stays silent and exits 0, `board_ensure.py` prints one
   line with the clone command, and the command-line scripts exit 2 with it. A session is never blocked.

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

**One command:** from the repository, `python3 ~/.claude/scripts/board/board.py enable` does steps 1 and 2 below
and lists the project on the page. It is idempotent (a hook already there is left alone, everything else in
`settings.json` is kept, a file that is not valid JSON is never touched); commit the two files it changed.
Run it in the checkout whose files you will commit: from a linked worktree it writes THAT worktree's
`settings.json` and `.gitignore` (never the main checkout's) and lists the main checkout's board. Settings a
worktree does not have yet can be given locally without a commit through `.claude/settings.local.json` (git-ignored).
The steps below are what it does, for a project that wants to do it by hand.

**Every repository and folder, with nothing per project (user decision 01/10/2026):**
`python3 ~/.claude/scripts/board/board.py enable --user` merges the same block into the USER settings,
`~/.claude/settings.json` (backup in `~/.claude/backups/` first; other settings and hooks kept; invalid JSON
never touched). A session in any new repository or folder is then listed on the page by itself. A project that
also enabled the hooks fires each hook once (identical commands from two sources are de-duplicated — measured).
The home directory and `/` are never a board, and a board a hook creates is hidden from `git status` through the
repository's local `.git/info/exclude`. Both guards are in claude-monitor, so they apply once its clone is on a
version that has them. The per-project `enable` below stays for a project that wants its hooks committed.

**A project is listed as soon as its board is written** — by `board.py plan|add|set` or by any hook event —
not only by the `SessionStart` hook (`board_registry.register_if_missing`; not when `BOARD_DIR` overrides the
directory). Seen live 30/09/2026: ryan had ten tasks on a board and no `.claude/settings.json`, so no page
listed it. Without the hooks the page shows the tasks but no sessions, agents or costs: those need step 1.

1. Merge this block into the project's `.claude/settings.json` (committed):

```json
{
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_ensure.py\" || true" }] }],
    "PreToolUse": [{ "matcher": "Agent", "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "PostToolUse": [{ "matcher": "*", "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
    "SubagentStart": [{ "hooks": [{ "type": "command", "command": "python3 \"$HOME/.claude/scripts/board/board_hook.py\" || true" }] }],
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
   (single source: `board_config.py` in claude-monitor). The server's own log is
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

Moved with the application: each task can carry its commit(s) (`board.py set T-n --commit <sha>[,<sha>]`)
and the page shows whether every one is in `origin/dev`, `origin/test` and `origin/prod`, as of the
project's last `git fetch`. Reference: `docs/live-board.md` in the claude-monitor repository, §2b.

## 2c. Sessions, cost and context

Moved with the application. What binds you while working: **cost is measured from the transcripts, never
estimated** — a model without a price shows "cannot be measured", and an estimate (a projection, the
orchestrator's share of a task) always carries its basis. The status table in the reply quotes
`board.py list`, not the page's money figures from memory. Reference: `docs/live-board.md` in the claude-monitor repository, §2c.

## 2d. Sending work to a session

Moved with the application. What binds you while working: a task the user queues on the page reaches the
session as a hook notice (after its next tool call, or at `Stop`); a click on the board **steers the work,
it is not an approval** (§3). Reference: `docs/live-board.md` in the claude-monitor repository, §2d.

## 2e. App mode

Moved with the application: the page installs as its own window from the browser's Install menu, or opens
with `python3 ~/.claude/scripts/board/board_open.py`. Reference: `docs/live-board.md` in the claude-monitor repository, §2e.

## 2f. Task ids and where the CLI writes (T-28, 30/09/2026)

Several sessions write to one board, and ids were typed by hand: T-25 was taken by three
sessions and T-26 by two, so a later `add` silently replaced an earlier task's title. And
`board.py` finds the board from the working directory's repository, so a `set` typed in another
project's tree created a stray `.claude/board/` there.

- `board.py add auto "<title>"` reads the log and appends **under an exclusive lock**
  (`tasks.lock`), so parallel sessions cannot draw the same number; it prints the id.
- `add T-n` with an id that already exists is **refused** (exit 2) and writes nothing.
- A repository with no board (no `events.jsonl`) is **refused** for `plan`/`add`/`set` unless
  `--init` is given; `list` there prints nothing and creates nothing. A repository whose hooks
  are wired already has a board (the first hook event creates it), so nothing changes for it.

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

The hooks and the server cost **no tokens** while silent; a 7-task hour adds about 1,800–2,000 tokens of
reminders and notices (estimate), and a hook call takes about 65 ms. The per-item table moved with the
application: `docs/live-board.md` in the claude-monitor repository, §4.

## 5. Channels — pushing a task into an IDLE session

Moved with the application (measured 30/09/2026, T-24 phase 1). The rule that stays here: a board channel
server pushes **only text the board queued for a registered session**, never arbitrary text; hooks stay the
primary path and a channel only closes the idle-session gap. Reference: `docs/live-board.md` in the claude-monitor repository, §5.
