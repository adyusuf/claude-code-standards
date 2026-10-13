"""install-live-hooks.py since the plugin took the hooks over: a plain run WRITES NOTHING and prints the two
/plugin commands; --remove strips the LEGACY command strings and the old link (backup first, foreign entries
kept); --check reports them. Left in place they would run every hook twice."""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
INSTALLER = os.path.join(SCRIPTS, 'install-live-hooks.py')
REAL_REPO = os.path.dirname(os.path.realpath(SCRIPTS))

_spec = importlib.util.spec_from_file_location('install_live_hooks', INSTALLER)
installer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(installer)

MD_HOOK = 'bash "$HOME/.claude/scripts/md-hook.sh"'
GUARD = 'bash "$HOME/.claude/hooks/guard-destructive.sh"'
GUARD_OLD = 'bash "$HOME/.claude/scripts/guard-destructive.sh"'
PLUGIN_HOOK = 'bash "${CLAUDE_PLUGIN_ROOT}/scripts/md-hook.sh"'
MEASURE = 'python3 "$HOME/.claude/hooks/measure-stop.py"'      # the private measurement hook: never ours to touch


def text_of(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def hook(command):
    return {'type': 'command', 'command': command}


FOREIGN = {'PostToolUse': [{'matcher': 'Edit|Write', 'hooks': [hook(PLUGIN_HOOK)]}],
           'Stop': [{'hooks': [hook(MEASURE)]}]}
LEGACY_SETTINGS = {
    'hooks': {
        'PreToolUse': [{'matcher': 'Bash', 'hooks': [hook(GUARD)]}],
        'PostToolUse': [{'matcher': 'Edit|Write', 'hooks': [hook(MD_HOOK), hook(PLUGIN_HOOK)]}],
        'Stop': [{'hooks': [hook(MD_HOOK)]}, {'hooks': [hook(MEASURE)]}],
    },
    'theme': 'dark',
}


def commands(data, event):
    return [h['command'] for e in data['hooks'].get(event, []) for h in e['hooks']]


class Fixture(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)
        os.makedirs(os.path.join(self.home, '.claude'))
        self.settings = os.path.join(self.home, '.claude', 'settings.json')
        self.write_settings(LEGACY_SETTINGS)

    def write_settings(self, data, newline=True):
        with open(self.settings, 'w', encoding='utf-8') as handle:
            handle.write(json.dumps(data, indent=2) + ('\n' if newline else ''))

    def read_settings(self):
        return json.loads(text_of(self.settings))

    def run_installer(self, *args):
        return subprocess.run([sys.executable, INSTALLER, '--home', self.home, *args],
                              capture_output=True, text=True, encoding='utf-8')

    def hooks_dir(self):
        return os.path.join(self.home, '.claude', 'hooks')

    def legacy_link(self, target=None):
        os.makedirs(self.hooks_dir(), exist_ok=True)
        link = os.path.join(self.hooks_dir(), 'guard-destructive.sh')
        os.symlink(target or os.path.join(self.home, 'checkout', 'scripts', 'guard-destructive.sh'), link)
        return link

    def backups(self):
        folder = os.path.join(self.home, '.claude-standards', 'backups', 'settings')
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


class Install(Fixture):
    """A plain run installs nothing: the plugin owns the hooks. Every old side effect is asserted ABSENT."""

    def test_it_prints_the_two_plugin_commands_and_the_way_off_the_old_install(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        for expected in ('/plugin marketplace add adyusuf/claude-code-standards#prod',
                         '/plugin install adyusuf@adyusuf-marketplace', 'install-live-hooks.py --remove'):
            self.assertIn(expected, result.stdout)

    def test_settings_json_stays_byte_identical_and_nothing_is_linked_or_backed_up(self):
        before = text_of(self.settings)
        self.assertEqual(self.run_installer().returncode, 0)
        self.assertEqual(text_of(self.settings), before)
        self.assertFalse(os.path.exists(self.hooks_dir()))
        self.assertEqual((self.backups(), os.listdir(os.path.join(self.home, '.claude'))), ([], ['settings.json']))

    def test_a_missing_settings_file_is_not_created(self):
        os.remove(self.settings)
        self.assertEqual(self.run_installer().returncode, 0)
        self.assertEqual(os.listdir(os.path.join(self.home, '.claude')), [])

    def test_repo_is_accepted_and_ignored_even_when_it_does_not_exist(self):
        result = self.run_installer('--repo', os.path.join(self.home, 'no-such-checkout'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_settings(), LEGACY_SETTINGS)


class Refusals(Fixture):
    def test_unparsable_settings_abort_remove_with_nothing_touched(self):
        link = self.legacy_link()
        pathlib.Path(self.settings).write_text('{ not json')
        result = self.run_installer('--remove')
        self.assertEqual(result.returncode, 2)
        self.assertIn('refusing to continue', result.stderr)
        self.assertEqual(text_of(self.settings), '{ not json')
        self.assertTrue(os.path.islink(link))
        self.assertEqual(self.backups(), [])

    def test_a_real_file_where_the_legacy_link_was_is_never_deleted(self):
        os.makedirs(self.hooks_dir())
        blocker = os.path.join(self.hooks_dir(), 'guard-destructive.sh')
        pathlib.Path(blocker).write_text('mine')
        self.assertEqual(self.run_installer('--remove').returncode, 0)
        self.assertEqual(text_of(blocker), 'mine')
        self.assertEqual(self.run_installer('--check').returncode, 0)       # a file is not a legacy link

    def test_remove_deletes_the_link_never_the_file_it_points_to(self):
        target = os.path.join(self.home, 'guard-destructive.sh')
        pathlib.Path(target).write_text('#!/bin/sh\n')
        link = self.legacy_link(target)
        self.assertEqual(self.run_installer('--remove').returncode, 0)
        self.assertFalse(os.path.lexists(link))
        self.assertEqual(text_of(target), '#!/bin/sh\n')


class CheckAndRemove(Fixture):
    def test_check_fails_while_legacy_entries_remain_and_passes_after_remove(self):
        result = self.run_installer('--check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('legacy hooks: 3 still present', result.stdout)        # guard + md-hook x2; the foreign ones don't count
        self.assertIn('--remove', result.stdout)
        self.assertEqual(self.run_installer('--remove').returncode, 0)
        result = self.run_installer('--check')
        self.assertEqual(result.returncode, 0)
        self.assertIn('none — the hooks come from the adyusuf plugin', result.stdout)

    def test_a_legacy_link_alone_fails_the_check_and_a_dangling_one_counts(self):
        self.write_settings(FOREIGN)                                    # the plugin's own + the measurement hook
        self.assertEqual(self.run_installer('--check').returncode, 0)
        self.legacy_link()                                              # points at a checkout that does not exist
        result = self.run_installer('--check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('1 still present', result.stdout)

    def test_a_group_whose_hooks_is_not_a_list_is_no_traceback_and_not_legacy(self):
        self.write_settings({'hooks': {'Stop': [{'hooks': 3}]}})
        result = self.run_installer('--check')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertIn('legacy hooks: none', result.stdout)

    def test_an_unreadable_settings_file_fails_the_check_in_one_line(self):
        pathlib.Path(self.settings).write_text('{ not json')
        result = self.run_installer('--check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('settings.json is unreadable', result.stdout)
        self.assertEqual(result.stdout.count('\n'), 1)

    def test_remove_takes_only_the_legacy_entries_the_link_and_keeps_everything_else(self):
        link = self.legacy_link()
        result = self.run_installer('--remove')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.read_settings()
        self.assertEqual(data['hooks'], {
            'PostToolUse': [{'matcher': 'Edit|Write', 'hooks': [hook(PLUGIN_HOOK)]}],     # the group kept its other hook
            'Stop': [{'hooks': [hook(MEASURE)]}]})                                        # the legacy-only group went
        self.assertNotIn('PreToolUse', data['hooks'])                                     # an emptied event is pruned
        self.assertEqual(data['theme'], 'dark')
        self.assertFalse(os.path.lexists(link))
        self.assertIn('legacy hooks removed from settings.json', result.stdout)
        self.assertIn('unlinked', result.stdout)

    def test_remove_backs_the_settings_up_first_outside_dot_claude(self):
        self.run_installer('--remove')
        self.assertEqual(len(self.backups()), 1)
        backup = os.path.join(self.home, '.claude-standards', 'backups', 'settings', self.backups()[0])
        with open(backup, encoding='utf-8') as handle:
            self.assertEqual(json.load(handle), LEGACY_SETTINGS)
        self.assertFalse(os.path.exists(os.path.join(self.home, '.claude', 'backups')))   # Claude Code prunes there

    def test_remove_twice_changes_nothing_the_second_time(self):
        self.run_installer('--remove')
        first = text_of(self.settings)
        result = self.run_installer('--remove')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(text_of(self.settings), first)
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(result.stdout, '')

    def test_remove_on_a_clean_setup_is_a_no_op(self):
        self.write_settings(FOREIGN)
        before = text_of(self.settings)
        self.assertEqual(self.run_installer('--remove').returncode, 0)
        self.assertEqual(text_of(self.settings), before)
        self.assertEqual(self.backups(), [])

    def test_remove_without_a_settings_file_still_unlinks_and_creates_no_settings(self):
        os.remove(self.settings)
        link = self.legacy_link()
        self.assertEqual(self.run_installer('--remove').returncode, 0)
        self.assertFalse(os.path.lexists(link))
        self.assertFalse(os.path.exists(self.settings))

    def test_remove_prunes_the_hooks_key_when_nothing_else_is_left(self):
        self.write_settings({'hooks': {'Stop': [{'hooks': [hook(MD_HOOK), hook(GUARD_OLD)]}]}, 'theme': 'dark'})
        self.run_installer('--remove')
        self.assertEqual(self.read_settings(), {'theme': 'dark'})

    def test_trailing_newline_and_indent_are_preserved(self):
        self.run_installer('--remove')
        self.assertTrue(text_of(self.settings).endswith('\n') and '\n  "hooks"' in text_of(self.settings))
        self.write_settings(LEGACY_SETTINGS, newline=False)
        self.run_installer('--remove')
        self.assertFalse(text_of(self.settings).endswith('\n'))

    def test_backing_up_a_file_that_does_not_exist_makes_nothing(self):
        folder = os.path.join(self.home, 'backups')
        self.assertIsNone(installer.backup(os.path.join(folder, 'no-settings.json'), folder))
        self.assertFalse(os.path.exists(folder))


class PureFunctions(unittest.TestCase):
    def test_legacy_commands_lists_in_file_order_and_survives_odd_shapes(self):
        self.assertEqual(installer.legacy_commands(LEGACY_SETTINGS), [GUARD, MD_HOOK, MD_HOOK])
        for odd in ([], {}, {'hooks': []}, {'hooks': {'Stop': 'x'}}, {'hooks': {'Stop': [1, {'hooks': [None, 2]}, {'hooks': 3}, {'hooks': 'x'}]}}):
            self.assertEqual(installer.legacy_commands(odd), [], odd)
        mixed = {'hooks': {'Stop': [{'hooks': 3}, {'hooks': [hook(GUARD)]}]}}
        self.assertEqual(installer.legacy_commands(mixed), [GUARD])         # a malformed group hides nothing after it

    def test_strip_legacy_keeps_unknown_shapes_and_reports_whether_it_changed(self):
        data = {'hooks': {'Stop': 'x', 'Pre': [7, {'matcher': 'a'}, {'hooks': 'y'}]}}
        before = json.dumps(data)
        self.assertFalse(installer.strip_legacy(data))
        self.assertEqual(json.dumps(data), before)
        self.assertTrue(installer.strip_legacy(json.loads(json.dumps(LEGACY_SETTINGS))))


class WindowsPaths(unittest.TestCase):
    """os.readlink on Windows returns \\\\?\\C:\\...: a plain comparison read every link as wrong (04/10/2026)."""
    def test_the_extended_length_prefix_is_ignored(self):
        self.assertTrue(installer.same_path('\\\\?\\C:\\Work\\repo\\scripts\\g.sh', 'C:\\Work\\repo\\scripts\\g.sh'))

    def test_a_different_target_is_still_different(self):
        # The control: the normalisation must not make every link look right.
        self.assertFalse(installer.same_path('\\\\?\\C:\\Work\\other\\g.sh', 'C:\\Work\\repo\\g.sh'))
        self.assertFalse(installer.same_path('/a/b', '/a/c'))


class Python3Note(unittest.TestCase):
    def test_python3_present(self):
        self.assertEqual(installer.python3_note(lambda name: '/usr/bin/' + name), 'python3: on PATH')

    def test_only_python_warns_and_names_the_fix(self):
        note = installer.python3_note(lambda name: 'C:\\Python\\python.exe' if name == 'python' else None)
        self.assertIn('NOT on PATH (warning)', note)
        self.assertIn('falls back to `python`', note)
        self.assertIn('mklink', note)

    def test_no_python_at_all_warns_that_the_guard_blocks(self):
        self.assertIn('will block', installer.python3_note(lambda name: None))


class PluginGuardWorks(unittest.TestCase):
    """The real thing: the command hooks/hooks.json registers, with the plugin root pointed at THIS repository."""

    def command(self):
        return json.loads(text_of(os.path.join(REAL_REPO, 'hooks', 'hooks.json')))['hooks']['PreToolUse'][0]['hooks'][0]['command']

    def run_guard(self, shell_command):
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=REAL_REPO)
        return subprocess.run(['bash', '-c', self.command()], env=env, capture_output=True, text=True,
                              input=json.dumps({'tool_input': {'command': shell_command}}))

    def test_the_registered_command_blocks_a_force_push_and_allows_a_normal_command(self):
        blocked, allowed = self.run_guard('git push --force'), self.run_guard('ls')
        self.assertEqual((blocked.returncode, allowed.returncode), (2, 0), blocked.stderr)


if __name__ == '__main__':
    unittest.main()
