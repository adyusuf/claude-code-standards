"""scripts/install.py — the plugin-era install: it prints the two /plugin commands and runs only the monitor step.

Since 13/10/2026 the rule set is a Claude Code plugin. A plain run (and --prod/--test/--dev) must link nothing and
touch no settings.json; --remove (test_install_remove.py) and --check (test_install_check.py) deal with what the
OLD linked install left behind. The shared Fixture below builds a temp HOME and a fake checkout of this repository.
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
INSTALL = os.path.join(SCRIPTS, 'install.py')
GUARD = 'bash "$HOME/.claude/hooks/guard-destructive.sh"'

_spec = importlib.util.spec_from_file_location('install', INSTALL)
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)

LINKS = ('CLAUDE.md', 'agents', 'docs', 'modes', 'scripts', 'standards')
PLUGIN_LINK = os.path.join('skills', 'adyusuf')


class FakeMonitor:
    """Stands in for install_monitor.py: records the calls instead of building or uninstalling an agent."""
    SERVERS = {'prod': 'https://prod.example', 'test': 'https://test.example', 'dev': 'http://localhost:1'}

    def __init__(self, install_code=0, check_code=0):
        self.calls, self.install_code, self.check_code = [], install_code, check_code

    def install(self, server, home):
        self.calls.append(('install', server, home))
        return self.install_code

    def remove(self, home):
        self.calls.append(('remove', home))
        return 0

    def check(self, home):
        self.calls.append(('check', home))
        return self.check_code

    def sync(self, home):
        self.calls.append(('sync', home))
        return 0


class Fixture(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.repo = os.path.realpath(tempfile.mkdtemp())
        self.agent_home = tempfile.mkdtemp()                       # an empty CM_AGENT_HOME: no cm-agent installed
        for path in (self.home, self.repo, self.agent_home):
            self.addCleanup(shutil.rmtree, path, True)
        for name in ('standards/00-working-method.md', 'modes/README.md', 'CLAUDE.md', 'agents/qa.md', 'docs/d.md',
                     'scripts/guard-destructive.sh', 'plugin/.keep'):
            self.put(os.path.join(self.repo, *name.split('/')), 'x\n')
        os.makedirs(os.path.join(self.home, '.claude'))
        self.settings = self.claude('settings.json')
        self.write_json(self.settings, {'theme': 'dark'})
        self.monitor = FakeMonitor()

    def put(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)

    def write_json(self, path, data):
        self.put(path, json.dumps(data, indent=2) + '\n')

    def read(self, path):
        with open(path, encoding='utf-8') as handle:
            return handle.read()

    def claude(self, *parts):
        return os.path.join(self.home, '.claude', *parts)

    def store(self, *parts):
        return os.path.join(self.home, '.claude-standards', *parts)

    def link_legacy(self, name, target=None):
        """The old install's link: ~/.claude/<name> -> <checkout>/<name> (skills/adyusuf -> <checkout>/plugin)."""
        source = target or os.path.join(self.repo, 'plugin' if name == PLUGIN_LINK else name)
        os.makedirs(os.path.dirname(self.claude(name)), exist_ok=True)
        os.symlink(source, self.claude(name), target_is_directory=os.path.isdir(source))
        return source

    def legacy_settings(self):
        """settings.json as the old install wrote it: its guard hook next to a hook that is yours."""
        self.write_json(self.settings, {'theme': 'dark', 'hooks': {'PreToolUse': [
            {'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': GUARD},
                                          {'type': 'command', 'command': 'echo mine'}]}]}})

    def write_plugins(self, data):
        self.write_json(self.claude('plugins', 'installed_plugins.json'), data)

    def plugin_entry(self, version='1.2.3'):
        self.write_plugins({'version': 2, 'plugins': {install.PLUGIN_ID: [
            {'scope': 'user', 'installPath': '/p', 'version': version}]}})

    def tree(self, root):
        """{relative path: link target or file text} of everything under root, links not followed."""
        found = {}
        for folder, dirs, files in os.walk(root):
            for name in dirs + files:
                path = os.path.join(folder, name)
                key = os.path.relpath(path, root)
                found[key] = os.readlink(path) if os.path.islink(path) else (
                    None if os.path.isdir(path) else self.read(path))
        return found

    def run_install(self, *args, monitor=False):
        """A real subprocess. --no-monitor is added unless monitor=True (only used for --remove/--check/--sync:
        an install with the monitor on would clone and build an agent)."""
        extra = [] if monitor else ['--no-monitor']
        return subprocess.run([sys.executable, INSTALL, '--home', self.home, *extra, *args], capture_output=True,
                              text=True, encoding='utf-8', errors='replace',
                              env=dict(os.environ, CM_AGENT_HOME=self.agent_home))

    def call(self, *args, monitor=None, preflight=([], [])):
        """install.main in this process with a FakeMonitor and a canned preflight: (code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        fake = monitor or self.monitor
        real_load = install.load
        with mock.patch.object(install, 'load',
                               side_effect=lambda name, file: fake if name == 'install_monitor' else real_load(name, file)), \
                mock.patch.object(install, 'preflight', return_value=preflight), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = install.main(['--home', self.home, *args])
        return code, out.getvalue(), err.getvalue()


class PlainRun(Fixture):
    def test_it_prints_the_two_plugin_commands_and_asks_for_a_new_session(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(install.hooks.MARKETPLACE_ADD, result.stdout)
        self.assertIn(install.hooks.PLUGIN_INSTALL, result.stdout)
        self.assertIn('open a NEW Claude Code session', result.stdout)

    def test_it_links_nothing_and_leaves_settings_json_alone(self):
        # The removed behaviour must stay removed: no symlink, no hook, no backup, no moved file.
        self.put(self.claude('CLAUDE.md'), 'my own rules\n')
        before = self.tree(self.claude())
        for channel in ((), ('--prod',), ('--test',), ('--dev',)):
            with self.subTest(channel=channel):
                self.assertEqual(self.run_install(*channel).returncode, 0)
                self.assertEqual(self.tree(self.claude()), before)
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'my own rules\n')
        self.assertFalse(os.path.exists(self.store('backups')), 'a plain run backs nothing up: it moves nothing')

    def test_the_channel_is_named_and_only_picks_the_monitor_server(self):
        for flag, want in (('--prod', 'prod'), ('--test', 'test'), ('--dev', 'dev')):
            with self.subTest(flag=flag):
                self.assertIn(f'channel     {want}', self.run_install(flag).stdout)
        self.assertIn('channel     prod', self.run_install().stdout)

    def test_it_reports_whether_the_plugin_is_installed(self):
        self.assertIn('plugin      ✗ not installed', self.run_install().stdout)
        self.plugin_entry('1.2.3')
        self.assertIn('plugin      ✓ installed: adyusuf@adyusuf-marketplace 1.2.3 (user scope)',
                      self.run_install().stdout)

    def test_old_pieces_are_warned_about_but_never_removed_by_a_plain_run(self):
        link = self.link_legacy('docs')
        self.legacy_settings()
        settings = self.read(self.settings)
        out = self.run_install().stdout
        self.assertIn('2 piece(s) of the old linked install are still here', out)
        self.assertIn('install.py --remove', out)
        self.assertEqual(os.readlink(self.claude('docs')), link)
        self.assertEqual(self.read(self.settings), settings)

    def test_a_clean_home_gets_no_old_install_warning(self):
        self.assertNotIn('old linked install', self.run_install().stdout)

    def test_a_refused_claude_folder_stops_before_anything_is_created(self):
        shutil.rmtree(self.claude())
        env = dict(os.environ, PATH=self.agent_home)       # an empty folder: no `claude` on PATH
        result = subprocess.run([sys.executable, INSTALL, '--home', self.home, '--no-monitor'],
                                capture_output=True, text=True, encoding='utf-8', env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Claude Code is not installed', result.stderr)
        self.assertNotIn(install.hooks.MARKETPLACE_ADD, result.stdout)
        self.assertFalse(os.path.exists(self.store()), 'no log folder either')


class InstallLog(Fixture):
    def logs(self):
        folder = self.store('logs')
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []

    def test_a_run_leaves_its_whole_output_in_a_log(self):
        result = self.run_install()
        [name] = self.logs()
        self.assertRegex(name, r'^install-\d{8}-\d{6}\.log$')
        text = self.read(self.store('logs', name))
        for expected in ('choices:', install.hooks.PLUGIN_INSTALL, '✓ done'):
            self.assertIn(expected, text)
        self.assertIn(name, result.stdout, 'the console must say where the log is')

    def test_a_preflight_refusal_is_logged_and_runs_no_monitor_step(self):
        code, out, err = self.call(preflight=(['git is not on PATH'], []))
        self.assertEqual(code, 2)
        self.assertIn('✗ git is not on PATH', err)
        self.assertNotIn(install.hooks.MARKETPLACE_ADD, out)
        self.assertEqual(self.monitor.calls, [])
        [name] = self.logs()
        self.assertIn('git is not on PATH', self.read(self.store('logs', name)))

    def test_preflight_warnings_are_printed_and_do_not_stop_the_run(self):
        code, out, _ = self.call(preflight=([], ['python3: NOT on PATH (warning)']))
        self.assertEqual(code, 0)
        self.assertIn('⚠️  python3: NOT on PATH (warning)', out)

    def test_check_is_read_only_and_writes_no_log(self):
        self.run_install('--check')
        self.assertEqual(self.logs(), [])


if __name__ == '__main__':
    unittest.main()
