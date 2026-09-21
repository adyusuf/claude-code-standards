# claude-code-standards

**AI changed our lives — at least the lives of those of us who write software.**

The coding world will not be what it was. But the real question is not whether
the tools got better. It is this: in a world this vast, **how do we get the most
out of it without losing our way in it?**

My answer turned out to be boring, and it is this repository. Not a prompt
collection and not a framework — a rule set, a gate, and an audit protocol that
together do the things I always knew I should do and mostly could not:

- **Apply the SDLC / SSDLC practices we could never really do by hand.** A real
  coverage threshold per codebase. A secret scan on every push. Schema changes
  that stay backward compatible. A setup document a stranger can follow. An e2e
  suite before production. Not once a quarter — on every change.
- **Enforce them when a rule is not enough.** Some of it cannot be left to good
  intentions, so it is a gate with an exit code.
- **Keep the cost as low as it can be.** Agent teams get expensive fast, and
  most of the spend is not where it looks like it is.
- **Still scale to agent teams when I want them.** One file in the project
  switches between no agents and fourteen roles.
- **Run fast, and repeat as little as possible.** The heavy checks belong where
  code leaves for the outside world, not on every commit.
- **Shape the flows around SDLC roles** — analyst, architect, developer, qa,
  devops, security, data, e2e — rather than one agent doing everything.
- **Not let the role agents get away with mistakes.** The auditors assume the
  agents will be wrong, and assume the person supervising them will be too.

**Agentic coding, not just an AI coding tool** — that was a choice, and here is
the reasoning: a tool that answers questions cannot run a gate, and rules nobody
executes are documentation. The discipline only becomes real when something
*acts* on it per change. That said, the lowest mode (`A`) uses no agents at all,
so a plain coding assistant gets the same rules and the same gate; the agents
are how it scales, not how it works.

There is one thing behind all of it. An agent will happily apply every practice
on that list. **An agent will just as happily tell you that it did.** Everything
here is built for that gap: rules loaded before the work starts, gates that fail
loudly when a step did not run, and reports that are not accepted without
evidence.

**This is my live configuration, running as-is.** It is not a sample, a
write-up, or a tidied copy of something I keep privately: `~/.claude` symlinks
straight into this repository, so every session I open — across nine
repositories, .NET and TypeScript, web and mobile — loads exactly the files you
are reading. When a rule here is wrong, it is wrong in my own working day first.
That is also why it changes so often: `prod` is the live branch, work happens on
`dev`, and promoting between them is a decision I have to make about my own
tooling.

## Who this is for

- You build production software with an AI coding agent, and "it looks fine"
  is not a standard you can ship on.
- You want SDLC / SSDLC practice applied per change, not per quarter.
- You have felt the agent-team bill and want the discipline without it.
- You want the flows shaped by **SDLC roles** — analyst, architect, developer,
  qa, devops, security, data, e2e — rather than one agent doing everything.

Not for you if you want a prompt pack. There are no clever prompts here. There
are rules, gates, measurements, and the record of what each one cost.

## How each of those is actually done

The list above is the promise. This is the mechanism, in the same order.

**1. The practices become rules, not intentions.** 33 invariant rules load into
every session; 22 standards documents carry the detail. The agent does not get
to decide whether backward compatibility matters this time.

**2. Where a rule is not enough, a gate has an exit code.** A shared gate
(`scripts/gate-core.sh`) runs the same step set in every repository: formatter,
typecheck, build, unit tests, **coverage per codebase**, secret scan,
dependency CVE, SAST, backward-compatibility scan, guidance-file budget, and a
missing-e2e-spec check. One step cannot be waived at all — coverage — because a
threshold with an exception is a suggestion.

**3. The cost is cut where the measurement says it is, not where it feels like
it is.** A subagent's tokens run roughly **4x** an orchestrator turn, and the
fixed prompt prefix is re-read on every single request — across the records here
that is **~11.1 billion tokens**. So the default mode uses almost no agents, the
expensive modes are opt-in, and the audit protocol buys its rigour from the
*shape of the output* rather than from another agent: a role returns the
**command that produced its finding**, and re-running that command costs about
nothing.

