import json
import os
import shutil
import subprocess
import sys
import tempfile
import contextlib
import importlib.util
import io
import unittest
from unittest import mock

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ONBOARD = os.path.join(SCRIPTS, 'onboard.py')
REAL_REPO = os.path.dirname(SCRIPTS)
MARKETPLACE_ADD = '/plugin marketplace add adyusuf/claude-code-standards#prod'
PLUGIN_INSTALL = '/plugin install adyusuf@adyusuf-marketplace'


def text_of(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.repo = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.repo, 'standards'))
        with open(os.path.join(self.repo, 'standards', 'README.md'), 'w') as handle:
            handle.write('index, not a document\n')
        for name in ('05-react.md', '10-test-strategy.md'):
            with open(os.path.join(self.repo, 'standards', name), 'w') as handle:
                handle.write(f'# {name}\n')
        with open(os.path.join(self.repo, 'CLAUDE.md'), 'w') as handle:
            handle.write('# rules\n')

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.repo, ignore_errors=True)

    def run_onboard(self, *args, repo=None):
        return subprocess.run([sys.executable, ONBOARD, '--home', self.home, '--repo', repo or self.repo, *args],
                              capture_output=True, text=True)

    def claude_md(self):
        return os.path.join(self.home, '.claude', 'CLAUDE.md')


class TestDescribe(Fixture):
    def test_mentions_the_apply_project_standards_command(self):
        result = self.run_onboard('describe')
        self.assertEqual(result.returncode, 0)
        self.assertIn('/adyusuf:apply-project-standards', result.stdout)

    def test_falls_back_to_the_path_without_a_git_remote(self):
        result = self.run_onboard('describe')
        # The script prints the RESOLVED path; on Windows mkdtemp may hand out the 8.3 short form (ADMINI~1).
        self.assertIn(os.path.realpath(self.repo), result.stdout)


    def test_names_the_plugin_as_the_way_to_get_the_whole_rule_set(self):
        out = self.run_onboard('describe').stdout
        self.assertIn(MARKETPLACE_ADD, out)
        self.assertIn(PLUGIN_INSTALL, out)

    def test_uses_the_origin_url_when_the_repo_has_one(self):
        subprocess.run(['git', 'init', '-q', self.repo], check=True, capture_output=True)
        subprocess.run(['git', '-C', self.repo, 'remote', 'add', 'origin', 'https://example.invalid/r.git'],
                       check=True, capture_output=True)
        out = self.run_onboard('describe').stdout
        self.assertIn('https://example.invalid/r.git', out)
        self.assertNotIn(os.path.realpath(self.repo), out)


class TestInProcess(Fixture):
    """The few branches a subprocess run cannot reach."""

    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location('onboard', ONBOARD)
        self.onboard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.onboard)

    def test_a_machine_without_git_has_no_origin_url(self):
        with mock.patch.object(self.onboard.subprocess, 'run', side_effect=FileNotFoundError('git')):
            self.assertIsNone(self.onboard.origin_url(self.repo))

    def test_a_repo_without_an_origin_has_no_origin_url(self):
        self.assertIsNone(self.onboard.origin_url(self.repo))

    def test_a_missing_source_is_refused_and_nothing_is_written(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code = self.onboard.copy_one(os.path.join(self.repo, 'standards', 'nope.md'),
                                         os.path.join(self.home, '.claude', 'standards', 'nope.md'),
                                         self.home, True, False)
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(self.home, '.claude')))

    def test_a_folder_source_is_copied_whole(self):
        dest = os.path.join(self.home, '.claude', 'standards-copy')
        with contextlib.redirect_stdout(io.StringIO()):
            code = self.onboard.copy_one(os.path.join(self.repo, 'standards'), dest, self.home, True, False)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(dest)), ['05-react.md', '10-test-strategy.md', 'README.md'])


