# claude-code-standards

My live Claude Code configuration, packaged as one plugin, `adyusuf`: 34 rules loaded into every session, the standards
behind them, 14 role agents in 5 modes, a shared gate with an exit code, and the measurements that produced each rule.
It is not a sample: every session I open installs it from this repository's `prod` branch, so when a rule here is
wrong, it is wrong in my own working day first. Why it exists and what it changed: [`docs/README.md`](docs/README.md).

## Install

One standard-library script installs the plugin or updates it. It asks GitHub for the newest commit of `prod`, and
when an older version is installed it asks **"Remove the old one and install the new one? [y/N]"**; your settings and
the marketplace link carry on unchanged. It needs `python3`, `git` and `claude` on `PATH`; read it before you run it.

**macOS / Linux:**

```bash
d=$(mktemp -d) && curl -fsSL https://raw.githubusercontent.com/adyusuf/claude-code-standards/prod/scripts/plugin-setup.py -o "$d/plugin-setup.py" && python3 "$d/plugin-setup.py"
```

**Windows (PowerShell):**

```powershell
$d = New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([guid]::NewGuid()))
Invoke-WebRequest https://raw.githubusercontent.com/adyusuf/claude-code-standards/prod/scripts/plugin-setup.py -OutFile "$d\plugin-setup.py"
python "$d\plugin-setup.py"
```

Or, inside a Claude Code session (the desktop app's **Code** tab too):

```
/plugin marketplace add adyusuf/claude-code-standards#prod
/plugin install adyusuf@adyusuf-marketplace
```

Then open a new session (or `/reload-plugins`). The script's flags (`--check`, `--yes`, `--ref`, `--claude`) and how it
finds `claude` when it is not on `PATH`: [`scripts/README.md`](scripts/README.md) (`plugin-setup.py`). Prerequisites,
Windows included: [`SETUP.md`](SETUP.md) §1 and §6.

## What is in here

| What | Where | Count | Read more |
|---|---|---|---|
| Working rules, loaded into every session | [`CLAUDE.md`](CLAUDE.md) | 34 rules | why each exists: [`docs/decision-log.md`](docs/decision-log.md) |
| Engineering standards | `standards/` | 24 documents + 8 templates | [`standards/README.md`](standards/README.md) |
| Operating modes and the role agents | `modes/`, `agents/` | 5 modes, 14 roles | [`modes/README.md`](modes/README.md) |
| Gate, hook scripts, measurement, install | `scripts/` | 35 scripts, 829 tests | [`scripts/README.md`](scripts/README.md) |
| Hooks and the `adyusuf` pane (`/adyusuf:panels`) | `hooks/` | 77 tests | [`hooks/README.md`](hooks/README.md) |
| Slash commands | `commands/` | `apply-project-standards`, `panels`, `prod-readiness`, `standards-check` | each file |
| Skills | `skills/` | `board-plan`, `config`, `software-standards`, `test-inventory`, `working-mode` | each `SKILL.md` |
| The record: motivation, measurements, case studies | `docs/` | 4 case studies | [`docs/README.md`](docs/README.md) |
| Working on this repository | [`SETUP.md`](SETUP.md) | | |

Everything is invoked as `/adyusuf:<name>`. Counts are of 01/11/2026; `scripts/doc-check.py` fails when the rule, standards,
template, mode, role or script count stops matching the disk.

## If you take only five things

These paste straight into your own `CLAUDE.md`. They are stack-agnostic and depend on nothing else here; every one
exists because work was reported as finished when it was not.

```markdown
1. Report the truth. If tests are red, say so with the output; name any step
   that was skipped. Never report completion on the basis of "it probably
   works".
2. Before saying "done", re-read the ORIGINAL request — not a summarised memory
   of it — and check it item by item. Anything knowingly deferred is listed in
   the final report, never skipped silently.
3. A gate that did not run did not pass. A missing tool is reported as SKIPPED
   and the result is INCOMPLETE, never green. The exit code is the gate.
4. A new rule is never left verbal. The moment a permanent decision is made,
   write it to the rule file in the same turn.
5. Line coverage is measured per codebase and never averaged. Only GENERATED
   code may leave the denominator, and the exclusion list carries a reason per
   entry.
```

Here they are rules #15, #24, #19 + #25, #14 and #29. Why the fifth: one project reported **95.0%** coverage; with
generated migrations out of the denominator it was **83.0%**, and the average hid a web client at **~14%**
([case 01](docs/case-01-coverage-illusion.md)).

## How to use it

Take the smallest amount that is useful; each step works on its own.

1. **Read only:** [`CLAUDE.md`](CLAUDE.md) and [`docs/decision-log.md`](docs/decision-log.md).
2. **Take the five rules** above.
3. **Take the standards for your stack:** the files in `standards/` read independently. Keep the rule numbers if you
   edit; everything cross-references by number.
4. **Install the plugin** (above). `/adyusuf:config` and the `adyusuf` pane set the mode, the models, how much Claude
   writes and what it merges and pushes without asking; resting the pointer on a label explains it. Outside a git
   repository the pane shows only Status and Replies ([`hooks/README.md`](hooks/README.md)).
5. **Put the gate in a project:** [`scripts/README.md`](scripts/README.md#putting-the-gate-in-a-project-of-your-own).

How I run it myself: the installed plugin is a copy of `prod`, never edited in place. Work happens on a `dev` worktree
(tried with `claude --plugin-dir <worktree>`), passes the gate, is promoted to `test` and `prod`, and reaches my sessions
through `plugin-setup.py` ([`standards/00-working-method.md`](standards/00-working-method.md) §7a). ⚠️ A wrong rule
reaches every session once the plugin is updated, which is why the guidance files have their own size and rule-loss
gates (`scripts/md-size-gate.sh`, `scripts/md-rule-gate.py`). Start with the five rules, not here.
`settings.example.json` is my own selection, not a template.

## What it does to your machine

The hooks and the pane run locally, open no network connection and send no telemetry. The gate reaches the network
only for dependency installs and advisory lookups in your own project, and `plugin-setup.py` only to ask GitHub for the
newest commit. Everything it runs, reads and writes: [`hooks/README.md`](hooks/README.md).

## Not in this repository

Client or project memory, business logic, data schemas, secrets, hostnames, session transcripts and personal data.
Project names in the measurements are replaced with *Project A / B / C*; the numbers are unchanged. The rules that keep
it that way are in [`standards/15-security.md`](standards/15-security.md) and
[`standards/18-setup-and-environment.md`](standards/18-setup-and-environment.md). Everything is in English.

## License

MIT — see [`LICENSE`](LICENSE).
