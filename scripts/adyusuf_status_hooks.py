"""The plugin's hooks on the Status box (user decisions 02/11/2026), split out of adyusuf_status.py so no file passes 300
lines (rule #9). `adyusuf_status.py hook EVENT` reads the hook payload on stdin and calls `hook` here.

    session     a session starts: `now` is "waiting for you"
    prompt      the user's message: `now` is its first line, and Claude is reminded to analyse it into steps first
    stop        a turn's end: "waiting for you", or "waiting for background work" while a task or cron runs
    subagent    a subagent starts: it is told how to write its own steps into this session's box
    guard       before an edit or a commit: with `steps.enforce` set to block, refused until the box holds steps

A hook never fails a session: a bad payload or an unusable id does nothing. Only `guard` may refuse (exit code 2).
"""
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adyusuf_status import EMPTY, OPEN, StatusError, clip, load, locked, save, valid  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adyusuf_status.py')
# What `now` says when a session starts or a turn ends: it waits for the user, or for its own background work.
WAITING = 'waiting for you'
WAITING_BACKGROUND = 'waiting for background work'
# The turns a person starts: a system-started turn (a task notification, a wake-up) must not replace the user's task.
USER_SOURCES = (None, 'user', 'sdk')
# Where an edit is Claude's own bookkeeping, never code work (standards/13 §8a): its notes and plans, the adyusuf settings
# and status files, a project's mode files, temp files. Code under ~/.claude (a mod, a plugin) is code work.
CLAUDE_HOME = os.path.join(os.path.expanduser('~'), '.claude')
BOOKKEEPING = tuple(os.path.normcase(os.path.join(CLAUDE_HOME, name)) for name in (
    'projects', 'plans', 'todos', 'adyusuf.json', 'adyusuf-status', 'adyusuf-session', 'adyusuf-seen')) + tuple(
    os.path.normcase(path) + os.sep for path in {os.path.realpath(tempfile.gettempdir()), '/tmp', '/private/tmp', '/var/folders',
                                                 '/private/var/folders'})
PROJECT_BOOKKEEPING = ('mode', 'mode-model', 'adyusuf.json')       # <project>/.claude/<name>
# `git commit` where a command starts (after ;, &, |, a newline or the line's start), options such as -C <dir> allowed.
COMMIT = re.compile(r'(?:^|[;&|\n])\s*git(?:\s+(?:-[Cc]\s+\S+|-\S+))*\s+commit(?![-\w])')


def hook_text(event, payload):
    """What `now` becomes for one hook payload, or None to leave the table alone."""
    if event == 'prompt':
        if payload.get('source') not in USER_SOURCES:
            return None
        return 'working on: ' + str(payload.get('prompt') or '').strip().split('\n')[0]
    if event == 'stop':
        return WAITING_BACKGROUND if payload.get('background_tasks') or payload.get('session_crons') else WAITING
    return WAITING if event == 'session' else None


def enforce(session):
    """The `steps.enforce` setting this session runs on: 'block' or 'remind' (block when it cannot be read)."""
    try:
        import adyusuf_layers
        value = adyusuf_layers.load(session=session)[0].get('steps.enforce', ('block', ''))[0]
    except Exception:  # noqa: BLE001 - a hook falls back to the shipped default, never fails
        return 'block'
    return value if value in ('block', 'remind') else 'block'


def open_steps(session, agents):
    """Whether one of `agents` ('' = this session) has a step still to finish, written with `step` (it has a %): a plan
    left from a finished task does not let the next task's edits through (qa, 02/11/2026). None: the file is unreadable."""
    try:
        rows = load(session)['rows']
    except (StatusError, OSError):
        return None
    return any(row.get('agent', '') in agents and row.get('percent') != '' and row.get('state') in OPEN for row in rows)


def bookkeeping(path):
    path = os.path.normcase(path)
    parent, name = os.path.split(path)
    return path.startswith(BOOKKEEPING) or (os.path.basename(parent) == '.claude' and name in PROJECT_BOOKKEEPING)


def reminder(session):
    """What every user message carries: analyse first, steps in the box, % and blockers kept current."""
    return ('adyusuf steps (setting steps.enforce: %s): before acting on this message, analyse it. If it adds work, '
            'write its steps into the Status box first, in order, as phases where it helps: python3 "%s" --session %s '
            'step "<n. step>" "not started" 0 [--after "<step>"] (a request that arrives mid-work goes in with --after). '
            'Keep each step current: state running/done/blocked/did not run, its %% done, --blocker "<what>" when stuck. '
            'Status box: standards/00 §1a, §10d.' % (enforce(session), SCRIPT, session))


def agent_name(payload):
    """How a subagent signs its steps: its type and the start of its id, so two of a kind stay apart."""
    return ('%s %s' % (str(payload.get('agent_type') or 'agent'), str(payload.get('agent_id') or '')[:6])).strip()


def subagent_note(session, payload):
    name = agent_name(payload)
    return ('adyusuf steps: you are "%s". Write your own steps into the parent\'s Status box before working: python3 "%s" '
            '--session %s step "<n. step>" "not started" 0 --agent "%s"; keep state and %% current, --blocker "<what>" '
            'when stuck.' % (name.strip(), SCRIPT, session, name.strip()))


def blocked(payload):
    """Why an edit or a commit is refused, or '' to let it run: with `block`, code work waits for the steps."""
    session = str(payload.get('session_id') or '')
    tool, given = str(payload.get('tool_name') or ''), payload.get('tool_input') or {}
    if tool == 'Bash':
        work = bool(COMMIT.search(str(given.get('command') or '')))
    else:
        given_path = str(given.get('file_path') or given.get('notebook_path') or '')
        work = given_path != '' and not bookkeeping(os.path.abspath(given_path))
    if not work or not valid(session):
        return ''
    # A subagent may go on under its own steps or the session's; it is told to write its own (--agent).
    name = agent_name(payload) if payload.get('agent_id') else ''
    found = open_steps(session, {'', name})
    if found or enforce(session) != 'block':
        return ''
    if found is None:
        return ('adyusuf steps: the Status file cannot be read; replace it with python3 "%s" --session %s clear, then write '
                'the steps. Then retry.' % (SCRIPT, session))
    sign = ' --agent "%s"' % name if name else ''
    return ('adyusuf steps (steps.enforce: block): no step of this task is open. Analyse the work and write its steps into '
            'the Status box first: python3 "%s" --session %s step "<n. step>" "not started" 0%s. Then retry.'
            % (SCRIPT, session, sign))


def context(event, text):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': event, 'additionalContext': text}}))


def hook(event, payload_text):
    """Run one hook; returns the exit code (2 only when `guard` refuses). Never raises."""
    try:
        payload = json.loads(payload_text)
        session = str(payload.get('session_id') or '')
        if event == 'guard':
            reason = blocked(payload)
            if reason:
                print(reason, file=sys.stderr)
                return 2
            return 0
        if not valid(session):
            return 0
        if event == 'subagent':
            context('SubagentStart', subagent_note(session, payload))
            return 0
        text = hook_text(event, payload)
        if text is None:
            return 0
        with locked(session):
            try:
                data = load(session)
            except StatusError:
                data = dict(EMPTY, rows=[])          # a corrupt file is replaced, as `clear` would
            save(session, dict(data, now=clip(text), next=''))
        if event == 'prompt':
            context('UserPromptSubmit', reminder(session))
    except (ValueError, AttributeError, OSError, StatusError):
        return 0
    return 0
