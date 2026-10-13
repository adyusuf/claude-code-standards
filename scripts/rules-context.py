#!/usr/bin/env python3
"""Puts the global working rules (CLAUDE.md) into Claude's context from a plugin hook.

A plugin cannot ship a CLAUDE.md that Claude Code loads, so the adyusuf plugin's
hooks/hooks.json calls this script on SessionStart and SubagentStart instead
(docs/decision-log.md, "Plugin install"). Claude Code caps each hook's output at
10,000 characters, so CLAUDE.md is split into parts at its own boundaries (a `## `
heading or a numbered rule) and every registered hook prints one part.

Usage:
    rules-context.py session  <part> <registered>   # plain text, SessionStart
    rules-context.py subagent <part> <registered>   # JSON additionalContext, SubagentStart

<part> is 1-based; <registered> is how many parts hooks.json registers for the event.
A part past the end prints nothing. If CLAUDE.md needs more parts than are
registered, the last registered part says so, so a rule is never dropped silently.
Exit codes: 0 printed (or nothing to print) · 1 CLAUDE.md unreadable · 2 bad usage.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, 'CLAUDE.md')
HOOK_LIMIT = 10000      # Claude Code's cap per hook output
PART_LIMIT = 9500       # room for the part header
BOUNDARY = re.compile(r'^(## |\d+(-\d+)?\. )')
EVENTS = {'session': 'SessionStart', 'subagent': 'SubagentStart'}


def blocks(text):
    """The text cut before every top-level boundary line; joined back they equal the text."""
    out, current = [], []
    for line in text.splitlines(keepends=True):
        if BOUNDARY.match(line) and current:
            out.append(''.join(current))
            current = []
        current.append(line)
    if current:
        out.append(''.join(current))
    return out


def split_lines(block, limit):
    """A single block longer than the limit is cut at line ends (a line longer than it, hard)."""
    out, current = [], ''
    for line in block.splitlines(keepends=True):
        while len(line) > limit:
            if current:
                out.append(current)
                current = ''
            out.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            out.append(current)
            current = ''
        current += line
    if current:
        out.append(current)
    return out


def parts(text, limit=PART_LIMIT):
    """Greedy packing of whole blocks into parts of at most `limit` characters, in order."""
    out, current = [], ''
    for block in blocks(text):
        pieces = split_lines(block, limit) if len(block) > limit else [block]
        for piece in pieces:
            if current and len(current) + len(piece) > limit:
                out.append(current)
                current = ''
            current += piece
    if current:
        out.append(current)
    return out


def render(all_parts, part, registered):
    """The text for one hook, or '' when that hook has nothing to add."""
    total = len(all_parts)
    if part > total:
        return ''
    text = f'[Global working rules, part {part}/{total} (adyusuf plugin, CLAUDE.md)]\n' + all_parts[part - 1]
    if part == registered and total > registered:
        text += (f'\n[WARNING: the global rules need {total} parts but only {registered} hooks are '
                 f'registered; read the rest in {RULES}]\n')
    return text


def output(mode, all_parts, part, registered):
    """What one hook prints: the plain part (session) or the JSON envelope (subagent)."""
    text = render(all_parts, part, registered)
    if not text or mode == 'session':
        return text
    return json.dumps({'hookSpecificOutput': {'hookEventName': EVENTS[mode], 'additionalContext': text}},
                      ensure_ascii=False)


def mode_parts(text, mode, registered):
    """The parts for one mode, each printed hook output under HOOK_LIMIT.

    JSON escapes every newline and quote, so the subagent envelope is longer than the
    text it carries; its parts are cut smaller until every printed output fits. The
    result depends only on the text and the mode, so every hook of an event agrees."""
    limit = PART_LIMIT
    while True:
        cut = parts(text, limit)
        if all(len(output(mode, cut, n, max(registered, len(cut)))) < HOOK_LIMIT
               for n in range(1, len(cut) + 1)) or limit <= 1000:
            return cut
        limit -= 250


def main(argv):
    if len(argv) != 4 or argv[1] not in EVENTS or not argv[2].isdigit() or not argv[3].isdigit():
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        print('usage: rules-context.py session|subagent <part> <registered>', file=sys.stderr)
        return 2
    mode, part, registered = argv[1], int(argv[2]), int(argv[3])
    if part < 1 or registered < part:
        print(f'rules-context: part {part} is outside 1..{registered}', file=sys.stderr)
        return 2
    try:
        with open(RULES, encoding='utf-8') as handle:
            text = handle.read()
    except OSError as error:
        print(f'rules-context: cannot read the global rules: {error}', file=sys.stderr)
        return 1
    out = output(mode, mode_parts(text, mode, registered), part, registered)
    if out:
        sys.stdout.write(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
