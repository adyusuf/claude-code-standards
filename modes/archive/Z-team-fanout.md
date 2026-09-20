# Mode Z — Team + fan-out (the team equivalent of E)

⚠️ **Z is the team equivalent of subagent mode E (fan-out).**

On top of Y's roster, the **`Workflow` tool is enabled** — but with an important
restriction.

⚠️ Shared rules: [`team-rules.md`](team-rules.md) — **including the §0
precondition** · role selection [`role-selection.md`](../role-selection.md).

## ⚠️ The restriction: the LEADER runs fan-out, a teammate cannot

An **in-process teammate cannot start a background agent** (stated verbatim in the
Claude Code binary). `Workflow` runs in the background.

⚠️ **The inference here is NOT VERIFIED:** the text of that prohibition belongs to
the `Agent` tool's `run_in_background` path; `Workflow` runs through a different gate,
and **no** teammate-specific `Workflow` prohibition could be found in the binary. The
rule below is therefore not a mechanism finding but **a deliberate restriction** — its
rationale is that fan-out should concentrate in the leader so the cost is visible in
one place. If it is tried and found otherwise, it is reconsidered with that reasoning;
it does not lapse on its own.

So:

- **I (the leader) call `Workflow`.** Teammates cannot.
- If teammates need fan-out, they open a task for me and I run it.
- ⚠️ Whether this restriction lifts in other teammate transports is **not verified** —
  do not assume, and do not claim "it can be done" without trying it.

For that reason Z is not "D + a team"; it is **"the leader running a parallel sweep
while the team works"**. The benefit: when the fan-out result arrives, the roles that
will use it are already up with warm context — in D you would have to set the agents
up again at that moment.

## Rules
- `Workflow` only when there are **5 or more genuinely independent** pieces of work.
- **A live Artifact dashboard is mandatory** (the global "LIVE DASHBOARD during a long
  gate/run" rule): the weighted percentage + the measurement timestamp + the risks +
  **the number of open findings**.
- Before the run, the **teammate count + workflow agent count + cost estimate** are
  written down.
- Review: the `qa` teammate; critical findings are verified by me.
- Fan-out output also goes through **one clean pass**; if something is missing the task
  is reopened.

## When to use it
A long feature with a wide scan or audit running alongside it at the same time. If it
is only a scan, **D is enough and cheaper**; if it is only a feature, **Y is enough**.

## Expected cost
**~6–12x** (NOT MEASURED — the most expensive mode). Threshold: ~$300 warning /
**~$600 stop**. Choosing this mode means approving an unmeasured multiplier up front.
