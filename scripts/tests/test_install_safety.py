"""install_safety.py — what install.py checks, keeps and reports (split from test_install.py, #9).

After the plugin move it owns: the Claude-Code-is-there refusal, the install log (logged/Tee), restore_latest
(the migration puts back what the OLD install moved aside), and the small helpers store/shown. plugin_installed
is covered case by case in test_install_check.py.
"""
import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
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
        result = subprocess.run([sys.executable, install.__file__, '--home', self.home],
                                capture_output=True, text=True, encoding='utf-8', env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Claude Code is not installed', result.stderr)
        self.assertFalse(os.path.exists(self.claude()), 'not even a log folder: it would fake an install')
        self.assertFalse(os.path.exists(self.store()), 'nor ~/.claude-standards')

    def test_an_unwritable_claude_folder_stops_too(self):
        with mock.patch.object(safety.tempfile, 'NamedTemporaryFile', side_effect=PermissionError('denied')):
            errors = safety.claude_errors(self.home, lambda name: None)
        self.assertEqual(len(errors), 1)
        self.assertIn('is not writable', errors[0])
        self.assertIn('nothing was changed', errors[0])

    def test_a_writable_folder_leaves_no_probe_file_behind(self):
        self.assertEqual(safety.claude_errors(self.home, lambda name: None), [])
        self.assertEqual(os.listdir(self.claude()), ['settings.json'])

    def test_a_cli_without_the_folder_yet_is_enough(self):
        os.remove(self.settings)
        os.rmdir(self.claude())
        self.assertEqual(safety.claude_errors(self.home, lambda name: '/bin/claude'), [])


class RestoreLatest(Fixture):
    """The migration off the old install: its backups, in ~/.claude-standards/backups/install-*/manifest.json."""

    def backup(self, stamp, name, text=None, kind='file', manifest=True):
        folder = self.store('backups', stamp)
        item = {'kind': kind}
        if text is not None:
            saved = os.path.join(folder, *name.split('/'))
            self.put(saved, text)
            item['backup'] = saved
        if manifest:
            self.write_json(os.path.join(folder, 'manifest.json'), {'items': {name: item}})
        return item

    def restore(self):
        out = io.StringIO()
        with redirect_stdout(out):
            safety.restore_latest(self.home)
        return out.getvalue()

    def test_a_free_place_gets_its_file_back_and_the_backup_is_kept(self):
        item = self.backup('install-20261001-100000', 'CLAUDE.md', 'my own rules\n')
        out = self.restore()
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'my own rules\n')
        self.assertIn('restored', out)
        self.assertTrue(os.path.isfile(item['backup']), 'the backup is kept')

    def test_an_occupied_place_is_never_overwritten(self):
        item = self.backup('install-20261001-100000', 'CLAUDE.md', 'old\n')
        self.put(self.claude('CLAUDE.md'), 'newer\n')
        out = self.restore()
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'newer\n')
        self.assertIn(f'is occupied — left as it is; your copy stays in {item["backup"]}', out)

    def test_a_dangling_link_in_the_place_counts_as_occupied(self):
        self.backup('install-20261001-100000', 'CLAUDE.md', 'old\n')
        os.symlink(os.path.join(self.home, 'gone'), self.claude('CLAUDE.md'))
        self.assertIn('is occupied', self.restore())
        self.assertTrue(os.path.islink(self.claude('CLAUDE.md')))

    def test_the_newest_backup_that_holds_the_item_wins_even_if_a_newer_one_holds_none(self):
        # A second install found a link where CLAUDE.md was and moved nothing: its manifest has no 'backup'.
        self.backup('install-20261001-100000', 'CLAUDE.md', 'my own rules\n')
        self.backup('install-20261002-100000', 'CLAUDE.md', None, kind='link')
        self.restore()
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'my own rules\n')

    def test_the_newest_copy_beats_an_older_one(self):
        self.backup('install-20261001-100000', 'CLAUDE.md', 'older\n')
        self.backup('install-20261002-100000', 'CLAUDE.md', 'newer\n')
        self.restore()
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'newer\n')

    def test_a_folder_is_restored_with_its_content_and_a_missing_parent_is_recreated(self):
        folder = self.store('backups', 'install-20261001-100000', 'skills', 'adyusuf')
        self.put(os.path.join(folder, 'a.md'), 'a\n')
        self.write_json(self.store('backups', 'install-20261001-100000', 'manifest.json'),
                        {'items': {'skills/adyusuf': {'kind': 'dir', 'backup': folder}}})
        self.assertFalse(os.path.exists(self.claude('skills')))
        self.restore()
        self.assertEqual(self.read(self.claude('skills', 'adyusuf', 'a.md')), 'a\n')

    def test_settings_json_is_never_restored_over_the_live_one(self):
        self.backup('install-20261001-100000', 'settings.json', '{"theme": "light"}\n')
        self.restore()
        self.assertEqual(json.loads(self.read(self.settings)), {'theme': 'dark'})

    def test_an_unreadable_manifest_is_skipped_and_named_not_fatal(self):
        self.put(self.store('backups', 'install-20261003-100000', 'manifest.json'), '{ nope')
        self.backup('install-20261001-100000', 'CLAUDE.md', 'my own rules\n')
        out = self.restore()
        self.assertIn('no readable manifest', out)
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'my own rules\n')

    def test_a_folder_that_is_not_an_install_backup_is_ignored(self):
        self.backup('settings', 'CLAUDE.md', 'not ours\n')
        self.assertIn('nothing to put back', self.restore())
        self.assertFalse(os.path.exists(self.claude('CLAUDE.md')))

    def test_with_no_backups_at_all_it_says_so(self):
        self.assertIn('nothing to put back', self.restore())


