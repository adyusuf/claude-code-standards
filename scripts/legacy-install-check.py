#!/usr/bin/env python3
"""SessionStart hook of the adyusuf plugin: warn while the OLD, symlinked install is still on this machine.

Usage:  python3 scripts/legacy-install-check.py      (hooks/hooks.json runs it on SessionStart "startup")

The old install linked ~/.claude/{CLAUDE.md,agents,docs,modes,scripts,standards} and ~/.claude/skills/adyusuf
into a checkout and wrote hooks into ~/.claude/settings.json. Next to the plugin that means the global rules,
the role agents and the guard all load TWICE. The plugin cannot undo that itself (it never touches files
outside its own copy), so it says so — once, in one paragraph — and points at the command that does.

Silent when clean. Always exit 0: a check that blocks a session would be worse than the double load. A file
it cannot read is one line on stderr, never an exception. HOME is read from the environment (tests set it).
The LEGACY command list is imported from install-live-hooks.py, so there is one list.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
LINKED = ('CLAUDE.md', 'agents', 'docs', 'modes', 'scripts', 'standards', os.path.join('skills', 'adyusuf'))
REMOVE_COMMAND = 'python3 {checkout}/scripts/install.py --remove --no-monitor'


def home_dir():
    return os.environ.get('HOME') or os.path.expanduser('~')


def load_hooks_module():
    spec = importlib.util.spec_from_file_location('install_live_hooks', os.path.join(HERE, 'install-live-hooks.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacy_links(home):
    paths = (os.path.join(home, '.claude', name) for name in LINKED)
    return [path for path in paths if os.path.islink(path)]


def checkout_of(links):
    """The checkout the old links point into: the parent of the first link's target, if it has install.py."""
    for link in links:
        candidate = os.path.dirname(os.path.realpath(link))
        if os.path.isfile(os.path.join(candidate, 'scripts', 'install.py')):
            return candidate
    return None


def legacy_settings(home, hooks):
    path = os.path.join(home, '.claude', 'settings.json')
    try:
        data, _ = hooks.load_settings(path)
    except (ValueError, OSError) as error:
        print(f'adyusuf legacy-install-check: cannot read {path}: {error}', file=sys.stderr)
        return []
    return hooks.legacy_commands(data)


def message(links, commands, checkout):
    found = []
    if links:
        found.append(f'{len(links)} symlink(s) under ~/.claude ({", ".join(os.path.basename(p) for p in links)})')
    if commands:
        found.append(f'{len(commands)} old hook entr{"y" if len(commands) == 1 else "ies"} in ~/.claude/settings.json')
    command = REMOVE_COMMAND.format(checkout=checkout or '<your claude-code-standards checkout>')
    return (f'⚠️ adyusuf: the old symlinked install is still present next to the plugin — {" and ".join(found)}. '
            'Until it is removed the global rules, the role agents and the destructive-command guard load TWICE. '
            f'To finish the move, run: {command}  (then start a new session).')


def main():
    home = home_dir()
    links = legacy_links(home)
    try:
        hooks = load_hooks_module()
    except (ImportError, OSError, SyntaxError) as error:
        print(f'adyusuf legacy-install-check: cannot load install-live-hooks.py: {error}', file=sys.stderr)
        commands = []
    else:
        commands = legacy_settings(home, hooks)
    if links or commands:
        print(message(links, commands, checkout_of(links)))
    return 0


if __name__ == '__main__':
    try:
        main()
    except Exception as error:                    # never block a session; say what went wrong instead
        print(f'adyusuf legacy-install-check: {type(error).__name__}: {error}', file=sys.stderr)
    sys.exit(0)
