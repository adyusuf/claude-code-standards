"""coverage-shell.sh end to end (#29) — split from test_coverage_tooling.py so both
files stay under the 300-line limit (#9). The fixtures are shared from there."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_coverage_tooling import SHELL_COVERAGE, Repo, executable  # noqa: E402


class ShellCoverageRunsEndToEnd(Repo):
    """coverage-shell.sh's BODY, which nothing reached before.

    It measured 2 of 35 lines — every test stopped at one of its two probes, so
    the shim it writes, the run it drives, the merge and the report were all
    untested. The reason it is awkward is real: when it runs for real it is the
    OUTER process, not a script invoked through its own shim, so it cannot trace
    itself. That does not stop a TEST from driving it to completion with a stub
    `kcov` and a tiny suite, which is what this does.

    The stub kcov is the interesting part. The real one is asked two different
    questions: "can you trace this bash" (the probe) and "trace this script"
    (each run), and it answers both by writing a report directory. The stub does
    the same, so the script's own merge and threshold logic — the part that
    decides PASS or FAIL — runs against real files.
    """

    COBERTURA = (
        '<?xml version="1.0"?>\n'
        '<coverage><packages><package><classes>'
        '<class filename="{path}"><lines>'
        '<line number="1" hits="1"/><line number="2" hits="{second}"/>'
        '</lines></class>'
        '</classes></package></packages></coverage>\n')

    def build(self, hits_second_line, failure=None, targets_file=None):
        """A repo with one shell script, one trivial test, and a stub kcov whose
        reports cover 1 or 2 of that script's 2 lines. `failure` makes the trivial
        test fail with that message, standing in for a red suite; `targets_file`,
        when given, receives the script path each kcov run was handed."""
        # ⚠️ realpath, not the tempfile path. On macOS /var is a symlink to
        # /private/var, so `git rev-parse --show-toplevel` inside the script
        # reports the physical path while tempfile hands out the logical one —
        # the shim's `$root/scripts/*.sh` pattern then matches nothing and the
        # script correctly reports "the shim was never reached". Correct
        # behaviour, wrong fixture: a mismatch here looks exactly like a script
        # that does not work.
        root = os.path.realpath(self.root)
        self.bin = os.path.join(root, '.stubbin')
        os.makedirs(self.bin, exist_ok=True)
        os.makedirs(os.path.join(root, 'scripts', 'tests'), exist_ok=True)
        target = os.path.join(root, 'scripts', 'thing.sh')
        with open(target, 'w', encoding='utf-8') as handle:
            handle.write('#!/usr/bin/env bash\ntrue\ntrue\n')
        # ⚠️ NOT copied. The original is run with the temp repo as cwd — it
        # resolves its root with `git rev-parse --show-toplevel` and cd's there,
        # so behaviour is identical, and a tracer then attributes the run to the
        # real file. Copying it left scripts/coverage-shell.sh at 2/35 while
        # these very tests drove it end to end: the same mistake this script's
        # own header warns about, made in the test for it.
        # A test that invokes the script through `bash <path>`, which is what the
        # shim intercepts.
        with open(os.path.join(root, 'scripts', 'tests', 'test_x.py'), 'w', encoding='utf-8') as handle:
            handle.write(
                'import subprocess, unittest\n'
                'class T(unittest.TestCase):\n'
                '    def test_it(self):\n'
                f'        subprocess.run(["bash", {target!r}], check=True)\n'
                + (f'        self.fail({failure!r})\n' if failure else ''))
        report = self.COBERTURA.format(path=target, second=hits_second_line)
        report_file = os.path.join(root, 'report.xml')
        with open(report_file, 'w', encoding='utf-8') as handle:
            handle.write(report)
        # kcov <flags> <outdir> <target> [args...] — the stub finds the outdir as
        # the first argument that is not a flag, and writes a cobertura report
        # into it, then runs the target so the suite still passes.
        executable(os.path.join(self.bin, 'kcov'),
                   '#!/bin/sh\n'
                   'out=""\n'
                   'for a in "$@"; do\n'
                   '  case "$a" in --*) ;; *) if [ -z "$out" ]; then out="$a"; else target="$a"; fi ;; esac\n'
                   'done\n'
                   'mkdir -p "$out/run"\n'
                   # BOTH files: the probe looks for coverage.json to decide
                   # whether this bash is traceable, while the report is read
                   # from cobertura.xml. A stub that writes only one of them
                   # fails the probe and the script correctly reports NOT
                   # MEASURED — which is how this fixture was wrong at first.
                   'printf \'{"percent_covered":100}\' > "$out/run/coverage.json"\n'
                   f'cp {report_file} "$out/run/cobertura.xml"\n'
                   + (f'printf "%s %s\\n" "$target" "$(cd "$(dirname "$target")" && pwd -P)" >> {targets_file}\n' if targets_file else '') +
                   '[ -n "$target" ] && [ -f "$target" ] && sh "$target" >/dev/null 2>&1\n'
                   'exit 0\n')
        env = {'PATH': self.bin + os.pathsep + os.environ['PATH'],
               'COVERAGE_BASH': '/bin/sh'}
        result = subprocess.run(['bash', SHELL_COVERAGE],
                                cwd=root, capture_output=True, text=True,
                                env=dict(os.environ, **env))
        return result.stdout + result.stderr, result.returncode

    def test_full_coverage_passes_the_threshold(self):
        out, code = self.build(hits_second_line=1)
        self.assertIn('thing.sh', out)
        self.assertIn('100.0%', out)
        self.assertIn('at or above', out)
        self.assertEqual(0, code, out)

    def test_half_coverage_fails_the_threshold(self):
        # 1 of 2 lines = 50%, under 80: the gate must close on it.
        out, code = self.build(hits_second_line=0)
        self.assertIn('50.0%', out)
        self.assertIn('below 80%', out)
        self.assertEqual(1, code)

    def test_the_traced_run_count_is_reported(self):
        # It is the evidence that the shim was actually reached. A report with no
        # runs behind it would be a number with nothing under it.
        out, _ = self.build(hits_second_line=1)
        self.assertRegex(out, r'\(\d+ traced runs\)')

    def test_the_kcov_path_symptom_is_an_environment_failure(self):
        # The symptom of a too-long checkout path. It must not read as a product
        # failure (exit 1): exit 2 is "environment", and the message names the
        # measured limit and the way out.
        out, code = self.build(hits_second_line=1,
                               failure='kcov: error: /x/bin/bash is not an integer')
        self.assertEqual(2, code, out)
        self.assertIn('ENVIRONMENT', out)
        self.assertIn('70 or fewer', out)
        self.assertNotIn('the tests are red', out)

    def test_an_ordinary_red_suite_is_still_a_failure(self):
        # The environment branch must not swallow a real red suite.
        out, code = self.build(hits_second_line=1, failure='expected 1, got 2')
        self.assertEqual(1, code, out)
        self.assertIn('the tests are red', out)
        self.assertNotIn('ENVIRONMENT', out)

    def test_kcov_is_handed_a_short_path_however_deep_the_checkout_is(self):
        # kcov loses the trace lines whose file field is long, and it prefixed every
        # line with the checkout path: from 80 characters up a whole suite measured
        # 0%, and a test capturing a child's output printed "kcov: error: ... is not
        # an integer" (30/09/2026). The scripts are therefore started through a short
        # link, and this is what pins it: the path kcov is given must not contain
        # the deep checkout at all — and the run must still measure and pass.
        parent = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        self.root = os.path.join(parent, 'd' * 120, 'checkout')
        os.makedirs(os.path.join(self.root, 'scripts'))
        subprocess.run(['git', 'init', '-q', self.root], check=True)
        targets = os.path.join(parent, 'targets.txt')
        out, code = self.build(hits_second_line=1, targets_file=targets)
        self.assertEqual(0, code, out)
        with open(targets, encoding='utf-8') as handle:
            handed = [line.split(' ') for line in handle.read().splitlines() if '/thing.sh ' in line]
        self.assertTrue(handed, 'kcov was never handed the script: ' + out)
        for path, resolved in handed:
            self.assertNotIn('d' * 120, path)
            self.assertLess(len(path), 60, path)
            # and it is still the checkout's own script, not a copy (a copy measures 0%)
            self.assertEqual(os.path.join(os.path.realpath(self.root), 'scripts'), resolved)

    def test_the_short_link_is_removed_and_the_checkout_survives(self):
        before = set(os.listdir('/tmp'))
        out, code = self.build(hits_second_line=1)
        self.assertEqual(0, code, out)
        self.assertEqual([], sorted(n for n in set(os.listdir('/tmp')) - before if n.startswith('kc.')))
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'scripts', 'thing.sh')))


if __name__ == '__main__':
    unittest.main()