class LoggedOutput(Fixture):
    def run_logged(self, function):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = safety.logged(self.home, function)
        [name] = os.listdir(self.store('logs'))
        return code, out.getvalue(), err.getvalue(), self.read(self.store('logs', name))

    def test_stdout_and_stderr_reach_the_console_and_the_log(self):
        def work():
            print('to stdout')
            print('to stderr', file=sys.stderr)
            return 7
        code, out, err, log = self.run_logged(work)
        self.assertEqual(code, 7)
        self.assertIn('to stdout', out)
        self.assertIn('to stderr', err)
        self.assertIn('to stdout', log)
        self.assertIn('to stderr', log)
        self.assertIn('command: install.py', log)

    def test_the_streams_are_restored_even_when_the_work_raises(self):
        real = sys.stdout
        with redirect_stdout(io.StringIO()) as shown, self.assertRaises(RuntimeError):
            safety.logged(self.home, lambda: (_ for _ in ()).throw(RuntimeError('boom')))
        self.assertIs(sys.stdout, real)
        self.assertIn('the full output is in', shown.getvalue())

    def test_the_tee_forwards_other_attributes_to_the_stream(self):
        stream = io.StringIO()
        tee = safety.Tee(stream, io.StringIO())
        self.assertEqual(tee.write('abc'), 3)
        self.assertEqual(tee.getvalue(), 'abc')


    def test_flush_reaches_both_the_console_and_the_log(self):
        stream, log = mock.Mock(), mock.Mock()
        safety.Tee(stream, log).flush()
        stream.flush.assert_called_once_with()
        log.flush.assert_called_once_with()


class Helpers(unittest.TestCase):
    def test_link_targets_are_shown_without_the_windows_prefix(self):
        self.assertEqual(safety.shown('\\\\?\\C:\\Work\\r\\CLAUDE.md'), 'C:\\Work\\r\\CLAUDE.md')
        self.assertEqual(safety.shown('/Users/a/r/CLAUDE.md'), '/Users/a/r/CLAUDE.md')

    def test_the_store_lives_outside_claude(self):
        self.assertEqual(safety.store('/h', 'backups', 'x'), os.path.join('/h', '.claude-standards', 'backups', 'x'))
        self.assertNotIn(os.path.join('.claude', ''), safety.store('/h'))


if __name__ == '__main__':
    unittest.main()
