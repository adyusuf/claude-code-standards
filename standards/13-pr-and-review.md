# Commits, PRs and code review

## 1. Branches

```
<type>/<short-description>     feat/member-process-status
                               fix/order-total-rounding
                               chore/upgrade-efcore
                               docs/api-contract
```

- English, kebab-case, short. A person's name or a ticket number alone is not a branch name.
- A branch is cut **from the integration branch** (`dev`) and returns there. No branch is cut directly from `test`/`prod`.
- No long-lived branches — a branch older than two or three days is either split or frequently rebased/merged from `dev`.

## 2. Commits

```
<type>(<scope>): <summary, imperative mood, under 72 characters>

The body: why this change was needed, and which alternative was ruled out.
If it is breaking: BREAKING CHANGE: <explanation>
```

Types: `feat` `fix` `refactor` `perf` `test` `docs` `chore` `build` `ci` `revert`

- **Atomic commits:** a commit compiles and covers exactly one subject. "wip", "fix", "final" are forbidden.
- A formatting or rename commit is committed **separately** from a logical change (so the diff stays readable).
- Generated files, `node_modules` and build output are never committed.
- **Commit only your own diff.** Never use `git add -A` blindly; a parallel session may grab someone else's file.

## 3. PR size and contents

- Target: **under 400 changed lines**. If it is bigger, split it — review quality collapses on a large PR.
- **One PR = one subject.** A refactor, a feature and a reformat never share a PR.
- The PR description (`templates/pr-template.md`):
  - What / why
  - How it was tested (the command plus its result)
  - A screenshot (if the UI changed, before/after)
  - Backward-compatibility impact (**a required field**: "none" is a valid answer, but it is written down)
  - Whether there is a migration / an env change / a new secret
  - How to roll it back

## 4. The merge gate (automatic — no merge without passing it)

