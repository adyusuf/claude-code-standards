"""`gate-core.sh <target> --coverage-only`: what still runs when the configuration turns the gate off.

User decision 29/10/2026: with `gates_before_push.<t>` = no the gate is not run, but the coverage step runs on
its own and blocks below the threshold - unless `coverage_before_push.<t>` is no (30/10/2026, CoverageSetting). What matters:

  · it runs the coverage step and NOTHING else (the rest was turned off on purpose);
  · it blocks like the full gate: a red measurement is CLOSED, a missing one INCOMPLETE, never green;
  · its green line never reads as the gate's green, since the rest did not run;
  · the full gate still runs coverage (the step moved into a shared function, gate_coverage).

Mutation-checked: making --coverage-only fall through to the full gate, or end with the gate's
"GATE GREEN", turns these tests red.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FILES = ('gate-core.sh', 'gate-lib.sh', 'gate-lib-node.sh', 'gate-lib-prod.sh')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


class GateProject(unittest.TestCase):
    """A throwaway repository holding the four gate twins."""

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


class CoverageOnly(GateProject):
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


class CoverageSetting(GateProject):
    """The panel's "Run coverage before pushing" (coverage_before_push.<t>, user decision 30/10/2026), read by the gate
    from the project's .claude/sdlc-settings.json. Only an explicit false waives the step; everything else measures.

    Mutation-checked: reading the wrong target, treating a missing key as off, or counting a waived step as passed
    turns these tests red."""

    def settings(self, text):
        os.makedirs(os.path.join(self.project, '.claude'), exist_ok=True)
        with open(os.path.join(self.project, '.claude', 'sdlc-settings.json'), 'w', encoding='utf-8') as handle:
            handle.write(text)

    def coverage(self, **targets):
        self.settings('{"version": 1, "settings": {"coverage_before_push": %s}}' % json.dumps(targets))

    def test_off_for_the_target_waives_it_and_nothing_is_measured(self):
        self.coverage(dev=False, test=True, prod=True)
        out, code = self.gate(self.measured(1), '--coverage-only', target='dev')
        self.assertEqual(0, code, out)
        self.assertFalse(os.path.exists(self.marker), 'a waived coverage step still ran')
        self.assertIn('COVERAGE WAIVED', out)
        self.assertIn('coverage_before_push.dev = no', out)
        self.assertNotIn('COVERAGE GREEN', out)
        self.assertIn('passed  : 0', out)

    def test_on_for_the_target_measures_and_blocks_below_the_threshold(self):
        self.coverage(dev=False, test=True, prod=True)
        for target in ('test', 'prod'):
            out, code = self.gate(self.measured(1), '--coverage-only', target=target)
            self.assertEqual(1, code, f'{target}: {out}')
            self.assertTrue(os.path.exists(self.marker), target)
            self.assertIn('GATE CLOSED', out)
            os.remove(self.marker)

    def test_the_full_gate_reports_the_waived_step_and_never_counts_it_as_passed(self):
        self.coverage(dev=False)
        out, _ = self.gate(self.measured(0), target='dev')
        self.assertFalse(os.path.exists(self.marker))
        self.assertIn('waived  : 1', out)
        self.assertIn('WAIVED coverage (configuration; the merge commit must carry Gate-Waived: coverage)', out)
        self.assertNotIn('✓ coverage', out)

    def test_a_missing_file_key_or_target_measures(self):
        for text in (None, '{"version": 1, "settings": {}}', '{"version": 1, "settings": {"coverage_before_push": {"test": false}}}'):
            if text is not None:
                self.settings(text)
            out, code = self.gate(self.measured(0), '--coverage-only', target='dev')
            self.assertEqual(0, code, out)
            self.assertTrue(os.path.exists(self.marker), f'not measured with {text!r}')
            self.assertIn('COVERAGE GREEN', out)
            os.remove(self.marker)

    def test_a_file_that_does_not_parse_measures_and_says_so(self):
        self.settings('{ broken')
        out, code = self.gate(self.measured(0), '--coverage-only', target='dev')
        self.assertEqual(0, code, out)
        self.assertTrue(os.path.exists(self.marker))
        self.assertIn('could not be read - coverage runs (fail closed)', out)

    def test_only_false_waives_it(self):
        for value in ('0', '"no"', 'null'):
            self.settings('{"settings": {"coverage_before_push": {"dev": %s}}}' % value)
            self.gate(self.measured(0), '--coverage-only', target='dev')
            self.assertTrue(os.path.exists(self.marker), f'{value} waived coverage')
            os.remove(self.marker)


if __name__ == '__main__':
    unittest.main()
