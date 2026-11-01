"""The adyusuf configuration's layers on disk: where each file is, how a file is read, merged and written.

Split out of adyusuf_config.py so no file passes 300 lines (rule #9); adyusuf_config.py re-exports every name here.
Layers, lowest first: the shipped defaults < the user's file < the project's file < the session's own layer.
"""
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import tempfile

try:
    import fcntl
except ImportError:      # Windows: no advisory lock, the atomic replace below still never leaves a half-written file
    fcntl = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adyusuf_session as sessions  # noqa: E402
from adyusuf_schema import DEFAULTS_FILE, RETIRED_KEYS, SCHEMA, SPECS  # noqa: E402

class ConfigError(Exception):
    """A usage error (exit 2) or an unreadable file (exit 1)."""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def user_file():
    return os.environ.get('ADYUSUF_CONFIG_USER') or os.path.join(os.path.expanduser('~'), '.claude', 'adyusuf.json')


def project_file():
    try:
        top = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        top = os.getcwd()
    return os.path.join(top, '.claude', 'adyusuf.json')


def flatten(tree, prefix=''):
    flat = {}
    for key, value in tree.items():
        name = prefix + key
        if isinstance(value, dict):
            flat.update(flatten(value, name + '.'))
        else:
            flat[name] = value
    return flat


def nest(flat):
    tree = {}
    for name in sorted(flat):
        node = tree
        parts = name.split('.')
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = flat[name]
    return tree


def check(key, value):
    """The value as the schema wants it, or ConfigError (exit 2)."""
    spec = SPECS.get(key)
    if spec is None:
        raise ConfigError("unknown setting '%s' (see: adyusuf_config.py schema)" % key)
    if spec['type'] == 'bool':
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ('true', 'yes', 'y', '1', 'on'):
            return True
        if text in ('false', 'no', 'n', '0', 'off'):
            return False
        raise ConfigError("'%s' is a yes/no setting, got %r" % (key, value))
    text = str(value).strip()
    for option in spec['options']:
        if text.lower() == option.lower():
            return option
    raise ConfigError("'%s' must be one of %s, got %r" % (key, '/'.join(spec['options']), value))


def read_layer(path, keep_unknown=False):
    """(flat values, problem). A missing file is an empty layer; an unreadable or invalid one is reported.

    A key this schema does not know was written by a NEWER plugin (forward compatibility, rule #11): it is left out of
    the values, never a problem, so one new key does not throw away the whole layer - an older copy once read a user's
    file holding `coverage_before_push.dev` as empty and answered push.prod = yes against the user's no (found by QA
    30/10/2026). `keep_unknown` hands such keys back unchecked, so a write keeps what the newer plugin wrote."""
    if not os.path.exists(path):
        return {}, None
    try:
        with open(path, encoding='utf-8') as handle:
            tree = json.load(handle)
        if not isinstance(tree, dict):
            raise ValueError('the top level is not an object')
        flat = flatten(tree)
        values = {}
        for key, value in flat.items():
            if key in RETIRED_KEYS:
                continue
            if key not in SPECS:
                if keep_unknown:
                    values[key] = value
                continue
            values[key] = check(key, value)
        return values, None
    except (OSError, ValueError, ConfigError) as error:
        return {}, '%s: %s' % (path, error)


def load(user_path=None, session=None, project=True):
    """(effective {key: (value, source)}, problems [str]). `user_path` replaces the user's file (the installer's --home);
    `session` adds that session's layer on top (an unusable id adds nothing). `project=False` leaves the project's layer out."""
    problems = []
    defaults, problem = read_layer(DEFAULTS_FILE)
    if problem:
        problems.append(problem)
    effective = {spec['key']: (defaults.get(spec['key']), 'default') for spec in SCHEMA}
    layers = [('user', user_path or user_file())] + ([('project', project_file())] if project else [])
    if sessions.valid(session):
        layers.append(('session', sessions.session_file(session)))
    for source, path in layers:
        values, problem = read_layer(path)
        if problem:
            problems.append(problem)
        for key, value in values.items():
            effective[key] = (value, source)
    return effective, problems


@contextlib.contextmanager
def locked(path):
    """One writer at a time per configuration file (clicks in the rail boxes arrive in quick succession). The lock file
    lives in the temp folder, keyed by the path, so no `.lock` lands in ~/.claude or in a project's committed `.claude/`."""
    name = 'adyusuf-config-%s.lock' % hashlib.sha1(os.path.abspath(path).encode('utf-8')).hexdigest()[:16]
    with open(os.path.join(tempfile.gettempdir(), name), 'a') as handle:
        if fcntl:
            fcntl.flock(handle, fcntl.LOCK_EX)
        yield                                    # closing the handle releases the lock


def write_layer(path, changes, removals=()):
    """Merge `changes` into the layer's file and write it back. Refuses to overwrite an unreadable file. The read, the
    change and the write happen under a lock, and the file is replaced atomically: a reader never sees it half-written."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked(path):
        current, problem = read_layer(path, keep_unknown=True)
        if problem:
            raise ConfigError('refusing to overwrite an unreadable configuration file - ' + problem, 1)
        current.update(changes)
        for key in removals:
            current.pop(key, None)
        temp = '%s.%d.tmp' % (path, os.getpid())
        try:
            with open(temp, 'w', encoding='utf-8') as handle:
                json.dump(nest(current), handle, indent=2)
                handle.write('\n')
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.remove(temp)