> **Scope (global rule #25):** the gate below is SHARED — `scripts/gate-core.sh <dev|test|prod>`,
> a copy of the canonical script committed in every project and called by that project's
> own `scripts/merge-gate.sh` orchestrator. It is four twin files (`gate-core.sh` plus
> `gate-lib.sh`, `gate-lib-node.sh`, `gate-lib-prod.sh`, listed in `scripts/twins.txt`): copy them
> together, a core without its libraries refuses to run. Everything in it runs at **every**
> promotion, `feature/* → dev` included; **the single deferred step is RUNNING e2e**, which belongs
> to the `prod` gate (#33). On `dev` and `test` the gate also CHECKS whether an e2e spec is missing:
> a warning in BOTH directions, never blocking — the gaps are written at the `test → prod` gate
> (#33 step 2). A step whose tool is missing is reported SKIPPED and the
> result is INCOMPLETE, never green.

- [ ] Build (backend + web + mobile)
- [ ] Unit tests green
- [ ] **Line coverage ≥ 80% in every codebase** — with an honest denominator; an unmeasured codebase blocks (global #29, `10-test-strategy.md` §7)
- [ ] `tsc --noEmit`, ESLint, `dotnet format --verify-no-changes`
- [ ] Backward-compatibility scan (`08-backward-compatibility.md` §7)
- [ ] The secret scanner (gitleaks or similar) is clean
- [ ] The dependency security scan has no critical finding
- [ ] `SETUP.md`, `.env.example` and the secret/token inventory exist (global #16) — a missing one fails the gate
- [ ] If there is a migration, its reversibility is stated

The gate is **never bypassed**. Loosening a test to get through it is forbidden.

## 5. Review checklist (for the reviewer)

**Correctness**
- [ ] Does it genuinely meet the acceptance criteria?
- [ ] Edge cases: empty, one, many, null, long text, negative, concurrent
- [ ] Are the error paths handled? Is any exception swallowed silently?

**Contract / compatibility**
- [ ] Was a field deleted, renamed or retyped?
- [ ] Is there a new required input field?
- [ ] Did enum ordering break? Did a global serializer setting change?
- [ ] Does the older mobile version still work with this change?

**Security**
- [ ] Is every endpoint authorized? Is resource ownership (IDOR) checked?
- [ ] Is input validated? Is raw SQL parameterized?
- [ ] Does a secret or PII leak into a log or a response?

**Data**
- [ ] Any N+1? Is there pagination? Is an index needed?
- [ ] Is the transaction boundary right? Is there an external call inside it?
- [ ] Is the migration reversible? Does it contain a `DROP`?

**Readability**
- [ ] Do the names convey intent? The 300-line rule?
- [ ] Any dead code, commented-out code, or an ownerless TODO?
- [ ] Any hard-coded URL/port/key?

**Tests & documentation**
- [ ] Is there a test for the behaviour change? Was a test loosened?
- [ ] Are Swagger/OpenAPI, CLAUDE.md and the related documents current?

## 6. Finding severity levels

| Level | Meaning | Consequence |
|---|---|---|
| **Blocking** | Data loss, a security hole, a breaking change, wrong business logic | Not merged |
| **Important** | A performance problem, a missing test, a missing error path, a contract risk | Fixed in this PR |
| **Suggestion** | Naming, structure, readability | The author's call |
| **Note** | Sharing information | No action |

When writing a comment: **what** is wrong + **why** it matters + **a suggestion**.
"This is bad" is not a review. A suggestion-level comment does not block the merge.

## 7. The author's responsibility

- **Read your own diff** before opening the PR. Do not make the reviewer find what you could see yourself.
- Answer every comment (fixed / not fixing, for this reason). No silent resolutions.
- If you made a large change after review, ask for review again.

## 8. Merge strategy

- Into `dev`: a **merge commit** (`--no-ff`) that keeps every task's own commit. Never squash: a squashed
  batch loses the per-task history (#26).
- **Batch promotion (#26, user decisions 29/09/2026 and 30/09/2026 — gates are long).** Promotions to
  `dev` and to `test` are made in batches, never one feature / worktree at a time:
  0. **Producers hand off, they are not gated (user decision 05/10/2026, every mode —
     `modes/README.md` › *One review, one test run, one gate*).** An agent, subagent, `Workflow`
     agent or background task does its OWN job to the end — code, then its unit tests (#32), plus
     only the narrow run it needs to trust its own piece — and hands the branch to the orchestrator.
     It is never code-reviewed, fully test-run or gated on its own; those happen once, on the batch.
  1. **Collect:** every READY sub-branch (feature branch or worktree branch, each task in its own
     commit(s)) is merged with `--no-ff` into one batch branch cut from the fresh target. No
     per-branch test or gate run happens before this — the tests and the gate run ONCE, on the batch.
  1a. **ONE code review on the merged batch** — not one per sub-branch. Findings are attributed to
     the sub-branch that produced them (step 3).
  2. **Run:** the full test suite and the gate run on the batch (#31: the whole run, no stop at the
     first failure; every failure classified and attributed to the sub-branch that caused it).
  2a. **The auditor judges the RESULTS, not only the code:** it reads the test run and the gate
     output (every failure, SKIPPED step, warning, and the measured coverage figures — #29, #25),
     checks that the run was the whole run and valid (#31), and that nothing was loosened to pass.
     A gap or wrong result is sent back to the producing sub-branch (#28 hand-back, same
     closure rule); a batch with an open finding does not promote.
  3. **Fix where it was born:** each failure is fixed **on its own sub-branch** (its own commit),
     never as a patch on the batch branch; the fixed sub-branches are merged into the batch again,
     together.
  4. **Re-verify — this is where `dev` and `test` differ:**
     - **→ `dev`:** re-run **only the failed tests** (plus what the fix could affect, `00` §11.3),
       then the gate, then merge the batch to `dev` in one merge commit.
     - **→ `test`:** re-run the **FULL test suite** (not only what failed), then the gate, then merge
       to `test`. A narrow re-run is not enough on the way to `test`.
  5. **A red batch is never waved through**, and the gate's step set is never trimmed to fit a
     narrow re-run (#25).
- **"Batch" does NOT chain the stages.** A batch reaching `dev` says nothing about `test`: the
  `dev → test` promotion is a separate batch, a separate full run and gate, and the user's own
  decision (#26.4). Never read "batch" as "merged to `dev` ⇒ also merged to `test`".
- `dev → test → prod`: a **promotion**, fast-forward/merge. Never a merge in the reverse direction.
- **The `prod` gate runs on the ref being promoted** — normally a detached checkout of `origin/test`
  (the usual source), never on a `test`-into-`prod` merge candidate. It does **not** check the `test`
  branch or the test environment (user decision 04/10/2026, general rule): a branch may go to `prod`
  without having been on `test`. The gate WARNS it did not look; `GATE_CHECK_TEST_DEPLOY=1` opts in to
  the deployed-SHA check, and that check compares `HEAD` with the SHA the test environment runs, so a
  merge candidate's new commit fails it by construction (measured 29/09/2026). The merge to `prod`
  follows the green run.
- **E2E is optional and never run by a gate (user decision 03/10/2026, general rule; it replaces the 30/09/2026 "mandatory before `prod`" rule — there are not enough resources to run it).** The `test` and `prod` promotions WARN that e2e was not run and continue; `GATE_RUN_E2E=1` runs the suite and a red result then blocks like any step. The deployed-to-`test` check on `test → prod` is optional as well (04/10/2026, `GATE_CHECK_TEST_DEPLOY=1`).
- **No** direct commit or PR to `test` and `prod` — only from the previous stage, with the user's approval.
- Before merging, `git fetch` and update if you are behind — a gate running against stale code gives false confidence.
- A `--force` push happens only on your own feature branch and only with explicit approval.

## 8a. Merges, pushes and the gates before them follow the configuration (global rule #34)

Since 17/10/2026 Claude **does not ask** whether to merge, run a gate or push: the answers are settings
(`/adyusuf:config`, `scripts/adyusuf_config.py`; defaults in `defaults/adyusuf.json`, the user's own in
`~/.claude/adyusuf.json`, a project's in `.claude/adyusuf.json`, and the running session's own layer
`~/.claude/adyusuf-session/<session id>.json`, which the rail boxes write and which ends with the session). Asking every
time was too much work for the user, so the defaults say what normally happens and whoever wants something else changes
the setting once, or for one session.

**When the code is done**, for each target `<t>` in `dev`, `test`, `prod` (in that order; a batch merge, §8, is one merge):

| Setting | Effect |
|---|---|
| `merge.<t>` = yes | Merge the finished code into `<t>` (`--no-ff`, from the fresh remote tip, §8). `no` leaves it out, and the later targets with it. |
| `gates_before_push.<t>` = yes | Run the gates (unit tests, coverage, secret scan, SAST) on the merged result before `<t>` is pushed, with the local gate (`scripts/merge-gate.sh`). Defaults: dev no, test yes, prod yes. |
| `push.<t>` = yes | Push `<t>` after its merge and its gates. `no` leaves the merge local and the report says so. |
| `ci_after_push.<t>` = yes | After `<t>` is pushed, wait for the project's CI to finish on the pushed commit. A red run is reported with the failing job and stops every later target. A project with no CI says "no CI", which is not a failure. `no` does not wait and the merge commit carries `Gate-Waived: ci`. Defaults: dev no, test yes, prod yes. |
| `e2e_before_deploy.<t>` = yes (`test`, `prod`) | Before `<t>` is deployed, run the e2e suite (Playwright / Maestro, `11`/`12`) against the environment below it: `e2e_before_deploy.test` runs on `dev` before `test` is deployed, `e2e_before_deploy.prod` runs on `test` before `prod` is deployed. It applies only where the project has an e2e suite and that environment; otherwise the report says "no e2e suite" or "no such environment", which is not a failure. A red run is reported with the failing specs and blocks the promotion to `<t>` (it was asked for, #33). The deploy itself still needs the user's approval (#20, #27). Defaults: both no. |

**A red gate blocks** the push of that target and every later one; it is fixed, not waved through (§8, point 5). **A gate set
to no is not run and is recorded**: the merge commit message ends with one line naming only what was skipped,

```
Gate-Waived: ci, gates (neden: configuration)
```

(`neden:` is the literal the user gave; a scanner accepts `reason:` too.) **Before the `prod` merge**, scan the range being
promoted for those lines and put the result in the report - for example `git log --format=%B origin/prod..origin/test |
grep '^Gate-Waived:'` (a project may ship a helper that lists commit, gate and reason). It is reported, not asked: the user has already said what runs. "A step that did not run
did not pass" (#25) stays true in the report.

**The setting is the only switch** (user decision 29/10/2026): a project keeps no gate switch of its own (a file listing
targets whose gate is off, a project rule saying "promote only on approval"). Its `merge-gate.sh` runs every gate by
default and skips them only when Claude passes the waiver because `gates_before_push.<t>` is no; the trailer then reads
`(neden: configuration)`.

**What no setting changes:** coverage ≥ 80% per codebase (#29) is part of what the gate owner runs and is not a setting;
force pushes, `DROP`, deploys and anything on `main` need the user's approval in every mode (#20, #27) and are guarded by
`guard-destructive.sh`; secrets stay out of the repository (#3). A push to `prod` is an ordinary push when `push.prod` is
yes (the hook no longer judges it); a pending migration or other irreversible step in the change still needs approval.

## 9. Claude's role in review

- **If the target branch is `dev`, no review happens** (global rule #25): the diff is not read, no agent is invoked, no scan runs — if build + fast tests + lint are green, it is merged. If something catches the eye along the way, it is noted in one line without blocking the merge.
  - ⚠️ **One exception (`modes/role-selection.md` §3):** if the change weakens **backups, secret management or a security gate itself** (`continue-on-error`, disabling a gate, switching off gitleaks, breaking backup/restore) then `qa` runs in the `dev` direction too and the reason is recorded. #25 buys speed, not an irreversible loss.
- If the "merge" command **targets `test` or `prod`**: **the diff is reviewed first**; if there is a **blocking** finding, STOP and report it.
- The "review done" flag is never given to the merge gate without a review having happened.
- What automatic scanning cannot catch (a change of meaning, enum drift, tightened authorization) is checked **by hand**.
