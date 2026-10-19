"""scripts/install.py — the plugin-era install: it prints the two /plugin commands and reports what is left.

Since 13/10/2026 the rule set is a Claude Code plugin. A plain run must link nothing and touch no settings.json; --remove (test_install_remove.py) and --check (test_install_check.py) deal with what the
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


class Fixture(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.repo = os.path.realpath(tempfile.mkdtemp())
        self.empty_path = tempfile.mkdtemp()                       # an empty folder: a PATH with no `claude` on it
        for path in (self.home, self.repo, self.empty_path):
            self.addCleanup(shutil.rmtree, path, True)
        for name in ('standards/00-working-method.md', 'modes/README.md', 'CLAUDE.md', 'agents/qa.md', 'docs/d.md',
                     'scripts/guard-destructive.sh', 'plugin/.keep'):
            self.put(os.path.join(self.repo, *name.split('/')), 'x\n')
        os.makedirs(os.path.join(self.home, '.claude'))
        self.settings = self.claude('settings.json')
        self.write_json(self.settings, {'theme': 'dark'})

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

    def run_install(self, *args):
        """A real subprocess against the temp HOME."""
        return subprocess.run([sys.executable, INSTALL, '--home', self.home, *args], capture_output=True,
                              text=True, encoding='utf-8', errors='replace')

    def call(self, *args, preflight=([], [])):
        """install.main in this process with a canned preflight: (code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(install, 'preflight', return_value=preflight), \
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
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(self.tree(self.claude()), before)
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'my own rules\n')
        self.assertFalse(os.path.exists(self.store('backups')), 'a plain run backs nothing up: it moves nothing')

    def test_the_retired_server_flags_are_refused(self):
        # The install talks to no server any more: a flag that named one is an error, not a silent no-op.
        for flag in ('--prod', '--test', '--dev', '--no-monitor', '--monitor-server', '--monitor-sync'):
            with self.subTest(flag=flag):
                result = self.run_install(flag)
                self.assertEqual(result.returncode, 2)
                self.assertIn('unrecognized arguments', result.stderr)

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
        env = dict(os.environ, PATH=self.empty_path)
        result = subprocess.run([sys.executable, INSTALL, '--home', self.home],
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

    def test_a_preflight_refusal_is_logged(self):
        code, out, err = self.call(preflight=(['git is not on PATH'], []))
        self.assertEqual(code, 2)
        self.assertIn('✗ git is not on PATH', err)
        self.assertNotIn(install.hooks.MARKETPLACE_ADD, out)
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
