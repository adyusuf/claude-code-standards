#!/usr/bin/env python3
"""One command: make this checkout the live ~/.claude configuration (README Level 4).

Usage:
    python3 scripts/install.py                         # rules, standards, modes, docs, scripts, agents, plugin, hooks
    python3 scripts/install.py --with-monitor          # ... and the claude-monitor agent (cm-agent, built from source)
    python3 scripts/install.py --with-monitor --monitor-server URL   # ... and connect it (approve the code on the web)
    python3 scripts/install.py --check                 # report only; exit 1 if anything is missing or wrong
    python3 scripts/install.py --remove                # take the links and the hooks out again (backups stay)

Fresh machine, one line (Windows needs core.symlinks for plugin/, see SETUP.md §6):
    git clone -c core.symlinks=true https://github.com/adyusuf/claude-code-standards ~/ClaudeCode/claude-code-standards
    python3 ~/ClaudeCode/claude-code-standards/scripts/install.py

What it does, in order — and what it never does:
    1. Preflight: Python 3.9+, git, bash (Git Bash on Windows), plugin/ checked out as real symlinks. A failed
       preflight touches nothing.
    2. Links ~/.claude/{CLAUDE.md,agents,docs,modes,scripts,standards} and ~/.claude/skills/adyusuf (= plugin/)
       into this checkout. A real file or folder in the way is MOVED to ~/.claude/backups/<name>.<stamp> — never
       deleted, never overwritten. A link already pointing here is left alone; a link pointing elsewhere is
       re-pointed (a link holds no data).
    3. Wires the hooks through install-live-hooks.py (settings.json is backed up first).
    4. With --with-monitor: install_monitor.py (clone, dotnet publish, cm-agent install, optional login).
Exit codes: 0 done · 1 --check found a problem · 2 refused (nothing changed by the refused step) ·
3 installed but INCOMPLETE (a monitor step could not run; the output names it — never reported as done).
"""
import argparse
import datetime
import importlib.util
import os
import shutil
import subprocess
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
    branch = current_branch(repo)
    if branch and branch != 'prod':
        warnings.append(f'the checkout is on "{branch}", not prod — the live configuration should follow prod (#26)')
    note = hooks.python3_note(which)
    if 'warning' in note:
        warnings.append(note)
    return errors, warnings


def current_branch(repo):
    try:
        result = subprocess.run(['git', '-C', repo, 'symbolic-ref', '--short', 'HEAD'],
                                capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


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


def install_links(repo, home, stamp, symlink=os.symlink):
    backups = os.path.join(home, '.claude', 'backups')
    for link, source, is_dir in links(repo, home):
        current = state(link, source)
        if current == 'ok':
            print(f'  ok        {link}')
            continue
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if current == 'wrong-target':
            unlink(link)
        elif current == 'blocked':
            os.makedirs(backups, exist_ok=True)
            moved = os.path.join(backups, f'{os.path.basename(link)}.{stamp}')
            shutil.move(link, moved)
            print(f'  moved     {link} -> {moved}')
        make_link(link, source, is_dir, symlink)
        print(f'  linked    {link} -> {source}')


def remove_links(repo, home):
    for link, source, _is_dir in links(repo, home):
        if state(link, source) == 'ok':                     # only OUR links; anything else is not ours to remove
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
    parser.add_argument('--with-monitor', action='store_true')
    parser.add_argument('--monitor-server', help='connect cm-agent to this claude-monitor API (implies --with-monitor)')
    parser.add_argument('--repo', default=DEFAULT_REPO)
    parser.add_argument('--home', default=os.path.expanduser('~'))
    args = parser.parse_args(argv)
    repo, home = os.path.realpath(args.repo), os.path.abspath(args.home)
    monitor = args.with_monitor or bool(args.monitor_server)
    if hasattr(sys.stdout, 'reconfigure'):
        # A cp1252 console must not crash on ✓/—, and each line must land BEFORE the git/dotnet output that
        # follows it: a block-buffered pipe printed the steps after the build log (seen 04/10/2026).
        sys.stdout.reconfigure(errors='replace', line_buffering=True)

    if args.check:
        print(f'live configuration (repo: {repo})')
        problems = check(repo, home)
        if monitor:
            problems += load('install_monitor', 'install_monitor.py').check()
        print('✓ everything is in place' if not problems else f'✗ {problems} problem(s)')
        return 1 if problems else 0
    if args.remove:
        remove_links(repo, home)
        code = hooks.remove(repo, home)
        if monitor:
            load('install_monitor', 'install_monitor.py').remove()
        print('removed; anything moved aside is still in ~/.claude/backups')
        return code

    errors, warnings = preflight(repo)
    for warning in warnings:
        print(f'⚠️  {warning}')
    if errors:
        for error in errors:
            print(f'✗ {error}', file=sys.stderr)
        return 2
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    print('links:')
    install_links(repo, home, stamp)
    print('hooks:')
    code = hooks.install(repo, home)
    if code == 0 and monitor:
        print('monitor:')
        code = load('install_monitor', 'install_monitor.py').install(args.monitor_server)
    print({0: '✓ installed — open a NEW Claude Code session to load it',
           3: '⚠️  installed but INCOMPLETE — the step(s) marked above did not run'}.get(code, f'✗ stopped (exit {code})'))
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
