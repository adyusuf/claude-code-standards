# CLAUDE.md maintenance tools (the canonical copy)

Three tools, one family. **Their canonical form lives here**; every project takes
a **copy** into its own `scripts/` directory and commits that copy.

⚠️ Projects never call this directory **directly**. A project's gate cannot depend
on a path outside the repository — that is exactly why `md-rule-gate.py` was once
lost: it sat under a directory that belonged to no git repository, and although
`md-budget.tsv` pointed at it, it existed in no worktree.

| Tool | What it does | How it runs |
|---|---|---|
| `md-size-gate.sh` | Ties every `CLAUDE.md`'s size to a **ratchet**: the ceiling only goes down (`--update`); raising it is manual and needs a reason in the `note` column. A file with no budget is fail-closed red. | **Automatically**, in the project's merge gate |
| `md-rule-gate.py` | Measures **rule loss** in a simplification: ❌ items, lines carrying a prohibition or obligation, backticked identifiers. A dropped identifier requires **justified triage**. | **By hand**, while splitting |
| `audit-triage.py` | Decides whether every HIGH/CRITICAL `npm audit` advisory is covered by a written, unexpired entry in `audit-triage.tsv`; fails closed on anything it cannot trust. | Called by `gate-core.sh` only after `npm audit` failed. |
| `md-split.py` | Splits a decision log into two layers — **moving verbatim, never paraphrasing**. | **By hand**, while splitting |

## Installing into a project

The `/adyusuf:apply-project-standards` command does this. By hand:

```bash
mkdir -p scripts && cp <this repository>/scripts/md-*.sh <this repository>/scripts/md-*.py scripts/
bash scripts/md-size-gate.sh --init     # writes your budget: every CLAUDE.md, ceiling = today's size
```

Then add a `bash scripts/md-size-gate.sh` step to the project's merge gate.

## The right order when splitting

```bash
python3 scripts/md-rule-gate.py <(git show origin/dev:CLAUDE.md) /tmp/new.md
```

If the move was spread across several files, the "new" side is given
**concatenated**: `cat CLAUDE.md docs/decision-log.md > /tmp/new.md`

## ⚠️ Read this before shrinking anything

The header of `md-budget.tsv` records a **measured** result: a `CLAUDE.md` was
once simplified three different ways; one of them **dropped 383 rule lines** and
another **made the file larger**. Measured at sentence level: **61% rule, 9%
history**. These files are usually **dense, not bloated**.

That was later verified independently (only **7%** of the archive section of one
backend file was historical, by byte) — **with one exception:** the measurement
held for *sub* files, **not for the root `CLAUDE.md`**. At the root the problem
was not density but accumulation in a single file, and **moving** content (not
summarising it) gained 74% and passed the rule gate cleanly.

**The decision rule:** in the **root** file, which is loaded in every session and
every agent turn, moving is worth it. In a **sub** file, loaded only in its own
directory, it usually is not — a ratcheted ceiling is enough there.

## Measurement and commit-gate scripts

