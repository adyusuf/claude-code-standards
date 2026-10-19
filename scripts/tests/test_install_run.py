"""scripts/install.py — the install step, the flag notices and the pure helpers (split from test_install.py, #9).

A plain run prints the two /plugin commands and reports what is left of the old install; it contacts no server.
"""
import os
import sys
import unittest
from argparse import Namespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_install import Fixture, install  # noqa: E402


class InstallStep(Fixture):
    def test_a_plain_run_ends_with_the_new_session_reminder(self):
        code, out, _ = self.call()
        self.assertEqual(code, 0)
        self.assertIn('✓ done', out)

    def test_a_preflight_error_is_the_exit_code(self):
        code, out, err = self.call(preflight=(['git is not on PATH'], []))
        self.assertEqual(code, 2)
        self.assertIn('✗ git is not on PATH', err)
        self.assertNotIn('✓ done', out)

    def test_main_prints_the_flag_notes_before_anything_else(self):
        _, out, _ = self.call('--repo', '/somewhere/else')
        self.assertTrue(out.startswith('note: --repo changes nothing'), out)

    def test_nothing_in_the_script_names_a_server(self):
        with open(install.__file__, encoding='utf-8') as handle:
            text = handle.read().lower()
        for word in ('monitor', 'cm-agent', 'bitreka', 'http://', 'https://'):
            self.assertNotIn(word, text)


class FlagNotices(unittest.TestCase):
    def notes(self, **changes):
        base = dict(check=False, remove=False, repo=install.DEFAULT_REPO)
        return install.flag_notices(Namespace(**{**base, **changes}))

    def test_no_flag_no_note(self):
        self.assertEqual(self.notes(), [])

    def test_repo_changes_nothing(self):
        [note] = self.notes(repo='/somewhere/else')
        self.assertIn('--repo changes nothing', note)


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