**4. Scales up to agent teams when you want them.** Five operating modes, A to
E: no agents, three agents, nine roles, fourteen roles, fan-out. The mode is one
file in the project; choosing it *is* the approval, so there is no per-call
friction. Nothing else in the rule set changes with the mode.

The roles are **subagents**, not personas in a prompt. Each one is spawned by
the orchestrator with its own context window, its own tool allow-list and **its
own model** — and that is exactly why the bill behaves the way it does: a
subagent starts by reading the whole fixed prefix again, which is what makes its
tokens run about **4x** an orchestrator turn. So the model is assigned per role
by what the role actually has to do, not uniformly:

| Role | Model | Why that tier | Tools it may use |
|---|---|---|---|
| `architect` | opus | designs a change across many files; a wrong plan costs more than the model does | read-only + shell |
| `developer` | opus | writes product code against a fixed contract | read/write + shell |
| `qa` | opus | the first review pass — correctness, security, backward compatibility | read-only + shell |
| `security` | opus | OWASP, secret leakage, authorization, gate integrity | read-only + shell |
| `data` | opus | schema, migrations, data loss risk — the least reversible work there is | read-only + shell |
| `analyst` | sonnet | reads a lot, returns little; must also return the command that produced the finding | read-only + shell |
| `test-writer` | sonnet | tests for a stated behaviour, scope already decided | read/write + shell |
| `e2e-writer` | sonnet | Playwright/Maestro specs against the test environment only | read/write + shell |
| `devops` | sonnet | CI, deploy, gate and backup configuration — its output still goes through `qa` | read/write + shell |
| `coverage-auditor` | sonnet | measures the per-codebase threshold; writes no tests | read-only + shell |
| `observability` | sonnet | logging, metrics, tracing, alerting gaps | read-only + shell |
| `designer` | sonnet | flow, states, accessibility, empty and error states | read-only |
| `product-manager` | sonnet | scope and acceptance criteria; output goes to human approval | read-only |
| `doc-writer` | haiku | writes a decided rule into the right file | read/write, no shell |

⚠️ **The orchestrator has no `model:` field** — it is whatever `/model` selected
for the session, and it is the most expensive seat at the table, because its
context is re-read on every single request. Across the records in this
repository that is where the money went: **73%** of total spend was orchestrator
cache reads and **7.7%** was agent turns. Choosing cheaper agents while leaving
the orchestrator unexamined optimises the small half.

Every model here is a Claude model on purpose, and the reason is written down
rather than assumed: a subagent's `model:` field only accepts Anthropic models,
so a third-party comparison would answer a question this system cannot act on.

**5. Speed comes from where the checks sit, not from skipping them.** Merging to `dev` is
deliberately fast — build and unit tests only. The heavy gates run where code
leaves for the outside world. The formatter runs once at the end of a task list,
not per commit. E2E belongs to the pre-production gate alone, not to every
branch.

**6. The auditors assume the agents are wrong.** Every role whose output someone relies on
closes its report with an evidence block: the command it ran, each requested
item mapped to `file:line`, and what it could not verify. A report with no
evidence is not accepted. **What cannot be verified does not count as fine.** If
something is missing, the work goes *back* to the producer — it is not escalated
to the human as a question.

```mermaid
flowchart LR
    R["Rules<br/>33 invariants + 22 standards"] --> G["Gates<br/>one shared step set<br/>per promotion"]
    G --> A["Audit<br/>evidence block<br/>at every handoff"]
    A --> M["Measurement<br/>ledger + decision log"]
    M -->|"a rule that cost more<br/>than it returned is retired"| R
```

---

## What is in here

The live configuration, not a showcase written for display — most rules exist
because something broke first.

