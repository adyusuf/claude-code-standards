"""scripts/install.py — the monitor step, the flag notices and the pure helpers (split from test_install.py, #9).

The monitor is the ONLY thing a plain run installs now; every test here replaces it with FakeMonitor so no agent
is built or uninstalled.
"""
import json
import os
import sys
import unittest
from argparse import Namespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_install import FakeMonitor, Fixture, install  # noqa: E402


class MonitorStep(Fixture):
    def test_the_monitor_is_the_only_step_and_follows_the_channel(self):
        for args, server in (((), 'prod'), (('--prod',), 'prod'), (('--test',), 'test'), (('--dev',), 'dev')):
            with self.subTest(args=args):
                self.monitor.calls.clear()
                code, out, _ = self.call(*args)
                self.assertEqual(code, 0)
                self.assertEqual(self.monitor.calls, [('install', FakeMonitor.SERVERS[server], self.home)])
                self.assertIn(f'monitor     on -> {FakeMonitor.SERVERS[server]}', out)

    def test_monitor_server_overrides_the_channels(self):
        self.call('--test', '--monitor-server', 'https://mine.example')
        self.assertEqual(self.monitor.calls, [('install', 'https://mine.example', self.home)])

    def test_no_monitor_skips_the_step_but_still_prints_the_commands(self):
        code, out, _ = self.call('--no-monitor')
        self.assertEqual((code, self.monitor.calls), (0, []))
        self.assertIn('off (--no-monitor)', out)
        self.assertIn(install.hooks.PLUGIN_INSTALL, out)

    def test_the_configuration_can_turn_the_monitor_off_for_an_install_only(self):
        # monitor.connect = no in the user's configuration (adyusuf:config) skips the step like --no-monitor.
        os.makedirs(os.path.join(self.home, '.claude'), exist_ok=True)
        with open(os.path.join(self.home, '.claude', 'adyusuf.json'), 'w', encoding='utf-8') as handle:
            json.dump({'monitor': {'connect': False}}, handle)
        code, out, _ = self.call()
        self.assertEqual((code, self.monitor.calls), (0, []))
        self.assertIn('monitor.connect = no', out)
        self.assertIn('off (--no-monitor)', out)

    def test_an_unreadable_configuration_leaves_the_monitor_on(self):
        os.makedirs(os.path.join(self.home, '.claude'), exist_ok=True)
        with open(os.path.join(self.home, '.claude', 'adyusuf.json'), 'w', encoding='utf-8') as handle:
            handle.write('{ broken')
        code, out, _ = self.call()
        self.assertEqual(code, 0)
        self.assertEqual(self.monitor.calls, [('install', FakeMonitor.SERVERS['prod'], self.home)])

    def test_a_failed_monitor_step_is_a_warning_not_a_failure(self):
        # The monitor is optional (user decision 13/10/2026): cm-agent missing or unreachable is not a problem.
        for exit_code in (1, 2, 5):
            with self.subTest(exit_code=exit_code):
                monitor = FakeMonitor(install_code=exit_code)
                code, out, _ = self.call(monitor=monitor)
                self.assertEqual(code, 0)
                self.assertEqual(len(monitor.calls), 1, 'the step was tried once')
                self.assertIn(f'⚠️  the monitor agent was not installed or connected (exit {exit_code})', out)
                self.assertIn('optional', out)
                self.assertIn('✓ done', out)
                self.assertNotIn('✗ stopped', out)

    def test_a_working_monitor_step_prints_no_warning(self):
        code, out, _ = self.call()
        self.assertEqual(code, 0)
        self.assertNotIn('the monitor agent was not installed', out)
        self.assertIn('✓ done', out)

    def test_a_preflight_error_is_still_the_exit_code_whatever_the_monitor_does(self):
        monitor = FakeMonitor(install_code=2)
        code, out, err = self.call(monitor=monitor, preflight=(['git is not on PATH'], []))
        self.assertEqual(code, 2)
        self.assertIn('✗ git is not on PATH', err)
        self.assertEqual(monitor.calls, [], 'a refused run never reaches the monitor step')
        self.assertNotIn('✓ done', out)

    def test_main_prints_the_flag_notes_before_anything_else(self):
        _, out, _ = self.call('--with-monitor', '--no-monitor')
        self.assertTrue(out.startswith('note: --with-monitor changes nothing'), out)

    def test_monitor_sync_runs_only_the_sync(self):
        code, _, _ = self.call('--monitor-sync')
        self.assertEqual((code, self.monitor.calls), (0, [('sync', self.home)]))

    def test_monitor_sync_end_to_end_registers_the_plugin_disabled(self):
        result = self.run_install('--monitor-sync', monitor=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('DORMANT', result.stdout)
        data = json.loads(self.read(self.settings))
        self.assertIs(data['enabledPlugins']['monitor-agent@monitor-agent-local'], False)
        self.assertEqual(data['theme'], 'dark')


class FlagNotices(unittest.TestCase):
    def notes(self, **changes):
        base = dict(with_monitor=False, channel=None, check=False, remove=False, monitor_sync=False,
                    no_monitor=False, repo=install.DEFAULT_REPO)
        return install.flag_notices(Namespace(**{**base, **changes}))

    def test_no_flag_no_note(self):
        self.assertEqual(self.notes(), [])
        self.assertEqual(self.notes(channel='test'), [], 'a channel on a plain install picks the monitor server')

    def test_with_monitor_changes_nothing(self):
        [note] = self.notes(with_monitor=True)
        self.assertIn('--with-monitor changes nothing', note)

    def test_a_channel_next_to_a_mode_that_ignores_it_is_named(self):
        for mode in ('check', 'remove', 'monitor_sync', 'no_monitor'):
            with self.subTest(mode=mode):
                [note] = self.notes(channel='dev', **{mode: True})
                self.assertIn('--dev only picks the monitor', note)

    def test_repo_changes_nothing(self):
        [note] = self.notes(repo='/somewhere/else')
        self.assertIn('--repo changes nothing', note)

    def test_every_note_is_reported_not_only_the_first(self):
        self.assertEqual(len(self.notes(with_monitor=True, channel='test', check=True, repo='/x')), 3)


class Units(unittest.TestCase):
    def test_bash_is_found_in_git_for_windows_when_not_on_path(self):
        found = install.find_bash(lambda name: None, exists=lambda path: path == install.WINDOWS_BASH[0], windows=True)
        self.assertEqual(found, install.WINDOWS_BASH[0])

    def test_no_bash_anywhere_is_none(self):
        self.assertIsNone(install.find_bash(lambda name: None, exists=lambda path: False, windows=True))
        self.assertIsNone(install.find_bash(lambda name: None, exists=lambda path: True, windows=False))

    def test_a_bash_on_path_wins_over_the_windows_locations(self):
        self.assertEqual(install.find_bash(lambda name: '/bin/bash', exists=lambda path: True, windows=True), '/bin/bash')

    def test_preflight_errors_without_git_or_bash(self):
        errors, _ = install.preflight(which=lambda name: None, windows=False)
        self.assertTrue(any('git is not on PATH' in error for error in errors))
        self.assertTrue(any('bash not found' in error for error in errors))

    def test_preflight_with_everything_on_path_is_clean(self):
        self.assertEqual(install.preflight(which=lambda name: f'/bin/{name}', windows=False), ([], []))

    def test_a_missing_python3_is_a_warning_not_an_error(self):
        errors, warnings = install.preflight(which=lambda name: None if name == 'python3' else f'/bin/{name}',
                                             windows=False)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn('python3', warnings[0])

    def test_an_old_python_is_an_error(self):
        with mock.patch.object(install.sys, 'version_info', (3, 8, 0)):
            errors, _ = install.preflight(which=lambda name: f'/bin/{name}', windows=False)
        self.assertEqual(len(errors), 1)
        self.assertIn('Python 3.9+ is required', errors[0])

    def test_the_plugin_id_is_the_one_the_install_command_names(self):
        self.assertEqual(install.PLUGIN_ID, 'adyusuf@adyusuf-marketplace')
        self.assertTrue(install.hooks.PLUGIN_INSTALL.endswith(install.PLUGIN_ID))


if __name__ == '__main__':
    unittest.main()
