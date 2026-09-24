# Phase 3 — Run, prove, report

Input: the branch with the phase-2 tests. Output: measured results and the updated
report. The cycle is `standards/00-working-method.md` §11; parallelism follows §12.

## 1. Environment first

Read the project `CLAUDE.md` "commands" section: required env vars (an integration test
database connection string, for instance), services that must be up, the SDK to use.
A suite that fails because the environment is missing is **invalid**, not red — fix the
environment and run again; never report it as a product failure (global #31).

## 2. Full run of the affected suites

- Every layer that got a new test runs its full suite once, without stopping at the
  first failure. Output goes to a log file in the scratchpad, never through `tail`/`head`
  (global status-reporting rule).
- Unit and integration tests only. E2E is NOT run here unless the target is the
  `test → prod` gate and the code is deployed to the test environment (global #33).

## 3. Classify every failure

product bug · stale test · fixture/data · environment · tooling. One root cause often
explains several red lines — find it first.

- **New test red because the product is wrong** → it is a defect: record it, do not
  bend the test, ask for the fix decision.
- **New test red because the test is wrong** → fix the test.
- **Existing test red** → classify; loosening an assertion, adding a skip or a retry is
  never a fix (`standards/10` §9).

Re-run ONLY what failed (the narrowest filter that reproduces it) plus what the fix
could affect. Then decide on ONE full run and write the reason in one line.

## 4. Prove each new test by mutation

For every test written in phase 2:

1. Break the exact line the test is about (flip the condition, remove the guard,
   change the returned value).
2. Run only that test — it must turn red.
3. Revert and confirm `git diff` shows no product change.

A test that stays green under its mutation is not a test: fix it or delete it
(`standards/10` §7.5). Record per test: mutated `path:line` · red ✓/✗ · reverted ✓.

## 5. Coverage per codebase

Measure line coverage for each codebase separately (global #29). Report the number and
the command; a codebase that was not measured is "not measured" and blocks promotion.

## 6. Report

In the screen report and in chat:

| Suite | Command | Passed / failed / skipped | Duration | Coverage |
|---|---|---|---|---|

then the classified failures, the mutation table, and what was NOT run (with the
reason). "Did not run" is never reported as passing.

## 7. After green

Formatter/linter once at the end of the task list (global #26 step 5). Commit only your
own diff. Merge to `dev` per screen only when the user asks; `test`/`prod` promotions
are always the user's decision.
