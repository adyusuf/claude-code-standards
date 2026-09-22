# Role selection — who, on what basis, when

> **Role selection** (§0-§4) applies in C · D · E · **Y · Z**; in B and **X** only §0
> and §1 apply (the agent set is limited to three). **§5 (stopping), §6 (visibility +
> cost), §7 (the completeness check) and §8 (thresholds + measurement) apply in EVERY
> mode that runs agents** — including B/X. What narrows is the agent set, not the
> audit. There are no agents in A; there, §0's "I do it myself" branch applies, and
> **global #24 applies instead of §7** (a single mental pass) — §7's evidence block and
> hand-back chain are only for turns that run agents. (The team modes are archived:
> [`archive/README.md`](archive/README.md).)

**THE ORCHESTRATOR decides — that is, me.** Agents never call each other, never pick
the next role, and never change scope. No agent definition contains the `Agent` tool,
and that is **deliberate**: if role selection does not stay in one place, who did what
and why becomes untraceable and cost grows unpredictably.

⛔ **An agent's model can only be Claude (verified).** Claude Code's subagent `model:`
field accepts Anthropic models — `sonnet`, `opus`, `haiku`, or a full Claude model id.
Models such as Kimi, Gemini, GPT or Grok **cannot be run as role agents**; their own
applications (Kimi Code, Gemini CLI) are separate sessions, and §7's evidence block ·
hand-back · closure chain does **not** apply automatically there — it has to be
carried by hand. Third-party model comparisons therefore answer "which model suits
this work", not "can I wire this up".

⚠️ **Subscription vs. API in cost comparisons:** if Claude Code runs on a
subscription, Claude tokens are a fixed cost, and model comparisons made with API
price tables **overstate the marginal cost** in that case. If a model with no coding
application of its own is used as an agent, it adds **a separate bill** on top of the
subscription — the option that looks cheap in the table can be expensive in practice.

**The orchestrator's model = the session's model.** Agents have a `model:` field
(sonnet/opus/haiku, by cost); the orchestrator does not, because it is not a separate
process — it is whatever `/model` selected. ⚠️ This is the most expensive seat: it
carries all the context, every agent's output passes through it, and its cost comes
from **cache reads**, not from the agents (measured: 73% of the total). On that line
item Fable is half the cost of Opus (2.5% vs 10%) — measured at 0.90x; for a
long-context orchestrator Fable is cheap, while sonnet/haiku remain right for agents.

## §0 — First: an agent, or me?

Before selecting a role, decide **whether that work needs an agent at all**.

| The shape of the work | Decision | Why |
|---|---|---|
| **Reads a lot, returns little** (search, inventory, classification, cross-checking) | **Agent** | The reading load stays in the agent's context; only the result comes back to me |
| **Reads little, writes a lot** (code, prose generation) | **Me** | I re-read whatever the agent wrote, and so does the user → the same content becomes tokens two or three times |
| **The decision will be made together with the user** | **Me** | An agent takes the user out of the room |
| **One file, a clear contract, no exploration** | Can be an agent | The output is narrow and verifiable |
| **A few minutes, one command** | **Me** | ~$5-40 fixed cost per agent (an **estimate**, not a measurement — the one measured role sits at ~$4.10/turn); the work is cheaper than that either way |

⚠️ This table came out of cost measurement: a subagent token is ~4x more expensive
than the main conversation (a cache read/write ratio of 53:1 against 14:1), because
every agent writes its prefix from scratch.

## §1 — The shape of the work → the role

