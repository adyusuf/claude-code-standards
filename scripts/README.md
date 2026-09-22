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
| `step-stats.py` | Generates `docs/measurement-log.md`: the prefix distribution, the before/after comparison per configuration cut, per-role agent runs and cost, and **how many times each SDLC step ran**. Flags: `--write`, `--days N`. |
| `doc-check.py` | Keeps the documentation from drifting: every relative link resolves, every backticked repo path exists, each index (`standards/`, `docs/`, `modes/`) lists every file beside it, the counts `README.md` states (rules, standards documents, templates, roles) equal what is on disk, and no `#NN` points past the last rule. ~0.1 s. Inside a git repository it reads only Markdown files git does not ignore (a plugin cache or vendored tree is not documentation). Runs as **step 3 of `pre-commit.sh`** when the script is present, except in the live `~/.claude` repository (see `pre-commit.sh` step notes). `python3 scripts/doc-check.py [root]`; tests: `python3 -m unittest scripts/tests/test_doc_check.py`. |
| `measurement-cuts.tsv` | The timestamps of configuration changes (`ISO timestamp<TAB>label`); `step-stats.py` computes the prefix median **before and after** each cut on its own. |
| `coverage.sh` | Line coverage of this repository's own scripts (#29). Python is measured with `coverage` in a venv **outside** the repository (`COVERAGE_VENV`, default `~/.cache/claude-standards/venv`; subprocesses included) against `.coveragerc`, threshold 80% (`COVERAGE_MIN`); shell is reported **NOT MEASURED** on every run. Exit 0 all measured and passing · 1 red tests or below threshold · 3 something not measured (blocks like a failure). `gate-core.sh` runs it as its coverage step. Current numbers and the plan: `docs/coverage-gap.md`. |
| `real-name-check.sh`, `commit-msg.sh` | **A real project name must never enter a commit.** `real-name-check.sh --staged` (step 4 of `pre-commit.sh`) checks staged file names and ADDED lines; `commit-msg.sh` (installed as the `commit-msg` hook by `pre-commit.sh --install`) checks the message. Three names reached this repository's history through a script comment, a generated log and three commit messages — places a content scan never looked. The names come from the local, git-ignored `docs/project-nicknames.tsv`: column 1 (the key) and column 3 (comma-separated aliases) are searched case-insensitively; a 4th column `public` marks a name that is not secret. A missing map is a visible warning (`NOT RUN`), not a silent pass (`REAL_NAMES_STRICT=1` makes it a failure). No environment bypass; an exception is the user's (`--no-verify`). Tests: `python3 -m unittest scripts/tests/test_real_name_check.py`. |
| `require-private-remote.sh` | A `pre-push` hook for a repository whose content is only safe while it is PRIVATE (`~/.claude`, which tracks per-project memory under real names). It asks GitHub, authenticated (`gh api repos/<owner>/<repo> --jq .private`), on every push and refuses unless the answer is `true`; **fails closed** (no `gh`, not logged in, offline, or not a github.com remote all refuse). Install: `ln -s <checkout>/scripts/require-private-remote.sh ~/.claude/.git/hooks/pre-push`. Tests: `python3 -m unittest scripts/tests/test_require_private_remote.py`. |
| `onboard.py` | Implements README's "How to use this" levels 1-3 for someone bringing this rule set into `~/.claude` (level 0 is just reading; level 4 is `install-live-hooks.py`). `python3 scripts/onboard.py describe` prints a ready-to-paste description of this repository for a fresh Claude session in another project; `status` reports what `--home` already has; `level1`/`level2 FILE...`/`level3` copy the matching README level in. Every subcommand defaults to a **dry run** — pass `--apply` to actually write. Idempotent (level1's block carries a marker) and never overwrites an existing destination without `--force` (which backs the old file up first, same as `install-live-hooks.py`). `--home`/`--repo` point it at another target (tests). Tests: `python3 -m unittest scripts/tests/test_onboard.py`. |
| `install-live-hooks.py` | **Activates the live hook:** symlinks `guard-destructive.sh` into `~/.claude/hooks/` (pointing into the checkout you name with `--repo`, default: the one it lives in) and registers them in `~/.claude/settings.json` — `PreToolUse(Bash)` → the guard, `Stop` → `measurement-ledger.py --auto --detach`. Symlinks live in `hooks/`, not `scripts/`, because `~/.claude/scripts` points into the **prod** worktree and a new file there would collide with the next promotion. `settings.json` is backed up first; running it twice changes nothing; a real file in the way or unparsable JSON aborts untouched. `--check` reports (exit 1 if anything is missing or broken), `--remove` undoes it, and after a promotion `--repo <prod checkout>` re-points the links. Tests: `python3 -m unittest scripts/tests/test_install_live_hooks.py`. |
| `guard-destructive.sh` | A `PreToolUse(Bash)` hook that BLOCKS the never-do commands: forced push, push straight to `main`/`prod`, `--no-verify`, `DROP`/`TRUNCATE`, `rm -rf` on `/` `~` `.` `*`. Exit 2; **no env-variable bypass** — the user runs it themselves. A grep prefilter keeps it a few ms on ordinary calls. It matches text, so a commit message that merely *mentions* one of these is blocked too: reword it. Enabled through `settings.example.json`; tests: `python3 -m unittest scripts/tests/test_guard_destructive.py`. |
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
| `real-name-check.sh` + `commit-msg.sh` | **Copy as is, if you keep a local nickname map** | Run `pre-commit.sh --install` after copying so the `commit-msg` hook is linked too. Without the map they only warn. |
| `doc-check.py` | **Copy if you want it** | Runs from `pre-commit.sh` when present. Checks that do not apply (no `standards/`, no index) are no-ops. |
| `evidence-check.py` + `evidence-block.schema.json` | **Copy both, only if you run agents (modes C/D/E)** | The script loads the schema from beside itself. |
| `tests/` | **Copy only the tests of the scripts you copied** | |
| `md-hook.sh` | **Do not copy** | A user-level hook wired in `~/.claude/settings.json` (`settings.example.json`). |
| `step-stats.py`, `measurement-cuts.tsv` | **Do not copy** | They read the transcripts of *all* projects under `~/.claude/projects`; there is one canonical copy, here. The ledger, its per-day reports and the per-session cost tool USED to sit beside them and now live in ~/.claude/measurement/ (outside this repository, and deliberately so: it records per-session token and cost metadata, which a published rule set has no business carrying, and a ledger next to the rules keeps session metadata on disk longer than the platform's own retention). |

Every file marked **copy as is** is drift-checked against `~/.claude/scripts/` by `md-hook.sh` (the list is its `TWINS` variable; the configuration repository itself is exempt, since it is the canonical set).

After copying, run `python3 scripts/doc-check.py` and `bash scripts/gate-core.sh dev --list`:
the second prints every step that would run and the command it resolves to, without running any.