| File | What it does |
|---|---|
| `pre-commit.sh` | The gate that runs BEFORE the commit: the CLAUDE.md size budget + gitleaks over the staged content. If either is red it **stops** the commit (`md-hook.sh` only warns; its exit code is always 0). Install: `bash scripts/pre-commit.sh --install`; deliberate bypass: `git commit --no-verify`. |
| `step-stats.py` | Generates `docs/measurement-log.md`: the prefix distribution, the before/after comparison per configuration cut, per-role agent runs and cost, and **how many times each SDLC step ran**. Flags: `--write`, `--days N`. |
| `step_stats_sanitiser.py`, `step_stats_transcripts.py`, `step_stats_cells.py` | `step-stats.py`'s parts, split off so no file passes 300 lines (#9): the sanitiser (`shape`, the runtime deny-set, the output scan), the transcript readers (prices, step patterns, per-transcript cost, agent roles) and the printed cells (`role_label`, `cut_delta`). `step-stats.py` loads them from beside itself and re-exports every name, so callers keep reading them from `step-stats.py`. Tests: `python3 -m unittest discover -s scripts/tests -p 'test_step_stats*.py'`. |
| `doc-check.py` | Keeps the documentation from drifting: every relative link resolves, every backticked repo path exists, each index (`standards/`, `docs/`, `modes/`) lists every file beside it, the counts `README.md` states (rules, standards documents, templates, roles) equal what is on disk, and no `#NN` points past the last rule. ~0.1 s. Inside a git repository it reads only Markdown files git does not ignore (a plugin cache or vendored tree is not documentation). Runs as **step 3 of `pre-commit.sh`** when the script is present, except in the live `~/.claude` repository (see `pre-commit.sh` step notes). `python3 scripts/doc-check.py [root]`; tests: `python3 -m unittest scripts/tests/test_doc_check.py`. |
| `measurement-cuts.tsv` | The timestamps of configuration changes (`ISO timestamp<TAB>label`); `step-stats.py` computes the prefix median **before and after** each cut on its own. |
| `coverage.sh` | Line coverage of this repository's own scripts (#29). JavaScript (none here; the live board's page script is measured in claude-monitor) is measured with Node's built-in coverage, and a file no test loads is NOT MEASURED. Python is measured with `coverage` in a venv **outside** the repository (`COVERAGE_VENV`, default `~/.cache/claude-standards/venv`; subprocesses included) against `.coveragerc`, threshold 80% (`COVERAGE_MIN`); shell is measured by `coverage-shell.sh` (kcov; `scripts/*.sh`), and reported NOT MEASURED only when kcov or a traceable bash is missing. Exit 0 all measured and passing · 1 red tests or below threshold · 3 something not measured (blocks like a failure). `gate-core.sh` runs it as its coverage step. Current numbers and the plan: `docs/coverage-gap.md`. |
| `real-name-check.sh`, `commit-msg.sh` | **A real project name must never enter a commit.** `real-name-check.sh --staged` (step 4 of `pre-commit.sh`) checks staged file names and ADDED lines; `commit-msg.sh` (installed as the `commit-msg` hook by `pre-commit.sh --install`) checks the message. Three names reached this repository's history through a script comment, a generated log and three commit messages — places a content scan never looked. The names come from the local, git-ignored `docs/project-nicknames.tsv`: column 1 (the key) and column 3 (comma-separated aliases) are searched case-insensitively; a 4th column `public` marks a name that is not secret. A missing map is a visible warning (`NOT RUN`), not a silent pass (`REAL_NAMES_STRICT=1` makes it a failure). No environment bypass; an exception is the user's (`--no-verify`). Tests: `python3 -m unittest scripts/tests/test_real_name_check.py`. |
| `require-private-remote.sh` | A `pre-push` hook for a repository whose content is only safe while it is PRIVATE (`~/.claude`, which tracks per-project memory under real names). It asks GitHub, authenticated (`gh api repos/<owner>/<repo> --jq .private`), on every push and refuses unless the answer is `true`; **fails closed** (no `gh`, not logged in, offline, or not a github.com remote all refuse). Install: `ln -s <checkout>/scripts/require-private-remote.sh ~/.claude/.git/hooks/pre-push`. Tests: `python3 -m unittest scripts/tests/test_require_private_remote.py`. |
| `onboard.py` | README's Levels 1-2 for someone taking only part of this rule set into `~/.claude`: `describe` prints a ready-to-paste description of this repository, `status` reports what `--home` has (and whether the `adyusuf` plugin is installed), `level1`/`level2 FILE...` copy the five-rule block or chosen standards. `level3` is obsolete — Level 3 is the plugin install now — and only prints the `/plugin` commands. Every subcommand defaults to a **dry run** (`--apply` writes) and never overwrites without `--force` (which backs the old file up first). Tests: `python3 -m unittest scripts/tests/test_onboard.py`. |
| `install.py` | No longer installs the rule set — that is the plugin (`SETUP.md` §6). A plain run (`--prod` default, `--test`, `--dev`) prints the two `/plugin` commands and installs **claude-monitor's agent** for that channel (`--no-monitor` skips it; the agent is optional — a failure is a warning, exit 0). **`--remove`** is the one way off the old link install: it removes every `~/.claude` link into a checkout of this repository (a dangling one with an expected name too — its target may have been your own), strips the legacy hooks through `install-live-hooks.py` and restores your own files from the newest backup; an unreadable `settings.json` stops it with "partially removed" (exit 2) before the monitor and the restore; `--no-monitor` keeps the agent. **`--check`** exits 1 while a legacy link or hook remains or the plugin is missing from `~/.claude/plugins/installed_plugins.json`. Logs to `~/.claude-standards/logs/`. Tests: `python3 -m unittest discover -s scripts/tests -p 'test_install*.py'`. |
| `install_safety.py` | What `install.py` keeps: the run log (`~/.claude-standards/logs/install-<stamp>.log`), the check that Claude Code is installed, `restore_latest` (puts your own files back from the newest backup on `--remove`) and `plugin_installed` (reads `installed_plugins.json`; a missing or unreadable record is "not installed", never a pass). Tests: `python3 -m unittest scripts/tests/test_install_safety.py`. |
| `install_channel.py` | Resolves which checkout is on a channel's branch (`resolve`). It no longer creates worktrees: the rule set's channels are marketplace refs now (`#prod`, `#test`). Tests: `python3 -m unittest scripts/tests/test_install_channel.py`. |
| `install_monitor.py` | `install.py`'s monitor step: holds the ONE table of claude-monitor APIs (prod `https://monitor.bitreka.com`, test `https://testmonitor.bitreka.com`, dev `http://localhost:9872`); clones claude-monitor into `$CLAUDE_MONITOR_HOME` (default `~/ClaudeCode/claude-monitor`), builds `cm-agent` with the .NET 10 SDK (`dotnet publish -r osx-arm64/osx-x64/win-x64/win-arm64`; no release is published yet), runs `cm-agent install` (copies the binary, writes its Claude Code plugin) into the agent's home (`CM_AGENT_HOME`; Windows default `%USERPROFILE%\.claude-monitor`, **not** AppData, which the Claude desktop app redirects; a `cm-agent` installed in the old default `%LOCALAPPDATA%\ClaudeMonitor` is still found, new home first; on Windows it **warns** when run inside the Claude app while a redirected copy of that folder exists), and `cm-agent login --server URL` — a code a person approves on the web, skipped when already connected to that API. **The plugin is ENABLED only while connected** (user decision 04/10/2026): with no server it is registered DISABLED in `settings.json` (`extraKnownMarketplaces` + `enabledPlugins`; no `claude` CLI needed), so none of its 11 hooks or its MCP server runs and nothing is queued — the output says DORMANT. Connecting switches it on without a rebuild; `--monitor-sync` re-derives it after a logout. `--check` reports a MISMATCH between the switch and the connection. Tests: `test_install_monitor.py` (an injected runner: no SDK or network needed). |
| `rules-context.py` | **The global rules for a plugin install:** a plugin cannot ship a `CLAUDE.md` that loads, so the plugin's `hooks/hooks.json` runs this on `SessionStart` (plain text) and `SubagentStart` (JSON `additionalContext`). It cuts `CLAUDE.md` at its `## ` / numbered-rule boundaries into parts that each print under Claude Code's 10,000-character hook cap (the JSON parts are cut smaller, since escaping lengthens them) and prints one part per hook; if the rules ever need more parts than are registered, the last part says so. `CLAUDE.md` stays the single source. `python3 scripts/rules-context.py session\|subagent <part> <registered>`. Tests: `python3 -m unittest scripts/tests/test_rules_context.py`. |
| `install-live-hooks.py` | The hooks ship with the plugin (`hooks/hooks.json`), so this only cleans up after the old install: a plain run prints the `/plugin` commands; **`--remove`** strips the `LEGACY` command strings it, `settings.example.json` or the retired live board once registered (backup of `settings.json` first, foreign entries kept) and the `~/.claude/hooks/guard-destructive.sh` link; **`--check`** exits 1 while any remain. `load_settings`/`save_settings`/`backup` are shared with `install.py` and `install_monitor.py`. Tests: `python3 -m unittest scripts/tests/test_install_live_hooks.py`. |
| `legacy-install-check.py` | A plugin `SessionStart` hook: prints one paragraph while the old link install is still present (links in `~/.claude`, or a `LEGACY` hook in `settings.json`) — the rules, agents and guard then load twice — naming `install.py --remove --no-monitor`. Silent when clean, never blocks a session (exit 0). Tests: `python3 -m unittest scripts/tests/test_legacy_install_check.py`. |
| `guard-destructive.sh` | A `PreToolUse(Bash)` hook that BLOCKS the never-do commands: forced push, push straight to `main`/`prod`, `--no-verify`, `DROP`/`TRUNCATE`, `rm -rf` on `/` `~` `.` `*`. Exit 2; **no env-variable bypass** — the user runs it themselves. A grep prefilter keeps it a few ms on ordinary calls. It matches text, so a commit message that merely *mentions* one of these is blocked too: reword it. A plugin hook (`hooks/hooks.json`, `PreToolUse` Bash); tests: `python3 -m unittest scripts/tests/test_guard_destructive.py`. |
| `evidence-check.py` + `evidence-block.schema.json` | Validates the §7 completeness-check block of a role's report against the schema: evidence in `Verification`, a mapped item, `Not covered`, and a `YES` that carries `BACK TO: <who> · <what> · <closing evidence>`. **A report with no block fails** (unaudited is not clean). Usage: `python3 scripts/evidence-check.py report.md` (or `-` for stdin). Tests: `python3 -m unittest scripts/tests/test_evidence_check.py`. |

