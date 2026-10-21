#!/usr/bin/env python3
"""SessionStart hook of the adyusuf plugin: warn while the OLD, symlinked install is still on this machine.

Usage:  python3 scripts/legacy-install-check.py      (hooks/hooks.json runs it on SessionStart "startup")

The old install linked ~/.claude/{CLAUDE.md,agents,docs,modes,scripts,standards} and ~/.claude/skills/adyusuf
into a checkout and wrote hooks into ~/.claude/settings.json. Next to the plugin that means the global rules,
the role agents and the guard all load TWICE. The plugin cannot undo that itself (it never touches files
outside its own copy), so it says so — once, in one paragraph — and points at the command that does.

Silent when clean. Always exit 0: a check that blocks a session would be worse than the double load. A file
it cannot read is one line on stderr, never an exception. HOME is read from the environment (tests set it).
The LEGACY command list is imported from install-live-hooks.py and the link predicate from install.py, so the
warning names exactly what `install.py --remove` takes out (a dotfiles link at one of these names is not ours).
"""
import importlib.util
import os
import shlex
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
# The command runs THIS copy of install.py (the plugin's own), never the one in the old checkout: an older checkout's
# install.py may still do more than take the old install out.
REMOVE_COMMAND = 'python3 {script} --remove'


def home_dir():
    return os.environ.get('HOME') or os.path.expanduser('~')


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_hooks_module():
    return load_module('install_live_hooks', 'install-live-hooks.py')


def legacy_links(home, install=None):
    """The old install's links — install.py's own predicate, so a warning always clears after --remove."""
    install = install or load_module('adyusuf_install', 'install.py')
    return [link for link, _ in install.legacy_links(home)]


def legacy_settings(home, hooks):
    path = os.path.join(home, '.claude', 'settings.json')
    try:
        data, _ = hooks.load_settings(path)
    except (ValueError, OSError) as error:
        print(f'adyusuf legacy-install-check: cannot read {path}: {error}', file=sys.stderr)
        return []
    return hooks.legacy_commands(data)


def message(links, commands):
    found = []
    if links:
        found.append(f'{len(links)} symlink(s) under ~/.claude ({", ".join(os.path.basename(p) for p in links)})')
    if commands:
        found.append(f'{len(commands)} old hook entr{"y" if len(commands) == 1 else "ies"} in ~/.claude/settings.json')
    command = REMOVE_COMMAND.format(script=shlex.quote(os.path.join(HERE, 'install.py')))
    return (f'⚠️ adyusuf: the old symlinked install is still present next to the plugin — {" and ".join(found)}. '
            'Until it is removed the global rules, the role agents and the destructive-command guard load TWICE. '
            f'To finish the move, run: {command}  (then start a new session).')


def main():
    home = home_dir()
    try:
        links = legacy_links(home)
    except (ImportError, OSError, SyntaxError) as error:
        print(f'adyusuf legacy-install-check: cannot load install.py: {error}', file=sys.stderr)
        links = []
    try:
        hooks = load_hooks_module()
    except (ImportError, OSError, SyntaxError) as error:
        print(f'adyusuf legacy-install-check: cannot load install-live-hooks.py: {error}', file=sys.stderr)
        commands = []
    else:
        commands = legacy_settings(home, hooks)
    if links or commands:
        print(message(links, commands))
    return 0


if __name__ == '__main__':
    try:
        main()
    except Exception as error:                    # never block a session; say what went wrong instead
        print(f'adyusuf legacy-install-check: {type(error).__name__}: {error}', file=sys.stderr)
    sys.exit(0)
