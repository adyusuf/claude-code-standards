"""scripts/legacy-install-check.py: the SessionStart hook that tells a machine still carrying the OLD symlinked
install about it. Silent when clean, one paragraph naming what it found and the command that removes it, always
exit 0, and it never writes — a check that blocked or repaired a session on its own would be worse than the
double load it reports."""
import contextlib
import importlib.util
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CHECK = os.path.join(SCRIPTS, 'legacy-install-check.py')
HOOKS_MODULE = os.path.join(SCRIPTS, 'install-live-hooks.py')
_spec = importlib.util.spec_from_file_location('legacy_install_check', CHECK)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)
MD_HOOK = 'bash "$HOME/.claude/scripts/md-hook.sh"'
GUARD = 'bash "$HOME/.claude/hooks/guard-destructive.sh"'
PLUGIN_HOOK = 'bash "${CLAUDE_PLUGIN_ROOT}/scripts/md-hook.sh"'
FALLBACK = '<your claude-code-standards checkout>'


def snapshot(root):
    """Everything under root: relative path -> file bytes, or the link target. Equal before and after = not written."""
    seen = {}
    for folder, dirs, files in os.walk(root):
        for name in dirs + files:
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, root)
            if os.path.islink(path):
                seen[rel] = ('link', os.readlink(path))
            elif os.path.isfile(path):
                with open(path, 'rb') as handle:
                    seen[rel] = ('file', handle.read())
            else:
                seen[rel] = ('dir', None)
    return seen


