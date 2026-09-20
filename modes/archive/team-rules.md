# The Agent Teams modes (X · Y · Z) — shared rules

> X/Y/Z are the **team** equivalents of B/C/D. The roles and the audit regime are the
> same; what changes is an agent's **lifetime and communication**. Role selection is
> still [`role-selection.md`](../role-selection.md) (all of §0-§8 applies in X/Y/Z
> too); this file only records the team-specific differences.

## 0. ⛔ PRECONDITION — X/Y/Z CANNOT be started today

For two separate reasons; the mode does not open until both are resolved.

**(a) The role definitions do not carry the team tools.** The nine roles have closed
`tools:` allowlists and none of them contains `SendMessage`, `TaskList`, `TaskGet`,
`TaskUpdate` or `TaskCreate` (`grep -n "^tools:" agents/*.md` → 9/9 closed,
`SendMessage` → 0 matches). A teammate comes up but **nobody hears it**: its plain
text is invisible, it cannot mark its task `completed`, and the leader assumes it is
idle and assigns the same work a second time.
→ Without extending the roles, X/Y/Z **does not open**. And extending them also
enlarges the agent permissions in B/C/D, because those are the same files.

✅ **Decision: the tools are not being added now.** X/Y/Z already sits behind a plan
gate; adding them today would grant B/C/D agents permissions they will not use and gain
nothing in return. They are added **on the day the plan gate opens**, and that day it is
also decided whether to extend the nine roles in place or to open separate role files
for teams (such as `qa-team.md`) and preserve the permission separation — the latter
turns 9 files into 18 and creates a twin maintenance burden.
⛔ Until that decision is made, §0(a) stands: the mode does not open.

**(b) The feature is disabled.** The activation gate is an experimental flag or
environment variable **and** there is an account-plan gate. The teammate-mode setting
does not enable the feature — it only says **how** it would run. **There is no `/teams`
slash command.**

⚠️ In a desktop session the `Agent` schema carries no `team_name`/`name`/`mode`; the
binary has conditional text for exactly this: *"The run_in_background, name, team_name,
and mode parameters are not available in this context."*

## 1. The mechanism (verified from the Claude Code binary)

| | Subagent (B/C/D) | Teammate (X/Y/Z) |
|---|---|---|
| Lifetime | One shot | **Lives for the session**, drops to idle after each turn |
| Communication | Reports only to me | **`SendMessage`** — its plain-text output is invisible to the others |
| Coordination | None — I sequence it | **A shared task list** (`TaskList`/`TaskGet`/`TaskUpdate`/`TaskCreate`; `owner`, `status`, `blockedBy`) |
| Parallelism | Turns started in the same message | **Real concurrency** |
| Nesting | An agent cannot call an agent | **A teammate cannot call a teammate** — but it **can call a synchronous subagent** (§2.3) |
| Persistence | — | Does **not** live across sessions; the team/task state **persists on disk** |

Spawn: the `Agent` tool with `team_name` + `name` (+ `mode`). A setting provides the
default teammate model, which the leader overrides per agent with `model`.

