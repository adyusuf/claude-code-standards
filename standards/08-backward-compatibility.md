# Backward compatibility — APIs and databases evolve additively only

> **Why this is so strict:** a mobile user stays stuck on an old version and may
> not update for days or weeks. A field removed today is a screen crashing on
> thousands of devices tomorrow. On the web everyone gets the new version the
> moment you deploy; on mobile they do not.

## 1. The golden rule

- **A new field** → nullable / optional / with a default.
- **A field being retired** → never deleted; made nullable and marked obsolete.
- **The name and type of an existing field never change.** Renaming = delete + add = **forbidden**.
- If a change is needed: **a new field is added** and the old one enters the obsolete flow.

## 2. Changes that count as breaking (the full list)

| # | Change | Why it breaks |
|---|---|---|
| 1 | Deleting a field/endpoint | The old client cannot find it / blows up on null |
| 2 | Renaming a field/endpoint | Identical to delete + add |
| 3 | A type change (`int`→`string`, `string`→`object`) | A parse error |
| 4 | Nullable → non-nullable (input) | The old client may not be sending the field |
| 5 | Non-nullable → nullable (output) | The old client does not null-check |
| 6 | A new **required** input field | The old client's request returns 400 |
| 7 | Tightening validation (lowering `MaxLength`, a new `Required`, a new `UNIQUE`) | Data that used to be accepted no longer is |
| 8 | A change of meaning or unit (currency→minor units, days→hours, local→UTC) | Silent, and the most dangerous kind |
| 9 | Changing an enum's **numeric** value, or inserting a value in the middle | The ordering shifts |
| 10 | Changing the error/status-code contract | The client mishandles the error path |
| 11 | Changing a route or an HTTP method | 404/405 |
| 12 | A global JSON serializer setting (casing, null handling, date format) | It changes every response at once |
| 13 | A SignalR/WebSocket hub method name or payload shape | Live connections drop |
| 14 | A change of default behaviour (default sort, default `pageSize`) | A silent regression |
| 15 | Tightening authorization (a record previously visible now returns 403) | That is a product decision; never done silently |

## 3. The obsolete lifecycle

```
1. ACTIVE      → normal use
2. OBSOLETE    → the new field was added; the old one is [Obsolete] + deprecated in Swagger
                 ⚠ the old field KEEPS RETURNING REAL VALUES (returning null = deleting it)
                 ⚠ the old input field is BRIDGED to the new one
3. OBSERVATION → at least 4-8 weeks; real usage is measured from access logs
4. VERIFICATION→ grep (every client) + production logs: is anyone still using it?
                 on mobile: is the number of users on the old version negligible?
5. REMOVAL     → in a separate deploy: from the code first, from the database (DROP) in the NEXT deploy
```

**Obsolete ≠ non-functional.** An obsolete field keeps working; the new one is
merely preferred.

## 4. The inventory table (kept in every project)

In `docs/backward-compatibility.md` or in the project's CLAUDE.md:

| Field/Endpoint | Obsoleted on | Replaced by | Condition for removal | Status |
|---|---|---|---|---|
| `Member.phone` | 2026-07-29 | `Member.phoneNumbers[]` | once users on mobile ≤2.3 drop below 1% | Under observation |

An obsolete entry that is not in the inventory is a forgotten obsolete entry.

## 5. The database: expand → migrate → contract

```
EXPAND    A new column/table is added (nullable, with a default). Old code keeps working.
          New code writes both the old and the new (dual write), or a trigger / the
          application layer bridges them.
MIGRATE   Historical data is backfilled (in batches, without locking production).
          New code starts reading the new column. The old column is still written.
CONTRACT  Once non-use is verified, the old column is DROPped in a SEPARATE deploy.
```

The rules:
- A migration must be **reversible**; write the `Down` or document the rollback plan.
- Before a migration containing a `DROP`, take a **manual backup** and rehearse it **in the test environment first**.
- Create an index on a large table `CONCURRENTLY` (Postgres) — never lock production.
- Never do both a schema change and a large data move in one migration; separate them.
- Adding `NOT NULL`: first nullable plus a backfill → then `NOT NULL` as a separate step.

## 6. Client-side defence

- Enum `switch` statements **always have a `default` branch** — the server may send a new value tomorrow.
- Unknown JSON fields are ignored rather than raising (strict deserialization off).
- New fields are typed as optional; if one is absent the UI does not crash.
- If a server response has an unexpected shape, the screen shows an empty or error state; the app does not close.

## 7. The automatic brake (scanned in CI)

The merge gate scans for these patterns and does not let them through without
`--allow-breaking`:

- A deleted `public` member, or deleted `[HttpGet/Post/Put/Delete]` / `[Route]` lines
- A new `[Required]` / a narrowed `[MaxLength]` / a new `[JsonIgnore]`
- A change to a global serializer setting
- In DDL: a new `NOT NULL` / `UNIQUE` / `CHECK`, a `DROP COLUMN`, an `ALTER TYPE`

**What automatic scanning cannot catch** (human review is mandatory):
- A change of meaning or unit
- A shift in enum numeric ordering
- The contents of a hub payload
- Tightened authorization
- A changed default value or sort order

## 8. If a breaking change really is unavoidable

1. Write an ADR: why it is unavoidable, and why the alternatives are insufficient.
2. Get the user's approval (this is a **product decision**, not a technical one).
3. Do it through a new version (`/api/v2`) or by enforcing a minimum client version.
4. Write the migration timetable, a measurement of client version distribution, and the rollback plan.
5. Keep the old path **working** for the whole of that timetable.
