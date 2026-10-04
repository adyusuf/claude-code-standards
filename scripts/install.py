#!/usr/bin/env python3
"""One command: make this checkout the live ~/.claude configuration (README Level 4).

Usage:
    python3 scripts/install.py                 # everything, from PROD, with the monitor agent connected to prod
    python3 scripts/install.py --test          # the same from the TEST branch, the agent connected to test
    python3 scripts/install.py --dev           # the same from the DEV branch, the agent connected to a LOCAL API
    python3 scripts/install.py --no-monitor    # rules, standards, modes, docs, scripts, agents, plugin, hooks only
    python3 scripts/install.py --monitor-server URL   # another claude-monitor API than the channel's
    python3 scripts/install.py --monitor-sync  # re-derive the agent's ON/OFF from its connection (e.g. after logout)
    python3 scripts/install.py --check         # report only; exit 1 if anything is missing or wrong
    python3 scripts/install.py --remove        # take the links and the hooks out again (backups stay)
--prod is the default; --with-monitor is accepted and changes nothing (the monitor is on by default).

Fresh machine, one line (Windows needs core.symlinks for plugin/, see SETUP.md §6):
    git clone -c core.symlinks=true https://github.com/adyusuf/claude-code-standards ~/ClaudeCode/claude-code-standards
    python3 ~/ClaudeCode/claude-code-standards/scripts/install.py

What it does, in order — and what it never does:
    1. Picks the checkout of the channel's branch (install_channel.py): this one if it is on that branch, else
       an existing worktree on it, else a new worktree beside it. Your own checkout is never switched.
    2. Preflight: Python 3.9+, git, bash (Git Bash on Windows), plugin/ checked out as real symlinks. A failed
       preflight changes nothing but leaves its log.
    3. Links ~/.claude/{CLAUDE.md,agents,docs,modes,scripts,standards} and ~/.claude/skills/adyusuf (= plugin/)
       into that checkout. A real file or folder in the way is MOVED to ~/.claude-standards/backups/ —
       never deleted, never overwritten. A link already pointing there is left alone; a link pointing elsewhere
       is re-pointed (a link holds no data).
    4. Wires the hooks through install-live-hooks.py (settings.json is backed up first).
    5. Unless --no-monitor: install_monitor.py builds cm-agent and connects it to the channel's server (a code
       to approve on the web; skipped when already connected there). The agent's plugin is ENABLED only while
       connected; otherwise it is DISABLED (no hooks, no agent, nothing queued) and the output says DORMANT.
Log: install, --remove and --monitor-sync write their whole output, git/dotnet/cm-agent included, to
~/.claude-standards/logs/install-<stamp>.log as well as the console (--check is read-only and writes none).
Exit codes: 0 done · 1 --check found a problem · 2 refused or failed (nothing changed by the refused step).
"""
import argparse
import datetime
import importlib.util
import os
import shutil
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_REPO = os.path.dirname(HERE)
LINKED = ('CLAUDE.md', 'agents', 'docs', 'modes', 'scripts', 'standards')
PLUGIN_LINK = os.path.join('skills', 'adyusuf')
WINDOWS_BASH = (r'C:\Program Files\Git\bin\bash.exe', r'C:\Program Files (x86)\Git\bin\bash.exe')


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hooks = load('install_live_hooks', 'install-live-hooks.py')
channels = load('install_channel', 'install_channel.py')
safety = load('install_safety', 'install_safety.py')


def links(repo, home):
    """[(link path in ~/.claude, source in the checkout, is a directory)]."""
    claude = os.path.join(home, '.claude')
    pairs = [(os.path.join(claude, name), os.path.join(repo, name)) for name in LINKED]
    pairs.append((os.path.join(claude, PLUGIN_LINK), os.path.join(repo, 'plugin')))
    return [(link, source, os.path.isdir(source)) for link, source in pairs]


def find_bash(which=shutil.which, exists=os.path.exists, windows=os.name == 'nt'):
    found = which('bash')
    if found or not windows:
        return found
    return next((path for path in WINDOWS_BASH if exists(path)), None)


