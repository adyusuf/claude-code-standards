"""scripts/install.py — the one-command live install (README Level 4).

The cases that matter most are the ones where something of the user's is in the way: a real
~/.claude/CLAUDE.md or folder must be MOVED to backups, never deleted or overwritten, and a refused
preflight must leave ~/.claude untouched.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
INSTALL = os.path.join(SCRIPTS, 'install.py')
GUARD = 'bash "$HOME/.claude/hooks/guard-destructive.sh"'

_spec = importlib.util.spec_from_file_location('install', INSTALL)
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)

NAMES = ('CLAUDE.md', 'agents', 'docs', 'modes', 'scripts', 'standards', os.path.join('skills', 'adyusuf'))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.addCleanup(shutil.rmtree, self.repo, True)
        with open(os.path.join(self.repo, 'CLAUDE.md'), 'w') as handle:
            handle.write('# rules\n')
        for folder in ('agents', 'docs', 'modes', 'scripts', 'standards', 'plugin/commands', 'plugin/skills/s',
                       'plugin/.claude-plugin'):
            os.makedirs(os.path.join(self.repo, *folder.split('/')))
        for name, text in (('scripts/guard-destructive.sh', '#!/bin/sh\n'), ('agents/qa.md', 'qa\n'),
                           ('plugin/.claude-plugin/plugin.json', '{"name": "adyusuf", "version": "1.0.0"}'),
                           ('plugin/skills/s/SKILL.md', 'skill\n'), ('plugin/commands/c.md', 'command\n')):
            with open(os.path.join(self.repo, *name.split('/')), 'w') as handle:
                handle.write(text)
        os.makedirs(os.path.join(self.home, '.claude'))
        self.settings = os.path.join(self.home, '.claude', 'settings.json')
        with open(self.settings, 'w') as handle:
            handle.write('{"theme": "dark"}\n')

    def run_install(self, *args):
        # --no-monitor: the monitor is on by default, and these tests are about the links and the hooks.
        return subprocess.run([sys.executable, INSTALL, '--home', self.home, '--repo', self.repo, '--no-monitor', *args],
                              capture_output=True, text=True, encoding='utf-8', errors='replace')

    def claude(self, *parts):
        return os.path.join(self.home, '.claude', *parts)

    def store(self, *parts):
        """~/.claude-standards: backups and logs live outside ~/.claude, out of Claude Code's cleanup."""
        return os.path.join(self.home, '.claude-standards', *parts)

    def backups(self):
        """What install backups hold of the user's own things, as '<install-stamp>/<name>' (the manifest and the
        settings.json copy every install keeps are not listed)."""
        folder, found = self.store('backups'), []
        for stamp in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            if stamp.startswith('install-'):
                found += [f'{stamp}/{name}' for name in sorted(os.listdir(os.path.join(folder, stamp)))
                          if name not in ('manifest.json', 'settings.json')]
        return found

    def assert_linked(self, name, source):
        link = self.claude(name)
        self.assertTrue(os.path.islink(link), f'{name} is not a symlink')
        self.assertTrue(install.hooks.same_path(os.readlink(link), source), f'{name} -> {os.readlink(link)}')

    def guard_registered(self):
        with open(self.settings, encoding='utf-8') as handle:
            data = json.load(handle)
        return GUARD in [h['command'] for e in data.get('hooks', {}).get('PreToolUse', []) for h in e['hooks']]


