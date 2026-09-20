# Mode Y — Team: full roster (the team equivalent of C)

Nine roles can be opened as teammates; **I am the leader** (there is NO separate
leader agent).

⛔ **Precondition:** [`team-rules.md`](team-rules.md) **§0** — the role definitions
do not carry the team tools and the feature is disabled; Y does not open until both
are resolved.

⚠️ Shared rules: that whole file. Role selection:
[`role-selection.md`](../role-selection.md) §0-§7. **Read both before opening a role.**

## The roster
`product-manager` · `analyst` · `architect` · `designer` · `developer` ·
`test-writer` · `qa` · `devops` · `doc-writer`

⚠️ Y is a **superset of X**. Test writing is not left to `developer`.

## Rules
- **Do not open all of them at once.** The number of teammates alive at any moment is
  what the work requires (criterion: `role-selection.md` §0 — "agent or me").
  ⚠️ The cost of an idle teammate is **not measured**; a teammate drops to idle and
  produces no turns until a message arrives (`team-rules.md` §7).
  At the start of the turn I write **who I opened and why**, and I **close** a
  teammate whose work is finished.
- `developer` only for **isolated pieces with a clear contract**. Cross-layer work
  stays with me.
- Review: the `qa` teammate makes the first pass and **I verify the critical
  findings**.
- `product-manager` output does not flow into the chain, it comes to **your approval**
  (§2a).
- `devops` output goes into `qa` (§3, including its intersection with #25).
- I assign the task `owner`s; free grabbing is disabled.

## The difference from C — in one sentence
In C the roles report to **me** and then end; in Y the roles report to **each other**
and stay alive. The expected gain: the hand-back loop gets cheaper (the producer is
still up). ⚠️ Neither that gain nor its cost has been **measured**.
⚠️ Because the roles report to each other, it is essential that the
completeness-check block also goes **to the leader** (`team-rules.md` §4).

## When to use it
An end-to-end feature (backend + web + mobile), 15+ files, **and** several
round-trips expected between roles. For a one-directional flow, **C is cheaper**.

## Expected cost
**~3–6x** (NOT MEASURED). Threshold: ~$150 warning / **~$300 stop**.
