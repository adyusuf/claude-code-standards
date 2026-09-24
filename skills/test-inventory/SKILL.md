---
name: test-inventory
description: Screen-by-screen test audit in four phases — (1) inventory every test layer of a screen as use cases, hunt for defects, gaps and unhandled cases, and report; (2) write the approved missing tests and report; (3) run every suite, list and classify each failure one by one, report; (4) fix the failures, re-run only what was fixed, then hand back to phase 3 for one full run — the 3 → 4 → 3 loop repeats until green or the ceiling. Use when the user says "/test-inventory", "review the tests", "find the missing tests", "which use cases are tested", "test inventory per page", "eksik testleri bul", "testleri gözden geçir", "sayfa sayfa test envanteri".
---

# Test inventory — audit → write → run ⇄ fix

One screen at a time, every layer at once (web unit · e2e · backend unit/integration ·
Android · iOS · Maestro). The unit of work is a **use case**, not a file: a report tells
the reader what the screen does, which layer proves each behaviour, what is wrong and
what nobody handled.

## Arguments

`/test-inventory <phase> <target>`

| Argument | Values | Default |
|---|---|---|
| `phase` | `1` audit · `2` write · `3` run · `4` fix | `1` |
| `target` | a route or screen name · `top N` (risk-ranked) · `all` | ask |

## The four phases

| Phase | Does | Changes code? | Ends with | Reference |
|---|---|---|---|---|
| **1 — Audit** | Maps the screen, lists tests per layer as use cases, measures coverage, hunts defects and unhandled cases, verifies every finding | No (report files only) | Docs synced · report + the list of tests proposed for phase 2 → **STOP, wait for approval** | `references/phase-1-audit.md` |
| **2 — Write** | Writes ONLY the approved tests, on a branch off `dev`, following the project's own test conventions | Tests only — product fixes are separate, approved tasks | Docs synced · report: finding → test file:line, or "not written + why" → **STOP** | `references/phase-2-write.md` |
| **3 — Run** | Runs every affected suite FULL, one suite at a time, never stopping at the first failure; lists each failure on its own line, re-runs each failing test in isolation, classifies it; proves new tests by mutation; measures coverage | **No** — phase 3 never edits anything | Docs synced · failure list (one row per failure, classified) → green: report and **STOP** · red: hand to phase 4 | `references/phase-3-run.md` |
| **4 — Fix** | Fixes the failures phase 3 listed, one at a time; after each fix runs ONLY that failure (and what the fix could affect) until it is green | Test/fixture/env: yes · product code: only fixes already approved | Docs synced · all listed failures green in their narrow runs → **calls phase 3 again** for one full run | `references/phase-4-fix.md` |

### The 3 ⇄ 4 loop

```
phase 3 (full run, classify) ──red──▶ phase 4 (fix, narrow re-run) ──all fixed──▶ phase 3
        │                                   │
      green ──▶ report, STOP        unapproved product bug / ceiling ──▶ report, STOP
```

- One **round** = one phase-3 run + the phase-4 fixes that follow it. Rounds are
  numbered in the report (R1, R2, …).
- **Ceiling: 3 rounds** (global #28's three passes). If the third phase-3 run is still
  red, stop and report every still-open failure individually — do not start a fourth.
- The loop also stops early when a failure needs a decision that is not the agent's:
  a product bug whose fix was not approved, a test whose expectation contradicts a
  project rule, or an environment the agent cannot repair (a missing secret).
- Phases 1 → 2 → 3 are gated by the user; 3 ⇄ 4 runs on its own inside those limits.

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
9. **Every phase ends with a documentation sync** (`references/doc-sync.md`): the
   findings register, every screen report, the index, and the project documents the
   phase made stale (`CLAUDE.md` counts and known gaps, `SETUP.md`) are updated
   before the chat report. A phase whose Markdown still describes the previous state
   is not finished.

## Where the reports live

Use the project's docs folder and naming convention. Default: `docs/test-inventory/`
with one `<screen-slug>.md` per screen, a `README.md` index and a **findings register**
(`findings.md`). If the project already has an inventory folder (for example
`docs/test-envanteri/`), continue there — never start a second one.

**Every finding is also written to the findings register** the moment it is verified
(`templates/findings.md`): a stable id (F-001…), screen, priority, class, evidence,
proposal and status. The register is the one list the user approves from, phase 2
writes against and phases 3/4 close; screen reports reference its ids. A finding is
never deleted — it is closed with evidence, or marked "not a finding" with the reason.

## Supporting files

- `references/phase-1-audit.md` — screen selection, surface mapping, use-case matrix, verification
- `references/unhandled-case-checklist.md` — the defect and unhandled-case hunt (the most valuable step)
- `references/list-tests.md` — commands that list test names and counts per stack
- `references/phase-2-write.md` — how the approved tests are written
- `references/phase-3-run.md` — full run, per-failure isolation and classification, mutation proof, coverage
- `references/phase-4-fix.md` — fixing, narrow re-runs, the hand-back to phase 3, the ceiling
- `templates/screen-report.md` — the per-screen report
- `templates/index.md` — the index across screens
- `templates/findings.md` — the findings register (all findings and run failures, with status)
- `references/doc-sync.md` — the documentation sync that closes every phase