class Install(Fixture):
    def test_a_fresh_install_links_everything_and_registers_the_guard(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        repo = os.path.realpath(self.repo)
        for name in NAMES[:-1]:
            self.assert_linked(name, os.path.join(repo, name))
        self.assert_linked(NAMES[-1], os.path.join(repo, 'plugin'))
        self.assertTrue(self.guard_registered())
        with open(self.settings, encoding='utf-8') as handle:
            self.assertEqual(json.load(handle)['theme'], 'dark')     # other settings kept

    def test_a_real_CLAUDE_md_is_moved_to_backups_never_deleted(self):
        with open(self.claude('CLAUDE.md'), 'w') as handle:
            handle.write('my own rules\n')
        self.assertEqual(self.run_install().returncode, 0)
        moved = [name for name in self.backups() if name.endswith('/CLAUDE.md')]
        self.assertEqual(len(moved), 1)
        with open(self.store('backups', *moved[0].split('/'))) as handle:
            self.assertEqual(handle.read(), 'my own rules\n')
        self.assert_linked('CLAUDE.md', os.path.join(os.path.realpath(self.repo), 'CLAUDE.md'))

    def test_a_real_folder_in_the_way_is_moved_with_its_content(self):
        os.makedirs(self.claude('agents'))
        with open(self.claude('agents', 'mine.md'), 'w') as handle:
            handle.write('x')
        self.assertEqual(self.run_install().returncode, 0)
        moved = [name for name in self.backups() if name.endswith('/agents')]
        self.assertEqual(len(moved), 1)
        self.assertTrue(os.path.exists(self.store('backups', *moved[0].split('/'), 'mine.md')))

    def test_running_it_twice_changes_nothing(self):
        self.run_install()
        result = self.run_install()
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('linked', result.stdout.replace('unlinked', ''))
        self.assertEqual(self.backups(), [])

    def test_a_link_pointing_elsewhere_is_repointed(self):
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other, True)
        os.symlink(other, self.claude('modes'), target_is_directory=True)
        self.assertEqual(self.run_install().returncode, 0)
        self.assert_linked('modes', os.path.join(os.path.realpath(self.repo), 'modes'))
        self.assertTrue(os.path.isdir(other), 'the old target must survive: only the link is replaced')


class CheckAndRemove(Fixture):
    def test_check_fails_before_and_passes_after(self):
        self.assertEqual(self.run_install('--check').returncode, 1)
        self.run_install()
        result = self.run_install('--check')
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_remove_takes_out_only_our_links_and_the_hook(self):
        self.run_install()
        foreign = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, foreign, True)
        install.unlink(self.claude('docs'))
        os.symlink(foreign, self.claude('docs'), target_is_directory=True)     # not ours: must stay
        self.assertEqual(self.run_install('--remove').returncode, 0)
        for name in ('CLAUDE.md', 'agents', 'modes', 'scripts', 'standards', NAMES[-1]):
            self.assertFalse(os.path.lexists(self.claude(name)), name)
        self.assertTrue(os.path.islink(self.claude('docs')))
        self.assertFalse(self.guard_registered())
        self.assertTrue(os.path.isfile(os.path.join(self.repo, 'CLAUDE.md')), 'the checkout itself is untouched')


class InstallLog(Fixture):
    def logs(self):
        folder = self.store('logs')
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []

    def test_an_install_leaves_its_whole_output_in_a_log(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        [name] = self.logs()
        self.assertRegex(name, r'^install-\d{8}-\d{6}\.log$')
        with open(self.store('logs', name), encoding='utf-8') as handle:
            text = handle.read()
        for expected in ('linked', 'registered PreToolUse', '✓ installed'):
            self.assertIn(expected, text)
        self.assertIn(name, result.stdout, 'the console must say where the log is')

    def test_a_refusal_is_logged_too(self):
        os.remove(os.path.join(self.repo, 'CLAUDE.md'))
        self.assertEqual(self.run_install().returncode, 2)
        with open(self.store('logs', self.logs()[0]), encoding='utf-8') as handle:
            self.assertIn('does not exist', handle.read())

    def test_check_is_read_only_and_writes_no_log(self):
        self.run_install('--check')
        self.assertEqual(self.logs(), [])


class MonitorSwitch(Fixture):
    def test_monitor_sync_without_an_agent_registers_the_plugin_disabled(self):
        # No cm-agent at CM_AGENT_HOME -> not connected -> the plugin is switched OFF, other settings kept.
        agent_home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, agent_home, True)
        result = subprocess.run([sys.executable, INSTALL, '--home', self.home, '--monitor-sync'],
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                env=dict(os.environ, CM_AGENT_HOME=agent_home))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('DORMANT', result.stdout)
        with open(self.settings, encoding='utf-8') as handle:
            data = json.load(handle)
        self.assertIs(data['enabledPlugins']['monitor-agent@monitor-agent-local'], False)
        self.assertEqual(data['theme'], 'dark')


class Refusals(Fixture):
    def test_plugin_checked_out_without_symlinks_refuses_and_touches_nothing(self):
        # Windows without core.symlinks checks plugin/commands out as a text file holding "../commands".
        shutil.rmtree(os.path.join(self.repo, 'plugin', 'commands'))
        with open(os.path.join(self.repo, 'plugin', 'commands'), 'w') as handle:
            handle.write('../commands')
        result = self.run_install()
        self.assertEqual(result.returncode, 2)
        self.assertIn('core.symlinks', result.stderr)
        # Nothing in ~/.claude changes; the refusal leaves only its log, in ~/.claude-standards.
        self.assertEqual(sorted(os.listdir(self.claude())), ['settings.json'])
        self.assertFalse(self.guard_registered())

    def test_a_missing_source_refuses(self):
        shutil.rmtree(os.path.join(self.repo, 'standards'))
        result = self.run_install()
        self.assertEqual(result.returncode, 2)
        self.assertIn('does not exist', result.stderr)
        self.assertFalse(os.path.lexists(self.claude('CLAUDE.md')))