def preflight(repo, which=shutil.which, windows=os.name == 'nt'):
    """(errors, warnings). An error stops the install before anything is touched."""
    errors, warnings = [], []
    if sys.version_info < (3, 9):
        errors.append(f'Python 3.9+ is required, this is {sys.version.split()[0]}')
    if not which('git'):
        errors.append('git is not on PATH')
    if not find_bash(which, windows=windows):
        errors.append('bash not found — the hooks run through it (Windows: install Git for Windows)')
    for _link, source, _is_dir in links(repo, os.path.expanduser('~')):
        if not os.path.exists(source):
            errors.append(f'{source} does not exist (wrong --repo?)')
    for part in ('commands', 'skills'):
        path = os.path.join(repo, 'plugin', part)
        if os.path.exists(path) and not os.path.isdir(path):
            errors.append(f'plugin/{part} is a plain file, not a symlink: the checkout was made without symlinks. '
                          f'Fix: git -C "{repo}" config core.symlinks true && git -C "{repo}" checkout -- plugin '
                          '(Windows: as administrator or with Developer Mode on)')
    note = hooks.python3_note(which)
    if 'warning' in note:
        warnings.append(note)
    return errors, warnings


def state(link, source):
    """ok | missing | wrong-target | blocked (a real file or folder is in the way)."""
    if os.path.islink(link):
        return 'ok' if hooks.same_path(os.readlink(link), source) else 'wrong-target'
    return 'blocked' if os.path.exists(link) else 'missing'


def make_link(link, source, is_dir, symlink=os.symlink):
    try:
        symlink(source, link, target_is_directory=is_dir)
    except OSError as error:
        if getattr(error, 'winerror', None) == 1314:        # ERROR_PRIVILEGE_NOT_HELD
            raise SystemExit('refusing to continue — Windows would not create a symlink: turn on Developer Mode '
                             '(Settings > System > For developers) or run this from an administrator shell') from error
        raise


def unlink(link):
    """Remove a symlink, never its target. Windows removes a DIRECTORY symlink with rmdir only."""
    try:
        os.remove(link)
    except OSError:
        os.rmdir(link)


def install_links(repo, home, backup, symlink=os.symlink):
    for link, source, is_dir in links(repo, home):
        backup.record(link)                               # what was there BEFORE, into the manifest
        current = state(link, source)
        if current == 'ok':
            print(f'  ok        {link}')
            continue
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if current == 'wrong-target':
            unlink(link)
        elif current == 'blocked':
            print(f'  moved     {link} -> {backup.move_aside(link)}')
        make_link(link, source, is_dir, symlink)
        print(f'  linked    {link} -> {source}')


def remove_links(repos, home):
    """Our links into ANY of `repos` (the prod and test checkouts): an install from either is undone."""
    for repo in repos:
        for link, source, _is_dir in links(repo, home):
            if state(link, source) == 'ok':                 # only OUR links; anything else is not ours to remove
                unlink(link)
                print(f'  unlinked  {link}')


