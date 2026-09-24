# Phase 3 — Run and classify (no edits)

Input: the branch with the phase-2 tests (round R1), or the branch after a phase-4 pass
(round R2, R3). Output: measured results and a failure list, one row per failure.
Phase 3 **never edits a file** — not a test, not a fixture, not the product. The cycle
is `standards/00-working-method.md` §11; parallelism follows §12.

## 1. Environment first

Read the project `CLAUDE.md` "commands" section: required env vars (an integration test
database connection string, for instance), services that must be up, the SDK to use.
A suite that fails because the environment is missing is **invalid**, not red — record
it as an environment failure; it goes to phase 4 like any other failure, and is never
reported as a product failure (global #31).

## 2. Run every affected suite FULL, one suite at a time

- Each layer that has a new or changed test runs its full suite — web unit, backend
  unit, backend integration, Android, iOS — **one suite after another**, each into its
  own log file in the scratchpad. Never pipe through `tail`/`head`. Never stop at the
  first failure: read the whole result before listing anything.
- Suites that fight for the same resource are not run in parallel (§12); two batteries
  never share a worktree (§11.6).
- Unit and integration only. E2E runs here only when the target is the `test → prod`
  gate and the code is deployed to the test environment (global #33).

## 3. List each failure on its own row

For every failing test: suite · test name · file:line · the first assertion or error
line from the log. One root cause often explains several rows — group them under the
cause, but keep every row.

## 4. Re-run each failing test ALONE

Run each failing test in isolation with the narrowest filter (`vitest run <file> -t
"<name>"`, `dotnet test --filter "FullyQualifiedName~<name>"`, Gradle `--tests`,
`xcodebuild -only-testing:`). This separates:

| Alone | In the full run | Meaning |
|---|---|---|
| red | red | a real failure — classify it |
| green | red | order dependence or shared state — a test defect (fix the isolation, never add a retry) |
| sometimes | sometimes | flaky — `standards/10` §8, never "fixed" with a retry |

## 5. Classify every failure

| Class | Examples | Phase 4 may fix it? |
|---|---|---|
| **Test defect** | wrong expectation, stale selector, order dependence | yes |
| **Fixture / data** | seed missing, fake misconfigured | yes |
| **Environment** | env var, service down, port, SDK | yes, if within the machine; a missing secret → stop |
| **Product bug — approved** | the fix is an approved task from phase 1 | yes, on the fix's own branch |
| **Product bug — not approved** | a new defect revealed by the run | **no** — stop and ask |
| **Tooling / gate** | the runner or gate script is wrong | yes, separately reported |

Loosening an assertion, adding a skip, raising a timeout or a retry is never a fix
(`standards/10` §9).

## 6. Prove each new test by mutation (round R1 only, or when a test changed)

For every test written in phase 2 or changed in phase 4:

1. Break the exact line the test is about (flip the condition, remove the guard,
   change the returned value).
2. Run only that test — it must turn red.
3. Revert and confirm `git diff` shows no product change.

A test that stays green under its mutation is a **test defect** — list it as a failure
for phase 4 (`standards/10` §7.5). The mutation is reverted before anything else runs;
phase 3 leaves no edit behind.

## 7. Coverage per codebase

Measure line coverage for each codebase separately (global #29). A codebase that was
not measured is "not measured" and blocks promotion.

## 8. Sync the docs, report, then either stop or hand to phase 4

First run the documentation sync (`references/doc-sync.md`) — measured counts and
coverage go into the project `CLAUDE.md` here, with the date.

Report for this round (screen report § run results, and chat):

| Round | Suite | Command | Passed / failed / skipped | Duration | Coverage |
|---|---|---|---|---|---|

then the failure list (one row each, with class and isolation result), the mutation
table and what was NOT run with the reason. "Did not run" is never "passed".

- **All green** → the loop ends: formatter/linter once (global #26 step 5), then STOP.
  Merges to `dev` only when the user asks; promotions are always the user's.
- **Red, and every failure is phase-4-fixable, and this was not round 3** → hand the
  failure list to phase 4.
- **Red, and a failure needs the user's decision, or this was round 3** → STOP and
  report every open failure individually.
