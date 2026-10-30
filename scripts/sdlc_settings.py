#!/usr/bin/env python3
"""The SDLC settings file a project commits: what the panel says, written down where CI can read it.

    sdlc_settings.py write [--project DIR] [--session ID]    write <project>/.claude/sdlc-settings.json from the panel's settings
    sdlc_settings.py check [--project DIR] [--session ID]    exit 1 when that file differs from what the panel says now
    sdlc_settings.py show  [--session ID]                    print the settings as the file would hold them
    sdlc_settings.py vars  --repo OWNER/NAME [--session ID] [--dry-run]   set the repo variable SDLC_RUNNER_LABELS from "CI runner"

CI runs on a server that cannot read this machine's panel, so every merge writes the panel's SDLC settings into the
project (user decision 29/10/2026): the shared workflow (.github/workflows/sdlc.yml) and the local gate read this one
file, nothing else. Only the layers the PANEL owns count - the shipped defaults, the user's file and, with --session,
that session's layer; a project's own `.claude/adyusuf.json` is left out on purpose, the projects take the panel's
settings and keep none of their own. A setting the panel has not seen yet takes the shipped default.

The file is the same for the same settings (sorted keys, no timestamp), so writing it on every merge changes nothing
when nothing changed. Exit codes: 0 done / equal · 1 differs (check) or a configuration file is unreadable · 2 usage.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adyusuf_config as cfg  # noqa: E402

FILE = os.path.join('.claude', 'sdlc-settings.json')
# What the pipeline reads. The session's own choices (mode, agents) and the pod are not part of the SDLC.
SDLC_PREFIXES = ('merge.', 'push.', 'gates_before_push.', 'coverage_before_push.', 'ci_after_push.', 'e2e_before_deploy.')
SDLC_KEYS = ('ci.runner', 'deploy_after_push')
VERSION = 1
RUNNER_VARIABLE = 'SDLC_RUNNER_LABELS'
# "CI runner" in the panel -> the JSON array the shared workflow gives runs-on. The labels of this machine's runners
# (scripts/runner-setup.sh) are `self-hosted` plus the architecture; a hosted runner is the GitHub-provided one.
RUNNER_LABELS = {'hosted': '["ubuntu-latest"]', 'self-hosted': '["self-hosted"]'}


def settings(session=None, user_path=None):
    """{"version": 1, "settings": nested SDLC settings} from defaults < user file < session (the panel's layers)."""
    effective, problems = cfg.load(user_path=user_path, session=session, project=False)
    if problems:
        raise cfg.ConfigError('; '.join(problems))
    flat = {key: value for key, (value, _source) in effective.items()
            if key in SDLC_KEYS or key.startswith(SDLC_PREFIXES)}
    return {'version': VERSION, 'settings': cfg.nest(flat)}


def render(payload):
    return json.dumps(payload, indent=2, sort_keys=True) + '\n'


def project_root(explicit):
    if explicit:
        return os.path.abspath(explicit)
    try:
        return subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getcwd()


def option(argv, name):
    if name in argv:
        index = argv.index(name)
        if index + 1 >= len(argv):
            raise SystemExit('%s needs a value' % name)
        return argv[index + 1]
    return None


def set_runner_variable(repo, runner, dry_run):
    """Give the repo the runner labels the panel chose. The workflow's runs-on is decided before any job starts, so
    it cannot read the settings file - a repository variable is the one place it can read at that moment."""
    if not repo:
        print('vars needs --repo OWNER/NAME', file=sys.stderr)
        return 2
    labels = RUNNER_LABELS.get(runner)
    if labels is None:
        print('sdlc_settings: unknown CI runner %r' % runner, file=sys.stderr)
        return 1
    if dry_run:
        print('%s=%s (%s) - not set, --dry-run' % (RUNNER_VARIABLE, labels, repo))
        return 0
    done = subprocess.run(['gh', 'variable', 'set', RUNNER_VARIABLE, '--repo', repo, '--body', labels], capture_output=True, text=True)
    if done.returncode != 0:
        print('sdlc_settings: gh could not set %s on %s: %s' % (RUNNER_VARIABLE, repo, (done.stdout + done.stderr).strip()), file=sys.stderr)
        return 1
    print('%s=%s set on %s' % (RUNNER_VARIABLE, labels, repo))
    return 0


def main(argv):
    if not argv or argv[0] not in ('write', 'check', 'show', 'vars'):
        print(__doc__)
        return 2
    command, rest = argv[0], argv[1:]
    session, project = option(rest, '--session'), option(rest, '--project')
    try:
        text = render(settings(session=session, user_path=os.environ.get('ADYUSUF_CONFIG_USER') or None))
    except cfg.ConfigError as problem:
        print('sdlc_settings: %s' % problem, file=sys.stderr)
        return 1
    if command == 'show':
        sys.stdout.write(text)
        return 0
    if command == 'vars':
        return set_runner_variable(option(rest, '--repo'), json.loads(text)['settings']['ci']['runner'], '--dry-run' in rest)
    path = os.path.join(project_root(project), FILE)
    try:
        with open(path, encoding='utf-8') as handle:
            current = handle.read()
    except OSError:
        current = None
    if command == 'check':
        if current == text:
            print('sdlc-settings.json matches the panel')
            return 0
        print('%s %s the panel - run: sdlc_settings.py write' % (path, 'is missing, the panel has settings' if current is None else 'differs from'))
        return 1
    if current == text:
        print('unchanged: %s' % path)
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    print('written: %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
