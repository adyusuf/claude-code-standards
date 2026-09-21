import importlib.util
import json
import os
import shutil
import tempfile
import time
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), os.path.join(SCRIPTS, name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger = load('measurement-ledger')
report = load('measurement-report')
STATS = ledger.load_stats()


def usage(ts, output=1000):
    return {'timestamp': ts, 'message': {'model': 'claude-sonnet-5', 'usage': {
        'input_tokens': 0, 'output_tokens': output, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}}}


class Timezone(unittest.TestCase):
    """The daily split is by LOCAL day, so the tests pin the zone (UTC+3, no daylight saving)."""

    def setUp(self):
        self.saved = os.environ.get('TZ')
        os.environ['TZ'] = 'Etc/GMT-3'
        time.tzset()

    def tearDown(self):
        if self.saved is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = self.saved
        time.tzset()


class ProjectKey(unittest.TestCase):
    def setUp(self):
        self.stats = STATS
        self.stats.TRANSCRIPTS = '/home/x/.claude/projects/**/*.jsonl'

    def key(self, folder):
        return ledger.project_key(f'/home/x/.claude/projects/{folder}/abc.jsonl', self.stats)

    def test_the_home_prefix_and_the_worktree_suffix_are_dropped(self):
        self.assertEqual(self.key('-Users-me-ClaudeCode-Alpha'), 'Alpha')
        self.assertEqual(self.key('-Users-me-ClaudeCode-Alpha--claude-worktrees-brave-fox-123abc'), 'Alpha')
        self.assertEqual(self.key('-Users-me-Beta'), 'Beta')

    def test_a_sub_project_stays_a_project_of_its_own(self):
        self.assertEqual(self.key('-Users-me-ClaudeCode-Alpha-api'), 'Alpha-api')

    def test_the_root_folder_of_the_workspace_keeps_its_name(self):
        self.assertEqual(self.key('-Users-me-ClaudeCode'), 'ClaudeCode')


class Nicknames(unittest.TestCase):
    PAIRS = [('Alpha', 'groot'), ('Alpha-api', 'rocket'), ('scratch*', 'picasso')]

    def test_an_exact_key_wins_over_a_prefix_and_matching_ignores_case(self):
        self.assertEqual(ledger.nickname_for('alpha', self.PAIRS), 'groot')
        self.assertEqual(ledger.nickname_for('Alpha-api', self.PAIRS), 'rocket')
        self.assertEqual(ledger.nickname_for('scratch-2026-09-20', self.PAIRS), 'picasso')

    def test_an_unmapped_project_gets_a_stable_opaque_label_never_its_name(self):
        first = ledger.nickname_for('SecretClient', self.PAIRS)
        self.assertEqual(first, ledger.nickname_for('SecretClient', self.PAIRS))
        self.assertTrue(first.startswith('unmapped-'))
        self.assertNotIn('secret', first.lower())

    def test_a_nickname_that_contains_a_real_project_name_is_refused(self):
        bad = ledger.nickname_problems([('Zorbexico', 'zorbexico-2'), ('Other', 'fine')], STATS)
        self.assertEqual([nick for nick, _ in bad], ['zorbexico-2'])

    def test_a_nickname_must_be_a_plain_lowercase_word_and_not_the_reserved_prefix(self):
        bad = ledger.nickname_problems([('A', 'Has Space'), ('B', '9lives'), ('C', 'unmapped-abc123'), ('D', 'ok-name')], STATS)
        self.assertEqual(sorted(nick for nick, _ in bad), ['9lives', 'Has Space', 'unmapped-abc123'])

    def test_the_file_is_read_with_comments_and_blank_lines_skipped(self):
        with tempfile.NamedTemporaryFile('w', suffix='.tsv', delete=False) as handle:
            handle.write('# comment\n\nAlpha\tgroot\nnot-a-pair\nBeta\t\n')
        try:
            self.assertEqual(ledger.load_nicknames(handle.name), [('Alpha', 'groot')])
        finally:
            os.unlink(handle.name)
        self.assertEqual(ledger.load_nicknames('/nonexistent/file.tsv'), [])


class RowProjectAndDays(Timezone):
    def setUp(self):
        super().setUp()
        self.root = tempfile.mkdtemp()
        self.stats = STATS
        self.stats.TRANSCRIPTS = os.path.join(self.root, 'projects', '**', '*.jsonl')
        folder = os.path.join(self.root, 'projects', '-Users-me-ClaudeCode-Alpha--claude-worktrees-x-1')
        os.makedirs(folder)
        self.path = os.path.join(folder, 'session.jsonl')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        super().tearDown()

    def write(self, records):
        with open(self.path, 'w', encoding='utf-8') as handle:
            for record in records:
                handle.write(json.dumps(record) + '\n')

    def test_the_row_carries_the_nickname_of_its_project_and_never_the_name(self):
        self.write([usage('2026-09-01T10:00:00Z')])
        row = ledger.row_for(self.path, 'session', None, self.stats, [], [('Alpha', 'groot')])
        self.assertEqual(row['project'], 'groot')
        self.assertNotIn('Alpha', '\t'.join(row.values()))
        self.assertEqual(ledger.problems([row]), [])

    def test_the_row_records_the_last_timestamp_of_the_transcript_as_its_end(self):
        self.write([usage('2026-09-01T20:30:00Z'), usage('2026-09-02T08:15:40Z'), {'timestamp': '2026-09-02T09:05:59Z'}])
        row = ledger.row_for(self.path, 'session', None, self.stats, [], [])
        self.assertEqual(row['started'], '2026-09-01T20:30')
        self.assertEqual(row['ended'], '2026-09-02T09:05')          # a record without usage still counts as activity
        self.assertEqual(ledger.problems([row]), [])


def ledger_row(**fields):
    row = {name: '' for name in ledger.NAMES}
    row.update(id='aaaaaaaaaa', started='2026-09-01T10:00', kind='session', role='main', model='m', requests='10',
               usd='10.0000', project='groot', ended='', steps='', step_seconds='')
    row.update(fields)
    return row


class Report(Timezone):
    def test_a_row_is_charged_whole_to_the_local_day_its_session_ended(self):
        # started on the 1st, ended 21:30Z = 00:30 on the 2nd in UTC+3: the whole $9 belongs to the 2nd.
        text = report.render([ledger_row(started='2026-09-01T08:00', ended='2026-09-01T21:30', usd='9.0000')])
        self.assertIn('| 02/09/2026 | $9.0 |', text)
        self.assertNotIn('01/09/2026', text)
        self.assertNotIn('≈', text)

    def test_a_row_with_no_recorded_end_falls_back_to_its_start_day_and_is_marked(self):
        text = report.render([ledger_row(started='2026-09-01T22:00', ended='', usd='4.0000')])       # 22:00Z = 01:00 on the 2nd
        self.assertIn('| 02/09/2026 | ≈$4.0 |', text)
        self.assertIn('1 of 1 rows have no recorded end time', text)

    def test_projects_are_grouped_and_sorted_by_cost_with_totals_that_add_up(self):
        rows = [ledger_row(id='aaaaaaaaaa', project='groot', usd='10.0000', ended='2026-09-01T10:00'),
                ledger_row(id='bbbbbbbbbb', project='ryan', usd='30.0000', ended='2026-09-01T11:00'),
                ledger_row(id='cccccccccc', project='ryan', kind='agent', role='qa', usd='5.0000', ended='2026-09-02T10:00')]
        text = report.render(rows)
        matrix = text[text.index('## Day × project'):text.index('## By day')]
        self.assertLess(matrix.index('ryan'), matrix.index('groot'))          # the dearer project comes first
        self.assertIn('| **project total** | **$35.0** | **$10.0** | **$45.0** |', matrix)
        self.assertIn('| 01/09/2026 | $30.0 | $10.0 | **$40.0** |', matrix)
        self.assertIn('| ryan | $35.0 | 78% | 2 | 1 | 1 | 14% |', text)          # 35/45, two active days, 5/35 from agents

    def test_a_project_without_a_nickname_is_flagged_with_how_to_fix_it(self):
        text = report.render([ledger_row(project='unmapped-1a2b3c')])
        self.assertIn('No nickname for: unmapped-1a2b3c', text)
        self.assertIn('project-nicknames.tsv', text)

    def test_the_report_states_the_units_and_that_it_is_a_generated_local_file(self):
        text = report.render([ledger_row()])
        self.assertIn('list-price USD', text)
        self.assertIn('git-ignored', text)

    def test_write_report_writes_beside_the_ledger_from_the_rows_it_holds(self):
        folder = tempfile.mkdtemp()
        try:
            path = os.path.join(folder, 'ledger.tsv')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(ledger.render([ledger_row(ended='2026-09-01T10:00')]))
            written = report.write_report(path)
            self.assertEqual(written, os.path.join(folder, 'measurement-daily-by-project.md'))
            with open(written, encoding='utf-8') as handle:
                self.assertIn('groot', handle.read())
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_the_report_of_a_real_looking_run_contains_no_real_project_name(self):
        root = tempfile.mkdtemp()
        try:
            stats = STATS
            stats.TRANSCRIPTS = os.path.join(root, 'projects', '**', '*.jsonl')
            folder = os.path.join(root, 'projects', '-Users-me-ClaudeCode-SecretClientPortal')
            os.makedirs(folder)
            path = os.path.join(folder, 's.jsonl')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(json.dumps(usage('2026-09-01T10:00:00Z')) + '\n')
            row = ledger.row_for(path, 'session', None, stats, [], [('SecretClientPortal', 'groot')])
            text = report.render([row])
            self.assertNotIn('SecretClientPortal', text)
            self.assertNotIn('secretclientportal', text.lower())
            self.assertIn('groot', text)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class OtherGroupings(Timezone):
    ROWS = [ledger_row(id='aaaaaaaaaa', kind='session', role='main', model='claude-opus-5', usd='10.0000', ended='2026-09-01T10:00'),
            ledger_row(id='bbbbbbbbbb', kind='agent', role='qa', model='claude-sonnet-5', usd='4.0000', ended='2026-09-01T11:00'),
            ledger_row(id='cccccccccc', kind='agent', role='qa', model='claude-sonnet-5', usd='6.0000', ended='2026-09-02T09:00')]

    def test_the_role_report_groups_by_role_and_gives_the_median_cost_per_run(self):
        text = report.render_by_role(self.ROWS)
        self.assertIn('# Measurement report — cost by day and role', text)
        self.assertIn('| qa | $10.0 | 50% | 2 | 2 | $5.0 | 20 | 0.0 |', text)
        self.assertIn('| 01/09/2026 | $10.0 | $4.0 | **$14.0** |', text)

    def test_the_kind_report_separates_conversations_from_delegated_runs(self):
        text = report.render_by_kind(self.ROWS)
        self.assertIn('cost by day and kind', text)
        self.assertIn('| session | $10.0 | 50% | 1 | 1 | $10.0 |', text)
        self.assertIn('| agent | $10.0 | 50% | 2 | 2 | $5.0 |', text)

    def test_the_model_report_groups_by_model_and_says_a_row_has_one_model(self):
        text = report.render_by_model(self.ROWS)
        self.assertIn('cost by day and model', text)
        self.assertIn('| claude-opus-5 | $10.0 | 50% | 1 | 1 |', text)
        self.assertIn('| claude-sonnet-5 | $10.0 | 50% | 2 | 2 |', text)
        self.assertIn('the first the run used', text)

    def test_every_grouping_totals_to_the_same_amount_and_uses_the_same_end_day_rule(self):
        for render in (report.render, report.render_by_role, report.render_by_kind, report.render_by_model):
            text = render(self.ROWS)
            self.assertIn('$20 over 2 day(s)', text)
            self.assertIn('**$20.0**', text)

    def test_write_reports_writes_four_files_beside_the_ledger(self):
        folder = tempfile.mkdtemp()
        try:
            path = os.path.join(folder, 'ledger.tsv')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(ledger.render(self.ROWS))
            written = report.write_reports(path)
            self.assertEqual(sorted(os.path.basename(p) for p in written),
                             ['measurement-daily-by-kind.md', 'measurement-daily-by-model.md',
                              'measurement-daily-by-project.md', 'measurement-daily-by-role.md'])
            for output in written:
                self.assertTrue(os.path.getsize(output) > 0)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_run_with_no_role_or_model_is_grouped_as_unknown_not_dropped(self):
        text = report.render_by_role([ledger_row(role='', usd='3.0000', ended='2026-09-01T10:00')])
        self.assertIn('| unknown |', text)


if __name__ == '__main__':
    unittest.main()