⚠️ **The shared `team/` memory is NOT the team mechanism** — it is a memory scope shared
with **all users** working in the project directory, and it already works independently
of X/Y/Z. The binary's own restriction applies: **no secrets or API keys are written to
shared memory** (the same direction as global #3).

## 2. What is closed to a teammate (each verified separately)

### 2.1 Permission mode — ⛔ a teammate STOPS on an irreversible action

A teammate is born as a separate process and **the leader's permission mode passes to
its command line**: `bypassPermissions` → `--dangerously-skip-permissions`,
`acceptEdits` → `--permission-mode acceptEdits`. So a dialogue **may not** appear to the
user at all.

**Rule:** when a teammate reaches an irreversible action (deploy, `DROP`, force push,
sending anything outward, a `test`/`prod` promotion) it **does not do it**: it stops,
reports to the leader via `SendMessage`, and the leader asks the user. This is written
**explicitly** into the teammate's spawn prompt — it does not come from the environment.

⚠️ If the leader session is in `bypassPermissions`/`acceptEdits`, X/Y/Z **does not
open**; the approval gate is already absent and a teammate cannot inherit it.

### 2.2 Autonomous loops — ⛔ a teammate does not set up cron or Monitor

A teammate cannot create a durable cron, but it **can create a session-scoped one**
(`durable:false` = in-memory, dies with the session) and it can open a `Monitor`. Global
#20 (no autonomous loop without asking) applies unchanged in X/Y/Z: **a teammate does
not use `CronCreate`/`Monitor`/`ScheduleWakeup`**; if one is needed it reports to the
leader.

### 2.3 Synchronous subagents — counted and reported

From the binary: *"In-process teammates cannot spawn background agents. Use
run_in_background=false for synchronous subagents."* So the **teammate → synchronous
subagent path is open**.

**Rule:** a teammate does not call subagents. If work requires one, it reports to the
leader. Reason: `role-selection.md`'s invariant that "role selection lives in one
place", and keeping cost visible in one hand — a turn run from inside a teammate does
not appear on my cost line, and the threshold is exceeded without ever firing.

## 3. I am the leader — tasks are **assigned**, not claimed

A teammate's built-in instruction **encourages** claiming work (*"Claim an available
task using TaskUpdate (set `owner` to your name), or wait for leader assignment"*) and
the runner behaves that way too (`Claimed task #`). **There is no switch to turn this
off** — this rule only holds if it is written into the spawn prompt.

**Implementation (without it, the mode does not open):**
- This line goes **verbatim** into every teammate's spawn prompt: *"Task claiming: do
  not assign `owner` to yourself via `TaskUpdate`. Only the leader assigns. Do not open
  new tasks with `TaskCreate` — send any scope-change proposal to the leader via
  `SendMessage`."*
- The leader **leaves no unowned `pending` task**; unassigned work is kept locked with
  `blockedBy`.

⚠️ Reason: otherwise the `developer` teammate claims the `qa` task when its turn comes
and **reviews its own code** — C/Y's principle that "the producer does not audit its own
work" collapses silently.

## 4. Auditing — IDENTICAL to `role-selection.md` §7, only the carrier differs

| §7 concept | Its form in a team |
|---|---|
| Hand-back | The task is **reopened** (`TaskUpdate`: status → `pending`, owner → the producer) + a `SendMessage` with "what is missing · with what evidence · what to fix · closing evidence" |
| Closure | A claim of "done" is not enough; the auditor **re-runs** the verification and writes the raw result |
| Ceiling | The same task is sent back at most **twice**; then it stops, the open findings are listed and I am informed |
| The completeness-check block | The teammate closes its report with this block and **sends it via `SendMessage`** |

⚠️ **The block always goes to the LEADER as well** (`to: team-lead`). Only a **summary**
of a teammate-to-teammate DM reaches the leader, not its content — so if `qa` sends its
finding straight to `developer` and they close it between themselves, §7's "the
orchestrator does not swallow the block" guarantee and #28's "closed / still open"
distinction are left unevidenced.

⚠️ Because teammates live a long time, "I'll look at it later" becomes easier here: the
**number of open findings** is reported at the end of the turn, and if it is not zero it
is visible.

## 5. Concurrent editing — two teammates never enter the same file

This is the price of "real concurrency". One of two rules is chosen and **written down**
at the start of the turn:

- **File separation:** the path group each teammate will touch is defined in its task;
  intersecting work goes to a single teammate.
- **Isolation:** `isolation: "worktree"` in the `Agent` call — the teammate works in its
  own worktree and merging belongs to the leader.

⚠️ Without such a rule, the second `Edit` writes without seeing what the first one
wrote; #26's "each task its own commit, traceable" order turns into one tangled working
tree.

## 6. Task-list discipline

- Every task belongs to **exactly one role** and carries **acceptance criteria**.
- Dependencies are written with `blockedBy`, not verbally.
- When a task closes, **its evidence is added as a comment** (the command run + its result).
- ⚠️ The list does **not replace** the start-of-turn and end-of-turn report in
  `role-selection.md` §6 — the list is the team's internal state, the report is yours.

## 7. Cost

| Mode | Estimated multiplier | Its counterpart |
|---|---|---|
| **X** | ~1.5–2.5x | B (~1.15–1.35x) |
| **Y** | ~3–6x | C (2.5–4x) |
| **Z** | ~6–12x | D (4–8x) |

⚠️ **None of the multipliers has been measured**; they are derived from the B/C/D
estimates.
⚠️ **The mechanism rationale is unverified too.** "A teammate re-reads its context every
turn / burns money while idle" is **an untested hypothesis**, and the binary suggests
otherwise: a teammate drops to **idle** after each turn (it produces no turns until a
message arrives) and compacts its history when needed. Until a measurement exists, those
sentences are not used as a justification for a decision.

**Measurement:** `python3 ~/.claude/scripts/session-cost.py <session-id>` — it measures
from the transcript rather than estimating. It is run on the first real X/Y/Z turn and
written into the measurement ledger in `role-selection.md` §8.

**The thresholds** are in §8's X/Y/Z rows (two-stage: a warning at half, a stop at the
full figure).

## 8. When a team, when a subagent?

| Situation | Choose |
|---|---|
| The work is **one shot** (investigate, report, done) | **B/C/D** |
| The roles will **pass data back and forth turn by turn** | **X/Y/Z** |
| Repeating the same work across N modules | **E** (Workflow) |
| Work that must continue after the session closes | **None** — a teammate does not live across sessions |

⚠️ **The lowest sufficient mode**: if X is enough, Y is not proposed; if B is enough, X
is not proposed.

## 9. End of session and handover

Teammates die, but **the team and the task list persist on disk**. Therefore:

- **No task is left `in_progress`** before the session closes — it returns to either
  `completed` or `pending`; otherwise it appears as an unowned "in progress" in the next
  session.
- The handover note carries **the state of the task list**.
- The same `team_name` cannot be reused — a new session takes a new name.

## 10. Rules outside the mode that do not loosen in X/Y/Z either

Approval on irreversible work (§2.1) · the `test`/`prod` promotion belonging to the user
(#26) · the completeness check before "done" (#24) · secrets staying out of the repo and
out of shared memory (#3) · autonomous-run approval (#20, §2.2).
**Teammates cannot take these over on my behalf.**