| Trigger | Role |
|---|---|
| The request is vague or broad, with no scope or acceptance criteria | `product-manager` → its output goes to **user approval** (§2) |
| "How does this work / where is it defined / how many places use it" | `analyst` |
| Will touch 10+ files, order and dependencies unclear | `architect` |
| A screen, a flow, empty/error states, accessibility | `designer` |
| Code: **isolated + clear contract** | `developer` |
| Code: **cross-layer / needs exploration** | **me** |
| Behaviour changed, tests are needed | `test-writer` |
| A diff is ready for review (code **or** infrastructure configuration) | `qa` → **I verify** the critical findings |
| CI, deploy, gates, backups, environments | `devops` |
| A permanent decision was made and needs writing down | `doc-writer` |
| **— below this line, modes D/E only —** | |
| Auth, secrets, authorization, injection, CVEs, OWASP mapping | `security` → **I verify** the critical findings |
| Schema, migrations, indexes, transactions, data migration | `data` → its output goes into `qa` |
| The coverage threshold (#29) to measure / the denominator to audit | `coverage-auditor` → **straight to me** |
| An e2e spec to write, or a failing run to classify | `e2e-writer` (only against the `test` environment) |
| Missing logs/metrics/traces/alerts, a performance regression | `observability` → its output goes into `qa` |

## §2 — Ordering and handoff

The order is **not fixed**; but once a role is selected, its input must be ready:

```
product-manager → scope + acceptance criteria + edge cases
        ↓
   ⛔ USER APPROVAL (does not flow automatically — §2a)
        ↓ (without these, architect cannot plan)
architect / designer → file plan + flow (can run in parallel)
        ↓
developer | me → code
        ↓
test-writer → tests          qa → review (in parallel)
        ↓
doc-writer → permanent decisions
```

**Independent roles are started in parallel in the same message.** Dependent ones
queue — if one's output is another's input, starting them in parallel means the second
one works with incomplete data.

### §2a — The scope gate

`product-manager` output does **not flow into the chain on its own**: the scope,
acceptance criteria and assumptions are presented to **the user as one block and
approval is awaited**. `architect`/`designer`/code do not start before that approval.

⚠️ Reason: `product-manager` has no auditor and cannot have one — `qa` will not say
"you built the wrong thing correctly", because it looks at the code, not the contract.
A wrong scope propagates through the entire chain and is the most expensive mistake.
The auditor here is **the user**; adding another agent would be both expensive and wrong.

## §3 — Skipping

A role **may be skipped**, but the skip **cannot be silent**: at the start of the turn
it is written down — "`designer` skipped because no visible interface changes".

Typical legitimate skips: the scope is already clear → no `product-manager` · the
interface does not change → no `designer` · single-file work → no `architect` · no new
permanent decision → no `doc-writer`.

### The gate-paired roles — the direction rule (modes D/E)

`security` and `coverage-auditor` run **only on the `dev → test` and `test → prod`
promotions**; in the `feature/* → dev` direction they are skipped, and that skip
**needs no explanation** (#25 keeps `dev` fast). The gate is the authority; the agent
looks for what the gate cannot see and for defects in the gate itself —
[`D-wide-team.md`](D-wide-team.md) › "Gate or agent".

⚠️ `data` is **outside this rule and the opposite applies**: work that touches the
schema passes through `data` BEFORE it is merged to `dev`. A migration cannot be undone.

⚠️ **`qa` is never skipped.** If code **or infrastructure configuration** changed,
there is a review. Infrastructure = CI workflows, deploy/gate scripts, backup scripts,
Dockerfiles, IIS/nginx configuration, environment file schemas, cron. "The diff is
config, not code" is **not** a reason to skip — `devops` output goes into `qa` too. If
it is going to be skipped, the reason is told to the user; it is never passed over
silently.

⚠️ Reason: `devops` was the one risky role with no audit; it touches the CI gate, the
backups and the deploy configuration. Where the audit has been removed, a second pair
of eyes is essential.

#### ⚠️ The intersection with #25 — which one wins

Global #25 removes review (both by hand **and** by agent) in the `feature/* → dev`
direction; the "`qa` is never skipped" rule here wants a review. The conflict is real.
**Precedence: #25 wins** (§4 precedence 2 — an explicit user decision):

- **The `dev` direction:** `qa` is **not called**. If I spot a finding I do not block
  the merge, I leave a note; the fix is handled before the `test` promotion (#25's own
  rule).
- **The `test`/`prod` promotion:** `qa` is **not skipped**, and infrastructure diffs
  are in scope.
- **The single exception** (§4 precedence 1 — security and data loss always win): if
  the change weakens **backups, secret management or the security gate itself**
  (`continue-on-error`, disabling a gate, switching off gitleaks, breaking
  backup/restore), then `qa` runs in the `dev` direction too and the reason is written
  down. Because #25 buys speed, not irreversible loss — #25 leaves the pre-commit
  gitleaks hook enabled for exactly this reason.

## §4 — Conflict

If two roles contradict each other **I arbitrate** and write down the reasoning. The
order of precedence:

1. **Security / backward compatibility / data loss** — always wins.
2. **An explicit user decision** — if they said "do it this way", a design preference
   is not debated.
3. **The repository's existing pattern** — beats a general "best practice".
4. The rest is my call, with its reasoning.

⚠️ A conflict I cannot arbitrate **goes to the user** — I do not present my own
preference as "the agents said so".

## §5 — Stopping

The chain stops and I come back to the user in these cases:

- **The scope changed** — the work is turning into something other than what was asked.
- **An irreversible action** — deploy, `DROP`, force push, sending anything outward.
  The mode **never** loosens this.
- **An unresolvable conflict between agents** (§4).
- **The stop tier of a cost threshold was reached** (§8) — the warning tier does not
  stop, the stop tier does.
- **The mode exceeded its own turn ceiling** — 4 agent turns in B.
- **A completeness check did not close** — the `Result` line of the §7 block is still
  "YES", or `Not covered` contains "not verified", **and** the work has been sent back
  twice (3 passes) without reaching a clean result.
  A single finding is **not a stop reason**: it is sent back and fixed (§7), not
  escalated. Continuing with uncertainty means carrying that uncertainty downstream.

## §6 — Visibility and cost (mandatory)

- **At the start of the turn:** which roles, in what order, and which were **skipped
  and why**.
- **At every handoff** (as one role ends and the next begins): a one-line cost
  reminder — that role's estimated cost + the turn's running total + the distance to
  the threshold:

      ↳ analyst done · completeness check ✅ clean · ~$3 · turn total ~$9 (2 agents) · threshold ~$150 (C)

- **At the end of the turn:** how many agents ran + the total estimated cost + where
  that stands against the threshold.

Modes C/D are not run without these lines — because the approval is given up front,
visibility is the only audit mechanism left.

⚠️ **The cost reminder is never deferred.** A figure totalled only at the end of the
turn arrives too late to make a "let's not continue" decision. It is visible at every
handoff; the source of the figures and the thresholds are in §8.

## §7 — The completeness check: the auditor **does not ask; it checks, sends back, and GETS IT FIXED**

The auditor's subject is not only what is **missing** but also what is **wrong**:
incorrect behaviour, a wrong assumption, a rule written in the wrong place, wrong
evidence. Both follow the same path — found, sent back, **fixed**, closure verified.

**Every role** whose output another role or the user will rely on — `qa`, `analyst`,
`devops`, `test-writer`, `product-manager`, and in modes D/E additionally `security`,
`data`, `coverage-auditor`, `e2e-writer`, `observability` — closes its report with this
**evidence block**:

```
## Completeness check — pass N
- Verification   → command run / line range read + raw result
- Item mapping   → each requested item → where it is (file:line)
- Not covered    → what could not be verified + what was deliberately left out
→ Result: clean NO  |  YES → BACK TO: <who> · <what to fix> · <closing evidence>
```

The block is machine-checkable: `python3 scripts/evidence-check.py <report>` validates it
against `scripts/evidence-block.schema.json`, and a report with no block fails.

### The orchestrator: one line per handoff, the full block at the END of the turn

The orchestrator does **not** write the full block at every handoff — the role's own
block already carries the evidence, and a second copy repeats it. The orchestrator's
obligations:

- **One line per handoff** (the same line as the cost line in §6):
  `↳ analyst done · ✅ clean (grep -rn X → 3) · ~$3 · turn total ~$9 · threshold ~$150 (C)`
  — "clean" **cannot be written without evidence**: the line carries the verification
  that passed the handoff.
- **The full block in two cases:** (a) **once at the end of the turn** — item mapping
  + not covered for the whole turn; (b) **on every "YES" decision** — the hand-back
  must carry what, with which evidence, and to whom it returns.
- The role's own block is **never swallowed**: it passes to the user as-is, alongside
  the handoff line (see "Other rules" below).

In a 14-role turn like D/E this reduces 14 orchestrator blocks to one; the role's block
and the "YES" decisions stand as they are — so no evidence is lost and nothing is
duplicated.

⚠️ **This is a check, not a list of questions.** The auditor does not ask "is anything
missing?" — not the user, not the producing role. It looks, writes the evidence, and
decides. Handing it over as "does this look right to you?" is not auditing, it is
returning responsibility.

### When something is missing: THE HAND-BACK

The work **does not move forward**, it returns to its producer. The hand-back contains:
**what is missing · with what evidence · what to do.** When the fix arrives, the check
starts **from the beginning** and the counter resets.

| Auditor | Where it sends the work when it finds a gap |
|---|---|
| `qa` | To the producer — `developer` or me → fix → **`qa` again** |
| `analyst` | To itself: it does not hand off, it completes its scan |
| `test-writer` | To itself; if what is missing is product-code behaviour, **to me** |
| `devops` | To itself; it writes "not verified" for a gate that did not run, it **does not say green** |
| `product-manager` | To itself; it writes the ambiguity as an **assumption**, it leaves no question |
| the orchestrator (me) | To the relevant role; to myself if I produced it |

**When does it reach the user?** Only for the stop reasons in §5 and at the ceiling
below — and even then as a **status report, not a question**: "not closed · this is
missing · these were tried".

### Getting it fixed: **no handoff while a finding is open**

A hand-back is not a note, it is **an order**. The auditor is obliged to get the gap or
error fixed; writing a finding into a report and moving on **does not count as closure**.

1. **The auditor does not fix, it gets it fixed.** `qa` still "finds, does not fix" —
   but it **tracks the fix and verifies its closure**. The fixing party is the producer
   (`developer` / me); `analyst` and `product-manager` fix their own output themselves.
2. **Closure happens with evidence.** After the fix arrives, **the same verification
   that surfaced the finding is re-run** and its result written down. A claim of
   "fixed" is not closure on its own.
3. **It does not close with "we'll look at it later".** A finding closes in one of
   three ways only: **(a)** fixed + evidenced · **(b)** the user explicitly said
   "don't" · **(c)** **reported to the user** as out of scope and listed in the report
   as an open finding. No finding is ever dropped silently.
4. **Cosmetic findings do not get lost either.** They do not block a handoff (they are
   not serious) but they are either fixed in the same turn or reported as an "open
   finding".
5. **The open-findings list is carried through the turn.** The end-of-turn report shows
   "closed / still open" — the same line as the completeness check in global #24.

### How many passes? — **1 clean**

**One** "no serious gap" is enough for a handoff (`✅ clean`).

**What is a "serious gap"?** Anything that changes behaviour, affects
security/backward compatibility/data, or **leaves a requested item unmet**. Cosmetic
notes and things deliberately left out of scope are not serious gaps — they are listed
in the report and do not block the handoff.

⚠️ **A single pass makes the evidence block even more binding.** With no second pass,
that block is the only safeguard: an unevidenced "clean" is caught nowhere. That is why
the `Verification` line **must** carry the command run or the range read, and why
**what cannot be verified does not count as fine** (see "Other rules" below).

**What does not change:**

- **On "YES" the work is sent back** — it returns to its producer, it is not escalated
  to the user (§7 opening).
- **When the fix arrives, the verification that surfaced the finding is re-run.** This
  is not a "second pass", it is **closing evidence**: a claim of "fixed" is not closure.
- **Ceiling: the same work is sent back at most twice (3 passes).** Then the chain stops
  and the user is **informed** — a status report, not a question. Unclosed findings are
  listed individually as **open findings**; saying "I tried, it didn't work" and handing
  off silently is forbidden.

<details>
<summary><b>Option: two consecutive clean passes (2/2)</b> — disabled</summary>

If the user asks for "two looks", a handoff requires two consecutive clean results. In
that case pass 2 cannot be a repeat of the same check: it uses **at least one
independent evidence source** not used in pass 1 (a different command, reading from the
other end of the code, or mapping the original request item by item) and it does not
exceed **half** the tool-call count of pass 1, within the same turn (+10–20% overhead).
An unevidenced "clean" turns 2/2 into a ceremony. The ceiling then becomes 2 hand-backs
= 4 passes.

The measured reason this option is disabled: in a 14-role turn the second pass was
roughly **22% of the estimated cost**.
</details>

### Other rules

- The block is written **every time**; it is visible even on a clean pass. An invisible
  check is an unperformed check.
- The answer **carries evidence, not a template.** "Yes, I'm sure" is invalid on its
  own; "verified with `grep -rn X` across 3 files, the 4th match is in a test file" is
  valid.
- **What cannot be verified does not count as fine.** If it cannot be verified, either
  a way to verify it is found or it is reported as "not verified" — a guess does not
  substitute for a clean pass.
- ⚠️ The orchestrator does **not swallow** this block. The agent's completeness check
  and its hand-back decision pass to the user as-is, alongside the handoff line.

### Addition for `analyst`: the result must be verifiable

`analyst` returns not only the result but **the command that produced it**
(`grep -rn "X" --include=*.cs`, `rg -c`, `find`). The orchestrator re-runs the command
in a second and compares the count.

⚠️ Reason: `analyst` reads a lot and returns little; when it says "used in 3 places"
and misses the 4th, the only way to verify that is to redo the whole scan — which
destroys the reason for using the agent. Returning the command delivers most of a full
audit at **near-zero cost**. If the command is not returned, the finding counts as
"not verified".

## §8 — Cost: the figures and the threshold

**Measured** (33 sessions): an average of **$6.9** per agent turn; **73%** of the
total cost comes from the orchestrator's cache reads, not from the agents. Agent turns
were 7.7% of the total.

| Role | Model | Estimate per turn |
|---|---|---|
| `doc-writer` | haiku | ~$0.5–2 |
| `analyst` · `designer` · `product-manager` · `test-writer` · `devops` | sonnet | ~$2–6 |
| `qa` | opus | **~$4** (MEASURED — 3 records; avg. $4.10) |
| `architect` · `developer` | opus | ~$8–20 (NOT MEASURED — writing roles, expected to cost more than `qa`) |
| `coverage-auditor` · `e2e-writer` · `observability` | sonnet | ~$2–6 (NOT MEASURED — mode D) |
| `security` · `data` | opus | ~$4–10 (NOT MEASURED — auditors of the `qa` class) |
| `Workflow` (mode E) | mixed | agent count × the above + an orchestration share |

⚠️ **Two** numbers here are measured: the ~$6.9 per-turn average across 33 sessions,
and the `qa` row at ~$4.10/turn from 3 records (the calibration below). Everything
else — the per-model breakdown — is an **estimate** derived from price ratios and is
presented as such. If the real bill differs, the table is corrected; the estimate is
not defended.

### Calibration: the table is corrected BY MEASUREMENT

The table is an estimate today; **a measurement is recorded on every real agent turn**
and the table is corrected once enough data accumulates. The method:

1. After the turn, read **`subagent_tokens`** from the task notification.
2. **The preferred route:** `python3 ~/.claude/measurement/session-cost.py <session-id>` —
   it sums the `usage` fields in the transcript, i.e. it **measures**.
   If only `subagent_tokens` is available, multiply by the model's per-MTok price; the
   current list is in the bundled `claude-api` skill.
3. The notification carries no input/output breakdown, so a **lower and upper bound**
   is written (all input ↔ all output). The real value is near the lower bound: agent
   turns are read-heavy.
4. The result is added to the ledger below. **The table is never changed on a single
   measurement** — it takes at least 3 records or one real end-to-end C/D feature turn;
   generalising from a single narrow run is the very mistake we are trying to correct.

#### The measurement ledger

Work descriptions are kept generic on purpose; the figures are what matters.

| Role / model | Work | Raw measurement | Cost range |
|---|---|---|---|
| `qa` / opus | audit of 17 markdown rule files against 10 decisions (20 tool calls, 355 s) | 85,682 tokens | **$0.43 – $2.14** |
| `qa` / opus | audit of four mode definitions (28 calls, 633 s) | 105,118 tokens | **$0.53 – $2.63** |
| `qa` / opus | audit of three team-mode definitions (57 calls, 872 s) | 137,942 tokens | **$0.69 – $3.45** |
| **session total** (measured by script) | 3 `qa` turns + the orchestrator, 170 messages | — | **main $26.99 + subagent $12.31 = $39.30** |
| `test-writer` / sonnet | behaviour tests for a shell loop, 6 scenarios + 3 mutations (28 calls, 308 s) | 99,994 tokens | **$0.20 – $1.00** |
| `qa` / opus | review of two merge-gate fixes — 3 critical findings (18 calls, 444 s) | 114,795 tokens | **$0.57 – $2.87** |
| `test-writer` / sonnet | runner behaviour tests with fakes + locks, 9 mutations (69 calls, 984 s) | 193,779 tokens | **$0.39 – $1.94** |
| `analyst` / sonnet | classification of 7 failing e2e tests (regression/stale spec) with git history (98 calls, 1222 s) | 175,657 tokens | **$0.35 – $1.76** |
| `qa` / opus | second pass on the gate fixes — closing evidence for 7 findings, 6 minor findings (29 calls, 657 s) | 109,862 tokens | **$0.55 – $2.75** |
| `test-writer` / sonnet | rewriting stale e2e specs, real run against the test environment (75 calls, 907 s) | 146,706 tokens | **$0.29 – $1.47** |
| `test-writer` / sonnet | 3 locks + mutation for minor `qa` findings (43 calls, 435 s) | 91,468 tokens | **$0.18 – $0.91** |
| `developer` / opus | Android feature parity with web — 18 files, build + 59 tests (73 calls, 1225 s) | 286,217 tokens | **$1.43 – $7.16** |
| `developer` / opus | iOS feature parity with web — 21 files, project generation, 92 tests (76 calls, 1198 s) | 263,389 tokens | **$1.32 – $6.58** |
| `developer` / opus | Android hand-back fix (continuation turn) (10 calls, 102 s) | ~10,600 tokens (delta) | **$0.05 – $0.27** |
| `developer` / opus | iOS hand-back fix (continuation turn) (11 calls, 154 s) | ~13,200 tokens (delta) | **$0.07 – $0.33** |
| `test-writer` / sonnet | Android JVM tests, 62 tests + 4 mutations (59 calls, 561 s) | 185,031 tokens | **$0.37 – $1.85** |
| `test-writer` / sonnet | iOS screen + rule tests, 34 tests + 5 mutations (104 calls, 1869 s) | 358,542 tokens | **$0.72 – $3.59** |
| `qa` / opus | pre-`dev` review of 4 commits, pass 1 — 3 high findings (26 calls, 216 s) | 104,366 tokens | **$0.52 – $2.61** |
| `qa` / opus | pass 2, closing the fixes + one new high finding (continuation turn) (7 calls, 124 s) | ~34,700 tokens (delta) | **$0.17 – $0.87** |
| `qa` / opus | pass 3, clean (continuation turn) (2 calls, 49 s) | ~9,000 tokens (delta) | **$0.04 – $0.22** |
| `qa` / opus | pass 4, request→code mapping, clean (continuation turn) (3 calls, 106 s) | ~5,600 tokens (delta) | **$0.03 – $0.14** |

✅ **Calibration 1 is done:** 3 records accumulated and a script-measured session total
was obtained — **subagent $12.31** for 3 `qa`/opus turns, i.e. **~$4.10** per turn. The
`~$8–20` estimate in the table was **2-5x too high**; the `qa` row was replaced with
the measurement.

⚠️ **Still unmeasured:** `architect`/`developer` (the writing roles — all three
calibration records were auditing turns), the sonnet and haiku roles, and **all of
X/Y/Z**. The thresholds were not changed: all three records came from the same kind of
work (auditing rule files) and there is still no real end-to-end feature turn. That is
what a threshold correction would require.

⚠️ The orchestrator's share confirms the measurement: in the same session, **main
$26.99** vs **subagent $12.31** — most of the cost is still not in the agents, it is in me.

### The threshold: **mode-dependent, two-stage**

| Mode | Warning (half) | **Stop** |
|---|---|---|
| **A** | — (no agents) | — |
| **B** | ~$12 | **~$25** |
| **C** | ~$75 | **~$150** |
| **D** | ~$130 | **~$260** |
| **E** | ~$200 | **~$400** |
| **X** (archived) | ~$25 | **~$50** |
| **Y** (archived) | ~$150 | **~$300** |
| **Z** (archived) | ~$300 | **~$600** |

⚠️ D read ~$150/$300 here while `CLAUDE.md` #28, `modes/README.md` and
`D-wide-team.md` all said ~$130/$260, and **E was missing from the table
entirely** while three archived modes had rows. The active figures are the ones
in #28; this table follows them rather than the other way round.

- **The warning tier:** one word is added to the handoff line (`⚠ half the threshold`)
  and the work **does not stop**. The point is to remove the surprise: you see it
  before hitting the ceiling.
- **The stop tier:** the chain stops, what has been spent and what remains are written
  down, and the decision to continue belongs to the user.
- ⚠️ A threshold **must be consistent with the cost the mode itself declares.** A
  single flat value set at a quarter of C's own expectation (+$100–150) would fire in
  the **middle** of a normal C feature — which means either an unnecessary question on
  every task or a dead rule. A brake fires in abnormal conditions, not in normal ones.
- The autonomous run's own **$100** ceiling applies **independently** of this
  (`autonomous-run.md`), and whichever fills first is the one that stops.
- The thresholds can be changed by the user.