| What | Where | Count |
|---|---|---|
| Working rules (index loaded every session) | `CLAUDE.md` | 33 rules |
| Engineering standards | `standards/` | 22 documents + 6 templates |
| Agent roles (each with explicit scope and prohibitions) | `agents/` | 14 roles |
| Operating modes (agent use + review + approval policy) | `modes/` | 5 modes |
| Gate and measurement scripts | `scripts/` | 20 scripts + 292 tests |
| Slash commands and skills | `commands/`, `skills/` | 5 |
| Decision log (rationale and measurement per rule) | `docs/` | — |

```mermaid
pie showData title Repository composition (files)
 "standards/ (22 docs + 6 templates)" : 29
 "agents/ (14 roles)" : 14
 "modes/ (5 modes + selection guide)" : 13
 "scripts/ (gates, hooks, measurement, tests)" : 36
 "docs/ (decision log + case studies + method)" : 9
 "commands/ + skills/" : 5
 "root (CLAUDE.md, settings, license)" : 5
```

## Why it is measurement-driven

There are numbers behind these rules, not opinions. The decision log records how
each rule was discovered, which measurement produced it, and the text of rules
that have since been retired.

**Test coverage: what was reported vs. what was true**

| | | |
|---|---|---|
| Reported (raw) | `████████████████████` | **95.0%** |
| Honest (generated code excluded) | `█████████████████░░░` | **83.0%** |
| Same project, web codebase | `███░░░░░░░░░░░░░░░░░` | **~14%** |

EF Core migrations made up **85% of the denominator**. A single averaged number
hid the fact that 107 of 136 web files had no test touching them at all.

**Where the cost actually was**

| | | |
|---|---|---|
| Orchestrator cache reads | `███████████████░░░░░` | **73%** of total |
| Agent turns | `██░░░░░░░░░░░░░░░░░░` | **7.7%** of total |

Every agent call required approval, and the stated reason was cost. The
measurement showed the approval friction was guarding 7.7% of the bill while
slowing down every turn.

**Estimate vs. measurement for one agent role (`qa`, opus)**

| | | |
|---|---|---|
| Estimated (before) | `████████████████████` | $8 – $20 / turn |
| Measured (3 records, script) | `████░░░░░░░░░░░░░░░░` | **$4.10** / turn |

The estimate was 2–5x too high. The table was corrected; the estimate was not
defended.

## What it changed: before and after

