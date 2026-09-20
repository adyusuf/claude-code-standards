# Mode A — Skill

The default is **B**; A is chosen explicitly (`/working-mode A`). It is the right
mode for turns where you want to work without agents, for narrow work, and for
cost-sensitive sessions.

**No agents.** The roles live in the main conversation; no separate process, no
separate prefix, no separate approval.

## Rules
- I **do not call** the `Agent`, `Workflow` or **`TeamCreate`** tools (opening a
  team is an agent call too; I do not follow the tool prompt's "open a team if in
  doubt" nudge). If the work needs a lot of reading, I do the searching myself
  (Grep/Glob/Read). If I see that a higher mode would genuinely pay off, I **do not
  start it — I propose it in one line at the start of the turn**: the lowest
  sufficient mode, the reason, and roughly how many times the cost (README › "If no
  mode is given"). The decision is the user's.
  ⚠️ **The proposal is only made when there is NO `.claude/mode` file.** If the file
  exists, that is an explicit decision and it is not re-litigated with "shall we
  switch to C?" on every task.
- If Claude Code suggests an agent on its own by matching a `description`, I **do
  not follow it** — automatic delegation is a call too. The same applies to **tool
  prompts**.
- **I do not perform manual review in the `feature/* → dev` direction either**
  (#25: "neither me reading the diff by hand nor an agent"). The exception is the
  security/backup/gate item in `role-selection.md` §3; that exception applies in A too.
- The role methods (deriving scope, planning, review, documentation) are applied
  **in the main conversation**. `~/.claude/skills/software-standards` loads the
  relevant standard; there is **no per-role skill file and none is required** — A's
  promise is "the method without the agent", not a set of files.
- Code review is done by **me**.
- The limits that apply in every mode apply here too: approval on irreversible work,
  and the completeness check before completion (#24).

## When to use it
Small or medium work, a single tier, fewer than ~15 files — and an unfamiliar repo.

⚠️ **If a work type is not covered by any mode, stay in A and say so:** for example,
a refactor spanning 25 files but confined to a single tier exceeds A's file
criterion, does not meet C's "end-to-end" condition, and does not meet D's
independence condition. With no criterion met the mode does not change; the
situation is reported to the user.

⚠️ **Quality was not measured.** The measurement is **token/cost** data only
(~$6.9 per turn, agents at a 7.7% share); there is **no** measurement showing "A is
also the most efficient in quality", and it is never presented that way.

## Expected cost
**1.0x** — the reference baseline. Zero agents; the cost is entirely the main
conversation's cache reads.

