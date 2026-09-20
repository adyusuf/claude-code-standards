# Database Standards

## 1. Naming

- Tables: plural `PascalCase` (the EF default) or `snake_case` — **one style per
  project**, never mixed.
- Columns: a clear field name; no abbreviations. Booleans use `Is*`/`Has*`.
- Foreign keys: `<Entity>Id` (`MemberId`). Index names `IX_<Table>_<Columns>`, FK names
  `FK_<Table>_<TargetTable>_<Column>`.
- Reserved words are avoided (`user`, `order`, `group` → `Users`, `Orders`,
  `MemberGroups`).

## 2. Schema rules

- Every table has a **surrogate PK** (`int identity` or `uuid`). A natural key is never
  the PK (it can change).
- Every table has audit columns: `CreatedAt` (UTC), `CreatedByMemberId`, `UpdatedAt`,
  `UpdatedByMemberId`.
- Time is **UTC** (`timestamptz`). Local time is never stored.
- Money: `numeric(19,4)` plus a separate `Currency` column. Money as `float`/`real` is
  **forbidden**.
- Text: `varchar(n)` sized to the business rule rather than an unbounded `text` — but
  **narrowing a limit is breaking** (see `08-backward-compatibility.md`).
- Enums are stored in the DB as `int` or `varchar`; **if `int`, the numeric value of a
  member never changes** and no value is inserted in the middle.
- Referential integrity is enforced in the DB with FKs — "the application checks it
  anyway" is not enough.
- Delete behaviour is chosen explicitly (`Restrict` by default; `Cascade` only for a true
  ownership relationship).

## 3. Indexes

- An index on every FK (Postgres does not create them automatically).
- Indexes on frequently filtered or sorted columns; **order matters** (equality columns
  first, range columns last).
- A covering index with `INCLUDE` for large lists.
- If a uniqueness constraint is a business rule, use `UNIQUE` — but **adding a new UNIQUE
  to an existing table is breaking** (clean and validate the data first).
- Unused indexes are dropped (they cost on writes). Check `pg_stat_user_indexes`
  periodically.
- For accent- and case-insensitive search, a functional index on `unaccent(lower(col))` or
  a `pg_trgm` GIN index.

## 4. Migration discipline

- **Every schema change goes through a migration.** Running SQL by hand and saying "I'll
  write the migration later" is forbidden.
- A migration's name says what it does: `AddPhoneNumbersToMember`.
- The generated SQL is **read** — what EF produces is not trusted blindly.
- One migration = one logical change. A schema change and a large data migration never
  share a migration.
- `Down` is written, or the rollback plan is documented.
- A long-running operation locks production: in Postgres use `CREATE INDEX CONCURRENTLY`,
  add columns without a default (fast on PG11+), and prefer a new column over `ALTER TYPE`.
- Migrations accumulate **forward**; a past migration is never edited (it may already have
  been applied).

## 5. Query rules

- `SELECT *` is forbidden — select the columns you need.
- **No N+1**: no query inside a loop; one query via a join or a projection.
- No list query without pagination; `OFFSET` gets slower the deeper it goes → use
  keyset/cursor pagination on large sets.
- Raw SQL is **parameterised**; string concatenation = SQL injection.
- If a query plan is suspect, look at it with `EXPLAIN ANALYZE`; "slow" is never optimised
  by guesswork.
- A `statement_timeout` is applied to long queries.

## 6. Transactions

- The transaction boundary is **the service method** (one unit of work). Not the
  controller, not the repository.
- **No outbound call inside a transaction** (HTTP, email, a queue) — it extends the lock
  and creates inconsistency. External effects happen after commit (the outbox pattern).
- The isolation level is chosen deliberately; `ReadCommitted` by default. If there is a
  lost-update risk, use optimistic concurrency (`xmin`/`rowVersion`).
- To avoid deadlocks, resources are accessed **in the same order** everywhere.

## 7. Delete policy

- User data is generally **soft deleted** (`DeletedAt`, `DeletedByMemberId`) plus a global
  query filter.
- If soft delete is used, unique indexes must be partial with `WHERE DeletedAt IS NULL`.
- Hard delete only for a data-protection erasure request or clearing junk data, and **with
  approval**.
- Deletion is a **product decision** — who may delete, how long it can be undone; it is
  never assumed without asking the user.

## 8. Multi-tenancy

- Tenant separation is mandatory **on every query** — a global query filter, verified by a
  test.
- Every use that bypasses the filter (`IgnoreQueryFilters`) carries a justifying comment.
- An automated test is written for tenant leakage ("tenant A cannot see tenant B's
  record").

## 9. Backup and recovery

- A daily automatic backup plus a weekly **off-server** copy.
- **A restore drill once a month.** An untested backup is not a backup.
- The retention period and encryption are defined.
- A manual backup before any `DROP` or bulk `UPDATE`, and a rehearsal in the test
  environment first.
- The point-in-time recovery target (RPO/RTO) is written down.

## 10. Seed and test data

- Seeds are **idempotent** (running twice produces no duplicates).
- Test data is realistic: names with non-ASCII characters, long strings, boundary values,
  empty fields.
- Production data is never copied into a development environment **unmasked** (data
  protection).

## 11. Never-do list

- ❌ A manual schema change (with no migration)
- ❌ `SELECT *`, N+1, a list with no pagination
- ❌ `float` for money
- ❌ Storing local time
- ❌ Changing an enum's numeric value / inserting a value in the middle
- ❌ An HTTP or email call inside a transaction
- ❌ A `DROP` without a backup
- ❌ Mixing the test and production databases (connection strings are per environment and
  controlled)
