#!/usr/bin/env bash
# Line coverage of THIS repository's own scripts (global rule #29): Python and JavaScript measured,
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
# A Windows venv keeps its executables in Scripts/, not bin/.
vbin="$venv/bin"
[ -d "$vbin" ] || [ ! -d "$venv/Scripts" ] || vbin="$venv/Scripts"
# UTF-8 mode for the tests AND every Python they start (PEP 540): on Windows the locale
# codec is cp1252, which garbled every ✓/✗ the scripts print and left subprocess output
# as None where it could not be decoded (42 of 92 Windows failures, 04/10/2026).
export PYTHONUTF8=1

echo "▶ Python scripts (threshold ${min}%)"
if [ ! -x "$vbin/coverage" ] && [ ! -x "$vbin/coverage.exe" ]; then
  echo "  NOT MEASURED: no coverage in $venv"
  echo "  create it: python3 -m venv \"$venv\" && \"$vbin/pip\" install coverage"
  status=3
else
  purelib="$("$vbin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
  [ -f "$purelib/coverage-subprocess.pth" ] || echo 'import coverage; coverage.process_startup()' > "$purelib/coverage-subprocess.pth"
  data="$(mktemp -d)"
  export COVERAGE_SRC="$root/scripts" COVERAGE_DATA="$data/.coverage" COVERAGE_PROCESS_START="$root/.coveragerc"
  if ! PATH="$vbin:$PATH" coverage run -m unittest discover -s scripts/tests -p 'test_*.py' >"$data/tests.log" 2>&1; then
    tail -20 "$data/tests.log" | sed 's/^/  /'
    echo "  ✗ the tests are red — coverage of a red suite is not a measurement"
    status=1
  else
    PATH="$vbin:$PATH" coverage combine >/dev/null 2>&1
    if PATH="$vbin:$PATH" coverage report --fail-under="$min" | sed 's/^/  /'; then
      echo "  ✓ at or above ${min}%"
    else
      echo "  ✗ below ${min}% — the gap and the plan to close it: docs/coverage-gap.md"
      status=1
    fi
  fi
  find scripts -name __pycache__ -path '*tests*' -prune -exec rm -rf {} + 2>/dev/null
  rm -rf "$data"
fi

# JavaScript: MEASURED with Node's built-in coverage, so there is no package to
# install. This repository has none; a project that copies this file gets the step either way. Node only
# reports files a test LOADED, so a file no test touches
# would silently leave the denominator: every file must appear in the report, or
# the codebase is NOT MEASURED (#29).
echo "▶ JavaScript (threshold ${min}%)"
js_files="$(find scripts -name '*.js' -not -path '*/tests/*' -not -path '*/node_modules/*' 2>/dev/null | sort)"
js_status=0
# Anything but a number counts as too old (fail closed: an unreadable version must not run).
node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null | tr -d '\r')"
case "$node_major" in ''|*[!0-9]*) node_major=0 ;; esac
if [ -z "$js_files" ]; then
  echo "  n/a: no JavaScript here"
elif ! command -v node >/dev/null 2>&1; then
  echo "  NOT MEASURED: node is not installed"
  js_status=3
elif [ "$node_major" -lt 22 ]; then
  # Node 20 rejects the --test-coverage-* flags and the run reads as a RED suite — an
  # environment problem reported as a product one (Windows machine, 04/10/2026).
  echo "  NOT MEASURED: node $(node --version 2>/dev/null) is too old — the coverage flags need Node 22+"
  js_status=3
else
  js_log="$(mktemp)"
  node --test --experimental-test-coverage --test-coverage-include='scripts/**/*.js' \
       --test-coverage-exclude='scripts/tests/**' --test-coverage-lines="$min" \
       'scripts/tests/**/*.test.js' >"$js_log" 2>&1
  js_run=$?
  sed -n '/start of coverage report/,/end of coverage report/p' "$js_log" | sed 's/^/  /'
  unloaded=""
  for file in $js_files; do
    grep -q " $(basename "$file") " "$js_log" || unloaded="$unloaded $file"
  done
  if ! grep -q '^# fail 0$' "$js_log"; then
    grep -E '^not ok|^# (pass|fail) ' "$js_log" | sed 's/^/  /'
    echo "  ✗ the tests are red — coverage of a red suite is not a measurement"
    js_status=1
  elif [ -n "$unloaded" ]; then
    echo "  NOT MEASURED: no test loads$unloaded"
    js_status=3
  elif [ "$js_run" != 0 ]; then
    echo "  ✗ below ${min}%"
    js_status=1
  else
    echo "  ✓ at or above ${min}%"
  fi
  rm -f "$js_log"
