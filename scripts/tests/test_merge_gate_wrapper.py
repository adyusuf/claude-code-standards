"""scripts/merge-gate.sh — the wrapper every promotion in this repository goes through.

It was the one script at 0% coverage. Eight lines, and all it does is call the shared
core and then the twin-drift check — but nothing proved it called them, which is the
whole reason it exists. The tests below replace both callees with stubs so the wrapper
is the only real thing running.

What has to hold:
  * the target reaches the core verbatim, and `dev` is the default when none is given;
  * a core that fails stops the wrapper — the drift check must NOT run after it, or a
    closed gate would be followed by output that looks like progress;
  * drift is a WARNING: the wrapper still exits 0, because a project's copy being
    stale is not a defect in this commit (and a CI runner sees no sibling checkouts
    at all).
"""
import os
import subprocess
import tempfile
import unittest

REAL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'merge-gate.sh'))


class MergeGateWrapper(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.root, 'scripts'))
        subprocess.run(['git', 'init', '-q', self.root], check=True)

    def write(self, rel, text, executable=True):
        path = os.path.join(self.root, rel)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        if executable:
            # 0o700, not 0o755: the only process that runs these stubs is this test.
            # CodeQL flagged the wider mask (py/overly-permissive-file, 7.8) and it was
            # right — a world-writable temp directory plus a world-readable stub is a
            # shape nobody needs in a fixture.
            os.chmod(path, 0o700)
        return path

    def stub(self, name, exit_code=0):
        self.write(f'scripts/{name}',
                   f'#!/bin/sh\necho "{name} ran: $*" >> "{self.root}/calls.log"\nexit {exit_code}\n')

    def calls(self):
        path = os.path.join(self.root, 'calls.log')
        if not os.path.exists(path):
            return ''
        with open(path, encoding='utf-8') as handle:
            return handle.read()

    def run_wrapper(self, *args):
        # The REAL script, not a copy into self.root. A copy passes every assertion
        # here and still leaves the original at 0% coverage, because a tracer
        # attributes execution to the file it actually ran — the same trap
        # scripts/coverage-shell.sh documents. The wrapper resolves its own root with
        # `git rev-parse --show-toplevel`, so running it with cwd inside the fixture
        # repository makes it pick up the stubs there while the file under test is the
        # one in this repository.
        result = subprocess.run(['bash', REAL, *args], cwd=self.root, capture_output=True, text=True)
        return result.stdout + result.stderr, result.returncode

    def test_the_target_reaches_the_core(self):
        self.stub('gate-core.sh')
        self.stub('twin-drift.sh')
        _, code = self.run_wrapper('prod')
        self.assertEqual(0, code)
        self.assertIn('gate-core.sh ran: prod', self.calls())

    def test_dev_is_the_default_target(self):
        self.stub('gate-core.sh')
        self.stub('twin-drift.sh')
        self.run_wrapper()
        self.assertIn('gate-core.sh ran: dev', self.calls())

    def test_a_failing_core_stops_the_wrapper_before_the_drift_check(self):
        self.stub('gate-core.sh', exit_code=1)
        self.stub('twin-drift.sh')
        _, code = self.run_wrapper('test')
        self.assertNotEqual(0, code, 'a closed gate must not exit 0')
        self.assertNotIn('twin-drift.sh ran', self.calls(),
                         'output after a closed gate reads as progress')

    def test_drift_is_reported_and_does_not_close_the_gate(self):
        self.stub('gate-core.sh')
        self.stub('twin-drift.sh', exit_code=1)
        out, code = self.run_wrapper('dev')
        self.assertEqual(0, code, 'a stale project copy is not a defect in this commit')
        self.assertIn('twin drift is reported, not fatal', out)

    def test_the_drift_check_runs_when_the_core_passes(self):
        self.stub('gate-core.sh')
        self.stub('twin-drift.sh')
        self.run_wrapper('dev')
        self.assertIn('twin-drift.sh ran', self.calls())


if __name__ == '__main__':
    unittest.main()
