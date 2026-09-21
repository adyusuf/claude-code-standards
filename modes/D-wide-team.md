# Mode D — Wide team (14 roles)

C's nine roles plus **five auditing roles**. I am the orchestrator (there is NO
separate orchestrator agent — that would mean a second cold prefix).

## The agent set

**The nine from C:** `product-manager` · `analyst` · `architect` · `designer` ·
`developer` · `test-writer` · `qa` · `devops` · `doc-writer`

**The five D adds:** `security` · `data` · `coverage-auditor` · `e2e-writer` ·
`observability`

⚠️ **D is a superset of C** (B ⊂ C ⊂ D). All five new roles are **auditors**: none
of them writes product code, and two (`data`, `e2e-writer`) produce only within
their own narrow area.

## Why these five roles

Each one is the unowned work of **a rule that is already written down**:

| Role | The rule left unowned |
|---|---|
| `security` | #19 — SAST, secret scanning, CVEs, ZAP, the OWASP Top 10 mapping |
| `data` | #4 + #9 — additive schema evolution, migrations, indexes, transactions |
| `coverage-auditor` | #29 — 80% line coverage per codebase, denominator honesty |
| `e2e-writer` | #30 + #31 + #32 — e2e data, the run cycle, classification |
| `observability` | the `standards/17-observability.md` standard — logs, metrics, traces, alerts, performance |

In C this work was either squeezed into one of `qa`'s axes or belonged to nobody.

## Rules

⚠️ **The rule for deciding who does what lives in a separate file:**
[`role-selection.md`](role-selection.md) — agent or me, work type → role, ordering
and handoff, skipping, conflict arbitration, stopping, visibility. **Read it before
selecting a role.**

- The order is not fixed; I select the roles the work requires and write down at the
  start of the turn **which ones I chose and why, and which ones I skipped and why**.
  ⚠️ **Running all fourteen roles every turn is not using D, it is wasting it** — a
  typical turn opens 5–8 roles.
- Independent roles are started **in parallel in the same message**.
- `developer` only for **isolated pieces with a clear contract**; cross-layer work
  stays with me.
- I do not ask before an agent call; I pass a cost line at **every handoff** (§6, §8).
  The threshold is two-stage: **a warning at ~$130, a stop at ~$260**.
- The auditing roles **do not ask, they check**: if anything is missing or wrong the
  work is **sent back to its producer and fixed**, and closure is evidenced by
  re-running the same verification; a handoff requires **one clean pass** (§7). If it
  is not closed within 2 hand-backs the chain stops, the open findings are listed and
  you are **informed**.

## The auditor map — who reports to whom

This is D's real difference from C: **`qa` stops being the only auditor.**

| Producer | Its auditor |
|---|---|
| `developer` · `test-writer` · `devops` | `qa` |
| `data` · `e2e-writer` · `observability` | `qa` |
| **`security`** | **the orchestrator** (directly) |
| **`coverage-auditor`** | **the orchestrator** (directly) |
| `qa` | the orchestrator — I verify the critical findings |
| `product-manager` | **the user** (the §2a scope gate) |
| `architect` · `designer` | the orchestrator (the §7 exemption) |

⚠️ **Why `security` and `coverage-auditor` do not go through `qa`:** in C three
producers reported to `qa`; across fourteen roles that would rise to eight, and the
busiest node in the chain would also be the least audited one. These two are **final
on their own axis** — `qa`'s security axis is already covered more deeply by
`security`, and measuring coverage a second time adds nothing. What matters is the
denominator decision and the attack-scenario decision, and the orchestrator verifies
those.

⚠️ **The `architect` exemption is riskier in D:** the plan now feeds `data`,
`security` and `e2e-writer` as well — three times the blast radius it had in C. The
exemption stands, but when the implementation deviates from the plan the chain comes
back to **me**, not to `architect`.

## Gate or agent — the timing

**The gate is the authority; an agent does not replace the gate.** The red/green
decision belongs to `scripts/merge-gate.sh` and CI. An agent saying "clean" does not
make the gate passed, and #19's "a gate that did not run did not pass" stands
unchanged.

**They do not do the same job — they look at different things:**

| | Gate (script/CI) | Agent |
|---|---|---|
| What it looks for | A known pattern | Something that needs context |
| Example | `gitleaks`: "this string looks like an AWS key" | "this endpoint never checks authorization" |
| Its output | An exit code | A finding + an attack or data-loss scenario |
| How it errs | False positives | Misses |

The third and most important job: **the agent audits the gate itself** —
`continue-on-error`, a swallowed exit code, a step that never runs but looks green. A
script cannot find that about itself (#19: "you do not accept a scan's clean result
without a control variable proving it can find something").

### The gate-paired roles do NOT run in the `dev` direction

`security` and `coverage-auditor` run **only on the `dev → test` and `test → prod`
promotions**. They are not invoked in the `feature/* → dev` direction.

- Reason: #25 deliberately keeps the `dev` merge fast; adding five auditors there
  would reinstate the banned gates by way of agents. The gates belong at promotion,
  and so do these agents.
- ⚠️ The cost is accepted: a security or coverage problem becomes visible at
  promotion time rather than on `dev`. In exchange, `dev` stays fast.
- The single exception in the `dev` direction is #25's own exception: the
  **pre-commit gitleaks** hook. That is a gate, not an agent, and it stays enabled.

### The roles that are NOT gate-paired run whenever the work needs them

`data` and `observability` are **outside** this restriction, because they are not the
counterpart of a promotion gate — they are audits needed **while the code is being
written**:

- ⚠️ **`data` specifically runs BEFORE `dev`.** Auditing a migration after it has
  landed on `dev` is too late: a wrong schema change cannot be undone, and #4's
  additive rule can only be applied before it is written. Work that touches the
  schema is not merged to `dev` without `data`.
- `observability` also produces value while the code is being written — noticing a
  missing log in production is by definition too late.

`e2e-writer` is already environment-bound: per #31 it runs **only against code that
has reached `test`**, which puts it outside the scope of this decision.

## When to use it
- An end-to-end feature **with a security or data dimension** (auth, payments, data
  protection, migration)
- The full gate before a `test`/`prod` promotion (#19 + #29 + #31 together)
- A feature containing a schema change — without `data`, nobody verifies backward
  compatibility

**When NOT to:** routine features, single-layer work, a change with no
security/data/coverage dimension → **C is enough**. Making D the default in place of
C means running five auditors for nothing.

## Expected cost

**4.5–7x** ⚠ estimated (C's 2.5–4x × ~1.75). A calculated full turn (Opus 5, 14
roles, auditing included): **~$11.4**; C's nine roles on the same model come to ~$6.5.

⚠️ That figure is **not a measurement**: the token profiles and a 35% probability of
a hand-back are assumptions. The only measured number is the ~$6.9 average per agent
turn (§8). On the first real D turn, record **how many findings were sent back** —
that is the weakest link in the estimate.

