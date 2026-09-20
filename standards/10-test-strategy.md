# Test strategy

## 1. The pyramid

```
        /\        E2E (Playwright / Maestro)      — few, critical flows, the real system
       /  \       Integration (API + a real DB)   — some, the contract and the data layer
      /____\      Unit                            — many, fast, isolated
```

- Inverting the pyramid (testing everything through e2e) means a slow and fragile CI.
- When a bug is found: **first write the test that exposes it**, then fix it (a regression shield).

## 2. What is tested, and what is not

**Tested:** business rules, boundary values, error paths, authorization decisions,
calculations, state machines, the serialization contract, backward compatibility.

**Not tested:** the framework itself, getters/setters, things the type system
already guarantees, implementation detail (private method names, call order).

## 3. Unit test rules

- **AAA:** Arrange / Act / Assert — the three blocks should be visible.
- The test name states the behaviour:
  `restores_stock_when_order_is_cancelled` / `returns_400_when_email_is_invalid`
- **One test, one behaviour.** If a test has eight assertions it should probably be three tests.
- **No logic in a test**: no `if`, no `for`, no computation. The expected value is written by hand (never re-implement the code's formula).
- Tests are **independent of each other** and **of order**; no shared mutable state.
- Deterministic: `DateTime.Now`, `Random` and `Guid.NewGuid()` are never used directly → they are injected or fixed.
- `Thread.Sleep` is forbidden → use a fake clock or wait on an event instead of a real wait.
- Test data comes from a builder/factory (`aMember().withStatus(Active).build()`), not twenty lines of setup in every test.

## 4. Choosing a test double

| Kind | When |
|---|---|
| **Fake** (a simple working implementation) | Preferred — an in-memory repository, a fake clock |
| **Stub** (returns a fixed value) | To supply an input |
| **Mock** (verifies an interaction) | Only when an **external effect** must be verified (was the email sent) |

- Over-mocking ties the test to the implementation → it breaks during a refactor and catches no bugs.
- Never mock your own code; mock the boundaries (external services, the clock, the network, the filesystem).

## 5. Integration tests

- They run against a real database (**Testcontainers** preferred).
- If an in-memory provider is used, know the differences: case sensitivity, `unaccent`, transactions, concurrency, raw SQL and foreign-key behaviour **all differ**. Critical behaviour is not considered verified by an in-memory run.
- Every test creates and cleans up its own data (a transaction rollback or an isolated schema).
- API tests go through HTTP (`WebApplicationFactory`) — not by calling the controller method directly.

### 5a. A test result can never depend on the machine — cut secret leakage at the base factory

If an integration test boots in the development environment (`Development`), the
configuration chain **also loads user secrets**. Every secret defined on the
developer's machine leaks into the test; on a clean machine it does not. The
result: the same commit produces two different results on two machines, and what
the test proves becomes unclear.

- In the **base factory** the test boots (a `WebApplicationFactory` derivative), **every setting that reaches the outside world or changes behaviour is pinned explicitly** — all of them, not one at a time as leaks are discovered. The usual suspects: LLM/API keys, the path of the encryption key ring, external service addresses, browser visibility, feature flags.
- The default is **"not configured"** (empty/off). Most endpoint tests do not need those capabilities; a test that does sets the capability up **itself** (`WithWebHostBuilder` + a temporary directory scoped to the test), and that override wins because it runs after the base factory.
- Write **why** next to the pinning. "Left empty" means nothing to the next person and gets deleted; "a developer's real key leaked and the test spent money" does not.
- When a local workaround (clearing it in one sub-factory) is moved into the base factory, it is **removed** locally. That the test still passes after the local line is gone is the proof the base setting really applies.

The same rule applies to the test database: a shared, fixed-name test database
wipes another working copy's data in parallel runs. The name is **derived from the
working copy**; `[Collection]` serialization only protects within a single process.

## 6. Contract tests

- Do the fields the client expects exist in the server's response — **the backward-compatibility shield**.
- The minimum per endpoint: the status code plus the presence and type of the required fields.
- If a field is deleted or renamed this test **turns red** — which is precisely its purpose.
- Validation against the OpenAPI schema can be automated.

## 7. Coverage — THE THRESHOLD IS 80%, no exceptions (global rule #29)

**THE DECISION:** line coverage in every codebase is **at least 80%**. This
section used to say "coverage is a diagnostic, not a target"; that sentence has
been **removed** — the threshold is now a gate and it blocks the `dev → test` and
`test → prod` promotions.

### 7.1 What is measured

- **Line coverage**, every codebase **separately**: backend · web · Android · iOS. Never a combined average.
- Branch and function coverage are **reported** but the threshold is on lines. ⚠️ v8 (Vitest) counts branches only for the files it **loaded** — files never imported do not enter the branch denominator, which makes the branch percentage look inflated.
- E2E does not count. It measures a scenario, not a line; it is a separate gate.

### 7.2 The denominator — what may be excluded

Only **generated or non-product** code:

| Stack | May be excluded |
|---|---|
| .NET | `Migrations/`, `*ModelSnapshot.cs`, `*.Designer.cs`, `obj/`, `*.g.cs` |
| TS/React | `*.test.ts(x)`, `*.d.ts`, `e2e/`, `*.config.ts` |
| Android | `R`, `BuildConfig`, generated Hilt/Room/Compose classes |
| iOS | test targets, generated resource accessors |

The exclusion list lives in **one file** in the project, with a reason next to
every pattern.
⚠️ **Hand-written product code may never enter the list** — including files that
are hard to test (an HTTP client, start-up code). A hard file is tested **with a
fake dependency** (a fake `HttpMessageHandler`, a fake clock), not excluded from
the denominator.

⚠️ **The raw number misleads.** One project's backend measured 95.0% with
migrations included — and **83.0%** once they were excluded. EF migrations run by
themselves during tests and made up 85% of the denominator.

### 7.3 The gate

- A step in the shared gate (`scripts/merge-gate.sh`), running at **every** promotion including `dev`; below the threshold the exit code is ≠ 0. CI calls the same script (#19, #25).
- A codebase that cannot be measured is reported as **"not measured"** and **still blocks** the promotion — a gate that did not run did not pass.
- The threshold is never lowered in a project; a project's `CLAUDE.md` cannot override it.

### 7.4 Commands per stack

```bash
# .NET — coverlet (included in the xunit template), cobertura output
dotnet test <sln> --collect:"XPlat Code Coverage" --results-directory <dir>
# two test projects produce separate files and the same line may appear in both →
# take the UNION of the lines, not the sum

# Vitest — @vitest/coverage-v8; the threshold lives in the config
#   coverage: { include: ['src/**/*.{ts,tsx}'], thresholds: { lines: 80 } }
npx vitest run --coverage

# Android — Kover (a Gradle plugin; ask before adding it, global #10)
./gradlew koverVerify          # koverVerify { rule { minBound(80) } }

# iOS
xcodebuild test ... -enableCodeCoverage YES -resultBundlePath <path>
xcrun xccov view --report --json <path>.xcresult
```

### 7.5 The quality of a test written for coverage

- A test with no assertion, one that merely runs the code and passes, is **forbidden** — it is the same as loosening the threshold.
- That every added test catches something is verified **by mutation**: break the line it tests and it must turn red. If it does not, it is not a test.
- In critical business logic (money, authorization, state machines) 80% is **a floor**, not a target — more is expected there.
- Mutation testing (Stryker) is valuable in critical modules — it exposes the "there are tests but they catch nothing" situation.

## 8. Flaky test policy

- A flaky test is **immediately** either fixed or quarantined (with an issue opened). Silently adding `retry` is forbidden.
- The usual causes: timing (`sleep`), shared data, order dependency, a real network, time zones, randomness.
- A quarantined test that is not resolved within two weeks is deleted or adopted; it is never ignored forever.

## 9. When tests change

- If the behaviour changed, the test changes — **that is normal**.
- If only a refactor happened, the test should not change. A test that breaks during a refactor is too tied to the implementation.
- **Loosening a test "so it passes" is forbidden** — no deleting assertions, no adding `Skip`, no lowering a threshold. Nothing is touched before it is understood why it broke.
- A test for an obsoleted field lives until that field is genuinely removed.

## 10. Tests in CI

- The fast gate (unit + tsc + lint) runs **on every push**.
- Slow or stateful tests (a live database, e2e) live in a separate workflow or are triggered manually — never mixed into the fast gate.
- Test output must be readable; the log must make clear **why** a failing test failed.
- Tests must run locally with the same command (`npm test`, `dotnet test`) — no CI-only magic.