fi
if [ "$js_status" != 0 ] && [ "$status" = 0 ]; then status="$js_status"; fi

# TypeScript of the Claude Code mod (hooks/*.ts, hooks/*.tsx): the NARROW exception of rule #29 (user decision
# 22/10/2026). The mod runs only inside Claude Code's engine, whose test runner (`claude plugin test`) reports no
# coverage. So: (1) the logic lives in engine-free files (no import from 'claude-code'); they are MEASURED here with Deno
# and held to the threshold; (2) the engine glue is the ONE exclusion below, with its reason, and is reported "not
# measured" in every run - never dropped silently; (3) any other hand-written .ts/.tsx under hooks/ that is neither
# tested logic nor that listed glue file makes the run NOT MEASURED. Adding a file to the glue list is loosening #29.
ts_glue="hooks/register.tsx"          # imports 'claude-code' and draws through the engine; no runner reports its lines
echo "▶ TypeScript mod logic (threshold ${min}%)"
ts_status=0
ts_all="$(find hooks -maxdepth 1 \( -name '*.ts' -o -name '*.tsx' \) -not -name '*.test.ts' -not -name '*.test.tsx' 2>/dev/null | sort)"
ts_logic=""
for file in $ts_all; do
  [ "$file" = "$ts_glue" ] && continue
  if grep -q "from 'claude-code" "$file"; then
    echo "  NOT MEASURED: $file imports the engine but is not the listed glue file ($ts_glue)"; ts_status=3
  else
    ts_logic="$ts_logic $file"
  fi
done
if [ -z "$ts_all" ]; then
  echo "  n/a: no TypeScript here"
elif ! command -v deno >/dev/null 2>&1; then
  echo "  NOT MEASURED: deno is not installed (brew install deno)"; ts_status=3
elif [ "$ts_status" = 0 ]; then
  ts_cov="$(mktemp -d)"
  if ! deno test --quiet --sloppy-imports --coverage="$ts_cov" --import-map=scripts/ts-shim/import_map.json hooks/*.test.ts \
        >"$ts_cov/run.log" 2>&1; then
    sed 's/^/  /' "$ts_cov/run.log" | head -20
    echo "  ✗ the tests are red — coverage of a red suite is not a measurement"; ts_status=1
  else
    ts_lines=0; ts_hit=0
    for file in $ts_logic; do
      lcov="$(deno coverage "$ts_cov" --lcov --include="$(printf '%s' "$file" | sed 's/\./\\./g')\$" 2>/dev/null)"
      lf="$(printf '%s\n' "$lcov" | sed -n 's/^LF://p' | head -1)"; lh="$(printf '%s\n' "$lcov" | sed -n 's/^LH://p' | head -1)"
      if [ -z "$lf" ]; then echo "  NOT MEASURED: no test loads $file"; ts_status=3; continue; fi
      printf '    %-28s %s/%s  %s%%\n' "$file" "$lh" "$lf" "$(( lf == 0 ? 100 : 100 * lh / lf ))"
      ts_lines=$((ts_lines + lf)); ts_hit=$((ts_hit + lh))
    done
    if [ "$ts_status" = 0 ]; then
      pct=$(( ts_lines == 0 ? 100 : 100 * ts_hit / ts_lines ))
      echo "    TOTAL                        ${ts_hit}/${ts_lines}  ${pct}%"
      if [ "$pct" -ge "$min" ]; then echo "  ✓ at or above ${min}%"; else echo "  ✗ below ${min}%"; ts_status=1; fi
    fi
  fi
  rm -rf "$ts_cov"
  echo "  not measured, listed exclusion (rule #29, narrow exception): $ts_glue - engine glue, no runner reports its lines"
fi
if [ "$ts_status" != 0 ] && [ "$status" = 0 ]; then status="$ts_status"; fi

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
