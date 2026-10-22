"""scripts/plugin-setup.py — finding the `claude` program when it is not on PATH (a Windows terminal opened before the
install, or a machine that has only the Claude desktop app and no terminal install)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plugin_setup_helpers import Case, Fake, github_market, setup  # noqa: E402
import types  # noqa: E402


def touch(*parts):
    path = os.path.join(*parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('')
    return path


class Locate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = self.tmp.name
        self.env = {'PATH': '/usr/bin'}

    def ctx(self, on_path=False):
        return types.SimpleNamespace(home=self.home, which=lambda tool: '/x/claude' if on_path else None,
                                     exists=lambda path: path.startswith(self.home) and os.path.isfile(path))

    def test_a_claude_on_path_needs_nothing(self):
        self.assertEqual(setup.locate_claude(self.ctx(True), None, self.env), (None, None))
        self.assertEqual(self.env['PATH'], '/usr/bin')

    def test_a_claude_in_the_installers_folder_joins_path_for_this_run(self):
        path = touch(self.home, '.local', 'bin', 'claude.exe')
        note, problem = setup.locate_claude(self.ctx(), None, self.env)
        self.assertIsNone(problem)
        self.assertIn(path, note)
        self.assertTrue(self.env['PATH'].startswith(os.path.dirname(path) + os.pathsep))

    def test_the_npm_folder_on_windows_is_searched(self):
        env = dict(self.env, APPDATA=os.path.join(self.home, 'AppData', 'Roaming'))
        path = touch(env['APPDATA'], 'npm', 'claude.cmd')
        self.assertIn(path, setup.locate_claude(self.ctx(), None, env)[0])

    def test_the_desktop_apps_own_copy_is_found_on_windows(self):
        env = dict(self.env, APPDATA=os.path.join(self.home, 'AppData', 'Roaming'))
        path = touch(env['APPDATA'], 'Claude', 'claude-code', '2.1.308', 'abc123', 'claude.exe')
        note, problem = setup.locate_claude(self.ctx(), None, env)
        self.assertEqual((problem, path in note), (None, True))

    def test_the_desktop_apps_own_copy_is_found_on_macos(self):
        path = touch(self.home, 'Library', 'Application Support', 'Claude', 'claude-code', '2.1.308', 'abc123',
                     'claude.app', 'Contents', 'MacOS', 'claude')
        self.assertIn(path, setup.locate_claude(self.ctx(), None, self.env)[0])

    def test_the_newest_desktop_version_wins_numerically_not_alphabetically(self):
        base = ('Library', 'Application Support', 'Claude', 'claude-code')
        touch(self.home, *base, '2.1.9', 'aaa', 'claude')
        newest = touch(self.home, *base, '2.1.10', 'bbb', 'claude')
        self.assertIn(newest, setup.locate_claude(self.ctx(), None, self.env)[0])

    def test_an_explicit_path_beats_path_and_must_exist(self):
        path = touch(self.home, 'custom', 'claude')
        self.assertIn(path, setup.locate_claude(self.ctx(True), path, self.env)[0])
        _, problem = setup.locate_claude(self.ctx(True), os.path.join(self.home, 'nope'), self.env)
        self.assertIn('does not exist', problem)

    def test_when_nothing_is_found_the_message_gives_both_ways_forward(self):
        _, problem = setup.locate_claude(self.ctx(), None, self.env)
        self.assertIn('claude is not on PATH', problem)
        self.assertIn("desktop app's own copy", problem)
        self.assertIn('/plugin marketplace add adyusuf/claude-code-standards#prod', problem)
        self.assertIn('/plugin install adyusuf@adyusuf-marketplace', problem)
        self.assertIn('--claude <full path>', problem)


class InTheRun(Case):
    def test_a_found_claude_is_announced_and_the_run_goes_on(self):
        fake = Fake(self.home, market=github_market())
        code, out, _ = self.go(fake, which=lambda tool: '/bin/git' if tool == 'git' else None,
                               existing=(os.path.join(self.home, '.local', 'bin', 'claude'),))
        self.assertEqual(code, 0)
        self.assertIn('not on PATH — its folder is added to PATH for this run only', out)

    def test_nothing_found_stops_before_any_command_with_the_way_forward(self):
        fake = Fake(self.home)
        code, _, err = self.go(fake, which=lambda tool: '/bin/git' if tool == 'git' else None)
        self.assertEqual(code, 2)
        self.assertIn('/plugin install adyusuf@adyusuf-marketplace', err)
        self.assertEqual(fake.commands, [])


if __name__ == '__main__':
    unittest.main()
