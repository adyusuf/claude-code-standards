"""bin/adyusuf-check: the plugin's one command on the Bash PATH, and the folder that keeps the plugin Claude Code only.

Every run uses a temporary HOME and an empty CM_AGENT_HOME: the command reads ~/.claude and writes
install.py's log under ~/.claude-standards, and neither may be the real one.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECK = os.path.join(ROOT, 'bin', 'adyusuf-check')
PLUGIN_ID = 'adyusuf@adyusuf-marketplace'


class AdyusufCheck(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)

    def run_check(self, *args, path=CHECK, env_path=None):
        env = dict(os.environ, HOME=self.home, CM_AGENT_HOME='', USERPROFILE=self.home)
        if env_path is not None:
            env['PATH'] = env_path
        # bash by absolute path, found on the caller's PATH: a test that strips PATH still starts it, and under
        # shell coverage this is the tracing shim (scripts/coverage-shell.sh).
        bash = shutil.which('bash')
        return subprocess.run([bash, path, *args], capture_output=True, text=True, env=env, timeout=60)

    def install_plugin(self):
        path = os.path.join(self.home, '.claude', 'plugins', 'installed_plugins.json')
        os.makedirs(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({'plugins': {PLUGIN_ID: [{'scope': 'user', 'installPath': '/p', 'version': 'abc'}]}}, handle)

    def test_it_is_executable_and_tracked_as_such(self):
        self.assertTrue(os.access(CHECK, os.X_OK))
        mode = subprocess.run(['git', 'ls-files', '-s', 'bin/adyusuf-check'], cwd=ROOT,
                              capture_output=True, text=True).stdout.split(' ')[0]
        self.assertEqual(mode, '100755')

    def test_an_empty_home_reports_the_missing_plugin_and_exits_1(self):
        done = self.run_check()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn('plugin: ✗ not installed', done.stdout)
        self.assertIn('✗ 1 problem(s)', done.stdout)

    def test_an_installed_plugin_with_nothing_old_left_exits_0(self):
        self.install_plugin()
        done = self.run_check()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn(f'plugin: ✓ installed: {PLUGIN_ID} abc (user scope) at /p', done.stdout)
        self.assertIn('✓ everything is in place', done.stdout)

    def test_it_names_the_plugin_root_it_runs_from(self):
        first = self.run_check().stdout.splitlines()[0]
        self.assertTrue(first.startswith('plugin root: '), first)
        self.assertTrue(os.path.samefile(first[len('plugin root: '):], ROOT))

    def test_a_link_on_the_path_still_finds_the_plugin_root(self):
        links = os.path.realpath(tempfile.mkdtemp())   # macOS: /var is a link to /private/var
        self.addCleanup(shutil.rmtree, links, True)
        os.symlink(os.path.relpath(CHECK, links), os.path.join(links, 'adyusuf-check'))
        done = self.run_check(path=os.path.join(links, 'adyusuf-check'))
        root = done.stdout.splitlines()[0][len('plugin root: '):]
        self.assertTrue(os.path.samefile(root, ROOT), done.stdout + done.stderr)

    def test_help_prints_the_usage_and_exits_0(self):
        done = self.run_check('--help')
        self.assertEqual(done.returncode, 0)
        self.assertIn('Usage: adyusuf-check', done.stdout)
        self.assertIn('claude.ai chat and Cowork refuse', done.stdout)

    def test_an_argument_is_refused_with_exit_2(self):
        done = self.run_check('--fix')
        self.assertEqual(done.returncode, 2)
        self.assertIn('takes no arguments (got: --fix)', done.stderr)

    def test_without_python3_it_says_so_and_exits_2(self):
        tools = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tools, True)
        for tool in ('dirname', 'readlink'):
            os.symlink(shutil.which(tool), os.path.join(tools, tool))
        done = self.run_check(env_path=tools)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn('needs python3', done.stderr)


class ClaudeCodeOnly(unittest.TestCase):
    """The top-level bin/ is what makes claude.ai chat and Cowork refuse the plugin (docs/decision-log.md)."""

    def test_the_plugin_root_has_a_top_level_bin_with_a_tracked_command(self):
        tracked = subprocess.run(['git', 'ls-files', 'bin'], cwd=ROOT, capture_output=True, text=True).stdout.split()
        self.assertIn('bin/adyusuf-check', tracked)


if __name__ == '__main__':
    unittest.main()
