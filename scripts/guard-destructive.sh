#!/usr/bin/env bash
# PreToolUse(Bash) hook: blocks the irreversible commands from the never-do list.
#
#   git push --force / -f / --force-with-lease     git push ... main|prod (any refspec)
#   git commit/push/merge --no-verify               DROP|TRUNCATE  TABLE|DATABASE|SCHEMA
#   rm -rf on / ~ $HOME . *
#
# Exit 2 = the harness blocks the call and shows this message to the model. The
# model cannot approve it; the user runs the command themselves, or rewords a
# command that only MENTIONS one of these words (a commit message, an echo).
# There is deliberately NO environment-variable bypass: a switch the agent can
# set is not a guard.
#
# Heredoc bodies are ignored by the GIT rules (a heredoc that WRITES a script
# containing "--no-verify" is not a commit) but NOT by the SQL and rm rules (a
# `psql <<EOF DROP TABLE` heredoc executes). A script run through `bash <<EOF`
# is therefore not inspected for git commands: this is a safety net against
# accidents, not a sandbox.
#
# Cost: a grep prefilter runs on every Bash call (a few ms, ~93% of real calls
# stop there); the JSON is parsed and the patterns applied only on a keyword hit.
set -uo pipefail

payload="$(cat 2>/dev/null || true)"
printf '%s' "$payload" | grep -qiE 'push|drop|truncate|rm |no-verify' || exit 0

# The judgement lives in scripts/guard-inspect.py. It used to be a ~37-line
# Python program inline in a heredoc here, which meant it could not be tested
# except through this wrapper, and could not be measured at all: a bash coverage
# tracer counts a heredoc as ONE statement, so this file reported 3 of 19 lines
# covered while every rule in it was being exercised (#29 wants an honest
# denominator). Moved, patterns byte-identical.
# ⚠️ THE SYMLINK MUST BE RESOLVED FIRST. This hook is installed as a SYMLINK at
# ~/.claude/hooks/guard-destructive.sh pointing into the repository's scripts/,
# and $BASH_SOURCE is the path bash was INVOKED with — the link, not the target.
# `dirname` on it gives ~/.claude/hooks/, where guard-inspect.py does not exist,
# so the fail-closed branch below fired and a plainly allowed command came back
# BLOCKED. Caught by invoking this file through a symlink on purpose; the direct
# call worked perfectly and hid it completely. Fail-closed turned what would have
# been a security hole into a total work stoppage instead — better, but still the
# whole hook.
src="${BASH_SOURCE[0]}"
while [ -L "$src" ]; do
  target="$(readlink "$src")"
  case "$target" in
    /*) src="$target" ;;
    *)  src="$(cd "$(dirname "$src")" && pwd)/$target" ;;
  esac
done
here="$(cd "$(dirname "$src")" && pwd)"
inspector="$here/guard-inspect.py"
if [ ! -f "$inspector" ]; then
  echo "BLOCKED by guard-destructive.sh: guard-inspect.py is missing next to this hook. Ask the user to run the command." >&2
  exit 2
fi
message="$(printf '%s' "$payload" | python3 "$inspector" 2>&1 >/dev/null)"
status=$?
# 0 = allowed, 2 = blocked (the inspector wrote the reason). Anything else means
# the inspector itself failed: fail closed rather than let the command through.
case "$status" in
  0) exit 0 ;;
  2) printf '%s\n' "$message" >&2; exit 2 ;;
  *) echo "BLOCKED by guard-destructive.sh: could not inspect the command (python3 unavailable?). Ask the user to run it." >&2; exit 2 ;;
esac
