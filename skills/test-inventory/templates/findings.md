# Findings register

> One list for every finding across all screens and phases — the screen reports link
> here instead of repeating details. A finding keeps its id forever; it is never
> deleted, only closed. Updated: <dd/mm/yyyy>

Status values: `open` · `approved` (fix or test approved, not done) · `in progress` ·
`fixed` (with evidence) · `won't fix` (with the user's decision) · `not a finding`
(disproved — keep the row and the reason).

| Id | Found | Screen(s) | Priority | Class | Finding | Evidence | Proposal | Status | Closed by |
|---|---|---|---|---|---|---|---|---|---|
| F-001 | <dd/mm/yyyy> · phase 1 | … | 🔴 | Defect / Unhandled / Test gap / Dead code / Parity | … | `path:line` | … | open | — |

## Run failures (phase 3 ⇄ 4)

| Round | Failure | Suite · test | Class | Isolation | Cause | Fix `path:line` | Narrow re-run | Status |
|---|---|---|---|---|---|---|---|---|
| R1 | … | … | … | red alone / green alone / flaky | … | … | `command` → green | fixed |
