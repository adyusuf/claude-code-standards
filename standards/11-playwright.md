# Playwright — web e2e standards

## 1. What belongs in e2e

E2E is **expensive** (slow, fragile). Only these:

- Critical flows that lose money or data (login, sign-up, ordering, payment confirmation, deletion)
- Flows that prove several systems at once (UI → API → DB → email)
- Real bugs that have regressed before

**Not in e2e:** the validation of every form field, every button, every variant —
those are unit/component tests.
Target: 15-40 scenarios, running in under 10 minutes.

## 2. Selector policy (in order)

1. `getByRole('button', { name: 'Save' })` — tests the same path accessibility uses
2. `getByLabel('Email')`
3. `getByText(...)` — stable, but be careful with i18n-dependent text
4. `getByTestId('member-row')` — **a last resort**, though legitimate in complex lists

**Forbidden:** CSS classes, `nth-child`, XPath, generated class names (`css-1x2y3z`),
chains that depend on the DOM structure. A styling change must not break a test.

When a `data-testid` is added, a comment states that it must not be deleted.

## 3. Waiting

- **`waitForTimeout` / `sleep` are forbidden.** Use Playwright's auto-wait plus web-first assertions:
  `await expect(page.getByRole('row')).toHaveCount(3)`
- If you are waiting on the network, use `page.waitForResponse(...)` or wait for the result's reflection in the UI.
- Raising a fixed timeout is not a fix for flakiness — find the cause.

## 4. Data and isolation

