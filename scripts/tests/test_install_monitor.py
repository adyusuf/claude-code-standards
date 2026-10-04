"""scripts/install_monitor.py — cm-agent for `install.py --with-monitor`.

Every external step (git, dotnet, the agent) goes through an injected runner, so the sequence and the
refusals are tested without a .NET SDK or a network. The building and the agent itself are claude-monitor's
own tests; what is tested here is that this installer never reports a step as done that did not run.
"""
import importlib.util
import os
import subprocess
import unittest
from contextlib import redirect_stdout
from io import StringIO

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('install_monitor', os.path.join(SCRIPTS, 'install_monitor.py'))
monitor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(monitor)

ENV = {'CLAUDE_MONITOR_HOME': '/m', 'CM_AGENT_HOME': '/agent'}
SDKS = '8.0.421 [C:\\sdk]\n10.0.300 [C:\\sdk]\n'


class FakeRun:
    """Records each command; answers by the first word that matches in `codes` (default 0)."""

    def __init__(self, **codes):
        self.calls, self.codes = [], codes

    def __call__(self, command, capture=False):
        self.calls.append(command)
        if command[:2] == ['dotnet', '--list-sdks']:
            return subprocess.CompletedProcess(command, 0, self.codes.get('sdks', SDKS), '')
        for word, code in self.codes.items():
            if word in command or os.path.basename(command[0]) == word:
                return subprocess.CompletedProcess(command, code, '', '')
        return subprocess.CompletedProcess(command, 0, '', '')

    def ran(self, word):
        return [call for call in self.calls if word in call]


def run_install(run, server=None, exists=lambda path: False, system='Windows', machine='AMD64'):
    out = StringIO()
    with redirect_stdout(out):
        code = monitor.install(server, run=run, env=ENV, system=system, machine=machine, exists=exists)
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


class Install(unittest.TestCase):
    def test_a_fresh_machine_clones_builds_registers_and_says_it_is_not_connected(self):
        run = FakeRun()
        code, out = run_install(run)
        self.assertEqual(code, 3, 'not connected is INCOMPLETE, never done')
        self.assertIn('NOT CONNECTED', out)
        self.assertEqual(run.ran('clone')[0][-1], '/m')
        publish = run.ran('publish')[0]
        self.assertEqual(publish[publish.index('-r') + 1], 'win-x64')
        self.assertEqual(run.ran('install')[0], [os.path.join('/m', 'out', 'win-x64', 'cm-agent.exe'), 'install'])
        self.assertEqual(run.ran('login'), [])

    def test_a_server_connects_with_the_INSTALLED_binary(self):
        run = FakeRun()
        code, _ = run_install(run, server='https://monitor.example')
        self.assertEqual(code, 0)
        login = run.ran('login')[0]
        self.assertEqual(login[0], os.path.join('/agent', 'bin', 'cm-agent.exe'))
        self.assertEqual(login[-2:], ['--server', 'https://monitor.example'])

    def test_an_existing_clone_is_used_not_cloned_again(self):
        run = FakeRun()
        run_install(run, exists=lambda path: True)
        self.assertEqual(run.ran('clone'), [])
        self.assertEqual(len(run.ran('publish')), 1)

    def test_an_old_checkout_without_the_agent_refuses(self):
        run = FakeRun()
        code, out = run_install(run, exists=lambda path: path == '/m')
        self.assertEqual(code, 2)
        self.assertIn('older checkout', out)
        self.assertEqual(run.ran('publish'), [])

    def test_no_dotnet_10_sdk_refuses_before_cloning(self):
        run = FakeRun(sdks='8.0.421 [C:\\sdk]\n')
        code, out = run_install(run)
        self.assertEqual(code, 2)
        self.assertIn('.NET 10 SDK', out)
        self.assertEqual(run.ran('clone'), [])

    def test_an_unsupported_platform_refuses_before_anything_runs(self):
        run = FakeRun()
        code, _ = run_install(run, system='Linux', machine='x86_64')
        self.assertEqual((code, run.calls), (2, []))

    def test_a_failed_clone_or_publish_stops_there(self):
        run = FakeRun(clone=128)
        self.assertEqual(run_install(run)[0], 2)
        self.assertEqual(run.ran('publish'), [])
        run = FakeRun(publish=1)
        self.assertEqual(run_install(run)[0], 2)
        self.assertEqual(run.ran('install'), [])

    def test_an_unregistered_plugin_is_INCOMPLETE_even_when_connected(self):
        run = FakeRun(install=1)
        code, out = run_install(run, server='https://monitor.example')
        self.assertEqual(code, 3)
        self.assertIn('NOT registered', out)

    def test_a_failed_registration_or_login_is_a_failure(self):
        self.assertEqual(run_install(FakeRun(install=5))[0], 2)
        self.assertEqual(run_install(FakeRun(login=1), server='https://monitor.example')[0], 2)


class CheckAndRemove(unittest.TestCase):
    def call(self, function, run, exists):
        with redirect_stdout(StringIO()):
            return function(run=run, env=ENV, system='Windows', exists=exists)

    def test_check_counts_a_missing_or_unconnected_agent(self):
        self.assertEqual(self.call(monitor.check, FakeRun(), lambda path: False), 1)
        self.assertEqual(self.call(monitor.check, FakeRun(status=1), lambda path: True), 1)
        self.assertEqual(self.call(monitor.check, FakeRun(), lambda path: True), 0)

    def test_remove_unregisters_only_when_installed(self):
        run = FakeRun()
        self.call(monitor.remove, run, lambda path: True)
        self.assertEqual(run.calls, [[os.path.join('/agent', 'bin', 'cm-agent.exe'), 'uninstall']])
        run = FakeRun()
        self.call(monitor.remove, run, lambda path: False)
        self.assertEqual(run.calls, [])


if __name__ == '__main__':
    unittest.main()
