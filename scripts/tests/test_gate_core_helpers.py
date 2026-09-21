"""The gate core's result helpers, and the invariant that makes its `&&`/`||`
lines safe.

ShellCheck flags eight lines in gate-core.sh with SC2015 — `A && B || C` is not
if-then-else, because C also runs when B fails. For example:

    grep -q '"build"' pkg.json && run "build" npm run build || skip "no build script"

Today that is correct, but ONLY because `run` always exits 0 (its last statement
is an `rm -f`), so the `|| skip` can never fire after the step actually ran. That
is load-bearing and invisible: add one failing statement to the end of `run` and
a FAILED build starts being reported as "skipped: no build script" — a failure
turned into a gap, which is the exact failure mode this gate exists to prevent
and the one that cost a whole day's measurements.

Rewriting the eight lines into if/else would also fix it, and may be the better
end state. Pinning the invariant is the smaller step (#1) and it fails loudly the
moment someone breaks it, which the rewrite alone would not do for the next
helper somebody adds.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GATE = os.path.join(SCRIPTS, 'gate-core.sh')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


class HelpersAlwaysSucceed(unittest.TestCase):
    """Each helper must exit 0 so that a following `|| fallback` never fires."""

    HELPERS = ('ok', 'bad', 'na', 'warn', 'skip')

    def call(self, snippet):
        """Source gate-core.sh's helper definitions and run `snippet`.

        The file is sourced with no arguments, which makes it print its usage and
        `exit 2` — so it is sourced inside a subshell whose exit is swallowed, and
        the helpers are then redefined from the same text. Simpler and honest: run
        a shell that extracts the helper block and evaluates it.
        """
        script = f'''
        set -uo pipefail
        PASS=(); FAIL=(); SKIP=(); WARN=(); NA=(); ACCEPTED=()
        # The helper definitions, taken from the gate itself rather than copied.
        eval "$(sed -n '/^say()/,/^have()/p' "{GATE}")"
        {snippet}
        '''
        result = subprocess.run(['bash', '-c', script], capture_output=True, text=True)
        return ANSI.sub('', result.stdout + result.stderr), result.returncode

    def test_each_helper_exits_zero(self):
        for helper in self.HELPERS:
            out, code = self.call(f'{helper} "a label"; echo "exit=$?"')
            self.assertIn('exit=0', out, f'{helper} did not exit 0:\n{out}')

    def test_a_following_fallback_does_not_fire_after_a_helper(self):
        # The shape SC2015 warns about, with the invariant holding.
        out, _ = self.call('true && bad "the step failed" || echo "FALLBACK RAN"')
        self.assertNotIn('FALLBACK RAN', out,
                         'a failure was about to be re-reported as a skip')

    def test_bad_records_a_failure_rather_than_exiting(self):
        # `bad` must not exit: the gate reports EVERY failing step, then decides.
        out, code = self.call('bad "one"; bad "two"; echo "count=${#FAIL[@]}"')
        self.assertIn('count=2', out)
        self.assertEqual(0, code)


class TheRunHelper(unittest.TestCase):
    """`run` is the one with a command in it, so it gets its own cases."""

    def run_gate_with(self, command, target='dev', with_dotnet=True):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        subprocess.run(['git', 'init', '-q', root], check=True)
        os.makedirs(os.path.join(root, 'scripts'))
        with open(os.path.join(root, 'SETUP.md'), 'w', encoding='utf-8') as handle:
            handle.write('# Setup\n## Secret and token inventory\n')
        open(os.path.join(root, '.env.example'), 'w').close()
        with open(os.path.join(root, 'scripts', 'merge-gate.conf'), 'w', encoding='utf-8') as handle:
            handle.write(f'COVERAGE_CMD="{command}"\n')
        if with_dotnet:
            # An empty .sln makes the real dotnet steps run and fail, which is
            # what the failing cases want as a backdrop. The passing case must
            # not have it, or the gate closes on dotnet rather than on coverage.
            open(os.path.join(root, 'App.sln'), 'w').close()
        result = subprocess.run(['bash', GATE, target], cwd=root, capture_output=True, text=True)
        return ANSI.sub('', result.stdout), result.returncode

    def test_a_failing_command_is_reported_as_FAILED_not_skipped(self):
        # The whole point: a step that ran and failed must never be recorded as a
        # step that did not run. They lead to different verdicts (CLOSED vs
        # INCOMPLETE) and to different decisions by whoever reads the gate.
        out, code = self.run_gate_with('false')
        self.assertIn('✗ coverage', out)
        self.assertNotIn('SKIPPED: coverage', out)
        self.assertIn('GATE CLOSED', out)
        self.assertEqual(1, code)

    def test_a_failing_command_prints_its_output(self):
        out, _ = self.run_gate_with('echo DIAGNOSTIC_LINE; exit 1')
        self.assertIn('DIAGNOSTIC_LINE', out,
                      'a failure with no output is a failure nobody can act on')

    def test_a_passing_command_is_reported_as_passed(self):
        # The assertion is about the STEP, not the gate's verdict: this throwaway
        # project configures no SAST and has no e2e suite, so the run ends
        # INCOMPLETE on those skips. That is correct behaviour and not what this
        # case is measuring — an earlier version asserted exit 0 here and was
        # wrong about the fixture, not about the helper.
        out, _ = self.run_gate_with('true', with_dotnet=False)
        self.assertIn('✓ coverage', out)
        self.assertNotIn('✗ coverage', out)
        self.assertNotIn('SKIPPED: coverage', out)


if __name__ == '__main__':
    unittest.main()
