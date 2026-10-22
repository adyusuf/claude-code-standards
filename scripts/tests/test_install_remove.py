"""install.py --remove — the migration off the old linked install: links, legacy hooks, the backups.

remove_all runs in this process; the end-to-end cases run the real script against a temp HOME.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_install import LINKS, PLUGIN_LINK, Fixture, install  # noqa: E402


class RemoveAll(Fixture):
    def test_every_old_link_goes_and_the_checkout_stays(self):
        for name in LINKS + (PLUGIN_LINK,):
            self.link_legacy(name)
        before = self.tree(self.repo)
        code, out, _ = self.call('--remove')
        self.assertEqual(code, 0)
        for name in LINKS + (PLUGIN_LINK,):
            self.assertFalse(os.path.lexists(self.claude(name)), name)
        self.assertEqual(self.tree(self.repo), before)
        self.assertIn(f'unlinked  {self.claude("CLAUDE.md")}', out)

    def test_a_real_file_a_foreign_link_and_other_settings_survive(self):
        self.put(self.claude('CLAUDE.md'), 'my own rules\n')
        self.put(self.claude('agents', 'mine.md'), 'mine\n')
        self.link_legacy('docs')
        foreign = self.claude('foreign-target')
        os.makedirs(os.path.join(foreign, 'modes'))
        os.symlink(os.path.join(foreign, 'modes'), self.claude('modes'))
        self.call('--remove')
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'my own rules\n')
        self.assertTrue(os.path.isfile(self.claude('agents', 'mine.md')))
        self.assertTrue(os.path.islink(self.claude('modes')))
        self.assertFalse(os.path.lexists(self.claude('docs')))
        self.assertEqual(json.loads(self.read(self.settings)), {'theme': 'dark'})

    def test_legacy_hooks_leave_settings_json_with_a_backup_and_your_own_hook_stays(self):
        self.legacy_settings()
        code, _, _ = self.call('--remove')
        self.assertEqual(code, 0)
        data = json.loads(self.read(self.settings))
        self.assertEqual(data['theme'], 'dark')
        [group] = data['hooks']['PreToolUse']
        self.assertEqual([h['command'] for h in group['hooks']], ['echo mine'])
        saved = os.listdir(self.store('backups', 'settings'))
        self.assertEqual(len(saved), 1)
        self.assertIn('hooks', json.loads(self.read(self.store('backups', 'settings', saved[0]))))

    def test_the_legacy_guard_link_in_claude_hooks_is_unlinked(self):
        guard = os.path.join(self.repo, 'scripts', 'guard-destructive.sh')
        os.makedirs(self.claude('hooks'))
        os.symlink(guard, self.claude('hooks', 'guard-destructive.sh'))
        self.call('--remove')
        self.assertFalse(os.path.lexists(self.claude('hooks', 'guard-destructive.sh')))
        self.assertTrue(os.path.isfile(guard))

    def test_an_unreadable_settings_json_makes_the_exit_code_2_but_the_links_still_go(self):
        self.link_legacy('docs')
        self.put(self.settings, '{ not json')
        code, _, err = self.call('--remove')
        self.assertEqual(code, 2)
        self.assertIn('settings.json is unreadable', err)
        self.assertFalse(os.path.lexists(self.claude('docs')))
        self.assertEqual(self.read(self.settings), '{ not json', 'an unreadable file is never rewritten')

    def test_it_ends_by_pointing_at_the_plugin_and_the_backups(self):
        _, out, _ = self.call('--remove')
        self.assertIn(f'every backup is kept in {self.store("backups")}', out)
        self.assertIn(install.hooks.PLUGIN_INSTALL, out)

    def test_the_removal_is_logged(self):
        self.call('--remove')
        [name] = os.listdir(self.store('logs'))
        self.assertIn('removed; every backup is kept', self.read(self.store('logs', name)))


class RemoveEndToEnd(Fixture):
    """The real script: --remove touches the old install's pieces and no other plugin's settings.json entries."""

    def setUp(self):
        super().setUp()
        self.write_json(self.settings, {'theme': 'dark',
                                        'extraKnownMarketplaces': {'other-marketplace': {'source': 'x'}},
                                        'enabledPlugins': {'other@other-marketplace': True}})

    def test_remove_leaves_another_plugins_entries_alone(self):
        before = json.loads(self.read(self.settings))
        result = self.run_install('--remove')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(self.read(self.settings)), before)

    def test_a_second_remove_changes_nothing(self):
        self.link_legacy('docs')
        self.run_install('--remove')
        snapshot = self.tree(self.claude())
        self.assertEqual(self.run_install('--remove').returncode, 0)
        self.assertEqual(self.tree(self.claude()), snapshot)

    def test_remove_without_claude_code_is_refused_and_creates_nothing(self):
        shutil.rmtree(self.claude())
        result = subprocess.run([sys.executable, install.__file__, '--home', self.home, '--remove'],
                                capture_output=True, text=True, encoding='utf-8',
                                env=dict(os.environ, PATH=self.empty_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn('Claude Code is not installed', result.stderr)
        self.assertFalse(os.path.exists(self.claude()))
        self.assertFalse(os.path.exists(self.store()))


class RemoveRestoresWhatTheOldInstallMovedAside(Fixture):
    def backup(self, stamp, name, text):
        folder = self.store('backups', stamp)
        saved = os.path.join(folder, name)
        self.put(saved, text)
        self.write_json(os.path.join(folder, 'manifest.json'), {'items': {name: {'kind': 'file', 'backup': saved}}})

    def test_your_claude_md_comes_back_where_the_old_link_was(self):
        self.backup('install-20261001-100000', 'CLAUDE.md', 'my own rules\n')
        self.link_legacy('CLAUDE.md')
        code, out, _ = self.call('--remove')
        self.assertEqual(code, 0)
        self.assertFalse(os.path.islink(self.claude('CLAUDE.md')))
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'my own rules\n')
        self.assertIn('restored', out)

    def test_a_place_you_have_filled_since_is_never_overwritten(self):
        self.backup('install-20261001-100000', 'CLAUDE.md', 'old\n')
        self.put(self.claude('CLAUDE.md'), 'newer\n')
        _, out, _ = self.call('--remove')
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'newer\n')
        self.assertIn('is occupied', out)

    def test_with_no_backup_it_says_so(self):
        _, out, _ = self.call('--remove')
        self.assertIn('nothing to put back', out)


if __name__ == '__main__':
    unittest.main()
