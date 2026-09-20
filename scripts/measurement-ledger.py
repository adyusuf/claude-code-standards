#!/usr/bin/env python3
"""Measurement ledger — ONE ROW PER SESSION / AGENT RUN, derived automatically.

Usage:
    python3 scripts/measurement-ledger.py                 # summarise, write nothing
    python3 scripts/measurement-ledger.py --write         # merge into docs/measurement-ledger.tsv
    python3 scripts/measurement-ledger.py --days 30       # limit the transcripts read (default 30)

Why it exists: docs/measurement-log.md is an AGGREGATE. A number in it cannot be
re-derived or compared later. The ledger keeps the rows it was computed from.

Every column is derived from the transcripts in ~/.claude/projects — there is NO
hand-filled column, so no row can be missing "because nobody wrote it down".

⚠️ Rows are MERGED by id and never dropped: Claude Code deletes old transcripts, the
   ledger keeps the history. A row of a session still running is replaced on the
   next run with its newer totals.
⚠️ Nothing identifying is written. No project name, no path, no command line: the id
   is a hash, the role is a fixed vocabulary, the steps are the names from step-stats.py.
   Every field is checked against a strict pattern before anything is written; a
   value that does not match refuses the whole write (fail closed).
⚠️ USD is the API LIST price, a proxy for consumption, not a bill (see step-stats.py).
"""
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(os.path.dirname(HERE), 'docs', 'measurement-ledger.tsv')
CUTS = os.path.join(HERE, 'measurement-cuts.tsv')

STEP = r'[A-Za-z0-9 /()]+=\d+'
COLUMNS = (
    ('id', r'[0-9a-f]{10}'),
    ('started', r'\d{4}-\d\d-\d\dT\d\d:\d\d'),
    ('kind', r'session|agent'),
    ('role', r'[A-Za-z][A-Za-z0-9:_-]{0,40}'),
    ('model', r'[A-Za-z0-9._-]{1,40}'),
    ('requests', r'\d+'),
    ('input', r'\d+'),
    ('output', r'\d+'),
    ('cache_write', r'\d+'),
    ('cache_read', r'\d+'),
    ('usd', r'\d+\.\d{4}'),
    ('cut', r'\d+'),
    ('steps', rf'(|{STEP}(;{STEP})*)'),
)
NAMES = [name for name, _ in COLUMNS]

HEADER = (
    "# Measurement ledger — one row per session or agent run. GENERATED: do not edit by hand.\n"
    "# Regenerate: python3 scripts/measurement-ledger.py --write   (merges; rows are never dropped)\n"
    "# started : UTC minute of the first record · kind: session|agent · role: main, the agent role, or other\n"
    "# input/output/cache_write/cache_read : summed token counters · usd : API LIST price (a proxy, not a bill)\n"
    "# cut : how many configuration cuts (scripts/measurement-cuts.tsv) preceded this row — compare rows with\n"
    "#       the SAME cut only (docs/benchmark-method.md)\n"
    "# steps : SDLC steps this transcript RAN (step-stats.py patterns); a step run inside another script is not seen\n"
)


