"""The adyusuf configuration's schema: what can be set, the role sets of the modes, and the agents each mode runs.

Split out of adyusuf_config.py so no file passes 300 lines (rule #9); adyusuf_config.py re-exports every name here.
"""
import os

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
                + tuple('%s.%s' % (group, t) for group in ('ci_before_merge', 'e2e_after_deploy') for t in TARGETS)
                + ('deploy_after_push',))      # one radio choice until 30/10/2026; now deploy_after_push.<test|prod> checkboxes


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
REPLY_LENGTHS = ('short', 'normal', 'long')       # how much Claude writes in a reply (standards/00 §5a)
DEPLOY_ENVS = ('test', 'prod')                    # which environment a push is deployed to
CI_RUNNERS = ('hosted', 'self-hosted')            # where the shared SDLC workflow runs (self-hosted: this Mac's runners)
AGENT_STATES = ('auto', 'on', 'off')
AGENT_MODELS = ('default', 'opus', 'sonnet', 'haiku', 'fable')


# The one definition of what can be set: order is the display order. `group` titles the sections of `show`.
SCHEMA = (
    [dict(_enum('mode', 'Working mode', MODES), group='Session'),
     dict(_enum('mode_model', 'Model that replaces Opus in the agents', MODELS), group='Session'),
     dict(_enum('reply.length', 'Reply length', REPLY_LENGTHS), group='Session'),
     dict(_bool('pod.connect', 'Connect to pod'), group='Pod'),
     dict(_enum('pod.message_format', 'Message format', POD_FORMATS), group='Pod'),
     dict(_bool('write.unit_tests', 'Write unit tests'), group='Writing'),
     dict(_bool('write.e2e', 'Write e2e specs'), group='Writing')]
    + [dict(_bool('merge.' + t, 'Merge into ' + t), group='Merge') for t in TARGETS]
    + [dict(_bool('push.' + t, 'Push ' + t), group='Push') for t in TARGETS]
    + [dict(_bool('gates_before_push.' + t, 'Run gates before pushing %s' % t), group='Gates before a push') for t in TARGETS]
    + [dict(_bool('coverage_before_push.' + t, 'Run coverage before pushing %s' % t), group='Coverage before a push')
       for t in TARGETS]
    + [dict(_bool('ci_after_push.' + t, 'Run CI after pushing %s' % t), group='CI after push') for t in TARGETS]
    + [dict(_bool('deploy_after_push.' + env, 'After pushing update, deploy to ' + env), group='Deploy after push') for env in DEPLOY_ENVS]
    + [dict(_enum('ci.runner', 'CI runner', CI_RUNNERS), group='CI after push')]
    + [dict(_bool('e2e_before_deploy.' + after, 'Run e2e on %s before deploying %s' % (on, after)), group='E2E before deploy')
       for on, after in E2E_STAGES]
    + [dict(_enum('agents.%s.%s' % (role, field), '%s: %s' % (role, field), options), group='Agents')
       for role in D_ROLES for field, options in (('enabled', AGENT_STATES), ('model', AGENT_MODELS))])
SPECS = {spec['key']: spec for spec in SCHEMA}


def front_matter(role, field, missing):
    """One front-matter line of an agent file (`model:`, `description:`), or `missing` when the file or line is absent."""
    try:
        with open(os.path.join(AGENTS_DIR, role + '.md'), encoding='utf-8') as handle:
            for line in handle:
                if line.startswith(field + ':'):
                    return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return missing


def defined_model(role):
    """The model an agent file names (its `model:` front-matter line), or 'inherit'."""
    return front_matter(role, 'model', 'inherit')


def effective_model(defined, override):
    """Only the Opus agents move to the mode's override; `keep` (and no override) leaves every agent as defined."""
    return override if defined == 'opus' and override not in ('keep', 'opus', None) else defined


def agents(values, include_inactive=False):
    """One dict per role: defined model, the model it runs on, the model `default` gives it (`default_model`, also while
    another is pinned: the pane's model radios need it), whether it is active, and the settings behind that.

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
        default_model = effective_model(defined, override)
        runs_on = chosen if chosen != 'default' else default_model
        if active or include_inactive:
            rows.append({'role': role, 'defined': defined, 'runs_on': runs_on, 'default_model': default_model, 'active': active,
                         'in_mode': in_mode, 'enabled': enabled, 'model': chosen,
                         'description': front_matter(role, 'description', '')})   # the pane's hover card (01/11/2026)
    return rows
