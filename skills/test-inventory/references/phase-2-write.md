# Phase 2 — Write the approved tests

Input: the phase-1 report and the user's approval of a list of findings. Only approved
items are written. Output: the tests, and the report updated finding by finding.

## 0. Branch

Global #26: `git fetch`, update `dev`, create a branch (or worktree) off `dev` — one
branch per screen, so each screen merges to `dev` on its own. Never commit on `dev`.

## 1. What gets written, what does not

| Finding class | Phase 2 action |
|---|---|
| Test gap (approved) | Write the test. |
| Defect (fix approved as its own task) | Write the regression test FIRST, on the fix's own branch, together with the fix (`standards/10-test-strategy.md` §1). Never commit a red test to `dev` on its own. |
| Defect (fix NOT approved) | Do not write a test that encodes the wrong behaviour, and do not write a red test. Leave it in the report as open. |
| Unhandled case | Needs a design decision — not written until the behaviour is decided. |
| E2E gap | Not written at the `dev` stage (global #33) — goes to the e2e backlog in the index. |
| Parity / dead code | Not a test task. |

## 2. Before writing a test

- Open the neighbouring test file for the same service/page and copy its conventions:
  naming language, fixtures, factories, helper builders, how the fake gateway or API
  mock is configured. Reuse — do not create a second fake or a second helper.
- If a shared fake cannot express a failure (e.g. always succeeds), extend it with an
  opt-in switch whose default keeps today's behaviour, so no existing test changes.
- Test data e-mail addresses come from the project's single helper (global #30).
- Time comes from the clock abstraction; no `Now`, no random ids in assertions.

## 3. Test rules (from `standards/10-test-strategy.md`)

- The name states the behaviour and the expected outcome.
- AAA blocks visible; one behaviour per test; no `if`/`for`/computed expectations.
- An assertion that would fail if the behaviour broke — an assertion-free or
  "does not throw" test is forbidden (§7.5). Phase 3 proves this by mutation.
- Assert the observable contract (status code, body field, persisted state, rendered
  text, request payload), not implementation detail.
- For "must never contain" rules (card data, secrets), assert on every sink the finding
  named: stored record, API response, audit log.

## 4. Scope discipline

- Tests only. No product-code change in a test task — if writing a test reveals that the
  product is wrong, stop, record it as a new defect in the report, and ask.
- Do not run suites after each test (global #32): write everything approved for the
  screen, then hand over to phase 3. A compile/type check of the test project is fine.
- Mode: the approved agent set applies (`test-writer` from mode B up); in mode A write
  them yourself.

## 5. Report and stop

Update the screen report's findings table: each approved item gets `→ test: path:line`
or `not written: <reason>`. In chat, a table: layer · tests added · files · items left
open. Then stop — phase 3 runs them.
