#!/usr/bin/env python3
"""The claude-monitor agent, and the ONE way off the old linked install. The rule set itself is a plugin.

The adyusuf rule set is a standard Claude Code plugin (decision log, 13/10/2026: no symlinks, no install script).
Install it from inside Claude Code; /plugin update brings each promotion to prod:
    /plugin marketplace add adyusuf/claude-code-standards#prod
    /plugin install adyusuf@adyusuf-marketplace
This script links nothing and wires no hooks. What it still does:

Usage:
    python3 scripts/install.py                 # print the two /plugin commands, then the monitor agent on prod
    python3 scripts/install.py --test          # the same, the monitor agent connected to test
    python3 scripts/install.py --dev           # the same, the monitor agent connected to a LOCAL API
    python3 scripts/install.py --no-monitor    # only print the two /plugin commands
    python3 scripts/install.py --monitor-server URL   # another claude-monitor API than the channel's
    python3 scripts/install.py --monitor-sync  # re-derive the agent's ON/OFF from its connection (e.g. after logout)
    python3 scripts/install.py --check         # exit 1 while an old link or hook is left, or the plugin is missing
    python3 scripts/install.py --remove        # MIGRATION: take the old links and hooks out (backups stay)
    python3 scripts/install.py --remove --no-monitor  # the same, and the monitor agent stays installed
--prod is the default. --prod/--test/--dev only pick the monitor's server now; --with-monitor changes nothing.

--remove, the migration off the old install (it linked ~/.claude/{CLAUDE.md,agents,docs,modes,scripts,standards}
and ~/.claude/skills/adyusuf -> <checkout>/plugin, and wired hooks into settings.json):
    1. Removes each of those links that points into ANY checkout of this repository (a folder holding
       standards/00-working-method.md and modes/README.md), and each one whose target is gone — a dangling
       link holds nothing. A real file or folder is never touched, and neither is a link into anything else.
    2. Takes the legacy hooks out through install-live-hooks.py (settings.json is backed up first).
    3. Unless --no-monitor: uninstalls the monitor agent, as before.
    4. Puts back what the old install moved aside, from ~/.claude-standards/backups/ (never over an occupied place).
--check reads ~/.claude/plugins/installed_plugins.json for the adyusuf@adyusuf-marketplace entry; a missing file
or entry is "not installed" and fails the check. The monitor step: install_monitor.py builds cm-agent and connects
it to the channel's server; its plugin is ENABLED only while connected, otherwise DORMANT.
Log: install, --remove and --monitor-sync write their whole output to ~/.claude-standards/logs/install-<stamp>.log
as well as the console (--check is read-only and writes none).
Exit codes: 0 done · 1 --check found a problem · 2 refused or failed (nothing changed by the refused step).
"""
import argparse
import importlib.util
import os
import shutil
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_REPO = os.path.dirname(HERE)
LINKED = ('CLAUDE.md', 'agents', 'docs', 'modes', 'scripts', 'standards')
PLUGIN_LINK = os.path.join('skills', 'adyusuf')
PLUGIN_SOURCE = 'plugin'                               # what ~/.claude/skills/adyusuf pointed at, in the checkout
# Files every checkout of this repository has carried, old and new: how a link's target folder is recognised.
FINGERPRINT = (os.path.join('standards', '00-working-method.md'), os.path.join('modes', 'README.md'))
WINDOWS_BASH = (r'C:\Program Files\Git\bin\bash.exe', r'C:\Program Files (x86)\Git\bin\bash.exe')


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hooks = load('install_live_hooks', 'install-live-hooks.py')
safety = load('install_safety', 'install_safety.py')
PLUGIN_ID = hooks.PLUGIN_INSTALL.split()[-1]           # the id the install command names: one source


def find_bash(which=shutil.which, exists=os.path.exists, windows=os.name == 'nt'):
    found = which('bash')
    if found or not windows:
        return found
    return next((path for path in WINDOWS_BASH if exists(path)), None)


def preflight(which=shutil.which, windows=os.name == 'nt'):
    """(errors, warnings). An error stops before anything runs: the monitor step clones with git, and the plugin's
    own hooks run through bash and python3."""
    errors, warnings = [], []
    if sys.version_info < (3, 9):
        errors.append(f'Python 3.9+ is required, this is {sys.version.split()[0]}')
    if not which('git'):
        errors.append('git is not on PATH')
    if not find_bash(which, windows=windows):
        errors.append('bash not found — the plugin\'s hooks run through it (Windows: install Git for Windows)')
    note = hooks.python3_note(which)
    if 'warning' in note:
        warnings.append(note)
    return errors, warnings


def plugin_commands():
    print('the rule set is the adyusuf Claude Code plugin — install it from inside Claude Code:')
    print(f'  {hooks.MARKETPLACE_ADD}')
    print(f'  {hooks.PLUGIN_INSTALL}')


def is_checkout(folder):
    return all(os.path.isfile(os.path.join(folder, part)) for part in FINGERPRINT)


