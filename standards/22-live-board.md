# 22 — The plan file (what replaced the live board)

> **History.** Until 03/10/2026 this standard described a local "live board": hooks wrote an event log into
> every project, a Python server showed it on `127.0.0.1`, and `board.py` wrote the plan. `claude-monitor`
> removed that board (its commit `86684df`, ADR-0002; last version: tag `archive/board-final`) for
> **cm-agent**, which only **observes** (sessions, subagents, Claude Code's own task tools) and offers Claude
> two tools, `monitor_status` and `monitor_note`. Nothing replaced the plan itself — mode, roles, routing,
> task ids, semantic status, commits. On 13/10/2026 the user chose a **local plan file** for that part
> (`docs/decision-log.md`); the board's launchers, hooks and CLI were removed from this repository.

## 1. What it is

One Markdown file per session, written by Claude through `/adyusuf:board-plan`:
`.claude/board/plan-<session id>.md` at the repository root. It holds the mode, the role set and one row
per task (id, task, role, branch, status, commit, note). It is an **extra record**: the status table in the
reply stays the deliverable (`00-working-method.md` §10).

## 2. Enabling it in a project

1. `.gitignore` carries `.claude/board/` (runtime data, never committed).
2. Nothing else: the skill ships in the `adyusuf` plugin; no hook, no server, no port.
3. **Migrating a project that had the old board:** remove the board hooks from its `.claude/settings.json`
   (every command that runs `scripts/board/board_*.py`) — merge, never overwrite: keep every other hook.
   They fail silently today (`|| true`) but still start a process on every tool call. Verify with
   `python3 -m json.tool .claude/settings.json`.

## 3. Permanent rules

- ⚠️ **The plan is written BEFORE the first piece starts.** Work that splits into 2+ pieces, or that starts
  an agent, is planned in the file first; each task's status moves with the work in the same turn
  (`running` → `agent_done` → `done` / `waiting` / `failed` / `needs_decision`), and a task that reached a
  branch carries its commit. *Reason (03/10/2026): a session ran 100+ tool calls and the plan was written
  afterwards in one batch, which is a log, not a plan.*
- ⚠️ **The file is an extra record, never the report.** The table in the reply stays the deliverable, and
  its figures come from the file, not from memory.
- ⚠️ **`agent_done` is not `done`.** Only the orchestrator closes a task, after auditing it (#28).
- ⚠️ **A decision recorded in the file steers the work; it is not an approval.** A `test`/`prod` promotion
  (#26), a deploy, deleting data or sending anything outward still needs the user's yes in the chat.
- **The role set is copied from the mode file**, not from memory (#27); roles are called as
  `adyusuf:<role>`.
- **No published board.** No Artifact dashboard or hosted page (`00-working-method.md` §10).
- **Progress percentages are not written.** They cannot be measured; states and commits can (§10b).

## 4. The monitor

When the claude-monitor agent is installed (`scripts/install.py`, `SETUP.md`), it records sessions, subagents
and Claude Code's task tools by itself; `monitor_note` adds one line per status change. Its design and data
model are in the `claude-monitor` repository (<https://github.com/adyusuf/claude-monitor>).