class TestStatus(Fixture):
    def test_reports_everything_missing_on_an_empty_home(self):
        result = self.run_onboard('status')
        self.assertEqual(result.returncode, 0)
        self.assertIn('level1 (CLAUDE.md): missing', result.stdout)
        self.assertIn('level2 (standards/): 0/2', result.stdout)
        self.assertIn('whole rule set (the adyusuf plugin): not installed', result.stdout)
        self.assertIn(f'install it inside Claude Code: {MARKETPLACE_ADD} then {PLUGIN_INSTALL}', result.stdout)
        self.assertIn('an old symlinked install (level 4): see install.py --check', result.stdout)

    def test_status_writes_nothing(self):
        self.run_onboard('status')
        self.assertEqual(os.listdir(self.home), [])

    def test_the_installed_plugin_is_reported_with_its_version_and_no_install_hint(self):
        path = os.path.join(self.home, '.claude', 'plugins', 'installed_plugins.json')
        os.makedirs(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({'plugins': {'adyusuf@adyusuf-marketplace': [
                {'scope': 'user', 'installPath': '/p', 'version': '4.5.6'}]}}, handle)
        out = self.run_onboard('status').stdout
        self.assertIn('whole rule set (the adyusuf plugin): installed: adyusuf@adyusuf-marketplace 4.5.6 (user scope)',
                      out)
        self.assertNotIn('install it inside Claude Code', out)

    def test_an_unreadable_plugin_record_counts_as_not_installed(self):
        path = os.path.join(self.home, '.claude', 'plugins', 'installed_plugins.json')
        os.makedirs(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('{ nope')
        out = self.run_onboard('status').stdout
        self.assertIn('not installed', out)
        self.assertIn('unreadable', out)

    def test_level1_and_level2_are_counted_from_the_home(self):
        self.run_onboard('level1', '--apply')
        self.run_onboard('level2', '05-react.md', '--apply')
        out = self.run_onboard('status').stdout
        self.assertIn('level1 (CLAUDE.md): present, five-rule block found', out)
        self.assertIn('level2 (standards/): 1/2', out)

    def test_a_claude_md_without_the_block_is_said_so(self):
        os.makedirs(os.path.dirname(self.claude_md()))
        with open(self.claude_md(), 'w', encoding='utf-8') as handle:
            handle.write('# mine\n')
        self.assertIn('present, five-rule block NOT found', self.run_onboard('status').stdout)

    def test_the_standards_readme_is_never_counted(self):
        result = self.run_onboard('status')
        self.assertIn('0/2', result.stdout)          # 2, not 3 (README.md is an index, not a document)


class TestLevel1(Fixture):
    def test_dry_run_writes_nothing(self):
        result = self.run_onboard('level1')
        self.assertEqual(result.returncode, 0)
        self.assertIn('would append', result.stdout)
        self.assertFalse(os.path.exists(self.claude_md()))

    def test_apply_writes_the_block(self):
        result = self.run_onboard('level1', '--apply')
        self.assertEqual(result.returncode, 0)
        text = text_of(self.claude_md())
        self.assertIn('Report the truth', text)
        self.assertIn('five-rule block', text)

    def test_apply_twice_is_idempotent(self):
        self.run_onboard('level1', '--apply')
        first = text_of(self.claude_md())
        result = self.run_onboard('level1', '--apply')
        second = text_of(self.claude_md())
        self.assertEqual(first, second)
        self.assertIn('already present, nothing to do', result.stdout)

    def test_apply_keeps_an_existing_claude_md(self):
        os.makedirs(os.path.dirname(self.claude_md()))
        with open(self.claude_md(), 'w', encoding='utf-8') as handle:
            handle.write('# my own rules\n')
        self.run_onboard('level1', '--apply')
        text = text_of(self.claude_md())
        self.assertIn('my own rules', text)
        self.assertIn('Report the truth', text)


class TestLevel2(Fixture):
    def test_list_does_not_touch_home(self):
        result = self.run_onboard('level2', '--list')
        self.assertEqual(result.returncode, 0)
        self.assertIn('05-react.md', result.stdout)
        self.assertNotIn('README.md', result.stdout.splitlines())
        self.assertFalse(os.path.exists(os.path.join(self.home, '.claude')))

    def test_no_files_and_no_list_is_an_error(self):
        result = self.run_onboard('level2')
        self.assertEqual(result.returncode, 2)

    def test_unknown_file_refuses_without_writing(self):
        result = self.run_onboard('level2', 'nope.md', '--apply')
        self.assertEqual(result.returncode, 2)
        self.assertIn('not in standards/', result.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.home, '.claude', 'standards')))

    def test_apply_copies_the_chosen_file_only(self):
        result = self.run_onboard('level2', '05-react.md', '--apply')
        self.assertEqual(result.returncode, 0)
        dest_dir = os.path.join(self.home, '.claude', 'standards')
        self.assertTrue(os.path.exists(os.path.join(dest_dir, '05-react.md')))
        self.assertFalse(os.path.exists(os.path.join(dest_dir, '10-test-strategy.md')))

    def test_apply_never_overwrites_without_force(self):
        dest = os.path.join(self.home, '.claude', 'standards', '05-react.md')
        os.makedirs(os.path.dirname(dest))
        with open(dest, 'w', encoding='utf-8') as handle:
            handle.write('local edits\n')
        self.run_onboard('level2', '05-react.md', '--apply')
        self.assertEqual(text_of(dest), 'local edits\n')

    def test_force_overwrites_and_backs_up(self):
        dest = os.path.join(self.home, '.claude', 'standards', '05-react.md')
        os.makedirs(os.path.dirname(dest))
        with open(dest, 'w', encoding='utf-8') as handle:
            handle.write('local edits\n')
        result = self.run_onboard('level2', '05-react.md', '--apply', '--force')
        self.assertEqual(result.returncode, 0)
        self.assertIn('# 05-react.md', text_of(dest))
        backups = os.listdir(os.path.join(self.home, '.claude', 'backups'))
        self.assertTrue(any(b.startswith('05-react.md.') for b in backups))


