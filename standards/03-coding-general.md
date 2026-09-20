# General Coding Standards (language-agnostic)

## 1. Naming

- Identifiers are **English**; comments and documentation are in the team's working
  language.
- A name states intent: `daysUntilExpiry`, not `d`; `normalizeMemberRow`, not
  `handleData`.
- Booleans start with `is/has/can/should`: `isActive`, `canEditProfile`.
- A function name is a **verb**, a class or type name is a **noun**. No abbreviations
  (`usr`, `mgr`, `tmp`).
- The same concept is called the same word everywhere. Mixing `Member` / `User` /
  `Person` is forbidden.
- No negative names: `isEnabled`, not `isNotDisabled`.

## 2. Function and file size

- A function does one job; review it if it exceeds 40 lines.
- **A file never exceeds 300 lines** — it is split at its natural boundaries. Splitting
  does not change behaviour.
- Nesting does not exceed 3 levels → use early `return` / guard clauses.
- If the parameter count exceeds 4, group them into an object or record.
- Instead of a boolean parameter, use a separate function or an enum (`render(true)` is
  unreadable).

## 3. Single source of truth

- URL / port / host / key / constant threshold → **one config module**. A fallback
  repeated in every file, such as `?? "http://localhost:5080"`, is forbidden.
- The same business logic is never written in two places. Code copied a third time moves
  to a shared location (twice is tolerated, the third triggers a refactor).
- Enums and constant lists live in one place; if the client and server share them, a
  generated type or a shared package is used.
- No magic strings or numbers: `if (status == 3)` → `if (status == MemberStatus.Active)`.

## 4. Error handling

- **Silent swallowing is forbidden:** `catch {}`, `catch (e) { return null; }` with no
  log, `.catch(() => {})`.
- A caught error is either handled or enriched and rethrown. Logging it and swallowing it
  does not count as "handled".
- An expected error (validation, not found, unauthorized) is expressed with a typed result
  or the appropriate HTTP status, not with an exception. Exceptions are for **exceptional**
  situations.
- Technical details are never shown to the user; the **full** detail plus a correlation id
  goes into the log.
- No PII, tokens or passwords in an error message.
- Resources are released on every path via `finally` / `using` / `defer`.

## 5. Null and boundary cases

- Nullability is modelled explicitly (C# nullable reference types on, TS `strict` on).
- Nothing coming from the outside world (HTTP, files, the DB, env) is used **without
  validation**.
- Empty list, single element, many elements, very long text, unicode/emoji, negative
  numbers, zero, and future/past dates are all considered.
- Dates and times are **stored and transported in UTC**; they are converted to local time
  only for display. Time-zone information is never lost.
- **Always pass an explicit culture when formatting dates.** In .NET and PowerShell, the
  `/` in a format string is not a literal character — it is **the culture's date
  separator**, and `:` is the time separator. On a machine with a Turkish locale,
  `Get-Date -Format 'dd/MM/yyyy'` produces `15.08.2026` — silently violating the global
  `dd/mm/yyyy` rule according to the machine's language. The same trap is worse when
  reading: `[datetime]::ParseExact(x, 'dd/MM/yyyy', $null)` falls back to CurrentCulture
  and **throws** because it cannot parse `15/08/2026` — so the writer and the reader
  cannot even meet inside the same codebase. The fix is to pass
  `[cultureinfo]::InvariantCulture` in both directions. Easy to test: force the culture to
  `tr-TR` and run a write→read round trip.
- Money is held as `decimal` (C#) or as integer minor units; calculating money with
  `double`/`float` is **forbidden**. The currency is stored alongside the amount.

## 6. Async

- An async path is async all the way through; synchronous blocking (`.Result`, `.Wait()`,
  wrapping in `Task.Run`) is forbidden.
- Every outbound call has a **timeout** and, where relevant, a **cancellation token**.
- Retries only on **idempotent** operations, with exponential backoff + jitter and an
  upper bound.
- Independent work that can run in parallel runs in parallel; sequential dependencies run
  sequentially.
- No fire-and-forget work — it is either awaited or written to a durable queue.

## 7. Comments and documentation

- A comment explains the **why**, not the **what**. A comment that repeats the code gets
  deleted.
- The source of a complex business rule is written next to it ("regulation X, article Y" /
  "ADR-004").
- If you write a `TODO`, include its owner and context:
  `// TODO(<name>, <yyyy-mm>): remove Y once X is settled`. An unowned TODO is forbidden.
- **Commented-out code is never committed** — git already remembers.
- A public API or service method documents what it does and which errors it returns.

## 8. Dead code and dependencies

- Unused functions, imports, files, feature flags and env variables are deleted.
- Before adding a dependency: is it genuinely needed, is it maintained (last commit, open
  issues), is the licence suitable, how large is it, is it being added for a single
  function?
- Dependency versions are pinned (the lock file is committed).

## 9. Logging

- Structured logging (key-value), not string concatenation.
- Levels: `Debug` (development), `Information` (a business event), `Warning` (expected but
  undesirable), `Error` (the operation failed), `Critical` (the system is at risk).
- Every request or operation carries a **correlation id**; logs are matched by it.
- Never in a log: passwords, tokens, card numbers, national identity numbers, a full email
  or phone number (mask them), a full request body.
- No logging inside a loop; log an aggregate summary instead.

## 10. Immutability and purity

- Immutable data wherever possible (records, readonly, `const`). Parameters are never
  mutated.
- Pure functions (no side effects) are preferred — they are easy to test.
- No global mutable state; state is carried either through DI or as an explicit parameter.

## 11. Ask yourself before review

- Would I understand this change if I read it in 6 months?
- If something breaks, **how would we notice** (is there a log, a metric, a test)?
- Can this code be misused? Does the compiler or the type system prevent the misuse?
- Did I leave anything behind that should have been deleted?

## Deriving uniqueness from a UUIDv7

A UUIDv7 is **time-ordered**: the first 48 bits (roughly the first 8 hex characters in
text form) are a millisecond timestamp. Two ids generated in the same millisecond
**share** that part.

If a short discriminator (a prefix, a short code, a directory name, a tenant label) is
derived from part of an id, take it from **the end**, not the beginning:

```csharp
// WRONG — the first 8 characters are the timestamp; two concurrent records get the same prefix
var prefix = $"tb-{id:N}"[..11];

// RIGHT — the random part is at the end
var prefix = $"tb-{id.ToString("N")[^8..]}";
```

The cost of this is not just an ugly collision: if the prefix determines **ownership** of
data (what a cleanup will delete, which record belongs to whom), two parallel jobs delete
each other's data. Easy to test: generate two ids at the same moment and assert the
prefixes differ.
