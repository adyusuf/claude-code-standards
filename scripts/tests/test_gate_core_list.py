"""`gate-core.sh <target> --list` runs nothing, so it must never read as a verdict.

It used to end "GATE GREEN — dev promotion is allowed" and count "passed: N" after running nothing
(found 29/10/2026 while cleaning the projects). A listing is read before a promotion is asked for, so
a green line there is a pass nobody earned. What a listing CAN already tell — a check that would be
skipped or would fail — still ends INCOMPLETE / CLOSED with a non-zero exit, as the real run would
(test_gate_core_prod.py pins that); this file pins the clean listing.

Mutation-checked: with the LIST_ONLY branch removed from gate_result, every test here fails.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FILES = ('gate-core.sh', 'gate-lib.sh', 'gate-lib-node.sh', 'gate-lib-prod.sh', 'md-size-gate.sh', 'md-rule-gate.py')
ANSI = re.compile(r'\x1b\[[0-9;]*m')
# Every step resolves to a command, so the listing has nothing to skip.
CONF = 'COVERAGE_CMD="true"\nSAST_CMD="true"\nBACKCOMPAT_CMD="true"\n'


class AListingIsNotAVerdict(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.project, ignore_errors=True)
        os.makedirs(os.path.join(self.project, 'scripts'))
        subprocess.run(['git', 'init', '-q', self.project], check=True)
        for name in FILES:
            shutil.copy(os.path.join(SCRIPTS, name), os.path.join(self.project, 'scripts'))

    def listing(self, conf=CONF, target='dev'):
        with open(os.path.join(self.project, 'scripts', 'merge-gate.conf'), 'w', encoding='utf-8') as handle:
            handle.write(conf)
        done = subprocess.run(['bash', 'scripts/gate-core.sh', target, '--list'], cwd=self.project,
                              capture_output=True, text=True)
        return ANSI.sub('', done.stdout), done.returncode

    def test_a_clean_listing_says_it_is_a_listing(self):
        out, code = self.listing()
        self.assertEqual(0, code, out)
        self.assertIn('LISTING ONLY', out)
        self.assertIn('nothing ran, so there is no verdict', out)
        self.assertNotIn('GATE GREEN', out)
        self.assertNotIn('promotion is allowed', out)

    def test_the_count_is_what_would_run_not_what_passed(self):
        out, _ = self.listing()
        self.assertRegex(out, r'would run: [1-9]')
        self.assertNotIn('passed  :', out)

    def test_an_accepted_gap_does_not_turn_a_listing_green(self):
        out, code = self.listing(CONF.replace('BACKCOMPAT_CMD="true"\n', '')
                                 + 'ACCEPTED_GAPS="backward-compatibility scan"\nACCEPTED_GAPS_REASON="no API"\n')
        self.assertEqual(0, code, out)
        self.assertIn('ACCEPTED GAP', out)
        self.assertIn('LISTING ONLY', out)
        self.assertNotIn('GATE GREEN', out)

    def test_no_target_lists_a_verdict(self):
        for target in ('dev', 'test', 'prod'):
            out, _ = self.listing(target=target)
            self.assertNotIn('GATE GREEN', out, target)
            self.assertIn('LISTING ONLY', out, target)


if __name__ == '__main__':
    unittest.main()
