"""The coverage scripts and the commit-msg hook — the last shell files with no tests.

`coverage.sh` and `coverage-shell.sh` decide whether the 80% threshold (#29) is
enforced at all, and until now neither had a single test. Their failure paths are
the interesting ones: a missing tool must end as NOT MEASURED and BLOCK, never as
a pass, because "#29 does not count an unmeasured codebase as passing" is only
true if the script actually behaves that way.
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
COVERAGE = os.path.join(SCRIPTS, 'coverage.sh')
SHELL_COVERAGE = os.path.join(SCRIPTS, 'coverage-shell.sh')
COMMIT_MSG = os.path.join(SCRIPTS, 'commit-msg.sh')


def executable(path, body):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path


class Repo(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        subprocess.run(['git', 'init', '-q', self.root], check=True)
        os.makedirs(os.path.join(self.root, 'scripts'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_in(self, script, *args, cwd=None, env=None, stdin=None):
        result = subprocess.run(['bash', script, *args], cwd=cwd or self.root,
                                capture_output=True, text=True,
                                env=dict(os.environ, **(env or {})), input=stdin)
        return result.stdout + result.stderr, result.returncode


class OutsideAGitRepository(Repo):
    def test_coverage_refuses_to_run_outside_a_repository(self):
        # The scripts locate everything from the repository root; without one
        # there is nothing to measure and guessing would measure the wrong tree.
        loose = tempfile.mkdtemp()
        try:
            out, code = self.run_in(COVERAGE, cwd=loose)
            self.assertIn('not inside a git repository', out)
            self.assertEqual(2, code)
        finally:
            shutil.rmtree(loose, ignore_errors=True)

    def test_shell_coverage_refuses_too(self):
        loose = tempfile.mkdtemp()
        try:
            out, code = self.run_in(SHELL_COVERAGE, cwd=loose)
            self.assertIn('not inside a git repository', out)
            self.assertEqual(2, code)
        finally:
            shutil.rmtree(loose, ignore_errors=True)


class MissingToolsBlockRatherThanPass(Repo):
    """#29: an unmeasured codebase does not count as passing. Exit 3, not 0."""

    def test_no_kcov_is_not_measured_and_blocks(self):
        empty_bin = tempfile.mkdtemp()      # a PATH with no kcov on it
        try:
            out, code = self.run_in(SHELL_COVERAGE, env={'PATH': f'{empty_bin}:/usr/bin:/bin'})
            self.assertIn('NOT MEASURED', out)
            self.assertIn('kcov', out)
            self.assertEqual(3, code, 'a missing tracer must block, not pass')
        finally:
            shutil.rmtree(empty_bin, ignore_errors=True)

    def test_no_traceable_bash_is_not_measured_and_blocks(self):
        # kcov is present but fails on every candidate bash — which is exactly
        # the macOS situation before a second bash was installed.
        fake = tempfile.mkdtemp()
        try:
            executable(os.path.join(fake, 'kcov'), '#!/bin/sh\nexit 1\n')
            out, code = self.run_in(SHELL_COVERAGE,
                                    env={'PATH': f'{fake}:/usr/bin:/bin', 'COVERAGE_BASH': '/nonexistent/bash'})
            self.assertIn('NOT MEASURED', out)
            self.assertEqual(3, code)
        finally:
            shutil.rmtree(fake, ignore_errors=True)

    def test_no_coverage_venv_is_not_measured_and_blocks(self):
        out, code = self.run_in(COVERAGE, env={'COVERAGE_VENV': os.path.join(self.root, 'absent')})
        self.assertIn('NOT MEASURED', out)
        self.assertIn('no coverage in', out)
        self.assertNotEqual(0, code, 'an unmeasured codebase must not exit 0')


class CoverageBashOverrideIsHonoured(Repo):
    def test_an_explicit_bash_is_probed_first(self):
        # COVERAGE_BASH exists but kcov cannot trace it -> the probe must reject
        # it and fall through, rather than trusting the variable.
        fake = tempfile.mkdtemp()
        try:
            executable(os.path.join(fake, 'kcov'), '#!/bin/sh\nexit 1\n')
            out, code = self.run_in(SHELL_COVERAGE,
                                    env={'PATH': f'{fake}:/usr/bin:/bin',
                                         'COVERAGE_BASH': '/bin/sh'})
            self.assertEqual(3, code)
            self.assertIn('cannot trace any bash', out)
        finally:
            shutil.rmtree(fake, ignore_errors=True)


