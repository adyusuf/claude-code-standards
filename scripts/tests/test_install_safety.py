"""install.py's safety and reporting (scripts/install_safety.py) — split from test_install.py (#9).

The questions a person must be able to answer from the screen or the log alone (user request 04/10/2026):
is Claude Code there and writable (if not: stop, touch nothing), what was backed up and where, is the backup
proven, what did CLAUDE.md become, did the plugin and the skills load, and does an uninstall bring my own
CLAUDE.md back?
"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_install import Fixture, install  # noqa: E402

safety = install.safety


def without_claude(path):
    """PATH minus any directory holding a `claude` CLI."""
    return os.pathsep.join(entry for entry in path.split(os.pathsep)
                           if not any(os.path.exists(os.path.join(entry, 'claude' + ext))
                                      for ext in ('', '.exe', '.cmd')))


class ClaudeMustBeThere(Fixture):
    def test_no_claude_code_stops_before_anything_is_created(self):
        os.remove(self.settings)
        os.rmdir(self.claude())
        env = dict(os.environ, PATH=without_claude(os.environ['PATH']))
        result = self.run_install_env(env)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Claude Code is not installed', result.stderr)
        self.assertFalse(os.path.exists(self.claude()), 'not even a log folder: it would fake an install')
        self.assertFalse(os.path.exists(self.store()), 'nor ~/.claude-standards')

    def test_an_unwritable_claude_folder_stops_too(self):
        with mock.patch.object(safety.tempfile, 'NamedTemporaryFile', side_effect=PermissionError('denied')):
            errors = safety.claude_errors(self.home, lambda name: None)
        self.assertEqual(len(errors), 1)
        self.assertIn('is not writable', errors[0])

    def test_a_cli_without_the_folder_yet_is_enough(self):
        os.remove(self.settings)
        os.rmdir(self.claude())
        self.assertEqual(safety.claude_errors(self.home, lambda name: '/bin/claude'), [])

    def run_install_env(self, env):
        import subprocess
        return subprocess.run([sys.executable, install.__file__, '--home', self.home, '--repo', self.repo,
                               '--no-monitor'], capture_output=True, text=True, encoding='utf-8', env=env)


class BackupAndReport(Fixture):
    def own_claude_md(self):
        with open(self.claude('CLAUDE.md'), 'w', encoding='utf-8', newline='\n') as handle:
            handle.write('my own rules\n')                # 13 bytes on every OS

    def manifest(self):
        [folder] = [n for n in os.listdir(self.store('backups')) if n.startswith('install-')]
        with open(self.store('backups', folder, 'manifest.json'), encoding='utf-8') as handle:
            return folder, json.load(handle)['items']

    def test_backups_and_logs_live_outside_claude_where_its_cleanup_cannot_reach(self):
        # Claude Code pruned a CLAUDE.md set aside in ~/.claude/backups half an hour later (04/10/2026).
        self.own_claude_md()
        self.run_install()
        inside = self.claude('backups')
        self.assertFalse(os.path.isdir(inside) and any(n.startswith('install-') for n in os.listdir(inside)))
        self.assertFalse(os.path.exists(self.claude('logs')))
        self.assertTrue(os.listdir(self.store('backups')) and os.listdir(self.store('logs')))

    def test_the_choices_and_every_path_are_on_the_screen(self):
        out = self.run_install().stdout
        for expected in ('choices:', 'channel     prod', 'monitor     off (--no-monitor)',
                         self.claude(), 'backup      ' + self.store('backups'), 'log: '):
            self.assertIn(expected, out)

    def test_the_manifest_records_what_was_there_before_with_a_hash(self):
        self.own_claude_md()
        self.run_install()
        _, items = self.manifest()
        self.assertEqual(items['CLAUDE.md']['kind'], 'file')
        self.assertEqual(len(items['CLAUDE.md']['sha256']), 64)
        self.assertEqual(items['agents']['kind'], 'missing')
        self.assertIn('backup', items['settings.json'], 'settings.json is copied before the hooks touch it')

    def test_the_backup_is_proven_and_the_report_answers_the_questions(self):
        self.own_claude_md()
        out = self.run_install().stdout
        self.assertIn('✓ proven  CLAUDE.md', out)
        self.assertIn('✓ readable, identical to the checkout', out)
        self.assertIn('your previous CLAUDE.md (13 bytes) is in', out)
        self.assertIn('plugin      ✓ adyusuf 1.0.0', out)
        self.assertIn('skills      ✓ 1: /adyusuf:s', out)
        self.assertIn('commands    ✓ 1: /adyusuf:c', out)
        self.assertIn('agents      ✓ 1 roles: qa', out)

    def test_link_targets_are_shown_without_the_windows_prefix(self):
        self.assertEqual(safety.shown('\\\\?\\C:\\Work\\r\\CLAUDE.md'), 'C:\\Work\\r\\CLAUDE.md')
        self.assertEqual(safety.shown('/Users/a/r/CLAUDE.md'), '/Users/a/r/CLAUDE.md')

    def test_a_changed_backup_is_caught(self):
        backup = safety.Backup(self.home, 'x')
        backup.record(self.settings)
        backup.copy_settings()
        with open(backup.items['settings.json']['backup'], 'a') as handle:
            handle.write('tampered')
        self.assertEqual([proven for _n, proven, _w in backup.verify()], [False])

    def test_a_CLAUDE_md_that_is_not_the_checkouts_is_reported(self):
        other = os.path.join(self.home, 'other.md')
        with open(other, 'w', encoding='utf-8') as handle:
            handle.write('not the rules\n')
        os.symlink(other, self.claude('CLAUDE.md'))
        backup = safety.Backup(self.home, 'r')
        out = __import__('io').StringIO()
        with mock.patch('sys.stdout', out):
            problems = safety.report(self.home, self.repo, backup)
        self.assertIn('✗ NOT readable as the checkout', out.getvalue())
        self.assertGreaterEqual(problems, 1)

    def test_a_plugin_that_cannot_load_fails_the_install(self):
        os.remove(os.path.join(self.repo, 'plugin', '.claude-plugin', 'plugin.json'))
        result = self.run_install()
        self.assertIn('plugin      ✗ not loadable', result.stdout)
        self.assertEqual(result.returncode, 1)


class UninstallRestores(Fixture):
    def test_remove_brings_your_CLAUDE_md_back_even_after_two_installs(self):
        with open(self.claude('CLAUDE.md'), 'w', encoding='utf-8') as handle:
            handle.write('my own rules\n')
        self.run_install()
        self.run_install()                                # the newest backup holds no CLAUDE.md of yours
        result = self.run_install('--remove')
        self.assertIn('restored', result.stdout)
        self.assertFalse(os.path.islink(self.claude('CLAUDE.md')))
        with open(self.claude('CLAUDE.md'), encoding='utf-8') as handle:
            self.assertEqual(handle.read(), 'my own rules\n')

    def test_an_occupied_place_is_never_overwritten(self):
        with open(self.claude('CLAUDE.md'), 'w', encoding='utf-8') as handle:
            handle.write('my own rules\n')
        self.run_install()
        install.unlink(self.claude('CLAUDE.md'))
        with open(self.claude('CLAUDE.md'), 'w', encoding='utf-8') as handle:
            handle.write('newer\n')
        safety_out = self.run_install('--remove').stdout
        self.assertIn('is occupied', safety_out)
        with open(self.claude('CLAUDE.md'), encoding='utf-8') as handle:
            self.assertEqual(handle.read(), 'newer\n')

    def test_a_link_that_fails_after_the_move_still_leaves_a_restorable_manifest(self):
        with open(self.claude('CLAUDE.md'), 'w', encoding='utf-8') as handle:
            handle.write('my own rules\n')
        backup = safety.Backup(self.home, 'failed')

        def refuse(*_args, **_kwargs):
            raise SystemExit('Windows would not create a symlink')
        with mock.patch('sys.stdout', new=__import__('io').StringIO()), self.assertRaises(SystemExit):
            install.install_links(self.repo, self.home, backup, symlink=refuse)
        self.assertFalse(os.path.lexists(self.claude('CLAUDE.md')))
        with open(os.path.join(backup.folder, 'manifest.json'), encoding='utf-8') as handle:
            self.assertIn('backup', json.load(handle)['items']['CLAUDE.md'])
        self.assertIn('restored', self.run_install('--remove').stdout)
        with open(self.claude('CLAUDE.md'), encoding='utf-8') as handle:
            self.assertEqual(handle.read(), 'my own rules\n')

    def test_two_backups_in_one_second_get_two_folders(self):
        first, second = safety.Backup(self.home, 'same'), safety.Backup(self.home, 'same')
        self.assertNotEqual(first.folder, second.folder)

    def test_with_no_backup_it_says_so(self):
        self.assertIn('nothing to put back', self.run_install('--remove').stdout)


if __name__ == '__main__':
    unittest.main()
