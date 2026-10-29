"""`gate-core.sh <target> --coverage-only`: what still runs when the configuration turns the gate off.

User decision 29/10/2026: with `gates_before_push.<t>` = no the gate is not run, but rule #29 is never
waived, so the coverage step runs on its own and blocks below the threshold. What matters:

  · it runs the coverage step and NOTHING else (the rest was turned off on purpose);
  · it blocks like the full gate: a red measurement is CLOSED, a missing one INCOMPLETE, never green;
  · its green line never reads as the gate's green, since the rest did not run;
  · the full gate still runs coverage (the step moved into a shared function, gate_coverage).

Mutation-checked: making --coverage-only fall through to the full gate, or end with the gate's
"GATE GREEN", turns these tests red.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FILES = ('gate-core.sh', 'gate-lib.sh', 'gate-lib-node.sh', 'gate-lib-prod.sh')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


class CoverageOnly(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.project, ignore_errors=True)
        os.makedirs(os.path.join(self.project, 'scripts'))
        subprocess.run(['git', 'init', '-q', '-b', 'feature/x', self.project], check=True)
        for name in FILES:
            shutil.copy(os.path.join(SCRIPTS, name), os.path.join(self.project, 'scripts'))
        self.marker = os.path.join(self.project, 'coverage-ran')

    def gate(self, conf, *args, target='dev'):
        with open(os.path.join(self.project, 'scripts', 'merge-gate.conf'), 'w', encoding='utf-8') as handle:
            handle.write(conf)
        done = subprocess.run(['bash', 'scripts/gate-core.sh', target, *args], cwd=self.project,
                              capture_output=True, text=True)
        return ANSI.sub('', done.stdout + done.stderr), done.returncode

    def measured(self, code=0):
        return f'COVERAGE_CMD="touch {self.marker}; exit {code}"\n'

    def test_a_passing_measurement_is_green_and_says_the_rest_did_not_run(self):
        out, code = self.gate(self.measured(0), '--coverage-only')
        self.assertEqual(0, code, out)
        self.assertTrue(os.path.exists(self.marker), 'the coverage command did not run')
        self.assertIn('COVERAGE GREEN', out)
        self.assertIn('did NOT run', out)
        self.assertNotIn('GATE GREEN', out)

    def test_a_passing_measurement_prints_the_figures_it_measured(self):
        out, code = self.gate('COVERAGE_CMD="echo web 86.61% lines; echo backend 85.41% lines"\n', '--coverage-only')
        self.assertEqual(0, code, out)
        self.assertIn('web 86.61% lines', out)
        self.assertIn('backend 85.41% lines', out)

    def test_the_full_gate_prints_them_too(self):
        out, _ = self.gate('COVERAGE_CMD="echo web 86.61% lines"\n')
        self.assertIn('web 86.61% lines', out)

    def test_it_runs_no_other_step(self):
        out, _ = self.gate(self.measured(0) + 'SECRET_CMD="echo SECRET_RAN"\nSAST_CMD="echo SAST_RAN"\n',
                           '--coverage-only')
        for other in ('secret scan', 'SAST', 'formatter', 'unit tests', 'CLAUDE.md gates', 'SECRET_RAN', 'SAST_RAN'):
            self.assertNotIn(other, out)

    def test_coverage_below_the_threshold_closes_the_gate(self):
        out, code = self.gate(self.measured(1), '--coverage-only')
        self.assertEqual(1, code, out)
        self.assertIn('GATE CLOSED', out)
        self.assertNotIn('COVERAGE GREEN', out)

    def test_a_missing_measurement_is_incomplete_never_green(self):
        out, code = self.gate('', '--coverage-only')
        self.assertEqual(1, code, out)
        self.assertIn('GATE INCOMPLETE', out)
        self.assertIn('the threshold is NOT measured', out)

    def test_coverage_can_not_be_accepted_away_here_either(self):
        out, code = self.gate('ACCEPTED_GAPS="coverage"\nACCEPTED_GAPS_REASON="later"\n', '--coverage-only')
        self.assertNotEqual(0, code, out)
        self.assertNotIn('COVERAGE GREEN', out)

    def test_every_target_takes_it(self):
        for target in ('dev', 'test', 'prod'):
            out, code = self.gate(self.measured(0), '--coverage-only', target=target)
            self.assertEqual(0, code, f'{target}: {out}')
            self.assertIn(f'rest of the {target} gate did NOT run', out)

    def test_an_unknown_option_is_refused(self):
        out, code = self.gate(self.measured(0), '--coverage')
        self.assertEqual(2, code, out)
        self.assertIn('--coverage-only', out)
        self.assertFalse(os.path.exists(self.marker))

    def test_the_full_gate_still_lists_coverage(self):
        out, _ = self.gate(self.measured(0), '--list')
        self.assertIn('coverage (>= 80% lines, per codebase)', out)
        self.assertFalse(os.path.exists(self.marker), 'a listing ran the coverage command')


if __name__ == '__main__':
    unittest.main()
