"""The CLAUDE.md size gate (scripts/md-size-gate.sh).

It had NO tests: the only file that touched it replaced it with a stub
(`exit 0`) because it was testing the hook around it, so the gate measured 0%
coverage while being the thing that decides whether a guidance file may grow.

Two behaviours here are regression pins for incidents recorded in the script's
own comments, and both are the kind that pass silently:
  · CR bytes are subtracted, so a CRLF checkout measures the same as an LF one.
    Before that, every budgeted file reported "ceiling exceeded" on Windows with
    no change made at all.
  · A CLAUDE.md with no budget line must be DISCOVERED and fail. The discovery
    loop once matched the root itself when run from a git worktree, found no
    files, and let a budget-less file through — with no symptom, because the
    budgeted files were still checked through the tsv.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GATE = os.path.join(SCRIPTS, 'md-size-gate.sh')


def kb_of(text):
    """What the gate will report for this content: CR excluded, rounded up."""
    raw = text.encode()
    return (len(raw) - raw.count(b'\r') + 1023) // 1024


class Gate(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, relative, text):
        path = os.path.join(self.root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
        return path

    def budget(self, *lines):
        return self.write('scripts/md-budget.tsv', ''.join(l + '\n' for l in lines))

    def run_gate(self, *args, budget=None):
        env = dict(os.environ, MD_ROOT=self.root)
        if budget:
            env['MD_BUDGET'] = budget
        result = subprocess.run(['bash', GATE, *args], capture_output=True, text=True, env=env)
        return result.stdout + result.stderr, result.returncode


class BudgetFileDiscovery(Gate):
    def test_a_missing_budget_fails_the_merge_gate(self):
        # Deleting the budget file must not delete the gate with it.
        out, code = self.run_gate()
        self.assertIn('No budget file', out)
        self.assertEqual(1, code)

    def test_a_missing_budget_is_not_an_error_in_hook_mode(self):
        # In a project that has not installed the gate, the hook stays quiet.
        out, code = self.run_gate('--hook')
        self.assertIn('No CLAUDE.md budget is installed', out)
        self.assertEqual(0, code)

    def test_the_budget_is_found_under_scripts(self):
        self.write('CLAUDE.md', 'x')
        self.budget('CLAUDE.md\t1\t1\treason')
        out, code = self.run_gate()
        self.assertIn('within its budget', out)
        self.assertEqual(0, code)

    def test_the_budget_is_found_at_the_root(self):
        self.write('CLAUDE.md', 'x')
        self.write('md-budget.tsv', 'CLAUDE.md\t1\t1\treason\n')
        out, code = self.run_gate()
        self.assertEqual(0, code, out)


class Verdicts(Gate):
    def setUp(self):
        super().setUp()
        self.write('CLAUDE.md', 'x' * 3000)      # 3 KB
        self.assertEqual(3, kb_of('x' * 3000))

    def test_at_or_below_the_target_is_on_target(self):
        self.budget('CLAUDE.md\t5\t3\treason')
        out, code = self.run_gate()
        self.assertIn('on target', out)
        self.assertEqual(0, code)

    def test_between_target_and_ceiling_passes_without_claiming_on_target(self):
        self.budget('CLAUDE.md\t5\t1\treason')
        out, code = self.run_gate()
        self.assertIn('under the ceiling', out)
        self.assertNotIn('on target', out)
        self.assertEqual(0, code)

    def test_above_the_ceiling_closes_the_gate_and_says_by_how_much(self):
        self.budget('CLAUDE.md\t1\t1\treason')
        out, code = self.run_gate()
        self.assertIn('CEILING EXCEEDED', out)
        self.assertIn('+2 KB', out)            # 3 KB against a ceiling of 1
        self.assertIn('GATE CLOSED', out)
        self.assertEqual(1, code)

    def test_a_budgeted_file_that_does_not_exist_fails(self):
        self.budget('CLAUDE.md\t5\t3\treason', 'backend/CLAUDE.md\t5\t3\treason')
        out, code = self.run_gate()
        self.assertIn('FILE MISSING', out)
        self.assertEqual(1, code)

    def test_comments_and_blank_lines_in_the_budget_are_skipped(self):
        self.budget('# a comment', '', 'CLAUDE.md\t5\t3\treason')
        out, code = self.run_gate()
        self.assertEqual(0, code, out)


class LineEndingsDoNotChangeTheMeasurement(Gate):
    """The Windows incident: with core.autocrlf=true every line is one byte
    longer, and budgeted files reported "ceiling exceeded" with no change made."""

    def test_crlf_and_lf_measure_the_same(self):
        body = ''.join(f'line {i}\n' for i in range(400))
        self.write('CLAUDE.md', body)
        self.budget('CLAUDE.md\t99\t99\treason')
        lf_out, lf_code = self.run_gate()
        lf_now = [l for l in lf_out.splitlines() if l.startswith('CLAUDE.md')][0].split()[1]

        self.write('CLAUDE.md', body.replace('\n', '\r\n'))
        crlf_out, crlf_code = self.run_gate()
        crlf_now = [l for l in crlf_out.splitlines() if l.startswith('CLAUDE.md')][0].split()[1]

        self.assertEqual(lf_now, crlf_now,
                         f'CRLF changed the measurement: {lf_now} vs {crlf_now}')
        self.assertEqual(lf_code, crlf_code)

    def test_a_crlf_file_at_its_ceiling_still_passes(self):
        body = ''.join(f'line {i}\r\n' for i in range(400))   # +400 CR bytes
        self.write('CLAUDE.md', body)
        self.budget(f'CLAUDE.md\t{kb_of(body)}\t{kb_of(body)}\treason')
        out, code = self.run_gate()
        self.assertEqual(0, code, out)


class UnbudgetedFilesAreDiscovered(Gate):
    def test_a_claude_md_with_no_budget_line_fails(self):
        self.write('CLAUDE.md', 'x')
        self.write('backend/CLAUDE.md', 'x')
        self.budget('CLAUDE.md\t1\t1\treason')
        out, code = self.run_gate()
        self.assertIn('NO BUDGET', out)
        self.assertIn('backend/CLAUDE.md', out)
        self.assertEqual(1, code)

    def test_dot_claude_and_node_modules_and_the_archive_are_pruned(self):
        self.write('CLAUDE.md', 'x')
        for hidden in ('.claude/CLAUDE.md',
                       'web/node_modules/pkg/CLAUDE.md',
                       'docs/claude-md-archive/CLAUDE.md'):
            self.write(hidden, 'x')
        self.budget('CLAUDE.md\t1\t1\treason')
        out, code = self.run_gate()
        self.assertNotIn('NO BUDGET', out)
        self.assertEqual(0, code, out)

    def test_an_exclusion_in_the_budget_file_is_honoured(self):
        self.write('CLAUDE.md', 'x')
        self.write('vendor/thing/CLAUDE.md', 'x')
        self.budget('# exclude:vendor', 'CLAUDE.md\t1\t1\treason')
        out, code = self.run_gate()
        self.assertNotIn('NO BUDGET', out)
        self.assertEqual(0, code, out)

    def test_an_empty_exclusion_excludes_nothing(self):
        # A typo must not switch discovery off wholesale.
        self.write('CLAUDE.md', 'x')
        self.write('vendor/thing/CLAUDE.md', 'x')
        self.budget('# exclude:', 'CLAUDE.md\t1\t1\treason')
        out, code = self.run_gate()
        self.assertIn('NO BUDGET', out)
        self.assertEqual(1, code)


class UpdateIsARatchet(Gate):
    def test_update_lowers_a_ceiling(self):
        self.write('CLAUDE.md', 'x' * 1000)                  # 1 KB
        path = self.budget('CLAUDE.md\t9\t1\treason')
        out, code = self.run_gate('--update')
        self.assertIn('ceiling 9 -> 1', out)
        self.assertEqual(0, code)
        self.assertIn('CLAUDE.md\t1\t1\treason', open(path).read())

    def test_update_never_raises_a_ceiling(self):
        self.write('CLAUDE.md', 'x' * 5000)                  # 5 KB, over the ceiling
        path = self.budget('CLAUDE.md\t2\t1\treason')
        out, code = self.run_gate('--update')
        self.assertEqual(0, code)
        kept = open(path).read()
        self.assertIn('CLAUDE.md\t2\t1\treason', kept)
        self.assertNotIn('\t5\t', kept)


if __name__ == '__main__':
    unittest.main()
