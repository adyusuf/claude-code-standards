#!/usr/bin/env python3
"""The adyusuf configuration: defaults instead of questions.

    adyusuf_config.py show [--json]              every setting, its value and where the value comes from
    adyusuf_config.py get <key>                  one effective value
    adyusuf_config.py set <key> <value> [--project]    change one setting (default scope: the user's)
    adyusuf_config.py unset <key> [--project]    fall back to the next layer
    adyusuf_config.py apply <file|-> [--project] set many at once from a JSON object {"push.prod": false, ...}
    adyusuf_config.py schema                     the keys with type, options and label (the panel is built from it)
    adyusuf_config.py agents [--json] [--all]    the active agents and the model each one runs on (--all: inactive too)
    adyusuf_config.py reset-agents [--project]   remove every agents.<role>.* setting (back to the mode's own set)
    adyusuf_config.py panel-data                 everything the panel needs: schema, values, defaults, sources, roles
    adyusuf_config.py panel                      the panel page (HTML) with that data embedded, ready to publish as an Artifact
    adyusuf_config.py context                    the block the SessionStart hook prints
    adyusuf_config.py notify <event>             hook: tells the running session when a setting changed (stdin: the payload)

Layers, lowest first: defaults/adyusuf.json (shipped with the plugin) < ~/.claude/adyusuf.json (the user's own
defaults) < <project>/.claude/adyusuf.json (committed, like .claude/mode). The user changes them with the
`adyusuf:config` skill or the panel; Claude never asks what a setting already answers (global rule #34).

Keys are dotted (`push.prod`); files hold them nested. A key is validated against SCHEMA, a file that does not
parse is reported and ignored (the layer below wins) - the SessionStart hook must never fail a session.
Exit codes: 0 done · 1 a configuration file is unreadable (set/unset/apply refuse to overwrite it) ·
2 bad usage, unknown key or invalid value (nothing is written).
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULTS_FILE = os.path.join(ROOT, 'defaults', 'adyusuf.json')
TARGETS = ('dev', 'test', 'prod')
MODES = ('A', 'B', 'C', 'D', 'E')
MODELS = ('keep', 'sonnet', 'haiku', 'fable')
# Settings that no longer exist. A user's file written before they were retired still holds them: they are skipped
# on read, so one stale key never makes the whole layer invalid (and the next write drops them).
RETIRED_KEYS = ('monitor.connect', 'monitor.message_format')


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
PANEL_TEMPLATE = os.path.join(ROOT, 'skills', 'config', 'panel.template.html')


AGENT_STATES = ('auto', 'on', 'off')
AGENT_MODELS = ('default', 'opus', 'sonnet', 'haiku', 'fable')


# The one definition of what can be set: order is the panel's order. `group` titles the panel sections.
SCHEMA = (
    [dict(_enum('mode', 'Working mode', MODES), group='Session'),
     dict(_enum('mode_model', 'Model that replaces Opus in the agents', MODELS), group='Session'),
     dict(_bool('write.unit_tests', 'Write unit tests'), group='Writing'),
     dict(_bool('write.e2e', 'Write e2e specs'), group='Writing')]
    + [dict(_bool('merge.' + t, 'Merge into ' + t), group='Merge') for t in TARGETS]
    + [dict(_bool('push.' + t, 'Push ' + t), group='Push') for t in TARGETS]
    + [dict(_bool('run_before_push.%s.%s' % (t, gate), 'Run %s before pushing %s' % (
        'unit tests' if gate == 'unit' else 'e2e', t)), group='Gates before a push')
       for t in TARGETS for gate in ('unit', 'e2e')]
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


def load(user_path=None):
    """(effective {key: (value, source)}, problems [str]). `user_path` replaces the user's file (the installer's --home)."""
    problems = []
    defaults, problem = read_layer(DEFAULTS_FILE)
    if problem:
        problems.append(problem)
    effective = {spec['key']: (defaults.get(spec['key']), 'default') for spec in SCHEMA}
    for source, path in (('user', user_path or user_file()), ('project', project_file())):
        values, problem = read_layer(path)
        if problem:
            problems.append(problem)
        for key, value in values.items():
            effective[key] = (value, source)
    return effective, problems


def write_layer(path, changes, removals=()):
    """Merge `changes` into the layer's file and write it back. Refuses to overwrite an unreadable file."""
    current, problem = read_layer(path)
    if problem:
        raise ConfigError('refusing to overwrite an unreadable configuration file - ' + problem, 1)
    current.update(changes)
    for key in removals:
        current.pop(key, None)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(nest(current), handle, indent=2)
        handle.write('\n')


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