class CommitMsgHook(Repo):
    """Three of the real names that reached this repository's history came in
    through commit MESSAGES, which is why this hook exists at all."""

    def message_file(self, text):
        path = os.path.join(self.root, 'msg.txt')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
        return path

    def test_it_is_silent_when_the_project_has_no_checker(self):
        # A project that never copied real-name-check.sh must still be able to
        # commit — the hook is not installed there, so it passes quietly.
        out, code = self.run_in(COMMIT_MSG, self.message_file('a message\n'))
        self.assertEqual(0, code)
        self.assertEqual('', out.strip())

    def test_it_delegates_to_the_checker_when_present(self):
        marker = os.path.join(self.root, 'called.txt')
        executable(os.path.join(self.root, 'scripts', 'real-name-check.sh'),
                   f'#!/bin/sh\necho "$@" > {marker}\nexit 7\n')
        out, code = self.run_in(COMMIT_MSG, self.message_file('a message\n'))
        self.assertEqual(7, code, 'the checker\'s exit code must be the hook\'s')
        with open(marker) as handle:
            asked = handle.read()
        self.assertIn('--message', asked)

    def test_outside_a_repository_it_passes_quietly(self):
        loose = tempfile.mkdtemp()
        try:
            path = os.path.join(loose, 'msg.txt')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write('m\n')
            out, code = self.run_in(COMMIT_MSG, path, cwd=loose)
            self.assertEqual(0, code)
        finally:
            shutil.rmtree(loose, ignore_errors=True)


class CoverageWithAFakeVenv(Repo):
    """coverage.sh's measurement path, which nothing reached before: every test
    stopped at "no coverage in <venv>". A fake venv gets past that, so the parts
    that decide PASS vs FAIL vs "the tests are red" are exercised.

    The distinction that matters: a RED suite must not be reported as a coverage
    figure at all. A percentage computed from a suite that failed measures
    nothing, and treating it as a measurement would let a broken test file raise
    the number.
    """

    def venv(self, coverage_body):
        venv = os.path.join(self.root, '.venv')
        os.makedirs(os.path.join(venv, 'bin'))
        executable(os.path.join(venv, 'bin', 'coverage'), coverage_body)
        # ⚠️ coverage.sh asks this python for sysconfig's purelib and WRITES a
        # .pth file there, so a stub that forwards straight to the real
        # interpreter makes it write into the developer's own site-packages. It
        # did exactly that once: a stray coverage-subprocess.pth landed in an
        # anaconda install and every later `python3` start printed
        # "ModuleNotFoundError: No module named 'coverage'". The stub therefore
        # answers the purelib question with a directory INSIDE the fixture, and
        # forwards everything else.
        purelib = os.path.join(venv, 'lib', 'site-packages')
        os.makedirs(purelib)
        executable(os.path.join(venv, 'bin', 'python'),
                   '#!/bin/sh\n'
                   'case "$*" in\n'
                   '  *sysconfig*) echo "' + purelib + '"; exit 0 ;;\n'
                   'esac\n'
                   'exec ' + sys.executable + ' "$@"\n')
        os.makedirs(os.path.join(self.root, 'scripts', 'tests'), exist_ok=True)
        return venv

    def run_coverage(self, coverage_body):
        venv = self.venv(coverage_body)
        # A stub shell-coverage helper: this test is about the Python half.
        executable(os.path.join(self.root, 'scripts', 'coverage-shell.sh'),
                   '#!/usr/bin/env bash\necho "  shell: stubbed"\nexit 0\n')
        return self.run_in(COVERAGE, env={'COVERAGE_VENV': venv})

    @staticmethod
    def stub(run_exit, report_line, report_exit):
        return (
            '#!/bin/sh\n'
            'case "$1" in\n'
            f'  run) {run_exit} ;;\n'
            '  combine) exit 0 ;;\n'
            f'  report) echo "{report_line}"; exit {report_exit} ;;\n'
            'esac\n'
            'exit 0\n')

    def test_a_passing_suite_at_the_threshold_passes(self):
        out, code = self.run_coverage(self.stub('exit 0', 'TOTAL 100 0 100%', 0))
        self.assertIn('at or above', out)
        self.assertEqual(0, code, out)

    def test_below_the_threshold_fails_and_points_at_the_plan(self):
        out, code = self.run_coverage(self.stub('exit 0', 'TOTAL 100 50 50%', 1))
        self.assertIn('below 80%', out)
        self.assertIn('coverage-gap.md', out)
        self.assertEqual(1, code)

    def test_a_RED_suite_is_not_reported_as_a_coverage_figure(self):
        out, code = self.run_coverage(
            self.stub('echo "FAILED (failures=1)"; exit 1', 'TOTAL 100 0 100%', 0))
        self.assertIn('the tests are red', out)
        self.assertNotIn('at or above', out)
        self.assertEqual(1, code, 'a red suite must not pass on a 100% report')


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

    def build(self, hits_second_line):
        """A repo with one shell script, one trivial test, and a stub kcov whose
        reports cover 1 or 2 of that script's 2 lines."""
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
                f'        subprocess.run(["bash", {target!r}], check=True)\n')
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


if __name__ == '__main__':
    unittest.main()