class Fixture(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = os.path.join(self.base, 'home')
        self.dot = os.path.join(self.home, '.claude')
        os.makedirs(self.dot)
        self.checkout = os.path.realpath(os.path.join(self.base, 'claude-code-standards'))
        os.makedirs(os.path.join(self.checkout, 'scripts'))
        open(os.path.join(self.checkout, 'scripts', 'install.py'), 'w').close()
        for name in ('agents', 'docs', 'modes', 'plugin', 'standards'):
            os.makedirs(os.path.join(self.checkout, name))
        # What makes the folder a checkout of this repository (install.py's fingerprint): a link into it is the old install's.
        for name in ('CLAUDE.md', os.path.join('standards', '00-working-method.md'), os.path.join('modes', 'README.md')):
            open(os.path.join(self.checkout, name), 'w').close()

    def link(self, name, target=None):
        """~/.claude/<name> -> <checkout>/<name> (skills/adyusuf -> <checkout>/plugin), as the old install made it."""
        path = os.path.join(self.dot, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        default = os.path.join(self.checkout, 'plugin' if name == os.path.join('skills', 'adyusuf') else name)
        os.symlink(target or default, path)

    def settings(self, hooks=None, text=None):
        with open(os.path.join(self.dot, 'settings.json'), 'w', encoding='utf-8') as handle:
            handle.write(text if text is not None else json.dumps({'theme': 'dark', 'hooks': hooks or {}}))

    def run_check(self, script=CHECK, **env):
        # PYTHONDONTWRITEBYTECODE: the interpreter caching a loaded sibling as lone/__pycache__ is not the check
        # writing; without this the test passed or failed on the caller's environment (a macOS Terminal, 18/10/2026).
        env = {**os.environ, 'HOME': self.home, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', **env}
        before = snapshot(self.base)
        result = subprocess.run([sys.executable, script], capture_output=True, text=True, encoding='utf-8', env=env)
        self.assertEqual(snapshot(self.base), before, 'the check must never write, link or delete anything')
        self.assertEqual(result.returncode, 0, result.stderr)          # never blocks a session
        return result.stdout, result.stderr

    def lone_copy(self, hooks_module_source=None):
        """The script in a folder with install.py and its safety module (the link predicate lives there), its
        install-live-hooks.py sibling missing or replaced — install.py itself loads that sibling too."""
        folder = os.path.join(self.base, 'lone')
        os.makedirs(folder)
        for name in ('legacy-install-check.py', 'install.py', 'install_safety.py'):
            shutil.copy(os.path.join(SCRIPTS, name), folder)
        if hooks_module_source is not None:
            with open(os.path.join(folder, 'install-live-hooks.py'), 'w') as handle:
                handle.write(hooks_module_source)
        return os.path.join(folder, 'legacy-install-check.py')


class Clean(Fixture):
    def test_a_clean_home_prints_nothing_and_exits_0(self):
        self.assertEqual(self.run_check(), ('', ''))

    def test_a_clean_home_with_settings_and_the_plugins_own_hooks_is_still_silent(self):
        self.settings({'PostToolUse': [{'matcher': 'Edit|Write', 'hooks': [{'type': 'command', 'command': PLUGIN_HOOK}]}]})
        self.assertEqual(self.run_check(), ('', ''))

    def test_a_regular_file_or_directory_where_a_link_used_to_be_is_not_a_legacy_link(self):
        os.makedirs(os.path.join(self.dot, 'modes'))
        open(os.path.join(self.dot, 'CLAUDE.md'), 'w').close()
        self.assertEqual(self.run_check(), ('', ''))

    def test_a_link_that_is_not_one_of_the_old_ones_is_ignored(self):
        os.symlink(self.checkout, os.path.join(self.dot, 'my-own-link'))
        self.assertEqual(self.run_check(), ('', ''))


class Links(Fixture):
    def test_one_link_gives_one_paragraph_naming_it_and_the_resolved_remove_command(self):
        self.link('modes')
        out, err = self.run_check()
        self.assertEqual(err, '')
        self.assertEqual(out.count('\n'), 1, out)
        self.assertTrue(out.startswith('⚠️ adyusuf: the old symlinked install is still present'), out)
        self.assertIn('1 symlink(s) under ~/.claude (modes)', out)
        self.assertNotIn('settings.json', out)
        self.assertIn(f'python3 {self.checkout}/scripts/install.py --remove --no-monitor', out)
        self.assertNotIn(FALLBACK, out)
        self.assertIn('load TWICE', out)

    def test_several_links_are_counted_and_named_by_their_last_path_part(self):
        for name in ('CLAUDE.md', 'standards', os.path.join('skills', 'adyusuf')):
            self.link(name)
        out, _ = self.run_check()
        self.assertIn('3 symlink(s) under ~/.claude (CLAUDE.md, standards, adyusuf)', out)

    def test_a_dangling_link_is_still_reported_and_names_the_placeholder_checkout(self):
        self.link('docs', os.path.join(self.base, 'gone', 'docs'))
        out, _ = self.run_check()
        self.assertIn('1 symlink(s) under ~/.claude (docs)', out)
        self.assertIn(f'python3 {FALLBACK}/scripts/install.py --remove --no-monitor', out)

    def test_the_checkout_comes_from_the_first_link_that_points_into_one(self):
        self.link('agents', os.path.join(self.base, 'elsewhere', 'agents'))     # dangling: no install.py there
        self.link('modes')
        out, _ = self.run_check()
        self.assertIn(f'python3 {self.checkout}/scripts/install.py', out)

    def test_checkout_of_needs_an_install_py_beside_the_target(self):
        link = os.path.join(self.dot, 'modes')
        os.symlink(os.path.join(self.checkout, 'modes'), link)
        self.assertEqual(check.checkout_of([link]), self.checkout)
        os.remove(os.path.join(self.checkout, 'scripts', 'install.py'))
        self.assertIsNone(check.checkout_of([link]))
        self.assertIsNone(check.checkout_of([]))


class Settings(Fixture):
    def entries(self, *commands):
        return {'PreToolUse': [{'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': c} for c in commands]}]}

    def test_a_legacy_settings_entry_is_named_without_any_link(self):
        self.settings(self.entries(GUARD))
        out, err = self.run_check()
        self.assertEqual(err, '')
        self.assertIn('1 old hook entry in ~/.claude/settings.json', out)
        self.assertNotIn('symlink(s)', out)
        self.assertIn(f'python3 {FALLBACK}/scripts/install.py --remove --no-monitor', out)

    def test_entries_are_counted_across_events_and_the_plural_is_right(self):
        events = self.entries(GUARD)
        events['Stop'] = [{'hooks': [{'type': 'command', 'command': MD_HOOK}]}]
        self.settings(events)
        out, _ = self.run_check()
        self.assertIn('2 old hook entries in ~/.claude/settings.json', out)

    def test_every_command_the_old_installer_ever_wrote_is_found(self):
        spec = importlib.util.spec_from_file_location('install_live_hooks', HOOKS_MODULE)
        hooks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hooks)
        self.assertGreaterEqual(len(hooks.LEGACY), 3)
        for command in sorted(hooks.LEGACY):
            self.settings(self.entries(command))
            self.assertIn('1 old hook entry', self.run_check()[0], command)

    def test_links_and_entries_are_reported_together_in_one_paragraph(self):
        self.link('modes')
        self.settings(self.entries(GUARD, 'echo mine'))
        out, _ = self.run_check()
        self.assertEqual(out.count('\n'), 1)
        self.assertIn('1 symlink(s) under ~/.claude (modes) and 1 old hook entry in ~/.claude/settings.json', out)

    def test_the_plugins_own_commands_and_foreign_hooks_are_not_legacy(self):
        self.settings(self.entries(PLUGIN_HOOK, 'bash "$HOME/.claude/scripts/my-own.sh"'))
        self.assertEqual(self.run_check(), ('', ''))

    def test_settings_of_an_unexpected_shape_do_not_crash_the_check(self):
        for text in ('[]', '{"hooks": []}', '{"hooks": {"Stop": "x"}}', '{"hooks": {"Stop": [1, {"hooks": [2, null]}]}}'):
            self.settings(text=text)
            self.assertEqual(self.run_check(), ('', ''), text)

    def test_a_group_whose_hooks_is_not_a_list_is_ignored_silently_and_a_later_legacy_entry_is_still_found(self):
        self.settings(text='{"hooks": {"Stop": [{"hooks": 3}]}}')
        self.assertEqual(self.run_check(), ('', ''))                 # no stderr line, no traceback, nothing reported
        self.settings(text=json.dumps({'hooks': {'Stop': [{'hooks': 3}, {'hooks': [{'type': 'command', 'command': GUARD}]}]}}))
        self.assertIn('1 old hook entry', self.run_check()[0])

    def test_unreadable_settings_are_one_stderr_line_and_exit_0(self):
        self.settings(text='{ not json')
        out, err = self.run_check()
        self.assertEqual(out, '')
        self.assertEqual(err.count('\n'), 1, err)
        self.assertIn(f'cannot read {os.path.join(self.dot, "settings.json")}', err)

    def test_a_settings_path_that_cannot_be_opened_is_the_same_one_line(self):
        os.makedirs(os.path.join(self.dot, 'settings.json'))        # a directory where the file should be
        out, err = self.run_check()
        self.assertEqual((out, err.count('\n')), ('', 1), err)
        self.assertIn('cannot read', err)

    def test_unreadable_settings_do_not_hide_a_legacy_link(self):
        self.link('modes')
        self.settings(text='{ not json')
        out, err = self.run_check()
        self.assertIn('1 symlink(s) under ~/.claude (modes)', out)
        self.assertIn('cannot read', err)


