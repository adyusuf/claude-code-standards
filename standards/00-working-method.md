# Working Method — how to proceed with Claude

## 1. When a task arrives

1. **Classify it:** is this a bug fix, a new feature, a refactor or research? Each has a
   different output.
2. **Gather context:** the project's `CLAUDE.md` → its `docs/` if present → the relevant
   files. **Read** before editing.
3. **Confirm the scope:** what was requested is what gets done. It is neither narrowed
   nor widened. A "while I was in there" improvement is separate work → note it, propose
   it later.
4. **If something is unclear:** finish the independent parts; ask one clear question
   about the rest. If a wrong assumption would throw the work away, **ask first**.

## 2. Plan → approval → execute

- A small single-file change: just do it.
- **Multiple files / architectural impact / a schema change:** present a 5–10 line plan
  first — which file, what changes, why, what the risk is. Get approval.
- Split large work into **vertical slices**: each slice is a working, testable whole
  (API + UI + tests). Horizontal slices (all the DTOs first, then all the services) are
  forbidden.

## 3. Order of implementation

```
schema/model → API → contract test → client → e2e → documentation
```

- Stay compilable and runnable at every step. Never leave "I'll fix it later" behind.
- If work is left half-done, do not leave a `TODO(<name>): ...` — report it **explicitly
  in the message**.

## 4. Verification (mandatory before finishing)

- [ ] The build passes (`dotnet build` / `tsc --noEmit` / `expo doctor`)
- [ ] The relevant tests were run and passed
- [ ] The formatter and linter were run (`dotnet format`, `eslint --fix`, `prettier`)
- [ ] Backward compatibility was checked (was a field/endpoint deleted, did a type change)
- [ ] No secret or PII leakage
- [ ] Changed behaviour was written into the documentation / CLAUDE.md

**Never count a step you did not run as "passed".** If you could not run it, write why.

## 5. Reporting format

- What was done → which files → how it was verified → what was not done / what is left.
- If tests are red, show the output. Do not hide an error.
- No long prose; bullet points, with file paths as clickable links.

## 6. Context and token discipline

- Read the relevant section rather than the whole file (`offset`/`limit`, `grep`).
- Do not re-read a file you just edited in order to verify it.
- Do not paste long logs or output verbatim; summarise the relevant lines.
- Open a detailed standard only when you enter that topic.

### 6a. A `CLAUDE.md` is a rule index, not a decision journal

A `CLAUDE.md` enters context automatically in **every session** that works in that
directory: the cost of a line you add is paid not once but on **every session** that
reads the file. Its content therefore splits into two classes, and only one of them
belongs there:

| **Stays** in the active `CLAUDE.md` | **Moves** to `docs/<tier>-decision-log.md` |
|---|---|
| The rule statement, the prohibition, the gate, the flow | The rule's rationale, why the alternatives were eliminated |
| A trap warning (so it is not repeated) | The story of how it was discovered |
| The **name** of a test lock | That day's run record ("1017/1017 green") |
| The contract that holds today | The steps of a completed migration, `DROP` lists |

Every block that moves leaves behind **a rule statement + a link to the detail**. The
text is **moved verbatim, never paraphrased** — paraphrasing is the most common way to
lose it.

**This is tied to a gate.** A size ceiling is kept per file (ratcheted: the ceiling only
comes down) and the merge gate rejects growth. The rationale was measured: in one
project a `backend/CLAUDE.md` went from 48 KB to 378 KB in two months — 8x. **A one-off
cleanup does not solve this**; two months later you are back in the same place. What
solves it is the gate.

⚠️ When simplifying, rule loss is audited **mechanically** (never-do items, lines
carrying obligation or prohibition, backticked identifiers). The gate is verified by
mutation: an attempt that deletes a known rule **must** break the gate. If it does not,
the gate is decorative.

### 6b. The plugin/MCP surface counts against the token budget too

The second most expensive item after `CLAUDE.md` is **the set of enabled plugins**:
every plugin's skill and agent descriptions, its MCP tool names, and any session-start
hook output enter the system prompt — so they are re-read on **every request** and paid
again on every subagent call.

- The set of enabled plugins is **limited to the stack**. A plugin not used in the
  project is not left enabled; it is switched on in `settings.json` when the need arises.
- Before enabling a new plugin, measure its cost:
  `find <plugin> -name SKILL.md -exec awk '/^name:|^description:/' {} \; | wc -c`
- **An unauthorized MCP server is never left enabled** — it consumes prompt space and
  provides no capability.

Measurement: the median fixed prefix was 57,756 tokens, **18%** of total spend, having
grown 27,700 → 63,500 tokens over fourteen weeks. The description text alone of the 10
plugins that were switched off came to 45,333 characters.

