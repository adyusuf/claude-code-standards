#!/usr/bin/env python3
"""The adyusuf configuration: defaults instead of questions.

    adyusuf_config.py show [--json] [--user]     every setting, its value and where the value comes from (--user: only the
                                                 shipped defaults and the user's own file, no project or session layer)
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
import json
import os
import sys

# The schema and the layers live beside this file (split so no file passes 300 lines, rule #9); every name they hold is
# re-exported here, so callers keep reading them from adyusuf_config.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adyusuf_session as sessions  # noqa: E402
from adyusuf_schema import (  # noqa: E402,F401
    AGENTS_DIR, AGENT_MODELS, AGENT_STATES, B_ROLES, CI_RUNNERS, C_ROLES,
    DEFAULTS_FILE, DEPLOY_ENVS, D_ROLES, E2E_STAGES, MODELS, MODES,
    MODE_ROLES, POD_FORMATS, REPLY_LENGTHS, RETIRED_KEYS, ROOT, SCHEMA,
    SPECS, TARGETS, agents, defined_model, effective_model, front_matter)
from adyusuf_layers import (  # noqa: E402,F401
    ConfigError, check, flatten, load, locked, nest,
    project_file, read_layer, user_file, write_layer)


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


# What each reply length asks of Claude, printed at session start (standards/00-working-method.md §5a). Whatever the
# length, a red test, a skipped step, an open finding and what waits on the user are said: shorter, never left out.
REPLY_MEANING = {
    'short': 'write a few sentences: what changed, what is not done or not verified, what waits on the user; no extra '
             'tables, recaps or lists of checks unless asked. Still said at every length: a red test, a skipped step, an '
             'open finding, the long-run table, the #28 handoff line and end-of-turn block, the #24 deferred list, the '
             '#27 agent count and cost (standards/00 §5a)',
    'normal': 'the result and the reasoning that matters, short lists where they help (standards/00 §5a)',
    'long': 'a full report: every step with its evidence and figures, tables where they help (standards/00 §5a)',
}


def context(effective, problems, session=None):
    """The compact block a session starts with: the effective values, what they mean, how to change them."""
    value = lambda key: effective[key][0]  # noqa: E731
    steps = []
    for target in TARGETS:
        steps.append('%s: merge %s, gates before push %s, coverage before push %s, push %s, CI after push %s' % (
            target, shown(value('merge.' + target)), shown(value('gates_before_push.' + target)),
            shown(value('coverage_before_push.' + target)), shown(value('push.' + target)),
            shown(value('ci_after_push.' + target))))
    steps.append('e2e before deploy: ' + ', '.join(
        'on %s before deploying %s %s' % (on, after, shown(value('e2e_before_deploy.' + after))) for on, after in E2E_STAGES))
    lines = ['adyusuf configuration (effective; global rule #34 - follow it, do not ask what it answers):',
             '  for code work: changing a project repository\'s files. A no-code task (a question, research, Claude\'s own '
             'bookkeeping in ~/.claude) makes no branch or commit and runs no merge, push, gate, coverage, CI, deploy, e2e, '
             'test writing or agent; replies, the Status box and #14/#15/#24 still apply (standards/13 §8a).',
             '  mode %s, model for the Opus agents: %s' % (value('mode'), value('mode_model')),
             '  replies: %s - %s' % (value('reply.length'), REPLY_MEANING.get(value('reply.length'), REPLY_MEANING['short'])),
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
            'was started, do not restart or split it. Reply length is the exception: it applies from your next reply. '
            'Changes: ' + '; '.join(changes) + '.\n' + context(effective, problems, session))
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
    scope_user = '--user' in args
    args = [a for a in args if a not in ('--project', '--user')]
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
        if scope_user and (command != 'show' or session is not None):
            raise ConfigError('--user only applies to show, and not with --session')
        if command == 'show':
            effective, problems = load(session=session, project=not scope_user)
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
