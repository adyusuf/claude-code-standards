import os
import shutil
import subprocess
import tempfile
import unittest

# normpath, not just join: the path is handed to a coverage tracer's filter, and
# `.../tests/../require-private-remote.sh` does not match a scripts/ pattern even
# though it resolves to the same file.
HOOK = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'require-private-remote.sh'))


class RequirePrivateRemote(unittest.TestCase):
    """A fake `gh` on PATH answers as the test says and records what it was asked."""

    def setUp(self):
        self.bin = tempfile.mkdtemp()
        self.log = os.path.join(self.bin, 'asked.txt')
        gh = os.path.join(self.bin, 'gh')
        with open(gh, 'w') as handle:
            handle.write('#!/bin/sh\necho "$@" >> "$FAKE_GH_LOG"\necho "$FAKE_GH_SAYS"\nexit "${FAKE_GH_STATUS:-0}"\n')
        os.chmod(gh, 0o755)

    def tearDown(self):
        shutil.rmtree(self.bin, ignore_errors=True)

    def push(self, url, says='true', status='0', path=None):
        # The fake `gh` goes FIRST so the real one is never reached, but the rest of
        # PATH is kept. Replacing PATH wholesale also dropped the coverage shim
        # (scripts/coverage-shell.sh), so this hook measured 0% while being fully
        # exercised — the tests were fine, the measurement could not see them.
        env = dict(os.environ, PATH=path or f'{self.bin}:' + os.environ.get('PATH', '/usr/bin:/bin'),
                   FAKE_GH_SAYS=says, FAKE_GH_STATUS=status, FAKE_GH_LOG=self.log)
        return subprocess.run(['bash', HOOK, 'origin', url], capture_output=True, text=True, env=env)

    def asked(self):
        with open(self.log) as handle:
            return handle.read()

    def test_a_private_repository_is_allowed(self):
        self.assertEqual(self.push('https://github.com/me/cfg.git', says='true').returncode, 0)

    def test_a_public_repository_is_refused_and_named(self):
        result = self.push('https://github.com/me/cfg.git', says='false')
        self.assertEqual(result.returncode, 1)
        self.assertIn('PUBLIC', result.stderr)

    def test_an_answer_that_is_not_true_is_refused_because_could_not_check_is_not_private(self):
        result = self.push('https://github.com/me/cfg.git', says='HTTP 401: Bad credentials', status='1')
        self.assertEqual(result.returncode, 1)
        self.assertIn('could not confirm', result.stderr)

    def test_a_missing_gh_refuses(self):
        result = self.push('https://github.com/me/cfg.git', path='/usr/bin:/bin')
        self.assertEqual(result.returncode, 1)
        self.assertIn('gh is not installed', result.stderr)

    def test_a_remote_that_is_not_github_is_refused(self):
        for url in ('https://gitlab.com/me/cfg.git', '/some/local/path', 'ssh://host/me/cfg.git'):
            with self.subTest(url=url):
                self.assertEqual(self.push(url).returncode, 1)

    def test_every_github_url_form_asks_about_owner_slash_repo(self):
        for url in ('https://github.com/me/cfg.git', 'https://github.com/me/cfg', 'git@github.com:me/cfg.git',
                    'ssh://git@github.com/me/cfg.git', 'https://tok@github.com/me/cfg.git'):
            with self.subTest(url=url):
                if os.path.exists(self.log):
                    os.remove(self.log)
                self.assertEqual(self.push(url).returncode, 0)
                self.assertIn('repos/me/cfg', self.asked())


if __name__ == '__main__':
    unittest.main()
