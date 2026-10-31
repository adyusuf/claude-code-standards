"""scripts/sdlc_settings.py: the panel's SDLC settings, written into a project where CI can read them.

User decision 29/10/2026: CI cannot read this machine's panel, so each merge writes the panel's settings into the
project. What matters here:

  · the file holds the PANEL's layers only (defaults < the user's file < a session) - a project's own
    `.claude/adyusuf.json` is ignored, the projects keep no settings of their own;
  · a setting the user never touched takes the shipped default (a new panel setting needs nothing from anyone);
  · nothing outside the SDLC (mode, agents, pod) leaks into the file;
  · writing is repeatable: the same settings give the same bytes, so a merge without a change adds no diff;
  · `check` fails when the file is missing or stale, and an unreadable settings file is an error, never a silent default.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TOOL = os.path.join(SCRIPTS, 'sdlc_settings.py')
CONFIG = os.path.join(SCRIPTS, 'adyusuf_config.py')


class SdlcSettings(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.project, ignore_errors=True)
        self.user = os.path.join(self.home, 'adyusuf.json')
        self.env = dict(os.environ, ADYUSUF_CONFIG_USER=self.user, ADYUSUF_SESSION_DIR=os.path.join(self.home, 'sessions'))
        self.file = os.path.join(self.project, '.claude', 'sdlc-settings.json')

    def run_tool(self, *args, tool=TOOL):
        done = subprocess.run([sys.executable, tool, *args], cwd=self.project, capture_output=True, text=True, env=self.env)
        return done.stdout + done.stderr, done.returncode

    def raw(self):
        with open(self.file, 'rb') as handle:
            return handle.read()

    def written(self):
        with open(self.file, encoding='utf-8') as handle:
            return json.load(handle)

    def test_a_user_who_changed_nothing_gets_the_shipped_defaults(self):
        out, code = self.run_tool('write', '--project', self.project)
        self.assertEqual(0, code, out)
        settings = self.written()['settings']
        self.assertEqual('hosted', settings['ci']['runner'])
        self.assertEqual({'test': True, 'prod': False}, settings['deploy_after_push'])
        self.assertFalse(settings['gates_before_push']['dev'])
        self.assertTrue(settings['ci_after_push']['prod'])
        # The gate reads coverage_before_push from this file (gate-lib.sh coverage_setting), so it must be written.
        self.assertEqual({'dev': False, 'test': True, 'prod': True}, settings['coverage_before_push'])

    def test_the_users_choice_beats_the_default_and_the_session_beats_the_user(self):
        self.run_tool('set', 'deploy_after_push.prod', 'yes', tool=CONFIG)
        self.run_tool('write', '--project', self.project)
        self.assertEqual({'test': True, 'prod': True}, self.written()['settings']['deploy_after_push'])
        self.run_tool('set', 'deploy_after_push.prod', 'no', '--session', 'abc-1', tool=CONFIG)
        self.run_tool('write', '--project', self.project, '--session', 'abc-1')
        self.assertEqual({'test': True, 'prod': False}, self.written()['settings']['deploy_after_push'])

    def test_a_projects_own_adyusuf_json_is_ignored(self):
        os.makedirs(os.path.join(self.project, '.claude'))
        with open(os.path.join(self.project, '.claude', 'adyusuf.json'), 'w') as handle:
            json.dump({'ci': {'runner': 'self-hosted'}, 'push': {'prod': False}}, handle)
        self.run_tool('write', '--project', self.project)
        settings = self.written()['settings']
        self.assertEqual('hosted', settings['ci']['runner'])
        self.assertTrue(settings['push']['prod'])

    def test_only_sdlc_settings_are_written(self):
        self.run_tool('write', '--project', self.project)
        with open(self.file, encoding='utf-8') as handle:
            text = handle.read()
        for leaked in ('mode', 'agents', 'pod', 'write'):
            self.assertNotIn('"%s"' % leaked, text, leaked)

    def test_writing_twice_changes_nothing(self):
        self.run_tool('write', '--project', self.project)
        first = self.raw()
        out, code = self.run_tool('write', '--project', self.project)
        self.assertEqual(0, code)
        self.assertIn('unchanged', out)
        self.assertEqual(first, self.raw())

    def test_check_fails_on_a_missing_or_stale_file_and_passes_on_a_current_one(self):
        out, code = self.run_tool('check', '--project', self.project)
        self.assertEqual(1, code, out)
        self.assertIn('missing', out)
        self.run_tool('write', '--project', self.project)
        self.assertEqual(0, self.run_tool('check', '--project', self.project)[1])
        self.run_tool('set', 'ci.runner', 'self-hosted', tool=CONFIG)
        out, code = self.run_tool('check', '--project', self.project)
        self.assertEqual(1, code, out)
        self.assertIn('differs', out)

    def test_an_unreadable_settings_file_is_an_error_and_writes_nothing(self):
        with open(self.user, 'w') as handle:
            handle.write('{ not json')
        out, code = self.run_tool('write', '--project', self.project)
        self.assertEqual(1, code, out)
        self.assertFalse(os.path.exists(self.file))

    def fake_gh(self, exit_code=0):
        bin_dir = os.path.join(self.home, 'bin')
        os.makedirs(bin_dir, exist_ok=True)
        log = os.path.join(self.home, 'gh.log')
        path = os.path.join(bin_dir, 'gh')
        with open(path, 'w') as handle:
            handle.write('#!/bin/sh\necho "$*" >> "%s"\nexit %d\n' % (log, exit_code))
        os.chmod(path, 0o700)
        self.env['PATH'] = bin_dir + os.pathsep + self.env['PATH']
        return log

    def test_vars_sets_the_repo_variable_from_the_runner_choice(self):
        log = self.fake_gh()
        out, code = self.run_tool('vars', '--repo', 'o/r')
        self.assertEqual(0, code, out)
        with open(log) as handle:
            self.assertIn('variable set SDLC_RUNNER_LABELS --repo o/r --body ["ubuntu-latest"]', handle.read())
        self.run_tool('set', 'ci.runner', 'self-hosted', tool=CONFIG)
        self.run_tool('vars', '--repo', 'o/r')
        with open(log) as handle:
            self.assertIn('--body ["self-hosted"]', handle.read())

    def test_vars_dry_run_sets_nothing_and_a_failing_gh_is_an_error(self):
        log = self.fake_gh()
        out, code = self.run_tool('vars', '--repo', 'o/r', '--dry-run')
        self.assertEqual(0, code, out)
        self.assertFalse(os.path.exists(log))
        self.fake_gh(exit_code=1)
        self.assertEqual(1, self.run_tool('vars', '--repo', 'o/r')[1])
        self.assertEqual(2, self.run_tool('vars')[1])

    def test_no_arguments_is_a_usage_error(self):
        self.assertEqual(2, self.run_tool()[1])


if __name__ == '__main__':
    unittest.main()
