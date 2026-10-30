"""scripts/runner-setup.sh - local GitHub Actions runners, at least two per project (user decision 29/10/2026).

`gh` and `curl` are replaced by stubs on PATH, and the "runner" is a tarball holding a config.sh / svc.sh that only
log their arguments. What is pinned: two runners are registered and started, the download is checked against the
checksum in the release notes, a second run changes nothing, a public repository gets the fork-approval policy
first (and nothing is installed if that fails), the registration token never reaches the output, fewer than two
runners is refused, and remove moves the folders aside instead of deleting them.
"""
import hashlib
import io
import os
import subprocess
import tarfile
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SCRIPT = os.path.join(ROOT, 'scripts', 'runner-setup.sh')
TOKEN = 'AAAA-SECRET-TOKEN-1234'

CONFIG_SH = '#!/bin/sh\necho "config $*" >> "$STUB_LOG"\nif [ "$1" != remove ]; then touch .runner; fi\n'
SVC_SH = '#!/bin/sh\necho "svc $*" >> "$STUB_LOG"\n'

# Answers by the arguments gh was called with; every call is logged.
GH_STUB = r'''#!/bin/sh
echo "gh $*" >> "$STUB_LOG"
case "$*" in
  *releases/latest*) printf 'v9.9.9\n<!-- BEGIN SHA osx-arm64 -->%s<!-- END SHA osx-arm64 -->\n<!-- BEGIN SHA osx-x64 -->%s<!-- END SHA osx-x64 -->\n' "$STUB_SHA" "$STUB_SHA" ;;
  *fork-pr-contributor-approval*) [ "${STUB_POLICY_FAILS:-}" = 1 ] && exit 1; exit 0 ;;
  *registration-token*|*remove-token*) echo "$STUB_TOKEN" ;;
  *actions/runners*) echo "github: stub online busy=false" ;;
  *"repos/"*) echo "${STUB_PRIVATE:-true}" ;;
esac
'''
CURL_STUB = '#!/bin/sh\necho "curl $*" >> "$STUB_LOG"\nwhile [ $# -gt 0 ]; do [ "$1" = -o ] && out="$2"; shift; done\ncp "$STUB_TARBALL" "$out"\n'


def make_tarball(path):
    with tarfile.open(path, 'w:gz') as tar:
        for name, body in (('config.sh', CONFIG_SH), ('svc.sh', SVC_SH)):
            data = body.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(data))
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class RunnerSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bin = os.path.join(self.tmp, 'bin')
        os.mkdir(self.bin)
        for name, body in (('gh', GH_STUB), ('curl', CURL_STUB)):
            path = os.path.join(self.bin, name)
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(body)
            os.chmod(path, 0o755)
        self.tarball = os.path.join(self.tmp, 'runner.tar.gz')
        self.sha = make_tarball(self.tarball)
        self.log = os.path.join(self.tmp, 'log')
        self.home = os.path.join(self.tmp, 'runners')

    def tearDown(self):
        subprocess.run(['rm', '-rf', self.tmp], check=False)

    def run_script(self, *args, **extra):
        env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ['PATH'], RUNNER_HOME=self.home,
                   STUB_LOG=self.log, STUB_SHA=extra.pop('sha', self.sha), STUB_TOKEN=TOKEN, STUB_TARBALL=self.tarball)
        env.update(extra)
        return subprocess.run(['bash', SCRIPT, *args], capture_output=True, text=True, env=env, check=False)

    def logged(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding='utf-8') as handle:
            return handle.read().splitlines()

    def test_installs_two_runners_and_starts_their_services(self):
        result = self.run_script('install', 'me/proj')
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.logged()
        self.assertEqual(len([line for line in log if line.startswith('config --unattended')]), 2)
        self.assertEqual(log.count('svc install'), 2)
        self.assertEqual(log.count('svc start'), 2)
        for n in ('1', '2'):
            self.assertTrue(os.path.isfile(os.path.join(self.home, 'me-proj', n, '.runner')))
        self.assertIn('--url https://github.com/me/proj', ' '.join(log))
        self.assertIn('github: stub online', result.stdout)

    def test_the_registration_token_is_never_printed(self):
        result = self.run_script('install', 'me/proj')
        self.assertNotIn(TOKEN, result.stdout + result.stderr)

    def test_a_second_install_changes_nothing(self):
        self.run_script('install', 'me/proj')
        before = self.logged().count('svc install')
        again = self.run_script('install', 'me/proj')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(self.logged().count('svc install'), before)
        self.assertEqual(again.stdout.count('already configured'), 2)

    def test_a_wrong_checksum_stops_the_install_and_keeps_the_file_aside(self):
        result = self.run_script('install', 'me/proj', sha='0' * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stderr)
        self.assertFalse([line for line in self.logged() if line.startswith('config ')])
        self.assertTrue([f for f in os.listdir(os.path.join(self.home, '.cache')) if f.endswith('.bad')])

    def test_fewer_than_two_runners_is_refused(self):
        result = self.run_script('install', 'me/proj', '--count', '1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('at least 2', result.stderr)

    def test_more_runners_than_two_are_allowed(self):
        self.assertEqual(self.run_script('install', 'me/proj', '--count', '3').returncode, 0)
        self.assertEqual(self.logged().count('svc start'), 3)

    def test_a_public_repository_gets_the_fork_approval_policy_first(self):
        result = self.run_script('install', 'me/proj', STUB_PRIVATE='false')
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.logged()
        policy = next(i for i, line in enumerate(log) if 'fork-pr-contributor-approval' in line)
        first_config = next(i for i, line in enumerate(log) if line.startswith('config '))
        self.assertLess(policy, first_config)
        self.assertIn('approval_policy=all_external_contributors', log[policy])

    def test_a_public_repository_installs_nothing_when_the_policy_cannot_be_set(self):
        result = self.run_script('install', 'me/proj', STUB_PRIVATE='false', STUB_POLICY_FAILS='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no runner was installed', result.stderr)
        self.assertFalse([line for line in self.logged() if line.startswith(('config ', 'svc '))])

    def test_a_private_repository_does_not_touch_the_fork_policy(self):
        self.run_script('install', 'me/proj')
        self.assertFalse([line for line in self.logged() if 'fork-pr-contributor-approval' in line])

    def test_status_lists_local_folders_and_what_github_reports(self):
        self.run_script('install', 'me/proj')
        result = self.run_script('status', 'me/proj')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('local: '), 2)
        self.assertIn('github: stub online', result.stdout)

    def test_remove_unregisters_and_moves_the_folders_aside(self):
        self.run_script('install', 'me/proj')
        result = self.run_script('remove', 'me/proj')
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.logged()
        self.assertEqual(log.count('svc stop'), 2)
        self.assertEqual(log.count('svc uninstall'), 2)
        self.assertEqual(len([line for line in log if line.startswith('config remove')]), 2)
        self.assertFalse(os.path.exists(os.path.join(self.home, 'me-proj', '1')))
        self.assertEqual(len(os.listdir(os.path.join(self.home, '.removed'))), 2)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)

    def test_usage_errors(self):
        self.assertEqual(self.run_script().returncode, 2)
        self.assertEqual(self.run_script('install', 'no-slash').returncode, 2)
        self.assertEqual(self.run_script('install', 'me/proj', '--bogus').returncode, 2)
        self.assertEqual(self.run_script('frobnicate', 'me/proj').returncode, 2)
        self.assertNotEqual(self.run_script('install', 'me/pr oj').returncode, 0)
        self.assertIn('must be a number', self.run_script('install', 'me/proj', '--count', 'x').stderr)


if __name__ == '__main__':
    unittest.main()