⚠️ Measurement method: within a session's transcript, the sum of
`input + cache_creation + cache_read` on that session's **first** request is that
session's fixed prefix. The effect of a change is visible **only in a new session**; an
open session takes its configuration snapshot at the start (verified by measurement: in
the same session, the agent prefix before and after a change was identical).

## 7. Parallel session / worktree discipline

The same repository may be open in more than one Claude session:

- **Always** verify `git status` + `git diff --staged` before committing; stage only your
  own diff. `git add -A` is never used blindly.
- `git push --force` / `--force-with-lease` is not used unless the user explicitly asks.
- When checking out a branch, assume it may already be checked out in another worktree;
  if you get an error, use an isolated clone.
- Before long-running work: `git fetch`, and a `--ff-only` pull if you are behind.

### 7a. The live configuration is a symlink into this repository

`~/.claude` does not hold its own copy of the instruction text: `CLAUDE.md`,
`standards/`, `agents/`, `modes/`, `scripts/`, `docs/` and the `adyusuf` plugin
are **symlinks** into this repository's **main worktree**. The same text therefore
lives in exactly one place (rule #2 applied to the configuration itself), and
there is no twin to drift.

The consequence that matters: **the live configuration follows whatever branch the
main worktree has checked out.** So:

- The main worktree stays on **`prod`** — that is the configuration actually in
  force in every session.
- Work happens in a **separate `dev` worktree** (`git worktree add ../<repo>-dev dev`),
  so an unfinished rule never becomes live by accident.
- A change reaches the live configuration only by promotion `dev → test → prod`,
  which Claude performs and pushes through the gate. Never check out `dev` in the main worktree to "try something".

⚠️ **Our skills and commands are ONE plugin: `adyusuf`.** Every skill in `skills/`
and every command in `commands/` is invoked as `/adyusuf:<name>`, so ours are
never confused with plugins or third-party skills. The mechanism is Claude Code's
skills-dir plugin: `plugin/` holds `.claude-plugin/plugin.json` plus links back to
`../skills` and `../commands`, and one link makes it live —
`ln -s <main worktree>/plugin ~/.claude/skills/adyusuf`. A new skill or command on
`prod` is then live from the next session with no extra step. Check it with
`claude plugin details adyusuf`. There is no `~/.claude/commands` link and no
per-skill link under `~/.claude/skills` — either would load a second, unprefixed
copy. A real directory under `~/.claude/skills` is always third-party.

## 8. Work that requires approval (no exceptions)

- Deploying to production / merging to a production branch
- A `DROP` in a migration, deleting data, a bulk `UPDATE`
- `git push --force`, deleting a branch, moving a tag
- Sending anything outward: email, messages, social posts, triggering a webhook
- A new dependency, a new service, a new cost line
- A file containing user data leaving the machine

## 9. Making a rule permanent

When the user says "from now on, always do it this way":

1. Decide whether the rule belongs **to the project or to the global set**.
2. If it is the project's, `<project>/CLAUDE.md`; if it is global, `~/.claude/CLAUDE.md`
   or the relevant `standards/*.md`.
3. Write it with a **PERMANENT** label and **the reason**. A rule with no stated reason
   gets reverted by accident later.
4. Write it in the same turn; never say "I'll add it later".

## 14. Human actions are written down in one file (PERMANENT, all projects)

Anything only a **person** can or should do goes into `docs/human-actions.md` of that project
(template: [`templates/human-actions-md.md`](templates/human-actions-md.md)), **in the same turn**
the need is found. A line in the chat is not a record: it scrolls away and the next session never
sees it. *Reason: user decision 03/10/2026 — after a long run the open decisions, approvals and
manual steps were spread over the reply, `<TODO>` fields in documents and a "reported, not fixed"
list, and nobody could answer "what is waiting on me?" from one place.*

**What belongs in it** (one row each, with the exact command, menu path or the options):

- a decision Claude was not given — owners, rotation periods, domains, targets (RPO/RTO), accepting a gap or a risk;
- an approval that #8 or #26 reserves for the user — a deploy, a dependency, a new cost line, a push outside `dev`/`test`/`prod` or a PR, sending anything outward;
- a credential, token or account step — creating, rotating or entering one (Claude never handles secret values);
- a step in a console or UI that Claude cannot or must not drive — Vercel, Neon, Cloudflare, a password manager;
- a destructive step Claude was not allowed to run (a `DROP`, deleting data, removing a container or a database it left behind);
- anything that needs a real environment, device or network Claude does not have — and every claim that stayed **unverified** for that reason;
- a second person's review the process asks for;
- every item a report lists as "conflicts with the standards — reported, not fixed", and every `<TODO: ...>` left in a project document.

**How it is kept:**

1. One table row per item with an ID (`H-n`), what to do, why it is a person's, **what it blocks**, the date added and the exact way to do it. Items are never silently removed: they move to **Done** (with the date, who, and the evidence) or **Dropped** (with the person's reason).
2. Claude **adds** and **links**; it never closes an item on its own. Closing needs the person's word, or evidence that can be observed.
3. A document `<TODO: ...>` and a blocked task both name the `H-n` they wait for.
4. **Every final report** says how many items are open and links the file; an item that blocks the work being reported is named in the report, not only in the file.
5. No secret values, ever. A secret's source and owner belong in `SETUP.md` §3; this file points there.
6. The file is read **first** by anyone asking "what is waiting on me?" — and at the start of a session in a project that has one, Claude reads its open rows before proposing work that depends on them.

