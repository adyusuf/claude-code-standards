#!/usr/bin/env bash
# PRE-COMMIT gate — runs BEFORE the commit and STOPS it when red.
#
# Why it exists: md-hook.sh is a behavioural warning and always exits 0. In a
# real round the CLAUDE.md budget stayed over the ceiling across two commits
# because nothing blocked them, and each "fixed it" commit was written without
# measuring first. A ceiling nobody measures is not a ceiling; the gate belongs
# on the commit itself.
#
# Two steps, both in seconds, so the "merging into dev is fast" rule still holds:
#   1. CLAUDE.md size budget   (scripts/md-size-gate.sh)
#   2. gitleaks — secret scan over the staged content (pre-commit gitleaks is
#      the one gate that stays on in the dev direction)
#
# Install:            bash scripts/pre-commit.sh --install
# Deliberate bypass:  git commit --no-verify   (write the reason in the message)
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$root" ] || exit 0

if [ "${1:-}" = "--install" ]; then
  mkdir -p "$root/.git/hooks"
  ln -sf ../../scripts/pre-commit.sh "$root/.git/hooks/pre-commit"
  echo "installed: $root/.git/hooks/pre-commit -> scripts/pre-commit.sh"
  exit 0
fi

failed=0

# --- 1. CLAUDE.md size budget ------------------------------------------------
if [ -f "$root/scripts/md-size-gate.sh" ]; then
  output="$(MD_ROOT="$root" MD_KOK="$root" bash "$root/scripts/md-size-gate.sh" 2>&1)" || true
  if printf '%s' "$output" | grep -qi 'CEILING EXCEEDED\|TAVAN AŞILDI\|NO BUDGET\|BÜTÇESİZ'; then
    printf '%s\n' "$output"
    echo "✗ commit STOPPED — CLAUDE.md budget (standards/00-working-method.md §6a)."
    echo "  Move the rule to docs/decision-log.md, or raise the ceiling with a written reason."
    failed=1
  fi
fi

# --- 2. gitleaks over the staged content -------------------------------------
if command -v gitleaks >/dev/null 2>&1; then
  if ! gitleaks git --staged --no-banner --redact -l error >/dev/null 2>&1; then
    echo "✗ commit STOPPED — gitleaks found a secret in the staged content."
    echo "  If a secret leaked, ROTATE it first, then clean the history."
    failed=1
  fi
else
  echo "⚠️ gitleaks is not installed — the secret scan DID NOT RUN (a gate that does not run is not a gate that passed)."
fi

exit "$failed"
