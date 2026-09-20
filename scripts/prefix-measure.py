#!/usr/bin/env python3
"""MEASURES the FIXED PREFIX of sessions (system prompt + tool/skill listings + CLAUDE.md).

Usage:  python3 ~/.claude/scripts/prefix-measure.py ["YYYY-MM-DD HH:MM"]
        With a cut timestamp, sessions that started AFTER that moment are marked.

WHY IT EXISTS: the fixed prefix is re-read on every request; in one measurement it
was 18% of the total spend. Disabling plugins or shrinking CLAUDE.md lowers that
number, but the effect is visible ONLY IN A NEW SESSION — an open session takes its
configuration snapshot at start-up (verified by measurement: before and after the
change, the agent prefix inside the same session was byte-for-byte identical).

⚠️ Sorting is by SESSION START, not by file timestamp: the most recently WRITTEN
transcript is usually an older session and is easily mistaken for "after".
"""
import glob, json, os, sys, datetime

cut = None
if len(sys.argv) > 1:
    cut = datetime.datetime.fromisoformat(' '.join(sys.argv[1:])).timestamp()

rows = []
for path in glob.glob(os.path.expanduser('~/.claude/projects/**/*.jsonl'), recursive=True):
    if os.path.basename(path).startswith('agent-'):
        continue
    first = started = None
    for line in open(path, errors='ignore'):
        try:
            record = json.loads(line)
        except Exception:
            continue
        if started is None and record.get('timestamp'):
            started = record['timestamp']
        usage = (record.get('message') or {}).get('usage')
        if usage:
            first = sum(usage.get(key, 0) or 0 for key in
                        ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
            break
    if first and started:
        when = datetime.datetime.fromisoformat(started.replace('Z', '+00:00')).timestamp()
        rows.append((when, os.path.basename(path)[:8], first))

rows.sort(reverse=True)
print("the last 10 sessions, by session start:\n")
for when, name, prefix in rows[:10]:
    marker = ' ← after the cut' if cut and when > cut else ''
    print(f"  {datetime.datetime.fromtimestamp(when):%d/%m %H:%M}  {name}  {prefix:>8,} tokens{marker}")
if cut:
    after = [prefix for when, _name, prefix in rows if when > cut]
    if after:
        print(f"\nsessions started after the cut: {len(after)} · median prefix {sorted(after)[len(after)//2]:,} tokens")
    else:
        print("\nsessions started after the cut: 0 → a new session is needed")
