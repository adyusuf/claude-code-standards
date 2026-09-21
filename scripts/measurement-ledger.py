#!/usr/bin/env python3
"""Measurement ledger — ONE ROW PER SESSION / AGENT RUN, derived automatically.

Usage:
    python3 scripts/measurement-ledger.py                 # summarise, write nothing
    python3 scripts/measurement-ledger.py --write         # merge into docs/measurement-ledger.tsv
    python3 scripts/measurement-ledger.py --days 30       # limit the transcripts read (default 30)
    python3 scripts/measurement-ledger.py --ledger PATH   # read/write another file (a trial run, a copy)
    python3 scripts/measurement-ledger.py --nicknames PATH  # project nicknames (default: project-nicknames.tsv beside the ledger)
    python3 scripts/measurement-ledger.py --auto --detach # what the Stop hook runs: incremental, in the background

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
⚠️ --auto is INCREMENTAL and safe to fire on every turn: it reads only transcripts modified since the
   last write, skips when the last write is under --min-interval seconds old (default 600), holds a
   lock so two sessions never write at once, replaces the file atomically, never raises, and with
   --detach returns to the caller immediately. It writes the git-ignored docs/measurement-ledger.tsv of
   the repository the script lives in (a local file: a tracked one would leave the worktree dirty and block promotions).
⚠️ USD is the API LIST price, a proxy for consumption, not a bill (see step-stats.py).
"""
import datetime
import hashlib
import collections
import importlib.util
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))     # resolves a symlink: the ledger lands in the repository the script really lives in
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
    ('step_seconds', rf'(|{STEP}(;{STEP})*)'),
    ('project', r'[a-z][a-z0-9-]{1,30}'),
    ('ended', r'(|\d{4}-\d\d-\d\dT\d\d:\d\d)'),
)
NAMES = [name for name, _ in COLUMNS]