def load_stats():
    spec = importlib.util.spec_from_file_location('step_stats', os.path.join(HERE, 'step-stats.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_cuts(path=CUTS):
    """Epoch seconds of every configuration cut, oldest first (the file is local time)."""
    cuts = []
    if os.path.exists(path):
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                if line.startswith('#') or not line.strip():
                    continue
                try:
                    cuts.append(datetime.datetime.fromisoformat(line.split('\t', 1)[0]).timestamp())
                except ValueError:
                    continue
    return sorted(cuts)


def safe_role(role, stats):
    """Only a plain role name may reach the ledger; anything else is `other`."""
    role = stats.ROLE_ALIASES.get(role, role)     # runs recorded under the old Turkish names
    if not role or not re.fullmatch(r'[A-Za-z][A-Za-z0-9:_-]{0,40}', role):
        return 'other'
    deny = stats.deny_pattern()
    return 'other' if deny is not None and deny.search(role) else role


def row_for(path, kind, role, stats, cuts):
    """One transcript -> one ledger row (a dict of strings), or None if it has no usage."""
    started = model = None
    requests = 0
    totals = dict(input=0, output=0, cache_write=0, cache_read=0)
    usd = 0.0
    with open(path, errors='ignore') as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except Exception:
                continue
            if started is None and record.get('timestamp'):
                started = record['timestamp']
            message = record.get('message') or {}
            usage = message.get('usage')
            if not usage:
                continue
            p_in, p_out, cache_rate = stats.price(message.get('model'))
            model = model or message.get('model')
            tokens = dict(input=usage.get('input_tokens', 0) or 0, output=usage.get('output_tokens', 0) or 0,
                          cache_write=usage.get('cache_creation_input_tokens', 0) or 0,
                          cache_read=usage.get('cache_read_input_tokens', 0) or 0)
            for key, value in tokens.items():
                totals[key] += value
            usd += (tokens['input'] * p_in + tokens['output'] * p_out
                    + tokens['cache_write'] * p_in * 1.25 + tokens['cache_read'] * p_in * cache_rate) / 1e6
            requests += 1
    if not requests or not started:
        return None
    when = datetime.datetime.fromisoformat(started.replace('Z', '+00:00'))
    counts, _examples, _dismissed = stats.count_steps([path])
    steps = ';'.join(f'{name}={counts[name]}' for name, _ in stats.STEPS if counts.get(name))
    return {
        'id': hashlib.sha256(os.path.basename(path).encode()).hexdigest()[:10],
        'started': when.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M'),
        'kind': kind,
        'role': 'main' if kind == 'session' else safe_role(role, stats),
        'model': re.sub(r'[^A-Za-z0-9._-]', '', model or 'unknown')[:40] or 'unknown',
        'requests': str(requests),
        'input': str(totals['input']), 'output': str(totals['output']),
        'cache_write': str(totals['cache_write']), 'cache_read': str(totals['cache_read']),
        'usd': f'{usd:.4f}',
        'cut': str(sum(1 for cut in cuts if cut < when.timestamp())),
        'steps': steps,
    }


def problems(rows):
    """Every field must match its column pattern. Returns the offending (id, column) pairs."""
    bad = []
    for row in rows:
        for name, pattern in COLUMNS:
            if not re.fullmatch(pattern, row.get(name, '')):
                bad.append((row.get('id', '?'), name))
    return bad


def read_ledger(path=LEDGER):
    rows = {}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                if line.startswith('#') or not line.strip() or line.startswith('id\t'):
                    continue
                cells = line.rstrip('\n').split('\t')
                if len(cells) == len(NAMES):
                    rows[cells[0]] = dict(zip(NAMES, cells))
    return rows


def merge(existing, fresh):
    """Fresh rows replace rows with the same id; nothing else is ever dropped."""
    merged = dict(existing)
    for row in fresh:
        merged[row['id']] = row
    return sorted(merged.values(), key=lambda r: (r['started'], r['id']))


def render(rows):
    return HEADER + '\t'.join(NAMES) + '\n' + ''.join('\t'.join(r[n] for n in NAMES) + '\n' for r in rows)


def build(days, stats):
    sessions, agents = stats.collect(days)
    roles = stats.role_ids(sessions)
    cuts = read_cuts()
    rows = []
    for path in sessions:
        rows.append(row_for(path, 'session', None, stats, cuts))
    for path in agents:
        rows.append(row_for(path, 'agent', roles.get(os.path.basename(path)[6:14]), stats, cuts))
    return [r for r in rows if r]


def main(argv):
    days = int(argv[argv.index('--days') + 1]) if '--days' in argv else 30
    stats = load_stats()
    fresh = build(days, stats)
    bad = problems(fresh)
    if bad:
        sys.exit(f'refusing to write — {len(bad)} field(s) failed their pattern: {bad[:5]}')
    merged = merge(read_ledger(), fresh)
    print(f'{len(fresh)} row(s) read from the last {days} days · ledger would hold {len(merged)} row(s) '
          f'· est. ${sum(float(r["usd"]) for r in merged):,.2f} list price')
    if '--write' in argv:
        with open(LEDGER, 'w', encoding='utf-8') as handle:
            handle.write(render(merged))
        print('written:', LEDGER)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
