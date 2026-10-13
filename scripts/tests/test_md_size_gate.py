"""The CLAUDE.md size gate (scripts/md-size-gate.sh).

It had NO tests: the only file that touched it replaced it with a stub
(`exit 0`) because it was testing the hook around it, so the gate measured 0%
coverage while being the thing that decides whether a guidance file may grow.

Two behaviours here are regression pins for incidents recorded in the script's
own comments, and both are the kind that pass silently (the last section covers
`--init`, which writes a fresh budget for a project that has none):
  · CR bytes are subtracted, so a CRLF checkout measures the same as an LF one.
    Before that, every budgeted file reported "ceiling exceeded" on Windows with
    no change made at all.
  · A CLAUDE.md with no budget line must be DISCOVERED and fail. The discovery
    loop once matched the root itself when run from a git worktree, found no
    files, and let a budget-less file through — with no symptom, because the
    budgeted files were still checked through the tsv.
"""
import datetime
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


class AGlobInTheRepositoryPATH(Gate):
    """A repository path containing glob characters must not change the verdict.

    `rel="${file#$ROOT/}"` strips the repository prefix so the exclusion patterns
    can be matched RELATIVE to the root. Unquoted, $ROOT is a GLOB: under a path
    containing `[`, `*` or `?` — a worktree directory, a branch slug — the prefix
    does not strip, `rel` keeps the absolute path, the exclusions stop matching,
    and a budget-less CLAUDE.md passes. Found by ShellCheck (SC2295), pinned here
    because "the fix is obvious" is how the previous worktree blind spot in this
    same loop survived a full day.
    """

    def setUp(self):
        # A directory name with a bracket expression in it, which is exactly what
        # an unquoted pattern would treat as a character class.
        self.parent = tempfile.mkdtemp()
        self.root = os.path.join(self.parent, 'repo[1]-x')
        os.makedirs(self.root)

    def tearDown(self):
        shutil.rmtree(self.parent, ignore_errors=True)

    def test_an_unbudgeted_file_is_still_found_under_a_glob_path(self):
        self.write('CLAUDE.md', 'x')
        self.write('backend/CLAUDE.md', 'x')
        self.budget('CLAUDE.md\t1\t1\treason')
        out, code = self.run_gate()
        self.assertIn('NO BUDGET', out, f'discovery broke under a glob path:\n{out}')
        self.assertEqual(1, code)

    def test_an_exclusion_still_applies_under_a_glob_path(self):
        self.write('CLAUDE.md', 'x')
        self.write('vendor/thing/CLAUDE.md', 'x')
        self.budget('# exclude:vendor', 'CLAUDE.md\t1\t1\treason')
        out, code = self.run_gate()
        self.assertNotIn('NO BUDGET', out, f'the exclusion stopped matching:\n{out}')
        self.assertEqual(0, code, out)


def today_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y')


class Init(Gate):
    """`--init`: a project adopting the gate has no budget.

    Copying this repository's md-budget.tsv and running `--update` failed
    ("No budget file") or, with the file copied, left the project's own CLAUDE.md
    files "NO BUDGET" — `--update` only lowers rows that already exist. `--init`
    writes a fresh budget: one row per CLAUDE.md, ceiling = target = today's size.
    """

    def budget_path(self):
        return os.path.join(self.root, 'scripts', 'md-budget.tsv')

    def rows(self, path=None):
        """The data rows of the written budget, as (path, ceiling, target, note)."""
        with open(path or self.budget_path(), encoding='utf-8', newline='') as handle:
            lines = handle.read().split('\n')
        return [tuple(l.split('\t')) for l in lines if l and not l.startswith('#')]

    def read_bytes(self, path):
        with open(path, 'rb') as handle:
            return handle.read()


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
