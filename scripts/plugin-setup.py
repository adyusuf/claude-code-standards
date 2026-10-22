#!/usr/bin/env python3
"""Install or update the adyusuf plugin from GitHub. One standalone file, standard library only.

It asks GitHub which commit the plugin's branch is on, compares that with the commit Claude Code has installed, and:
    not installed      adds the marketplace (the link to GitHub) and installs the plugin;
    installed, current says so and changes nothing (it still adds the marketplace if that link is missing);
    installed, older   asks "remove the old version and install the new one?"; on yes it removes the old one
                       (keeping the plugin's data) and installs the new one, then checks that your settings and
                       the marketplace link are exactly as they were.

Usage:
    python3 plugin-setup.py                # install, or ask before replacing an older version
    python3 plugin-setup.py --yes          # replace without asking (needed when stdin is not a terminal)
    python3 plugin-setup.py --check        # report only: contacts GitHub, changes nothing, exit 1 if work is due
    python3 plugin-setup.py --ref test     # the branch to install when no marketplace is linked yet

Your settings live outside the plugin (~/.claude/adyusuf.json, a project's .claude/adyusuf.json) and the marketplace
link lives in Claude Code's own settings; neither is touched. ~/.claude/adyusuf.json is copied to
~/.claude-standards/backups/ first anyway. Every run but --check writes ~/.claude-standards/logs/plugin-setup-<stamp>.log.
Exit codes: 0 done / current / you answered no · 1 --check found work to do · 2 refused or failed.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import types

REPO = 'adyusuf/claude-code-standards'
GIT_URL = f'https://github.com/{REPO}.git'
MARKETPLACE = 'adyusuf-marketplace'
PLUGIN_ID = f'adyusuf@{MARKETPLACE}'
DEFAULT_REF = 'prod'
REF_OK = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]*$')       # never starts with "-": it becomes a command argument
SHA = re.compile(r'^[0-9a-f]{40}$')


def run(command):
    """(exit code, output) of a child process; GitHub is never allowed to prompt for a password."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    command = [shutil.which(command[0]) or command[0]] + command[1:]      # Windows: claude is claude.cmd
    try:
        done = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                              env=env, timeout=600)
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)
    return done.returncode, (done.stdout + done.stderr).strip()


def read_json(path):
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def installed_entry(home):
    """{sha, version, scope} of the installed plugin from Claude Code's own record, or None."""
    data = read_json(os.path.join(home, '.claude', 'plugins', 'installed_plugins.json'))
    entries = (data or {}).get('plugins', {}).get(PLUGIN_ID) if isinstance(data, dict) else None
    entries = [e for e in (entries if isinstance(entries, list) else [entries]) if isinstance(e, dict)]
    if not entries:
        return None
    first = next((e for e in entries if e.get('scope') == 'user'), entries[0])
    return {'sha': first.get('gitCommitSha') or '', 'version': first.get('version') or '',
            'scope': first.get('scope') or 'user'}


def is_current(entry, remote):
    return any(len(c) >= 7 and remote.startswith(c) for c in (entry['sha'], entry['version']))


def marketplace_entry(ctx):
    """(entry or None, problem or None): this plugin's marketplace as Claude Code lists it."""
    code, out = ctx.run(['claude', 'plugin', 'marketplace', 'list', '--json'])
    try:
        listed = json.loads(out)
    except ValueError:
        listed = None
    if code or not isinstance(listed, list):
        return None, f'cannot read the marketplace list ({out[:200] or "exit " + str(code)})'
    return next((m for m in listed if isinstance(m, dict) and m.get('name') == MARKETPLACE), None), None


def remote_sha(ctx, ref):
    """The commit GitHub has on `ref` ('HEAD' = the default branch). (sha, None) or (None, why not)."""
    pattern = 'HEAD' if ref == 'HEAD' else f'refs/heads/{ref}'
    code, out = ctx.run(['git', 'ls-remote', GIT_URL, pattern])
    sha = out.split()[0] if out.split() else ''
    if code or not SHA.match(sha):
        return None, f'GitHub did not answer for {GIT_URL} {pattern} ({out[:200] or "exit " + str(code)})'
    return sha, None


def snapshot(home):
    settings = read_json(os.path.join(home, '.claude', 'settings.json')) or {}
    path = os.path.join(home, '.claude', 'adyusuf.json')
    config = None
    if os.path.isfile(path):
        with open(path, 'rb') as handle:
            config = handle.read()
    enabled = settings.get('enabledPlugins', {}).get(PLUGIN_ID) if isinstance(settings, dict) else None
    return {'config': config, 'enabled': enabled, 'path': path}


def back_up(ctx, before):
    if before['config'] is None:
        return
    folder = os.path.join(ctx.home, '.claude-standards', 'backups', f'plugin-setup-{ctx.stamp}')
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, 'adyusuf.json'), 'wb') as handle:
        handle.write(before['config'])
    ctx.say(f'  backup    {folder}/adyusuf.json')


def step(ctx, label, command):
    ctx.say(f'  {label}')
    code, out = ctx.run(command)
    for line in out.splitlines():
        ctx.say(f'    {line}')
    return code == 0


