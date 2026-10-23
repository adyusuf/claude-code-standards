#!/usr/bin/env python3
"""The adyusuf configuration: defaults instead of questions.

    adyusuf_config.py show [--json]              every setting, its value and where the value comes from
    adyusuf_config.py get <key>                  one effective value
    adyusuf_config.py set <key> <value> [--project|--session ID]   change one setting (default scope: the user's)
    adyusuf_config.py unset <key> [--project|--session ID]         fall back to the next layer
    adyusuf_config.py apply <file|-> [--project|--session ID]      set many at once from a JSON object {"push.prod": false, ...}
    (--session ID: show, get, agents and context also read that session's layer)
    adyusuf_config.py schema                     the keys with type, options and label
    adyusuf_config.py agents [--json] [--all]    the active agents and the model each one runs on (--all: inactive too)
    adyusuf_config.py reset-agents [--project]   remove every agents.<role>.* setting (back to the mode's own set)
    adyusuf_config.py context [--stdin]          the block the SessionStart hook prints (--stdin: take the session id from the hook payload)
    adyusuf_config.py notify <event>             hook: tells the running session when a setting changed (stdin: the payload)

Layers, lowest first: defaults/adyusuf.json (shipped with the plugin) < ~/.claude/adyusuf.json (the user's own
defaults) < <project>/.claude/adyusuf.json (committed, like .claude/mode) < the session's own layer (adyusuf_session.py:
what the rail boxes change; gone with the session). The user changes them with the
`adyusuf:config` skill; Claude never asks what a setting already answers (global rule #34).

Keys are dotted (`push.prod`); files hold them nested. A key is validated against SCHEMA, a file that does not
parse is reported and ignored (the layer below wins) - the SessionStart hook must never fail a session.
Exit codes: 0 done · 1 a configuration file is unreadable (set/unset/apply refuse to overwrite it) ·
2 bad usage, unknown key or invalid value (nothing is written).
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULTS_FILE = os.path.join(ROOT, 'defaults', 'adyusuf.json')
TARGETS = ('dev', 'test', 'prod')
E2E_STAGES = (('dev', 'test'), ('test', 'prod'))      # (the environment e2e runs on, the target about to be deployed)
MODES = ('A', 'B', 'C', 'D', 'E')
MODELS = ('keep', 'sonnet', 'haiku', 'fable')
# Settings that no longer exist. A user's file written before they were retired still holds them: they are skipped
# on read, so one stale key never makes the whole layer invalid (and the next write drops them).
RETIRED_KEYS = (('monitor.connect', 'monitor.message_format')
                + tuple('run_before_push.%s.%s' % (t, gate) for t in TARGETS for gate in ('unit', 'e2e'))
                + tuple('%s.%s' % (group, t) for group in ('ci_before_merge', 'e2e_after_deploy') for t in TARGETS))


def _bool(key, label):
    return {'key': key, 'type': 'bool', 'label': label}


def _enum(key, label, options):
    return {'key': key, 'type': 'enum', 'label': label, 'options': list(options)}


# The role sets of the modes (modes/README.md; the test pins them to the agent files and the mode documents).
# Each mode's set contains the one before it (B in C in D); E is D with parallel Workflow agents.
B_ROLES = ('analyst', 'test-writer', 'doc-writer')
C_ROLES = ('product-manager', 'analyst', 'architect', 'designer', 'developer', 'test-writer', 'qa', 'devops', 'doc-writer')
D_ROLES = C_ROLES + ('data', 'observability', 'security', 'coverage-auditor', 'e2e-writer')
MODE_ROLES = {'A': (), 'B': B_ROLES, 'C': C_ROLES, 'D': D_ROLES, 'E': D_ROLES}
AGENTS_DIR = os.path.join(ROOT, 'agents')


POD_FORMATS = ('short', 'full')
AGENT_STATES = ('auto', 'on', 'off')
AGENT_MODELS = ('default', 'opus', 'sonnet', 'haiku', 'fable')


# The one definition of what can be set: order is the display order. `group` titles the sections of `show`.
SCHEMA = (
    [dict(_enum('mode', 'Working mode', MODES), group='Session'),
     dict(_enum('mode_model', 'Model that replaces Opus in the agents', MODELS), group='Session'),
     dict(_bool('pod.connect', 'Connect to pod'), group='Pod'),
     dict(_enum('pod.message_format', 'Message format', POD_FORMATS), group='Pod'),
     dict(_bool('write.unit_tests', 'Write unit tests'), group='Writing'),
     dict(_bool('write.e2e', 'Write e2e specs'), group='Writing')]
    + [dict(_bool('merge.' + t, 'Merge into ' + t), group='Merge') for t in TARGETS]
    + [dict(_bool('push.' + t, 'Push ' + t), group='Push') for t in TARGETS]
    + [dict(_bool('gates_before_push.' + t, 'Run gates before pushing %s' % t), group='Gates before a push') for t in TARGETS]
    + [dict(_bool('ci_after_push.' + t, 'Run CI after pushing %s' % t), group='CI after push') for t in TARGETS]
    + [dict(_bool('e2e_before_deploy.' + after, 'Run e2e on %s before deploying %s' % (on, after)), group='E2E before deploy')
       for on, after in E2E_STAGES]
    + [dict(_enum('agents.%s.%s' % (role, field), '%s: %s' % (role, field), options), group='Agents')
       for role in D_ROLES for field, options in (('enabled', AGENT_STATES), ('model', AGENT_MODELS))])
SPECS = {spec['key']: spec for spec in SCHEMA}


def defined_model(role):
    """The model an agent file names (its `model:` front-matter line), or 'inherit'."""
    try:
        with open(os.path.join(AGENTS_DIR, role + '.md'), encoding='utf-8') as handle:
            for line in handle:
                if line.startswith('model:'):
                    return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return 'inherit'


def effective_model(defined, override):
    """Only the Opus agents move to the mode's override; `keep` (and no override) leaves every agent as defined."""
    return override if defined == 'opus' and override not in ('keep', 'opus', None) else defined


