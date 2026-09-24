# Phase 4 — Fix, re-run only what was fixed, hand back to phase 3

Input: the classified failure list from the last phase-3 run. Output: every listed
failure fixed and green in its own narrow run, then **phase 3 is called again** for one
full run. Phase 4 never runs a full suite — that is phase 3's job.

## 1. Order

Fix by root cause, not by row: one cause that explains five red rows is one fix.
Environment and fixture causes first (they hide real failures), then test defects,
then approved product fixes.

## 2. What may be fixed where

| Class (from phase 3) | Fix | Branch |
|---|---|---|
| Test defect | correct the test so it asserts the intended behaviour — never weaken it | the screen's test branch |
| Order dependence | remove the shared state / fix setup-teardown — never a retry | the screen's test branch |
| Fixture / data | fix the seed or the fake (opt-in switch, default unchanged) | the screen's test branch |
| Environment | repair it on the machine and note what was done; a missing secret → stop | — |
| Product bug — approved | fix the product, with its regression test | its OWN branch off `dev` (global #26, #31) |
| Product bug — not approved | not fixed — phase 3 already stopped the loop | — |

If a fix reveals a new, unapproved product defect, stop: record it in the findings
register (`templates/findings.md`) and ask. Do not widen the fix.

## 3. Re-run ONLY what was fixed

After each fix, run the narrowest command that reproduces the failure — the same filter
phase 3 used to isolate it — plus the tests the fix could plausibly affect (same file,
same fixture, same fake). Evidence that the narrow run was red BEFORE the fix comes from
phase 3's isolation step; evidence that it is green AFTER comes from this run.

A fix that changed a test also re-runs that test's mutation proof (phase 3 §6).

## 4. Hand back

When every failure on the list is green in its narrow run:

- update the findings register and the screen report (round N: failure → cause → fix
  `path:line` → narrow command → green);
- **call phase 3 again** for the next round — one full run of the affected suites.

Write in one line why the full run is needed (a shared fixture/fake changed, a product
fix landed, or simply that the loop requires one all-green pass before merge).

## 5. Stop conditions

- The round counter reached 3 (the ceiling) — report open failures individually.
- A failure cannot be fixed without the user's decision (unapproved product change,
  a test expectation that contradicts a project rule, a missing secret).
- The same failure came back after its fix — second occurrence is reported, not
  re-fixed blindly.
