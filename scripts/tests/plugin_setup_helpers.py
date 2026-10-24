"""Shared by the test_plugin_setup*.py files: the module under test, a recording fake for `claude` and `git`, a temp home.

Nothing here touches the network or the real ~/.claude.
"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('plugin_setup', os.path.join(os.path.dirname(HERE), 'plugin-setup.py'))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

OLD = '08627d64acff478bb44dff2f9148f1b33f0885b8'
NEW = 'a6879d0e53e9157d99fb9dbdca6ed8fab36db598'
CONFIG = b'{"mode": "C"}\n'


def github_market(ref='prod', source='github'):
    return {'name': setup.MARKETPLACE, 'source': source, 'repo': setup.REPO, 'ref': ref}




class Fake:
    """Stands in for `claude` and `git`. Records every command and keeps installed_plugins.json truthful."""

    def __init__(self, home, remote=NEW, installed=None, market=None, fail=(), stale=False):
        self.home, self.remote, self.market, self.fail, self.stale = home, remote, market, set(fail), stale
        self.commands = []
        self.record = os.path.join(home, '.claude', 'plugins', 'installed_plugins.json')
        os.makedirs(os.path.dirname(self.record), exist_ok=True)
        self.write(installed)

    def write(self, sha, scope='user'):
        plugins = {} if sha is None else {setup.PLUGIN_ID: [
            {'scope': scope, 'version': sha[:12], 'gitCommitSha': sha, 'installPath': '/cache'}]}
        with open(self.record, 'w', encoding='utf-8') as handle:
            json.dump({'version': 2, 'plugins': plugins}, handle)

    def verbs(self):
        return [' '.join(c[:3]) if c[0] == 'claude' else c[0] for c in self.commands]

    def __call__(self, command):
        self.commands.append(command)
        key = ' '.join(command[:4]) if command[0] == 'claude' else command[0]
        if any(key.startswith(f) for f in self.fail):
            return 1, f'boom: {key}'
        if command[0] == 'git':
            return 0, f'{self.remote}\trefs/heads/prod'
        verb = command[2]
        if verb == 'marketplace':
            return self.marketplace(command[3])
        if verb == 'uninstall':
            self.write(None)
        elif verb == 'install':
            self.write(OLD if self.stale else NEW)
            self.enable()
            self.disturb()
        return 0, f'ok {verb}'

    def marketplace(self, action):
        if action == 'list':
            return 0, json.dumps([self.market] if self.market else [])
        if action == 'add':
            self.market = github_market()
        return 0, f'ok {action}'

    def enable(self):
        """A fresh install marks the plugin enabled, whatever it was before."""
        path = os.path.join(self.home, '.claude', 'settings.json')
        if os.path.isfile(path):
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump({'enabledPlugins': {setup.PLUGIN_ID: True}}, handle)

    def disturb(self):
        """What a bad replacement could do: wipe the user's settings and mark the plugin enabled."""
        if getattr(self, 'wipe', False):
            os.remove(os.path.join(self.home, '.claude', 'adyusuf.json'))


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = self.tmp.name

    def settings(self, config=CONFIG, enabled=True):
        os.makedirs(os.path.join(self.home, '.claude'), exist_ok=True)
        if config is not None:
            with open(os.path.join(self.home, '.claude', 'adyusuf.json'), 'wb') as handle:
                handle.write(config)
        with open(os.path.join(self.home, '.claude', 'settings.json'), 'w', encoding='utf-8') as handle:
            json.dump({'enabledPlugins': {setup.PLUGIN_ID: enabled}}, handle)

    def go(self, fake, *args, answer='y', tty=True, which=lambda tool: f'/bin/{tool}', existing=()):
        ctx = types.SimpleNamespace(run=fake, ask=lambda prompt: answer, tty=tty, which=which,
                                    exists=lambda path: path in existing, probe=lambda path: True)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = setup.main(['--home', self.home, *args], ctx)
        return code, out.getvalue(), err.getvalue()

    def logs(self):
        folder = os.path.join(self.home, '.claude-standards', 'logs')
        return os.listdir(folder) if os.path.isdir(folder) else []