def agents(values, include_inactive=False):
    """One dict per role: defined model, the model it runs on, whether it is active, and the settings behind that.

    A role is active when `agents.<role>.enabled` is `on`, or `auto` and the mode's set holds it; mode A runs none
    whatever the settings say. `agents.<role>.model` other than `default` beats the mode's Opus override."""
    mode, override = values['mode'], values['mode_model']
    rows = []
    for role in D_ROLES:
        in_mode = role in MODE_ROLES.get(mode, ())
        enabled = values.get('agents.%s.enabled' % role, 'auto')
        active = False if mode == 'A' else (in_mode if enabled == 'auto' else enabled == 'on')
        defined = defined_model(role)
        chosen = values.get('agents.%s.model' % role, 'default')
        runs_on = chosen if chosen != 'default' else effective_model(defined, override)
        if active or include_inactive:
            rows.append({'role': role, 'defined': defined, 'runs_on': runs_on, 'active': active, 'in_mode': in_mode,
                         'enabled': enabled, 'model': chosen})
    return rows


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


def read_layer(path):
    """(flat values, problem). A missing file is an empty layer; an unreadable or invalid one is reported."""
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
            values[key] = check(key, value)
        return values, None
    except (OSError, ValueError, ConfigError) as error:
        return {}, '%s: %s' % (path, error)


def load(user_path=None, session=None):
    """(effective {key: (value, source)}, problems [str]). `user_path` replaces the user's file (the installer's --home);
    `session` adds that session's layer on top (an unusable id adds nothing)."""
    problems = []
    defaults, problem = read_layer(DEFAULTS_FILE)
    if problem:
        problems.append(problem)
    effective = {spec['key']: (defaults.get(spec['key']), 'default') for spec in SCHEMA}
    layers = [('user', user_path or user_file()), ('project', project_file())]
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
        current, problem = read_layer(path)
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


def shown(value):
    return 'yes' if value is True else 'no' if value is False else str(value)


def render(effective, problems):
    lines = []
    group = None
    for spec in SCHEMA:
        if spec['group'] != group:
            group = spec['group']
            lines.append(group)
        value, source = effective[spec['key']]
        lines.append('  %-34s %-8s %s' % (spec['key'], shown(value), '' if source == 'default' else '(%s)' % source))
    lines.extend('! ' + problem for problem in problems)
    return '\n'.join(lines)


