---
name: test-inventory
description: Screen-by-screen test audit in three gated phases — (1) inventory every test layer of a screen as use cases, hunt for defects, gaps and unhandled cases, and report; (2) write the approved missing tests and report; (3) run them, prove them by mutation and report. Use when the user says "/test-inventory", "review the tests", "find the missing tests", "which use cases are tested", "test inventory per page", "eksik testleri bul", "testleri gözden geçir", "sayfa sayfa test envanteri".
---

# Test inventory — audit → write → run

One screen at a time, every layer at once (web unit · e2e · backend unit/integration ·
Android · iOS · Maestro). The unit of work is a **use case**, not a file: a report tells
the reader what the screen does, which layer proves each behaviour, what is wrong and
what nobody handled.

## Arguments

`/test-inventory <phase> <target>`

| Argument | Values | Default |
|---|---|---|
| `phase` | `1` audit · `2` write · `3` run | `1` |
| `target` | a route or screen name · `top N` (risk-ranked) · `all` | ask |

## The three phases — each ends in a report and a STOP

| Phase | Does | Changes code? | Ends with | Reference |
|---|---|---|---|---|
| **1 — Audit** | Maps the screen, lists tests per layer as use cases, measures coverage, hunts defects and unhandled cases, verifies every finding | No (report files only) | Report + the list of tests proposed for phase 2 → **wait for approval** | `references/phase-1-audit.md` |
| **2 — Write** | Writes ONLY the approved tests, on a branch off `dev`, following the project's own test conventions | Tests only — product fixes are separate, approved tasks | Report: finding → test file:line, or "not written + why" → **wait** | `references/phase-2-write.md` |
| **3 — Run** | Runs the affected suites with the failure cycle, proves each new test by mutation, measures coverage per codebase | No product code; test defects only | Report: measured results, classified failures, mutation evidence → the user decides merges and promotions | `references/phase-3-run.md` |

A phase never starts the next one on its own. Approval between phases is the user's
(global #1 small step first, #26 the user decides promotions).

## Non-negotiables (all phases)

1. **Evidence or it did not happen.** Every "tested", "missing" or "wrong" carries a
   `file:line` or the command that showed it. A grep hit is a lead, not a finding —
   open the file and confirm before writing it down (global #15, #28).
2. **Numbers are measured.** Test counts, coverage and durations come from a run or a
   count command; otherwise the cell says "not measured".
3. **A defect is not a test gap.** A product bug found during the audit is reported
   as a defect with its own fix task. It is never quietly fixed inside a test task,
   and a test is never bent to pass around it.
4. **A missing feature is not a missing test.** If a layer does not implement the
   behaviour (e.g. mobile has no saved-card flow), the cell is `—` and the row goes to
   "parity", not "gaps".
5. **Dead code is not tested — it is proposed for deletion.**
6. **The project's rules win.** Read the project `CLAUDE.md` first: its layer layout,
   test commands, env vars (e.g. an integration DB string), language and doc folder.
   Respect the active operating mode for agent use (global #27); in mode A no agents.
7. **E2E follows global #33:** listed as gaps in phase 1, never written or run at the
   `dev` stage; they are written and run at the `test → prod` gate.
8. **Reports go to files and to chat.** Per-screen file + an index (see
   `templates/screen-report.md`, `templates/index.md`); the chat gets a short summary
   table (global "STATUS REPORTING"). No Artifact dashboards. Report prose is written in
   the user's language; file names follow the project's docs convention.

## Where the reports live

Use the project's docs folder and naming convention. Default: `docs/test-inventory/`
with one `<screen-slug>.md` per screen and a `README.md` index. If the project already
has an inventory folder (for example `docs/test-envanteri/`), continue there — never
start a second one.

## Supporting files

- `references/phase-1-audit.md` — screen selection, surface mapping, use-case matrix, verification
- `references/unhandled-case-checklist.md` — the defect and unhandled-case hunt (the most valuable step)
- `references/list-tests.md` — commands that list test names and counts per stack
- `references/phase-2-write.md` — how the approved tests are written
- `references/phase-3-run.md` — run cycle, mutation proof, coverage, reporting
- `templates/screen-report.md` — the per-screen report
- `templates/index.md` — the index across screens
