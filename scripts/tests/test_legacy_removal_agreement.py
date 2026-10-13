"""The old linked install, seen by its three readers — legacy-install-check.py (the startup warning),
install.py --check and install.py --remove — must AGREE: the warning names exactly what --remove takes out, so it
always clears after a --remove (QA repro "h1": a dotfiles ~/.claude/CLAUDE.md link was warned about forever).
Also: the retired live board's two hook strings are legacy, and --remove stops, "partially removed", on an
unreadable settings.json before the monitor and the restore.

Every case runs against a temp HOME and an empty CM_AGENT_HOME, with --no-monitor or the FakeMonitor stub: nothing
here can reach the real monitor or the real ~/.claude.
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_install import SCRIPTS, Fixture, install  # noqa: E402

CHECK = os.path.join(SCRIPTS, 'legacy-install-check.py')
LIVE_HOOKS = os.path.join(SCRIPTS, 'install-live-hooks.py')
BOARD_ENSURE = 'python3 "$HOME/.claude/scripts/board/board_ensure.py" || true'
BOARD_HOOK = 'python3 "$HOME/.claude/scripts/board/board_hook.py" || true'
GUARD_OLD = 'bash "$HOME/.claude/scripts/guard-destructive.sh"'
MD_HOOK = 'bash "$HOME/.claude/scripts/md-hook.sh"'
FOREIGN_HOOKS = ('echo mine', 'python3 "$HOME/my-tools/board_hook.py" || true')   # a look-alike is still not ours

_spec = importlib.util.spec_from_file_location('install_live_hooks_for_agreement', LIVE_HOOKS)
live_hooks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live_hooks)


class Agreement(Fixture):
    def run_check(self):
        """The startup warning, as a session would run it, against this HOME: stdout (stderr must stay empty)."""
        result = subprocess.run([sys.executable, CHECK], capture_output=True, text=True, encoding='utf-8',
                                env=dict(os.environ, HOME=self.home, PYTHONUTF8='1'))
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        return result.stdout

    def run_live_hooks(self, *args):
        return subprocess.run([sys.executable, LIVE_HOOKS, '--home', self.home, *args], capture_output=True,
                              text=True, encoding='utf-8')

    def hook_settings(self, *commands_by_event):
        events = {event: [{'hooks': [{'type': 'command', 'command': c} for c in commands]}]
                  for event, commands in commands_by_event}
        self.write_json(self.settings, {'theme': 'dark', 'hooks': events})

    def commands(self):
        data = json.loads(self.read(self.settings))
        return [h['command'] for groups in data.get('hooks', {}).values() for g in groups for h in g['hooks']]


class ForeignLinkAtALegacyName(Agreement):
    """~/.claude/CLAUDE.md -> ~/dotfiles/CLAUDE.md: an existing target outside this repository is yours."""

    def setUp(self):
        super().setUp()
        self.dotfile = os.path.join(self.home, 'dotfiles', 'CLAUDE.md')
        self.put(self.dotfile, 'my dotfiles rules\n')
        os.symlink(self.dotfile, self.claude('CLAUDE.md'))

    def test_the_startup_warning_is_silent(self):
        self.assertEqual(self.run_check(), '')

    def test_remove_leaves_the_link_and_its_target(self):
        result = self.run_install('--remove')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(os.readlink(self.claude('CLAUDE.md')), self.dotfile)
        self.assertEqual(self.read(self.dotfile), 'my dotfiles rules\n')
        self.assertIn('none      no link of the old install is left', result.stdout)

    def test_check_does_not_count_it(self):
        self.plugin_entry()
        result = self.run_install('--check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('✓ no link of the old install is left', result.stdout)
        self.assertNotIn('✗ left', result.stdout)

    def test_the_warning_names_only_what_remove_takes_out_and_is_gone_after_it(self):
        self.link_legacy('docs')                                    # ours, next to the dotfiles link
        self.legacy_settings()
        warning = self.run_check()
        self.assertIn('1 symlink(s) under ~/.claude (docs) and 1 old hook entry', warning)
        self.assertNotIn('CLAUDE.md', warning)
        self.assertEqual(self.run_install('--remove').returncode, 0)
        self.assertEqual(self.run_check(), '')                      # the warning clears — h1
        self.assertTrue(os.path.islink(self.claude('CLAUDE.md')))   # and the dotfiles link is still there

    def test_a_dangling_link_with_a_foreign_name_is_silent_for_all_three(self):
        os.symlink(os.path.join(self.home, 'unmounted', 'my-notes'), self.claude('standards'))
        self.plugin_entry()
        self.assertEqual(self.run_check(), '')
        self.assertEqual(self.run_install('--check').returncode, 0)
        self.assertEqual(self.run_install('--remove').returncode, 0)
        self.assertTrue(os.path.islink(self.claude('standards')))


class DanglingLinkWithTheExpectedName(Agreement):
    def setUp(self):
        super().setUp()
        gone = os.path.join(self.home, 'removed-checkout')
        os.symlink(os.path.join(gone, 'standards'), self.claude('standards'))
        os.makedirs(self.claude('skills'))
        os.symlink(os.path.join(gone, 'plugin'), self.claude(install.PLUGIN_LINK))

    def test_the_startup_warning_reports_both(self):
        self.assertIn('2 symlink(s) under ~/.claude (standards, adyusuf)', self.run_check())

    def test_check_counts_both(self):
        self.plugin_entry()
        result = self.run_install('--check')
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(f'✗ left    {self.claude("standards")}', result.stdout)
        self.assertIn(f'✗ left    {self.claude(install.PLUGIN_LINK)}', result.stdout)
        self.assertIn('✗ 2 problem(s)', result.stdout)

    def test_remove_takes_both_out_and_the_warning_clears(self):
        result = self.run_install('--remove')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(os.path.lexists(self.claude('standards')))
        self.assertFalse(os.path.lexists(self.claude(install.PLUGIN_LINK)))
        self.assertEqual(self.run_check(), '')


class RetiredBoardHooks(Agreement):
    """The retired live board's two user-level hooks start a process on every tool call once the old scripts link
    is gone (`|| true` hides the failure): reported by every reader, stripped by --remove, foreign hooks kept."""

    def setUp(self):
        super().setUp()
        self.hook_settings(('PreToolUse', (BOARD_ENSURE, FOREIGN_HOOKS[0])), ('PostToolUse', (BOARD_HOOK,)),
                           ('Stop', (FOREIGN_HOOKS[1],)))

    def test_the_legacy_set_holds_the_old_guard_and_md_hook_strings_and_the_two_board_ones(self):
        guard = 'bash "$HOME/.claude/hooks/guard-destructive.sh"'
        self.assertEqual(live_hooks.LEGACY, {guard, GUARD_OLD, MD_HOOK, BOARD_ENSURE, BOARD_HOOK})

    def test_install_live_hooks_check_reports_both(self):
        result = self.run_live_hooks('--check')
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('legacy hooks: 2 still present', result.stdout)

    def test_the_startup_warning_reports_both(self):
        self.assertIn('2 old hook entries in ~/.claude/settings.json', self.run_check())

    def test_install_check_counts_both(self):
        self.plugin_entry()
        result = self.run_install('--check')
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('legacy hooks: 2 still present', result.stdout)

    def test_live_hooks_remove_strips_them_with_a_backup_and_keeps_the_foreign_hooks(self):
        before = self.read(self.settings)
        result = self.run_live_hooks('--remove')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), list(FOREIGN_HOOKS))
        self.assertEqual(json.loads(self.read(self.settings))['theme'], 'dark')
        [saved] = os.listdir(self.store('backups', 'settings'))
        self.assertEqual(self.read(self.store('backups', 'settings', saved)), before)

    def test_install_remove_does_the_same_and_the_warning_clears(self):
        result = self.run_install('--remove')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.commands(), list(FOREIGN_HOOKS))
        self.assertEqual(len(os.listdir(self.store('backups', 'settings'))), 1)
        self.assertEqual(self.run_check(), '')
        self.assertIn('legacy hooks: none', self.run_live_hooks('--check').stdout)


class RemoveStopsOnUnreadableSettings(Agreement):
    """hooks.remove returns 2 on an unreadable settings.json: the links are already out, but the monitor uninstall
    and the restore of your own files must not run until the file is fixed and --remove is rerun."""

    def setUp(self):
        super().setUp()
        self.link_legacy('CLAUDE.md')
        self.link_legacy('docs')
        folder = self.store('backups', 'install-20261001-100000')
        self.put(os.path.join(folder, 'CLAUDE.md'), 'my own rules\n')
        self.write_json(os.path.join(folder, 'manifest.json'),
                        {'items': {'CLAUDE.md': {'kind': 'file', 'backup': os.path.join(folder, 'CLAUDE.md')}}})
        self.put(self.settings, '{ not json')

    def test_exit_2_partially_removed_and_the_restore_does_not_run(self):
        result = self.run_install('--remove')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('✗ partially removed', result.stdout)
        self.assertIn('settings.json is unreadable', result.stderr)
        self.assertFalse(os.path.lexists(self.claude('docs')), 'the links step already ran')
        self.assertFalse(os.path.lexists(self.claude('CLAUDE.md')), 'your backed-up CLAUDE.md must NOT come back yet')
        for later_step in ('  restored  ', '  restore   ', 'removed; every backup', 'monitor:'):
            self.assertNotIn(later_step, result.stdout)
        self.assertEqual(self.read(self.settings), '{ not json')

    def test_the_monitor_uninstall_is_not_called(self):
        code, out, _ = self.call('--remove')                        # the monitor is ON here, a FakeMonitor stands in
        self.assertEqual(code, 2)
        self.assertEqual(self.monitor.calls, [])
        self.assertIn('partially removed', out)

    def test_after_the_file_is_fixed_a_rerun_finishes_the_job(self):
        self.assertEqual(self.run_install('--remove').returncode, 2)
        self.write_json(self.settings, {'theme': 'dark'})
        result = self.run_install('--remove')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.read(self.claude('CLAUDE.md')), 'my own rules\n')
        code, _, _ = self.call('--remove')
        self.assertEqual((code, self.monitor.calls), (0, [('remove', self.home)]))


if __name__ == '__main__':
    unittest.main()