def check(repo, home):
    problems = 0
    for link, source, _is_dir in links(repo, home):
        current = state(link, source)
        print(f'  {current:<12}{link}')
        problems += current != 'ok'
    problems += len(hooks.report(repo, home))
    return problems


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--remove', action='store_true')
    branch = parser.add_mutually_exclusive_group()
    branch.add_argument('--prod', dest='channel', action='store_const', const='prod', help='the default')
    branch.add_argument('--test', dest='channel', action='store_const', const='test')
    branch.add_argument('--dev', dest='channel', action='store_const', const='dev', help='its monitor API is local')
    parser.add_argument('--no-monitor', action='store_true', help='skip the claude-monitor agent')
    parser.add_argument('--with-monitor', action='store_true', help=argparse.SUPPRESS)    # the default; kept
    parser.add_argument('--monitor-server', help="a claude-monitor API other than the channel's")
    parser.add_argument('--monitor-sync', action='store_true',
                        help="switch the agent's plugin on or off to match its connection, nothing else")
    parser.add_argument('--repo', default=DEFAULT_REPO)
    parser.add_argument('--home', default=os.path.expanduser('~'))
    args = parser.parse_args(argv)
    start, home, channel = os.path.realpath(args.repo), os.path.abspath(args.home), args.channel or 'prod'
    monitor = not args.no_monitor
    if hasattr(sys.stdout, 'reconfigure'):
        # A cp1252 console must not crash on ✓/—, and each line must land BEFORE the git/dotnet output that
        # follows it: a block-buffered pipe printed the steps after the build log (seen 04/10/2026).
        sys.stdout.reconfigure(errors='replace', line_buffering=True)

    # FIRST, before even the log (in ~/.claude-standards/logs): no Claude Code, or no access to it, stops here
    # with nothing created — not a log folder, not a backup.
    refused = safety.claude_errors(home, shutil.which)
    if refused and not args.check:
        for error in refused:
            print(f'✗ {error}', file=sys.stderr)
        return 2
    if args.monitor_sync:
        return safety.logged(home, lambda: load('install_monitor', 'install_monitor.py').sync(home=home))
    if args.remove:
        return safety.logged(home, lambda: remove_all(start, home, monitor))
    if args.check:                                        # read-only: no log
        return check_all(start, home, channel, monitor)
    return safety.logged(home, lambda: install_all(start, home, channel, monitor, args.monitor_server))


def remove_all(start, home, monitor):
    known = [path for path, _ in (channels.resolve(start, name, create=False) for name in channels.CHANNELS)]
    remove_links([start] + [path for path in known if path], home)
    code = hooks.remove(start, home)
    if monitor:
        load('install_monitor', 'install_monitor.py').remove(home=home)
    safety.restore_latest(home)                           # your CLAUDE.md and folders come back from the backup
    print(f'removed; every backup is kept in {safety.store(home, "backups")}')
    return code


def check_all(start, home, channel, monitor):
    repo, said = channels.resolve(start, channel, create=False)
    if repo is None:
        print(f'✗ {said}', file=sys.stderr)
        return 1
    print(f'channel {channel}: {said}')
    problems = check(repo, home)
    if monitor:
        problems += load('install_monitor', 'install_monitor.py').check(home=home)
    print('✓ everything is in place' if not problems else f'✗ {problems} problem(s)')
    return 1 if problems else 0


def install_all(start, home, channel, monitor, server_override):
    repo, said = channels.resolve(start, channel)
    if repo is None:
        print(f'✗ {said}', file=sys.stderr)
        return 2
    agent = load('install_monitor', 'install_monitor.py') if monitor else None
    server = (server_override or agent.SERVERS[channel]) if monitor else None
    print('choices:')
    print(f'  channel     {channel}  (--prod default · --test · --dev)')
    print(f'  rules from  {said}')
    print(f'  monitor     {"on -> " + server if monitor else "off (--no-monitor)"}')
    print(f'  claude      {os.path.join(home, ".claude")}  (Claude Code found, writable)')
    errors, warnings = preflight(repo)
    for warning in warnings:
        print(f'⚠️  {warning}')
    if errors:
        for error in errors:
            print(f'✗ {error}', file=sys.stderr)
        return 2
    backup = safety.Backup(home, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    print(f'  backup      {backup.folder}')
    backup.copy_settings()                                # BEFORE the hooks touch settings.json
    print('links:')
    install_links(repo, home, backup)
    backup.save()
    print('hooks:')
    code = hooks.install(repo, home)
    problems = safety.report(home, repo, backup)
    if code == 0 and monitor:
        print(f'monitor ({server}):')
        code = agent.install(server, home=home)
        if code:
            print('  the rules above ARE installed; only the monitor step failed (--no-monitor skips it)')
    if code == 0 and problems:
        code = 1
    print({0: '✓ installed — open a NEW Claude Code session to load it'}.get(code, f'✗ stopped (exit {code})'))
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
