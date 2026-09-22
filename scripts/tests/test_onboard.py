import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ONBOARD = os.path.join(SCRIPTS, 'onboard.py')
REAL_REPO = os.path.dirname(SCRIPTS)


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
        for name in ('agents', 'modes', 'commands', 'skills', 'scripts'):
            os.makedirs(os.path.join(self.repo, name))
            with open(os.path.join(self.repo, name, 'placeholder.md'), 'w') as handle:
                handle.write(f'{name}\n')

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
        self.assertIn('/apply-project-standards', result.stdout)

    def test_falls_back_to_the_path_without_a_git_remote(self):
        result = self.run_onboard('describe')
        self.assertIn(self.repo, result.stdout)


class TestStatus(Fixture):
    def test_reports_everything_missing_on_an_empty_home(self):
        result = self.run_onboard('status')
        self.assertEqual(result.returncode, 0)
        self.assertIn('level1 (CLAUDE.md): missing', result.stdout)
        self.assertIn('level2 (standards/): 0/2', result.stdout)
        self.assertIn('missing CLAUDE.md, standards, agents, modes, commands, skills, scripts', result.stdout)

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
    def test_dry_run_writes_nothing(self):
        result = self.run_onboard('level3')
        self.assertEqual(result.returncode, 0)
        for entry in ('CLAUDE.md', 'standards', 'agents', 'modes', 'commands', 'skills', 'scripts'):
            self.assertIn(entry, result.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.home, '.claude')))

    def test_apply_copies_every_entry(self):
        result = self.run_onboard('level3', '--apply')
        self.assertEqual(result.returncode, 0)
        claude = os.path.join(self.home, '.claude')
        for entry in ('CLAUDE.md', 'standards', 'agents', 'modes', 'commands', 'skills', 'scripts'):
            self.assertTrue(os.path.exists(os.path.join(claude, entry)), entry)

    def test_apply_never_recommends_copying_settings_example(self):
        result = self.run_onboard('level3', '--apply')
        self.assertIn('was NOT copied', result.stdout)

    def test_apply_keeps_an_existing_directory_without_force(self):
        dest = os.path.join(self.home, '.claude', 'agents')
        os.makedirs(dest)
        with open(os.path.join(dest, 'my-own-agent.md'), 'w', encoding='utf-8') as handle:
            handle.write('kept\n')
        self.run_onboard('level3', '--apply')
        self.assertTrue(os.path.exists(os.path.join(dest, 'my-own-agent.md')))
        self.assertFalse(os.path.exists(os.path.join(dest, 'placeholder.md')))


class TestAgainstTheRealRepository(unittest.TestCase):
    """The fixture repo above is a stand-in; also run level3 --list against the real checkout
    once, so a real missing file (a typo in LEVEL3_ENTRIES) cannot pass on the fixture alone."""

    def test_level3_dry_run_against_the_real_repository_finds_every_entry(self):
        result = subprocess.run(
            [sys.executable, ONBOARD, '--repo', REAL_REPO, '--home', tempfile.mkdtemp(), 'level3'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for entry in ('CLAUDE.md', 'standards', 'agents', 'modes', 'commands', 'skills', 'scripts'):
            self.assertIn(entry, result.stdout)


if __name__ == '__main__':
    unittest.main()