- **Every test creates its own data.** Never test against a shared record (it collides in parallel runs).
- Setup happens through the **API**, not the UI (fast and robust); the flow under test goes through the UI.
- Unique data — a fixed email or name is forbidden. **Email goes to a real mailbox** (global rule #30):
  `<account>+<label>@gmail.com`, where the label separates the record
  (`customer-${Date.now()}-${random}`). The address is produced by **one helper** in
  the fixtures (with the base overridable through `E2E_EMAIL_BASE`); no address is
  written into a spec. `.test` / `.local` / `example.com` are FORBIDDEN: if the test
  environment is wired to real SMTP, every invitation or link message bounces and
  raises a delivery error.
  Example: `e2eEmail(\`customer-${Date.now()}\`)` → `<account>+customer-1789…@gmail.com`.
- Clean up at the end of the test (or use an isolated tenant/schema).
- E2E never runs against production. It runs against the test environment, and the environment URL comes from env, never hard-coded.

## 5. Authentication

- Login does not go through the UI in every test → log in once with `storageState` and let every test use that session.
- Role-based fixtures: `adminPage`, `memberPage`, `guestPage`.
- **The login flow itself** is verified by its own test (and that test does not use storageState).

## 6. Structure

```
e2e/
  fixtures/      → auth, test data, API helpers
  pages/         → Page Objects (only for complex screens)
  specs/         → scenarios, grouped by business flow
  userstories/   → scenarios that mirror the acceptance criteria one to one
playwright.config.ts
```

- A Page Object is **not mandatory** — on a simple screen it is a needless layer. Extract one once the same selector repeats in three or more tests.
- No assertions inside a Page Object; assertions stay in the test.

## 7. Assertions

- Assert what the user sees: text, counts, visibility, the URL, a toast.
- Prefer `await expect(locator).toHaveCount(3)` (which retries) over `expect(await page.locator(...).count()).toBe(3)`.
- Focused tests per flow rather than one giant "check everything" test.
- Visual regression is used deliberately and narrowly; otherwise it burns red permanently.

## 8. Configuration

```ts
retries: process.env.CI ? 1 : 0,   // more than one retry = hiding flakiness
workers: process.env.CI ? 2 : 4,
use: {
  baseURL: process.env.E2E_BASE_URL,   // a hard-coded URL is forbidden
  trace: 'on-first-retry',
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
  locale: 'tr-TR',
  timezoneId: 'Europe/Istanbul',
}
```

- Locale and timezone are **pinned** — a date test that varies by machine breaks.
- `trace`/`screenshot`/`video` are uploaded as CI artifacts; a failure should be understandable without reading the log.

## 9. Run policy

- Never **mixed into** the fast CI gate (unit/lint/tsc) — a separate workflow.
- Trigger: the **`prod` gate only** (`scripts/merge-gate.sh prod`), plus optionally nightly. On `dev` and `test` the gate does not run e2e; it only checks whether a spec is missing (#25, #33).
- The last run's result (commit, time, outcome) is recorded in a file; before a prod merge that record is checked for **staleness**. If it is stale or red, nothing proceeds without approval.
- Nothing ships to prod while e2e is red.

### 9a. The run cycle (CLAUDE.md #31)

1. **The full run.** The whole suite runs; it does not stop at the first failure (`--max-failures=0`). Parallelism is chosen against the environment's limits: rate limits, session/token lifetime, shared fixtures. Suites that log in on every test run against a remote test environment with low parallelism (usually one worker).
2. **Classification.** Every failure gets a class, with evidence:
   - *product bug* — the behaviour really is broken;
   - *stale spec* — the product changed and the spec did not (a changed class or string);
   - *data/fixture* — test data is missing or left over from a previous run;
   - *environment* — a 429 rate limit, a timeout, a deploy delay, an expired session.
   The evidence: the error text, the trace (`trace.zip`), a screenshot, the network states, the test's result in previous runs. "Probably flaky" is not a class.
3. **The fix.** Each fix on its own branch (off `dev`) with its own merge. Raising retries, blindly increasing a wait, or loosening an assertion does not count as a fix. For a failure in the environment class the fix is a run setting (parallelism, the wait window), not the spec.
4. **The targeted run.** Only the fixed tests and the tests the fix could affect run (`--only-failed` where the project has it, otherwise a file/line filter).
   ⚠️ **E2E runs only against code that has reached `test`.** While a fix is on `dev`, verification means unit tests + tsc/lint. The targeted run and the full repeat happen after the fix reaches `test` and is deployed. Running a spec from the `dev` branch against the test environment is also running e2e — forbidden.
   ⚠️ **The timing is set by #33:** in the `dev` and `test` directions e2e is never RUN — the shared gate only CHECKS for a missing spec, and that check is a **warning in both directions** — it never blocks a promotion to `test`. The run itself belongs to the gate BEFORE `prod`, which first VERIFIES the deploy: is the code on `test` → are any e2e specs missing → write them → if it has not been run against this code, run it → prod. The list of gaps is produced **once**, not twice (previously it was produced in `dev`/`test` and recomputed at the prod gate). This item and the "once it reaches test" phrasing in item 4 are read in the light of that rule.
   ⛔ **Nothing ships to `prod` without e2e;** only work the user explicitly calls a "hotfix" ships without it, and the report then reads "e2e skipped (hotfix)".
5. **The decision to repeat the full suite — Claude makes it and reports the reasoning.** The full run is repeated if:
   - the fix touched something shared (layout, auth/session, a common component, a fixture helper, the Playwright config);
   - the promotion record (a commit status or similar) requires a valid full-run result;
   - some of the first run's failures were environmental (that run is not a valid baseline).
   If the fix is limited to a single spec or screen and no record is required, a targeted run is enough.
7. **No test environment (user decision, 21/09/2026).** When `E2E_BASE_URL` is unset, Claude starts the stack locally (API + web, a throwaway test DB, e2e-only secrets from `.env`) and runs the whole suite against it, then stops it. The result is reported as "e2e ran locally (no test env)"; it satisfies the `prod` gate's e2e step (#33) but does not replace a run against `test` once one exists. Never pointed at a real/production database.
6. **An invalid run.** The result of a run that hit an environment limit is never reported as a product result; parallelism is lowered, the run repeated, and this is stated explicitly.

## 10. Never-do list

- ❌ `waitForTimeout`
- ❌ A CSS class / XPath selector
- ❌ Data shared between tests, or an order dependency
- ❌ A hard-coded URL / user / password (use env or a fixture)
- ❌ Running e2e against production
- ❌ "Fixing" a flaky test by raising `retries`
- ❌ Committing `test.only` (block it with a lint rule)
