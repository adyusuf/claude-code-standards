"""install.py --check — read-only; exit 1 while an old link or hook is left or the plugin is not installed.

Exit-code cases run the real script against a temp HOME (--no-monitor, so no agent is needed); the monitor part of
the check runs in this process with a FakeMonitor.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_install import PLUGIN_LINK, FakeMonitor, Fixture, install  # noqa: E402


class CheckExitCodes(Fixture):
    def check(self, *extra):
        return self.run_install('--check', *extra)

    def test_a_clean_home_with_the_plugin_entry_passes(self):
        self.plugin_entry()
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('✓ no link of the old install is left', result.stdout)
        self.assertIn('legacy hooks: none', result.stdout)
        self.assertIn('plugin: ✓ installed: adyusuf@adyusuf-marketplace 1.2.3', result.stdout)
        self.assertIn('✓ everything is in place', result.stdout)

    def test_the_plugin_missing_fails(self):
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('plugin: ✗ not installed', result.stdout)
        self.assertIn('✗ 1 problem(s)', result.stdout)

    def test_an_old_link_fails_even_with_the_plugin_installed(self):
        self.plugin_entry()
        self.link_legacy('standards')
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn(f'✗ left    {self.claude("standards")} -> {os.path.join(self.repo, "standards")}', result.stdout)

    def test_a_dangling_old_link_fails_too(self):
        self.plugin_entry()
        self.link_legacy(PLUGIN_LINK, os.path.join(self.home, 'gone', 'plugin'))
        self.assertEqual(self.check().returncode, 1)

    def test_a_legacy_hook_in_settings_fails(self):
        self.plugin_entry()
        self.legacy_settings()
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('legacy hooks: 1 still present', result.stdout)

    def test_the_problems_are_counted(self):
        self.link_legacy('docs')
        self.link_legacy('agents')
        self.legacy_settings()
        self.assertIn('✗ 4 problem(s)', self.check().stdout)          # 2 links + 1 hook + the missing plugin

    def test_a_corrupt_installed_plugins_json_is_not_installed(self):
        self.put(self.claude('plugins', 'installed_plugins.json'), '{ not json')
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('plugin: ✗ not installed', result.stdout)
        self.assertIn('unreadable', result.stdout)

    def test_an_entry_for_another_plugin_is_not_ours(self):
        self.write_plugins({'plugins': {'other@market': [{'version': '9'}]}})
        self.assertEqual(self.check().returncode, 1)

    def test_a_check_changes_nothing(self):
        self.link_legacy('docs')
        self.legacy_settings()
        before = self.tree(self.home)
        self.check()
        self.assertEqual(self.tree(self.home), before)

    def test_a_missing_claude_folder_is_reported_not_refused(self):
        # --check is exempt from the "Claude Code must be there" refusal: it reports the plugin as missing.
        shutil.rmtree(self.claude())
        result = subprocess.run([sys.executable, install.__file__, '--home', self.home, '--check', '--no-monitor'],
                                capture_output=True, text=True, encoding='utf-8',
                                env=dict(os.environ, PATH=self.agent_home))        # no `claude` on PATH either
        self.assertEqual(result.returncode, 1)
        self.assertIn('plugin: ✗ not installed', result.stdout)


class CheckAndTheMonitor(Fixture):
    def setUp(self):
        super().setUp()
        self.plugin_entry()

    def test_a_monitor_problem_fails_the_check(self):
        code, out, _ = self.call('--check', monitor=FakeMonitor(check_code=1))
        self.assertEqual(code, 1)
        self.assertIn('✗ 1 problem(s)', out)

    def test_a_healthy_monitor_passes_and_was_asked_about_this_home(self):
        code, _, _ = self.call('--check')
        self.assertEqual(code, 0)
        self.assertEqual(self.monitor.calls, [('check', self.home)])

    def test_no_monitor_does_not_ask_the_monitor(self):
        code, _, _ = self.call('--check', '--no-monitor', monitor=FakeMonitor(check_code=1))
        self.assertEqual(code, 0)

    def test_a_monitor_problem_adds_to_the_others(self):
        self.link_legacy('docs')
        _, out, _ = self.call('--check', monitor=FakeMonitor(check_code=1))
        self.assertIn('✗ 2 problem(s)', out)


class PluginInstalledShapes(unittest.TestCase):
    """install_safety.plugin_installed over every shape installed_plugins.json can be in."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.safety = install.safety
        self.pid = install.PLUGIN_ID

    def write(self, text):
        path = os.path.join(self.home, '.claude', 'plugins', 'installed_plugins.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text if isinstance(text, str) else json.dumps(text))

    def read(self):
        return self.safety.plugin_installed(self.home, self.pid)

    def test_no_file(self):
        installed, said = self.read()
        self.assertFalse(installed)
        self.assertIn('does not exist', said)

    def test_a_list_of_entries_reads_the_first(self):
        self.write({'plugins': {self.pid: [{'scope': 'project', 'installPath': '/a', 'version': '2.0'},
                                           {'scope': 'user', 'installPath': '/b', 'version': '1.0'}]}})
        installed, said = self.read()
        self.assertTrue(installed)
        self.assertEqual(said, f'installed: {self.pid} 2.0 (project scope) at /a')

    def test_a_single_entry_object_is_accepted(self):
        self.write({'plugins': {self.pid: {'version': '3.1', 'scope': 'user', 'installPath': '/c'}}})
        self.assertEqual(self.read(), (True, f'installed: {self.pid} 3.1 (user scope) at /c'))

    def test_an_entry_without_details_is_still_installed(self):
        self.write({'plugins': {self.pid: [{}]}})
        self.assertEqual(self.read(), (True, f'installed: {self.pid} ? (? scope) at ?'))

    def test_not_installed_shapes(self):
        for label, content in (('empty object', {}), ('no entry', {'plugins': {'x@y': [{}]}}),
                               ('empty list', {'plugins': {self.pid: []}}),
                               ('null', {'plugins': {self.pid: None}}),
                               ('list of strings', {'plugins': {self.pid: ['adyusuf']}})):
            with self.subTest(label):
                self.write(content)
                installed, said = self.read()
                self.assertFalse(installed, said)
                self.assertIn('not installed', said)

    def test_unreadable_shapes_are_not_installed_and_say_why(self):
        for label, content in (('not json', '{ nope'), ('top level list', '[]'), ('empty file', ''),
                               ('plugins is null', {'plugins': None})):
            with self.subTest(label):
                self.write(content)
                installed, said = self.read()
                self.assertFalse(installed)
                self.assertIn('unreadable', said)


if __name__ == '__main__':
    unittest.main()