One working day, nine repositories, one shared gate. Every number below was read
from the run that produced it — each codebase measured separately, never
averaged (#29).

**Coverage: from "accepted as a gap" to a number**

Five repositories listed `coverage` in their gate's accepted-gaps line. Their
gates printed GREEN while **nothing measured coverage at all**.

| | | |
|---|---|---|
| Codebases with a measured number, before | `░░░░░░░░░░░░░░░░░░░░` | **4** |
| After | `████████████████████` | **20** |
| Of those, at or above the 80% threshold | `█████████░░░░░░░░░░░` | **9** |

**The rule-#16 setup document (fail-closed)**

The gate's document step only fired when a stack sat at the repository root, so
it looked at three repositories and failed all three. Fixing the detection made
it look at nine.

| | | |
|---|---|---|
| Repositories the step examined, before | `██████░░░░░░░░░░░░░░` | **3 of 9** |
| Passing, before | `░░░░░░░░░░░░░░░░░░░░` | **0 of 3** |
| Examined, after | `████████████████████` | **9 of 9** |
| Passing, after | `████████████████████` | **9 of 9** |

**One web codebase, taken over the line**

| | | |
|---|---|---|
| Before — 141 tests | `██████████████░░░░░░` | **57.2%** |
| After — 221 tests | `████████████████████` | **81.4%** |

Eighty tests, and not one of them written for the percentage: a cancelled prompt
must not be read as a quota of zero, a failed delete must not navigate away as
if it had succeeded, a missing invitation token must render no form at all. The
repository's other codebase was already at 87.7%, so **both** are now above the
threshold and coverage stopped being its promotion blocker.

**Security findings, cleared**

| | | |
|---|---|---|
| High/critical dependency advisories | `████████████████████` **26** &rarr; `░░░░░░░░░░░░░░░░░░░░` **0** | four repositories |
| Secret-scan findings, read | `████████████████████` **17** | across two repositories |
| Of those, actual credentials | `░░░░░░░░░░░░░░░░░░░░` **0** | expired tokens, a model id, an interface name, a placeholder that says "enter a secret here" |

The scans had been failing for a while and nobody had read them. Reading them
mattered more than fixing them: a wrong escalation ("rotate the payment key")
was corrected by looking at the value the rule actually matched.

**Four bugs in the gate itself**

The gate is the thing that is supposed to catch everything else, so its own
defects are the most expensive kind. All four were found by reading failures
instead of trusting them, all four are covered by a test that fails without its
fix, and all four were propagated to nine repositories.

| Bug | What it did |
|---|---|
| `.slnx` and nested `.csproj` invisible | **Skipped an entire .NET backend** — 673 tests, a red build, two high-severity advisories — and printed GATE GREEN |
| `coverage` waivable via accepted gaps | Turned rule #29's "no exceptions" into a suggestion in five repositories |
| jest handed vitest's `--run` | Reported a passing suite of 10 tests as failing |
| Node detected only at the root | Skipped the setup-document check in any repository whose JS lives one level down |

⚠️ The first one is the one to remember. A gate that fails is annoying; a gate
that reports success for work it never looked at is worse than no gate, because
it ends an argument that should have continued.

**What turned out not to be broken**

Three failures that looked like product bugs were not: a frontend build and its
812 tests failing on an incomplete `node_modules`; a mobile tier reporting 0%
coverage because all 57 suites died on a missing module and no test ran at all;
an API-contract check failing without the environment variable its own
documentation prescribes. Each coverage script now checks its install first and names which
problem it is, because an environment problem that reads as a coverage problem
sends the next person hunting in the wrong file.

```mermaid
flowchart TD
    subgraph before["Before"]
        B1["5 repos: coverage accepted as a gap<br/>nothing measured"]
        B2["3 of 9 repos: setup document checked"]
        B3["4 latent gate bugs<br/>one skipped a whole tier"]
        B4["26 high/critical advisories"]
        B5["17 secret findings, unread"]
    end
    subgraph after["After"]
        A1["20 codebases measured<br/>9 over the threshold"]
        A2["9 of 9 repos: checked and passing"]
        A3["4 fixed + 12 tests<br/>propagated to 9 repos"]
        A4["0 high/critical"]
        A5["17 read · 0 credentials<br/>triaged by value, with evidence"]
    end
    B1 --> A1
    B2 --> A2
    B3 --> A3
    B4 --> A4
    B5 --> A5
```

## Case studies

Each one ends with an **Honest limits** section: which numbers were measured,
which are estimates, and what is still open.

- [01 — The coverage illusion: how 95% turned out to be 83%](docs/case-01-coverage-illusion.md)
- [02 — 48 false failures: mistaking an environment limit for a product bug](docs/case-02-false-e2e-failures.md)
- [03 — Saving in the wrong place: measuring what agents actually cost](docs/case-03-agent-cost-measurement.md)
- [04 — Nine roles, one of them audited](docs/case-04-the-audit-gap.md)

## Progress

**Cost-table calibration** — how much of the cost model is measured rather than
estimated. This is the honest state, not a target:

| Role class | Status |
|---|---|
| `qa` (opus, auditing) | `████████████████████` measured — 3 records, ~$4.10/turn |
| Turn average across 33 sessions | `████████████████████` measured — ~$6.9/turn |
| `architect` / `developer` (writing roles) | `░░░░░░░░░░░░░░░░░░░░` estimated only |
| sonnet roles (`analyst`, `test-writer`, `devops`, …) | `░░░░░░░░░░░░░░░░░░░░` estimated only |
| `doc-writer` (haiku) | `░░░░░░░░░░░░░░░░░░░░` estimated only |
| Team modes (X / Y / Z) | `░░░░░░░░░░░░░░░░░░░░` never measured |

Thresholds have deliberately **not** been adjusted on this data: all three
calibration records came from the same kind of work, and a real end-to-end
feature turn has not been measured yet.

```mermaid
flowchart LR
    subgraph P1["Phase 1 · Foundations"]
        A1[Standards extracted<br/>from one project]
        A2[Agent bans and<br/>autonomy limits]
    end
    subgraph P2["Phase 2 · Measurement"]
        B1[Cost measured<br/>across 33 sessions]
        B2[Operating modes<br/>A-E introduced]
        B3[Audit protocol:<br/>evidence blocks]
    end
    subgraph P3["Phase 3 · Gates"]
        C1[Coverage honesty<br/>+ 80% gate]
        C2[E2E run cycle<br/>and classification]
        C3[E2E moved to<br/>the pre-prod gate]
    end
    A1 --> A2 --> B1 --> B2 --> B3 --> C1 --> C2 --> C3
```

## Selected rules

- **Backward compatibility is mandatory** — APIs and databases evolve additively only; fields and endpoints are never deleted, renamed or retyped (#4)
- **Line coverage ≥ 80% per codebase, never averaged** — an unmeasured codebase does not count as passing (#29)
- **Merging to `dev` is fast; heavy gates run on promotion** — the quality gate belongs where code leaves for the outside world (#25)
- **Authorization is fail-closed** — default denied; "I forgot to configure it" must never mean "open to everyone" (#6)
- **Search is always case- and accent-insensitive** — raw `LIKE` / `ToLower.Contains` is banned; one central normalizer (#13)
- **A gate that did not run did not pass** — a skipped step is reported as skipped and the result is not green (#19)
- **A new rule is never left verbal** — a permanent decision is written to the file in the same turn (#14)

## Usage

```bash
git clone https://github.com/<user>/claude-code-standards
cp -r claude-code-standards/{CLAUDE.md,standards,agents,modes,commands,skills,scripts} ~/.claude/
cp claude-code-standards/settings.example.json ~/.claude/settings.json # review it first
```

I run it one step further than copying: `~/.claude/CLAUDE.md`, `standards`,
`agents`, `modes`, `commands`, `scripts` and `docs` are **symlinks into a
checkout of this repository**, pinned to `prod`. Nothing is edited in place —
work happens in a `dev` worktree and reaches the live configuration only by
promotion. The upside is that there is exactly one copy of every rule; the cost
is that a bad promotion changes my tooling mid-session, which is why the
guidance files have their own size and rule-loss gates (`scripts/md-size-gate.sh`,
`scripts/md-rule-gate.py`).

You do not have to take it wholesale — the `standards/` documents read
independently. Rule numbers are linked between `CLAUDE.md` and the decision
log, so keep the numbering if you edit.

To put the gate into a project of your own, copy `scripts/gate-core.sh` beside
your own `scripts/merge-gate.sh` wrapper and run it once in list mode — it
prints the steps it would run without running them:

```bash
bash scripts/gate-core.sh test --list
```

A step it cannot run is reported as **skipped**, and a skipped step means the
result is not green. That is the whole design: you are told what was not
checked, every time.

## Anonymization

These rules were measured on real client projects. Project names are replaced
with **Project A / B / C**; **the measurements are unchanged** — the numbers are
the rationale, the names are not.

## Deliberately NOT in this repository

- Client or project memory, business logic, data schemas, prompts
- Secrets, tokens, connection strings, hostnames, IP addresses
- Session transcripts, conversation history, generated artifacts
- Personal data and real email addresses (placeholders such as
 `<account>+<label>@gmail.com` are used instead)

That split is not arbitrary: the rules governing what must never be published
are part of the set itself, in `standards/15-security.md` (security) and
`standards/18-setup-and-environment.md` (setup and secret inventory).

## Language

English throughout — prose, headings, file names, identifiers, commit messages
and comments. The rule set used to be Turkish and the portfolio documents
English; keeping two languages meant every rule had two possible homes and the
translation drifted. One language, one home.

## License

MIT — see `LICENSE`.
