"""The JS unit-test step must not hand vitest's flag to jest.

`--run` is a vitest flag. Handing it to a jest project fails with "Unrecognized
option run", so the gate reported a PASSING suite as failing — measured on
21/09/2026 against a mobile suite of 10 tests, which passes on its own.

Each case installs a stub runner at web/node_modules/.bin/<name>, which is where
`npm run` looks first, so `"test": "jest"` really resolves to the stub.
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ANSI = re.compile(r'\x1b\[[0-9;]*m')

# Fails when it IS given --run, the way jest does.
JEST_STUB = '#!/bin/sh\nfor a in "$@"; do [ "$a" = "--run" ] && { echo "Unrecognized option run" >&2; exit 1; }; done\necho ran\n'
# Fails when it is NOT given --run, the way a watching vitest would never return.
VITEST_STUB = '#!/bin/sh\nfor a in "$@"; do [ "$a" = "--run" ] && { echo ran; exit 0; }; done\necho "would watch forever" >&2\nexit 1\n'


def project(runner, stub):
    root = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q', root], check=True)
    os.makedirs(os.path.join(root, 'scripts'))
    shutil.copy(os.path.join(SCRIPTS, 'gate-core.sh'), os.path.join(root, 'scripts', 'gate-core.sh'))
    binary = os.path.join(root, 'web', 'node_modules', '.bin')
    os.makedirs(binary)
    path = os.path.join(binary, runner)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(stub)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    with open(os.path.join(root, 'web', 'package.json'), 'w', encoding='utf-8') as handle:
        handle.write('{"name":"w","scripts":{"test":"%s"}}' % runner)
    return root


def unit_test_step(root):
    """Only the lines of the 'unit tests' step."""
    result = subprocess.run(['bash', 'scripts/gate-core.sh', 'dev'],
                            cwd=root, capture_output=True, text=True)
    out = ANSI.sub('', result.stdout)
    match = re.search(r'▶ unit tests[^\n]*\n(.*?)\n▶ ', out, re.S)
    return match.group(1) if match else out


class JsTestStep(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(getattr(self, 'root', ''), ignore_errors=True)

    def test_a_jest_project_is_not_handed_the_vitest_flag(self):
        self.root = project('jest', JEST_STUB)
        step = unit_test_step(self.root)
        self.assertIn('test (web)', step)
        self.assertNotIn('✗ test (web)', step, f"jest was handed --run:\n{step}")

    def test_a_vitest_project_still_gets_the_flag(self):
        self.root = project('vitest', VITEST_STUB)
        step = unit_test_step(self.root)
        self.assertNotIn('✗ test (web)', step, f"vitest did not get --run:\n{step}")


if __name__ == '__main__':
    unittest.main()


class CoverageCannotBeAccepted(unittest.TestCase):
    """Rule #29 grants no exceptions, so ACCEPTED_GAPS must not waive coverage."""

    def tearDown(self):
        shutil.rmtree(getattr(self, 'root', ''), ignore_errors=True)

    def build(self, accepted):
        root = tempfile.mkdtemp()
        subprocess.run(['git', 'init', '-q', root], check=True)
        os.makedirs(os.path.join(root, 'scripts'))
        shutil.copy(os.path.join(SCRIPTS, 'gate-core.sh'), os.path.join(root, 'scripts', 'gate-core.sh'))
        with open(os.path.join(root, 'scripts', 'merge-gate.conf'), 'w', encoding='utf-8') as handle:
            handle.write(f'ACCEPTED_GAPS="{accepted}"\nACCEPTED_GAPS_REASON="a written reason"\n')
        self.root = root
        result = subprocess.run(['bash', 'scripts/gate-core.sh', 'test'],
                                cwd=root, capture_output=True, text=True)
        return ANSI.sub('', result.stdout), result.returncode

    def test_coverage_is_not_accepted_even_when_listed(self):
        out, code = self.build('coverage|SAST')
        self.assertIn('CANNOT be accepted', out)
        self.assertNotIn('ACCEPTED GAP: coverage', out)
        self.assertNotEqual(0, code, 'an unmeasured coverage gate must not exit 0')

    def test_another_gap_is_still_acceptable(self):
        out, _ = self.build('coverage|SAST')
        self.assertIn('ACCEPTED GAP', out)  # SAST still accepted
