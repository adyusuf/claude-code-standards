"""scripts/install_channel.py — which checkout `install.py --prod` (default) / `--test` links to.

Real git repositories throughout: an "origin" with prod and test branches and a clone of it, the way a
person who cloned from GitHub has it. What matters: the user's own checkout is never switched, an existing
worktree is reused, a new one is made only by an install, and a download without git still installs prod.
"""
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest

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
    def test_prod_from_a_prod_clone_is_the_clone_itself(self):
        path, said = channel.resolve(self.clone, 'prod')
        self.assertEqual(path, self.clone)
        self.assertIn('on prod', said)

    def test_test_makes_a_worktree_beside_it_and_leaves_the_clone_on_prod(self):
        path, said = channel.resolve(self.clone, 'test')
        self.assertEqual(path, self.clone + '-test')
        self.assertIn('new test worktree', said)
        self.assertEqual(self.head(path), 'test')
        self.assertEqual(self.head(self.clone), 'prod', 'the user\'s own checkout must never be switched')

    def test_an_existing_worktree_is_reused_not_made_again(self):
        first, _ = channel.resolve(self.clone, 'test')
        again, said = channel.resolve(self.clone, 'test')
        self.assertEqual(again, first)
        self.assertIn('existing test worktree', said)

    def test_prod_from_a_test_checkout_finds_the_prod_worktree(self):
        test_path, _ = channel.resolve(self.clone, 'test')
        path, _ = channel.resolve(test_path, 'prod')
        self.assertEqual(os.path.normcase(path), os.path.normcase(self.clone))

    def test_check_and_remove_never_create_a_worktree(self):
        path, said = channel.resolve(self.clone, 'test', create=False)
        self.assertIsNone(path)
        self.assertIn('no test checkout yet', said)
        self.assertFalse(os.path.exists(self.clone + '-test'))

    def test_a_foreign_folder_where_the_worktree_would_go_is_never_used(self):
        os.makedirs(self.clone + '-test')
        path, said = channel.resolve(self.clone, 'test')
        self.assertIsNone(path)
        self.assertIn('move it aside', said)

    def test_a_branch_the_clone_has_never_seen_is_refused(self):
        # A stale origin/test is a fine source offline, so the clone must not know the branch at all.
        git(self.origin, 'branch', '-D', 'test')
        git(self.clone, 'update-ref', '-d', 'refs/remotes/origin/test')
        path, said = channel.resolve(self.clone, 'test')
        self.assertIsNone(path)
        self.assertIn('could not create the test worktree', said)

    def test_an_unknown_channel_is_refused(self):
        self.assertIsNone(channel.resolve(self.clone, 'main')[0])

    def test_dev_is_a_channel_too(self):
        git(self.origin, 'branch', 'dev', 'prod')
        git(self.clone, 'fetch', '-q', 'origin')
        path, _ = channel.resolve(self.clone, 'dev')
        self.assertEqual(self.head(path), 'dev')


class WithoutGit(unittest.TestCase):
    """A GitHub ZIP download: no .git, so no branch to read."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def test_prod_installs_from_it_and_says_the_branch_is_unverified(self):
        path, said = channel.resolve(self.folder, 'prod')
        self.assertEqual(path, self.folder)
        self.assertIn('NOT a git checkout', said)

    def test_test_needs_a_clone(self):
        path, said = channel.resolve(self.folder, 'test')
        self.assertIsNone(path)
        self.assertIn('clone the repository', said)


if __name__ == '__main__':
    unittest.main()
