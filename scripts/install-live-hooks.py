#!/usr/bin/env python3
"""The live hooks ship with the adyusuf plugin; this script only finds and removes the LEGACY set.

Usage:
    python3 scripts/install-live-hooks.py             # writes nothing: says how to install the plugin
    python3 scripts/install-live-hooks.py --check     # one line; exit 1 while a legacy entry or link is present
    python3 scripts/install-live-hooks.py --remove    # take the legacy entries and the link out again
    python3 scripts/install-live-hooks.py --home DIR  # act on another home directory (tests)

What the plugin wires (hooks/hooks.json, with "${CLAUDE_PLUGIN_ROOT}/scripts/..."):
    PreToolUse(Bash)                  ->  guard-destructive.sh    blocks the never-do commands
    PostToolUse(Edit|Write) and Stop  ->  md-hook.sh              the CLAUDE.md size ratchet + twin drift

What the plugin replaces (LEGACY): the entries this script and settings.example.json used to write into
~/.claude/settings.json, and the ~/.claude/hooks/guard-destructive.sh symlink into the checkout. Left in
place they run every hook TWICE — once from settings.json, once from the plugin.

The measurement Stop hook is deliberately NOT in this repository: it records per-session token and cost
metadata, which a published rule set has no business carrying. Its entry and its link are never touched here.

Safe by construction: settings.json is backed up to ~/.claude-standards/backups/settings before any change
(outside ~/.claude, whose cleanup prunes old files there), an unparsable settings.json aborts with nothing
touched, only the exact LEGACY command strings are removed (every other entry is kept), a real file where
the legacy link was is never deleted, and running it twice changes nothing.

--repo is still accepted (install.py passes it) and no longer used: nothing points into a checkout now.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_REPO = os.path.dirname(HERE)

MARKETPLACE_ADD = '/plugin marketplace add adyusuf/claude-code-standards#prod'
PLUGIN_INSTALL = '/plugin install adyusuf@adyusuf-marketplace'

# Every command string this script or settings.example.json ever registered (git log -p of both files).
# One list: legacy-install-check.py imports it.
LEGACY = frozenset((
    'bash "$HOME/.claude/hooks/guard-destructive.sh"',
    'bash "$HOME/.claude/scripts/guard-destructive.sh"',
    'bash "$HOME/.claude/scripts/md-hook.sh"',
))
# The links this script made, relative to ~/.claude. Removed only while they are symlinks.
LEGACY_LINKS = (os.path.join('hooks', 'guard-destructive.sh'),)


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


def hook_events(data):
    hooks = data.get('hooks') if isinstance(data, dict) else None
    return hooks if isinstance(hooks, dict) else {}


def legacy_commands(data):
    """The LEGACY command strings still registered in a parsed settings.json, in file order."""
    found = []
    for groups in hook_events(data).values():
        for group in groups if isinstance(groups, list) else []:
            hooks = group.get('hooks') if isinstance(group, dict) else None
            for hook in hooks if isinstance(hooks, list) else []:
                command = hook.get('command') if isinstance(hook, dict) else None
                if command in LEGACY:
                    found.append(command)
    return found


def legacy_links(home):
    paths = (os.path.join(home, '.claude', name) for name in LEGACY_LINKS)
    return [path for path in paths if os.path.islink(path)]


def strip_legacy(data):
    """Drop every LEGACY hook from `data` in place; prune the groups and events left empty. True if changed."""
    events = hook_events(data)
    changed = False
    for event in list(events):
        groups = events[event]
        if not isinstance(groups, list):
            continue
        kept = []
        for group in groups:
            hooks = group.get('hooks') if isinstance(group, dict) else None
            if not isinstance(hooks, list):
                kept.append(group)
                continue
            remaining = [h for h in hooks if not (isinstance(h, dict) and h.get('command') in LEGACY)]
            if len(remaining) != len(hooks):
                changed = True
                if not remaining:
                    continue                      # the group held only legacy hooks: drop the group
                group = {**group, 'hooks': remaining}
            kept.append(group)
        if kept:
            events[event] = kept
        else:
            del events[event]
    if changed and not events and isinstance(data.get('hooks'), dict):
        del data['hooks']
    return changed


def report(repo, home):
    """One line; returns the problems (legacy entries and links still present). `repo` is unused."""
    settings_path = os.path.join(home, '.claude', 'settings.json')
    try:
        data, _ = load_settings(settings_path)
    except (ValueError, OSError) as error:
        print(f'legacy hooks: settings.json is unreadable ({error})')
        return [settings_path]
    problems = legacy_commands(data) + legacy_links(home)
    if problems:
        print(f'legacy hooks: {len(problems)} still present (settings.json entries and ~/.claude/hooks links) '
              f'— they run next to the plugin\'s own; remove them: python3 {os.path.join(HERE, "install-live-hooks.py")} --remove')
    else:
        print('legacy hooks: none — the hooks come from the adyusuf plugin')
    return problems


def install(repo, home):
    """Writes nothing: the hooks are the plugin's now. `repo` and `home` are unused (install.py passes them)."""
    print('The live hooks ship with the adyusuf plugin; nothing is written to settings.json any more.')
    print('Install the plugin inside Claude Code:')
    print(f'  {MARKETPLACE_ADD}')
    print(f'  {PLUGIN_INSTALL}')
    print('An older install left hooks in settings.json? Remove them: install-live-hooks.py --remove')
    return 0


def remove(repo, home):
    settings_path = os.path.join(home, '.claude', 'settings.json')
    try:
        data, newline = load_settings(settings_path)
    except (ValueError, OSError) as error:
        print(f'refusing to continue — settings.json is unreadable: {error}', file=sys.stderr)
        return 2
    if strip_legacy(data):
        saved = backup(settings_path, backups_dir(home))
        save_settings(settings_path, data, newline)
        print('legacy hooks removed from settings.json' + (f' (backup: {saved})' if saved else ''))
    for link in legacy_links(home):
        os.remove(link)
        print(f'unlinked {link}')
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--remove', action='store_true')
    parser.add_argument('--repo', default=DEFAULT_REPO, help=argparse.SUPPRESS)    # accepted, unused
    parser.add_argument('--home', default=os.path.expanduser('~'))
    args = parser.parse_args(argv)
    repo, home = os.path.realpath(args.repo), os.path.abspath(args.home)
    if args.check:
        return 1 if report(repo, home) else 0
    return remove(repo, home) if args.remove else install(repo, home)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
