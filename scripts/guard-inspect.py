#!/usr/bin/env python3
"""Decides whether a Bash command is one of the never-do list's irreversible ones.

This is the judgement half of scripts/guard-destructive.sh, which carried it
inline in a heredoc until recently. Extracted for two reasons:

  * it could not be TESTED directly, only through the shell wrapper, one
    subprocess per case with the payload squeezed through stdin;
  * it could not be MEASURED. A bash coverage tracer sees a heredoc as ONE
    statement, so guard-destructive.sh reported 3 of 19 lines covered while every
    rule inside it was being exercised. Rule #29 asks for an honest denominator,
    and 16 of those 19 lines were Python pretending to be shell.

The patterns below were moved VERBATIM by a script, not retyped. They are the
difference between a blocked force-push and a lost branch, and a regex rewritten
from memory is how a guard quietly stops matching.

Reads the hook payload (JSON, or raw text) on stdin.
Exit 0 = allowed. Exit 2 = blocked, with the reason on stderr.

WARNING - FAIL CLOSED. A payload that will not parse is judged as RAW TEXT rather
than waved through, and the wrapper turns any unexpected exit code into a block.
A guard that opens when it is confused is not a guard. There is deliberately no
environment-variable bypass: a switch the agent can set is not a guard either.
"""
import json
import re
import sys


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

# Heredoc bodies are stripped for the GIT rules only — a heredoc that WRITES a
# script containing "--no-verify" is not a commit. They are NOT stripped for the
# rules below it, because `psql <<EOF ...` really does execute.
GIT_RULES = (
    (r"git\s+push([^;&|\n]*\s)?(-f|--force[a-z-]*)(\s|$)", "forced push"),
    (r"git\s+push[^;&|\n]*(\s|:)(main|prod)(\s|$)", "push straight to main/prod"),
    (r"git\s+(commit|push|merge)[^;&|\n]*--no-verify", "--no-verify skips the pre-commit gitleaks hook"),
)
ANY_RULES = (
    (r"(drop|truncate)\s+(table|database|schema)", "DROP/TRUNCATE (take a backup and get approval first)"),
    (r"rm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(--\s+)?(/|~|\$HOME|\*|\.)/?\*?(\s|$)", "recursive delete of a root/home/working directory"),
)


def command_of(raw):
    """The text to judge. Fail closed: an unparseable payload is judged raw."""
    try:
        return json.loads(raw).get("tool_input", {}).get("command", "") or raw
    except Exception:
        return raw


def verdict(command):
    """The reason this command is blocked, or None when it is allowed."""
    for view, rules in ((without_heredocs(command), GIT_RULES), (command, ANY_RULES)):
        for pattern, reason in rules:
            if re.search(pattern, view, re.I):
                return reason
    return None


def main():
    reason = verdict(command_of(sys.stdin.read()))
    if reason is None:
        return 0
    sys.stderr.write(
        "BLOCKED by guard-destructive.sh: %s\n"
        "Ask the user to run it themselves (never-do list).\n" % reason)
    return 2


if __name__ == "__main__":
    sys.exit(main())
