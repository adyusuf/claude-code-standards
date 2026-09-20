# Operating modes — the single source

**Five** modes determine how a task is carried out: **A-E, subagent-based.**
(The Agent Teams modes X-Z are archived → [`archive/README.md`](archive/README.md).)
Reading order: **a session-scoped selection** (`/working-mode <letter> --tek`, not
written to the project file) → the project's `.claude/mode` → **B**. If neither
exists, **B** applies.

| Mode | Name | Agents | Review | Approval policy | Cost multiplier |
|---|---|---|---|---|---|
| [**A**](A-skill.md) | Skill | **none** | me | chosen explicitly | 1.0x (baseline) |
| [**B**](B-selective.md) | Selective **(DEFAULT)** | `analyst`, `test-writer`, `doc-writer` | me | the default = approval | 1.15–1.35x ⚠ estimated |
| [**C**](C-full-team.md) | Full team | 9 role agents (B ⊂ C) | the `qa` agent + me | choosing the mode = approval | 2.5–4x ⚠ estimated |
| [**D**](D-wide-team.md) | Wide team | 14 role agents (C ⊂ D) | `qa` + `security`/`coverage-auditor` directly to me + me | choosing the mode = approval | 4.5–7x ⚠ estimated |
| [**E**](E-fanout.md) | Fan-out | D + parallel `Workflow` (the 14 roles only) | the `qa` agent + me | choosing the mode = approval | 7–14x ⚠ estimated |

⚠️ **None of the multipliers has been measured** — the modes were created after the
measurement we have (33 sessions), which contains no mode comparison. The wall-clock
claims (C 20–40%, E 50–70%) are **not measured** either. The only thing measured is
role cost: the measurement ledger in [`role-selection.md`](role-selection.md) §8 —
where a `qa`/opus turn measured **$4.10**.

### The Agent Teams modes — X · Y · Z → **ARCHIVED**

The team modes were moved to `modes/archive/` because they **cannot be started**
(reason, the condition for bringing them back, and the mappings:
[`archive/README.md`](archive/README.md)). They are not offered as a mode; if the
user asks, the answer is "it cannot be started today".

## Role → auditor → what closes a finding