STEP_SECONDS_CAP = 3600
HEADER = (
    "# Measurement ledger — one row per session or agent run. GENERATED: do not edit by hand.\n"
    "# Regenerate: python3 scripts/measurement-ledger.py --write   (merges; rows are never dropped)\n"
    "# started : UTC minute of the first record · kind: session|agent · role: main, the agent role, or other\n"
    "# input/output/cache_write/cache_read : summed token counters · usd : API LIST price (a proxy, not a bill)\n"
    "# cut : how many configuration cuts (scripts/measurement-cuts.tsv) preceded this row — compare rows with\n"
    "#       the SAME cut only (docs/benchmark-method.md)\n"
    "# steps : SDLC steps this transcript RAN (step-stats.py patterns); a step run inside another script is not seen\n"
    "# step_seconds : wall-clock seconds those steps took (tool call -> its result). A command that runs several steps is\n"
    "#       split evenly; a wait for a permission prompt is INCLUDED; a call over 3600 s is dropped as a hang. Empty = not measured\n"
    "# project : a NICKNAME from project-nicknames.tsv (local, git-ignored); unmapped-xxxxxx when no nickname is set. Never a real name\n"
    "# ended : UTC minute of the LAST record of the transcript (the session end; a running session's moves forward). The reports\n"
    "#       charge a row to the local day it ENDED, or to the day it started when this is empty (rows written before it existed)\n"
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


def project_key(path, stats):
    """The project a transcript belongs to: its folder under ~/.claude/projects, without the
    home-directory prefix and without the worktree suffix (a worktree belongs to its project)."""
    root = stats.TRANSCRIPTS.split('**')[0]
    folder = os.path.relpath(path, root).split(os.sep)[0]
    folder = re.sub(r'--claude-worktrees-.*$', '', folder)
    return re.sub(r'^-Users-[^-]+-(?:ClaudeCode-)?', '', folder)


def load_nicknames(path):
    """[(key, nickname)] from a two-column TSV. A key ending in * is a prefix. Local file, never committed."""
    pairs = []
    if path and os.path.exists(path):
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                if line.startswith('#') or '\t' not in line:
                    continue
                key, nick = line.rstrip('\n').split('\t')[:2]
                if key.strip() and nick.strip():
                    pairs.append((key.strip(), nick.strip()))
    return pairs


def nickname_for(key, pairs):
    lowered = key.lower()
    for candidate, nick in pairs:
        if not candidate.endswith('*') and candidate.lower() == lowered:
            return nick
    for candidate, nick in pairs:
        if candidate.endswith('*') and lowered.startswith(candidate[:-1].lower()):
            return nick
    return 'unmapped-' + hashlib.sha256(key.encode()).hexdigest()[:6]


def nickname_problems(pairs, stats):
    """A nickname must be plain, and must not contain a real project name (fail closed)."""
    deny = stats.deny_pattern()
    keys = [k.lower().rstrip('*') for k, _ in pairs if len(k.rstrip('*')) > 3]
    bad = []
    for key, nick in pairs:
        if not re.fullmatch(r'[a-z][a-z0-9-]{1,30}', nick):
            bad.append((nick, 'not a lowercase a-z0-9- word'))
        elif nick.startswith('unmapped-'):
            bad.append((nick, 'reserved prefix'))
        elif (deny is not None and deny.search(nick)) or any(k in nick for k in keys):
            bad.append((nick, 'contains a real project name'))
    return bad


def epoch(text):
    return datetime.datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()


def matched_steps(command, stats):
    """The SDLC steps a shell command runs, judged exactly as step-stats.count_steps judges them."""
    raw = str(command or '')
    if not raw or stats.NOISE_COMMAND.search(raw):
        return []
    command = stats.command_part(raw)
    matched = []
    for name, pattern in stats.STEPS:
        found = re.search(pattern, command, re.I)
        if found and not stats.NOISE_PREFIX.search(command[max(0, found.start() - 60):found.start()]):
            matched.append(name)
    return matched


def row_for(path, kind, role, stats, cuts, nicknames=()):
    """One transcript -> one ledger row (a dict of strings), or None if it has no usage."""
    started = model = None
    requests = 0
    totals = dict(input=0, output=0, cache_write=0, cache_read=0)
    usd = 0.0
    pending, seconds = {}, collections.Counter()
    last = None
    with open(path, errors='ignore') as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except Exception:
                continue
            if record.get('timestamp'):
                started = started or record['timestamp']
                last = record['timestamp']
            message = record.get('message') or {}
            content = message.get('content')
            if isinstance(content, list) and record.get('timestamp'):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                        steps_run = matched_steps((block.get('input') or {}).get('command'), stats)
                        if steps_run:
                            pending[block.get('id')] = (steps_run, epoch(record['timestamp']))
                    elif block.get('type') == 'tool_result' and block.get('tool_use_id') in pending:
                        steps_run, began = pending.pop(block['tool_use_id'])
                        took = epoch(record['timestamp']) - began
                        if 0 <= took <= STEP_SECONDS_CAP:
                            for name in steps_run:
                                seconds[name] += took / len(steps_run)
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
    timed = ';'.join(f'{name}={round(seconds[name])}' for name, _ in stats.STEPS if round(seconds.get(name, 0)) > 0)
    return {
        'id': hash_id(path),
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
        'step_seconds': timed,
        'project': nickname_for(project_key(path, stats), nicknames),
        'ended': datetime.datetime.fromisoformat(last.replace('Z', '+00:00')).astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M'),
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
    """Rows by id. The header line decides which column is which, so a file written with
    fewer columns (before step_seconds, project, ended existed) is still read."""
    rows = {}
    if os.path.exists(path):
        names = None
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                if line.startswith('#') or not line.strip():
                    continue
                cells = line.rstrip('\n').split('\t')
                if line.startswith('id\t'):
                    names = cells
                    continue
                row = dict(zip(names or NAMES, cells))
                for name in NAMES:
                    row.setdefault(name, '')
                if row['id']:
                    rows[row['id']] = row
    return rows


def merge(existing, fresh):
    """Fresh rows replace rows with the same id; nothing else is ever dropped."""
    merged = dict(existing)
    for row in fresh:
        merged[row['id']] = row
    return sorted(merged.values(), key=lambda r: (r['started'], r['id']))


def render(rows):
    return HEADER + '\t'.join(NAMES) + '\n' + ''.join('\t'.join(r[n] for n in NAMES) + '\n' for r in rows)


def build(days, stats, only_newer_than=None, existing=None, nicknames=()):
    """Rows for the transcripts in the window; with `only_newer_than`, only recently modified ones."""
    sessions, agents = stats.collect(days)
    if only_newer_than is not None:
        sessions = [p for p in sessions if os.path.getmtime(p) > only_newer_than]
        agents = [p for p in agents if os.path.getmtime(p) > only_newer_than]
    roles = stats.role_ids(sessions)
    existing = existing or {}
    unresolved_new = [a for a in agents if os.path.basename(a)[6:14] not in roles
                      and hash_id(a) not in existing]
    if only_newer_than is not None and unresolved_new:
        # A new agent whose parent session did not change: find the parent among all sessions.
        roles.update(stats.role_ids(stats.collect(days)[0]))
    cuts = read_cuts()
    rows = []
    for path in sessions:
        rows.append(row_for(path, 'session', None, stats, cuts, nicknames))
    for path in agents:
        role = roles.get(os.path.basename(path)[6:14])
        row = row_for(path, 'agent', role, stats, cuts, nicknames)
        if row and role is None and row['id'] in existing:
            row['role'] = existing[row['id']]['role']          # keep the role an earlier run resolved
        rows.append(row)
    return [r for r in rows if r]


def hash_id(path):
    return hashlib.sha256(os.path.basename(path).encode()).hexdigest()[:10]


def write_atomically(path, text):
    temporary = f'{path}.{os.getpid()}.tmp'
    with open(temporary, 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.replace(temporary, path)


LOCK_STALE_SECONDS = 900


def take_lock(ledger_path, now):
    """True when this process holds the lock; a lock older than LOCK_STALE_SECONDS is a crashed run."""
    lock = ledger_path + '.lock'
    try:
        os.mkdir(lock)
        return True
    except FileExistsError:
        try:
            if now - os.path.getmtime(lock) > LOCK_STALE_SECONDS:
                os.rmdir(lock)
                os.mkdir(lock)
                return True
        except OSError:
            pass
        return False
    except OSError:
        return False


def release_lock(ledger_path):
    try:
        os.rmdir(ledger_path + '.lock')
    except OSError:
        pass


def nicknames_path_for(ledger_path):
    return os.path.join(os.path.dirname(ledger_path), 'project-nicknames.tsv')


def regenerate_report(ledger_path):
    """Rewrite the day-by-project and day-by-role reports beside the ledger."""
    spec = importlib.util.spec_from_file_location('measurement_report', os.path.join(HERE, 'measurement-report.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.write_reports(ledger_path)


def auto_update(ledger_path, stats, days=30, min_interval=600, now=None, nicknames_path=None):
    """Incremental refresh. Returns the number of rows written, or None when it did nothing."""
    now = time.time() if now is None else now
    existed = os.path.exists(ledger_path)
    if existed and now - os.path.getmtime(ledger_path) < min_interval:
        return None
    if not take_lock(ledger_path, now):
        return None
    try:
        existing = read_ledger(ledger_path)
        since = os.path.getmtime(ledger_path) - 300 if existed else None     # 5 min of overlap
        pairs = load_nicknames(nicknames_path or nicknames_path_for(ledger_path))
        if nickname_problems(pairs, stats):
            return None                                    # a nickname that could leak a name: write nothing
        fresh = build(days, stats, only_newer_than=since, existing=existing, nicknames=pairs)
        if not fresh or problems(fresh):
            return None
        write_atomically(ledger_path, render(merge(existing, fresh)))
        try:
            regenerate_report(ledger_path)
        except Exception:
            pass
        return len(fresh)
    finally:
        release_lock(ledger_path)


def detach():
    """Return in the caller at once; the work continues in a child with no terminal."""
    if os.fork() > 0:
        return False
    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    for descriptor in (0, 1, 2):
        os.dup2(devnull, descriptor)
    return True


def main(argv):
    days = int(argv[argv.index('--days') + 1]) if '--days' in argv else 30
    ledger_path = argv[argv.index('--ledger') + 1] if '--ledger' in argv else LEDGER
    if '--auto' in argv:
        if '--detach' in argv and not detach():
            return 0
        try:
            min_interval = int(argv[argv.index('--min-interval') + 1]) if '--min-interval' in argv else 600
            auto_update(ledger_path, load_stats(), days, min_interval)
        except Exception:
            pass                                    # a hook must never break the session
        return 0
    stats = load_stats()
    pairs = load_nicknames(argv[argv.index('--nicknames') + 1] if '--nicknames' in argv else nicknames_path_for(ledger_path))
    leaks = nickname_problems(pairs, stats)
    if leaks:
        sys.exit(f'refusing to write — unsafe nickname(s): {leaks[:5]}')
    fresh = build(days, stats, nicknames=pairs)
    bad = problems(fresh)
    if bad:
        sys.exit(f'refusing to write — {len(bad)} field(s) failed their pattern: {bad[:5]}')
    merged = merge(read_ledger(ledger_path), fresh)
    print(f'{len(fresh)} row(s) read from the last {days} days · ledger would hold {len(merged)} row(s) '
          f'· est. ${sum(float(r["usd"]) for r in merged):,.2f} list price')
    if '--write' in argv:
        write_atomically(ledger_path, render(merged))
        print('written:', ledger_path)
        try:
            print('reports:', ', '.join(regenerate_report(ledger_path)))
        except Exception as error:
            print('report not written:', error)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
