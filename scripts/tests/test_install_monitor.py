"""scripts/install_monitor.py — cm-agent for `install.py --with-monitor`.

Every external step (git, dotnet, the agent) goes through an injected runner, so the sequence and the refusals
are tested without a .NET SDK or a network. What matters most: the plugin is ENABLED only while a server is
connected — with none, Claude Code must run none of its 11 hooks and nothing may be queued (user decision
04/10/2026) — and a step that did not run is never reported as done.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('install_monitor', os.path.join(SCRIPTS, 'install_monitor.py'))
monitor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(monitor)

ENV = {'CLAUDE_MONITOR_HOME': '/m', 'CM_AGENT_HOME': '/agent'}
SDKS = '8.0.421 [C:\\sdk]\n10.0.300 [C:\\sdk]\n'
INSTALLED = os.path.join('/agent', 'bin', 'cm-agent.exe')
PLUGIN_DIR = os.path.join('/agent', 'claude-plugin')


class FakeRun:
    """Records each command; answers by the first word that matches in `codes` (default 0). The agent is NOT
    connected unless status=0 is given, and a successful login connects it, as the real agent does."""

    def __init__(self, **codes):
        self.calls, self.codes = [], {'status': 1, **codes}

    def __call__(self, command, capture=False):
        self.calls.append(command)
        if command[:2] == ['dotnet', '--list-sdks']:
            return subprocess.CompletedProcess(command, 0, self.codes.get('sdks', SDKS), '')
        for word, code in self.codes.items():
            if word in command:
                if word == 'login' and code == 0:
                    self.codes['status'] = 0
                return subprocess.CompletedProcess(command, code, '', '')
        if 'login' in command:
            self.codes['status'] = 0
        return subprocess.CompletedProcess(command, 0, '', '')

    def ran(self, word):
        return [call for call in self.calls if word in call]


class Home(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)
        os.makedirs(os.path.join(self.home, '.claude'))
        self.write({'theme': 'dark'})

    def path(self):
        return os.path.join(self.home, '.claude', 'settings.json')

    def write(self, data):
        with open(self.path(), 'w', encoding='utf-8') as handle:
            handle.write(json.dumps(data, indent=2) + '\n')

    def settings(self):
        with open(self.path(), encoding='utf-8') as handle:
            return json.load(handle)

    def enabled(self):
        return self.settings().get('enabledPlugins', {}).get(monitor.PLUGIN)

    def backups(self):
        folder = os.path.join(self.home, '.claude', 'backups')
        return os.listdir(folder) if os.path.isdir(folder) else []

    def quiet(self, function, *args, **kwargs):
        out = StringIO()
        with redirect_stdout(out):
            code = function(*args, env=ENV, system='Windows', home=self.home, **kwargs)
        return code, out.getvalue()

    def install(self, run, server=None, exists=lambda path: False, system='Windows', machine='AMD64'):
        out = StringIO()
        with redirect_stdout(out):
            code = monitor.install(server, run=run, env=ENV, system=system, machine=machine, exists=exists,
                                   home=self.home)
        return code, out.getvalue()


class RuntimeIds(unittest.TestCase):
    def test_the_four_shipped_targets(self):
        self.assertEqual(monitor.runtime_id('Windows', 'AMD64'), 'win-x64')
        self.assertEqual(monitor.runtime_id('Windows', 'ARM64'), 'win-arm64')
        self.assertEqual(monitor.runtime_id('Darwin', 'arm64'), 'osx-arm64')
        self.assertEqual(monitor.runtime_id('Darwin', 'x86_64'), 'osx-x64')

    def test_anything_else_is_none(self):
        self.assertIsNone(monitor.runtime_id('Linux', 'x86_64'))
        self.assertIsNone(monitor.runtime_id('Windows', 'i386'))

    def test_the_agent_home_follows_the_agent(self):
        self.assertEqual(monitor.agent_home({'CM_AGENT_HOME': '/x'}, 'Windows'), '/x')
        self.assertEqual(monitor.agent_home({'LOCALAPPDATA': 'C:\\L'}, 'Windows'), os.path.join('C:\\L', 'ClaudeMonitor'))
        self.assertTrue(monitor.agent_home({}, 'Darwin').endswith(os.path.join('Application Support', 'ClaudeMonitor')))
        self.assertTrue(monitor.installed_binary({}, 'Windows').endswith('cm-agent.exe'))


class NoServerMeansDormant(Home):
    def test_without_a_server_the_plugin_is_registered_DISABLED_and_says_DORMANT(self):
        run = FakeRun()
        code, out = self.install(run)
        self.assertEqual(code, 0)
        self.assertIn('DORMANT', out)
        self.assertIs(self.enabled(), False, 'no server: Claude Code must run none of the 11 hooks')
        marketplace = self.settings()['extraKnownMarketplaces'][monitor.MARKETPLACE]
        self.assertEqual(marketplace, {'source': {'source': 'directory', 'path': PLUGIN_DIR}})
        self.assertEqual(self.settings()['theme'], 'dark')
        self.assertEqual(run.ran('login'), [])

    def test_the_build_sequence(self):
        run = FakeRun()
        self.install(run)
        self.assertEqual(run.ran('clone')[0][-1], '/m')
        publish = run.ran('publish')[0]
        self.assertEqual(publish[publish.index('-r') + 1], 'win-x64')
        self.assertEqual(run.ran('install')[0], [os.path.join('/m', 'out', 'win-x64', 'cm-agent.exe'), 'install'])

    def test_a_missing_claude_cli_no_longer_matters(self):
        # cm-agent's own registration exits 1 without the CLI; settings.json carries the registration instead.
        code, _ = self.install(FakeRun(install=1))
        self.assertEqual(code, 0)
        self.assertIs(self.enabled(), False)


class ServerMeansActive(Home):
    def test_a_server_connects_and_ENABLES_the_plugin(self):
        run = FakeRun()
        code, out = self.install(run, server='https://monitor.example')
        self.assertEqual(code, 0)
        self.assertIn('ACTIVE', out)
        self.assertIs(self.enabled(), True)
        login = run.ran('login')[0]
        self.assertEqual(login, [INSTALLED, 'login', '--server', 'https://monitor.example'])

    def test_connecting_an_installed_agent_does_not_rebuild_it(self):
        run = FakeRun()
        code, _ = self.install(run, server='https://monitor.example', exists=lambda path: path == INSTALLED)
        self.assertEqual(code, 0)
        self.assertEqual((run.ran('clone'), run.ran('publish')), ([], []))
        self.assertIs(self.enabled(), True)

    def test_a_failed_login_leaves_the_plugin_as_it_was(self):
        code, _ = self.install(FakeRun(login=1), server='https://monitor.example')
        self.assertEqual(code, 2)
        self.assertIsNone(self.enabled())

    def test_a_server_that_goes_away_is_switched_off_by_sync(self):
        run = FakeRun()
        self.install(run, server='https://monitor.example')
        run.codes['status'] = 1                                         # cm-agent logout
        code, out = self.quiet(monitor.sync, run=run)
        self.assertEqual(code, 0)
        self.assertIn('DORMANT', out)
        self.assertIs(self.enabled(), False)

    def test_sync_twice_writes_once(self):
        run = FakeRun()
        self.quiet(monitor.sync, run=run)
        first = len(self.backups())
        self.quiet(monitor.sync, run=run)
        self.assertEqual(len(self.backups()), first)


class Refusals(Home):
    def test_an_existing_clone_is_used_not_cloned_again(self):
        run = FakeRun()
        self.install(run, exists=lambda path: path != INSTALLED)
        self.assertEqual(run.ran('clone'), [])
        self.assertEqual(len(run.ran('publish')), 1)

    def test_an_old_checkout_without_the_agent_refuses(self):
        run = FakeRun()
        code, out = self.install(run, exists=lambda path: path == '/m')
        self.assertEqual(code, 2)
        self.assertIn('older checkout', out)
        self.assertEqual(run.ran('publish'), [])

    def test_no_dotnet_10_sdk_refuses_before_cloning(self):
        run = FakeRun(sdks='8.0.421 [C:\\sdk]\n')
        code, out = self.install(run)
        self.assertEqual(code, 2)
        self.assertIn('.NET 10 SDK', out)
        self.assertEqual(run.ran('clone'), [])

    def test_an_unsupported_platform_refuses_before_anything_runs(self):
        run = FakeRun()
        code, _ = self.install(run, system='Linux', machine='x86_64')
        self.assertEqual((code, run.calls), (2, []))

    def test_a_failed_clone_publish_or_install_stops_there(self):
        run = FakeRun(clone=128)
        self.assertEqual(self.install(run)[0], 2)
        self.assertEqual(run.ran('publish'), [])
        run = FakeRun(publish=1)
        self.assertEqual(self.install(run)[0], 2)
        self.assertEqual(run.ran('install'), [])
        self.assertEqual(self.install(FakeRun(install=5))[0], 2)
        self.assertIsNone(self.enabled())

    def test_an_unparsable_settings_file_is_never_touched(self):
        with open(self.path(), 'w') as handle:
            handle.write('{ not json')
        code, _ = self.install(FakeRun())
        self.assertEqual(code, 2)
        with open(self.path()) as handle:
            self.assertEqual(handle.read(), '{ not json')


class CheckAndRemove(Home):
    def test_check(self):
        self.assertEqual(self.quiet(monitor.check, run=FakeRun(), exists=lambda path: False)[0], 1)
        self.quiet(monitor.sync, run=FakeRun())                                         # DORMANT, disabled
        code, out = self.quiet(monitor.check, run=FakeRun(), exists=lambda path: True)
        self.assertEqual(code, 0, 'DORMANT and disabled is the intended state, not a problem')
        self.assertIn('DORMANT', out)
        code, out = self.quiet(monitor.check, run=FakeRun(status=0), exists=lambda path: True)
        self.assertEqual(code, 1, 'connected but disabled is a mismatch')
        self.assertIn('MISMATCH', out)
        self.quiet(monitor.sync, run=FakeRun(status=0))                                 # ACTIVE, enabled
        self.assertEqual(self.quiet(monitor.check, run=FakeRun(), exists=lambda path: True)[0], 1,
                         'enabled while not connected is a mismatch: the hooks would run with nowhere to send')

    def test_remove_unregisters_and_drops_only_its_own_entries(self):
        self.quiet(monitor.sync, run=FakeRun())
        run = FakeRun()
        self.quiet(monitor.remove, run=run, exists=lambda path: True)
        self.assertEqual(run.calls, [[INSTALLED, 'uninstall']])
        self.assertEqual(self.settings(), {'theme': 'dark'})

    def test_remove_on_a_clean_machine_does_nothing(self):
        run = FakeRun()
        self.quiet(monitor.remove, run=run, exists=lambda path: False)
        self.assertEqual(run.calls, [])
        self.assertEqual(self.backups(), [])


if __name__ == '__main__':
    unittest.main()