class Failures(Fixture):
    def test_a_missing_install_live_hooks_module_is_named_on_stderr_and_the_session_goes_on(self):
        # install.py loads that sibling too, so both loads fail: two lines, nothing on stdout, still exit 0.
        self.link('modes')
        out, err = self.run_check(script=self.lone_copy())
        self.assertEqual(out, '')
        self.assertIn('cannot load install.py', err)
        self.assertIn('cannot load install-live-hooks.py', err)
        self.assertEqual(err.count('\n'), 2)

    def test_in_process_the_links_are_still_reported_when_only_the_hooks_module_cannot_load(self):
        self.link('modes')
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {'HOME': self.home}), \
                mock.patch.object(check, 'load_hooks_module', side_effect=ImportError('gone')), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(check.main(), 0)
        self.assertIn('1 symlink(s) under ~/.claude (modes)', out.getvalue())
        self.assertEqual(err.getvalue().strip(), 'adyusuf legacy-install-check: cannot load install-live-hooks.py: gone')

    def test_in_process_a_missing_module_leaves_one_stderr_line_per_module_and_exit_0(self):
        self.link('modes')
        empty = os.path.join(self.base, 'no-sibling')
        os.makedirs(empty)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {'HOME': self.home}), mock.patch.object(check, 'HERE', empty), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(check.main(), 0)
        self.assertEqual(out.getvalue(), '')
        self.assertIn('cannot load install.py', err.getvalue())
        self.assertIn('cannot load install-live-hooks.py', err.getvalue())

    def test_in_process_the_main_guard_turns_any_exception_into_a_stderr_line_and_exit_0(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {'HOME': self.home}), \
                mock.patch.object(importlib.util, 'module_from_spec', side_effect=RuntimeError('boom')), \
                contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            runpy.run_path(CHECK, run_name='__main__')
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(err.getvalue().strip(), 'adyusuf legacy-install-check: RuntimeError: boom')

    def test_a_broken_install_live_hooks_module_is_the_same_line(self):
        out, err = self.run_check(script=self.lone_copy('def broken(:\n'))
        self.assertEqual(out, '')
        self.assertIn('cannot load install-live-hooks.py', err)

    def test_any_other_failure_is_named_on_stderr_and_still_exits_0(self):
        out, err = self.run_check(script=self.lone_copy("raise RuntimeError('boom')\n"))
        self.assertEqual(out, '')
        self.assertEqual(err.strip(), 'adyusuf legacy-install-check: RuntimeError: boom')

    def test_the_home_variable_wins_and_without_it_the_users_home_is_used(self):
        with mock.patch.dict(os.environ, {'HOME': '/from/env'}):
            self.assertEqual(check.home_dir(), '/from/env')
        without = {k: v for k, v in os.environ.items() if k != 'HOME'}
        with mock.patch.dict(os.environ, without, clear=True), \
                mock.patch.object(os.path, 'expanduser', return_value='/from/passwd'):
            self.assertEqual(check.home_dir(), '/from/passwd')


class Message(unittest.TestCase):
    def test_the_command_names_the_checkout_and_asks_for_a_new_session(self):
        text = check.message(['/h/.claude/modes'], [], '/work/ccs')
        self.assertIn('run: python3 /work/ccs/scripts/install.py --remove --no-monitor  (then start a new session)', text)

    def test_the_plural_of_entries(self):
        self.assertIn('1 old hook entry in', check.message([], ['a'], None))
        self.assertIn('2 old hook entries in', check.message([], ['a', 'b'], None))


if __name__ == '__main__':
    unittest.main()
