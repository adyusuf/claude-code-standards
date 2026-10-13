"""scripts/install_channel.py — which checkout of this repository is on prod (default), test or dev.

Real git repositories throughout: an "origin" with prod and test branches and a clone of it, the way a
person who cloned from GitHub has it. What matters: the user's own checkout is never switched, an EXISTING
worktree is reused as it is, NOTHING is ever created (`create` is accepted and ignored), and a download without
git still resolves prod.
"""
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('install_channel', os.path.join(SCRIPTS, 'install_channel.py'))
channel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(channel)


def git(cwd, *args):
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True)


class Repos(unittest.TestCase):
    def setUp(self):
        self.top = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.top, True)
        seed = os.path.join(self.top, 'seed')
        os.makedirs(seed)
        git(seed, 'init', '-q', '-b', 'prod')
        git(seed, 'config', 'user.email', 't@t')
        git(seed, 'config', 'user.name', 't')
        with open(os.path.join(seed, 'CLAUDE.md'), 'w') as handle:
            handle.write('prod\n')
        git(seed, 'add', '-A')
        git(seed, 'commit', '-qm', 'prod')
        git(seed, 'branch', 'test')
        self.origin = os.path.join(self.top, 'origin.git')
        git(self.top, 'clone', '-q', '--bare', seed, self.origin)
        self.clone = os.path.join(self.top, 'standards')
        git(self.top, 'clone', '-q', self.origin, self.clone)          # on prod, like a GitHub clone

    def head(self, repo):
        return channel.branch_of(repo)


class Resolve(Repos):
    def add_worktree(self, branch):
        """What a person who wants a test checkout does by hand: git worktree add ../standards-<branch>."""
        path = f'{self.clone}-{branch}'
        git(self.clone, 'worktree', 'add', '-q', path, branch)
        return path

    def test_prod_from_a_prod_clone_is_the_clone_itself(self):
        path, said = channel.resolve(self.clone, 'prod')
        self.assertEqual(path, self.clone)
        self.assertIn('on prod', said)

    def test_a_branch_with_no_checkout_is_refused_and_nothing_is_created(self):
        path, said = channel.resolve(self.clone, 'test')
        self.assertIsNone(path)
        self.assertIn('there is no test checkout of this repository (no worktree is created)', said)
        self.assertFalse(os.path.exists(self.clone + '-test'))
        self.assertEqual(self.head(self.clone), 'prod', 'the user\'s own checkout must never be switched')

    def test_create_is_accepted_and_ignored(self):
        path, _ = channel.resolve(self.clone, 'test', create=True)
        self.assertIsNone(path)
        self.assertFalse(os.path.exists(self.clone + '-test'), 'the old behaviour made a worktree here')

    def test_an_existing_worktree_is_used_as_it_is(self):
        made = self.add_worktree('test')
        path, said = channel.resolve(self.clone, 'test')
        self.assertEqual(path, made)
        self.assertIn('the existing test worktree, used as it is', said)
        self.assertEqual(self.head(self.clone), 'prod')

    def test_prod_from_a_test_checkout_finds_the_prod_worktree(self):
        test_path = self.add_worktree('test')
        path, said = channel.resolve(test_path, 'prod')
        self.assertEqual(os.path.normcase(path), os.path.normcase(self.clone))
        self.assertIn('the existing prod worktree, used as it is', said)

    def test_dev_is_a_channel_too(self):
        git(self.clone, 'branch', 'dev', 'prod')
        made = self.add_worktree('dev')
        path, _ = channel.resolve(self.clone, 'dev')
        self.assertEqual((path, self.head(path)), (made, 'dev'))

    def test_a_foreign_folder_where_a_worktree_would_go_is_never_used(self):
        os.makedirs(self.clone + '-test')
        path, _ = channel.resolve(self.clone, 'test')
        self.assertIsNone(path)

    def test_a_detached_head_is_not_on_any_branch(self):
        git(self.clone, 'checkout', '-q', '--detach')
        self.assertIsNone(self.head(self.clone))
        self.assertIsNone(channel.resolve(self.clone, 'prod')[0])

    def test_an_unknown_channel_is_refused_before_git_is_asked(self):
        path, said = channel.resolve(self.clone, 'main')
        self.assertIsNone(path)
        self.assertIn("unknown channel 'main' (one of prod, test, dev)", said)

    def test_worktree_on_finds_only_the_branch_asked_for(self):
        self.assertEqual(channel.worktree_on(self.clone, 'prod'), self.clone)
        self.assertIsNone(channel.worktree_on(self.clone, 'test'))


class GitIsMissing(unittest.TestCase):
    def test_a_machine_without_git_reads_as_exit_127_not_a_crash(self):
        with mock.patch.object(channel.subprocess, 'run', side_effect=FileNotFoundError('git')):
            result = channel.git('/x', 'status')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (127, '', 'git'))
        with mock.patch.object(channel.subprocess, 'run', side_effect=FileNotFoundError('git')):
            self.assertIsNone(channel.branch_of('/x'))


class WithoutGit(unittest.TestCase):
    """A GitHub ZIP download: no .git, so no branch to read."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def test_prod_installs_from_it_and_says_the_branch_is_unverified(self):
        path, said = channel.resolve(self.folder, 'prod')
        self.assertEqual(path, self.folder)
        self.assertIn('NOT a git checkout', said)

    def test_test_and_dev_need_a_clone(self):
        for name in ('test', 'dev'):
            with self.subTest(channel=name):
                path, said = channel.resolve(self.folder, name)
                self.assertIsNone(path)
                self.assertIn(f'--{name} cannot pick a branch: clone the repository', said)


if __name__ == '__main__':
    unittest.main()
