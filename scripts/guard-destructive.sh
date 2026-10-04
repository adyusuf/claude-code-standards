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
# grep's 1 means "no keyword": allowed. Anything else means grep did not run, and reading that as "no
# keyword" let EVERY command through — `rm -rf ~` included — on a PATH where grep could not start
# (found on Windows, 04/10/2026). That fails closed now, like every other path here.
printf '%s' "$payload" | grep -qiE 'push|drop|truncate|rm |no-verify'
case $? in
  0) ;;
  1) exit 0 ;;
  *) echo "BLOCKED by guard-destructive.sh: could not inspect the command (grep did not run). Ask the user to run it." >&2
     exit 2 ;;
esac

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
# The interpreter: `python3`, else a `python` that IS Python 3. A Windows install of
# Python has no `python3` at all, only `python`; asking for python3 alone made this
# hook block every keyword-bearing command on such a machine (seen 04/10/2026, Git
# Bash on Windows Server). Each candidate is PROBED, not just looked up: the Windows
# Store stub answers to `python3` and runs nothing, and a `python` may be Python 2.
py=""
for candidate in python3 python; do
  if "$candidate" -c 'import sys; sys.exit(sys.version_info[0] < 3)' >/dev/null 2>&1; then
    py="$candidate"
    break
  fi
done
if [ -z "$py" ]; then
  echo "BLOCKED by guard-destructive.sh: could not inspect the command — no Python 3 interpreter on PATH (tried python3, then python). Install Python 3, or on Windows make python3 resolve to it. Ask the user to run the command." >&2
  exit 2
fi
message="$(printf '%s' "$payload" | "$py" "$inspector" 2>&1 >/dev/null)"
status=$?
# 0 = allowed, 2 = blocked (the inspector wrote the reason). Anything else means
# the inspector itself failed: fail closed rather than let the command through.
case "$status" in
  0) exit 0 ;;
  2) printf '%s\n' "$message" >&2; exit 2 ;;
  *) echo "BLOCKED by guard-destructive.sh: could not inspect the command ($py guard-inspect.py failed with status $status). Ask the user to run it." >&2; exit 2 ;;
esac
