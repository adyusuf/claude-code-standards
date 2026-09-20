#!/usr/bin/env bash
# The hook that runs the CLAUDE.md size ratchet automatically. It is bound to TWO
# events at once:
#
#   PostToolUse (Edit|Write) : immediately after the edit, for instant feedback
#   Stop                     : at the end of the turn, a METHOD-AGNOSTIC safety net
#
# ⚠️ WHY THE STOP EVENT IS ESSENTIAL: the PostToolUse matcher looks at the TOOL
# NAME. If Claude edits a CLAUDE.md through `Bash` (sed / a python heredoc / cat >)
# neither Edit nor Write fires and the hook stays SILENT. This is not theoretical:
# the very session in which this hook was installed made all of its CLAUDE.md
# edits through Bash — the hook would not have fired even once on the turn that
# created it. The Stop event looks at the whole repository at the end of the turn
# and does not care how the edit was made.
#
# ⚠️ SILENT WHEN GREEN: printing "within budget" on every turn is noise, and noise
# teaches people not to read. It speaks only when something EXCEEDS its ceiling or
# has NO BUDGET.
#
# ⚠️ This is NOT a release gate, it is a behavioural warning; the exit code is
# always 0. In a project where it is a real merge gate, a COPY of the script lives
# in the repository and CI runs that (see ~/.claude/scripts/README.md). Keep the
# distinction.
set -uo pipefail

input="$(cat 2>/dev/null || true)"

# PostToolUse supplies a file path; the Stop event does not.
path="$(printf '%s' "$input" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
ti=d.get("tool_input") or {}
print(ti.get("file_path") or ti.get("path") or "")' 2>/dev/null)"

if [ -n "$path" ]; then
  # Tool-based call: only CLAUDE.md is of interest.
  case "$(basename "$path")" in CLAUDE.md) ;; *) exit 0 ;; esac
  start="$(dirname "$path")"
else
  # Stop event: look at the repository of the current working directory.
  start="$PWD"
fi

root="$(git -C "$start" rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$root" ] || exit 0

output="$(MD_ROOT="$root" MD_KOK="$root" bash "$HOME/.claude/scripts/md-size-gate.sh" --hook 2>&1)" || true

# If no budget is installed, stay QUIET on the Stop event (suggesting an install
# on every turn is noise); say it once if a CLAUDE.md was explicitly edited.
if printf '%s' "$output" | grep -qi 'no CLAUDE.md budget is installed\|butcesi bu projede kurulu degil'; then
  [ -n "$path" ] && printf '%s\n' "$output"
  exit 0
fi

if printf '%s' "$output" | grep -qi 'CEILING EXCEEDED\|NO BUDGET\|FILE MISSING\|TAVAN AŞILDI\|BÜTÇESİZ\|DOSYA YOK'; then
  echo "⚠️ A CLAUDE.md budget was exceeded — a new permanent decision belongs in docs/<topic>.md, not in the root file:"
  printf '%s\n' "$output" | grep -Ei 'CEILING EXCEEDED|NO BUDGET|FILE MISSING|TAVAN AŞILDI|BÜTÇESİZ|DOSYA YOK'
  echo "   If you simplified it:  bash scripts/md-size-gate.sh --update"
fi

# ── Twin drift ───────────────────────────────────────────────────────────────
# These three tools are deliberate TWINS: the canonical copy lives under
# ~/.claude/scripts/, and every project takes a COPY into its own scripts/ and
# commits it (a project's gate cannot depend on a path outside the repository).
# Where there are twins there must also be a DRIFT TEST — this repository does
# exactly that for its other twins. Drift did happen once: the canonical copy was
# updated, the project copy stayed behind, and it was only noticed by comparing
# them by hand.
drifted=""
for tool in md-size-gate.sh md-rule-gate.py md-split.py; do
  [ -f "$root/scripts/$tool" ] || continue
  cmp -s "$root/scripts/$tool" "$HOME/.claude/scripts/$tool" || drifted="$drifted $tool"
done
if [ -n "$drifted" ]; then
  echo "⚠️ The MD tools have DRIFTED from the canonical copy:$drifted"
  echo "   Canonical: ~/.claude/scripts/  ·  This project: $root/scripts/"
  echo "   Which one is current? Compare first, then bring BOTH into line:"
  echo "   diff ~/.claude/scripts/<tool> scripts/<tool>"
fi
exit 0
