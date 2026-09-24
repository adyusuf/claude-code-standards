# Test inventory — index

> Updated: <dd/mm/yyyy> · the screens are in risk order (money → public → identity →
> authorization → pricing rules → mutation → read-only).

| # | Screen | Route | Phase | 🔴 | 🟡 | 🟢 | Open · in progress · closed | Top finding | Report |
|---|---|---|---|---|---|---|---|---|---|
| 1 | … | `…` | 1 | 0 (0 open, 0 in progress) | 0 | 0 | 0 · 0 · 0 | … | `<slug>.md` (as a relative link) |

The priority columns count findings that are NOT closed. A finding leaves them only
when it closes: a test gap when its test is green in phase 3, a defect or unhandled
case when the approved fix or decision is applied. "In progress" = test written, not
yet run — the status column is what shows progress between phases.

## Findings that span several screens

Report a shared root cause once here (e.g. "the shared gateway fake always succeeds",
"no concurrency control on any aggregate") and link each affected screen to it.

## E2E backlog (written at the `test → prod` gate, global #33)

- …

## Parity backlog (feature missing on a layer — not a test gap)

- …
