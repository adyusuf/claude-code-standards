import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
INSTALLER = os.path.join(SCRIPTS, 'install-live-hooks.py')
REAL_REPO = os.path.dirname(os.path.realpath(SCRIPTS))

MD_HOOK = 'bash "$HOME/.claude/scripts/md-hook.sh"'
GUARD = 'bash "$HOME/.claude/hooks/guard-destructive.sh"'


def text_of(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


EXISTING = {
    'hooks': {
        'PostToolUse': [{'matcher': 'Edit|Write', 'hooks': [{'type': 'command', 'command': MD_HOOK}]}],
        'Stop': [{'hooks': [{'type': 'command', 'command': MD_HOOK}]}],
    },
    'theme': 'dark',
}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.repo = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.repo, 'scripts'))
        for name in ('guard-destructive.sh',):
            with open(os.path.join(self.repo, 'scripts', name), 'w') as handle:
                handle.write('#!/bin/sh\n')
        os.makedirs(os.path.join(self.home, '.claude'))
        self.settings = os.path.join(self.home, '.claude', 'settings.json')
        self.write_settings(EXISTING)

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.repo, ignore_errors=True)

    def write_settings(self, data, newline=True):
        with open(self.settings, 'w', encoding='utf-8') as handle:
            handle.write(json.dumps(data, indent=2) + ('\n' if newline else ''))

    def read_settings(self):
        with open(self.settings, encoding='utf-8') as handle:
            return json.load(handle)

    def run_installer(self, *args, repo=None):
        return subprocess.run([sys.executable, INSTALLER, '--home', self.home, '--repo', repo or self.repo, *args],
                              capture_output=True, text=True)

    def hooks_dir(self):
        return os.path.join(self.home, '.claude', 'hooks')

    def backups(self):
        folder = os.path.join(self.home, '.claude', 'backups')
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


def commands(data, event):
    return [h['command'] for e in data['hooks'].get(event, []) for h in e['hooks']]


class Install(Fixture):
    def test_links_and_registers_both_hooks_and_keeps_everything_else(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ('guard-destructive.sh',):
            link = os.path.join(self.hooks_dir(), name)
            self.assertTrue(os.path.islink(link))
            self.assertEqual(os.readlink(link), os.path.join(os.path.realpath(self.repo), 'scripts', name))
        data = self.read_settings()
        self.assertIn(GUARD, commands(data, 'PreToolUse'))
        self.assertEqual(data['hooks']['PreToolUse'][0]['matcher'], 'Bash')
        self.assertEqual(commands(data, 'Stop'), [MD_HOOK])  # the ledger hook left with its script
        self.assertEqual(commands(data, 'PostToolUse'), [MD_HOOK])
        self.assertEqual(data['theme'], 'dark')

    def test_settings_are_backed_up_before_the_change(self):
        self.run_installer()
        self.assertEqual(len(self.backups()), 1)
        with open(os.path.join(self.home, '.claude', 'backups', self.backups()[0]), encoding='utf-8') as handle:
            self.assertEqual(json.load(handle), EXISTING)

    def test_running_it_twice_changes_nothing(self):
        self.run_installer()
        first = text_of(self.settings)
        result = self.run_installer()
        self.assertIn('already up to date', result.stdout)
        self.assertEqual(text_of(self.settings), first)
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(commands(self.read_settings(), 'PreToolUse').count(GUARD), 1)

    def test_trailing_newline_and_indent_are_preserved(self):
        self.run_installer()
        text = text_of(self.settings)
        self.assertTrue(text.endswith('\n'))
        self.assertIn('\n  "hooks"', text)
        self.write_settings(EXISTING, newline=False)
        self.run_installer('--remove')
        self.run_installer()
        self.assertFalse(text_of(self.settings).endswith('\n'))

    def test_a_missing_settings_file_is_created_without_a_backup(self):
        os.remove(self.settings)
        self.assertEqual(self.run_installer().returncode, 0)
        self.assertEqual(commands(self.read_settings(), 'PreToolUse'), [GUARD])
        self.assertEqual(self.backups(), [])

    def test_a_symlink_pointing_elsewhere_is_retargeted(self):
        self.run_installer()
        other = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(other, 'scripts'))
            for name in ('guard-destructive.sh',):
                open(os.path.join(other, 'scripts', name), 'w').close()
            self.assertEqual(self.run_installer(repo=other).returncode, 0)
            link = os.path.join(self.hooks_dir(), 'guard-destructive.sh')
            self.assertEqual(os.readlink(link), os.path.join(os.path.realpath(other), 'scripts', 'guard-destructive.sh'))
        finally:
            shutil.rmtree(other, ignore_errors=True)


