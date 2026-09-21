# Mode E — Workflow fan-out

On top of D's agent set (14 roles), the **`Workflow` tool is enabled**:
deterministic, parallel, multi-agent orchestration.

## Rules

⚠️ **The rule for deciding who does what lives in a separate file:**
[`role-selection.md`](role-selection.md) — agent or me, work type → role, ordering
and handoff, skipping, conflict arbitration, stopping, visibility. **Read it before
selecting a role.**

- ⛔ **A Workflow script runs only this mode's 14 role agents.** There are 21 active
  plugin agents on disk (`code-reviewer`, `test-engineer`, `code-simplifier`, …);
  **none** of them carries the §7 evidence block, the hand-back requirement or the
  clean-pass condition. Put one into a script and the dashboard will show "review
  ran" while the entire audit regime collapses in a single line.
- `Workflow` is used only when there are **5 or more genuinely independent** pieces
  of work. Writing a Workflow for a dependent chain is just an expensive way of
  calling agents in sequence.
- The script declares its stages via `meta.phases`; progress is followed from
  `/workflows`.
- **A status table is reported throughout a long run** (global rule: "STATUS
  REPORTING during a long gate/run"). The measured figures, the signal each was read
  from and the open risks go in a markdown table in the reply. ⚠️ No Artifact
  dashboard — it was removed from the flow on 21/09/2026.
- Before starting a Workflow I **write down the agent count and the cost estimate** —
  this mode removes asking per agent, not declaring the scale.
- Review: the `qa` agent; critical findings are verified by me.
- The Workflow prints a cost line **at the end of every phase** (it goes in the
  status table too), the auditing agents return the **completeness-check** block, and
  the **one clean pass** condition is required (`role-selection.md` §7). A phase that
  finds a gap **sends the work back and gets it fixed** (a retry gate in the script;
  closure is re-running the verification); if it is not closed within 2 hand-backs
  the phase stops and the open findings are written to the dashboard.
- The threshold (§8) in mode E is **a warning at ~$200, a stop at ~$400**; if it is
  going to be exceeded, it is asked before the run. The autonomous run's $100
  ceiling is independent of this — whichever fills first is the one that stops.

## When to use it
Multi-file scanning or auditing, repeating the same work across N modules,
exploration before a wide refactor. **Far too heavy** for routine feature work.

## Expected cost
**7–14x** ⚠ estimated, on top of the 14-role D baseline. Wall clock shortens by
50–70%. This mode buys time, not tokens.