⚠️ **Counting traps (found by measurement):** a heredoc **body** is data, not a
command (the body is stripped but everything after it is kept — otherwise the
count halves) · `grep -E "dotnet|codeql"` is not a SAST run, and such mentions are
reported separately in the `dismissed` column rather than counted · a step that
runs from inside another script is invisible: that is **"not seen"**, not "zero".

## gate-core.sh — the shared gate, in two layers

`scripts/gate-core.sh <dev|test|prod>` owns the SHARED STEP SET. A project's own
`scripts/merge-gate.sh` remains the orchestrator — it pulls, merges, pushes and
adds whatever that project needs — and CALLS the core for the shared steps. So the
step definition lives in one place while a project can ADD steps without forking
it. The canonical copy lives here; every project commits a copy, because a
project's gate cannot depend on a path outside its repository (CI runners do not
have the configuration checked out). The drift test in `md-hook.sh` covers it.

`gate-core.sh <target> --list` prints the steps that WOULD run and the command
each resolves to, and runs nothing — use it when rolling the gate into a project.

| Target | What runs |
|---|---|
| `dev`, `test` | **Everything except running e2e:** formatter/linter, typecheck, build, unit tests, coverage (80% per codebase), secret scan, dependency CVE, SAST, backward-compatibility scan, the **project documents check** (`SETUP.md`, `.env.example`, the secret inventory heading — missing ones FAIL, rule #16), the CLAUDE.md size and rule gates, and a CHECK for missing e2e specs — a warning in BOTH directions, never blocking; the gaps are written at the `test → prod` gate (#33 step 2). |
| `prod` | The `test` branch and the test environment are **not checked** (04/10/2026) — the gate warns; `GATE_CHECK_TEST_DEPLOY=1` verifies the deployed SHA through the version endpoint and a mismatch then blocks. **E2E is optional and is not run** — the gate warns "e2e was NOT run" and carries on; `GATE_RUN_E2E=1` runs the suite and a red result then blocks. |

Stacks are auto-detected (.NET solution, `web/`, `mobile/`, `e2e/`, `.maestro/`).
Per-project settings live in `scripts/merge-gate.conf` (sourced if present):
`TEST_VERSION_URL`, `E2E_WEB_CMD`, `E2E_MOBILE_CMD`, `COVERAGE_CMD`, `COVERAGE_MIN`,
`SAST_CMD`, `BACKCOMPAT_CMD`, `SECRET_CMD`, `SKIP_STACKS`. Point them at the scripts
the project already has instead of renaming those scripts.

⚠️ **A step that did not run did not pass.** A missing tool is reported SKIPPED
and the gate exits non-zero with INCOMPLETE — never green. A project may ADD
steps; it may never remove one.

## Adopting these scripts in a new project

Not everything here is meant to be copied, and some copied files must be edited.
`/adyusuf:apply-project-standards` does the document part; this is the script part.

| File | What to do | Note |
|---|---|---|
| `gate-core.sh` | **Copy as is** | Configure it through `scripts/merge-gate.conf`, never by editing the copy. |
| `merge-gate.sh` | **Write your own** | The project's orchestrator: pull, merge, push, and a call to `gate-core.sh`. This repository ships no template for it. |
| `merge-gate.conf` | **Create, values are yours** | The commands, `TEST_VERSION_URL`, `ACCEPTED_GAPS` with a written reason. The values shown in `gate-core.sh`'s header are examples, not defaults to keep. |
| `md-size-gate.sh`, `md-rule-gate.py`, `md-split.py`, `audit-triage.py` | **Copy as is** | `audit-triage.tsv` is yours and starts absent: no file, no waiver. |
| `md-budget.tsv` | **Do not copy — run `md-size-gate.sh --init`** | It writes your own budget: one row per `CLAUDE.md`, ceiling = its size today. A copy of this one carries our ceilings and exclusions, and `--update` only lowers rows that already exist. |
| `pre-commit.sh` | **Copy as is, then `--install` in every clone** | A git hook is per clone; it is not committed. |
| `guard-destructive.sh` | **Copy as is; register it** | In `.claude/settings.json` (shared) with `"$CLAUDE_PROJECT_DIR/scripts/guard-destructive.sh"`, or in your user settings. See `standards/18-setup-and-environment.md` §11. |
| `real-name-check.sh` + `commit-msg.sh` | **Copy as is, if you keep a local nickname map** | Run `pre-commit.sh --install` after copying so the `commit-msg` hook is linked too. Without the map they only warn. |
| `doc-check.py` | **Copy if you want it** | Runs from `pre-commit.sh` when present. Checks that do not apply (no `standards/`, no index) are no-ops. |
| `evidence-check.py` + `evidence-block.schema.json` | **Copy both, only if you run agents (modes C/D/E)** | The script loads the schema from beside itself. |
| `tests/` | **Copy only the tests of the scripts you copied** | |
| `md-hook.sh` | **Do not copy** | A plugin hook (`hooks/hooks.json`, `PostToolUse` Edit/Write and `Stop`); it finds its sibling scripts beside itself. |
| `step-stats.py` (+ its `step_stats_*.py` parts), `measurement-cuts.tsv` | **Do not copy** | They read the transcripts of *all* projects under `~/.claude/projects`; there is one canonical copy, here. The ledger, its per-day reports and the per-session cost tool USED to sit beside them and now live in ~/.claude/measurement/ (outside this repository, and deliberately so: it records per-session token and cost metadata, which a published rule set has no business carrying, and a ledger next to the rules keeps session metadata on disk longer than the platform's own retention). |

Every file marked **copy as is** is drift-checked against the plugin's `scripts/` by `md-hook.sh` (the list is its `TWINS` variable; the configuration repository itself is exempt, since it is the canonical set).

After copying, run `python3 scripts/doc-check.py` and `bash scripts/gate-core.sh dev --list`:
the second prints every step that would run and the command it resolves to, without running any.
