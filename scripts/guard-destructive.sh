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

message="$(printf '%s' "$payload" | python3 -c '
import json, re, sys

raw = sys.stdin.read()
try:
    command = json.loads(raw).get("tool_input", {}).get("command", "") or raw
except Exception:
    command = raw          # fail closed: judge the raw text

def without_heredocs(text):
    kept, tag = [], None
    for line in text.splitlines():
        if tag is not None:
            if line.strip() == tag:
                tag = None
            continue
        kept.append(line)
        m = re.search(r"<<-?\s*[\"\x27]?([A-Za-z_][A-Za-z_0-9]*)", line)
        if m:
            tag = m.group(1)
    return "\n".join(kept)

GIT_RULES = (
    (r"git\s+push([^;&|\n]*\s)?(-f|--force[a-z-]*)(\s|$)", "forced push"),
    (r"git\s+push[^;&|\n]*(\s|:)(main|prod)(\s|$)", "push straight to main/prod"),
    (r"git\s+(commit|push|merge)[^;&|\n]*--no-verify", "--no-verify skips the pre-commit gitleaks hook"),
)
ANY_RULES = (
    (r"(drop|truncate)\s+(table|database|schema)", "DROP/TRUNCATE (take a backup and get approval first)"),
    (r"rm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(--\s+)?(/|~|\$HOME|\*|\.)/?\*?(\s|$)", "recursive delete of a root/home/working directory"),
)
git_view = without_heredocs(command)
for view, rules in ((git_view, GIT_RULES), (command, ANY_RULES)):
    for pattern, reason in rules:
        if re.search(pattern, view, re.I):
            sys.stderr.write("BLOCKED by guard-destructive.sh: %s\nAsk the user to run it themselves (never-do list).\n" % reason)
            sys.exit(2)
' 2>&1 >/dev/null)"
status=$?
# 0 = allowed, 2 = blocked (message already printed). Anything else means the
# inspector itself failed: fail closed rather than let the command through.
case "$status" in
  0) exit 0 ;;
  2) printf '%s\n' "$message" >&2; exit 2 ;;
  *) echo "BLOCKED by guard-destructive.sh: could not inspect the command (python3 unavailable?). Ask the user to run it." >&2; exit 2 ;;
esac
