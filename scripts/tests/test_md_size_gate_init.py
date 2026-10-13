"""`--init` of the CLAUDE.md size gate (scripts/md-size-gate.sh): what it writes, which trees it
skips, and how the gate behaves on the budget it wrote. The guards (never overwrite, MD_BUDGET,
no CLAUDE.md, awkward paths) are in test_md_size_gate_init_guards.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md_size_gate_helpers import Init, kb_of, today_utc  # noqa: E402


class InitWritesAFreshBudget(Init):
    def setUp(self):
        super().setUp()
        # 1 KB exactly once the CRs are gone: raw 1026 bytes, 2 of them CR.
        self.crlf = ('a' * 511 + '\r\n') * 2
        self.assertEqual(1, kb_of(self.crlf))
        self.assertEqual(1026, len(self.crlf.encode()))
        self.big = 'x' * 2500                              # 3 KB
        # Created out of sorted order on purpose; 'Zeta' sorts before 'alpha' in C.
        self.write('web/app/CLAUDE.md', self.crlf)
        self.write('alpha/CLAUDE.md', 'y' * 1025)         # 2 KB: one byte over 1 KB
        self.write('Zeta/CLAUDE.md', self.big)
        self.write('CLAUDE.md', 'x')

    def test_it_creates_scripts_and_writes_the_budget_there(self):
        self.assertFalse(os.path.exists(os.path.join(self.root, 'scripts')))
        out, code = self.run_gate('--init')
        self.assertEqual(0, code, out)
        self.assertTrue(os.path.isfile(self.budget_path()), out)
        self.assertIn('Budget written', out)
        self.assertIn(self.budget_path(), out)

    def test_one_row_per_claude_md_with_ceiling_equal_to_target_equal_to_size(self):
        self.run_gate('--init')
        expected = {
            'CLAUDE.md': kb_of('x'),
            'Zeta/CLAUDE.md': kb_of(self.big),
            'alpha/CLAUDE.md': kb_of('y' * 1025),
            'web/app/CLAUDE.md': kb_of(self.crlf),
        }
        rows = self.rows()
        self.assertEqual(sorted(expected), sorted(r[0] for r in rows))
        for path, ceiling, target, note in rows:
            self.assertEqual(str(expected[path]), ceiling, path)
            self.assertEqual(str(expected[path]), target, path)

    def test_cr_bytes_are_not_counted_when_sizing_a_row(self):
        # 1026 raw bytes would round up to 2 KB if the CRs were counted.
        self.run_gate('--init')
        row = [r for r in self.rows() if r[0] == 'web/app/CLAUDE.md'][0]
        self.assertEqual(('1', '1'), (row[1], row[2]))

    def test_the_size_rounds_up_rather_than_down(self):
        self.run_gate('--init')
        row = [r for r in self.rows() if r[0] == 'alpha/CLAUDE.md'][0]
        self.assertEqual('2', row[1])

    def test_rows_are_sorted_bytewise(self):
        self.run_gate('--init')
        paths = [r[0] for r in self.rows()]
        self.assertEqual(['CLAUDE.md', 'Zeta/CLAUDE.md', 'alpha/CLAUDE.md', 'web/app/CLAUDE.md'],
                         paths)

    def test_the_note_carries_todays_utc_date_in_dd_mm_yyyy(self):
        before = today_utc()
        self.run_gate('--init')
        after = today_utc()                     # tolerate running across midnight UTC
        notes = [r[3] for r in self.rows()]
        self.assertEqual(4, len(notes))
        for note in notes:
            self.assertTrue(note.endswith(before) or note.endswith(after), note)
            self.assertRegex(note, r'\d{2}/\d{2}/\d{4}$')

    def test_every_row_has_exactly_four_tab_separated_columns(self):
        self.run_gate('--init')
        for row in self.rows():
            self.assertEqual(4, len(row), row)

    def test_the_header_is_comments_only_and_comes_first(self):
        before = today_utc()
        self.run_gate('--init')
        after = today_utc()
        lines = open(self.budget_path(), encoding='utf-8').read().split('\n')
        header = []
        for line in lines:
            if line and not line.startswith('#'):
                break
            header.append(line)
        self.assertGreaterEqual(len(header), 3)
        self.assertTrue(all(l.startswith('#') for l in header), header)
        self.assertTrue(any(before in l or after in l for l in header), header)
        self.assertTrue(any('Columns' in l for l in header), header)
        # nothing but a trailing newline after the last row
        self.assertEqual('', lines[-1])

    def test_it_lists_each_file_it_added_on_stdout(self):
        out, _ = self.run_gate('--init')
        self.assertIn('+ web/app/CLAUDE.md  1 KB', out)
        self.assertIn('4 CLAUDE.md file(s)', out)


class InitSkipsTheTreesTheGateSkips(Init):
    def test_dot_claude_node_modules_and_the_archive_are_not_written(self):
        self.write('CLAUDE.md', 'x')
        self.write('web/CLAUDE.md', 'x')
        for hidden in ('.claude/CLAUDE.md',
                       '.claude/worktrees/w/CLAUDE.md',
                       'node_modules/CLAUDE.md',
                       'web/node_modules/pkg/CLAUDE.md',
                       'docs/claude-md-archive/CLAUDE.md'):
            self.write(hidden, 'x')
        out, code = self.run_gate('--init')
        self.assertEqual(0, code, out)
        self.assertEqual(['CLAUDE.md', 'web/CLAUDE.md'], [r[0] for r in self.rows()])
        self.assertNotIn('node_modules', open(self.budget_path()).read())
        self.assertNotIn('claude-md-archive', open(self.budget_path()).read())

    def test_a_docs_claude_md_outside_the_archive_is_written(self):
        # Only the archive subtree is pruned, not docs/ as a whole.
        self.write('docs/CLAUDE.md', 'x')
        self.run_gate('--init')
        self.assertEqual(['docs/CLAUDE.md'], [r[0] for r in self.rows()])


class InitThenTheGate(Init):
    def test_the_gate_passes_right_after_init(self):
        self.write('CLAUDE.md', 'x' * 3000)
        self.write('backend/CLAUDE.md', 'x')
        self.write('web/CLAUDE.md', ('a' * 511 + '\r\n') * 2)     # CRLF at the 1 KB edge
        self.write('.claude/CLAUDE.md', 'x' * 9000)
        _, init_code = self.run_gate('--init')
        self.assertEqual(0, init_code)
        out, code = self.run_gate()
        self.assertIn('within its budget', out)
        self.assertNotIn('NO BUDGET', out)
        self.assertNotIn('CEILING EXCEEDED', out)
        self.assertEqual(0, code, out)

    def test_every_row_reads_on_target_right_after_init(self):
        self.write('CLAUDE.md', 'x' * 3000)
        self.write('backend/CLAUDE.md', 'x')
        self.run_gate('--init')
        out, _ = self.run_gate()
        self.assertEqual(2, out.count('on target'), out)

    def test_growing_a_file_after_init_closes_the_gate(self):
        # The ceiling written by --init is a real ceiling, not a placeholder.
        self.write('CLAUDE.md', 'x' * 1000)                 # 1 KB
        self.run_gate('--init')
        self.write('CLAUDE.md', 'x' * 2000)                 # 2 KB
        out, code = self.run_gate()
        self.assertIn('CEILING EXCEEDED (+1 KB)', out)
        self.assertEqual(1, code)

    def test_a_claude_md_added_after_init_is_reported_no_budget(self):
        self.write('CLAUDE.md', 'x')
        self.run_gate('--init')
        self.write('backend/CLAUDE.md', 'x')
        out, code = self.run_gate()
        self.assertIn('NO BUDGET', out)
        self.assertIn('backend/CLAUDE.md', out)
        self.assertEqual(1, code)

    def test_a_claude_md_removed_after_init_is_reported_missing(self):
        self.write('CLAUDE.md', 'x')
        gone = self.write('backend/CLAUDE.md', 'x')
        self.run_gate('--init')
        os.remove(gone)
        out, code = self.run_gate()
        self.assertIn('FILE MISSING', out)
        self.assertEqual(1, code)

    def test_update_after_init_keeps_the_rows(self):
        self.write('CLAUDE.md', 'x' * 3000)
        self.run_gate('--init')
        out, code = self.run_gate('--update')
        self.assertEqual(0, code, out)
        self.assertEqual([('CLAUDE.md', '3', '3')], [r[:3] for r in self.rows()])
