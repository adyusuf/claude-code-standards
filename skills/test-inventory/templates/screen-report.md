# Test inventory — <Screen name> (`<route>`)

> <One sentence: what the screen lets whom do.>
> Web: `<page file>` · Android: `<screen/actions>` · iOS: `<view/submission>` ·
> Endpoints: `<METHOD /api/...>`, …
>
> Audited: <dd/mm/yyyy> · branch `<branch>` · phase <1|2|3>

## 1. Tests on this screen — by the numbers

| Layer | Files | Tests |
|---|---|---|
| Web unit | … | … |
| Web e2e | … | … |
| Backend integration | … | … |
| Backend unit | … | … |
| Android | … | … |
| iOS | … | … |
| Mobile e2e | … | … |

**Measured coverage:** `<file>` NN.N % · … (command: `…`). Not measured: <which, why>.

## 2. Use cases and what is tested

`✅` tested · `◐` partly · `❌` not tested · `—` layer does not implement it.

| # | Use case | Web unit | e2e | Backend | Android | iOS |
|---|---|---|---|---|---|---|
| 1 | … | | | | | |

### UC-1 · <title>
- <what the tests assert, plain words — which layer>
- ❌/◐ <what is not asserted>

## 3. What is wrong — defects and unhandled cases

| # | Priority | Class | Finding | Evidence | Proposal |
|---|---|---|---|---|---|
| D1 | 🔴 | Defect / Unhandled | … | `path:line` | fix task / decision needed |

## 4. What is missing — test gaps

| # | Priority | Gap | Evidence | Proposed test (layer · name) | Phase 2 |
|---|---|---|---|---|---|
| G1 | 🟡 | … | `path:line` | … | pending / → `path:line` / not written: … |

## 5. Not counted as gaps

- Parity: <features a layer does not have>
- Dead code: <unused exports — propose deletion>
- E2E backlog (written at the `test → prod` gate): <items>

## 6. Run results (phase 3 ⇄ 4)

Findings and run failures are tracked in the findings register; this section is the
per-round summary.

| Round | Suite | Command | Passed / failed / skipped | Duration | Coverage |
|---|---|---|---|---|---|

| Round | Failure (register id) | Class | Isolation | Fixed by | Narrow re-run |
|---|---|---|---|---|---|

Mutation proof: | Test | Mutated line | Red | Reverted |