Not yet enforced by the gate (`gate-core.sh`'s project-documents step does not check for the file);
adding that check is a separate request.

## 10. Status reporting — during a long gate or run (PERMANENT, all projects)

When a gate, run or deploy takes minutes (merge gate, CI, test battery, publish/deploy
chain, migration), report it as a **short markdown table in the reply itself**.

⚠️ **No Artifact dashboard and no published board — they were REMOVED from the flow**
(user decision). Publishing a page, keeping it current at the same URL and
then repeating the same content as text cost a round of work per report and split the
record in two: the reply and the page disagreed as soon as one of them was updated. The
table in the conversation is the whole deliverable; the local live board (`22-live-board.md`) is an extra view only.

### 10a. What the table contains

One row per item that matters, and these columns:

| Column | What goes in it |
|---|---|
| The item | the job, named as the user would name it |
| State | done · running · blocked · did not run |
| Measured figure | the number **and the signal it was read from** (`983 tests`, `460/565 = 81.4%`, `exit 1`) |
| Waiting on | what has to happen next, or who owns it |

Keep it short. A twenty-row table is not a report, it is a dump — collapse what is
finished into one row and give the remaining work its own rows.

### 10b. Permanent rules

- ⚠️ **Every figure is MEASURED, not invented.** Name the signal it came from. If it
  cannot be measured, the row says "cannot be measured" — never a plausible-looking guess.
- ⚠️ **A step that did not run is reported as "did not run"**, never folded into a pass.
  The same rule as the gate's own (#25): a step that did not run did not pass.
- ⚠️ **An over-optimistic estimate is an ERROR and gets corrected.** If the figure drops
  once the breakdown exists, drop it and say why — never round quietly upward.
- ⚠️ **Never pipe a long run's output into something that buffers** (`tail`/`head`): no
  intermediate progress can be read until the job finishes. Write to a log file and read
  the table from that.
- ⚠️ **If a state is inferred rather than observed, SAY SO** ("inferred from the process
  count"). An indirect reading can be wrong and the reader must know which kind they have.
- **Give a time estimate for what is left**, split into what is yours and what is the
  user's. "Blocked" with no owner is not a status.
- The user sets the reporting interval; if they do not, report on state changes. Send a
  short line even on an unchanged turn — do not go silent.
- ⚠️ **A wait loop must not match itself.** `until [ "$(pgrep -f 'coverage.sh' | wc -l)"
  = 0 ]; do sleep 20; done` never finishes: the shell running the loop carries
  `coverage.sh` in its own command line, so `pgrep -f` counts it and the condition can
  never be met. It looks exactly like a job that is still running — and it was reported
  to the user as one, repeatedly, while the actual measurement had already finished
  Match on something the waiter cannot contain: `pgrep -f '[c]overage.sh'`,
  or `pgrep -x`, or wait on the writer's own PID (`kill -0 "$pid"`), or check the output
  file for its final line. **Before reporting "still running", verify with `ps` that a
  REAL process is there and not just the waiter.**

### 10c. Background task names show what they cost (PERMANENT, all projects)

Every background task and every delegated agent is named so the reader can tell at a
glance whether it is spending tokens. The prefix goes at the START of the name — the
`description` of a background `Bash`, an `Agent`, a `Workflow` or a scheduled task, and
the title of the board row that tracks it.

| The task | Prefix | Examples |
|---|---|---|
| **No model runs in it** — a shell process, wait loop, gate, test run, build, server | `FREE - ` | `FREE - dev gate (batch e2e4)`, `FREE - wait for other gates` |
| **A model runs in it** — a subagent, a workflow agent, `claude -p`, a loop or wake-up that re-enters the model | the **model name** | `Sonnet 5.5 - review T-56`, `Opus 5.5 - diagnose gate failure`, `Haiku 4.5 - classify failures` |

- ⚠️ **The prefix is the model that actually runs**, as the `model` of the call or the
  agent definition says — never a guess. An agent with no override inherits the parent's
  model: name that one.
- **FREE means no model runs INSIDE the task.** The notification that wakes the session
  when the task ends is a turn of the session, not of the task, and is not what the
  prefix describes.
- **A task that starts as FREE and later calls a model is renamed**, or split in two
  (rule #20 still applies: no autonomous loop without approval).
- An already-running task cannot be renamed; the rule applies to every task started
  after it. When asked "what is running and does it cost tokens", answer from the
  prefixes and verify with `ps` (§10b).

## 11. The failure cycle — EVERY test / gate / build run, not only e2e (PERMANENT, all projects)

Generalises `CLAUDE.md` #31 (which was written for e2e). The mistake it prevents: after
each failure the whole merge gate (tens of minutes: every tier plus the shared core) was re-run from the top,
repeatedly, although each fix could be proven by running only the step that failed.

1. **First run is FULL** and does not stop at the first failure. Read the WHOLE result before touching anything.
2. **Classify each failure** — product bug · stale test · fixture/data · environment · gate/tooling defect.
   One root cause often explains several red lines; find it before fixing line by line.
3. **Fix, then re-run ONLY what failed** (that step / test file / filter), plus what the fix could affect.
   Prefer the narrowest command that reproduces it (`dotnet test --filter`, `vitest run <file>`, one gate step,
   one script's own test file). Evidence that the narrow run reproduces the failure comes BEFORE the fix.
4. **Then ONE full run**, and only when the gate/merge script needs a single all-green pass to act. Repeat the
   full run again only if the fix touched something shared (gate core, config, base branch moved) — and write
   the reason in one line. Never use the full run as the way to "see if it works".
5. **A moving base is not a failure:** if `dev` moved, rebase and re-run the narrow check; do not restart the world.
6. **Never run two gates/test batteries in the same worktree at the same time** (shared ports, temp DB clusters,
   coverage dirs, branch checkout) — the second run invalidates the first.
7. **On a batch promotion to `test` the narrow re-run of step 3 is not enough:** after the fixes the FULL
   suite runs again before the gate. On the way to `dev` step 3 stands (`13-pr-and-review.md` §8).

## 12. Parallelism and reuse in test / coverage / gate runs (PERMANENT, all projects)

Why: a gate that runs every tier one after another, and re-runs the same suites in three places, costs tens of minutes and
then loses the promotion to a moving base. Speed-ups are allowed only under these rules:

1. **Parallelise by RESOURCE, not by count.** Tiers that use different resources (dotnet + a database cluster vs Node)
   run together. Tiers that fight for the same resource (several Node suites, each defaulting to "all cores") get an
   explicit **share** — `cores / number-of-parallel-tiers` workers each (`vitest` `VITEST_MAX_WORKERS`, `jest`
   `--maxWorkers`) — never the default, which oversubscribes the host and makes timing-sensitive tests flaky.
2. **A timing-sensitive suite stays alone.** If a suite already needs a raised timeout, serial file execution or
   retries, it is NOT run alongside other heavy work. Trading minutes for flaky timeouts is a loss (a run that hit an
   environment limit is invalid, `CLAUDE.md` #31).
3. **Each parallel leg writes to its OWN log and the logs are printed one after another afterwards** — never
   interleaved. A failed leg must be attributable at a glance; the exit status of every leg is collected (`wait <pid>`).
4. **Always keep a serial switch** (`COVERAGE_SERIAL=1` style) so a suspicious result can be reproduced without the
   parallelism as a variable.
5. **Never measure the same thing twice in one gate run.** A later step reuses an earlier step's report ONLY when a
   **stamp** written by the gate (the commit sha, right after it wipes the report dir) equals the current HEAD, the
   tracked tree is clean, and the report exists. No stamp / another commit / dirty tree / `…_REUSE=0` → measure from
   scratch. Reuse is **announced in the output**, and the decision function has its own two-way test (each refusal
   condition tested, mutants killed). A stale report taken for this commit's measurement is the "not measured but
   passed" defect (#29) — reuse without a stamp is forbidden.
6. **Two gates / test batteries never share a worktree** (§11.6) — parallelism is INSIDE one run, not between runs.
7. **Measure the gain before claiming it.** State the before/after wall-clock; a speed-up that was only reasoned about is
   reported as an estimate, not a result.

## 13. Tuning the delivery flow — cost, quality and speed (GUIDANCE, all projects)

Moved to [`23-delivery-flow-tuning.md`](23-delivery-flow-tuning.md) (§13 and the mandatory §13a flow-research task).