class Units(unittest.TestCase):
    def test_bash_is_found_in_git_for_windows_when_not_on_path(self):
        found = install.find_bash(lambda name: None, exists=lambda path: path == install.WINDOWS_BASH[0], windows=True)
        self.assertEqual(found, install.WINDOWS_BASH[0])

    def test_no_bash_anywhere_is_none(self):
        self.assertIsNone(install.find_bash(lambda name: None, exists=lambda path: False, windows=True))
        self.assertIsNone(install.find_bash(lambda name: None, exists=lambda path: True, windows=False))

    def test_preflight_errors_without_git_or_bash(self):
        errors, _ = install.preflight(install.DEFAULT_REPO, which=lambda name: None, windows=False)
        self.assertTrue(any('git is not on PATH' in error for error in errors))
        self.assertTrue(any('bash not found' in error for error in errors))

    def test_a_missing_symlink_privilege_names_the_fix(self):
        def refuse(*_args, **_kwargs):
            error = OSError('privilege')
            error.winerror = 1314
            raise error
        with self.assertRaises(SystemExit) as raised:
            install.make_link('link', 'source', True, symlink=refuse)
        self.assertIn('Developer Mode', str(raised.exception))

    def test_any_other_symlink_error_is_not_swallowed(self):
        def fail(*_args, **_kwargs):
            raise OSError('disk full')
        with self.assertRaises(OSError):
            install.make_link('link', 'source', False, symlink=fail)

class Channels(Fixture):
    """--prod (default) / --test end to end, from a real clone the way a GitHub user has one."""

    def make_clone(self):
        def git(cwd, *args):
            subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)
        for folder in ('agents', 'docs', 'modes', 'standards', 'plugin/commands', 'plugin/skills'):
            open(os.path.join(self.repo, folder, '.keep'), 'w').close()       # git keeps no empty folder
        git(self.repo, 'init', '-q', '-b', 'prod')
        git(self.repo, 'config', 'user.email', 't@t')
        git(self.repo, 'config', 'user.name', 't')
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-qm', 'rules')
        git(self.repo, 'branch', 'test')
        top = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, top, True)
        git(top, 'clone', '-q', '--bare', self.repo, 'origin.git')
        git(top, 'clone', '-q', 'origin.git', 'standards')
        return os.path.realpath(os.path.join(top, 'standards'))

    def install_from(self, clone, *args):
        return subprocess.run([sys.executable, INSTALL, '--home', self.home, '--repo', clone, '--no-monitor', *args],
                              capture_output=True, text=True, encoding='utf-8', errors='replace')

    def test_test_links_into_a_test_worktree_and_leaves_the_clone_on_prod(self):
        clone = self.make_clone()
        result = self.install_from(clone, '--test')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_linked('CLAUDE.md', os.path.join(clone + '-test', 'CLAUDE.md'))
        head = subprocess.run(['git', '-C', clone, 'symbolic-ref', '--short', 'HEAD'], capture_output=True, text=True)
        self.assertEqual(head.stdout.strip(), 'prod')

    def test_the_default_is_prod(self):
        clone = self.make_clone()
        self.assertEqual(self.install_from(clone).returncode, 0)
        self.assert_linked('CLAUDE.md', os.path.join(clone, 'CLAUDE.md'))

    def test_remove_undoes_a_test_install_without_being_told_the_channel(self):
        clone = self.make_clone()
        self.install_from(clone, '--test')
        self.assertEqual(self.install_from(clone, '--remove').returncode, 0)
        self.assertFalse(os.path.lexists(self.claude('CLAUDE.md')))

    def test_test_from_a_download_without_git_is_refused_before_anything_changes(self):
        result = self.run_install('--test')
        self.assertEqual(result.returncode, 2)
        self.assertIn('clone the repository', result.stderr)
        self.assertFalse(os.path.lexists(self.claude('CLAUDE.md')))


if __name__ == '__main__':
    unittest.main()
