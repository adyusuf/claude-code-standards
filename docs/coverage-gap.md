# Coverage — this repository's own scripts (global rule #29)

Measured with `bash scripts/coverage.sh` (line coverage, `coverage` 7.10 in a venv
outside the repository, subprocesses included). The denominator is every hand-written
script; only `scripts/tests/` is omitted (`.coveragerc`). Nothing else is excluded.

> This file used to be a **gap** report: Python at 52% with four scripts at 0%, and
> the shell codebase NOT MEASURED. Both are closed. It is kept as the record of what
> closing them took, and of what is still thin.

## Where it stands

| Codebase | Coverage | State |
|---|---|---|
| Python scripts | **84%** (1,250 of 1,491 statements) | above the 80% threshold |
| Shell scripts | **89.1%** (525 of 589 lines, 197 traced runs) | above the 80% threshold |

Neither figure is an average of the other. #29 forbids averaging codebases, and the
gate reads them separately — either one below 80% closes it.

## What is still thin

Above the threshold is not the same as well tested. The weakest files, worth knowing
before trusting them:

| File | Coverage | Why it matters |
|---|---|---|
| `scripts/merge-gate.sh` | **0%** (0 of 8 lines) | the wrapper every promotion goes through. It only calls the core and the drift check — but nothing proves it calls them |
| `scripts/step-stats.py` | **61%** (121 statements missed) | the reporting half is untested. The sanitiser half is covered, and that is the half that must not leak |
| `scripts/guard-destructive.sh` | **65%** | the hook that refuses `rm -rf`, force push and `DROP`. The refusal paths are covered; the pass-through variants are not |
| `scripts/real-name-check.sh` | **75%** | the commit-message guard |
| `scripts/coverage-shell.sh` | **77.1%** | the tracer wrapper: it measures, and is itself the least measured thing here |

## How the shell codebase became measurable

It was reported as NOT MEASURED for two separate reasons, and both had to go:

- **`kcov` could not trace the macOS system bash** (`Can't find or open /bin/bash` —
  SIP). It traces the Homebrew bash instead, and `coverage.sh` prints which
  interpreter the number belongs to on every run.
- **Most shell tests ran a temporary *copy*** of the script in a throwaway
  repository, and no tracer attributes a copy back to the original. The tests were
  changed to run the scripts **in place**; that change is what made the number exist
  at all, and the reasoning is in `scripts/coverage-shell.sh`.

## The rule that keeps it honest

Each added test must catch a fault under mutation (`standards/10-test-strategy.md`
§7). A test that only executes lines is fake coverage, and adding one is the same as
loosening the threshold — which #29 forbids outright. The exclusion list stays in one
place with a reason per entry, and only generated code may be on it.