def context(effective, problems):
    """The compact block a session starts with: the effective values, what they mean, how to change them."""
    value = lambda key: effective[key][0]  # noqa: E731
    steps = []
    for target in TARGETS:
        gates = [g for g in ('unit', 'e2e') if value('run_before_push.%s.%s' % (target, g))]
        steps.append('%s: merge %s, push %s, run before push: %s' % (
            target, shown(value('merge.' + target)), shown(value('push.' + target)), ', '.join(gates) or 'nothing'))
    lines = ['adyusuf configuration (effective; global rule #34 - follow it, do not ask what it answers):',
             '  mode %s, model for the Opus agents: %s' % (value('mode'), value('mode_model')),
             '  write unit tests: %s, write e2e: %s' % (shown(value('write.unit_tests')), shown(value('write.e2e')))]
    active = agents({k: v[0] for k, v in effective.items()})
    lines.append('  agents: %s' % (', '.join('%s (%s)' % (row['role'], row['runs_on']) for row in active) or 'none'))
    lines.extend('  ' + step for step in steps)
    lines.append('  change it with the adyusuf:config skill (or its panel); the mode may also be set per session or per project.')
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


def panel_data(effective, problems):
    roles = sorted({role for roles in MODE_ROLES.values() for role in roles})
    defaults, _ = read_layer(DEFAULTS_FILE)
    return {'schema': SCHEMA,
            'defaults': defaults,
            'values': {k: v[0] for k, v in effective.items()},
            'sources': {k: v[1] for k, v in effective.items()},
            'roles': [{'name': role, 'defined': defined_model(role), 'modes': [m for m in MODES if role in MODE_ROLES[m]]}
                      for role in roles],
            'agents': agents({k: v[0] for k, v in effective.items()}, include_inactive=True),
            'problems': problems}


def panel_html(effective, problems):
    """The panel page: the template with the data as a JSON literal (a '</' inside it cannot close the script)."""
    with open(PANEL_TEMPLATE, encoding='utf-8') as handle:
        template = handle.read()
    data = json.dumps(panel_data(effective, problems)).replace('</', '<\\/')
    return template.replace('__PANEL_DATA__', data)


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
    effective, problems = load()
    values = {key: value[0] for key, value in effective.items()}
    path = os.path.join(seen_dir(), session)
    try:
        with open(path, encoding='utf-8') as handle:
            before = json.load(handle)
    except (OSError, ValueError):
        before = None
    if isinstance(before, dict):
        before = {key: value for key, value in before.items() if key in SPECS}   # a retired key is not a change
    if before == values:
        return None
    try:
        os.makedirs(seen_dir(), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(values, handle)
    except OSError:
        return None
    if before is None:
        return None
    changes = ['%s: %s -> %s' % (key, shown(before.get(key)), shown(values[key])) for key in sorted(values)
               if before.get(key) != values[key]]
    text = ('adyusuf settings changed (/adyusuf:config). Apply them from the NEXT task on; finish the step in progress as it '
            'was started, do not restart or split it. Changes: ' + '; '.join(changes) + '.\n' + context(effective, problems))
    return {'hookSpecificOutput': {'hookEventName': event, 'additionalContext': text}}


def main(argv):
    args = list(argv)
    scope_project = '--project' in args
    args = [a for a in args if a != '--project']
    command = args[0] if args else ''
    path = project_file() if scope_project else user_file()
    try:
        if command in ('show', 'context', 'get', 'schema', 'agents', 'panel-data', 'panel') and scope_project:
            raise ConfigError('--project only applies to set, unset and apply')
        if command == 'show':
            effective, problems = load()
            if '--json' in args:
                print(json.dumps({'values': {k: v[0] for k, v in effective.items()}, 'sources': {k: v[1] for k, v in effective.items()},
                                  'problems': problems}, indent=2))
            else:
                print(render(effective, problems))
            return 0
        if command == 'agents':
            effective, _ = load()
            values = {k: v[0] for k, v in effective.items()}
            if '--json' in args:
                print(json.dumps(agents(values, include_inactive='--all' in args), indent=2))
            else:
                print(render_agents(values))
            return 0
        if command == 'reset-agents':
            effective, _ = load()
            write_layer(path, {}, [key for key in SPECS if key.startswith('agents.')])
            print('every agents.* setting removed from %s' % path)
            return 0
        if command == 'panel':
            sys.stdout.write(panel_html(*load()))
            return 0
        if command == 'panel-data':
            print(json.dumps(panel_data(*load()), indent=2))
            return 0
        if command == 'context':
            print(context(*load()))
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
            effective, _ = load()
            if args[1] not in effective:
                raise ConfigError("unknown setting '%s'" % args[1])
            print(shown(effective[args[1]][0]))
            return 0
        if command == 'set' and len(args) == 3:
            write_layer(path, {args[1]: check(args[1], args[2])})
            print('%s = %s  (%s)' % (args[1], shown(check(args[1], args[2])), path))
            return 0
        if command == 'unset' and len(args) == 2:
            check_key = args[1]
            if check_key not in SPECS:
                raise ConfigError("unknown setting '%s'" % check_key)
            write_layer(path, {}, (check_key,))
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
            skipped = sorted(key for key in flat if key in RETIRED_KEYS)   # a panel saved before they were retired
            write_layer(path, {key: check(key, value) for key, value in flat.items() if key not in RETIRED_KEYS})
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
