#!/usr/bin/env python3
"""This session's status table, which the pane's Status box shows (user decision 01/11/2026).

The table is the one `standards/00-working-method.md` §10 asks for in a reply during a long run: the item, its state, the
measured figure with the signal it was read from, what it waits on; plus what runs now and what runs next. Claude writes
it at each step, and a background run (a gate, a promotion) may write its own steps; the box re-reads the file after every
tool call and when its modification time changes. Every figure is MEASURED: the script stores what it is given and
invents nothing.

The file is `<session id>.json` in ADYUSUF_STATUS_DIR (an absolute path; default `~/.claude/adyusuf-status`). Writers take
a lock around read-modify-write, so Claude and a background run never lose each other's rows. Status files nobody has
written to for KEEP_DAYS are removed whenever one is written; a file that is not a status table is never touched.

Usage:
    adyusuf_status.py --session ID now TEXT                  what runs now ('' clears it)
    adyusuf_status.py --session ID next TEXT                 what runs next ('' clears it)
    adyusuf_status.py --session ID row ITEM STATE FIGURE WAITING
                                                             add the row named ITEM, or replace it in place
    adyusuf_status.py --session ID drop ITEM                 remove the row named ITEM
    adyusuf_status.py --session ID clear                     empty the table (also replaces a corrupt file)
    adyusuf_status.py --session ID show [--json]             print it
    adyusuf_status.py hook session|prompt|stop               the plugin's hooks (stdin: the hook payload): a session
                                                             starts "waiting for you", the user's message sets `now` to
                                                             its first line, the end of a turn waits for the user or for
                                                             background work; the rows stay, never fails a session
Exit codes: 0 done, 2 refused (an unusable session id or folder, an unreadable file, a failed write).
"""
import argparse
import contextlib
import json
import os
import re
import sys
import tempfile
import time

try:
    import fcntl
except ImportError:  # Windows: no advisory lock; one writer at a time is then the caller's duty (documented in §10d).
    fcntl = None

KEEP_DAYS = 14
MAX_ID = 100
MAX_TEXT = 300
MAX_ROWS = 50
FIELDS = ('item', 'state', 'figure', 'waiting')
EMPTY = {'now': '', 'next': '', 'rows': [], 'updated': ''}
SESSION_ID = re.compile(r'^[A-Za-z0-9_-]{1,%d}$' % MAX_ID)
STATUS_NAME = re.compile(r'^[A-Za-z0-9_-]{1,%d}\.json$' % MAX_ID)
CONTROL = re.compile('[\x00-\x1f\x7f-\x9f]')


class StatusError(Exception):
    """A refusal the command line reports with exit code 2."""


def status_dir():
    chosen = os.environ.get('ADYUSUF_STATUS_DIR')
    if chosen and not os.path.isabs(chosen):
        raise StatusError('ADYUSUF_STATUS_DIR must be an absolute path (the pane reads it from another directory): %r' % chosen)
    return chosen or os.path.join(os.path.expanduser('~'), '.claude', 'adyusuf-status')


def valid(session):
    """A session id becomes a file name, so it may hold only ASCII letters, digits, '-' and '_'."""
    return isinstance(session, str) and SESSION_ID.match(session) is not None


def status_file(session):
    if not valid(session):
        raise StatusError('not a usable session id: %r' % (session,))
    return os.path.join(status_dir(), session + '.json')


def clip(text):
    """One line of at most MAX_TEXT characters with no control characters: the box draws one line per field."""
    flat = ' '.join(CONTROL.sub(' ', '' if text is None else str(text)).split())
    return flat if len(flat) <= MAX_TEXT else flat[:MAX_TEXT - 1] + '…'


def is_table(data):
    return isinstance(data, dict) and isinstance(data.get('rows', []), list)


def normalise(data):
    """Keep only what a status table holds: string fields, rows that are objects, at most MAX_ROWS of them."""
    rows = [{key: clip(row.get(key)) for key in FIELDS} for row in data.get('rows', []) if isinstance(row, dict)]
    return {'now': clip(data.get('now')), 'next': clip(data.get('next')), 'rows': rows[-MAX_ROWS:],
            'updated': clip(data.get('updated'))}


def load(session):
    path = status_file(session)
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return dict(EMPTY, rows=[])
    except (OSError, ValueError) as error:
        raise StatusError('%s: unreadable (%s); `clear` replaces it' % (path, error))
    if not is_table(data):
        raise StatusError('%s: not a status table; `clear` replaces it' % path)
    return normalise(data)


