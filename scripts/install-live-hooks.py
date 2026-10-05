#!/usr/bin/env python3
"""Activate (or remove) the live hooks: symlinks under ~/.claude/hooks + entries in settings.json.

Usage:
    python3 scripts/install-live-hooks.py             # install, from the repository this file lives in
    python3 scripts/install-live-hooks.py --check     # report only; exit 1 if anything is missing or broken
    python3 scripts/install-live-hooks.py --remove    # take the hooks and the symlinks out again
    python3 scripts/install-live-hooks.py --repo DIR  # point the symlinks at another checkout (e.g. after a promotion)
    python3 scripts/install-live-hooks.py --home DIR  # act on another home directory (tests)

What it wires:
    PreToolUse(Bash)  ->  hooks/guard-destructive.sh          blocks the never-do commands

It used to wire a Stop hook for a measurement ledger as well. That tooling is
deliberately NOT in this repository: it records per-session token and cost metadata,
which a published rule set has no business carrying, and a ledger next to the rules
keeps session metadata on disk longer than the platform's own retention. If you run
something like it, wire it yourself and keep it outside the checkout.

Why symlinks in ~/.claude/hooks and not in ~/.claude/scripts: `scripts` is itself a
symlink into the PROD worktree, so a new file there would appear as untracked in prod
and collide with the file the next promotion brings. ~/.claude/hooks is a directory of
its own; its links point into the checkout you name with --repo (default: the one this
script lives in), so a change to a hook is live the moment it is in that checkout.

Safe by construction: settings.json is backed up to ~/.claude-standards/backups/settings
before any change (outside ~/.claude, whose cleanup prunes old files there), an unparsable settings.json aborts with nothing touched, a real file where a
symlink belongs is never overwritten, running it twice changes nothing, and other
entries in settings.json are preserved.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_REPO = os.path.dirname(HERE)

LINKS = ('guard-destructive.sh',)
HOOKS = (
    ('PreToolUse', 'Bash', 'bash "$HOME/.claude/hooks/guard-destructive.sh"'),
)


def entry(matcher, command):
    hook = {'hooks': [{'type': 'command', 'command': command}]}
    return {'matcher': matcher, **hook} if matcher else hook


def commands_in(entries):
    return {h.get('command') for e in entries for h in e.get('hooks', [])}


def load_settings(path):
    if not os.path.exists(path):
        return {}, True
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    return json.loads(text), text.endswith('\n')


def save_settings(path, data, trailing_newline):
    text = json.dumps(data, indent=2, ensure_ascii=False) + ('\n' if trailing_newline else '')
    temporary = f'{path}.{os.getpid()}.tmp'
    with open(temporary, 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.replace(temporary, path)


def backups_dir(home):
    """Where settings.json backups go: OUTSIDE ~/.claude. Claude Code prunes old files under ~/.claude on its
    own schedule (cleanupPeriodDays), and a CLAUDE.md backup kept there was gone half an hour later
    (04/10/2026). The same store install.py keeps its install backups in."""
    return os.path.join(home, '.claude-standards', 'backups', 'settings')


def backup(path, backups):
    if not os.path.exists(path):
        return None
    os.makedirs(backups, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    target = os.path.join(backups, f'settings.json.{stamp}.bak')
    shutil.copy2(path, target)
    return target


def same_path(a, b):
    """Path equality that survives Windows: os.readlink there returns the target with
    the extended-length prefix (\\\\?\\C:\\...), which made a correct link read as
    'wrong-target' and --check fail on every Windows install (seen 04/10/2026)."""
    def plain(path):
        return path[4:] if path.startswith('\\\\?\\') else path
    return os.path.normcase(plain(a)) == os.path.normcase(plain(b))


def link_state(link, source):
    """ok | missing | wrong-target | broken | blocked (a real file is in the way)."""
    if os.path.islink(link):
        if not same_path(os.readlink(link), source):
            return 'wrong-target'
        return 'ok' if os.path.exists(source) else 'broken'
    return 'blocked' if os.path.exists(link) else 'missing'


def plan(repo, home):
    claude = os.path.join(home, '.claude')
    hooks_dir = os.path.join(claude, 'hooks')
    links = [(os.path.join(hooks_dir, name), os.path.join(repo, 'scripts', name)) for name in LINKS]
    return claude, hooks_dir, links


def report(repo, home):
    claude, _hooks_dir, links = plan(repo, home)
    problems = []
    for link, source in links:
        state = link_state(link, source)
        print(f'  link {os.path.relpath(link, home)}: {state}')
        if state != 'ok':
            problems.append(link)
    settings_path = os.path.join(claude, 'settings.json')
    try:
        data, _ = load_settings(settings_path)
    except (ValueError, OSError) as error:
        print(f'  settings.json: unreadable ({error})')
        return problems + [settings_path]
    for event, _matcher, command in HOOKS:
        present = command in commands_in(data.get('hooks', {}).get(event, []))
        print(f'  hook {event}: {"registered" if present else "MISSING"}')
        if not present:
            problems.append(event)
    print(f'  {python3_note()}')
    return problems


def python3_note(which=shutil.which):
    """A WARNING, not a problem: the guard falls back to `python`, but other hooks people
    wire (the live board's, for one) call `python3` by name and fail silently without it."""
    if which('python3'):
        return 'python3: on PATH'
    if which('python'):
        return ('python3: NOT on PATH (warning) — the guard falls back to `python`, but hooks that '
                'call python3 by name (e.g. the live board) will not run. On Windows: '
                'mklink /H "<python dir>\\python3.exe" "<python dir>\\python.exe"')
    return 'python3: NOT on PATH and no python either (warning) — the guard will block every keyword-bearing command'


def install(repo, home):
    claude, hooks_dir, links = plan(repo, home)
    settings_path = os.path.join(claude, 'settings.json')
    try:
        data, newline = load_settings(settings_path)          # parse first: abort before touching anything
    except (ValueError, OSError) as error:
        print(f'refusing to continue — settings.json is unreadable: {error}', file=sys.stderr)
        return 2
    for link, source in links:
        if not os.path.exists(source):
            print(f'refusing to continue — {source} does not exist (wrong --repo?)', file=sys.stderr)
            return 2
        if link_state(link, source) == 'blocked':
            print(f'refusing to continue — {link} is a real file, not a symlink', file=sys.stderr)
            return 2
    os.makedirs(hooks_dir, exist_ok=True)
    for link, source in links:
        if link_state(link, source) in ('wrong-target', 'broken'):
            os.remove(link)
        if not os.path.lexists(link):
            os.symlink(source, link)
            print(f'linked {link} -> {source}')
    changed = False
    hooks = data.setdefault('hooks', {})
    for event, matcher, command in HOOKS:
        if command not in commands_in(hooks.get(event, [])):
            hooks.setdefault(event, []).append(entry(matcher, command))
            changed = True
            print(f'registered {event}: {command}')
    if changed:
        saved = backup(settings_path, backups_dir(home))
        save_settings(settings_path, data, newline)
        print(f'settings.json updated' + (f' (backup: {saved})' if saved else ''))
    else:
        print('settings.json already up to date')
    return 0


def remove(repo, home):
    claude, _hooks_dir, links = plan(repo, home)
    settings_path = os.path.join(claude, 'settings.json')
    try:
        data, newline = load_settings(settings_path)
    except (ValueError, OSError) as error:
        print(f'refusing to continue — settings.json is unreadable: {error}', file=sys.stderr)
        return 2
    changed = False
    for event, _matcher, command in HOOKS:
        kept = []
        for item in data.get('hooks', {}).get(event, []):
            remaining = [h for h in item.get('hooks', []) if h.get('command') != command]
            if len(remaining) != len(item.get('hooks', [])):
                changed = True
                if not remaining:
                    continue                      # the entry held only our hook: drop the entry
                item = {**item, 'hooks': remaining}
            kept.append(item)
        if event in data.get('hooks', {}):
            data['hooks'][event] = kept
            if not kept:
                del data['hooks'][event]
    if changed:
        backup(settings_path, backups_dir(home))
        save_settings(settings_path, data, newline)
        print('hooks removed from settings.json')
    for link, _source in links:
        if os.path.islink(link):
            os.remove(link)
            print(f'unlinked {link}')
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--remove', action='store_true')
    parser.add_argument('--repo', default=DEFAULT_REPO)
    parser.add_argument('--home', default=os.path.expanduser('~'))
    args = parser.parse_args(argv)
    repo, home = os.path.realpath(args.repo), os.path.abspath(args.home)
    if args.check:
        print(f'live hooks (repo: {repo})')
        problems = report(repo, home)
        print('✓ all live hooks are in place' if not problems else f'✗ {len(problems)} problem(s)')
        return 1 if problems else 0
    return remove(repo, home) if args.remove else install(repo, home)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
