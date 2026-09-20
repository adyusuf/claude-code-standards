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
| `measurement-cuts.tsv` | The timestamps of configuration changes (`ISO timestamp<TAB>label`); `step-stats.py` computes the prefix median **before and after** each cut on its own. |
| `session-cost.py` | Measures what a single session has spent so far, from its transcript, split into main conversation and subagents. |

⚠️ **Counting traps (found by measurement):** a heredoc **body** is data, not a
command (the body is stripped but everything after it is kept — otherwise the
count halves) · `grep -E "dotnet|codeql"` is not a SAST run, and such mentions are
reported separately in the `dismissed` column rather than counted · a step that
runs from inside another script is invisible: that is **"not seen"**, not "zero".
