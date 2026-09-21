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

## §25 — Merging to `dev` is fast; heavy gates run on promotion

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

### The e2e spec check warns, and blocks nothing (21/09/2026)

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

### The five fixes of 21/09/2026, and how each one is pinned

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
in one line, and it is not built.

## §26 — Pull `dev` → branch off `dev` → work → merge each task separately

Additional detail shortened out of the active file:

1. **First `git fetch` and update `dev`.** Branching from a stale base means
   working without ever seeing other sessions' commits (this repo is used with
   parallel worktrees).
3. **When a task is finished, merge that task to `dev` on its own.** Do not collect
   several tasks into one commit/merge — each task goes with its own commit, its own
   verification and its own merge.
4. **The USER decides on the `test` and `prod` promotions.** There is no
   self-initiated merge to `test`/`prod`; those branches are not touched until the
   user explicitly says "merge" / "prod merge" (#25 and the project's own rules
   still apply).

⚠️ **The configuration repository's own layout:** branches `dev` / `test` / `prod`,
with `prod` as the default. Work is committed to `dev`; the **user** decides on each
promotion. The repo is a **shared working tree** — parallel sessions work in the same
directory, so `git status` is verified before switching branches and only your own
diff is committed.

**Why:** the goal is to keep `dev` clean and traceable, to be able to see each task
separately, and to keep control of what goes outward.

**How to apply:** when given a multi-step task list, update the base and create the
branch before the first line of code; when each item is finished, verify it, commit
it and merge it to `dev`, then move to the next.

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
  eleven roles require C/D/E. If the user names a mode, run the `/working-mode` skill.

## §28 — The auditor checks, sends back and gets it fixed; cost is reported at every handoff

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
  **separately** once its unit run is green.

**Why:** intermediate runs consumed time and machine load; the order is all the
code, then write and run unit tests, and e2e once the code reaches `test`.
**How to apply:** do not start a run while writing code; batch the verifications,
including tsc/lint, after the code and the tests are written.

## §33 — The only place for e2e is the pre-production gate

- **`feature → dev` and `dev → test`:** e2e **does not run**. Earlier this stage
  carried a "was a spec written" check; that check was **removed** — it blocked
  nothing, and the list of missing specs it produced was **recomputed** at step 2 of
  the `prod` gate, i.e. an output produced twice and used once. There is no run, no
  waiting on a deploy, no reading a status file.
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
- **Activation (`scripts/install-live-hooks.py`).** Symlinks live in `~/.claude/hooks`,
  not `~/.claude/scripts`: `scripts` points into the PROD worktree, so a new file there
  would be untracked in prod and collide with the next promotion. The links point into
  the `dev` checkout; after a promotion `--repo <prod checkout>` re-points them.
- **Automatic ledger (`scripts/measurement-ledger.py --auto`).** Every column is derived
  from the transcripts; there is no hand-filled field, and no project name, path or command
  is written (raw commands were rejected: an earlier commit already had to fix a log that
  bypassed the sanitiser). Incremental, locked, atomic, 600 s minimum interval, detached.
  **The file is local and git-ignored.** It was first tracked and the hook rewrote it, which left the `dev`
  and live `prod` worktrees dirty and would have blocked any promotion touching it; it was untracked
  (history keeps the earlier rows) and `scripts/doc-check.py` no longer reports a git-ignored path as a
  broken reference. The cost: the file is not backed up by git.
- **Project nicknames and the per-day reports (`scripts/measurement-report.py`).** The ledger's
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
- ❌ Invoking the `test-writer` and `migration-reviewer` subagents — strictly forbidden. ⚠️ The ban is tied to **names** and those names are not on disk today; the real protection is **the mode's role set**: no agent outside the mode's roles is called (including the 21 active plugin agents) → #27, #28
- ❌ Starting an agent in mode A; calling an agent outside the mode's set in B/C/D/E. ⚠️ With no mode file, **B** now applies — B's three agents are free, a fourth is not → #27
- ❌ Ending a turn without reporting the agent count and estimated cost (B/C/D/E) → #27
- ❌ Slowing down a `dev` merge with review/scanning gates → #25 (but skipping the gate on the `test`/`prod` promotion is equally forbidden)
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

- **Gather context first.** Read a file before editing it; scan the project's own
  `CLAUDE.md` and its `docs/` if present. Do not write code on assumptions.
- **Plan → approval → execute.** For work touching multiple files, present a short
  plan first (which file, what changes, why).
- **Verify what you did.** Build + the relevant tests + lint/format. If you did not
  run them, say "I did not run them".
- **When uncertain:** finish the independent work, then ask one clear question. Do
  not stop at every assumption; but do ask if a wrong assumption would throw the
  work away.
- **Parallel-session awareness.** Other sessions may be working in the same repo:
  commit only your own diff, verify `git status`/`git diff` before committing, and
  never use `--force`.
- **Get approval for irreversible work.** Deploys, a migration `DROP`, sending
  anything outward, deleting files.
- Detail: `standards/00-working-method.md`

### ⚠️ Commit c68fbf1 bundled two unrelated tasks

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

## STATUS REPORTING during a long gate/run — the dashboard was removed (21/09/2026)

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
deliverable. User decision, 21/09/2026.

**What was kept, because it was never about the dashboard:** figures are measured and
name their signal; an unmeasurable figure says "cannot be measured"; a step that did
not run is reported as "did not run" and never folded into a pass; a long run's output
goes to a log file instead of a buffering pipe (`tail`/`head`); an inferred state says
it is inferred; an over-optimistic estimate is corrected downward out loud.

<details>
<summary>The retired dashboard rule, as it stood until 21/09/2026</summary>

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

## Measurement record — the token-reduction round

The question was where the operating-mode structure and the SDLC flow were spending
tokens unnecessarily, and which steps were being repeated when running once at the
end would do.

**Measurement:** the median fixed prefix was 57,756 tokens, an **18% share** of cost,
and it had grown 27,700 → 63,500 tokens (2.3x) over fourteen weeks. Across the
subagent runs in the same window the median was 52,313 tokens. Method and repeat instructions: `scripts/prefix-measure.py`,
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
