---
name: board-plan
description: Break a task into live-board items, route each to a role the active mode allows, and keep the board in step. Use in projects that enable the live board, whenever work splits into 2+ pieces or starts an agent.
---

# board-plan — plan onto the live board

The board records agent start/finish **by itself** (hooks). This skill covers what
the hooks cannot know: the task list, the routing and the semantic status.
Standard: `standards/22-live-board.md`. Below, `B` is
`python3 ~/.claude/scripts/board/board.py`.

## 1. Read the mode, then declare it
Read the mode in the order `modes/README.md` gives (session selection →
`.claude/mode` → B). Copy the role set from that mode's file — never from memory.

    B plan --mode <letter> --roles <comma-separated role set>

Mode A has no agents: declare `--roles ""` and the board tracks tasks only.

## 2. Break the work down
One item per unit that merges to `dev` on its own (#26). Ids are `T-1`, `T-2`, …

    B add T-1 "<short title>" --branch <branch> --role <role that will do it>

Route by `modes/role-selection.md`. A role outside the active mode is not started;
propose the mode change in one line (#27).

## 3. Tag every agent call
Put the task id in the Agent `description`: `"[T-3] SMS pause sentence"`.
Untagged agents still appear under "Agent activity" but link to no task.

## 4. Keep the semantic status current
The hooks set `running` and `agent_done`. Only you set the rest:

| When | Command |
|---|---|
| You audited the agent's output and the task is closed | `B set T-n --status done` |
| Blocked (review, the user, another task) | `B set T-n --status waiting --note "<what>"` |
| Failed and not retried now | `B set T-n --status failed --note "<why>"` |

`agent_done` means "the agent returned", not "the task is done" (#28).

**Record each task's commit** as soon as it exists: `B set T-n --commit <sha>` (several:
`<sha>,<sha>`). The page's Merge column then shows where it has landed — dev / test / prod —
read from git, so nobody has to write merge notes by hand.

**Asking the user:** `B set T-n --status needs_decision --note "<question>" --options "a|b"`
(no `--options` → Continue / Reject), ask the same question in the chat, then end the
turn. The Stop hook waits for the click (`BOARD_DECISION_WAIT`, default 180 s); the
answer arrives as a board change — apply it and move the task out of `needs_decision`.
A board answer is never an approval for promotion, deploy, deletion or sending outward:
those still need the user's yes in the chat (`standards/22-live-board.md` §3).

## 5. Obey the board's controls
A board change reaches you as a system reminder after your next tool call. Skip
removed tasks and stop their running agents (`TaskStop`); never retry a denied
agent call under another role.

## 6. The chat table still ships
The board is an extra view; the status table in the reply stays mandatory. Take
its figures from `B list`.
