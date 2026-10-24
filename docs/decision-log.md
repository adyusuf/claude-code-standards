# Decision log — the rationale behind the rules

> Per `standards/00-working-method.md` §6a, the active `CLAUDE.md` is a **rule
> index**, not a decision journal. A rule's rationale, how it was discovered, the
> measurement record and the text of retired rules all move here. The active file
> links to this one with `§<rule number>`.
>
> The move roughly halved the size of `CLAUDE.md`. Rule loss was audited with
> `scripts/md-rule-gate.py`.
>
> There are two parts: the **§N** headings hold text removed from the active file
> entirely; the **Appendix** at the end holds the original, fuller wording of lines
> that were shortened in the active file (look there for clauses dropped during
> shortening).

## §21-23 — retired rules

These three numbers are retired: two were delegated to #27 (the operating mode now
decides who performs review and how agent calls are approved) and one was removed
(browser verification of live UI does not require asking first; the measure is the
work itself — a pure logic or backend change does not need a browser).

The numbers themselves are preserved so that references elsewhere do not break.

## §24 — Self-administered completeness check before saying "done"

Additional checklist items that were shortened out of the active file:

- Were **tests** (#8), **build/lint/format**, and where relevant the
  **SETUP.md/.env.example/secret inventory** updates (#16) actually run, or is this
  "it probably works"? (#15 already forbids that — here it additionally enters the
  checklist.)
- Say "done" only after passing the check; do not narrate the check to the user
  step by step, fold its result briefly into the report (e.g. "X, Y, Z changed;
  tests pass; A is not done yet because …").

**Why:** on one task the user had to ask "is anything missing?" four or five times
in a row, and every time something genuinely was missing — meaning the "done"
report was not trustworthy. The check is required to run **automatically on every
task**, without the user having to ask.

**How to apply:** for very small, single-line changes the checklist is enough as a
one- or two-second mental pass — no separate step or report is needed. For
multi-step, multi-file work, or anything where "done" leads to a PR or a merge, the
checklist is run deliberately.

**Extended 04/10/2026 — the request list (`standards/00-working-method.md` §4a).**
The check above runs at the END; the same incident showed that is too late on a
multi-part task, because the root cause was mistaking "every gate is green" for
"every requested item was done". These items lived only in a machine-local copy of
the global rules and were carried over when this repository replaced that copy: the
request list written before the work, the evidence-or-reason definition of done, the
status labels, the six forbidden patterns, and scope narrowing as the user's decision.
The three other sections of that copy were **not** carried over, because this rule
set decided them the other way on purpose: per-call approval before an agent (#27
replaced it with the mode as the approval), the published Artifact board (retired —
see the board entries further down; the status table of `standards/00` §10 instead), and no gate on `dev`
(#25 runs the shared gate on every promotion).

The scripted-edit pattern paid for itself on the day it was carried over: a
PowerShell mutation test wrote through `[IO.File]` with a relative path, which .NET
resolves against its own working directory rather than PowerShell's — the assert on
"nothing matched" fired instead of a silent no-op on the wrong checkout.

## §25 — Merging to `dev` is fast; heavy gates run on promotion

> ⛔ **SUPERSEDED — this section records the original design, not the active rule.**
> The active #25 runs the SHARED STEP SET at **every** promotion, `dev` included:
> formatter, typecheck, build, unit tests, coverage per codebase, secret scan,
> dependency CVE, SAST, backward-compatibility scan, the guidance-file gates, and a
> missing-e2e-spec check. Only **running** e2e is deferred to the `prod` gate (#33).
> Everything below describes the earlier "light gate on `dev`" arrangement and is
> kept because the reasoning is why the rule moved, not because it still applies.

**Why:** the instruction was to skip review and gates when merging to `dev` so that
work moves without losing time. `dev` is an integration branch and publishes
nothing outward; the real place for a quality gate is the `test`/`prod` promotion,
where code leaves for the outside world. This rule narrows #19: those scans now
apply in the `test`/`prod` direction, and #27 (the mode) decides who performs review.

Additional detail shortened out of the active file:

- The **pre-commit gitleaks** hook stays enabled even on `dev` because it is local,
  takes a second, and a leaked secret cannot be undone (it requires rotation).
- In modes D/E the restriction applies to **agents** as well: the gate-paired roles
  `security` and `coverage-auditor` are not invoked in the `dev` direction, only on
  promotion — otherwise the gate ban would come back through an agent. `data` is
  the exception and the opposite holds: work touching the schema passes through
  `data` **before** it is merged to `dev`, because a migration cannot be undone.
- Only **build + fast unit tests** run on `dev` (seconds; the cost of a broken
  `dev` is higher). If they are red the merge does not happen and it is reported
  with its output per #15.
- On the `dev → test` and `test → prod` promotions nothing is skipped — and the
  promotion is performed with the user's approval anyway.

### The e2e spec check warns, and blocks nothing

`dev → test` used to FAIL when behaviour changed and no e2e spec was touched.
Two things were wrong with that. It put the entire e2e backlog in front of an
**integration** merge, so work with no e2e dimension at all was stopped by it.
And it asked for specs to be written at the wrong moment: #33 requires a spec to
be verified against a **deployed test environment**, so a spec written to satisfy
a `dev → test` gate is written blind — and a blind spec is the thing #31 later
classifies as a "stale spec" failure.

So the check is now a **warning in both directions**. What keeps it from becoming
a silent hole is that the gap is not dropped, only moved: **step 2 of the
`test → prod` gate writes every missing spec before the suite runs, and that gate
does block.** The warning is also printed on every single run, with the changed
files listed, so the backlog stays in front of whoever runs the gate.

Pinned by `MissingE2eSpecOnlyWarns` in `scripts/tests/test_gate_core_fixes.py` —
three tests, holding both halves together: the promotion is not blocked, and the
gap is still said out loud. Mutation-verified: putting `bad` back in place of
`warn` fails two of the three.

Text updated in the same turn (#14) in all five places that had claimed
"blocking on test": `CLAUDE.md` #25, `standards/13-pr-and-review.md` §4,
`standards/11-playwright.md`, `scripts/README.md`, and the header comment of
`scripts/gate-core.sh`. The contradiction was found because a project had already
made the change locally on the strength of the user's decision, while the shared
rule text still said the opposite — which is exactly the state #25 forbids, since
a project may add a step but never remove one. The right fix was the rule text,
not reverting the project.

### The five fixes, and how each one is pinned

The shared core had been carrying bugs that made it report **GREEN while whole
tiers went unchecked**. They were found by running the gate in every repository
that carries it rather than by reading it. The worst one: a repository with a
`.slnx` solution, 673 backend tests, a **red build** and two high-severity
advisories printed GATE GREEN, because stack detection came out `dotnet=0` and
not one .NET step ran — and a promotion had already been made on that basis.

| # | The bug | Why it was silent |
|---|---|---|
| 1 | `ls ./*.sln` did not match the newer `.slnx` | detection returned 0, so the tier was skipped, not failed |
| 2 | `ls ./**/*.csproj` is one level deep without `globstar` | a project at `src/Api/Api.csproj` was invisible |
| 3 | Node detection was root-only while .NET looked deeper | a repo whose JS lives in `frontend/` skipped the rule-#16 document step entirely |
| 4 | The solution was detected but never passed to `dotnet` | `MSBUILD : error MSB1003` in place of a build — four of five .NET repos keep their solution below the root |
| 5 | `npm test -- --run` was passed unconditionally | `--run` is vitest's flag; jest fails on it for a reason unrelated to the tests |

And one that was not a code bug but a policy hole: **`coverage` could be listed
in `ACCEPTED_GAPS`**, and several projects had done exactly that, so their gates
printed GREEN while nothing measured coverage at all. Rule #29 grants the
threshold no exceptions and says a project cannot override it, so the core now
refuses that one step by name (`NEVER_ACCEPTABLE`) and stays INCOMPLETE.

**Mutation record** (`scripts/tests/test_gate_core_fixes.py`, 16 tests). Each
fix was reverted and the suite re-run; a fix whose revert changes nothing is not
protected by a test:

| Reverted | Result |
|---|---|
| the whole detection block, back to its pre-fix three lines | 5 failed — `.slnx`, nested csproj, nested `package.json`, the dotnet target, `-warnaserror` |
| `NEVER_ACCEPTABLE` guard → `if false` | 1 failed — coverage was accepted and the gate went green |
| the vitest condition → `if true` | 1 failed — jest received `--run` |
| `dotnet build ${SLN:+"$SLN"}` → `dotnet build` | 1 failed — the nested solution was not the target |
| `package.json` search → root only | 1 failed — `node=0` for a repo whose JS is in `web/` |

One mutation did NOT fail at first: dropping `.slnx` from the `ls` alone changed
nothing, because the `find` fallback also matches it. That is the fix being
belt-and-braces, not a test gap — reverting the block as a whole does fail the
`.slnx` test, and that whole block is what actually shipped before.

**A defect in the test file itself**, found while consolidating it: its
`if __name__ == '__main__'` guard sat in the MIDDLE of the file, above three of
its five classes. Run as `python3 <file>` it executed **2 of 12 tests and printed
OK**, because the classes below the guard were never defined. pytest imports the
module rather than running `__main__`, so pytest saw all 12 and the hole stayed
invisible. The guard now sits at the bottom, with a warning comment saying why;
run directly, the file reports 16 of 16. The general lesson is the one this
section keeps repeating: **a green result from a runner that never loaded the
checks is the failure mode to look for**, in a gate or in a test file.

### ⚠️ A false claim I made about this, and how it happened

While doing the above I reported two things that were **not true**, and both are
worth keeping because the cause is a habit, not an accident:

1. *"The fixes were propagated to the project copies but the canonical copy was
   never updated — the single source was the stalest copy."*
2. *"The tests I reported writing for those fixes do not exist anywhere on disk."*

Both were wrong. The canonical **had** been updated and the test file **did**
exist — all of it committed and pushed to `origin/dev` from a different
worktree. What I actually measured was a **local worktree that was 8 commits
behind**, and I read that as the state of the repository. I compounded it by
searching the filesystem (`find`, `grep`) for the test file, which cannot see a
commit that is not checked out here, and by comparing against the `prod`
worktree, which is pinned to `prod` by design and is *supposed* to be behind.

**How to apply:** before reporting that something is missing, stale or
un-propagated in a repository, `git fetch` and name the ref that was measured.
"It is not in my working tree" and "it does not exist" are different claims, and
in a repository with several worktrees pinned to different branches the first one
is nearly worthless on its own. Compare **blob ids against a named remote ref**,
never files against whatever a checkout happens to hold.

A second trap from the same hour, with the same shape — a measurement that was
silently wrong rather than absent: in **zsh**, an unbraced `"$var:something"`
is parsed as a `:s` history modifier on `$var`, so
`git rev-parse "origin/$b:scripts/gate-core.sh"` in a loop resolved a **mangled
ref** and returned a blob id for a path nobody asked about. Every repository
came back "STALE" and the output looked entirely plausible. Brace it —
`"origin/${b}:scripts/gate-core.sh"` — in every shell one-liner that joins a
variable to a `:`-separated path.

**Still open:** nothing compares a project's committed `gate-core.sh` against the
canonical one. Today that comparison had to be done by hand, and doing it by hand
is exactly where the two false claims above came from. A check that walks the
known repositories and diffs blob ids against a named ref would have answered it
in one line, and it is not built. *(Closed since: `scripts/twin-drift.sh` does
this comparison and `merge-gate.sh` runs it.)*

### The dependency-CVE step failed open

The .NET step was `dotnet list … --vulnerable | grep -qi 'critical\|high'` and a
pass for everything else. On 24/09/2026 the NuGet vulnerability feed hung on a
network that black-holes IPv6; the process was killed after 13 minutes and the gate
printed `✓ dotnet packages`. With no `dotnet` on the machine the step did not appear
in the report at all — neither passed nor skipped.

The step now runs under `GATE_CVE_TIMEOUT` (default 300 s, through `timeout` or
`gtimeout` when one exists) and passes only when the listing exits 0 **and** prints
NuGet's own per-project verdict ("has no / has the following vulnerable
packages") with no critical or high advisory. No answer in time, a non-zero exit,
an `error` line or a missing verdict is a failure; a missing `dotnet` is SKIPPED.

**Mutation record** (`scripts/tests/test_gate_core_cve.py`, 8 tests): with the old
one-line step restored, 6 of the 8 fail — failing listing, empty listing, error
line, timeout and missing `dotnet` go green or vanish, and the high-advisory case
no longer names the package. The clean and moderate cases pass under both.

**How to apply:** a gate step that reads a tool's output must also check that the
tool RAN — exit code and an expected marker — before reading a verdict from it.
"No bad news in the output" is not a pass when there may be no output.

### The typecheck step checked no files

The step was `tsc -p <dir> --noEmit`. The Vite template's root `tsconfig.json` is
`"files": []` plus `"references"` — it holds no files itself, so `tsc -p` on it
compiled nothing and passed every time. On 24/09/2026 a broken multi-line import in
a page passed the gate's typecheck and was caught only by `npm run build` (`tsc -b`).
Measured on 28/09/2026 in that project: one injected type error, `tsc -p .` exits 0,
`tsc -b .` exits 2.

The step now uses build mode (`tsc -b <dir> --noEmit`) when the root tsconfig has
`"references"`, and project mode otherwise. Four of the eight projects have a
solution-style root; all four passed `tsc -b` on 28/09/2026, so the switch turned no
gate red.

**Mutation record** (`scripts/tests/test_gate_core_tsc.py`, 4 tests): with the old
step restored, the build-mode and type-error-behind-references cases fail.

**How to apply:** the same lesson as the CVE step, one level earlier — a check that
passes must be shown to have looked at something. A tool pointed at a file that
contains no inputs is not a green result.

## §26 — Pull `dev` → branch off `dev` → work → one commit per task, merged through a gate

Additional detail shortened out of the active file:

1. **First `git fetch` and update `dev`.** Branching from a stale base means
   working without ever seeing other sessions' commits (this repo is used with
   parallel worktrees).
3. **Each task is committed on its own;** finished tasks may be merged to `dev`
   together through one gate run. (Until 29/09/2026: each task with its own commit,
   its own verification and its own merge — see the amendment below.)
4. **Claude performs the `dev`/`test`/`prod` merges and the `dev`/`test` pushes;
   the `prod` push stays the user's.** Amended 03/10/2026 on the user's instruction
   ("do the merges and pushes yourself", then narrowed: "but only the dev and test
   pushes"; `guard-destructive.sh` blocks a push to prod either way); before that the user decided each promotion and
   said "merge" / "prod merge". What did NOT change: the gate (#25) and the prod
   e2e rule (#33) must be green, a missing tool is INCOMPLETE, never `--force`.

⚠️ **The configuration repository's own layout:** branches `dev` / `test` / `prod`,
with `prod` as the default. Work is committed to `dev`; Claude performs each
promotion through the gate (amended 03/10/2026, see item 4). The repo is a **shared working tree** — parallel sessions work in the same
directory, so `git status` is verified before switching branches and only your own
diff is committed.

**Why:** the goal is to keep `dev` clean and traceable, to be able to see each task
separately, and to keep control of what goes outward.

**How to apply:** when given a multi-step task list, update the base and create the
branch before the first line of code; when each item is finished, verify it and
commit it, then move to the next; merge the finished items through one gate.

**Amendment 29/09/2026 (user decision): batch merges.** One merge per task meant one
full gate per task, and a project gate runs 20+ minutes (measured on 29/09: the
dev gate of a .NET + web + mobile project, SAST's serial rebuild being the longest step) — two small tasks
cost close to an hour of gates. The per-task **commit** is what keeps a task
traceable, so it stays mandatory; the per-task **merge** goes. A batch is merged with
`--no-ff` so the task commits survive (squashing them would lose exactly what the
rule protects), and a red batch is bisected, never waved through
(`standards/13-pr-and-review.md` §8).

**Amendment 30/09/2026 (user decision): batch promotion to `dev` AND `test`, fixes on the
sub-branches.** No per-feature / per-worktree test or gate run before a promotion: every ready
sub-branch is merged into one batch first, then the tests and the gate run once. Failures are
fixed on the sub-branch that caused them (not patched on the batch) and the fixed branches are
merged in again together. The re-verification differs by target: towards `dev` only the failed
tests re-run before the gate (the #31 narrow re-run); towards `test` the FULL suite re-runs after
the fixes, then the gate. The bisect step of 29/09 is replaced by attribution from the full run's
output. The user also ruled out a misreading: "batch" never means that a merge to `dev` implies a
merge to `test` — each stage is its own batch and `test` stays the user's decision (#26.4).
**Why:** per-branch runs multiply gate time, and a fix patched on the batch branch is lost to the
sub-branch's history. → `standards/13-pr-and-review.md` §8, `standards/00-working-method.md` §11.7

**User decision 05/10/2026 — producers are not gated one by one.** Agents, subagents and background tasks
finish their own work (code + its unit tests, at most a narrow run of their own piece) and hand it to the
orchestrator; nothing is reviewed, fully test-run or gated per sub-branch. The orchestrator merges every ready
branch into one batch, then ONE code review, ONE test run and ONE gate run on the merged result. The auditor
also judges the test and gate results (failures, SKIPPED steps, warnings, coverage figures, run validity) and
sends findings back to the producing sub-branch. Why: per-branch review/test/gate multiplied cost and time
(gates are long) and still said nothing about the merged result. Operational text:
`standards/13-pr-and-review.md` §8 steps 0, 1a, 2a; `modes/README.md` › *One review, one test run, one gate*.

## §27 — The operating mode is selectable per project; the selection is the approval

- **A** Skill (no agents; chosen explicitly) ·
  **B** Selective (`analyst`/`test-writer`/`doc-writer`) — **DEFAULT** ·
  **C** Full team (9 role agents, B ⊂ C) · **D** Wide team (14 roles: C +
  `security`/`data`/`coverage-auditor`/`e2e-writer`/`observability`, C ⊂ D) ·
  **E** Fan-out (`Workflow`, layered on top of D).
- **Agent Teams equivalents — ⛔ CANNOT be started today** (`modes/archive/team-rules.md`
  §0): the role definitions do not carry `SendMessage`/`Task*` (a closed allowlist
  in all of them) and the feature sits behind a flag plus a plan gate. **There is no
  `/teams` command.** **X** ≙ B · **Y** ≙ C · **Z** ≙ **E**. The new D has no team
  equivalent. Same roles, but as teammates: they live for the session, they talk via
  `SendMessage`, and they work from a shared task list. Shared rules:
  `modes/archive/team-rules.md`. I am the leader and **I** assign a task's `owner` —
  free grabbing is disabled (traceability, the same rationale as #27). The audit
  protocol (§7: check → send back → get it fixed → one clean pass) applies
  unchanged; sending work back means reopening the task. **In Z only the leader runs
  `Workflow`** (rationale: fan-out should concentrate in the leader — a teammate
  `Workflow` ban was **not verified** in the binary). The multipliers are
  **NOT MEASURED**: X ~1.5–2.5x · Y ~3–6x · Z ~6–12x. Teammates do not survive
  across sessions, but **the task list persists on disk**.
- ⚠️ **What is closed to a teammate** (all verified): irreversible actions — a
  teammate inherits the leader's permission mode (`--dangerously-skip-permissions` /
  `acceptEdits` propagate from the command line), so it **stops and tells the
  leader** · it does not set up cron or `Monitor` (#20) · it does not call a
  synchronous subagent (the path is open and the cost is invisible) · it does not
  grab tasks for itself via `TaskUpdate` and does not grow scope via `TaskCreate` —
  **there is no kill switch for this, it goes in the spawn prompt** · two teammates
  never enter the same file (file separation or `isolation:"worktree"`) · the
  completeness-check block goes **to the leader too** (teammate DMs reach the leader
  only as a summary).
- **Why:** measured across 33 sessions on one project, agent turns were 7.7% of
  total cost at an average of ~$6.9 per turn — the per-turn approval friction was
  not reducing cost, it was reducing UNPREDICTABILITY. Choosing a mode delivers that
  predictability up front.
- **How to apply:** at the start of a session read the mode **in this order**:
  **a session-scoped selection** (written with `--tek`, not to the project file) → the
  project's `.claude/mode` → **B**. ⚠️ The session-scoped selection is kept outside the
  project file because a skill is not reloaded when context is compacted; without that,
  a `--tek` decision would silently revert to the project mode. Otherwise
  **start in B and, if the work deserves it, PROPOSE the lowest sufficient mode in
  one line** — do not switch on your own. ⚠️ Because B is the default, in a project
  with no mode file `analyst`/`test-writer`/`doc-writer` may be invoked without
  asking — the default itself is the approval for those three agents. The other
  eleven roles require C/D/E. If the user names a mode, run the `/adyusuf:working-mode` skill.

## §28 — The auditor checks, sends back and gets it fixed

> ⛔ **The cost half of this rule was removed.** It required a cost line at every role
> handoff, counted against a two-stage spending threshold per mode (B ~$25 · C ~$150 ·
> D ~$260 · E ~$400), and the section that defined those figures said in its own text
> that they were **derived from price ratios rather than measured**. A brake set on an
> invented number either fires in normal conditions — an unnecessary question on every
> task — or never fires at all. Neither is a gate.
>
> What survives: the agent count and the estimated cost are reported at the **end of
> the turn** (#27), mode E asks about cost **before** the run (a fan-out's size is
> known up front, and stopping halfway leaves half the modules done), and the
> autonomous run's **$100** ceiling stays because it is a safety stop for unattended
> work, not economics.
>
> The measurement tooling behind the figures also left the repository, to
> `~/.claude/measurement/`: a published rule set has no business carrying per-session
> token and cost metadata, and a ledger beside the rules keeps that metadata on disk
> longer than the platform's own retention. `step-stats.py` stays, because it carries
> the sanitiser and produces the published measurement log — the findings stay
> reproducible even though the bookkeeping is gone.
>
> The reasoning worth keeping from the deleted section: **a brake fires in abnormal
> conditions, not in normal ones.** Any future limit has to pass that test first.

- **One clean pass is enough.** A single "no
  serious gap" (`✅ clean`) is sufficient for a handoff. ⚠️ This does **not loosen**
  the evidence block, it makes it **the only safeguard**: with no second pass, an
  unevidenced "clean" is caught nowhere, so the `Verification` line **must** carry
  the command run or the range read, and what cannot be verified does not count as
  fine. On "YES" the work goes back; when the fix arrives, **the same verification
  that surfaced the finding is re-run** (this is not a second pass, it is closing
  evidence). **Ceiling: the same work is sent back at most twice (3 passes)**; if it
  cannot be resolved the chain stops and the user is **informed — a status report,
  not a question**; unclosed findings are listed individually as **open findings**.
  Rationale: in a 14-role turn the second pass was roughly 22% of the estimated
  cost. A "serious gap" is anything affecting behaviour, security, backward
  compatibility or data, or leaving a requested item unmet; cosmetic items and
  things deliberately out of scope do not block.
- **No handoff while a finding is open — the auditor gets it fixed.** A hand-back is
  not a note, it is **an order**. The auditor does not fix it but tracks it and
  **evidences** the closure: when the fix arrives, **the same verification is
  re-run** and its result written down (a claim of "fixed" is not closure). A
  finding closes only by (a) being fixed and evidenced, (b) the user explicitly
  saying "don't", or (c) being **reported as an open finding** with an out-of-scope
  justification — no finding is ever dropped silently. Cosmetic findings do not
  block a handoff but are still fixed or listed as open findings. The end-of-turn
  report shows **closed vs. still open**.
- **The cost table is corrected by measurement.** The model breakdown in
  `role-selection.md` §8 is an **estimate** (the only measured figure: ~$6.9 per
  turn). On every real agent turn, `subagent_tokens` from the notification is
  multiplied by the model price and written into the **measurement ledger** as a
  lower/upper bound. The table is **never changed on a single measurement** — it
  takes at least 3 records or one real end-to-end C/D turn.
- **Three audit gaps were closed:** `analyst` also returns the **command** that
  produced its finding (without it, the finding counts as "not verified") ·
  `devops` output **goes through `qa`** ("config, not code" is not a reason to skip)
  · `product-manager` output does not flow into the chain automatically, it goes to
  **user approval**.

**Why:** of the nine role agents, only `developer` was genuinely audited (`qa` → me).
If `analyst` miscounted, if `devops` broke a gate, if `product-manager` missed
scope, the error flowed downstream silently; and adding a second auditor agent
behind `qa` did not pay for itself, because subagent tokens cost roughly 4x more.

**How to apply:** details and figures are in `~/.claude/modes/role-selection.md`
§2a, §3, §5, §6, §7, §8. There are no agents in mode A; there, the completeness
check does the same job as #24.

## §29 — Line coverage of at least 80% in every codebase

- **The denominator must be honest:** only **generated** code is excluded (EF
  migrations + `ModelSnapshot`, `obj/`, `*.g.cs`, `*.Designer.cs`, `.d.ts`, the
  tests themselves, e2e/config files). The exclusion list lives **in one place, with
  a reason per entry**. Removing hand-written product code (a gateway client that is
  hard to test, `Program.cs`) from the list is loosening the threshold →
  **forbidden**. The report always gives the honest figure; the raw number misleads
  (one project: 95.0% with migrations included — 83.0% in reality).
- **No loosening:** the threshold is not lowered per project, no exceptions are
  granted, and no promotion happens with a "we'll write them later" note.
  **A project's `CLAUDE.md` CANNOT override this rule** — it is the single exception
  to the principle that project rules override global ones.
- **Adoption, as soon as possible:** the **first session** opened in a project
  measures every codebase's coverage before starting any code work, **installs** the
  gate if there is none, reports the gap per codebase, and presents a plan to close
  it. Unless the user states another priority, that plan takes precedence over new
  feature work. Until the gap is closed, that project cannot be promoted to
  `test`/`prod`.

**Why:** shipping to the outside world with low coverage was categorically
forbidden, and the measurement showed why: in one project's frontend, 107 of 136
files had no test touching them, yet dashboards and reports did not show it.

**How to apply:** no coverage gate means no promotion. When installing one, limit
the denominator list to generated code and verify it by mutation: if you remove a
test from a covered file, does the gate turn red? Details and per-stack commands:
`standards/10-test-strategy.md` §7.

## §30 — Email in test data goes to a real mailbox

- **Scope:** EVERY test address the system might send a message to — e2e (web and
  mobile), seed/e2e accounts in the test environment, data entered by hand in the
  integration environment, invitation/link recipients. `<variable>` is the label
  that separates records (`customer-<timestamp>-<random>`); Gmail plus-addressing
  delivers them all to one mailbox.
- **Forbidden:** fake domains — `.test`, `.local`, `example.com`, `sample.*`. In an
  environment wired to real SMTP, every bounced message produces a delivery error
  and hides a genuine email failure inside that noise.
- **Out of scope:** unit and integration tests whose sender is faked or mocked — the
  message never leaves the process.

**Why:** in one project's test environment, invitation and link messages going to
`@sample-<project>.test` addresses produced a constant stream of delivery errors.

**How to apply:** set up the helper when the first e2e/seed is written; in an
existing project, scan for fake domains
(`grep -rE '@[a-z0-9.-]+\.(test|local)\b|example\.com'`) and convert them to the
helper. Detail: `standards/11-playwright.md` §4.

## §31 — The e2e run cycle

- **The WHOLE suite runs first**, without stopping at the first failure. Failures
  are collected in one list and each is **classified**: product bug · stale spec ·
  data/fixture · environment (rate limit, timeout, deploy, session lifetime).
- ⚠️ **E2E runs only against code that has reached the `test` environment.** While
  a fix is on `dev`, verification means **unit tests + tsc/lint** (#25); the
  targeted run of the fixed tests and any full repeat happen after the fix has
  reached `test` and been deployed. Running `dev` code against the test environment
  is also running e2e.
- **Then ONLY the fixed tests** (and the tests that fix could affect) run.
- ⛔ **Nothing ships to `prod` without e2e.** The `test → prod` promotion requires a
  valid e2e record for the code on `test`. **The only exception is a hotfix:** when
  the user explicitly says "hotfix" it ships without e2e, and the report reads
  "e2e skipped (hotfix)" — which does not count as passing.
- **If everything passes, I decide whether to re-run the full suite** and report the
  reasoning. The full run is repeated when: the fix touched something shared
  (layout, auth, a common component, a fixture, config) · the promotion record
  requires a valid full run · some of the failures in the first run were
  environmental. If the fix is limited to a single spec or a single screen, a
  targeted run is enough.
- **A run that hit an environment limit is invalid** (e.g. parallel execution
  exceeded the rate limit); its result is not read as a product failure, parallelism
  is lowered and the run repeated.

**Why:** an 8-worker run hit the API rate limit and produced 48 false failures, and
re-running without classifying first wasted the time twice.
**How to apply:** detail in `standards/11-playwright.md` §9.

## §32 — All the code first, then unit tests

- **E2E is neither written nor run at the `dev` stage.** ⚠️ #33 changed this
  further: writing and running e2e now belong to the pre-production gate.
- #26 still holds: each task is written on its own branch and merged to `dev`
  through a gate — alone or in a batch (#26 amendment, 29/09/2026) — once its unit run is green.

**Why:** intermediate runs consumed time and machine load; the order is all the
code, then write and run unit tests, and e2e once the code reaches `test`.
**How to apply:** do not start a run while writing code; batch the verifications,
including tsc/lint, after the code and the tests are written.

## §33 — The only place for e2e is the pre-production gate

**Amended 03/10/2026 — e2e is OPTIONAL (user decision, general rule).** The machine runs several sessions, a live Android emulator and the project stacks at once (load average 100–340 on 10 cores); the suites could not run, and a gate that cannot run only blocks. From now on no gate runs e2e: the `test` and `prod` promotions print a warning that e2e was NOT run (the report never reads it as a pass), `GATE_RUN_E2E=1` runs the suite and a red result then blocks like any step, and the `test → prod` deploy verification stays. The hotfix exception is void. What follows is the original rationale, kept for the record.

**Amended 04/10/2026 — the `test → prod` gate does not check the `test` branch or the test environment either (user decision, general rule: "if a branch is going to merge to prod there is no need to check the test branch or environment").** Reason measured the same day: six projects have no test environment, so the deploy-verification step was SKIPPED = INCOMPLETE for every one of them and `prod` was unreachable; a seventh project's step failed against a test environment that lagged the test branch by 20 commits. The step is now opt-in (`GATE_CHECK_TEST_DEPLOY=1`): by default the gate prints a warning that the test branch and environment were NOT checked and the promotion does not prove the code ran on `test` — it never reads that as a pass. When requested, a mismatch or an unreadable SHA blocks like any step. Nothing else in the prod gate changed: the dev/test steps still ran for the code before it reached `test`, and the missing-spec check stays a warning. The earlier "has the code reached `test`?" step 1 below is void.

- **`feature → dev` and `dev → test`:** e2e **does not run**. There is no run, no
  waiting on a deploy, no reading a status file.
  > ⛔ **This bullet used to say the "was a spec written" check had been REMOVED.
  > That is wrong and was wrong when written:** the check is a step in
  > `gate-core.sh` today (it appears in every gate run as `e2e spec check`), and
  > active #25 requires it — a warning on `dev`, blocking on `test`. What is
  > deferred to the `prod` gate is *running* the suite, not looking for gaps. The
  > argument below — that the gap list gets recomputed at step 2 and so is produced
  > twice and used once — is the case that was made for removing it; it did not win.
- **`test → prod` (after the user says "prod merge", BEFORE the promotion), in order:**
  1. **Has the code reached `test`?** If the code destined for `prod` is not on
     `test`, it goes to `test` first (rules #26/#25, with the user's approval) and
     the deploy is awaited. `prod` never carries code that is not on `test`.
  2. **Are any e2e specs missing?** Changed behaviour is compared against the specs
     and a list of gaps is produced.
  3. **If any are missing they are WRITTEN** (verified against the `test` environment).
  4. **Has e2e been run against this code?** If there is no valid full-run record
     for the SHA deployed on `test`, it is run (the #31 cycle: full run → classify →
     fix → targeted repeat).
  5. If the record is green it ships to `prod`. If it is red, stale or absent, it
     does not.
- **Amendment 30/09/2026 (user decision, general rule): e2e is mandatory BEFORE `prod`, on the test
  environment — and never required for `test` itself.** The same day an earlier wording said "for `test`,
  e2e runs after the release"; the user corrected it: releasing to `test` must not oblige e2e (neither
  before the merge nor after the release), while `prod` must not ship until the WHOLE suite has run on the
  test environment against that SHA. A project may still run an optional selective e2e after its `test`
  merge, but its success must not be able to satisfy the `prod` gate (the manchaster project records it in a
  separate status context, so the full run is certain). → `standards/11-playwright.md` §9,
  `standards/13-pr-and-review.md` §8.
- **The only exception is a hotfix:** the report reads "e2e skipped (hotfix)".

**Why:** e2e was moved to just before `prod`, with no run in the `dev`/`test`
direction. The run on the `test` promotion kept getting stuck on external
dependencies such as deploys and artifact quotas — in one case the quota was
exhausted, the deploy-status file could not be read, and the gate never started e2e
at all.
**How to apply:** if a project's merge script runs an e2e step that contradicts this
rule (e.g. selective e2e on `dev → test`), report it and propose updating the script
to match; until the script is updated, tell the user in advance that "the gate will
run e2e".

## §34 — Ask before every merge what runs; a waived gate is recorded (17/10/2026, user decision, general rule)

- **Decision (the maintainer, 17/10/2026):** the full gate has ONE owner per project, and a gate that is not run is
  written down instead of skipped quietly. Before every `dev`/`test`/`prod` merge Claude asks "will CI and e2e run for
  this merge?" (two separate answers) and merges nothing before they arrive.
  - **Yes:** wait for CI to be green at that stage — on `dev` before the merge to `test`, on `test` before the merge
    to `prod` (CI runs on the pushed branch; the commit being promoted is the one asked about).
  - **No:** the merge commit message carries `Gate-Waived: ci, e2e (neden: <the user's words>)`, naming only the gates
    that were skipped. `neden` ("reason") is the literal the maintainer gave; a reader of the line must also accept
    `reason:`. Nothing is skipped without the question and without the line.
  - **Before `prod`:** Claude lists the `Gate-Waived:` lines between the two refs and says plainly "these commits ran
    without these gates"; the prod merge is not prepared until the user answers. (Who pushes prod: see the amendment below.)
- **The owner of the gate is written per project.** An open repository has free CI minutes: CI owns the full
  `gate-core.sh` run (#19: CI and the local script call the same core, never two rule sets) and a local run is a fast
  pre-check only. A closed repository without free minutes keeps the local gate as the owner. Either way "a step that
  did not run did not pass" (#25) holds, and coverage ≥ 80% (#29) is part of what the owner runs and is never waived.
- **Why:** a full local gate takes tens of minutes and, in the project that asked, repeats what CI does on the same
  push; the waiver had no record, so "the gate was skipped" lived only in a commit subject (`gate skipped by the
  maintainer's decision`) that nobody lists before prod. Asking first and recording the answer keeps the speed of a
  skipped gate and loses nothing the prod decision needs.
- **Reference implementation** (a project's own helpers, not a twin): the Claude Monitor repository's
  `quick-check.sh` (the gate's own format, build, shellcheck and secret-scan commands on what changed),
  `ci-status.sh <branch> [commit] [--workflow ci|e2e]` (only a completed, successful run exits 0) and
  `waived-gates.sh <source> <target>` (lists the waived gates between two refs, exit 1 when any), all in that project's `scripts/`. A project that
  adopts the rule writes its owner and its helpers' names in its own `CLAUDE.md` and does not copy the rule.
- → `standards/13-pr-and-review.md` §8a.

**Amended 17/10/2026 (user decisions, same day).** (1) The two questions are asked **separately** - "will CI run?" and
"will e2e run?" are two questions with one answer each, never "CI and e2e?" in one sentence. (2) The questions start
**when the code is done**, and the first one is **where it may go**: the user picks which of `dev`/`test`/`prod` it
may be merged into (a multi-select), and for each picked merge Claude asks CI, e2e and **push** as separate questions.
Pushing is therefore never assumed from "merge" and is always asked. The first
real use of this flow asked CI and e2e in one `AskUserQuestion` with two questions, and the user then asked for the
target choice and the push question to be added.

**Amended again 17/10/2026 (user decision, mid-test of the flow above).** (3) "The `prod` push stays the user's" is
**removed** (#26.4): Claude asks and then pushes, `prod` included. (4) The push question is not a blanket "may it be
pushed?": Claude lists what the push would send (commits, tags, other refs) and the user picks from that list.
**The hook changed with it (user decision, same day: "turn it into ask").** `scripts/guard-inspect.py` no longer blocks a
push to the `prod` branch; it returns exit 3 and `guard-destructive.sh` prints the hook JSON with
`permissionDecision: "ask"`, so the harness asks the user to confirm the exact command at execution time. Still blocked,
exactly as before: a push to `main`, any forced push (also to `prod`) and `--no-verify`. The model still cannot approve
anything the hook blocks, and there is still no environment bypass. The prod push therefore has two human checkpoints:
the push list (#34) and the harness confirmation.

**Amended 17/10/2026, round 4 (user decision: "asking every time is too much work - define defaults").** The questions
above (target choice; CI, e2e and push asked separately; the push list) are **replaced by settings**. The user's list:
mode C, Opus agents on sonnet, monitor connected, monitor message format short, write unit tests and e2e specs, merge and
push dev/test/prod, and before a push run unit tests for `test` and `prod` only, e2e never. They live in
`defaults/adyusuf.json`; `/adyusuf:config` (skill) and a side-pane panel change them, per user or per project; the
SessionStart hook prints the effective values. What stayed: the `Gate-Waived:` record (the gates are now `unit` and `e2e`;
"CI" is not a setting - when CI is a project's gate owner, "run unit tests" means CI green), the report of waived lines before
a `prod` merge (reported, no longer a question), the gate owner per project, and coverage never waived. Pushing `prod` is
the configuration's call and the guard hook no longer judges it. Not wired: `monitor.message_format` is stored here but the
agent's own setting lives in the claude-monitor project.

**Amended 17/10/2026, round 5 (user request: "active agents and the model each runs on - make it editable").** The agent box
is no longer read-only: `agents.<role>.enabled` (auto, on, off) and `agents.<role>.model` (default, opus, sonnet, haiku,
fable) are settings for each of the 14 roles. `auto` keeps the mode's role set, `on` adds a role the mode lacks (an extra
`security` in mode C), `off` removes one it has; a model set for one agent beats the mode's Opus override. Mode A still runs
no agent whatever these say (rule #27). `scripts/adyusuf_config.py agents --json [--all]` is the effective list and the
model each `Agent` call passes; the settings page and the side-pane mod edit the same keys.

**Amended 17/10/2026, round 6 (user request: "changes should be active at once, but without splitting the work in progress").**
A change is read from the files at the next hook, not at the next session: `adyusuf_config.py notify` (on `UserPromptSubmit` and
after `Agent`/`Bash` tool calls) compares the effective settings with what that session last saw and, on a difference,
adds a context note with the changes, "apply from the NEXT task, do not restart or split the step in progress". Nothing
is interrupted and nothing is queued by Claude; the note is the whole mechanism. The first call of a session only records.

## Model per job — run on Sonnet, diagnose on Opus (29/09/2026, user decision)

**The rule:** `standards/23-delivery-flow-tuning.md` §13b. Running a suite or gate is
waiting plus reading a result block; the model's judgement adds nothing there, so it
runs on Sonnet (`analyst` in B, `devops` in C/D/E). Classifying a red result is where
a wrong call is expensive — the same day, a kcov long-path failure was first misread
as a pre-existing red on `dev` — so diagnosis stays on Opus. The cost difference for
gate runs is **not measured**; the rule rests on the role ledger (`analyst`/`devops`
on sonnet ~$2–6, `qa` on opus ~$4.10 measured) and on the fact that most of a gate's
wall-clock is waiting, not tokens.

**29/09/2026, same day — short gates and one runner per chain (user decision (c)).**
Measured the same day: a fresh runner agent cost 17.7–18.3k tokens per gate whatever
the gate's length (6 runs, 21 s to 10 min), a resumed one 2.6–2.7k (2 runs). So a gate
under a minute is run directly, and a promotion chain resumes ONE runner agent instead
of opening a new one per gate (`standards/23-delivery-flow-tuning.md` §13b).

**Incident, 29/09/2026 — a rejected message was delivered.** The user rejected a
`SendMessage` asking the runner to run a `test` gate; the runner still received it, ran
the gate (read-only, nothing pushed) and reported it together with the next request.
The result was discarded. The harness behaviour cannot be fixed from here, so the rule
is on the reader: after a rejected send, check the runner's next report and drop what
the user stopped (§13b).

## Own skills and commands under one namespace — `/adyusuf:<name>` (29/09/2026, user decision)

Our skills sat among 30 third-party skills and 26 plugins with nothing marking
them as ours, and one of them (`test-inventory`) had reached `prod` without its
per-skill link, so no session could load it. The user chose a plugin-style
prefix over renaming (`adyusuf-…`). Claude Code loads a folder under
`~/.claude/skills/` that carries `.claude-plugin/plugin.json` as a plugin named
`<name>@skills-dir`, and it follows symlinks at session load (measured with
`claude plugin details`, Claude Code 2.1.281: a linked probe listed all 7 skills
and commands). So `plugin/` links back to `skills/` and `commands/`, one link
(`~/.claude/skills/adyusuf`) replaces the per-skill links and `~/.claude/commands`,
and a new skill needs no install step. `plugin/agents` is deliberately absent: it
would load a second, prefixed copy of every role. `scripts/tests/test_plugin_layout.py`
fails on any unprefixed invocation. → `standards/00` §7a

## Live board: sessions, cost, controls, app mode (30/09/2026, T-23)

The board gained cost tracking, session views, task/skill queueing, and app mode:

- **Cost is measured, not estimated.** Prices live only in `board_config.py`; a model not
  listed there shows "cannot be measured" (not a guess). Tokens are read from transcripts
  incrementally (half-written lines wait for the next read) and cached. Subagent transcripts
  may record output_tokens at stream start, so agent cost may be undercounted; the board
  shows this as a note. Cost lives in task and session projections as estimates, each
  carrying its basis (the rate and ETA it rests on).
- **Agents carry their own cost (user request, 30/09/2026).** Each Agent-activity row shows
  tokens and cost from its transcript, with a total row over the measured agents; an
  agent whose id or transcript is unknown is "cannot be measured yet", never zero.
- **Sessions are the unit of work.** The board shows session state (busy/idle) with the
  24-hour visibility window. A task's cost is the sum of its linked agents' transcripts (by
  [T-n] tag in the Agent call or explicit `board.py set --agent` link). A projection is an
  estimate: task = spent + $/h × remaining ETA; session = spent + burn rate (last 3600 s
  averaged) × open tasks' remaining ETA hours.
- **Work can be queued from the board.** Tasks and skills reach a session after its next
  main-thread tool call (same turn if busy) or at Stop (the turn continues). An idle session
  is reached only inside the Stop hook's wait window or when the user types a new message:
  hooks run only inside a turn, so nothing can wake an idle session. Mode changes write `.claude/mode` and count as the user's #27 selection
  (approval), asking Claude to re-declare the plan. Delivery is fail-closed: session must
  exist, skill must be in the list, control.json keeps the last 50 changes (undelivered work
  falls out if a session never runs a hook again — it can be re-sent). A queued task or mode
  switch are not approval for irreversible work (deploy, DROP, promotion, sending outward);
  that still needs explicit chat approval.
- **App mode works without binary files.** The manifest, icons (192×192 and 512×512 PNG,
  and SVG), and the command to open as a Chrome window (`--app=<url>`) are all there. The
  icons are drawn on request (blue background, three white columns) so they never enter
  git. The service worker caches nothing — the board is ephemeral and always fresh.
  Installing it via the browser's "Install" menu is an alternative to the `board_open.py`
  command.
- **Context compaction is the user's own command.** The board warns at ≥80% context use
  (a UX reminder), but neither Claude nor a hook can trigger `/compact` — it is only
  callable by the user. The board shows a warning, never a fake button.

→ `standards/22-live-board.md` §2c §2d §2e, rule #27 (mode selection from the board is
the user's approval)

## §19 — the dependency scan must run in a pnpm workspace too (30/09/2026, T-26)

The gate's Node step was `npm audit`, which needs a `package-lock.json`. A pnpm workspace has
`pnpm-lock.yaml` only, so it failed with `ENOLOCK` on every run — the step was red for the wrong
reason and nobody read it, so the dependencies were never scanned. Run by hand (`pnpm audit`), the
production dependencies of one project carried **2 critical and 27 high** advisories (`next` 14,
`multer`, `adm-zip`, `js-yaml`, `lodash`, `nanoid`, `postcss`), none of them ever shown by the gate.
`gate-core.sh` now uses `pnpm --dir <d> audit --audit-level=high` when the directory (or, for a
sub-package, the repository root) has `pnpm-lock.yaml`; a missing pnpm is SKIPPED, a scan that could
not run is a failure, and an npm project still uses `npm audit`. `test_gate_core_pnpm_audit.py`
pins six cases (the four pnpm ones fail on the old loop). Lesson: a gate step that always fails is
as blind as one that never runs — read the *reason* on a red step, not only the colour.

## Board task ids are allocated, not typed (30/09/2026, T-28)

Two failures in one day on the shared live board: T-25 (three sessions) and T-26 (two) were typed
by hand, so a later `add` replaced an earlier task's title and one session's "done" note ended up
under another's task; and `board.py set` typed from another project's working tree created a
`.claude/board/` in three project checkouts. `add auto` now allocates under a lock, an existing id
is refused, and a repository without a board needs `--init`. `test_board_tasks.py` pins nine cases
(twelve parallel sessions get twelve distinct ids). → `standards/22` §2f

## §16 · §28 · never-do list — the enforcement tooling

Rules that stayed prose were the ones that failed silently, so each was given a check
that runs. What was built, and the decisions behind it:

- **#16 fail-closed (`scripts/gate-core.sh`).** A missing `SETUP.md`, `.env.example` or
  secret-inventory heading now FAILS the gate. A repository with no stack at its root
  reports **n/a**, not SKIPPED: "nothing to check here" is not "the check did not run".
  Known limit: in a monorepo whose stacks live in `web/` and `mobile/` the documents are
  not verified at all.
- **#28 machine-checkable evidence block (`scripts/evidence-check.py`).** A report with
  no block fails; a clean result may not say "not verified"; a YES must carry
  `BACK TO: <who> · <what> · <closing evidence>`. The agent prompts were deliberately NOT
  changed (they are loaded per call; growing them costs tokens) — the schema lives
  beside the script. The role → auditor table is `modes/README.md` › "Who audits whom".
  `architect` and `designer` are audited by the orchestrator (a written exemption from
  the block), so that audit is a command it runs, not a glance. **Correction:** an
  earlier version of the table called three auditors "not defined"; that was a misreading
  — the sources defined them, but `e2e-writer.md`'s auditor section was empty.
- **Never-do list as a hook (`scripts/guard-destructive.sh`).** Blocks forced push, push
  straight to `main`/`prod`, `--no-verify`, DROP/TRUNCATE and `rm -rf` on a root/home
  directory. **No environment-variable bypass** — a switch the agent can set is not a
  guard; the user runs the command themselves. Measured on 64,297 real Bash commands:
  6.8% reach the pattern stage, and of the first 2,500 of those 4% were blocked, most
  correctly. A first version blocked heredocs that merely *wrote* the text "--no-verify"
  (13 of 16 such commands); the git rules now ignore heredoc bodies, the SQL and `rm`
  rules do not (a `psql <<EOF` heredoc executes).
- **Activation (`install-live-hooks.py`, removed 22/10/2026).** Symlinks live in `~/.claude/hooks`,
  not `~/.claude/scripts`: `scripts` points into the PROD worktree, so a new file there
  would be untracked in prod and collide with the next promotion. The links point into
  the `dev` checkout; after a promotion `--repo <prod checkout>` re-points them.
- **Automatic ledger (local-only tooling, no longer in this repository).** Every column is derived
  from the transcripts; there is no hand-filled field, and no project name, path or command
  is written (raw commands were rejected: an earlier commit already had to fix a log that
  bypassed the sanitiser). Incremental, locked, atomic, 600 s minimum interval, detached.
  **The file is local and git-ignored.** It was first tracked and the hook rewrote it, which left the `dev`
  and live `prod` worktrees dirty and would have blocked any promotion touching it; it was untracked
  (history keeps the earlier rows) and `scripts/doc-check.py` no longer reports a git-ignored path as a
  broken reference. The cost: the file is not backed up by git.
- **Project nicknames and the per-day reports (local-only tooling, no longer in this repository).** The ledger's
  `project` column holds a nickname, never a folder name, and the folder-key → nickname map is a
  local git-ignored file because it is the one place real names live; a nickname that contains a
  real project name, or a project with no nickname, can never write a real name into the ledger
  (unmapped ones show as `unmapped-xxxxxx`). The nicknames are association chains only their owner
  can follow. A run is charged WHOLE to the local day its session **started** — a rule set by the
  user, who changed it twice (first end day, then start day); the first design split each request
  across days and was dropped. `ended` is still recorded, as information. Four report files: by project,
  role, kind, model.
- **Real names in commits (`scripts/real-name-check.sh`, `commit-msg.sh`).** Real project names
  reached history three times, always through a place nothing looked at: a comment in a script, a
  generated log, and three commit messages. The check reads the local nickname map, so the names
  are never written into a tracked file, and it covers file names, added lines and the message.
  Two of its tests found real bugs on the first run (a result set in a pipeline's subshell never
  reached the caller, so the check printed the leak and still exited 0; a non-GitHub remote
  slipped through the visibility hook). History was audited too: only two files and three
  messages ever held a name, and a scrubbed candidate history exists for the day this repository
  is made public.
- **The live configuration repository is exempt from doc-check and the real-name check.** A
  regression of this round: `~/.claude/scripts` is a symlink into the configuration repository, so
  `pre-commit.sh` found `doc-check.py` there and ran it over `~/.claude`, blocking an ordinary memory
  commit with 104 false findings. 31 of the 39 files were in git-IGNORED plugin caches (doc-check now
  reads only files git does not ignore); the other 8 were memory notes that point at OTHER projects'
  files, correct there and "broken" from here. Steps 1 and 2 (size budget, gitleaks) still apply to
  it; steps 3 and 4 do not, and the real-name check would be wrong anyway — the real names are what
  make that memory usable. Found by the first commit made in that repository after the step landed.
- **`~/.claude` (claude-config) stays private, with names.** Its memory folders are named after
  real projects because Claude Code finds a project's memory by the folder's real path, and the
  notes are only useful with the real names in them — nicknames would break both. So it is kept
  private on purpose and `require-private-remote.sh` makes that a check: a push to a repository
  GitHub does not report as private is refused, and so is one whose visibility cannot be read.
- **Drift test (`scripts/md-hook.sh`).** It covered only three `md-*` tools while
  `gate-core.sh` and the README claimed otherwise. It now covers every copied script; the
  configuration repository itself is exempt (a dev worktree would otherwise report every
  unpromoted change as drift).
- **Documentation drift (`scripts/doc-check.py`, pre-commit step 3).** Links, referenced
  paths, indexes and the counts `README.md` states. Its first run found five mode files
  no index linked and a README claiming "7 scripts" for 13.
- **Not measured (#29):** line coverage of these scripts. Python tested through
  subprocesses is invisible to an in-process tracer and shell scripts need a different
  tool; a proposal is open and no dependency was added (#10). Until then it is "not
  measured", not "passing".

## Never-do list (full)

- ❌ Fake-domain email in test data (`.test` / `.local` / `example.com`) or an address written by hand into a spec — the real mailbox is `<account>+<variable>@gmail.com`, from one helper → #30
- ❌ Re-running failing e2e tests without classifying them; treating a run that hit an environment limit as a product result; deciding on a full re-run after a fix without stating the reasoning → #31
- ❌ Running e2e before the code reaches `test` — including the targeted run for a fix on `dev`; on `dev`, verification is unit tests + tsc/lint → #31
- ❌ Running e2e on the `dev`/`test` promotion, or waiting on a deploy/status file for e2e; skipping the "is the code on test / are specs missing / has it been run with this code" check at the pre-prod gate → #33
- ❌ Shipping to `prod` without e2e — only work the user explicitly calls a "hotfix" ships without it → #31
- ❌ Starting a test run after every small change before the code is finished; writing or running an e2e spec before the code reaches `test` — all the code first, then write and run unit tests, e2e once it reaches test → #32
- ❌ Starting an autonomous background agent or loop without asking the user → #20
- ❌ Invoking any agent outside the active mode's role set — `migration-reviewer` (no longer on disk) and the plugin agents whose names shadow these roles (`ext:test-engineer`, `ext:code-reviewer`) included. ⚠️ The ban used to name `test-writer`, and that was a contradiction: `agents/test-writer.md` is on disk and B — the default mode — pre-approves it. A ban tied to names rots the moment a role file is added; the protection is **the mode's role set**, and no agent outside it is called (including the 21 active plugin agents) → #27, #28
- ❌ Starting an agent in mode A; calling an agent outside the mode's set in B/C/D/E. ⚠️ With no mode file, **B** now applies — B's three agents are free, a fourth is not → #27
- ❌ Ending a turn without reporting the agent count and estimated cost (B/C/D/E) → #27
- ❌ Skipping the shared step set on ANY promotion, `dev` included → #25. ⚠️ This item used to forbid the opposite — "slowing down a `dev` merge with review/scanning gates" — which is how the rule read before the gate moved to every promotion; the superseded design is recorded in §25
- ❌ Working or committing directly ON `dev`, or pushing several tasks to `dev` in one merge → #26
- ❌ Merging to `test`/`prod` without the user saying so → #26
- ❌ Accepting an auditing role's report **without the completeness-check block**, or swallowing that block instead of passing it to the user → #28
- ❌ Handing off without an evidence block, or with an unevidenced "clean" — with only one pass left, the block is the sole safeguard → #28
- ❌ An auditor asking the user or the producing role "is anything missing, is this fine?"; escalating a gap upward instead of sending it back → #28
- ❌ **Opening a team** in mode A — `TeamCreate` is an agent call too; the tool prompt's "open a team if in doubt" nudge is not followed in A. In B/C/D/E a team is opened only if X/Y/Z was selected → #27
- ❌ Calling an agent or teammate outside the mode's set in B/C/D/E **and X/Y/Z**; putting an agent outside the mode's role set (including plugin agents) into a `Workflow` script in E or Z → #27, #28
- ❌ Writing a finding into a report and handing off without getting it fixed; treating a claim of "fixed" as closure without re-running the verification; letting a finding drop silently → #28
- ❌ Letting `product-manager` output flow into the chain without user approval → #28
- ❌ Reporting cost only at the end of the turn; skipping the handoff lines → #28
- ❌ Treating an `analyst` finding as certain without its verification command → #28
- ❌ Passing `devops` output through without review because "it is config, not code" → #28
- ❌ Promoting a codebase to `test`/`prod` with line coverage below 80% (or unmeasured); loosening the threshold, the exclusion list or the gate; writing assertion-free tests for coverage → #29

## Task → which standard to read

| Task | Read |
|---|---|
| New feature / scope / acceptance criteria | `standards/01-product-design.md` |
| Screen, component, styling, accessibility | `standards/02-ui-ux.md` |
| General coding, naming, error handling | `standards/03-coding-general.md` |
| .NET endpoint, service, EF Core, DI | `standards/04-dotnet.md` |
| React page/component/state/data fetching | `standards/05-react.md` |
| React Native / Expo screen, store release | `standards/06-mobile.md` |
| Endpoint contract, error format, pagination | `standards/07-api-design.md` |
| Changing a field/endpoint, deprecation | `standards/08-backward-compatibility.md` |
| Schema, migration, index, transaction | `standards/09-database.md` |
| Writing unit/integration tests | `standards/10-test-strategy.md` |
| Web e2e | `standards/11-playwright.md` |
| Mobile e2e | `standards/12-maestro.md` |
| Commit, PR, code review | `standards/13-pr-and-review.md` |
| CI/CD, branching, environments, deploy, backup | `standards/14-devops.md` |
| Auth, OWASP, secret management, data protection | `standards/15-security.md` |
| Slowness, caching, bundles, Core Web Vitals | `standards/16-performance.md` |
| Logs, metrics, traces, alerts, incidents | `standards/17-observability.md` |
| **Setup, prerequisites, secret/token inventory, `.env`** | `standards/18-setup-and-environment.md` |
| **Cloudflare: DNS, TLS, WAF, cache, Tunnel, Workers, R2** | `standards/19-cloudflare-and-edge.md` |
| **Server/application hardening, security headers, IIS/Docker** | `standards/20-hardening.md` |
| **Backup, restore drills, RPO/RTO, disaster recovery** | `standards/21-backup-and-recovery.md` |

Templates: `standards/templates/` — project CLAUDE.md, **SETUP.md**, PR, ADR, user story.

## Working method (for Claude)

The method itself is **not repeated here.** It is in `CLAUDE.md` › "Working method
(for Claude)", in full, and in `standards/00-working-method.md` in detail. A copy in
the log would be a third place for the same seven bullets to drift in — and this
section exists for what the log is for: the incidents that produced them.

### ⚠️ A commit that bundled two unrelated tasks

Its message describes only the reporting change, but it also carried the first
half of the shell-coverage work: `scripts/tests/test_gate_core_fixes.py` and
`test_gate_core_docs.py` were changed to run **the real `scripts/gate-core.sh`**
instead of copying it into each throwaway repository. That is a real change with
its own reason (a coverage tracer attributes execution to the file it actually
ran, so a copy leaves the script at 0% however many tests exercise it), and it
belonged in its own commit per #26 step 3. `git add -A` swept it in.

The change is correct and verified — the two invocations produce byte-identical
output, because gate-core.sh resolves its root with `git rev-parse
--show-toplevel` and cd's there, so the cwd decides what it inspects and not
where the file sits; 31 tests pass against the real path. It is recorded here
rather than rewritten out of history, because amending a pushed commit needs a
force push.

## STATUS REPORTING during a long gate/run — the dashboard was removed

**The rule now:** report a long gate, run or deploy as a **short markdown table in the
reply**. No Artifact dashboard, no published board. The table carries the item, its
state, the measured figure **with the signal it was read from**, and what it is waiting
on — plus a time estimate split into what is mine and what is the user's.

**Why the dashboard went.** It was published, kept current at the same URL, and then
the same content was repeated as text in the reply because "a text report does not
replace the dashboard". That cost a round of work per report and, worse, **split the
record in two**: the moment one side was updated and the other was not, the reply and
the page disagreed, and the reader had no way to tell which was current. The table in
the conversation is the thing the user actually reads, so it is now the whole
deliverable. User decision.

**What was kept, because it was never about the dashboard:** figures are measured and
name their signal; an unmeasurable figure says "cannot be measured"; a step that did
not run is reported as "did not run" and never folded into a pass; a long run's output
goes to a log file instead of a buffering pipe (`tail`/`head`); an inferred state says
it is inferred; an over-optimistic estimate is corrected downward out loud.

**29/09/2026 — the local live board is allowed back, as an extra view (user
decision).** The user wanted to watch, while Claude works, which task is where and
which agent runs on it, and to remove tasks and switch agents off without typing.
It does not bring back what sank the dashboard: **Claude does not write the page**
— hooks record agent start/finish, so there is no second record to keep in step by
hand and no round of work per report; the page is served on `127.0.0.1` and never
published; and the table in the reply stays the report (`CLAUDE.md` STATUS
REPORTING, `standards/22-live-board.md` §3). What it adds is control: a removed task
or a switched-off agent is enforced by a `PreToolUse` hook, not by memory. Cost was
measured before adoption (`22` §4): silent hooks cost no tokens, ≈1.8-2k tokens per
7-task hour, 65 ms per tool call. Found while building it and pinned by tests: a
denied spawn was being revived by a stray `PostToolUse`; a declared EMPTY role set
(mode A) meant "no limit" instead of "no agents" — now fail-closed (#6); a refused
control's error was wiped by the refresh that followed it.

**29/09/2026, same day — it starts by itself and shows every project (user request).**
A board started by hand in a terminal died with the terminal, and one server per
project would have meant one port and one page per project. Now a `SessionStart`
hook registers the project in a machine-wide list and starts ONE server if none
answers; the page has a tab per project. Chosen over a launchd service because it
lives in the same opt-in settings block, needs no per-machine service file, and is
up exactly when Claude is working. Pinned by tests: parallel registrations do not
drop each other (removing the lock fails the test), a foreign service or an older
one-project server on the port is reported, never replaced, and no test touches
the real registry or port.

**29/09/2026, same day — decisions from the board (user request).** Claude marks a task
`needs_decision` with its question and options; the page shows the choices. An idle
session cannot be woken from outside, so a click reaches Claude mid-turn through the
existing reminder, or at the end of a turn through the Stop hook, which waits
`BOARD_DECISION_WAIT` seconds (user's choice: configurable, default 180) and blocks the
stop with the decision. Found while designing it: a subagent's tool call (modes C/D/E)
was consuming board notices meant for the orchestrator — now only the main thread
does. A board click is steering, not approval: promotion, deploys and deletions still
need the user's yes in the chat. Pinned by mutation: removing the subagent guard, or
letting any change (not only a decision) prolong a turn, fails a test.

<details>
<summary>The retired dashboard rule, as it stood until recently</summary>

### LIVE DASHBOARD during a long gate/run (RETIRED)

When you start a gate, run or deploy that takes minutes (merge gate, CI, test
battery, publish/deploy chain, migration), **publish an Artifact dashboard and keep
it current by republishing to the SAME URL throughout the run.** A text report does
not replace the dashboard; give both.

### What the dashboard MUST contain

1. **A weighted overall percentage.** Break the work into items, weight each by the
   *effort remaining* (totalling 100), and sum the weights of what is complete. An
   unweighted "5 of 10 items done" is misleading — a review of 473 commits and a
   one-line config change are not the same thing.
2. **Per-item breakdowns.** The sub-steps of the running item must be individually
   visible; the percentage is computed from the breakdown, not from a guess.
3. **A live measurement.** The time of the last measurement, the raw data measured
   (processes, memory, SHA, file timestamps) and which stage that measurement
   corresponds to.
4. **Open risks and blockers.** Every item awaiting a decision or blocking the next
   one, with its reasoning.

### Permanent rules

- ⚠️ **The percentage is MEASURED, not invented.** State on the dashboard which
  signal you read it from (process signature, file timestamp, API result). If you
  cannot measure it, give a range and say "cannot be measured".
- ⚠️ **An over-optimistic estimate is an ERROR and gets corrected.** If the
  percentage drops once you produce the breakdown, drop it and say why — never
  round quietly upward.
- ⚠️ **Never pipe a long run's output into something that buffers** (`tail`/`head`):
  no intermediate progress can be read until the job finishes. Write to a log file
  and feed the dashboard from that.
- ⚠️ **If stage detection is indirect, SAY SO** ("I am inferring it from the process
  count"). An indirect measurement can be wrong; the reader must know what they are
  looking at.
- ⚠️ **Republish to the same file path** — do not produce a new URL, the user is
  keeping the tab open.
- The user sets the reporting interval; if they do not, report on stage changes.
  Pass a short line even on unchanged turns — do not go silent.

</details>

## Appendix — the fuller original wording of rules that were shortened

### Global working rules

> Project-specific rules live in the project's own `CLAUDE.md` and **override the
> rules here**.

### §17 — A single origin is preferred

The API is served **under** the UI's domain (`app.example.com/api/*`); a separate
`api.` subdomain is the exception and requires an ADR. The gains: no CORS,
httpOnly+SameSite cookies work, a single certificate/DNS/WAF, the backend topology
stays hidden, and web plus mobile share one base URL. The SPA fallback must **not**
cover `/api/*`.

### §19 — Security scanning is automatic

Clause dropped when the rule was shortened: in secret scanning, an allowance is
granted **to a value, not to a path**, and its narrowness is verified by mutation.

### §20 — An autonomous background agent is never started without asking

If such a job is already running — whether I started it or found it in another
session — **report it proactively**: what it is doing, which decision or approval it
is waiting for, that it is consuming tokens and resources, and how to stop it.

⚠️ **APPROVED, but CONDITIONALLY:** long work may be left to run to completion, with
the user contacted if a question arises. The conditions and stop rules are in
`~/.claude/modes/autonomous-run.md` — task list, definition of done, **$100** budget
ceiling, stall brake, STOP on any irreversible action. If any condition is absent
the run does not start and the rule applies in full again.

### §24 — Completeness check

Clauses dropped when the rule was shortened: edge cases and error paths are
considered **if the relevant standard covers this task**; and for multi-layer work
the question is whether all of them changed **or one was forgotten**.

### §34 round (17/10/2026) — lines shortened in `CLAUDE.md` to make room for rule 34

The size ceiling is a ratchet, so adding #34 meant moving words out of the active file. Each original line is kept
here verbatim (`scripts/md-rule-gate.py` checks that none was lost).

> 25. **The gate is SHARED and runs at every promotion; running e2e is OPTIONAL (#33).** Two layers: `scripts/gate-core.sh <dev|test|prod>` owns the SHARED STEP SET (canonical copy in the configuration repository, a committed copy in every project), and the project's own `scripts/merge-gate.sh` stays the orchestrator (pull, merge, push, project extras) and CALLS the core. A project's gate cannot depend on a path outside the repository, because CI runners do not have the configuration checked out. `gate-core.sh <target> --list` prints what would run without running it.
>  - **`feature/* → dev` and `dev → test`:** EVERYTHING EXCEPT RUNNING E2E — formatter/linter, typecheck, build, unit tests, **coverage: the 80% threshold per codebase (#29)**, secret scan, dependency CVE, SAST, backward-compatibility scan, the CLAUDE.md size and rule gates, and a **CHECK for missing e2e specs** — a **warning**, never blocking (#33).
>  - **`test → prod`:** the gate does **not** check the `test` branch or the test environment, and e2e is **not run** — it warns for both (#33).
>  - **`test → prod` does NOT check the `test` branch or the test environment either** (user decision 04/10/2026, general rule): a branch may go to `prod` without having been on `test`. The gate WARNS it was not checked; `GATE_CHECK_TEST_DEPLOY=1` verifies the deployed SHA and a mismatch then blocks. The missing-spec check stays a warning. No hotfix exception is needed.
>  - ⚠️ **The configuration repository's own layout:** branches `dev` / `test` / `prod`. The live config is the **installed `adyusuf` plugin, copied from `prod` by `/plugin update`**; work happens in a separate `dev` worktree (try it with `claude --plugin-dir`) and reaches the live config only by promotion, which Claude performs (`standards/00-working-method.md` §7a). Commit only your own diff. → rationale: `docs/decision-log.md` §26
>  - Say "done" only after passing the check; do not narrate the check, fold its result into the report.

### §34 round 2 (17/10/2026) - lines shortened again in `CLAUDE.md` to make room for the target and push questions

Original wording, verbatim:

> 34. **Ask before every merge what runs; a waived gate is RECORDED, never silent.** Before any `dev`/`test`/`prod` merge ask two SEPARATE questions, "Will **CI** run?" and "Will **e2e** run?" (no merge before both answers). **Yes** → wait for CI to be green at that stage. **No** → the merge commit carries `Gate-Waived: <skipped gates> (neden: <the user's words>)`. Before a `prod` merge list those lines between the two refs, say which commits ran without which gates, and prepare nothing until the user answers. Each project names its gate's **owner** (CI where its minutes are free, else the local gate); a gate that did not run did not pass, whoever owns it, and #29 is never waived. → `standards/13-pr-and-review.md` §8a; `docs/decision-log.md` §34
>  - **How to apply:** at the start of EVERY session, before any work, **ASK** the mode (A–E) and what replaces Opus (keep · sonnet · haiku · fable) in one `AskUserQuestion`; the answer is written with `--tek` and the session runs on it. Preselected = the read order: **a session-scoped selection** → the project's `.claude/mode` → **B**. Agents and non-interactive runs never ask; they use that order. If a mode name is given, run `/adyusuf:working-mode`. → `modes/README.md` › Session start; `docs/decision-log.md` §27
>  - Every promotion to `test` and to `prod` **WARNS "e2e was NOT run"** and carries on; the warning is part of the report and never reads as a pass. Run it by hand or with `GATE_RUN_E2E=1` (a red result then blocks like any step).

### §34 round 3 (17/10/2026) - the `prod` push is no longer the user's; the push question became a list

Original wording of the lines changed in `CLAUDE.md`, verbatim:

>  4. **Claude performs the `dev`/`test`/`prod` merges and the `dev`/`test` pushes; the `prod` push stays the user's** — never `--force`, not over a red gate (#25, #33).
> 34. **When the code is done, ask where it goes and what runs; a waived gate is RECORDED.** Ask the user which of `dev`/`test`/`prod` it may be merged into (they pick). For EACH picked merge ask SEPARATE questions: "Will **CI** run?", "Will **e2e** run?", "May it be **pushed**?" (one answer each; nothing is merged or pushed before its answers). **CI yes** → wait for CI green at that stage. **No** → the merge commit carries `Gate-Waived: <skipped gates> (neden: <the user's words>)`. Before a `prod` merge list those lines between the two refs, say which commits ran without which gates, and prepare nothing until the user answers. Each project names its gate's **owner** (CI where its minutes are free, else the local gate); a gate that did not run did not pass, and #29 is never waived. → `standards/13-pr-and-review.md` §8a; `docs/decision-log.md` §34

Also in round 3, verbatim:

> 33. **E2E is OPTIONAL — no gate runs it and it never blocks a promotion** (user decision 03/10/2026, general rule: not enough resources to run it).
> - ❌ Pushing directly to `main`/`prod`

### §34 round 4 (17/10/2026) - defaults instead of questions

Original wording of the lines changed in `CLAUDE.md`, verbatim:

>  4. **Claude performs the `dev`/`test`/`prod` merges and pushes, each only after #34's questions** — never `--force`, not over a red gate (#25, #33).
> 34. **When the code is done, ask where it goes and what runs; a waived gate is RECORDED.** Ask which of `dev`/`test`/`prod` it may be merged into. For EACH picked merge ask SEPARATE questions: "Will **CI** run?", "Will **e2e** run?", then list what the push would send and ask which of it may be pushed (one answer each; nothing merges or pushes before its answers; Claude pushes, `prod` too). **CI yes** → wait for CI green at that stage. **No** → the merge commit carries `Gate-Waived: <skipped gates> (neden: <the user's words>)`. Before a `prod` merge list those lines in the range, say which commits ran without which gates, and prepare nothing until answered. Each project names its gate's **owner** (CI if its minutes are free, else local); a gate that did not run did not pass, and #29 is never waived. → `standards/13-pr-and-review.md` §8a; `docs/decision-log.md` §34
>  - **How to apply:** at the start of EVERY session, before any work, **ASK** the mode (A–E) and what replaces Opus (keep · sonnet · haiku · fable) in one `AskUserQuestion`; the answer is written with `--tek` and the session runs on it. Preselected = the read order in `modes/README.md`. Agents and non-interactive runs never ask. If a mode name is given, run `/adyusuf:working-mode`. → `modes/README.md` › Session start; `docs/decision-log.md` §27
>  - **A** Skill (no agents) · **B** Selective (`analyst`/`test-writer`/`doc-writer`) — **DEFAULT** · **C** Full team (9 roles) · **D** Wide team (14 roles) · **E** Fan-out (`Workflow`). The Agent Teams modes (X/Y/Z) are **archived** and not offered — `modes/archive/`.

### §27 round 5 (17/10/2026) - the session-start question was removed

The section of `modes/README.md` it replaces, verbatim:

> ## Session start — ASK the mode and the Opus replacement (PERMANENT, all projects; user decision 05/10/2026)
>
> Every interactive session begins with **one `AskUserQuestion`** carrying two questions,
> **before any other work** (reading the mode files is the only thing that comes first):
>
> 1. **Mode** — the recommended option is the read order's result (a `--tek` selection →
>    `.claude/mode` → B), or the lowest sufficient mode for the first request when that is
>    higher (the rules of the next section); up to three other letters; "Other" takes any
>    letter.
> 2. **What replaces Opus** — `Keep the defined models` (recommended unless a
>    `mode-model` exists, which is then preselected) · `sonnet` · `haiku` · `fable`.
>
> The answer is applied as `/adyusuf:working-mode <letter> [<model>] --tek` — written to the
> session scratchpad (`$S/mode`, `$S/mode-model`), **never** to the project file — and the
> session's work starts on it. The first request is then carried out in the same turn.
>
> **Not asked:**
> - the user's first message already names the mode (`C sonnet`, `/adyusuf:working-mode …`)
>   → that is applied instead;
> - `$S/mode` already exists — the same session after compaction, already answered;
> - a subagent, a `Workflow` agent, a teammate — they never ask the user;
> - a non-interactive run (`claude -p`, a scheduled task, an autonomous run, a cloud session
>   with nobody to answer) → the read order applies silently.
>
> If the question is dismissed unanswered, the read order applies and the work continues.
>

### §34 round 4 - standards/13 §8a as it was before the configuration

Verbatim:

> ## 8a. Before every merge: ask what runs, record what is waived (global rule #34)
>
> The full gate has one **owner** per project, named in the project's own `CLAUDE.md`: **CI** where its minutes are
> free (an open repository), the **local gate** (`scripts/merge-gate.sh`) where they are not. The owner runs the
> whole shared gate (§4, coverage ≥ 80% included); the other side is a pre-check at most. CI and the local script
> call the same `gate-core.sh` with the same thresholds, never two rule sets (#19).
>
> **The questions come when the code is done, in this order** (user decisions of 17/10/2026). Use `AskUserQuestion`; a
> batch merge (§8) is one merge, so it gets one set of questions, and an answer given for an earlier merge never carries over.
>
> 1. **Where may it go?** One multi-select: which of `dev`, `test`, `prod` the finished code may be merged into. Only the
>    picked targets are touched; unpicked ones are left alone, and a pick does not imply the next stage (§8).
> 2. **For each picked merge, separately — one question, one answer each, never "CI and e2e?" in one sentence:**
>    - This merge is `<source>` → `<target>` (`<short sha>`). Will **CI** run for it?
>    - Will **e2e** run for it?
>    - **What may be pushed?** Not a blanket yes/no: list what the push to `origin/<target>` would send — the commits
>      (`git log --oneline origin/<target>..<target>`), tags, and any other ref it would update — and let the user pick from
>      the list (a multi-select, with "none" as an answer). Merging and pushing are two decisions, and **Claude makes the
>      push itself, `prod` included** (user decision of 17/10/2026, which replaces "the `prod` push stays the user's").
>
> Nothing is merged before its CI and e2e answers, and nothing is pushed before its push answer. What is not picked stays
> local and the report says so; a pick never reaches past what was listed.
>
> | Answer | What happens |
> |---|---|
> | CI **yes** | Wait for CI to be **green on the commit being promoted** — on `dev` before the merge to `test`, on `test` before the merge to `prod` (the project's CI-status helper, or `gh run list --branch <b> --commit <sha>`: only a *completed* run with conclusion *success* counts; running, queued, red, cancelled and no run at all are not a pass). |
> | e2e **yes** | Run it as the project defines it (#33: optional, by hand or `GATE_RUN_E2E=1`) and report the result. |
> | CI or e2e **no** | The merge commit message ends with one line naming **only what was skipped**, in the user's words: `Gate-Waived: ci, e2e (neden: <reason>)`. |
>
> The line sits in the merge commit's body (a `--no-ff` merge, §8), one `Gate-Waived:` line per commit; `neden:` is
> the literal the user gave, and a scanner accepts `reason:` too. **Nothing is waived without the question and
> without the line**, and a waived gate is reported as "did not run", never as passing (#15, #25).
>
> **Before a `prod` merge**, scan the range being promoted and say it plainly — for example `git log --format=%B
> origin/prod..origin/test | grep '^Gate-Waived:'` (a project may ship a helper; the Claude Monitor repository's
> `waived-gates.sh <source> <target>` lists commit, gate and reason, exit 1 when any):
>
> > These commits ran without these gates: `<sha>` — `<gates>` (`<reason>`). …
>
> The prod merge is not prepared until the user answers. With no record, say "no waived gate in `origin/prod..origin/test`".
> The `prod` push is made by Claude after the push list is answered (§8a, #26.4).
>
> **What this never loosens:** coverage ≥ 80% per codebase (#29) is part of what the owner runs and is not a
> waivable gate; secrets stay out of the repository (#3); a red result is not waved through by an answer to this
> question (§8, point 5). The question is about gates that were *not run*, not about gates that failed.
>

## Measurement record — the token-reduction round

The question was where the operating-mode structure and the SDLC flow were spending
tokens unnecessarily, and which steps were being repeated when running once at the
end would do.

**Measurement:** the median fixed prefix was 57,756 tokens, an **18% share** of cost,
and it had grown 27,700 → 63,500 tokens (2.3x) over fourteen weeks. Across the
subagent runs in the same window the median was 52,313 tokens. Method and repeat instructions: `~/.claude/measurement/prefix-measure.py` (local-only tooling),
`standards/00` §6b.

- **§21-23:** the X/Y/Z team modes were moved to `modes/archive/`. They cannot be
  started today (the role allowlist has no `SendMessage`/`Task*`, and the feature
  sits behind a flag and a plan gate), yet their ~16 KB of rules were being loaded
  every session. The condition for bringing them back is in
  `modes/archive/README.md`.
- **§28:** the "completeness check" text in the 14 agent files was a literal copy
  (~24 KB in total); it was reduced to a single version, with the full rule in
  `role-selection.md` §7. The orchestrator writes one evidence-carrying line per
  handoff, and the full block once at the end of the turn and on every "YES". Rationale: the role's own block already carries
  the evidence, and the orchestrator's copy repeated it — which in D/E meant 14
  blocks.
- **§33:** the "was an e2e spec written" check in the `dev`/`test` direction was
  **removed**. It blocked nothing, and the list of gaps it produced was
  **recomputed** at step 2 of the `prod` gate — an output produced twice and used
  once.
- **§25/§26:** the formatter/linter runs **once at the end of the task list**, not
  on every `feature → dev` merge. The `dev` merge gate is build + fast unit tests,
  which is what covers the risk of a broken `dev`, whereas formatter output was
  being re-read on every task. The scope note in `standards/13` §4 was updated
  accordingly.

⚠️ In this round the `CLAUDE.md` size gate stayed red across two commits and only went
green on the third attempt — the gate itself worked, but each commit that claimed to
fix it was written without measuring first. Lesson: the size gate is run BEFORE
committing.

## MCP channels to reach an idle session — measurement (30/09/2026, T-24 phase 1)

Question: can the live board push a new task into an IDLE Claude Code session? Hooks
cannot (they need a running turn). Claude Code 2.1.281 has MCP channels.

- **Measured:** a minimal stdlib stdio server (capability `claude/channel`) pushed a
  message into an idle interactive CLI session; the session woke and answered correctly
  (2/2). Enqueue → dequeue 20 ms. The notification shape is `params: {content, meta}`
  (reference: the official `fakechat` channel plugin).
- **Constraints found:** a manually configured server needs
  `--dangerously-load-development-channels server:<name>` plus a startup confirmation
  dialog; claude.ai Teams/Enterprise needs `channelsEnabled: true`; a server that
  negotiates a "modern" protocol revision is skipped by the client (the probe echoing the
  client's protocol version was NOT skipped); the desktop app passes no channel flag.
- **Decision:** channels are an OPTIONAL extra for terminal sessions, never a replacement
  for hooks (deterministic, zero tokens, can block). Phase 2 (a board channel server,
  UI toggle) depends on T-23's session registry and control queue and is built after
  T-23 is on `dev`.
- **Why the probe is not committed:** it was a throwaway measurement; the product server
  (phase 2) will carry tests and coverage (#29).

## Background task names show their cost (01/10/2026, user decision)

Question that prompted it: "do the background tasks running now spend tokens?" — the
answer needed a `ps` listing and a paragraph, because nothing in a task's name said
whether a model was running in it.

- **Decision:** a task in which no model runs is named `FREE - <name>`; a task in which a
  model runs starts with that model's name. The prefix covers background `Bash`, `Agent`,
  `Workflow`, scheduled tasks and the board row. → `standards/00` §10c.
- **Why a prefix and not a column:** the name is the one thing every view shows (the
  task list, the board, the notification), and it is read before anything else.
- **Boundary:** FREE describes the task, not the session — the notification that wakes
  the session when a FREE task ends is a turn of the session.

## Dependency-audit triage: a written, expiring acceptance (01/10/2026, T-58, user approved)

- **Trigger:** a project's mobile app had one HIGH advisory left (`image-size`, a parser DoS
  in a bundler-only package) that its parent tool pins to a vulnerable major; the fix exists
  only in a major the parent does not accept. `npm audit fix` cannot reach it.
- **Tried first, rejected:** a `package.json` override to the fixed major. The audit went
  clean and `tsc` and the unit tests stayed green, but the real Metro bundle FAILED (control
  without the override: succeeded). Lesson: a dependency override is verified by building the
  artifact, not by the unit suite.
- **Decision:** `audit-triage.tsv` + `scripts/audit-triage.py`. The step runs
  `npm audit` as before; only on failure does it ask the helper whether every HIGH/CRITICAL
  advisory has an entry with a reason and an unexpired date. No file → no waiver; expired → no
  waiver; an unparseable report or a finding with no advisory behind it → exit 2 (fail closed).
- **Scope:** npm only; `pnpm audit` is unchanged. The audit level is not lowered, the step is
  not removed, and a project lists each advisory by id — the rule itself stays on (#19).

## The live board became its own repository, claude-monitor (01/10/2026, user decision)

- **Decision:** the application (hooks, CLI, server, page, cost, their 264 Python and 96 Node tests and the
  design doc) moved to <https://github.com/adyusuf/claude-monitor>, **public**, in `~/ClaudeCode/claude-monitor`.
  This repository keeps what is about bringing it up and using it: `standards/22`, the `board-plan` skill, the
  hook block in `.claude/settings.json`, and launchers at the stable `~/.claude/scripts/board/` path.
- **Why launchers, not a changed path:** the hook block is committed in every project that enabled the board;
  a new path would have meant editing all of them in step. The launchers keep that path valid and make an
  update `git pull` in the clone.
- **Why a fresh history:** the old history of these files carries real project names and measurements from
  private projects (`real-name-check.sh` exists because of three such leaks). A public repository starts from
  a scrubbed tree; the history stays here.
- **Fail-soft by design:** with no clone present a hook exits 0 silently (it runs on every tool call), session
  start prints one clone line, a typed command exits 2. A machine without the clone has no board, never a broken
  session.
- **Rule #29 in the new repository:** coverage is measured per codebase there (Python and JavaScript); the shared
  gate copies beside the application are not traced, and `scripts/coverage.sh` says so in its header.


## The gate core is four twin files, listed once (02/10/2026, user decision: option B)

- **Why:** `scripts/gate-core.sh` had grown to 554 lines, against global rule #9 (no file over 300 lines).
  Options weighed: leave it and write an exception into #9 (A); split it into libraries that are twins too (B);
  have every project fetch the core from this repository (C - rejected: it breaks rule #25's premise that a
  project's gate cannot depend on a path outside its repository, because CI has no configuration checkout).
- **Decision:** B. `gate-core.sh` (260 lines) orchestrates; `gate-lib.sh` (helpers, stack detection, verdict),
  `gate-lib-node.sh` (the Node steps and the parallel track) and `gate-lib-prod.sh` (the test -> prod steps) are
  sourced from beside it. The code moved by line range and was not rewritten: the old and the new gate gave
  identical output on 48 runs (`--list` and real, serial and parallel, dev/test/prod, four fixture projects).
- **Fail closed:** a core copied without its libraries exits 2 and names the missing file; it never runs a
  partial gate. A project still on the old single file keeps working until it takes the new four.
- **One twin list:** `scripts/twins.txt` is read by both `md-hook.sh` (a project against the live copy) and
  `twin-drift.sh` (every project's `origin/dev` against this branch). Before, the two kept separate lists that
  had already diverged (`audit-triage.py` was in one, `evidence-block.schema.json` in the other). A missing list
  is announced (hook) or refused (drift check), never treated as "nothing to compare".
- **How to apply:** a new gate file is added to `twins.txt` in the same commit; a project takes all four gate
  files together (`cp scripts/gate-*.sh`). Rollout is project by project; `twin-drift.sh` shows who is behind.

## Human actions are written down in one file (03/10/2026, user decision)

- **Trigger:** after a long run in a project the things only a person could do — decisions not
  delegated, approvals, secrets and console steps, a `DROP` Claude was not allowed to run, claims
  left unverified — were spread over the final reply, `<TODO>` fields in documents and a
  "reported, not fixed" list. Nobody could answer "what is waiting on me?" from one place, and a
  line in the chat is gone by the next session.
- **Decision:** every project keeps a human-actions file under its own docs folder (file name `human-actions.md`); Claude adds an entry in the same turn it
  finds the need, links the file in every final report, and never closes an entry itself. Rule text:
  `standards/00-working-method.md` §14; template: `standards/templates/human-actions-md.md`.
- **Where it lives:** in standards, not in `CLAUDE.md`. The root file is at its size ceiling and "a new
  permanent rule goes into standards/ first" (§6a); the working-method paragraph there already points
  at `standards/00`, which is where this rule is read.
- **Not done:** the project-documents step of `gate-core.sh` does not check for the file. Doing so is
  a separate request (it changes a shared, twinned gate).

## The gate finds an e2e suite inside the web tier (03/10/2026, user instruction "fill the accepted gaps")

- **Trigger:** a project that keeps its Playwright suite in `web/e2e/` (market-copilot) was reported by the
  shared gate as "no e2e suite": the detection looked for `e2e/` or `tests/e2e/` at the root only. The project
  had to list the e2e spec check as an ACCEPTED GAP although it had a real suite, and on the `prod` path the
  suite would not have run at all ("nothing proves this promotion").
- **Decision:** `gate-lib.sh` also looks for `<web tier>/e2e` (the same `WEB_DIR` the lint/tsc/test steps use);
  the prod step runs the suite from the directory that holds it; the spec check treats `<dir>/e2e/` as spec
  territory (a change to a helper there is not "behaviour"). A web directory with no `e2e` folder is still
  "no suite", and a root suite still runs from the root.
- **Effect on projects:** none until they copy the new twins; a project that listed the spec check as an
  accepted gap because of this blind spot can then remove the entry. Tests: `test_gate_core_prod.py`
  (3) and `test_gate_core_fixes.py` (3); the detection was mutation-checked.

## The board stayed empty during a long session (03/10/2026, user report "no tasks on the board")

- **What happened:** one session in a board-enabled project made 100+ tool calls over several hours and
  the live board page listed no task. The hooks had recorded 45 events (turns, a subagent stop), but not one
  task.
- **Why (root cause, in order):** (1) the board has two sources — hooks record agents by themselves, the
  *plan* exists only when the session runs `board.py add|set`; (2) the session worked in mode B and called no
  agent, so the hooks had nothing to turn into a row; (3) the plan step lives in the `board-plan` skill, whose
  trigger ("whenever work splits into 2+ pieces") depends on the model remembering to use it, and it did not;
  (4) `/adyusuf:apply-project-standards` §6a *enables* the board but never says "now plan on it", and §3 calls
  the board "an extra view", which read as optional; (5) nothing detected the omission, so it ran for hours.
- **Fix, three parts:** the rule is now binding and says when (before the first piece) — `standards/22` §3;
  the monitor detects the omission — `board_nudge.py` (PostToolUse, once per session after
  `BOARD_NUDGE_AFTER` calls, claude-monitor docs §2j); and the session wrote the missing plan and uses the
  board from then on.
- **Not done:** no block, no gate. A reminder is advisory by design: a one-step question must not be forced
  through a plan. Making it a gate step would be a separate request.


## Mode + model: `<letter> <model>` runs only the Opus agents on another model (05/10/2026, user decision)

- **Request:** "agents keep the models they were given, but I want to be able to turn the
  Opus ones into Sonnet": the letter alone keeps the defined models; `<letter> <llm>` makes
  only the Opus agents use `<llm>`. A general rule.
- **Decision:** `modes/README.md` › *Model override*; the skill writes the word to
  `mode-model` beside `mode` in the same layer (project or `--tek` scratchpad) and the
  letter alone deletes it. Applied through the `Agent` tool's `model` override, which
  takes precedence over the definition's frontmatter.
- **Why a separate file:** `.claude/mode` is parsed as one letter by the live board
  (`board_api.py` in claude-monitor) and by other readers; a second word there would
  break them (#4, additive only).
- **Boundary:** only downgrades — a Sonnet/Haiku agent is never raised. "Opus" means the
  model the agent would actually run on, so an inheriting agent in an Opus session counts.
  The role set and the audit chain do not change with the model.

## A non-FREE background task names its model everywhere (05/10/2026, user decision)

- **Request:** "in every background task, if it is not FREE, also say which LLM it uses".
- **Decision:** §10c's prefix already named the model in the task's *name*; the model now
  also appears wherever the task is reported — status table row, start/finish lines,
  the end-of-turn agent report. Under a mode override the name is the override's model.
  → `standards/00` §10c.

## One review, one test run, one gate — on the combined work (05/10/2026, user decision)

- **Request:** "in whatever mode, do not put the separate work of agents, subagents or
  background tasks through code review, tests and the gate separately; do what can be
  done together together. Each does its work, writes the code and the tests, finishes what
  it must do alone and hands off to the orchestrator; the orchestrator merges all the
  branches and runs one code review, one test run and one gate; the auditor also evaluates
  the test and gate results and sends back what it finds."
- **Decision:** `modes/README.md` › *One review, one test run, one gate*. `developer` and
  `test-writer` no longer run build/lint/tests; `qa` gains axis 7 (the combined run's
  results); `role-selection.md` §2 shows the combined flow; `standards/13` §8 step 1
  names the producers and the review.
- **What was already true:** `13` §8 batched the test run and the gate for promotions
  (29–30/09/2026). New: it reaches each producer's own work, the review is consolidated
  too, and the auditor's input is the diff **plus** the test and gate logs.
- **Narrow run allowed (same day, user answer):** two sessions wrote this rule in
  parallel — one committed (no run at all by a producer), one left uncommitted in the live
  worktree (a narrow run allowed, plus the auditor reading warnings, coverage and run
  validity). The user chose to merge both and to allow **a narrow run of the producer's
  own piece**; the full suite, the review and the gate stay on the combined branch. The
  rule now lives once in `CLAUDE.md` (#26.3), not under both #26 and #28.
- **Gain:** one review, one run and one gate instead of N, and the review sees the
  interactions between pieces.

## Every session asks the mode and the Opus replacement first (05/10/2026, user decision)

- **Request:** "when every session opens, ask which mode and what to use instead of Opus;
  the session starts accordingly."
- **Decision:** `modes/README.md` › *Session start*; #27's "How to apply" now asks instead
  of starting silently in B. The answer is written with `--tek` (scratchpad), so a
  per-session choice never rewrites the committed `.claude/mode`.
- **Boundaries:** not asked when the first message names the mode, after compaction
  (`$S/mode` exists), inside any agent, or in a non-interactive run — none of those has
  someone to answer, and asking there would stall the run. The old "start in B and
  propose" text survives as the source of the recommended option and as the rule where
  nobody can be asked.
- **Not done:** no `SessionStart` hook enforces it; the rule is in `CLAUDE.md` #27, which
  every session loads. A hook could inject a reminder if sessions are seen skipping it.

## IIS layout and names on Windows servers (06/10/2026, user decision)

- **Request:** "do the IIS site installations under `c:\iis`; `<domain>_<test|prod>` is the main folder
  and `api`, `web` … go under it; the IIS application and pool names are `<main folder name>_<api|web|…>`."
  The user's `pro` is read as `prod`, the name the environments already carry everywhere.
- **Why:** measured on the one Windows server on 06/10/2026 — 28 IIS sites, 26 of them other
  projects', their paths under `C:\inetpub\<project>` and `C:\Work\...`, their names in at least three
  styles (`KolektifAgProdApi`, `BTTakvimWeb`, `ClaudeMonitor-prod`). claude-monitor itself sat in a fourth place,
  `C:\ClaudeMonitor\<env>`, as `ClaudeMonitor-<env>`. A name seen in Task Manager or the event log did not
  say which domain or environment it served.
- **Decision:** `standards/20-hardening.md` §6a (the rule) and a one-line pointer in `14-devops.md` §1. The
  rule fixes the top two levels (`C:\iis\<domain>_<env>\<component>`) and the names, not what lies below a
  component folder.
- **One choice that was mine, flagged for the user:** the environment file, backups and archives sit BESIDE
  the component folders, never inside one IIS serves — the user said "api, web, etc. under it" and a secret
  file next to `web\` would be one mistake from being served.
- **Corrected the same day (user):** the first wording left it open whether `web` and `api` were separate
  sites or applications, and its names ended in `_<component>`. The user's answer: **do not split them into
  sub-applications and pools** — one site and one pool per environment, named after the main folder
  (`monitor.bitreka.com_prod`); the components are folders. The `_<component>` names remain only for a
  project that really runs separate sites. For claude-monitor this is also what the code does: the API
  process serves the web app itself (`MONITOR_WEB_ROOT`).
- **Not done at the time of this entry:** no existing deployment was moved. claude-monitor's server scripts
  (`deploy/windows/*.ps1`, scheduled tasks, `monitor.env`) used `C:\ClaudeMonitor` and `ClaudeMonitor-<env>`.
  The move follows as a deploy (below the standard's own "a move is a deploy" rule).

## Plugin install: a standard marketplace plugin, no symlinks, no install script (13/10/2026, user decision)

- **Request:** "my skills and my plugin will work in the standard way like the others · no symlinks ·
  the install will be standard too · no extra script will be needed".
- **Why:** measured on 13/10/2026. Every other plugin on the machine (27 in `installed_plugins.json`)
  is installed from a marketplace and **copied** to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`.
  `adyusuf` was the exception: `install.py` linked `~/.claude/{CLAUDE.md,agents,docs,modes,scripts,standards}`
  and `~/.claude/skills/adyusuf` (= `plugin/`, whose `skills/` and `commands/` are links again) into the
  checkout, and 57 files carried 200 fixed `~/.claude/...` paths (`git grep -o '~/\.claude' origin/dev | wc -l`). Symlinks need Developer Mode and
  `core.symlinks` on Windows, an edit in the checkout went live at the next session, and nothing had a version.
- **Decision (user, three choices):**
  1. **Source: GitHub `adyusuf/claude-code-standards#prod`.** Install is
     `/plugin marketplace add adyusuf/claude-code-standards#prod` + `/plugin install adyusuf@adyusuf-marketplace`.
     The plugin is copied to the cache; a promotion to `prod` reaches a machine only through `/plugin update`.
     A local-directory marketplace was rejected: Claude Code loads it **in place**, which is the symlink's
     "an edit is live at once" behaviour under another name (plugins/loading, "In-place and copied plugins").
  2. **Global rules: the plugin's own hooks.** A plugin cannot ship a `CLAUDE.md` that loads
     (`claude plugin validate` warns that a root `CLAUDE.md` "is not loaded"). `hooks/hooks.json` runs
     `scripts/rules-context.py` on `SessionStart` (plain text) and `SubagentStart` (`additionalContext`).
     Claude Code caps each hook output at 10,000 characters, so `CLAUDE.md` (23,309 bytes) is split at its own
     `## ` / numbered-rule boundaries into parts of ≤ 9,500 characters, one hook per part; four parts are
     registered and three are used. `CLAUDE.md` stays the single source.
  3. **Pilot first** (#1): the manifest, the marketplace, the rules hooks and one skill (`software-standards`).
- **Layout:** the **repository root is the plugin** (`.claude-plugin/plugin.json` + `marketplace.json`, source `./`).
  `skills/`, `commands/`, `agents/` are already at the standard places and `standards/`, `modes/`, `scripts/`
  travel inside the copy, so nothing moves. `plugin.json` sets **no `version`** on purpose: the version is then
  the commit SHA and every `prod` commit is an update. An earlier attempt on `wip/self-contained-plugin`
  (moving `skills/` and `commands/` under `plugin/`) left `standards/`, `modes/` and `scripts/` outside the copy;
  its marketplace name `adyusuf-marketplace` was kept.
- **Pilot evidence (13/10/2026, Claude Code 2.1.294, `--plugin-dir`, haiku):** all three rule parts reached the
  main session and a `general-purpose` subagent (each prints its `[Global working rules, part n/3 …]` header;
  the order varied: 3,1,2 and 1,3,2); `/adyusuf:software-standards` resolved `${CLAUDE_PLUGIN_ROOT}/standards/`
  to the checkout's `standards/`. `claude plugin validate .` passes with the two intended warnings
  (root `CLAUDE.md`, no `version`).
- **Not done yet (the rest of the plan):** the remaining `~/.claude/...` paths (3 changed in the pilot), the hooks `install-live-hooks.py` writes into
  `settings.json`, agent names becoming `adyusuf:<role>`, retiring the link part of `install.py`, `SETUP.md`,
  and moving this machine off its links (that last step needs the user's approval).
  ⚠️ **The pilot stays on its own branch** (`feature/plugin-marketplace-pilot`) and reaches `dev` only in ONE
  batch with the migration (#26). Reason (QA, 13/10/2026): the live install is still the skills-dir plugin at
  `~/.claude/skills/adyusuf` → `plugin/`, where `${CLAUDE_PLUGIN_ROOT}/standards/` does not exist, and any
  promotion from `dev` would carry the pilot to `prod` — a note is not a guard, keeping it off `dev` is.
  Installing the marketplace plugin on a machine that still has the links would also load the 14 roles a second
  time as `adyusuf:<role>` and the global rules twice in every project; the migration removes the links first.
- **Windows (open):** `hooks/hooks.json` calls `python3`, which the python.org installer does not provide
  (`SETUP.md` prerequisites). With the plugin install no `install.py` checks it, so every hook would fail
  non-blocking and sessions would run **without the global rules**. `SETUP.md` must state the prerequisite
  before the plugin install is advertised.
- **Known cost:** working inside this repository the rules load twice (project `CLAUDE.md` + the hook) — accepted;
  every other project loads them once.

## Plugin install, completed: no links left; the board's plan becomes a file (13/10/2026, user decisions)

- **Request:** "continue the rest of the plan" after the pilot, plus two fixes: the CLAUDE.md gate
  install in `apply-project-standards`, and `board-plan`, whose board had been removed.
- **Done (branch `feature/plugin-marketplace-pilot`, one commit per task):** skill, command and agent bodies
  read through `${CLAUDE_PLUGIN_ROOT}` (substitution verified for skills and, with a probe plugin, agents);
  the Markdown read with the Read tool uses paths relative to the plugin root, anchored by the rules-context
  header; the project template names the plugin; the guard and `md-hook.sh` are plugin hooks
  (a probe confirmed a plugin `PreToolUse` hook exiting 2 blocks the call); `install-live-hooks.py` and
  `install.py --remove` only take the OLD install out, and a `SessionStart` check
  (`legacy-install-check.py`) warns while it is still there; `install.py` installs only the monitor agent;
  `plugin/` is gone, and with it the last symlink in the repository.
- **Agents are `adyusuf:<role>`:** a probe showed a plugin agent is found ONLY by its namespaced name (a bare
  name errors "not found"), so the modes and the never-do line now say so.
- **`board-plan` (user choice of three: retire / local plan file / a claude-monitor feature → "local plan
  file"):** claude-monitor's cm-agent only observes (sessions, subagents, Claude Code's task tools) and gives
  Claude `monitor_status` and `monitor_note`; mode, roles, routing, task ids, semantic status and commits had
  no home. They now live in `.claude/board/plan-${CLAUDE_SESSION_ID}.md`, one file per session so parallel
  sessions never share one; `monitor_note` mirrors a status change when the agent is installed. The board's
  launchers, their test and this repository's board hooks were removed.
- **The CLAUDE.md gate install:** `--update` only lowers rows that exist, so the old instruction failed
  ("No budget file") or, with our budget copied, left the project's own files "NO BUDGET". `md-size-gate.sh
  --init` writes the project's own budget and never overwrites one (`fix/md-budget-init`).
- **Still open:** the machine migration (approval first): merge to `prod`, the user's push, then
  `install.py --remove --no-monitor` and the two `/plugin` commands, on every machine; on this one also the
  private claude-config repository's tracked links and its `pre-commit` hook that goes through
  `~/.claude/scripts`, and the local measurement ledger, which reads `~/.claude/scripts/`. Every project that
  copied the twin scripts gets one copy commit (comments changed). The retired board's hooks: the 7 user-level
  entries are now `LEGACY` (QA, 13/10/2026), so `--remove` strips them; **five projects** still carry 27 board
  entries in their committed `.claude/settings.json` — each is cleaned with `apply-project-standards` §6a.2 in
  its own repository (they fail silently, `|| true`, until then). `step-stats.py` (492 lines) exceeded #9;
  it was split on its own branch the same day (`fix/step-stats-split`: 247 lines plus three sibling modules,
  output byte-identical on fixtures and on live data).

## The monitor agent is optional; its absence is never a problem (13/10/2026, user decision)

- **Request:** "if cm-agent is missing or unreachable you just don't connect — don't treat it as a problem".
- **Decision:** claude-monitor's agent is optional everywhere. `install.py` reports a monitor that cannot be
  built, installed or connected as one ⚠️ line and still exits 0; `install.py --check` prints the monitor's state
  but does not count it; `/adyusuf:board-plan` uses `monitor_note` only when it is there; `standards/22` §4 says
  a missing, disconnected or unreachable monitor is not a finding, not a failed step and nothing to repair.
- **Context:** the same day a test mutation ran a real monitor install and pointed the user's real monitor
  plugin at a temporary agent; it was written back by hand with the user's approval (backup
  `~/.claude-standards/backups/monitor-repair-20261013-124139`). Afterwards `cm-agent status` said "not
  connected"; whether it was connected before could not be established — under this decision that is fine.

## `claude plugin validate` warnings are accepted; distribution channels (13/10/2026, user question)

- **Rule:** `claude plugin validate .` passes with exactly two warnings, and both stay. Do not "fix" them:
  - **No `version` in `plugin.json`.** With a version set, `/plugin update` reports "already at the latest
    version" until someone raises it by hand on every `prod` push. Without one the commit SHA is the
    version, so every `prod` push is an update. The plugin docs (plugins/publish, "Decide how you'll version")
    offer exactly these two options, and say to drop `--strict` when the version is omitted. Run
    `validate` without `--strict` here; neither CI nor the gate runs it today.
  - **The root `CLAUDE.md` is not loaded as context.** This is intended: the rules reach every session and
    every subagent through the `SessionStart`/`SubagentStart` hooks (`scripts/rules-context.py`). The file
    is also this repository's own rules file and the size gate's subject, so it does not move.
- **A third warning is a finding, not noise.** Any warning beyond these two is read and fixed.
- **Updates are not automatic.** Auto-update is off by default for a self-hosted marketplace. Each machine
  gets a `prod` push through one of two routes:
  - `claude plugin update adyusuf@adyusuf-marketplace`;
  - auto-update, switched on in `/plugin` → Marketplaces.
- **Anthropic's channels (measured from the docs, 13/10/2026):**
  - `claude-plugins-official` takes no submissions; a listing there goes through an Anthropic partner
    contact.
  - The open channel is the directory (`claude.ai/directory/manage`), which needs a paid plan and reviews
    every version.
  - claude.ai chat skips hooks and agents, so there the plugin would arrive without the rules, the guard
    and the roles. Cowork loads both.
  - No manifest field limits the apps a plugin installs on. A top-level `bin/` makes chat and Cowork
    refuse the whole plugin, and that is the only documented switch.
  - The user decided the same day: the plugin is Claude Code only (next section). Listing it in the
    directory is still the user's call.

## The plugin is Claude Code only (13/10/2026, user decision)

- **Question:** "can it be set up so it is not installed where it cannot load?"
- **Measured from Anthropic's docs** (claude.com/docs/plugins/platform-support): claude.ai chat skips hooks
  and agents, so there the plugin would run without the global rules, the guard and the 14 roles. Cowork
  loads both. No manifest field limits the apps a plugin installs on. A top-level `bin/` makes chat **and**
  Cowork refuse the whole plugin, and the directory portal derives the supported apps from the same rules.
- **Decision (user picked the first of three):** Claude Code only, through `bin/`. The other two options were
  rejected:
  - leaving it as it is, so chat gets the skills alone;
  - a second, skills-only plugin, which means two plugins to maintain.
- **The folder holds a real command, not a marker:** `bin/adyusuf-check` runs
  `scripts/install.py --check --no-monitor`. It reports the plugin and any leftover of the old link install,
  and exits 1 while there is something to do. It follows a link on `PATH` back to the plugin root.
- **Coverage:** `scripts/coverage-shell.sh` traces `bin/*` as well as `scripts/*.sh`. A shell command
  outside the denominator would loosen #29.

## The directory icon (13/10/2026, user decision)

- `.claude-plugin/icon.png` holds the author's own brand mark: a "b" with a green dot, no text. It is
  rendered at 1024×1024 from the author's site favicon (SVG) with `rsvg-convert`.
- ⚠️ **The directory takes the icon only once**, when the plugin is first saved or submitted in the developer
  portal. Replacing the file later does not change the listing, so this file is effectively permanent.

## `bin/` removed: the plugin is no longer Claude Code only (15/10/2026, user decision)

- **Reverses** "The plugin is Claude Code only" (13/10/2026).
- **Why:** Anthropic's directory flags any top-level `bin/` as "Ships executable files" (`BUNDLES_BINARIES`), and
  a reviewer must look at it. `bin/adyusuf-check` only wrapped `install.py --check`; the `SessionStart` hook already
  warns about an old install. The user decided it was not worth a dependency that existed only for the restriction.
- **What it means:** the plugin installs in Claude Code, Cowork and claude.ai chat.
  - Claude Code and Cowork load hooks and agents.
  - Chat runs only the skills and commands: no global rules, no guard, no roles.
  - `SETUP.md` §6 says so.
- **Removed:** `bin/adyusuf-check` and its test file (`test_bin_check.py`). The `bin/*` tracing in
  `scripts/coverage-shell.sh` is gone; the file is back to its earlier version.

## Proposal: the shared gate runs every test suite twice — one run should feed both steps (17/10/2026, measured in the Claude Monitor project)

**Status: a proposal for the canonical `scripts/gate-core.sh` and its libraries (they are twins, `scripts/twins.txt`);
nothing in this repository's copy was changed for it.** The project below worked around it without touching its copy.

- **Finding (measured, one project, `gate-core.sh dev`, same commit):** the "unit tests" step runs `dotnet test <sln>`
  and the web tests; the "coverage" step then runs the project's coverage command, which runs the API, the agent and
  the web suites AGAIN with coverage on. Each suite ran twice: 1128 + 1899 + 417 tests, the 1128 API tests taking about
  3 minutes each time. The whole gate took 657 s.
- **Result of running them once:** 450 s (−207 s, −31%) on the same code; every "Passed!" line appears once; line
  coverage identical (API 97.09%, agent 86.60% against 86.59% before, web 96.40%); threshold, exclusion lists and exit
  codes unchanged. The project's method: the test projects collect coverage when `COVERAGE_DIR` is set (an MSBuild
  property file for the .NET projects, the vitest config for the web), its `merge-gate.conf` sets `COVERAGE_DIR` and
  `COVERAGE_REUSE=1` for a gate run, and its `coverage.sh` judges the files instead of running the tests; standalone it
  still runs them itself. A missing or unreadable result is "NOT MEASURED" (exit 3), which blocks (#29).
- **Why the project could not use the documented override:** the header of `gate-core.sh` lists
  `LINT_CMD / TYPECHECK_CMD / BUILD_CMD / UNIT_CMD` as overrides, but no code reads them (`grep` finds the words only in
  that comment). Either implement them or delete the line; today the comment promises what the gate does not do.
- **Proposed in the canonical core:** (1) the unit step runs once and exports a fresh `COVERAGE_DIR` to the project's
  coverage command, which reuses it when it understands the variable and runs its own tests when it does not (nothing
  breaks for a project that has not adopted it); (2) implement the `*_CMD` overrides the header lists; (3) `export
  COVERAGE_MIN` after the conf is sourced: it is a plain shell variable today, so a project's `coverage.sh` never sees
  the conf's value (a `COVERAGE_MIN=99` mutation left that project's gate green). (4) A test of any tool the gate runs
  must not depend on variables the gate exports (`COVERAGE_*`): two new tests failed only inside the gate for that reason.

## Phased work stays on the on-screen task list; decisions are tasks; nothing is dropped (18/10/2026, user decision)

- **Trigger:** tasks disappeared from the on-screen list between turns — an interrupted request (a deploy check) was
  simply abandoned when a new message arrived. The user asked that phased, sequential work always stay on screen and
  never get lost.
- **Decision:** `standards/00-working-method.md` §1a. Phased work is listed with its phase from the first message;
  open choices are asked AND listed as `P0 · Decide …`, then collapse into a completed `Decided: …` line and expand
  into concrete tasks; related new work is inserted at its phase, unrelated work and interrupted tasks are queued as
  `Queued · …`; the list is resent whole on every change. A one-question/one-answer exchange gets no list.
- **Demonstrated** on "I want a sudoku mobile app" (no code written): platform → both, framework → React Native +
  Expo, backend → yes; the backend answer raised two more decisions (features, sign-in), and the answers expanded
  into API and app tasks, while the interrupted deploy report stayed queued at the end.
- **Not in `CLAUDE.md`:** the file is at its size ceiling (`scripts/md-budget.tsv`); a new permanent rule goes into
  `standards/` first. The `board-plan` skill points to §1a.

## The task list carries the delivery stages and follows the configuration (18/10/2026, user decision)

- **Decision:** `standards/00-working-method.md` §1a gains two bullets. The delivery stages (plan + analysis, code,
  unit tests, review, merge / gate / push, deploy, release) are list items, but only the stages that will really
  happen and whose turn can be seen — no deploy for an offline app, no e2e while no gate runs it (#33), the review
  the active mode has. The merge, gate and push items are derived from `/adyusuf:config` (#34): a target appears
  only if `merge.<t>` is yes, its gate only if `run_before_push.<t>.<gate>` is yes, its push only if `push.<t>` is
  yes; a setting changed mid-session is re-read at the next task and the list resent.
- **Demonstrated** on "I want a chess mobile app" (no code written): online multiplayer made a deploy stage appear;
  Stockfish's GPL made a source-publication item appear; with `run_before_push.test.unit` and `.prod.unit` yes and
  the dev gates no, the list showed "merge dev, push dev (no gate: config)", "merge test, unit gate, push test",
  "merge prod, unit gate, push prod".

## No relation to claude-monitor or its daemon; nothing connects, nothing is sent (20/10/2026, user decision)

- **Request:** "remove the standards' tie to the daemon, no relation to claude-monitor should remain" and "no
  connecting to the daemon, no sending messages".
- **Decision:** the rule set has no code, setting, document or example that installs, connects to, configures or
  messages claude-monitor's agent (`cm-agent`) or its server.
  - **Removed:** the monitor installer module (`install_monitor.py`) and its test; the monitor step, the `--prod`/`--test`/`--dev`,
    `--no-monitor`, `--with-monitor`, `--monitor-server` and `--monitor-sync` flags of `install.py` (it now prints the
    two `/plugin` commands and reports or removes the old link install); the `monitor.connect` and
    `monitor.message_format` settings and their line in the session-start block; the `monitor_note` section of
    `/adyusuf:board-plan` (the plan file is the only record); `CLAUDE_MONITOR_HOME` and `CM_AGENT_HOME` from
    `.env.example` and `SETUP.md`; the .NET SDK prerequisite (it existed only to build the agent); the monitor
    paragraphs of `README.md`, `PRIVACY.md`, `SETUP.md`, `scripts/README.md` and `standards/22`; the `monitor.bitreka.com`
    example in `standards/20`.
  - **Kept for compatibility:** a user's `~/.claude/adyusuf.json` written before this change still holds the two
    retired keys. `adyusuf_config.py` lists them in `RETIRED_KEYS` and skips them on read, so one stale key does not
    invalidate the whole layer; the next write drops them.
  - **Not touched:** an agent already installed on a machine, and the plugin entry `install.py` once registered for it
    in `settings.json`. `install.py --remove` no longer uninstalls it; that is the agent's own `cm-agent uninstall`.
  - **QA findings fixed in the same change:** the old-install notice (`legacy-install-check.py`) now prints the plugin's
    OWN `install.py --remove`, never the old checkout's (an older checkout's `install.py` still uninstalled the agent
    unless `--no-monitor` was given); `adyusuf_config.py apply` skips the retired keys a panel saved earlier still holds
    and says so; `notify` ignores them when it compares a session's seen state, so no false "settings changed" notice.
  - **History stays:** the entries above that mention claude-monitor describe what was true when they were written.
    They are the record of why, not a relationship; this entry supersedes the ones that made the monitor optional.

## The settings page (panel) is removed; the settings live in the right-hand rail (22/10/2026, user decision)

- **Decision:** `/adyusuf:config` has no settings page any more. The Artifact "adyusuf Settings" and everything that
  built it are gone: `skills/config/panel.template.html`, the `panel` and `panel-data` commands of
  `adyusuf_config.py`, "The panel" section of the config skill and their tests.
- **What replaces it:** the rail boxes the user meant by "the boxes on the right (Environment, Context, Connectors,
  Outputs, Changes)": the mod written 17/10/2026 in one session's own mods folder (so no later session had it). It is now
  part of THIS plugin (user decision 22/10/2026: "not a separate plugin"): `hooks/register.tsx`, listed under `modules` in
  `hooks/hooks.json` beside the command hooks, answering `/adyusuf:panels`; the logic is in `hooks/choose.ts`. Settings,
  Agents and Promotion boxes with checkboxes and dropdowns; each click runs `adyusuf_config.py set`. It finds the script
  through the `adyusuf` plugin the plugin manager records as installed (`installed_plugins.json`; QA found that "the
  newest folder in the cache" is a replaced version after an update), so retired settings vanish from the boxes once
  `adyusuf` is updated. The config skill sends the user to the boxes first and uses `AskUserQuestion` (buttons, checkboxes,
  dropdowns in the chat) only when they cannot be shown.
- **Rule #29, the one written exception (user decision 22/10/2026):** `claude plugin test` reports no coverage, so TypeScript
  that runs only inside the engine could not be measured. `standards/10` §7.2a: the logic (`hooks/choose.ts`, no engine
  import) is measured with Deno in `scripts/coverage.sh` and held to 80% (100% now, 34/34 lines); the engine glue
  (`hooks/register.tsx`) is the ONE listed file, reported "not measured, listed exclusion" in every run; anything else
  there that is not tested logic makes the run NOT MEASURED. Deno is a new prerequisite of the coverage gate (SETUP §1).
  The separate repository `~/ClaudeCode/adyusuf-panels` that was started for the mod is obsolete.
- **Kept on purpose:** `apply` and the read path still skip the two retired `monitor.*` keys, because a file written
  earlier may hold them; `group` stays in the schema (it titles the sections of `show` and the boxes).
- **Not done here:** the published Artifact is deleted separately (it is not in the repository).

## Settings: CI before merge, gates before push and e2e after deploy replace `run_before_push` (22/10/2026, user decision)

- **Decision:** the six `run_before_push.<t>.unit|e2e` settings are retired. Three groups, each per target, replace them:
  `ci_before_merge.<t>` (defaults dev no, test yes, prod yes), `gates_before_push.<t>` ("Run gates before pushing";
  dev no, test yes, prod yes) and `e2e_after_deploy.<t>` (dev no, test no, prod yes). Rule #34 (`CLAUDE.md`),
  `standards/13` §8a, `standards/00` §1a and the config skill say what each does: CI is waited for before the merge, the
  gates (unit tests, coverage, secret scan, SAST) run on the merged result before the push, e2e runs against the target
  after it is deployed, and only where the project has a suite and deploys that target. A CI that is not waited for is
  recorded as `Gate-Waived: ci`, gates that are not run as `Gate-Waived: gates`.
- **Compatibility:** a user's file that still holds `run_before_push.*` keeps working: the keys are in `RETIRED_KEYS` and
  skipped on read (the old values are not carried over; the new defaults apply). A file that holds the NEW keys is unknown
  to an older installed copy of the plugin, which then ignores that layer and says so, so update `adyusuf` before setting them.
- **Not changed:** #29 (coverage) is part of what runs at every promotion and no setting turns it off; e2e stays optional
  and never blocks a promotion (#33), so a red `e2e_after_deploy` run is reported, not a reason to refuse the merge.

## One script installs and updates the plugin from GitHub (22/10/2026, user decision)

- **Decision:** `scripts/plugin-setup.py` installs the `adyusuf` plugin and brings it up to date. It asks GitHub for the
  commit of the marketplace's branch and compares it with Claude Code's `installed_plugins.json`: not installed → link the
  marketplace and install; already newest → nothing; older → ask "Remove the old one and install the new one?" and on yes
  remove (`--keep-data`) and install in the same scope. The user's settings (`~/.claude/adyusuf.json`, a project's
  `.claude/adyusuf.json`), the enabled state and the marketplace link must come out unchanged; the script checks that and
  puts the settings file back from a copy if a replacement disturbed it. README Level 3 carries the download line.
- **Why a new file and not `install.py`:** `install.py` is documented, and tested (`test_install_run.py`), as contacting no
  server. The installer has to ask GitHub, so it is a separate standalone file; the "no server" claim stays true of
  `install.py` and the network use is listed in README › What this does to your machine and `PRIVACY.md`.
- **Why standalone:** it must run on a machine that has no checkout yet, so it imports nothing from `scripts/` and uses only
  the standard library (no new dependency, #10).
- **Fail-closed:** without a terminal and without `--yes` it does not replace anything; an unreadable marketplace list, a
  GitHub that does not answer, a marketplace linked to a non-GitHub source and a branch name that could pass for an option
  all stop the run before any change. A replacement that fails after the removal prints the retry command and exits 2.
- **Not changed:** the plugin still has no `version` (every `prod` commit is new), and `/plugin update adyusuf` remains the
  in-session way to update.

## The other install scripts are removed; the README opens with the macOS and Windows install commands (22/10/2026, user decision)

- **Decision:** `scripts/plugin-setup.py` is the repository's only install script. Removed: `install.py` (the check and the
  migration off the old linked install), `install_safety.py`, `install_channel.py`, `install-live-hooks.py`, `onboard.py`
  (the helper for taking only Levels 1-2 into `~/.claude`) and `legacy-install-check.py` (the `SessionStart` hook that
  warned while the old link install was still there), with their tests (`test_install*.py`, `test_legacy_*.py`,
  `test_onboard.py`). The hook entry is gone from `hooks/hooks.json`, so a session now starts with the rules and the
  configuration context only. The README opens with an Install section: one macOS/Linux command and one Windows
  (PowerShell) command that download `plugin-setup.py` into a fresh temporary folder and run it.
- **Why it was safe to do:** the old linked install is gone from the machine this is maintained on (`install.py --check`
  reported no link, no legacy hook and the plugin installed, immediately before the removal); the plugin has been the only
  install path since 13/10/2026.
- **What is lost, on purpose:** a machine that still holds the old links in `~/.claude` (`CLAUDE.md`, `agents`, `docs`,
  `modes`, `scripts`, `standards`, `skills/adyusuf`) no longer gets a warning or a one-command cleanup; those links are
  removed by hand. Earlier entries of this log that name the removed scripts are history and stay as written.
- **Kept:** the gate's own install-like tools are unrelated and stay (`pre-commit.sh --install`, `md-size-gate.sh --init`).

## plugin-setup.py finds `claude` when it is not on PATH, including the Claude desktop app's own copy (22/10/2026, user report)

- **Report:** on Windows the script stopped with "claude is not on PATH". The user has the Claude desktop app and, as far as
  they know, no terminal install, so there is no `claude` command in any shell.
- **Decision:** `claude` is looked up on `PATH`, then in the installers' folders (`~/.local/bin`, `~/.claude/local`,
  `~/.npm-global/bin`, `%APPDATA%\npm`, `/usr/local/bin`, `/opt/homebrew/bin`) and in the copy the desktop app keeps for its
  Code tab (`<app data>/Claude/claude-code/<version>/<hash>/`, newest numeric version first; the macOS layout was read on
  this machine, the Windows `%APPDATA%\Claude\claude-code\...\claude.exe` layout is the same by convention and has not been
  seen on a Windows machine). A folder found that way is put on `PATH` for that run only; nothing is written to the
  user's environment. `--claude <path>` overrides. When nothing is found the run stops before any change and prints the two
  `/plugin` commands to type in the app's Code tab, which does the same job without a terminal install.
- **Not done on purpose:** the script does not install the Claude Code command itself. That is a download-and-run of
  someone else's installer, which is the user's step, and the Code-tab commands make it unnecessary for this plugin.

## Settings: CI after push and e2e before deploy replace CI before merge and e2e after deploy (23/10/2026, user decision)

- **Decision:** the two groups are replaced, in the config script, `defaults/adyusuf.json`, rule #34 (`CLAUDE.md`),
  `standards/13` §8a, `standards/00` §1a and the config skill:
  - `ci_after_push.<t>` ("Run CI after pushing dev / test / prod"; defaults dev no, test yes, prod yes): after `<t>` is
    pushed, wait for the project's CI to finish on the pushed commit; a red run stops every later target. A project with
    no CI reports "no CI", which is not a failure. Not waiting is still recorded as `Gate-Waived: ci` on the merge commit.
  - `e2e_before_deploy.<t>` for `test` and `prod` only ("Run e2e on dev before deploying test", "Run e2e on test before
    deploying prod"; defaults both no): the e2e suite runs on the environment below the one about to be deployed.
- **Assumption to confirm:** a red e2e before a deploy blocks the promotion to that target. The user asked for the run, so
  it behaves like `GATE_RUN_E2E=1` in #33 (a requested run that is red blocks); the old `e2e_after_deploy` only reported.
- **Why the order changed:** CI that runs before the merge needed the code on a remote already; after the push the CI run is
  on the exact commit that was pushed, and `gates_before_push` is the local script (`scripts/merge-gate.sh`) in every case.
- **Compatibility:** `ci_before_merge.*` and `e2e_after_deploy.*` are in `RETIRED_KEYS`: a user's file that still holds them
  keeps working, the keys are skipped on read (their values are not carried over, the new defaults apply) and the next write
  drops them. A file that holds the NEW keys is unknown to an older installed copy of the plugin, which then ignores that
  layer and says so, so update `adyusuf` before setting them.
- **Not changed:** #29 (coverage) is part of what runs at every promotion and no setting turns it off; e2e stays optional
  (#33) unless a setting asks for it.

## Rail-box changes apply to the current session only (23/10/2026, user decision)

- **Decision:** a click in the Settings or Agents box changes that session, nothing else. A new session loads the saved
  defaults (plugin defaults < `~/.claude/adyusuf.json` < the project's file); if nothing was changed it stays that way.
  The mechanism is one more layer on top: `adyusuf_config.py set|unset|apply|reset-agents --session <id>` writes
  `~/.claude/adyusuf-session/<id>.json` (`scripts/adyusuf_session.py`; `ADYUSUF_SESSION_DIR` overrides the folder),
  `show|get|agents|context --session <id>` read it, and the hooks (`context` at session start, `notify` on each prompt)
  take the id from the hook payload's `session_id`, so a change is announced to its own session only.
- **How the panel knows its session:** it calls `$.session.id()` for every read and every click (the id changes on `/clear`)
  and refuses to write when it cannot get one, rather than falling back to the saved defaults.
- **Unchanged:** `/adyusuf:config` and a typed `set` still write the user layer (or `--project`); "keep this" from the boxes is
  the same change without `--session`. A resumed session keeps its id, so its changes stay; files untouched for 14 days are
  removed whenever a session file is written. Rules #34 and #29 are not affected.
- **Not done:** a panel button that saves the session's values as the defaults.

## The Session Settings page is withdrawn; the rail boxes load in the desktop app through CLAUDE_CODE_PLUGIN_DIRS (24/10/2026, user decision)

- **Decision:** the HTML page (`adyusuf_page.py`, `skills/config/session-panel.html`, the comment round trip) was built on
  23/10/2026 and the user did not want it: they want the boxes in the rail. The page, its tests and the published Artifact are
  removed (the commit that added it is reverted; its entry above stays as the record of what was tried and why it was
  clumsy: a change was not live until Claude applied it, one turn per Apply).
- **The way to the rail:** the plugin's mod is not loaded in a desktop-app session by default. A session the app starts
  loads the folders named in `CLAUDE_CODE_PLUGIN_DIRS` (the process environment or the `env` block of
  `~/.claude/settings.json`) like `--plugin-dir`; the user set it to
  `~/.claude/plugins/marketplaces/adyusuf-marketplace`, the marketplace clone that `plugin-setup.py` and
  `/plugin marketplace update` keep at the `prod` tip. The previous `settings.json` is in
  `~/.claude-standards/backups/settings-<stamp>.json`.
- **Verified (24/10/2026, by the user):** with the line set, a new desktop session shows the Settings, Agents and Promotion
  boxes in its rail. A click wrote only a per-session file under `~/.claude/adyusuf-session/` and left `~/.claude/adyusuf.json`
  unchanged. **Prerequisite found on the way:** the boxes run the configuration script of the INSTALLED plugin, so while that
  copy was the old `29ea419` they listed the retired options and every click failed with a popup (the old script has no
  `--session`). `plugin-setup.py` brings the installed copy to the `prod` tip; the mod itself comes from the folder.
- **Not explained:** the two session files seen after the first clicks held `e2e_before_deploy` ticks, not the
  `ci_after_push.dev` tick the user described; the user confirmed the click was accepted, so this was left as it stands.

## One pane with three foldable boxes instead of three panes (24/10/2026, user decision)

- **Why:** in the desktop app the three panes (Settings, Agents, Promotion) came up as separate panels on the right. The user
  wanted boxes inside the session rail, like the app's own Environment card. **Not possible from a plugin in this build:** the
  engine's `RenderComponent` list ends at `Pane` (a pane is seated `dock` beside the transcript or `inline` above the prompt);
  the app's own rail cards are not an extension point.
- **Decision:** the closest thing the API allows. `hooks/register.tsx` opens ONE pane (`adyusuf-boxes`, titled "adyusuf") that
  holds the three boxes as bordered sections, each folded by its header (`▾`/`▸`) with a one-line summary beside it; Agents and
  Promotion start folded, so the pane opens as a short card. The fold state is `$.state` (`adyusuf.folded`).
- **Structure (rule #29):** what the boxes draw moved to `hooks/boxes.ts`, engine-free (no import from `claude-code`, no
  JSX: elements are built with a factory `h` that is handed in), so Deno measures it and `boxes.test.ts` pins it; the engine glue
  stays the ONE listed file, `hooks/register.tsx`, which only reads state, runs the script and returns the composed tree.

