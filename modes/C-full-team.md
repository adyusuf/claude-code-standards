# Mode C — Full team

Nine role agents are enabled; **I am the orchestrator** (there is NO separate
orchestrator agent — that would mean a second cold prefix).

## The agent set
`product-manager` · `analyst` · `architect` · `designer` · `developer` ·
`test-writer` · `qa` · `devops` · `doc-writer`

⚠️ C is a **superset of B** — `test-writer`, enabled in B, is enabled here too. Test
writing is not left to `developer`: letting the agent that writes the product code
write its own tests is the quietest way to loosen a test "so it passes".

## Rules

⚠️ **The rule for deciding who does what lives in a separate file:**
[`role-selection.md`](role-selection.md) — agent or me, work type → role, ordering
and handoff, skipping, conflict arbitration, stopping, visibility. **Read it before
selecting a role.**

- The order is not fixed; I select the roles the work requires and **write down at
  the start of the turn which ones I chose and why**.
- Independent roles are started **in parallel in the same message** (one turn, short
  wall clock).
- The `developer` agent is used only for **isolated pieces with a clear contract**
  (one file, a defined signature). Cross-layer work stays with me.
- Review: the `qa` agent makes **the first pass** and **I verify** the critical
  findings. Review is not lost, it becomes two-layered (#27).
- I do not ask before an agent call; the agent count and the estimated cost are
  reported at the **end of the turn** (#27, `role-selection.md` §6). The mode's own
  expectation is still +$100–150 per full pass, and that is an estimate to plan with
  rather than a gate: the per-handoff cost line and the spending threshold were both
  removed (`README.md` › "Who audits whom").
- The auditing roles **do not ask, they check**: if anything is missing or wrong the
  work is **sent back to its producer and fixed**, and closure is evidenced by
  re-running the same verification; a handoff requires **one clean pass** (§7). If
  it is not closed within 2 hand-backs the chain stops, the open findings are listed
  and you are **informed**.
- `product-manager` output goes to **your approval** (§2a); `devops` output goes
  into `qa` (§3).

## When to use it
An end-to-end feature (backend + web + mobile), 15+ files, or work where your time
is worth more than the token cost.

⚠️ If the work has a **security, schema/migration, coverage-threshold or e2e**
dimension, C is not enough → [`D-wide-team.md`](D-wide-team.md) (14 roles).

## Expected cost
**2.5–4x** — roughly **+$100–150** per feature. Wall clock shortens by 20–40%.
