"""The session layer of the adyusuf configuration: settings changed for ONE session only.

The rail boxes write here (`adyusuf_config.py set --session <id> ...`), so a click never changes what the next session
starts with: a new session has a new id, finds no file, and loads the saved defaults (the user's file, then the
project's). The file is one more layer on top of those, stored as `<session id>.json` in `ADYUSUF_SESSION_DIR`
(default `~/.claude/adyusuf-session`). A resumed session keeps its id and so its file; `/clear` starts a new id.
Files older than KEEP_DAYS are removed whenever a session file is written.
"""
import os
import time

KEEP_DAYS = 14
MAX_ID = 100


def session_dir():
    return os.environ.get('ADYUSUF_SESSION_DIR') or os.path.join(os.path.expanduser('~'), '.claude', 'adyusuf-session')


def valid(session):
    """A session id becomes a file name, so it may hold only letters, digits, '-' and '_'."""
    return isinstance(session, str) and 0 < len(session) <= MAX_ID and all(ch.isalnum() or ch in '-_' for ch in session)


def session_file(session):
    if not valid(session):
        raise ValueError('not a usable session id: %r' % (session,))
    return os.path.join(session_dir(), session + '.json')


def prune(now=None, keep_days=KEEP_DAYS):
    """Remove session files nobody has written to for `keep_days`. Never raises: a leftover file costs nothing."""
    limit = (time.time() if now is None else now) - keep_days * 86400
    try:
        names = os.listdir(session_dir())
    except OSError:
        return 0
    removed = 0
    for name in names:
        path = os.path.join(session_dir(), name)
        try:
            if name.endswith('.json') and os.path.getmtime(path) < limit:
                os.remove(path)
                removed += 1
        except OSError:
            continue
    return removed
