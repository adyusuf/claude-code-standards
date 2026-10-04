#!/usr/bin/env python3
"""What install.py checks, keeps and reports, so a person can answer — from the screen or the log alone —
"was Claude Code there, could it be written, what was backed up and where, what did CLAUDE.md become, did the
plugin and skills load, and will an uninstall bring my files back?" (user request 04/10/2026).

    · the log            ~/.claude-standards/logs/install-<stamp>.log — the whole output, children's included
    · the backup         ~/.claude-standards/backups/install-<stamp>/ — manifest.json (what was at every place
                         before, with size and sha256), settings.json as it was, and anything that stood in the way

Both live OUTSIDE ~/.claude on purpose. Claude Code prunes old files there on its own schedule
(cleanupPeriodDays), and a moved file keeps its old date: a CLAUDE.md set aside in ~/.claude/backups on
04/10/2026 was gone after Claude Code's next cleanup half an hour later. A backup that can vanish is not one.
    · verification       every backed-up item is re-hashed after the move: the backup is proven, not assumed
    · the report         CLAUDE.md (where it points, readable, same bytes as the checkout), plugin, commands,
                         skills, agent roles
    · restore            install.py --remove puts the items of the latest backup back where they were
"""
import datetime
import hashlib
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
        return []                                       # the CLI is there; the folder is made by the install
    try:
        with tempfile.NamedTemporaryFile(dir=claude, prefix='.install-probe-'):
            pass
    except OSError as error:
        return [f'{claude} is not writable ({error}) — nothing was changed']
    return []


def digest(path):
    """sha256 of a file, or of a folder's relative paths and file contents (so a moved folder can be proven)."""
    hasher = hashlib.sha256()
    if os.path.isfile(path):
        with open(path, 'rb') as handle:
            hasher.update(handle.read())
        return hasher.hexdigest()
    for base, dirs, names in os.walk(path):
        dirs.sort()
        # A link inside the folder is hashed as a link (its target), never followed: a broken one crashed the
        # install, and a move keeps links as links (shutil.move, copytree(symlinks=True)) — so must the proof.
        linked = [name for name in dirs if os.path.islink(os.path.join(base, name))]
        for name in sorted(names + linked):
            full = os.path.join(base, name)
            hasher.update(os.path.relpath(full, path).replace(os.sep, '/').encode())
            if os.path.islink(full):
                hasher.update(b'link:' + os.readlink(full).encode())
                continue
            with open(full, 'rb') as handle:
                hasher.update(handle.read())
    return hasher.hexdigest()


def describe(path):
    if os.path.islink(path):
        return {'kind': 'link', 'target': os.readlink(path)}
    if os.path.isfile(path):
        return {'kind': 'file', 'bytes': os.path.getsize(path), 'sha256': digest(path)}
    if os.path.isdir(path):
        return {'kind': 'folder', 'sha256': digest(path)}
    return {'kind': 'missing'}


class Backup:
    """One folder per install, created before anything changes."""

    def __init__(self, home, stamp):
        self.claude = os.path.join(home, '.claude')
        base = store(home, 'backups', f'install-{stamp}')
        # Never reuse a folder: two installs in one second would overwrite the first manifest, and with it the
        # only record of where your CLAUDE.md went.
        self.folder, n = base, 1
        while os.path.exists(self.folder):
            n += 1
            self.folder = f'{base}-{n}'
        self.items = {}
        os.makedirs(self.folder)

    def record(self, link):
        self.items[os.path.relpath(link, self.claude).replace(os.sep, '/')] = describe(link)

    def move_aside(self, link):
        name = os.path.relpath(link, self.claude).replace(os.sep, '/')
        destination = os.path.join(self.folder, *name.split('/'))
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        # The manifest is written BEFORE the move: a step that fails after it (Windows refusing the symlink, for
        # one) used to leave your file in the backup with no manifest naming it, and --remove said "nothing to
        # put back". A move that fails leaves the original in place, which restore then finds occupied.
        self.items[name]['backup'] = destination
        self.save()
        shutil.move(link, destination)
        return destination

    def copy_settings(self):
        source = os.path.join(self.claude, 'settings.json')
        if os.path.isfile(source):
            self.items['settings.json'] = dict(describe(source), backup=os.path.join(self.folder, 'settings.json'))
            shutil.copy2(source, self.items['settings.json']['backup'])

    def save(self):
        with open(os.path.join(self.folder, 'manifest.json'), 'w', encoding='utf-8') as handle:
            json.dump({'items': self.items}, handle, indent=2)

    def verify(self):
        """[(name, proven, where)] — every backed-up copy re-hashed against what was recorded before."""
        return [(name, os.path.exists(item['backup']) and digest(item['backup']) == item['sha256'], item['backup'])
                for name, item in sorted(self.items.items()) if 'backup' in item]


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


def report(home, repo, backup):
    """The answers, after an install. Returns the number of problems found."""
    claude, problems = os.path.join(home, '.claude'), 0
    print('report:')
    link, source = os.path.join(claude, 'CLAUDE.md'), os.path.join(repo, 'CLAUDE.md')
    readable = os.path.isfile(link) and digest(link) == digest(source)
    with open(source, encoding='utf-8') as handle:
        lines = sum(1 for _ in handle)
    print(f'  CLAUDE.md   {link} -> {shown(os.readlink(link)) if os.path.islink(link) else "NOT A LINK"}')
    print(f'              {"✓ readable, identical to the checkout" if readable else "✗ NOT readable as the checkout"}'
          f' ({lines} lines). Nothing was written INTO a file of yours: it is a link to the rules.')
    problems += not readable
    before = backup.items.get('CLAUDE.md', {'kind': 'missing'})
    if 'backup' in before:
        print(f'              your previous CLAUDE.md ({before.get("bytes", "?")} bytes) is in {before["backup"]}')
    else:
        print(f'              before: {before["kind"]}{" -> " + shown(before["target"]) if before["kind"] == "link" else ""}'
              ' — nothing of yours was replaced')
    for name, proven, where in backup.verify():
        print(f'  backup      {"✓ proven" if proven else "✗ DIFFERS"}  {name} -> {where}')
        problems += not proven
    plugin = os.path.join(claude, 'skills', 'adyusuf')
    try:
        with open(os.path.join(plugin, '.claude-plugin', 'plugin.json'), encoding='utf-8') as handle:
            manifest = json.load(handle)
        skills = sorted(n for n in os.listdir(os.path.join(plugin, 'skills'))
                        if os.path.isfile(os.path.join(plugin, 'skills', n, 'SKILL.md')))
        commands = sorted(n[:-3] for n in os.listdir(os.path.join(plugin, 'commands')) if n.endswith('.md'))
        print(f'  plugin      ✓ {manifest["name"]} {manifest.get("version", "")} at {plugin}')
        print(f'  skills      ✓ {len(skills)}: ' + ', '.join(f'/{manifest["name"]}:{s}' for s in skills))
        print(f'  commands    ✓ {len(commands)}: ' + ', '.join(f'/{manifest["name"]}:{c}' for c in commands))
    except (OSError, ValueError, KeyError) as error:
        print(f'  plugin      ✗ not loadable from {plugin}: {error}')
        problems += 1
    agents = os.path.join(claude, 'agents')
    roles = sorted(n[:-3] for n in os.listdir(agents) if n.endswith('.md')) if os.path.isdir(agents) else []
    print(f'  agents      {"✓" if roles else "✗"} {len(roles)} roles: {", ".join(roles)}')
    problems += not roles
    print(f'  backup      {backup.folder}  (install.py --remove puts these back)')
    return problems