class TestLevel3(Fixture):
    """level3 is OBSOLETE: the whole rule set is the plugin. It says so, whatever the flags, and writes nothing."""

    def test_every_flag_combination_prints_the_plugin_commands_and_writes_nothing(self):
        for flags in ((), ('--apply',), ('--apply', '--force'), ('--force',)):
            with self.subTest(flags=flags):
                result = self.run_onboard('level3', *flags)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('level3 is obsolete', result.stdout)
                self.assertIn(MARKETPLACE_ADD, result.stdout)
                self.assertIn(PLUGIN_INSTALL, result.stdout)
                self.assertEqual(os.listdir(self.home), [], 'nothing is copied into ~/.claude any more')

    def test_an_existing_claude_folder_is_left_exactly_as_it_was(self):
        mine = os.path.join(self.home, '.claude', 'agents', 'my-own-agent.md')
        os.makedirs(os.path.dirname(mine))
        with open(mine, 'w', encoding='utf-8') as handle:
            handle.write('kept\n')
        self.run_onboard('level3', '--apply', '--force')
        self.assertEqual(text_of(mine), 'kept\n')
        self.assertEqual(os.listdir(os.path.join(self.home, '.claude')), ['agents'])
        self.assertEqual(os.listdir(os.path.dirname(mine)), ['my-own-agent.md'])

    def test_it_never_mentions_copying_the_old_level_entries(self):
        out = self.run_onboard('level3', '--apply').stdout
        self.assertNotIn('copying', out)
        self.assertNotIn('would copy', out)


class TestAgainstTheRealRepository(unittest.TestCase):
    """The fixture repo above is a stand-in; run the obsolete level3 and `describe` against the real checkout
    too, so the notice and the plugin commands cannot pass on the fixture alone."""

    def run_real(self, *args):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, True)
        result = subprocess.run([sys.executable, ONBOARD, '--repo', REAL_REPO, '--home', home, *args],
                                capture_output=True, text=True)
        return result, home

    def test_level3_against_the_real_repository_is_the_notice_and_writes_nothing(self):
        result, home = self.run_real('level3', '--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(PLUGIN_INSTALL, result.stdout)
        self.assertEqual(os.listdir(home), [])

    def test_level2_list_names_the_real_standards(self):
        result, _ = self.run_real('level2', '--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('10-test-strategy.md', result.stdout)


if __name__ == '__main__':
    unittest.main()
