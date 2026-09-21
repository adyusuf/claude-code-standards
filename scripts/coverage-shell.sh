#!/usr/bin/env bash
# Line coverage of THIS repository's own SHELL scripts (global rule #29).
#
# It works by running the ordinary Python test suite with a `bash` SHIM first on
# PATH. The shim rewrites an invocation of one of our own scripts
#     bash scripts/gate-core.sh test --list
# into a kcov run of that script
#     kcov <outdir> scripts/gate-core.sh test --list
# and leaves every other `bash` call alone. Each run writes its own output
# directory; they are merged at the end.
#
# ⚠️ WHY THE SHIM, and not `kcov python3 -m unittest`: kcov chooses its engine
# from the TARGET. Given a binary (python3, or `bash` itself) it does native
# instrumentation and reports 0% with "no debug symbols"; it uses its bash engine
# only when the target IS the script. So the script has to be the target, which
# means intercepting at the point the test spawns it.
#
# ⚠️ AND WHY THE TESTS MUST NOT COPY THE SCRIPT: a tracer attributes execution to
# the file it actually ran. While the gate tests copied gate-core.sh into a
# throwaway repository, the real scripts/gate-core.sh measured 0% no matter how
# many tests exercised it — which is most of why shell coverage was reported here
# as an unmeasurable, blocking gap for so long.
#
# Requirements: kcov, and a bash that kcov can trace. macOS's /bin/bash is SIP
# protected and cannot be traced ("Can't find or open /bin/bash"), so a separate
# bash is needed — `brew install bash` puts one in /opt/homebrew/bin. Both are
# PROBED below, and if either is missing this exits 3: not measured, which blocks
# exactly like a failure (#29 — an unmeasured codebase does not count as passing).
#
# Exit codes: 0 at or above the threshold · 1 below it · 2 usage/environment · 3 NOT MEASURED
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not inside a git repository" >&2; exit 2; }
cd "$root" || exit 2
min="${COVERAGE_MIN:-80}"

kcov_bin="$(command -v kcov 2>/dev/null)" || true
[ -n "$kcov_bin" ] || {
  echo "  NOT MEASURED: kcov is not installed (brew install kcov)"; exit 3; }

# A traceable bash: the first candidate kcov can actually run.
trace_bash=""
for candidate in "${COVERAGE_BASH:-}" /opt/homebrew/bin/bash /usr/local/bin/bash /usr/bin/bash /bin/bash; do
  [ -n "$candidate" ] && [ -x "$candidate" ] || continue
  probe="$(mktemp -d)"
  printf '#!%s\ntrue\n' "$candidate" > "$probe/p.sh"; chmod +x "$probe/p.sh"
  if "$kcov_bin" --include-path="$probe/p.sh" "$probe/out" "$probe/p.sh" >/dev/null 2>&1 \
     && [ -n "$(find "$probe/out" -name coverage.json -print -quit 2>/dev/null)" ]; then
    trace_bash="$candidate"; rm -rf "$probe"; break
  fi
  rm -rf "$probe"
done
[ -n "$trace_bash" ] || {
  echo "  NOT MEASURED: kcov cannot trace any bash on this machine"
  echo "  macOS: /bin/bash is SIP protected — install a separate one: brew install bash"
  exit 3; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin" "$work/out"

# The shim. It must be a REAL bash script (its own shebang is the traceable bash),
# and it must pass everything it does not recognise straight through.
cat > "$work/bin/bash" <<SHIM
#!$trace_bash
# Interposed by scripts/coverage-shell.sh. Only OUR OWN scripts are traced.
for arg in "\$@"; do
  case "\$arg" in
    $root/scripts/*.sh)
      if [ -f "\$arg" ]; then
        # ⚠️ An ABSOLUTE path to kcov, not a PATH lookup. A test that legitimately
        # strips a directory from PATH (to prove a missing tool is announced) also
        # strips kcov when they share a directory, and the shim then died with
        # "exec: kcov: not found" — turning a passing suite red only under
        # measurement.
        exec "$kcov_bin" --include-path="$root/scripts" --exclude-pattern=/tests/ \\
                  "$work/out/\$(date +%s%N)-\$\$" "\$@"
      fi
      ;;
  esac
done
exec "$trace_bash" "\$@"
SHIM
chmod +x "$work/bin/bash"

echo "▶ Shell scripts (threshold ${min}%)"
echo "  tracer: kcov · bash: $trace_bash"
PATH="$work/bin:$PATH" python3 -m unittest discover -s scripts/tests -p 'test_*.py' \
  >"$work/tests.log" 2>&1
tests_status=$?
if [ "$tests_status" != 0 ]; then
  tail -15 "$work/tests.log" | sed 's/^/    /'
  echo "  ✗ the tests are red — coverage of a red suite is not a measurement"
  exit 1
fi

runs="$(find "$work/out" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')"
[ "$runs" != 0 ] || { echo "  NOT MEASURED: the shim was never reached — no test ran one of our scripts"; exit 3; }

python3 - "$work/out" "$min" "$runs" <<'REPORT'
import glob, sys, xml.etree.ElementTree as ET

out_dir, minimum, runs = sys.argv[1], float(sys.argv[2]), sys.argv[3]

# A TRUE union across runs, not an approximation: kcov's cobertura.xml carries
# per-line hit counts, so a line covered by any one test counts as covered.
# (coverage.json only has per-file totals, which would force a lower bound.)
hit, known = {}, {}
for path in glob.glob(f"{out_dir}/**/cobertura.xml", recursive=True):
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        continue
    for klass in tree.iter("class"):
        name = klass.get("filename") or ""
        if not name.endswith(".sh") or "/tests/" in name:
            continue
        for line in klass.iter("line"):
            number = int(line.get("number"))
            known.setdefault(name, set()).add(number)
            if int(line.get("hits") or 0) > 0:
                hit.setdefault(name, set()).add(number)

if not known:
    print("  NOT MEASURED: no shell file appeared in any report")
    raise SystemExit(3)

covered_sum = total_sum = 0
for name in sorted(known):
    covered, total = len(hit.get(name, set())), len(known[name])
    covered_sum += covered
    total_sum += total
    print(f"    {name.split('/')[-1]:<26} {covered:>4}/{total:<4} {100.0*covered/total:>6.1f}%")

pct = 100.0 * covered_sum / total_sum
print(f"    {'TOTAL':<26} {covered_sum:>4}/{total_sum:<4} {pct:>6.1f}%   ({runs} traced runs)")
if pct + 1e-9 < minimum:
    print(f"  \u2717 below {minimum:.0f}% \u2014 the gap and the plan: docs/coverage-gap.md")
    raise SystemExit(1)
print(f"  \u2713 at or above {minimum:.0f}%")
REPORT
