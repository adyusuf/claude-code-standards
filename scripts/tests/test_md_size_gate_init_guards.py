"""`--init` of the CLAUDE.md size gate (scripts/md-size-gate.sh): the guards — it never overwrites,
honours MD_BUDGET, copes with no CLAUDE.md and with awkward paths. What it writes is in
test_md_size_gate_init.py."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md_size_gate_helpers import Init  # noqa: E402


class InitNeverOverwrites(Init):
    SENTINEL = '# hand-edited\nCLAUDE.md\t7\t5\twhy it was raised\n'

    def assert_untouched(self, path, extra_missing=()):
        self.write('CLAUDE.md', 'x')
        before = self.read_bytes(path)
        out, code = self.run_gate('--init', budget=self.budget_env)
        self.assertEqual(1, code, out)
        self.assertIn('never overwrites', out)
        self.assertIn(path, out)
        self.assertEqual(before, self.read_bytes(path))
        for missing in extra_missing:
            self.assertFalse(os.path.exists(missing), f'--init created {missing}')

    budget_env = None

    def test_an_existing_budget_under_scripts(self):
        path = self.write('scripts/md-budget.tsv', self.SENTINEL)
        self.assert_untouched(path)

    def test_an_existing_budget_at_the_root(self):
        path = self.write('md-budget.tsv', self.SENTINEL)
        self.assert_untouched(path, [os.path.join(self.root, 'scripts')])

    def test_an_existing_budget_under_docs(self):
        path = self.write('docs/md-budget.tsv', self.SENTINEL)
        self.assert_untouched(path, [os.path.join(self.root, 'scripts')])

    def test_an_existing_budget_named_by_md_budget(self):
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other, True)
        path = os.path.join(other, 'custom.tsv')
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(self.SENTINEL)
        self.budget_env = path
        self.assert_untouched(path, [os.path.join(self.root, 'scripts')])

    def test_md_budget_wins_over_a_budget_under_scripts_and_both_survive(self):
        under_scripts = self.write('scripts/md-budget.tsv', self.SENTINEL)
        explicit = self.write('elsewhere/b.tsv', self.SENTINEL + '# explicit\n')
        self.write('CLAUDE.md', 'x')
        scripts_before = self.read_bytes(under_scripts)
        explicit_before = self.read_bytes(explicit)
        out, code = self.run_gate('--init', budget=explicit)
        self.assertEqual(1, code, out)
        self.assertIn(explicit, out)
        self.assertEqual(scripts_before, self.read_bytes(under_scripts))
        self.assertEqual(explicit_before, self.read_bytes(explicit))

    def test_a_second_init_refuses_and_keeps_the_first_result(self):
        self.write('CLAUDE.md', 'x')
        self.run_gate('--init')
        first = self.read_bytes(self.budget_path())
        self.write('backend/CLAUDE.md', 'x')
        out, code = self.run_gate('--init')
        self.assertEqual(1, code, out)
        self.assertIn('never overwrites', out)
        self.assertEqual(first, self.read_bytes(self.budget_path()))

    def test_an_existing_empty_budget_is_still_an_existing_budget(self):
        path = self.write('scripts/md-budget.tsv', '')
        self.assert_untouched(path)


class InitHonoursMdBudget(Init):
    def test_a_nonexistent_md_budget_path_is_written_exactly_there(self):
        self.write('CLAUDE.md', 'x' * 1500)
        target = os.path.join(self.root, 'config', 'deep', 'sizes.tsv')
        out, code = self.run_gate('--init', budget=target)
        self.assertEqual(0, code, out)
        self.assertEqual([('CLAUDE.md', '2', '2')], [r[:3] for r in self.rows(target)])
        self.assertFalse(os.path.exists(self.budget_path()), 'also wrote the default location')
        self.assertIn(target, out)

    def test_a_path_outside_the_root_is_honoured(self):
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other, True)
        target = os.path.join(other, 'b.tsv')
        self.write('CLAUDE.md', 'x')
        out, code = self.run_gate('--init', budget=target)
        self.assertEqual(0, code, out)
        self.assertTrue(os.path.isfile(target))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'scripts')))
        gate_out, gate_code = self.run_gate(budget=target)
        self.assertEqual(0, gate_code, gate_out)

    def test_the_gate_run_with_the_same_md_budget_passes(self):
        self.write('CLAUDE.md', 'x')
        self.write('web/CLAUDE.md', 'x')
        target = os.path.join(self.root, 'sizes.tsv')
        self.run_gate('--init', budget=target)
        out, code = self.run_gate(budget=target)
        self.assertIn('within its budget', out)
        self.assertEqual(0, code, out)

    def test_an_unwritable_parent_fails_with_a_message(self):
        blocker = self.write('blocker', 'a file, not a directory')
        out, code = self.run_gate('--init', budget=os.path.join(blocker, 'b.tsv'))
        self.assertEqual(1, code, out)
        self.assertIn('Cannot create', out)

    def test_a_budget_path_that_is_a_directory_fails_with_a_message(self):
        os.makedirs(os.path.join(self.root, 'taken'))
        out, code = self.run_gate('--init', budget=os.path.join(self.root, 'taken'))
        self.assertEqual(1, code, out)
        self.assertIn('Cannot write', out)


class InitWithNoClaudeMd(Init):
    def test_the_budget_is_header_only_and_the_gate_passes(self):
        out, code = self.run_gate('--init')
        self.assertEqual(0, code, out)
        self.assertIn('0 CLAUDE.md file(s)', out)
        content = open(self.budget_path(), encoding='utf-8').read()
        self.assertTrue(content.strip())
        self.assertEqual([], self.rows())
        self.assertTrue(all(l.startswith('#') for l in content.split('\n') if l), content)
        gate_out, gate_code = self.run_gate()
        self.assertIn('within its budget', gate_out)
        self.assertEqual(0, gate_code, gate_out)

    def test_only_pruned_trees_count_as_no_claude_md(self):
        self.write('.claude/CLAUDE.md', 'x')
        self.write('node_modules/p/CLAUDE.md', 'x')
        out, code = self.run_gate('--init')
        self.assertEqual(0, code, out)
        self.assertEqual([], self.rows())


class InitUnderAwkwardPaths(Init):
    """ROOT with a space or glob characters: the rows must stay relative.

    Unquoted, `${file#$ROOT/}` treats ROOT as a glob; under `[1]` the prefix does
    not strip and the budget would be written with absolute paths — which then
    never match anything (the script's own warnings name this class of bug).
    """

    NAMES = {'a space': 'my repo x', 'a bracket': 'repo[1]-x', 'a star and a question mark': 'r*po?x',
             'a space and a bracket': 'my repo[2] x'}

    def use_root(self, name):
        parent = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, parent, True)
        self.root = os.path.join(parent, name)
        os.makedirs(self.root)

    def test_rows_are_relative_and_the_round_trip_passes(self):
        for label, name in self.NAMES.items():
            with self.subTest(label):
                self.use_root(name)
                self.write('CLAUDE.md', 'x')
                self.write('backend/CLAUDE.md', 'x' * 1500)
                self.write('web/node_modules/p/CLAUDE.md', 'x')
                out, code = self.run_gate('--init')
                self.assertEqual(0, code, out)
                self.assertEqual([('CLAUDE.md', '1'), ('backend/CLAUDE.md', '2')],
                                 [r[:2] for r in self.rows()])
                gate_out, gate_code = self.run_gate()
                self.assertIn('within its budget', gate_out)
                self.assertEqual(0, gate_code, gate_out)

    def test_a_file_added_later_is_still_found_under_the_same_paths(self):
        for label, name in self.NAMES.items():
            with self.subTest(label):
                self.use_root(name)
                self.write('CLAUDE.md', 'x')
                self.run_gate('--init')
                self.write('backend/CLAUDE.md', 'x')
                out, code = self.run_gate()
                self.assertIn('NO BUDGET', out)
                self.assertEqual(1, code)


if __name__ == '__main__':
    unittest.main()
