#!/usr/bin/env python3
"""This session's status table, which the pane's Status box shows (user decision 01/11/2026).

The table is the one `standards/00-working-method.md` §10 asks for in a reply during a long run: the item, its state, the
measured figure with the signal it was read from, what it waits on; plus what runs now and what runs next. Claude writes
it at each step, and a background run (a gate, a promotion) may write its own steps; the box re-reads the file after every
tool call and when its modification time changes. Every figure is MEASURED: the script stores what it is given and
invents nothing.

The file is `<session id>.json` in ADYUSUF_STATUS_DIR (default `~/.claude/adyusuf-status`). Files nobody has written to
for KEEP_DAYS are removed whenever one is written.

Usage:
    adyusuf_status.py --session ID now TEXT                  what runs now ('' clears it)
    adyusuf_status.py --session ID next TEXT                 what runs next ('' clears it)
    adyusuf_status.py --session ID row ITEM STATE FIGURE WAITING
                                                             add the row named ITEM, or replace it in place
    adyusuf_status.py --session ID drop ITEM                 remove the row named ITEM
    adyusuf_status.py --session ID clear                     empty the table
    adyusuf_status.py --session ID show [--json]             print it
Exit codes: 0 done, 2 refused (an unusable session id, a missing argument, an unreadable file).
"""
import argparse
import json
import os
import sys
import tempfile
import time

KEEP_DAYS = 14
MAX_ID = 100
MAX_TEXT = 300
EMPTY = {'now': '', 'next': '', 'rows': [], 'updated': ''}


def status_dir():
    return os.environ.get('ADYUSUF_STATUS_DIR') or os.path.join(os.path.expanduser('~'), '.claude', 'adyusuf-status')


def valid(session):
    """A session id becomes a file name, so it may hold only letters, digits, '-' and '_'."""
    return isinstance(session, str) and 0 < len(session) <= MAX_ID and all(ch.isalnum() or ch in '-_' for ch in session)


def status_file(session):
    if not valid(session):
        raise ValueError('not a usable session id: %r' % (session,))
    return os.path.join(status_dir(), session + '.json')


def clip(text):
    """One line of at most MAX_TEXT characters: the box draws one line per field."""
    flat = ' '.join(str(text).split())
    return flat if len(flat) <= MAX_TEXT else flat[:MAX_TEXT - 1] + '…'


def load(session):
    path = status_file(session)
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return dict(EMPTY, rows=[])
    if not isinstance(data, dict) or not isinstance(data.get('rows', []), list):
        raise ValueError('%s: not a status table' % path)
    return {'now': str(data.get('now', '')), 'next': str(data.get('next', '')), 'rows': list(data.get('rows', [])),
            'updated': str(data.get('updated', ''))}


def save(session, data, now=None):
    """Write atomically (a temporary file renamed over the old one), so the box never reads half a file."""
    path = status_file(session)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = dict(data, updated=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() if now is None else now)))
    fd, temp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.status-', suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    os.replace(temp, path)
    prune()
    return data


def prune(now=None, keep_days=KEEP_DAYS):
    """Remove status files nobody has written to for `keep_days`. Never raises: a leftover file costs nothing."""
    limit = (time.time() if now is None else now) - keep_days * 86400
    try:
        names = os.listdir(status_dir())
    except OSError:
        return 0
    removed = 0
    for name in names:
        path = os.path.join(status_dir(), name)
        try:
            if name.endswith('.json') and os.path.getmtime(path) < limit:
                os.remove(path)
                removed += 1
        except OSError:
            continue
    return removed


def put_row(data, item, state, figure, waiting):
    row = {'item': clip(item), 'state': clip(state), 'figure': clip(figure), 'waiting': clip(waiting)}
    rows = [dict(one) for one in data['rows']]
    at = next((i for i, one in enumerate(rows) if one.get('item') == row['item']), None)
    if at is None:
        rows.append(row)
    else:
        rows[at] = row
    return dict(data, rows=rows)


def drop_row(data, item):
    return dict(data, rows=[one for one in data['rows'] if one.get('item') != clip(item)])


def render(data):
    lines = []
    if data['now']:
        lines.append('now:  ' + data['now'])
    if data['next']:
        lines.append('next: ' + data['next'])
    for row in data['rows']:
        lines.append(' | '.join(row.get(key, '') for key in ('item', 'state', 'figure', 'waiting')))
    return '\n'.join(lines) if lines else 'nothing running'


def main(argv=None):
    parser = argparse.ArgumentParser(description='This session\'s status table for the pane\'s Status box.')
    parser.add_argument('--session', required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('now', 'next'):
        sub.add_parser(name).add_argument('text')
    row = sub.add_parser('row')
    for name in ('item', 'state', 'figure', 'waiting'):
        row.add_argument(name)
    sub.add_parser('drop').add_argument('item')
    sub.add_parser('clear')
    sub.add_parser('show').add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        data = load(args.session)
    except (ValueError, OSError) as error:
        print('adyusuf_status: %s' % error, file=sys.stderr)
        return 2
    if args.action == 'show':
        print(json.dumps(data, ensure_ascii=False) if args.json else render(data))
        return 0
    if args.action in ('now', 'next'):
        data = dict(data, **{args.action: clip(args.text)})
    elif args.action == 'row':
        data = put_row(data, args.item, args.state, args.figure, args.waiting)
    elif args.action == 'drop':
        data = drop_row(data, args.item)
    else:
        data = dict(EMPTY, rows=[])
    try:
        save(args.session, data)
    except OSError as error:
        print('adyusuf_status: %s' % error, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
