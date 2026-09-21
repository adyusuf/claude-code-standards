#!/usr/bin/env bash
# SAST for this repository's Python (global rule #19).
#
# Rule #19 says SAST runs in every project and runs LOCALLY with the same
# thresholds CI uses — never two different rules in two places. gate-core.sh
# calls this file through SAST_CMD in scripts/merge-gate.conf.
#
# Scope: Python only. CodeQL has no shell analyser, so the shell scripts are NOT
# covered by SAST here and that is stated on every run rather than left to be
# assumed — the same honesty the coverage gate applies.
#
# Threshold: a result whose rule has security-severity >= 7.0 (CodeQL's high and
# critical band) FAILS the gate. Lower-severity results are printed and do not
# block. #19: "critical/high findings block the merge."
#
# Exit codes: 0 clean · 1 a high/critical finding · 2 usage/environment
#             3 NOT RUN — which blocks exactly like a failure, because a gate
#               that did not run did not pass (#19)
#
# ⚠️ The database is rebuilt on every run and cached under .codeql/ (gitignored).
# A stale database is worse than none: it reports yesterday's code as today's.
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not inside a git repository" >&2; exit 2; }
cd "$root" || exit 2

echo "▶ SAST (CodeQL, Python)"

command -v codeql >/dev/null 2>&1 || {
  echo "  NOT RUN: codeql is not installed (brew install --cask codeql)"
  echo "  A gate that did not run did not pass (#19)."
  exit 3; }

if [ -z "$(find . -name '*.py' -not -path './.codeql/*' -not -path '*/node_modules/*' -print -quit 2>/dev/null)" ]; then
  echo "  n/a: this repository has no Python"
  exit 0
fi

db="${CODEQL_DB:-$root/.codeql/db}"
out="${CODEQL_SARIF:-$root/.codeql/results.sarif}"
suite="${CODEQL_SUITE:-codeql/python-queries:codeql-suites/python-security-extended.qls}"
mkdir -p "$(dirname "$db")"
rm -rf "$db"

log="$(mktemp)"
trap 'rm -f "$log"' EXIT

if ! codeql database create "$db" --language=python --source-root="$root" \
        --overwrite >"$log" 2>&1; then
  tail -15 "$log" | sed 's/^/    /'
  echo "  NOT RUN: the CodeQL database could not be built"
  exit 3
fi

if ! codeql database analyze "$db" "$suite" \
        --format=sarif-latest --output="$out" --download >"$log" 2>&1; then
  tail -15 "$log" | sed 's/^/    /'
  echo "  NOT RUN: the CodeQL analysis did not complete (query pack unavailable offline?)"
  exit 3
fi

python3 - "$out" <<'REPORT'
import json, sys
from collections import Counter

with open(sys.argv[1], encoding='utf-8') as handle:
    sarif = json.load(handle)

# security-severity lives on the RULE, not the result, so the rules are indexed
# first. A rule without one is not a security rule — it is a quality query, and
# quality is not what this gate blocks on.
severity, blocking, other = {}, [], []
for run in sarif.get('runs', []):
    for rule in (run.get('tool', {}).get('driver', {}).get('rules') or []):
        props = rule.get('properties') or {}
        raw = props.get('security-severity')
        if raw is not None:
            try:
                severity[rule['id']] = float(raw)
            except (TypeError, ValueError):
                pass
    for result in run.get('results', []):
        rule_id = result.get('ruleId', '?')
        score = severity.get(rule_id)
        location = ''
        for loc in result.get('locations', [])[:1]:
            phys = loc.get('physicalLocation', {})
            location = '%s:%s' % (
                phys.get('artifactLocation', {}).get('uri', '?'),
                (phys.get('region') or {}).get('startLine', '?'))
        line = '%s  %s  %s' % (rule_id, location,
                               (result.get('message') or {}).get('text', '')[:100])
        (blocking if (score or 0) >= 7.0 else other).append((score, line))

print('  queries with a security severity: %d' % len(severity))
if other:
    print('  %d finding(s) below the high band (reported, not blocking):' % len(other))
    for score, line in sorted(other, key=lambda x: -(x[0] or 0))[:10]:
        print('    [%s] %s' % ('-' if score is None else score, line))
if blocking:
    print('  ✗ %d HIGH/CRITICAL finding(s) — the merge is blocked (#19):' % len(blocking))
    for score, line in sorted(blocking, key=lambda x: -(x[0] or 0)):
        print('    [%.1f] %s' % (score, line))
    raise SystemExit(1)
print('  ✓ no high or critical finding')
REPORT
status=$?

echo "  ⚠️ shell scripts are NOT covered: CodeQL has no shell analyser (see this file's header)"
exit "$status"
