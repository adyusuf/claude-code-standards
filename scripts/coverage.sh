#!/usr/bin/env bash
# Line coverage of THIS repository's own scripts (global rule #29): Python measured,
# shell reported honestly as NOT MEASURED. gate-core.sh runs this file as the
# coverage step when it is present (scripts/coverage.sh).
#
# Exit codes:  0  every codebase measured and at or above the threshold
#              1  the tests are red, or a measured codebase is below the threshold
#              3  something could NOT be measured — which blocks, exactly like a failure
#                 (#29: an unmeasured codebase does not count as passing)
#
# Python: `coverage` in a venv OUTSIDE the repository (COVERAGE_VENV, default
# ~/.cache/claude-standards/venv) so no interpreter of the user's is touched. Create it once:
#     python3 -m venv ~/.cache/claude-standards/venv && ~/.cache/claude-standards/venv/bin/pip install coverage
# Subprocesses started by the tests are measured too (a .pth file in the venv, written
# here if missing); tests that run a COPY of a script in a temporary directory are not
# attributed to the original — measure a script through the original path.
#
# Shell: MEASURED via scripts/coverage-shell.sh, which runs the test suite with a `bash`
# shim that turns each invocation of one of our scripts into a kcov run of that script.
# It needs kcov and a bash kcov can trace (macOS /bin/bash is SIP protected — install one
# with `brew install bash`); both are probed, and a missing tool exits 3, which blocks
# exactly like a failure (#29). The tests must run the ORIGINAL scripts, not copies:
# a tracer attributes execution to the file it ran, so a copied script measures 0%.
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not inside a git repository" >&2; exit 2; }
cd "$root" || exit 2
venv="${COVERAGE_VENV:-$HOME/.cache/claude-standards/venv}"
min="${COVERAGE_MIN:-80}"
status=0

echo "▶ Python scripts (threshold ${min}%)"
if [ ! -x "$venv/bin/coverage" ]; then
  echo "  NOT MEASURED: no coverage in $venv"
  echo "  create it: python3 -m venv \"$venv\" && \"$venv/bin/pip\" install coverage"
  status=3
else
  purelib="$("$venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
  [ -f "$purelib/coverage-subprocess.pth" ] || echo 'import coverage; coverage.process_startup()' > "$purelib/coverage-subprocess.pth"
  data="$(mktemp -d)"
  export COVERAGE_SRC="$root/scripts" COVERAGE_DATA="$data/.coverage" COVERAGE_PROCESS_START="$root/.coveragerc"
  if ! PATH="$venv/bin:$PATH" coverage run -m unittest discover -s scripts/tests -p 'test_*.py' >"$data/tests.log" 2>&1; then
    tail -20 "$data/tests.log" | sed 's/^/  /'
    echo "  ✗ the tests are red — coverage of a red suite is not a measurement"
    status=1
  else
    PATH="$venv/bin:$PATH" coverage combine >/dev/null 2>&1
    if PATH="$venv/bin:$PATH" coverage report --fail-under="$min" | sed 's/^/  /'; then
      echo "  ✓ at or above ${min}%"
    else
      echo "  ✗ below ${min}% — the gap and the plan to close it: docs/coverage-gap.md"
      status=1
    fi
  fi
  find scripts -name __pycache__ -path '*tests*' -prune -exec rm -rf {} + 2>/dev/null
  rm -rf "$data"
fi

# Shell: MEASURED by scripts/coverage-shell.sh (kcov). It used to be reported here
# as permanently NOT MEASURED, which made this gate impossible to pass on macOS at
# any Python coverage. Two things were actually in the way and both are fixed:
# kcov could not trace the SIP-protected /bin/bash (a separate bash is installed
# and probed for), and the tests ran COPIES of the scripts, which a tracer cannot
# attribute to the originals. If the tooling is absent the helper still exits 3 and
# this gate still blocks — #29 is unchanged, it is just no longer unmeasurable.
bash scripts/coverage-shell.sh
shell_status=$?
if [ "$shell_status" != 0 ] && [ "$status" = 0 ]; then status="$shell_status"; fi

exit "$status"