@contextlib.contextmanager
def locked(session):
    """Holds an exclusive lock on `<session>.lock` for one read-modify-write, so concurrent writers keep each other's rows."""
    path = status_file(session)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fcntl is None:
        yield
        return
    with open(path[:-len('.json')] + '.lock', 'a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def save(session, data, now=None):
    """Write atomically (a temporary file renamed over the old one), so the box never reads half a file."""
    path = status_file(session)
    data = dict(normalise(data), updated=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() if now is None else now)))
    fd, temp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.status-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
        os.replace(temp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(temp)
        raise
    prune()
    return data


def prune(now=None, keep_days=KEEP_DAYS):
    """Remove status files (and their locks) nobody has written to for `keep_days`. Never raises.

    Only a file named like a session's and holding a status table goes: the folder may be one the user chose
    (ADYUSUF_STATUS_DIR), where other JSON files must survive.
    """
    limit = (time.time() if now is None else now) - keep_days * 86400
    try:
        folder = status_dir()
        names = os.listdir(folder)
    except (OSError, StatusError):
        return 0
    removed = 0
    for name in names:
        path = os.path.join(folder, name)
        try:
            if not STATUS_NAME.match(name) or os.path.getmtime(path) >= limit:
                continue
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            if not (is_table(data) and 'updated' in data):
                continue
            os.remove(path)
            with contextlib.suppress(OSError):
                os.remove(path[:-len('.json')] + '.lock')
            removed += 1
        except (OSError, ValueError):
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
        lines.append(' | '.join(row.get(key, '') for key in FIELDS))
    return '\n'.join(lines) if lines else 'nothing running'


def change(args):
    """One write under the lock. `clear` does not read the old file, so it also replaces a corrupt one."""
    with locked(args.session):
        data = dict(EMPTY, rows=[]) if args.action == 'clear' else load(args.session)
        if args.action in ('now', 'next'):
            data = dict(data, **{args.action: clip(args.text)})
        elif args.action == 'row':
            data = put_row(data, args.item, args.state, args.figure, args.waiting)
        elif args.action == 'drop':
            data = drop_row(data, args.item)
        save(args.session, data)


# What `now` says when a session starts or a turn ends: it waits for the user, or for its own background work.
WAITING = 'waiting for you'
WAITING_BACKGROUND = 'waiting for background work'
# The turns a person starts: a system-started turn (a task notification, a wake-up) must not replace the user's task.
USER_SOURCES = (None, 'user', 'sdk')


def hook_text(event, payload):
    """What `now` becomes for one hook payload, or None to leave the table alone."""
    if event == 'prompt':
        if payload.get('source') not in USER_SOURCES:
            return None
        return 'working on: ' + str(payload.get('prompt') or '').strip().split('\n')[0]
    if event == 'stop':
        return WAITING_BACKGROUND if payload.get('background_tasks') or payload.get('session_crons') else WAITING
    return WAITING if event == 'session' else None


def hook(event, payload_text):
    """The plugin's hooks keep every session's box alive without Claude (user decision 02/11/2026): `now` follows the
    session start, the user's messages and the turns' ends; `next` empties and the rows stay. Never raises."""
    try:
        payload = json.loads(payload_text)
        session = str(payload.get('session_id') or '')
        text = hook_text(event, payload) if valid(session) else None
        if text is None:
            return
        with locked(session):
            try:
                data = load(session)
            except StatusError:
                data = dict(EMPTY, rows=[])          # a corrupt file is replaced, as `clear` would
            save(session, dict(data, now=clip(text), next=''))
    except (ValueError, AttributeError, OSError, StatusError):
        return


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['hook']:
        try:      # bytes, decoded here: a hook must not fail on the platform's encoding, a closed stdin or a terminal
            raw = b'' if sys.stdin is None or sys.stdin.isatty() else sys.stdin.buffer.read()
        except (OSError, ValueError, AttributeError):
            raw = b''
        hook(argv[1] if len(argv) > 1 else '', raw.decode('utf-8', errors='replace'))
        return 0
    parser = argparse.ArgumentParser(description='This session\'s status table for the pane\'s Status box.')
    parser.add_argument('--session', required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('now', 'next'):
        sub.add_parser(name).add_argument('text')
    row = sub.add_parser('row')
    for name in FIELDS:
        row.add_argument(name)
    sub.add_parser('drop').add_argument('item')
    sub.add_parser('clear')
    sub.add_parser('show').add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'show':
            data = load(args.session)
            print(json.dumps(data, ensure_ascii=False) if args.json else render(data))
        else:
            change(args)
    except (StatusError, OSError) as error:
        print('adyusuf_status: %s' % error, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