def legacy_links(home):
    """[(link, target)]: the old install's links in ~/.claude that point into a checkout of this repository, or
    whose target is gone. Only links: a real file or folder in one of these places is yours, never ours."""
    claude = os.path.join(home, '.claude')
    places = [(os.path.join(claude, name), name) for name in LINKED]
    places.append((os.path.join(claude, PLUGIN_LINK), PLUGIN_SOURCE))
    found = []
    for link, name in places:
        if not os.path.islink(link):
            continue
        # A relative target resolves from the link's folder; Windows' \\?\ prefix is dropped first.
        target = os.path.normpath(os.path.join(os.path.dirname(link), safety.shown(os.readlink(link))))
        if os.path.normcase(os.path.basename(target)) != os.path.normcase(name):
            continue                                      # not what the old install made here
        if not os.path.exists(target) or is_checkout(os.path.dirname(target)):
            found.append((link, target))
    return found


def unlink(link):
    """Remove a symlink, never its target. Windows removes a DIRECTORY symlink with rmdir only."""
    try:
        os.remove(link)
    except OSError:
        os.rmdir(link)


def remove_links(home):
    found = legacy_links(home)
    for link, target in found:
        unlink(link)
        print(f'  unlinked  {link} (-> {target})')
    if not found:
        print('  none      no link of the old install is left')


def flag_notices(args):
    """One line per flag that no longer does anything in this run."""
    notes = []
    if args.with_monitor:
        notes.append('--with-monitor changes nothing: the monitor is on by default')
    if args.channel and (args.check or args.remove or args.monitor_sync or args.no_monitor):
        notes.append(f'--{args.channel} only picks the monitor\'s server for an install; it changes nothing here')
    if args.repo != DEFAULT_REPO:
        notes.append('--repo changes nothing: no link points into a checkout any more')
    return notes


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
    parser.add_argument('--repo', default=DEFAULT_REPO, help=argparse.SUPPRESS)   # accepted; nothing links to it
    parser.add_argument('--home', default=os.path.expanduser('~'))
    args = parser.parse_args(argv)
    start, home, channel = os.path.realpath(args.repo), os.path.abspath(args.home), args.channel or 'prod'
    monitor = not args.no_monitor
    if hasattr(sys.stdout, 'reconfigure'):
        # A cp1252 console must not crash on ✓/—, and each line must land BEFORE the git/dotnet output that
        # follows it: a block-buffered pipe printed the steps after the build log (seen 04/10/2026).
        sys.stdout.reconfigure(errors='replace', line_buffering=True)
    for note in flag_notices(args):
        print(f'note: {note}')

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
        return check_all(start, home, monitor)
    return safety.logged(home, lambda: install_all(start, home, channel, monitor, args.monitor_server))


def remove_all(start, home, monitor):
    print('links:')
    remove_links(home)
    print('hooks:')
    code = hooks.remove(start, home)
    if monitor:
        load('install_monitor', 'install_monitor.py').remove(home=home)
    else:
        print('monitor: left installed (--no-monitor)')
    safety.restore_latest(home)                           # your CLAUDE.md and folders come back from the backup
    print(f'removed; every backup is kept in {safety.store(home, "backups")}')
    plugin_commands()
    return code


def check_all(start, home, monitor):
    print('old linked install (install.py --remove takes it out):')
    leftovers = legacy_links(home)
    for link, target in leftovers:
        print(f'  ✗ left    {link} -> {target}')
    if not leftovers:
        print('  ✓ no link of the old install is left')
    problems = len(leftovers) + len(hooks.report(start, home))
    installed, said = safety.plugin_installed(home, PLUGIN_ID)
    print(f'plugin: {"✓" if installed else "✗"} {said}')
    problems += not installed
    if monitor:
        problems += load('install_monitor', 'install_monitor.py').check(home=home)
    print('✓ everything is in place' if not problems else f'✗ {problems} problem(s)')
    return 1 if problems else 0


def install_all(start, home, channel, monitor, server_override):
    agent = load('install_monitor', 'install_monitor.py') if monitor else None
    server = (server_override or agent.SERVERS[channel]) if monitor else None
    print('choices:')
    print(f'  channel     {channel}  (--prod default · --test · --dev: the monitor\'s server only)')
    print(f'  monitor     {"on -> " + server if monitor else "off (--no-monitor)"}')
    print(f'  claude      {os.path.join(home, ".claude")}  (Claude Code found, writable)')
    errors, warnings = preflight()
    for warning in warnings:
        print(f'⚠️  {warning}')
    if errors:
        for error in errors:
            print(f'✗ {error}', file=sys.stderr)
        return 2
    plugin_commands()
    installed, said = safety.plugin_installed(home, PLUGIN_ID)
    print(f'  plugin      {"✓" if installed else "✗"} {said}')
    leftovers = len(legacy_links(home)) + len(hooks.report(start, home))
    if leftovers:
        print(f'⚠️  {leftovers} piece(s) of the old linked install are still here — run install.py --remove '
              'before installing the plugin, or the rules and the roles load twice')
    code = 0
    if monitor:
        print(f'monitor ({server}):')
        code = agent.install(server, home=home)
    print({0: '✓ done — open a NEW Claude Code session after installing the plugin'}.get(code,
                                                                                         f'✗ stopped (exit {code})'))
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
