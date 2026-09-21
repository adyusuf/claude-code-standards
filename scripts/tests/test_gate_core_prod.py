"""The prod branch of the shared gate — the one that had no tests.

This is where rule #33 is enforced: prod never carries code that is not already
running on test, and it never carries code the e2e suite has not run against.
Both checks are the kind that are worthless if they fail OPEN, so the tests here
are mostly about what happens when something is missing or ambiguous:

  · no way to read the deployed SHA -> SKIPPED, and a skip is not a pass;
  · the version endpoint answers with the SPA's HTML instead of a SHA -> failure,
    not "looks fine" (the fallback swallowing /version is a recorded incident);
  · several sites on test reporting DIFFERENT SHAs -> not deployed;
  · no e2e suite at all -> "nothing proves this promotion".

The gate is run from its real path so the measurement lands on it; see the note
in test_gate_core_fixes.py.
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GATE = os.path.join(SCRIPTS, 'gate-core.sh')
ANSI = re.compile(r'\x1b\[[0-9;]*m')

RULE_16_DOCS = {'SETUP.md': '# Setup\n## Secret and token inventory\n', '.env.example': ''}


class ProdGate(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        subprocess.run(['git', 'init', '-q', self.root], check=True)
        subprocess.run(['git', 'config', 'user.email', 't@t'], cwd=self.root, check=True)
        subprocess.run(['git', 'config', 'user.name', 't'], cwd=self.root, check=True)
        os.makedirs(os.path.join(self.root, 'scripts'), exist_ok=True)
        self.bin = os.path.join(self.root, '.stubbin')
        os.makedirs(self.bin)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def stub(self, name, body):
        path = os.path.join(self.bin, name)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(body)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def write(self, relative, text):
        path = os.path.join(self.root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)

    def commit(self):
        subprocess.run(['git', 'add', '-A'], cwd=self.root, check=True)
        subprocess.run(['git', 'commit', '-qm', 'base'], cwd=self.root, check=True)
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.root,
                              capture_output=True, text=True).stdout.strip()

    def setup_project(self, conf='', extra=None):
        files = dict(RULE_16_DOCS)
        files['scripts/merge-gate.conf'] = conf
        files.update(extra or {})
        for name, text in files.items():
            self.write(name, text)
        return self.commit()

    def run_gate(self, *args):
        env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ['PATH'])
        result = subprocess.run(['bash', GATE, 'prod', *args], cwd=self.root,
                                capture_output=True, text=True, env=env)
        return ANSI.sub('', result.stdout), result.returncode


class DeployVerification(ProdGate):
    def test_with_no_source_configured_it_skips_and_does_not_pass(self):
        self.setup_project()
        out, code = self.run_gate()
        self.assertIn('the deployed SHA cannot be read', out)
        self.assertIn('GATE INCOMPLETE', out)
        self.assertNotEqual(0, code, 'an unverified deploy must never exit 0')

    def test_a_command_reporting_this_sha_passes(self):
        sha = self.setup_project()
        # Written AFTER the commit and left uncommitted on purpose: the conf has
        # to name HEAD's own SHA, and committing it would move HEAD.
        self.write('scripts/merge-gate.conf', f'TEST_DEPLOY_SHA_CMD="echo {sha}"\n')
        out, _ = self.run_gate()
        self.assertIn('the test environment is running this code', out)

    def test_a_command_reporting_a_different_sha_fails(self):
        self.setup_project(conf='TEST_DEPLOY_SHA_CMD="echo deadbeefdeadbeef"\n')
        out, code = self.run_gate()
        self.assertIn('not', out)
        self.assertIn('GATE CLOSED', out)
        self.assertEqual(1, code)

    def test_html_from_the_version_endpoint_is_a_failure_not_a_sha(self):
        # Recorded incident: the SPA fallback answers /version with index.html,
        # and a lenient reader finds a hex-looking string in the bundle name.
        self.stub('curl', '#!/bin/sh\necho "<!DOCTYPE html><html>deadbeef</html>"\n')
        self.setup_project(conf='TEST_VERSION_URL="http://test.example/version"\n')
        out, code = self.run_gate()
        self.assertIn('returned HTML, not a version', out)
        self.assertEqual(1, code)

    def test_a_version_endpoint_with_no_sha_fails(self):
        self.stub('curl', '#!/bin/sh\necho "ok"\n')
        self.setup_project(conf='TEST_VERSION_URL="http://test.example/version"\n')
        out, code = self.run_gate()
        self.assertIn('reports no commit SHA', out)
        self.assertEqual(1, code)

    def test_two_sites_reporting_different_shas_are_not_deployed(self):
        # A project with several sites on test is deployed only when ALL agree.
        self.stub('curl', '#!/bin/sh\ncase "$*" in *one*) echo aaaaaaa;; *) echo bbbbbbb;; esac\n')
        self.setup_project(conf='TEST_VERSION_URL="http://one.example/v http://two.example/v"\n')
        out, code = self.run_gate()
        self.assertIn('while another site reports', out)
        self.assertEqual(1, code)

    def test_a_matching_short_sha_from_the_endpoint_passes(self):
        sha = self.setup_project(conf='TEST_VERSION_URL="http://test.example/version"\n')
        self.stub('curl', f'#!/bin/sh\necho "{sha[:7]}"\n')  # the short SHA must satisfy it
        out, _ = self.run_gate()
        self.assertIn('the test environment is running this code', out)


class E2eIsRequired(ProdGate):
    def test_with_no_suite_the_promotion_is_unproven(self):
        self.setup_project(conf='TEST_DEPLOY_SHA_CMD="echo x"\n')
        out, code = self.run_gate()
        self.assertIn('nothing proves this promotion', out)
        self.assertNotEqual(0, code)

    def test_a_configured_web_suite_is_run(self):
        marker = os.path.join(self.root, 'e2e-ran.txt')
        sha = self.setup_project(extra={'e2e/smoke.spec.ts': "test('s', () => {})\n"})
        self.write('scripts/merge-gate.conf',
                   f'TEST_DEPLOY_SHA_CMD="echo {sha}"\nE2E_WEB_CMD="touch {marker}"\n')
        out, code = self.run_gate()
        self.assertTrue(os.path.exists(marker), f'the e2e command was never run:\n{out}')
        self.assertIn('web e2e', out)

    def test_a_failing_e2e_suite_closes_the_gate(self):
        sha = self.setup_project(extra={'e2e/smoke.spec.ts': "test('s', () => {})\n"})
        self.write('scripts/merge-gate.conf',
                   f'TEST_DEPLOY_SHA_CMD="echo {sha}"\nE2E_WEB_CMD="exit 1"\n')
        out, code = self.run_gate()
        self.assertIn('GATE CLOSED', out)
        self.assertEqual(1, code)

    def test_the_list_mode_names_the_deploy_check_without_running_it(self):
        self.stub('curl', '#!/bin/sh\necho SHOULD_NOT_RUN\n')
        self.setup_project(conf='TEST_VERSION_URL="http://test.example/version"\n')
        out, _ = self.run_gate('--list')
        self.assertIn('deploy verification', out)
        self.assertNotIn('SHOULD_NOT_RUN', out)

    def test_the_list_mode_says_when_nothing_is_configured(self):
        self.setup_project()
        out, _ = self.run_gate('--list')
        self.assertIn('no source configured', out)


if __name__ == '__main__':
    unittest.main()