Who checks each role's output, and what has to be re-run before a finding counts as
closed (global #28: *a claim of "fixed" is not closure*). "Block" = the role closes its
report with the §7 completeness-check block, which
`python3 scripts/evidence-check.py <report>` validates. Sources:
[`role-selection.md`](role-selection.md) §1–§3 and §7, and each `agents/<role>.md`.

| Role | Modes | Audited by | Closed by re-running | Block |
|---|---|---|---|---|
| `product-manager` | C+ | **the user** — the scope is presented as one block and approved (§2a) | the user's explicit approval | yes |
| `analyst` | B+ | the orchestrator re-runs the command the analyst returned and compares the count | the analyst's own command (`grep -rn …`, `rg -c`) | yes |
| `architect` | C+ | not defined in the sources | — | no |
| `designer` | C+ | not defined in the sources | — | no |
| `developer` | C+ | `qa`, then the orchestrator verifies the critical findings | `qa`'s `Verification` command | no |
| `test-writer` | B+ | `qa` reviews the diff in parallel (§2) | `qa`'s `Verification` command | yes |
| `devops` | C+ | `qa` (infrastructure diffs are in scope) | `qa`'s `Verification` command | yes |
| `doc-writer` | B+ | the orchestrator verifies the permanent decision (rule files are outside `qa`) | reading the written text against the decision | no |
| `qa` | C+ | the orchestrator verifies the critical findings | the `Verification` line of its own block | yes |
| `security` | D+ | the orchestrator verifies the critical findings | the finding's verification command | yes |
| `data` | D+ | `qa` looks again along backward compatibility and data loss | `qa`'s `Verification` command | yes |
| `coverage-auditor` | D+ | straight to the orchestrator | the coverage command **and** the mutation check (remove a test; the gate must fail) | yes |
| `observability` | D+ | `qa` | `qa`'s `Verification` command | yes |
| `e2e-writer` | D+ | not defined in the sources | — | yes |

A "not defined" cell is a gap in the rule set, not a role that needs no check.
Until it is closed, the orchestrator's own end-of-turn block is the only audit of that
role's output.

## Permanent rule — agents only come with a mode

**No agent is called in A; in B/C/D/E choosing the mode is the approval for that
agent set.** No separate question before a call; at the end of the turn, how many
agents ran and the estimated cost are **reported**. If an agent is needed but the
mode is A: I do not start it, I **propose changing the mode** (`/working-mode B`) —
the decision is the user's.

⚠️ **Automatic delegation is a call too.** Claude Code may suggest an agent on its
own by matching its `description`; in A that is **not followed**, and in B/C/D it is
followed only if the agent is within that mode's set.


## Rules OUTSIDE the mode, applying in every mode

- Irreversible work (deploy, `DROP`, force push, sending anything outward) →
  **requires approval in every mode**. Choosing a mode does not cover it.
- The `test`/`prod` promotion → the user says so explicitly **in every mode**.
- The completeness check before "done" (global #24) → the same in every mode.

## If no mode is given — PROPOSE the cheapest and fastest

If the project carries no `.claude/mode` **and** the user has not named a mode:

1. **Start in B** (the default) — `analyst`, `test-writer` and `doc-writer` are
   enabled, code and review stay with me. No separate question for those three
   agents; the default itself is the approval.
2. If the work **genuinely** deserves a higher mode (a 15+ file end-to-end feature →
   C; work with a security/data/coverage/e2e dimension → D; 5+ independent pieces →
   E), **do not switch on your own** — **propose it in one line** at the start of the
   turn: which mode, why, and roughly how many times the cost (the multipliers in
   this README). The decision is the user's; if no answer comes, continue in B.
3. The proposal is always **the lowest sufficient** mode: if B is enough, C is not
   proposed.
4. ⚠️ **It also goes downward:** if the work does not even deserve B's three agents
   (one file, one command, pure thinking work) it is carried out without calling any
   agent — that is not switching to A, it is the "I do it myself" branch of §0 within
   B. Not using an agent is not a violation of B; **calling an unnecessary agent** is.

If `.claude/mode` exists, this section does not apply — that file is an explicit
decision.

## Audit and cost visibility

In every mode, on every turn that uses agents:

1. **The auditor does not ask — it checks, and sends work back if something is
   missing.** Every role whose output will be relied upon (`qa`, `analyst`, `devops`,
   `test-writer`, `product-manager`), and the orchestrator at every handoff, closes
   its report with an **evidence block** (verification command · item mapping · not
   covered → serious gap NO/YES). If something is missing or wrong the work
   **returns to its producer and is fixed**; it is not escalated to the user, and for
   closure **the same verification is re-run** — a claim of "fixed" is not enough and
   no finding drops silently.
   **One "no serious gap" is enough for a handoff** (`✅ clean`); that single pass
   **must carry evidence** — an unevidenced "clean" is invalid, and it does not
   exceed half the call count of pass 1 (+10–20% overhead).
   If the same work is sent back twice and still does not close, the chain stops and
   the user is **informed** — a status report, not a question.
   → [`role-selection.md`](role-selection.md) §7
2. **Cost is reported at every handoff**, never deferred to the end of the turn:
   `↳ analyst done · ~$3 · turn total ~$9 (2 agents) · threshold ~$150 (C)`.
   The threshold is **mode-dependent and two-stage**: a warning at half, a stop at
   the full figure — B ~$25 · C ~$150 · D ~$260 · E ~$400. Where the figures come
   from → §8.
3. **`product-manager` output goes to user approval**, it does not flow into the
   chain automatically (§2a). **`devops` output goes into `qa`** (§3).

⚠️ **Who audits whom** — the gaps are deliberate, not silent:

| Role | Its auditor |
|---|---|
| `developer`, and code I write myself | **`qa`** → I verify the critical findings |
| `qa`, `analyst`, `devops`, `test-writer`, `product-manager` | Their own **completeness-check** block (§7) + the orchestrator |
| `product-manager`'s scope | **The user** (the §2a approval gate) |
| `architect`, `designer`, `doc-writer` | **No separate auditor** — exempt from the completeness-check block; the orchestrator audits them |

No second auditor **agent** was added behind `qa`: subagent tokens cost ~4x more than
the main conversation, and the gain does not cover the cost.

## Role selection (C · D · E)

**The orchestrator** decides who does what — agents never call each other. The
criteria: [`role-selection.md`](role-selection.md).

## Autonomous runs (layered on C/D/E)

Leaving long work to run on its own: [`autonomous-run.md`](autonomous-run.md).
The approval falls under #20 and is CONDITIONAL — task list, definition of done,
budget ceiling, stall brake, stopping on any irreversible action.

## Selecting a mode

    /working-mode           # show the current mode
    /working-mode B         # switch this project to B (persistent)
    /working-mode B --tek   # this session only, do not write the file