def keep_settings(ctx, before):
    """Put back anything the replacement disturbed. Returns the number of problems left."""
    problems = 0
    after = snapshot(ctx.home)
    if before['config'] is not None and after['config'] != before['config']:
        with open(before['path'], 'wb') as handle:
            handle.write(before['config'])
        ctx.say(f'  restored  {before["path"]} (the replacement changed it)')
    if before['enabled'] is False and after['enabled'] is not False:
        problems += not step(ctx, 'disabled before — disabling again', ['claude', 'plugin', 'disable', PLUGIN_ID])
    market, why = marketplace_entry(ctx)
    if market is None:
        ctx.say(f'  ✗ the marketplace link is gone ({why or MARKETPLACE})')
        problems += 1
    else:
        ctx.say('  ✓ settings, enabled state and marketplace link are as they were')
    return problems


def connect(ctx, market, ref):
    """The link to GitHub: add the marketplace if it is missing, otherwise pull its newest state."""
    if market is None:
        return step(ctx, f'linking the marketplace ({REPO}#{ref})',
                    ['claude', 'plugin', 'marketplace', 'add', f'{REPO}#{ref}'])
    return step(ctx, 'refreshing the marketplace from GitHub', ['claude', 'plugin', 'marketplace', 'update', MARKETPLACE])


def install(ctx, scope):
    return step(ctx, f'installing {PLUGIN_ID}', ['claude', 'plugin', 'install', PLUGIN_ID, '--scope', scope])


def finish(ctx, remote):
    entry = installed_entry(ctx.home)
    if entry is None or not is_current(entry, remote):
        ctx.say(f'✗ the plugin is not at {remote[:12]} after the run — retry: claude plugin install {PLUGIN_ID}')
        return 2
    ctx.say(f'✓ {PLUGIN_ID} {entry["version"]} is installed — open a NEW Claude Code session (or /reload-plugins)')
    return 0


def replace(ctx, entry, market, ref, remote):
    before = snapshot(ctx.home)
    back_up(ctx, before)
    if not connect(ctx, market, ref):
        ctx.say('✗ could not refresh the marketplace — nothing was removed')
        return 2
    if not step(ctx, 'removing the old version (its data is kept)',
                ['claude', 'plugin', 'uninstall', PLUGIN_ID, '--keep-data', '--scope', entry['scope']]):
        ctx.say('✗ could not remove the old version — nothing was installed')
        return 2
    if not install(ctx, entry['scope']):
        ctx.say(f'✗ the old version is removed but the new one failed — retry: claude plugin install {PLUGIN_ID}')
        return 2
    return 2 if keep_settings(ctx, before) else finish(ctx, remote)


def decide(ctx, args):
    market, why = marketplace_entry(ctx)
    if why:
        ctx.say(f'✗ {why}')
        return 2
    if market and market.get('source') != 'github':
        ctx.say(f'✗ {MARKETPLACE} is linked to a {market.get("source")} source, not GitHub — left as it is')
        return 2
    ref = (market.get('ref') or 'HEAD') if market else args.ref
    if market and ref != args.ref and args.ref != DEFAULT_REF:
        ctx.say(f'note: the marketplace is already linked to "{ref}"; it stays as it is, --ref {args.ref} is ignored')
    remote, why = remote_sha(ctx, ref)
    if why:
        ctx.say(f'✗ {why} — nothing was changed')
        return 2
    entry = installed_entry(ctx.home)
    ctx.say(f'GitHub    {ref} is at {remote[:12]}')
    ctx.say('installed ' + (f'{entry["version"] or "?"} ({entry["scope"]} scope)' if entry else 'not installed'))
    if entry and is_current(entry, remote):
        ctx.say('✓ the installed plugin is the newest')
        due = market is None
        if due and not args.check:
            connect(ctx, market, ref)
        return 1 if due and args.check else 0
    if args.check:
        ctx.say('! a new version is due' if entry else '! the plugin is not installed')
        return 1
    if entry is None:
        if not connect(ctx, market, ref):
            ctx.say('✗ could not link the marketplace — nothing was installed')
            return 2
        if not install(ctx, 'user'):
            ctx.say(f'✗ the install failed — retry: claude plugin install {PLUGIN_ID}')
            return 2
        return finish(ctx, remote)
    if not args.yes:
        if not ctx.tty:
            ctx.say('✗ a newer version exists but there is no terminal to ask on — rerun with --yes to replace it')
            return 2
        answer = ctx.ask(f'A newer version exists ({entry["version"] or "?"} -> {remote[:12]}). '
                         'Remove the old one and install the new one? [y/N] ')
        if answer.strip().lower() not in ('y', 'yes'):
            ctx.say('left as it is — nothing was changed')
            return 0
    return replace(ctx, entry, market, ref, remote)


def preflight(which):
    return [f'{tool} is not on PATH' for tool in ('claude', 'git') if not which(tool)]


def main(argv, ctx=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--ref', default=DEFAULT_REF)
    parser.add_argument('--home', default=os.path.expanduser('~'))
    args = parser.parse_args(argv)
    lines = []

    def say(text):
        lines.append(text)
        print(text, flush=True)

    ctx = ctx or types.SimpleNamespace(run=run, ask=input, tty=sys.stdin.isatty(), which=shutil.which)
    ctx.say, ctx.home = say, os.path.abspath(args.home)
    ctx.stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    if not REF_OK.match(args.ref):
        print(f'✗ --ref {args.ref!r} is not a branch name', file=sys.stderr)
        return 2
    missing = preflight(ctx.which)
    if missing:
        print('✗ ' + '; '.join(missing) + ' — nothing was changed', file=sys.stderr)
        return 2
    try:
        return decide(ctx, args)
    finally:
        if not args.check:
            folder = os.path.join(ctx.home, '.claude-standards', 'logs')
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, f'plugin-setup-{ctx.stamp}.log'), 'w', encoding='utf-8') as log:
                log.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