class Refusals(Fixture):
    def test_a_real_file_in_the_way_is_never_overwritten(self):
        os.makedirs(self.hooks_dir())
        blocker = os.path.join(self.hooks_dir(), 'guard-destructive.sh')
        with open(blocker, 'w') as handle:
            handle.write('mine')
        result = self.run_installer()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(text_of(blocker), 'mine')
        self.assertEqual(self.read_settings(), EXISTING)

    def test_unparsable_settings_abort_with_nothing_touched(self):
        with open(self.settings, 'w') as handle:
            handle.write('{ not json')
        result = self.run_installer()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(os.path.exists(self.hooks_dir()))
        self.assertEqual(text_of(self.settings), '{ not json')

    def test_a_wrong_repo_aborts_before_any_link_is_made(self):
        os.remove(os.path.join(self.repo, 'scripts', 'guard-destructive.sh'))
        result = self.run_installer()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(os.path.exists(self.hooks_dir()))
        self.assertEqual(self.read_settings(), EXISTING)


class CheckAndRemove(Fixture):
    def test_check_fails_before_and_passes_after(self):
        self.assertEqual(self.run_installer('--check').returncode, 1)
        self.run_installer()
        self.assertEqual(self.run_installer('--check').returncode, 0)

    def test_check_notices_a_broken_symlink(self):
        self.run_installer()
        os.remove(os.path.join(self.repo, 'scripts', 'guard-destructive.sh'))
        result = self.run_installer('--check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('broken', result.stdout)

    def test_remove_takes_only_our_entries_and_links(self):
        self.run_installer()
        self.assertEqual(self.run_installer('--remove').returncode, 0)
        data = self.read_settings()
        self.assertEqual(data, EXISTING)
        self.assertEqual(os.listdir(self.hooks_dir()), [])

    def test_remove_on_a_clean_setup_is_a_no_op(self):
        before = text_of(self.settings)
        self.assertEqual(self.run_installer('--remove').returncode, 0)
        self.assertEqual(text_of(self.settings), before)
        self.assertEqual(self.backups(), [])


class InstalledGuardWorks(unittest.TestCase):
    """The real thing: install from THIS repository, then run the symlinked guard."""

    def test_the_installed_symlink_blocks_a_force_push_and_allows_a_normal_one(self):
        home = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(home, '.claude'))
            with open(os.path.join(home, '.claude', 'settings.json'), 'w') as handle:
                handle.write('{}\n')
            result = subprocess.run([sys.executable, INSTALLER, '--home', home, '--repo', REAL_REPO],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            guard = os.path.join(home, '.claude', 'hooks', 'guard-destructive.sh')
            blocked = subprocess.run(['bash', guard], input=json.dumps({'tool_input': {'command': 'git push --force'}}),
                                     capture_output=True, text=True)
            allowed = subprocess.run(['bash', guard], input=json.dumps({'tool_input': {'command': 'ls'}}),
                                     capture_output=True, text=True)
            self.assertEqual((blocked.returncode, allowed.returncode), (2, 0))
        finally:
            shutil.rmtree(home, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