def context(effective, problems, session=None):
    """The compact block a session starts with: the effective values, what they mean, how to change them."""
    value = lambda key: effective[key][0]  # noqa: E731
    steps = []
    for target in TARGETS:
        steps.append('%s: merge %s, gates before push %s, push %s, CI after push %s' % (
            target, shown(value('merge.' + target)), shown(value('gates_before_push.' + target)),
            shown(value('push.' + target)), shown(value('ci_after_push.' + target))))
    steps.append('e2e before deploy: ' + ', '.join(
        'on %s before deploying %s %s' % (on, after, shown(value('e2e_before_deploy.' + after))) for on, after in E2E_STAGES))
    lines = ['adyusuf configuration (effective; global rule #34 - follow it, do not ask what it answers):',
             '  mode %s, model for the Opus agents: %s' % (value('mode'), value('mode_model')),
             '  pod: connect %s, message format %s (stored only; nothing acts on it)' % (
                 shown(value('pod.connect')), value('pod.message_format')),
             '  write unit tests: %s, write e2e: %s' % (shown(value('write.unit_tests')), shown(value('write.e2e')))]
    active = agents({k: v[0] for k, v in effective.items()})
    lines.append('  agents: %s' % (', '.join('%s (%s)' % (row['role'], row['runs_on']) for row in active) or 'none'))
    lines.extend('  ' + step for step in steps)
    lines.append('  change it with the adyusuf:config skill; the mode may also be set per session or per project.')
    if sessions.valid(session):
        lines.append('  this session is %s: what the rail boxes change applies to it only (adyusuf_config.py set --session %s '
                     '<key> <value>); a new session starts from the saved defaults.' % (session, session))
    lines.extend('  ! ' + problem for problem in problems)
    return '\n'.join(lines)


def render_agents(values):
    rows = agents(values)
    if not rows:
        return 'mode %s runs no agents.' % values['mode']
    lines = ['mode %s - %d agent(s); Opus agents run on: %s (a per-agent model beats it)' % (values['mode'], len(rows), values['mode_model'])]
    lines.extend('  %-18s defined %-7s runs on %s%s' % (r['role'], r['defined'], r['runs_on'],
                 '' if r['enabled'] == 'auto' else '   [%s]' % r['enabled']) for r in rows)
    return '\n'.join(lines)


def seen_dir():
    return os.environ.get('ADYUSUF_SEEN_DIR') or os.path.join(os.path.expanduser('~'), '.claude', 'adyusuf-seen')


