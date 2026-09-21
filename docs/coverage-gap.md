# Coverage gap — this repository's own scripts (global rule #29)

Measured with `bash scripts/coverage.sh` (line coverage, `coverage` 7.10 in a venv outside
the repository, subprocesses included). The denominator is every hand-written script;
only `scripts/tests/` is omitted (`.coveragerc`). Nothing else is excluded.

## Where it stands

| Codebase | Coverage | State |
|---|---|---|
| Python scripts | **52%** (607 of 1,168 statements) | **below the 80% threshold** |
| Shell scripts | — | **not measured** (see below) |

| Script | Statements | Covered | Note |
|---|---:|---:|---|
| `install-live-hooks.py` | 149 | 95% | new, tested in place |
| `doc-check.py` | 101 | 92% | new |
| `evidence-check.py` | 117 | 85% | new |
| `measurement-ledger.py` | 191 | 79% | new; the detached-child test runs a copy |
| `step-stats.py` | 287 | 43% | existing |
| `md-rule-gate.py` | 155 | **0%** | existing, no test at all |
| `md-split.py` | 84 | **0%** | existing, no test at all |
| `session-cost.py` | 51 | **0%** | existing, no test at all |
| `prefix-measure.py` | 33 | **0%** | existing, no test at all |

The four scripts written in this round are at or near the bar; the gap is the four
older scripts that never had a test.

## Plan to close it

80% of 1,168 statements means at most 233 uncovered; 561 are. Every line that can be
covered in the four untested scripts plus `step-stats.py` is needed — roughly 390
coverable, 330 required. One task, one branch, one merge each (#26), in order of yield:

1. `md-rule-gate.py` (155 statements): fixtures for the three rule-loss measures
   (❌ items, prohibition lines, backticked identifiers) and the triage path.
2. `step-stats.py` (165 missed): `shape()` with the sanitiser canary, `count_steps` on a
   synthetic transcript, `price`, `compare_cuts`, and `report`.
3. `md-split.py` (84): a two-layer split of a small log, checking text moves verbatim.
4. `session-cost.py` and `prefix-measure.py` (84): a synthetic transcript each.
5. Wire `coverage.sh` into the promotion gate; until step 4 lands it stays red on purpose.

Each added test must catch a fault under mutation (`standards/10-test-strategy.md` §7):
a test that only executes lines is fake coverage and is the same as loosening the
threshold.

## Shell scripts: not measured, and why

`kcov` installs, but on this machine it cannot trace the macOS system bash
(`Can't find or open /bin/bash`; SIP). Separately, most shell tests run a temporary
*copy* of the script in a throwaway repository, which no tracer attributes to the
original. Two ways forward, neither done yet: measure the shell scripts on a Linux CI
runner where `kcov` works, and change the tests to run the scripts in place. Until then
`scripts/coverage.sh` reports the shell codebase as NOT MEASURED on every run, and that
blocks a promotion exactly as a failure would.
