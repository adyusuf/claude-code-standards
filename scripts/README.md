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
| `md-split.py` | Splits a decision log into two layers — **moving verbatim, never paraphrasing**. | **By hand**, while splitting |

## Installing into a project

The `/apply-project-standards` command does this. By hand:

```bash
mkdir -p scripts && cp ~/.claude/scripts/md-*.sh ~/.claude/scripts/md-*.py scripts/
bash scripts/md-size-gate.sh --update   # the ceilings become today's size
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
| `prefix-measure.py` | Lists the **fixed prefix** of sessions (system prompt + tool/skill listings + CLAUDE.md). Sorted by **session start**, not by file timestamp. |
| `step-stats.py` | Generates `docs/measurement-log.md`: the prefix distribution, the before/after comparison per configuration cut, per-role agent runs and cost, and **how many times each SDLC step ran**. Flags: `--write`, `--days N`. |
| `doc-check.py` | Keeps the documentation from drifting: every relative link resolves, every backticked repo path exists, each index (`standards/`, `docs/`, `modes/`) lists every file beside it, the counts `README.md` states (rules, standards documents, templates, roles) equal what is on disk, and no `#NN` points past the last rule. ~0.1 s; runs as **step 3 of `pre-commit.sh`** when the script is present. `python3 scripts/doc-check.py [root]`; tests: `python3 -m unittest scripts/tests/test_doc_check.py`. |
| `measurement-ledger.py` | Generates `docs/measurement-ledger.tsv`: **one row per session or agent run** (UTC start, role, model, the four token counters, list-price USD, the configuration-cut ordinal, the SDLC steps it ran and **how many seconds each took**). Every column is derived from the transcripts — **no hand-filled column**. Rows are **merged by id and never dropped** (Claude Code deletes old transcripts, the ledger keeps them); no project name, path or command is written, and every field must match a strict pattern or the whole write is refused. Flags: `--write`, `--days N` (default 30), `--ledger PATH` (another file, for a trial run); ~35 s for a full 30-day pass. **`--auto [--detach] [--min-interval S]`** is the incremental mode the Stop hook runs: it reads only transcripts modified since the last write, skips when the last write is under S seconds old (default 600), holds a lock, replaces the file atomically, never raises, and with `--detach` returns to the caller at once. It writes the tracked `docs/measurement-ledger.tsv` of the repository the script *really* lives in (a symlink is resolved), so that file shows as modified there until you commit it. Tests: `python3 -m unittest scripts/tests/test_measurement_ledger.py scripts/tests/test_ledger_auto.py`. |
| `measurement-cuts.tsv` | The timestamps of configuration changes (`ISO timestamp<TAB>label`); `step-stats.py` computes the prefix median **before and after** each cut on its own. |
| `coverage.sh` | Line coverage of this repository's own scripts (#29). Python is measured with `coverage` in a venv **outside** the repository (`COVERAGE_VENV`, default `~/.cache/claude-standards/venv`; subprocesses included) against `.coveragerc`, threshold 80% (`COVERAGE_MIN`); shell is reported **NOT MEASURED** on every run. Exit 0 all measured and passing · 1 red tests or below threshold · 3 something not measured (blocks like a failure). `gate-core.sh` runs it as its coverage step. Current numbers and the plan: `docs/coverage-gap.md`. |
| `install-live-hooks.py` | **Activates the live hooks:** symlinks `guard-destructive.sh` and `measurement-ledger.py` into `~/.claude/hooks/` (pointing into the checkout you name with `--repo`, default: the one it lives in) and registers them in `~/.claude/settings.json` — `PreToolUse(Bash)` → the guard, `Stop` → `measurement-ledger.py --auto --detach`. Symlinks live in `hooks/`, not `scripts/`, because `~/.claude/scripts` points into the **prod** worktree and a new file there would collide with the next promotion. `settings.json` is backed up first; running it twice changes nothing; a real file in the way or unparsable JSON aborts untouched. `--check` reports (exit 1 if anything is missing or broken), `--remove` undoes it, and after a promotion `--repo <prod checkout>` re-points the links. Tests: `python3 -m unittest scripts/tests/test_install_live_hooks.py`. |
| `guard-destructive.sh` | A `PreToolUse(Bash)` hook that BLOCKS the never-do commands: forced push, push straight to `main`/`prod`, `--no-verify`, `DROP`/`TRUNCATE`, `rm -rf` on `/` `~` `.` `*`. Exit 2; **no env-variable bypass** — the user runs it themselves. A grep prefilter keeps it a few ms on ordinary calls. It matches text, so a commit message that merely *mentions* one of these is blocked too: reword it. Enabled through `settings.example.json`; tests: `python3 -m unittest scripts/tests/test_guard_destructive.py`. |
| `evidence-check.py` + `evidence-block.schema.json` | Validates the §7 completeness-check block of a role's report against the schema: evidence in `Verification`, a mapped item, `Not covered`, and a `YES` that carries `BACK TO: <who> · <what> · <closing evidence>`. **A report with no block fails** (unaudited is not clean). Usage: `python3 scripts/evidence-check.py report.md` (or `-` for stdin). Tests: `python3 -m unittest scripts/tests/test_evidence_check.py`. |
| `session-cost.py` | Measures what a single session has spent so far, from its transcript, split into main conversation and subagents. |

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
| `dev`, `test` | **Everything except running e2e:** formatter/linter, typecheck, build, unit tests, coverage (80% per codebase), secret scan, dependency CVE, SAST, backward-compatibility scan, the **project documents check** (`SETUP.md`, `.env.example`, the secret inventory heading — missing ones FAIL, rule #16), the CLAUDE.md size and rule gates, and a CHECK for missing e2e specs — a warning on `dev`, blocking on `test`. |
| `prod` | The code must already be **deployed to the test environment** (verified through the version endpoint), then the **whole** e2e suite runs against it. Only a green run allows the promotion. |

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
`/apply-project-standards` does the document part; this is the script part.

| File | What to do | Note |
|---|---|---|
| `gate-core.sh` | **Copy as is** | Configure it through `scripts/merge-gate.conf`, never by editing the copy. |
| `merge-gate.sh` | **Write your own** | The project's orchestrator: pull, merge, push, and a call to `gate-core.sh`. This repository ships no template for it. |
| `merge-gate.conf` | **Create, values are yours** | The commands, `TEST_VERSION_URL`, `ACCEPTED_GAPS` with a written reason. The values shown in `gate-core.sh`'s header are examples, not defaults to keep. |
| `md-size-gate.sh`, `md-rule-gate.py`, `md-split.py` | **Copy as is** | |
| `md-budget.tsv` | **Copy, then `md-size-gate.sh --update`** | The ceilings are this repository's. Yours become your files' size today. |
| `pre-commit.sh` | **Copy as is, then `--install` in every clone** | A git hook is per clone; it is not committed. |
| `guard-destructive.sh` | **Copy as is; register it** | In `.claude/settings.json` (shared) with `"$CLAUDE_PROJECT_DIR/scripts/guard-destructive.sh"`, or in your user settings. See `standards/18-setup-and-environment.md` §11. |
| `doc-check.py` | **Copy if you want it** | Runs from `pre-commit.sh` when present. Checks that do not apply (no `standards/`, no index) are no-ops. |
| `evidence-check.py` + `evidence-block.schema.json` | **Copy both, only if you run agents (modes C/D/E)** | The script loads the schema from beside itself. |
| `tests/` | **Copy only the tests of the scripts you copied** | |
| `md-hook.sh` | **Do not copy** | A user-level hook wired in `~/.claude/settings.json` (`settings.example.json`). |
| `step-stats.py`, `measurement-ledger.py`, `session-cost.py`, `prefix-measure.py`, `measurement-cuts.tsv` | **Do not copy** | They read the transcripts of *all* projects under `~/.claude/projects`; there is one canonical copy, here. |

Every file marked **copy as is** is drift-checked against `~/.claude/scripts/` by `md-hook.sh` (the list is its `TWINS` variable; the configuration repository itself is exempt, since it is the canonical set).

After copying, run `python3 scripts/doc-check.py` and `bash scripts/gate-core.sh dev --list`:
the second prints every step that would run and the command it resolves to, without running any.
