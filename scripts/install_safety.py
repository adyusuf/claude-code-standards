#!/usr/bin/env python3
"""What install.py checks, keeps and reports, so a person can answer — from the screen or the log alone —
"was Claude Code there, could it be written, is the plugin installed, and will the migration off the old linked
install bring my files back?" (user request 04/10/2026; the links themselves are gone since 13/10/2026).

    · the log            ~/.claude-standards/logs/install-<stamp>.log — the whole output, children's included
    · the backups        ~/.claude-standards/backups/install-<stamp>/ — written by the OLD linked install:
                         manifest.json (what was at every place before) and anything that stood in its way

Both live OUTSIDE ~/.claude on purpose. Claude Code prunes old files there on its own schedule
(cleanupPeriodDays), and a moved file keeps its old date: a CLAUDE.md set aside in ~/.claude/backups on
04/10/2026 was gone after Claude Code's next cleanup half an hour later. A backup that can vanish is not one.
    · the plugin         Claude Code's own record, ~/.claude/plugins/installed_plugins.json; a missing file or
                         entry reads "not installed", never as fine
    · restore            install.py --remove puts the items of those backups back where they were
"""
import datetime
import json
import os
import shutil
import sys
import tempfile


def store(home, *parts):
    """~/.claude-standards/...: this rule set's own backups and logs, where Claude Code's cleanup does not reach."""
    return os.path.join(home, '.claude-standards', *parts)


class Tee:
    """Writes to the console and to the install log alike."""

    def __init__(self, stream, log):
        self.stream, self.log = stream, log

    def write(self, text):
        self.stream.write(text)
        self.log.write(text)
        return len(text)

    def flush(self):
        self.stream.flush()
        self.log.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)


def logged(home, function):
    """Run `function` with everything it prints — and every child it streams — also in the log."""
    folder = store(home, 'logs')
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f'install-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}.log')
    saved = sys.stdout, sys.stderr
    with open(path, 'w', encoding='utf-8', buffering=1) as log:
        sys.stdout, sys.stderr = Tee(saved[0], log), Tee(saved[1], log)
        try:
            print(f'log: {path}')
            print(f'command: install.py {" ".join(sys.argv[1:])}')
            return function()
        finally:
            sys.stdout, sys.stderr = saved
            print(f'the full output is in {path}')


def claude_errors(home, which):
    """Claude Code must be installed and its folder writable — otherwise nothing is touched."""
    claude = os.path.join(home, '.claude')
    if not os.path.isdir(claude) and not which('claude'):
        return [f'Claude Code is not installed here: there is no {claude} and no `claude` on PATH. '
                'Install Claude Code and open it once, then run this again. Nothing was changed.']
    if not os.path.isdir(claude):
        return []                                       # the CLI is there; Claude Code makes the folder on its first run
    try:
        with tempfile.NamedTemporaryFile(dir=claude, prefix='.install-probe-'):
            pass
    except OSError as error:
        return [f'{claude} is not writable ({error}) — nothing was changed']
    return []


def restore_latest(home):
    """Put each moved-aside item back where it was, from the NEWEST backup that holds it, if its place is free.
    Not just the newest backup: a second install finds a link where your CLAUDE.md was and moves nothing, so the
    newest folder alone would never give your file back."""
    root = store(home, 'backups')
    folders = sorted((n for n in os.listdir(root) if n.startswith('install-')), reverse=True) \
        if os.path.isdir(root) else []
    done = set()
    for folder in (os.path.join(root, n) for n in folders):
        try:
            with open(os.path.join(folder, 'manifest.json'), encoding='utf-8') as handle:
                items = json.load(handle)['items']
        except (OSError, ValueError, KeyError) as error:
            print(f'  restore   {folder}: no readable manifest ({error}) — skipped')
            continue
        for name, item in sorted(items.items()):
            if name == 'settings.json' or 'backup' not in item or name in done:
                continue                                # settings.json is undone entry by entry, not overwritten
            done.add(name)
            place = os.path.join(home, '.claude', *name.split('/'))
            if os.path.lexists(place):
                print(f'  restore   {place} is occupied — left as it is; your copy stays in {item["backup"]}')
                continue
            os.makedirs(os.path.dirname(place), exist_ok=True)     # e.g. ~/.claude/skills gone since the install
            if os.path.isdir(item['backup']) and not os.path.islink(item['backup']):
                shutil.copytree(item['backup'], place, symlinks=True)
            else:
                shutil.copy2(item['backup'], place, follow_symlinks=False)
            print(f'  restored  {place}  (from {item["backup"]}; the backup is kept)')
    if not done:
        print('  restore   no install backup holds anything of yours — nothing to put back')


def shown(target):
    """A link target as a person reads it: Windows' extended-length prefix (\\\\?\\C:\\...) dropped."""
    return target[4:] if target.startswith('\\\\?\\') else target


def plugin_installed(home, plugin_id):
    """(installed, what was read) from Claude Code's record of installed plugins. A missing or unreadable file, or
    no entry for `plugin_id`, is "not installed" — what cannot be read is never counted as fine."""
    path = os.path.join(home, '.claude', 'plugins', 'installed_plugins.json')
    if not os.path.isfile(path):
        return False, f'not installed ({path} does not exist)'
    try:
        with open(path, encoding='utf-8') as handle:
            plugins = json.load(handle).get('plugins', {})
        entries = plugins.get(plugin_id) or []
    except (OSError, ValueError, AttributeError) as error:
        return False, f'not installed — {path} is unreadable ({error})'
    entries = [entries] if isinstance(entries, dict) else entries
    first = entries[0] if isinstance(entries, list) and entries and isinstance(entries[0], dict) else None
    if first is None:
        return False, f'not installed (no {plugin_id} entry in {path})'
    return True, (f'installed: {plugin_id} {first.get("version", "?")} ({first.get("scope", "?")} scope) '
                  f'at {first.get("installPath", "?")}')
