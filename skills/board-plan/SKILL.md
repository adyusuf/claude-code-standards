---
name: board-plan
description: Break a task into items in this session's plan file, route each to a role the active mode allows, and keep the plan in step with the work (status, commits, decisions). Use whenever work splits into 2+ pieces or starts an agent.
---

# board-plan — the session's plan file

## Why this exists

When several sessions and agents work at once — across more than one project — the
chat alone no longer shows who is doing what, what is waiting for you and where each
commit has landed. Agent start and stop are recorded elsewhere (the claude-monitor
agent, when installed), but nothing records the plan: which tasks exist, which role does
each one, and whether a returned agent's work was actually accepted. This skill keeps
that plan in one small file per session, so it survives a long session and a context
compaction, and you can open it at any time.

Contributions are welcome: https://github.com/adyusuf/claude-code-standards

Standard: `${CLAUDE_PLUGIN_ROOT}/standards/22-live-board.md`.

## 1. The file

`.claude/board/plan-${CLAUDE_SESSION_ID}.md` at the repository root — one file per
session, so parallel sessions never write the same file. `.claude/board/` is git-ignored
(runtime data); add the line to `.gitignore` if it is missing, and say so.

Create it before the first piece starts, with Write:

    # Plan — <short goal> (<dd/mm/yyyy>)
    Mode: <letter> · Roles: <role set copied from the mode file, or "none">

    | Id | Task | Role | Branch | Status | Commit | Note |
    |---|---|---|---|---|---|---|

Read the mode in the order `${CLAUDE_PLUGIN_ROOT}/modes/README.md` gives (session
selection → `.claude/mode` → B) and copy the role set from that mode's file — never from
memory. Mode A has no agents: `Roles: none`, the file tracks tasks only.

## 2. Tasks

One row per unit that merges to `dev` on its own (#26). Ids are `T-1`, `T-2`, … in this
file; the next id is one more than the highest in it. Route by
`${CLAUDE_PLUGIN_ROOT}/modes/role-selection.md`; a role outside the active mode is not
started — propose the mode change in one line (#27). Work you do yourself has the role
`me`.

## 3. Tag every agent call

Put the task id in the Agent `description`: `"[T-3] SMS pause sentence"`, and call the
role by its plugin name (`subagent_type: "adyusuf:<role>"`). The monitor records agents
by that description, so the tag links them to the row.

## 4. Keep the status current — in the same turn as the work

| When | Status |
|---|---|
| Not started | `todo` |
| You or an agent started it | `running` |
| The agent returned, not yet audited | `agent_done` |
| You audited the output and the task is closed | `done` |
| Blocked (review, the user, another task) | `waiting` + what, in Note |
| Failed and not retried now | `failed` + why, in Note |
| A question only the user can answer | `needs_decision` + the question, in Note |

`agent_done` means "the agent returned", not "the task is done" (#28). Record each
task's commit as soon as it exists (several: `<sha>, <sha>`).

**Asking the user:** set `needs_decision`, ask the same question in the chat
(`AskUserQuestion`), and move the row on when the answer comes. An answer never stands
in for an approval that needs the user's explicit yes (promotion, deploy, deletion,
sending outward) — that is asked for in the chat in its own words.

## 5. The monitor (optional)

If the `monitor_note` tool is available (the claude-monitor agent), send one line per
status change: `T-3 → done (abc1234)`. Without it — not installed, not connected, unreachable —
the file is the record, and that is not a problem to report.

## 6. The chat table still ships

The plan file is an extra record; the status table in the reply stays mandatory. Take
its figures from the file, not from memory. The on-screen task list stays too, with the
same items: phases, decision tasks, related work inserted, unrelated work queued — never
dropped (`${CLAUDE_PLUGIN_ROOT}/standards/00-working-method.md` §1a).