def notify(event, payload_text):
    """A hook (UserPromptSubmit, PostToolUse): when the effective settings differ from what this session last saw,
    answer with additionalContext naming the changes. The first call of a session only records them (SessionStart already
    printed them). The note says the change applies from the NEXT task, so a running one is never split. Never raises."""
    try:
        session = str(json.loads(payload_text).get('session_id') or '')
    except (ValueError, AttributeError):
        session = ''
    if not session or not all(ch.isalnum() or ch in '-_' for ch in session):
        return None
    effective, problems = load(session=session)
    values = {key: value[0] for key, value in effective.items()}
    path = os.path.join(seen_dir(), session)
    try:
        with open(path, encoding='utf-8') as handle:
            before = json.load(handle)
    except (OSError, ValueError):
        before = None
    def remember():
        try:
            os.makedirs(seen_dir(), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump(values, handle)
            return True
        except OSError:
            return False

    changes = []
    if isinstance(before, dict):
        before = {key: value for key, value in before.items() if key in SPECS}   # a retired key is not a change
        # A setting the seen-file never had (the plugin was updated mid-session) is new, not changed.
        changes = ['%s: %s -> %s' % (key, shown(before[key]), shown(values[key])) for key in sorted(values)
                   if key in before and before[key] != values[key]]
        if not changes:
            if before != values:
                remember()                      # only new settings appeared: remember them, say nothing
            return None
    if not remember() or before is None:
        return None
    text = ('adyusuf settings changed (/adyusuf:config). Apply them from the NEXT task on; finish the step in progress as it '
            'was started, do not restart or split it. Changes: ' + '; '.join(changes) + '.\n' + context(effective, problems, session))
    return {'hookSpecificOutput': {'hookEventName': event, 'additionalContext': text}}


def payload_session():
    """The session id a hook's JSON payload on stdin carries ('' when it holds none). Only called for `context --stdin`:
    reading stdin would block a run that was not given a payload."""
    try:
        session = json.loads(sys.stdin.read()).get('session_id')
    except (OSError, ValueError, AttributeError):
        return ''
    return session if sessions.valid(session) else ''


def main(argv):
    args = list(argv)
    scope_project = '--project' in args
    args = [a for a in args if a != '--project']
    session = None
    if '--session' in args:
        at = args.index('--session')
        session = args[at + 1] if at + 1 < len(args) else ''
        del args[at:at + 2]
    command = args[0] if args else ''
    try:
        if session is not None and not sessions.valid(session):
            raise ConfigError('--session needs a session id (letters, digits, - and _)')
        if session is not None and scope_project:
            raise ConfigError('--project and --session cannot be combined')
        if command in ('show', 'context', 'get', 'schema', 'agents') and scope_project:
            raise ConfigError('--project only applies to set, unset and apply')
        if command in ('set', 'unset', 'apply', 'reset-agents'):
            path = sessions.session_file(session) if session else (project_file() if scope_project else user_file())

        def write(*parts):
            write_layer(*parts)
            if session:
                sessions.prune()                  # a session file nobody has touched for two weeks goes
        if command == 'show':
            effective, problems = load(session=session)
            if '--json' in args:
                print(json.dumps({'values': {k: v[0] for k, v in effective.items()}, 'sources': {k: v[1] for k, v in effective.items()},
                                  'problems': problems}, indent=2))
            else:
                print(render(effective, problems))
            return 0
        if command == 'agents':
            effective, _ = load(session=session)
            values = {k: v[0] for k, v in effective.items()}
            if '--json' in args:
                print(json.dumps(agents(values, include_inactive='--all' in args), indent=2))
            else:
                print(render_agents(values))
            return 0
        if command == 'reset-agents':
            effective, _ = load()
            write(path, {}, [key for key in SPECS if key.startswith('agents.')])
            print('every agents.* setting removed from %s' % path)
            return 0
        if command == 'context':
            session = session or (payload_session() if '--stdin' in args else '')
            print(context(*load(session=session), session))
            return 0
        if command == 'notify' and len(args) == 2:
            try:
                answer = notify(args[1], sys.stdin.read())
            except Exception:   # a hook must never fail the session it serves
                answer = None
            if answer:
                print(json.dumps(answer))
            return 0
        if command == 'schema':
            print(json.dumps(SCHEMA, indent=2))
            return 0
        if command == 'get' and len(args) == 2:
            effective, _ = load(session=session)
            if args[1] not in effective:
                raise ConfigError("unknown setting '%s'" % args[1])
            print(shown(effective[args[1]][0]))
            return 0
        if command == 'set' and len(args) == 3:
            write(path, {args[1]: check(args[1], args[2])})
            print('%s = %s  (%s)' % (args[1], shown(check(args[1], args[2])), path))
            return 0
        if command == 'unset' and len(args) == 2:
            check_key = args[1]
            if check_key not in SPECS:
                raise ConfigError("unknown setting '%s'" % check_key)
            write(path, {}, (check_key,))
            print('%s removed from %s' % (check_key, path))
            return 0
        if command == 'apply' and len(args) == 2:
            raw = sys.stdin.read() if args[1] == '-' else open(args[1], encoding='utf-8').read()
            try:
                incoming = json.loads(raw)
            except ValueError as error:
                raise ConfigError('not valid JSON: %s' % error)
            if not isinstance(incoming, dict):
                raise ConfigError('expected a JSON object of {"key": value}')
            flat = flatten(incoming)
            skipped = sorted(key for key in flat if key in RETIRED_KEYS)   # a file saved before they were retired
            write(path, {key: check(key, value) for key, value in flat.items() if key not in RETIRED_KEYS})
            print('%d setting(s) written to %s' % (len(flat) - len(skipped), path))
            if skipped:
                print('skipped (retired, no longer settings): %s' % ', '.join(skipped))
            return 0
        raise ConfigError(__doc__.split('Layers,')[0].strip())
    except ConfigError as error:
        sys.stderr.write('%s\n' % error)
        return error.code
    except OSError as error:
        sys.stderr.write('%s\n' % error)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
