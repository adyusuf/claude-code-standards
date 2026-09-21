import datetime
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ledger', os.path.join(HERE, '..', 'measurement-ledger.py'))
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
STATS = ledger.load_stats()


def transcript(records):
    handle = tempfile.NamedTemporaryFile('w', suffix='.jsonl', prefix='agent-', delete=False)
    for record in records:
        handle.write(json.dumps(record) + '\n')
    handle.close()
    return handle.name


def usage(ts, i=100, o=10, cw=1000, cr=5000, model='claude-sonnet-5'):
    return {'timestamp': ts, 'message': {'model': model, 'usage': {
        'input_tokens': i, 'output_tokens': o, 'cache_creation_input_tokens': cw, 'cache_read_input_tokens': cr}}}


def tool_call(command, at, ident):
    return {'timestamp': at, 'message': {'content': [
        {'type': 'tool_use', 'name': 'Bash', 'id': ident, 'input': {'command': command}}]}}


def tool_result(at, ident):
    return {'timestamp': at, 'message': {'content': [{'type': 'tool_result', 'tool_use_id': ident, 'content': 'ok'}]}}


def bash(command):
    return {'timestamp': '2026-09-01T10:00:05.000Z', 'message': {'content': [
        {'type': 'tool_use', 'name': 'Bash', 'id': 'x', 'input': {'command': command}}]}}


class LedgerRow(unittest.TestCase):
    def setUp(self):
        self.path = transcript([usage('2026-09-01T10:00:00.000Z'), bash('dotnet build /Users/someone/AcmeCorp'),
                                usage('2026-09-01T10:01:00.000Z', i=50, o=5, cw=0, cr=6000)])

    def tearDown(self):
        os.unlink(self.path)

    def test_tokens_are_summed_and_cost_matches_the_list_price(self):
        row = ledger.row_for(self.path, 'agent', 'qa', STATS, [])
        self.assertEqual((row['requests'], row['input'], row['output'], row['cache_write'], row['cache_read']),
                         ('2', '150', '15', '1000', '11000'))
        p_in, p_out, cache = STATS.price('claude-sonnet-5')
        expected = (150 * p_in + 15 * p_out + 1000 * p_in * 1.25 + 11000 * p_in * cache) / 1e6
        self.assertAlmostEqual(float(row['usd']), expected, places=4)

    def test_step_counted_and_no_path_or_project_reaches_the_row(self):
        row = ledger.row_for(self.path, 'agent', 'qa', STATS, [])
        self.assertEqual(row['steps'], 'build=1')
        self.assertNotIn('Users', '\t'.join(row.values()))
        self.assertNotIn('AcmeCorp', '\t'.join(row.values()))

    def test_row_passes_every_column_pattern(self):
        self.assertEqual(ledger.problems([ledger.row_for(self.path, 'agent', 'qa', STATS, [])]), [])

    def test_cut_ordinal_counts_only_cuts_before_the_row(self):
        before = datetime.datetime(2026, 9, 1, 9, 0, tzinfo=datetime.timezone.utc).timestamp()
        after = datetime.datetime(2026, 9, 2, 9, 0, tzinfo=datetime.timezone.utc).timestamp()
        row = ledger.row_for(self.path, 'agent', 'qa', STATS, [before, after])
        self.assertEqual(row['cut'], '1')

    def test_a_transcript_without_usage_produces_no_row(self):
        empty = transcript([{'timestamp': '2026-09-01T10:00:00.000Z'}])
        try:
            self.assertIsNone(ledger.row_for(empty, 'agent', 'qa', STATS, []))
        finally:
            os.unlink(empty)

    def test_id_is_stable_and_not_the_file_name(self):
        first = ledger.row_for(self.path, 'agent', 'qa', STATS, [])
        second = ledger.row_for(self.path, 'agent', 'qa', STATS, [])
        self.assertEqual(first['id'], second['id'])
        self.assertNotIn(first['id'], os.path.basename(self.path))


class StepSeconds(unittest.TestCase):
    def row(self, records):
        path = transcript([usage('2026-09-01T10:00:00.000Z')] + records)
        try:
            return ledger.row_for(path, 'agent', 'qa', STATS, [])
        finally:
            os.unlink(path)

    def test_a_step_is_timed_from_the_call_to_its_result(self):
        row = self.row([tool_call('dotnet build x', '2026-09-01T10:01:00.000Z', 'a'), tool_result('2026-09-01T10:01:42.000Z', 'a')])
        self.assertEqual(row['step_seconds'], 'build=42')
        self.assertEqual(row['steps'], 'build=1')

    def test_the_same_step_run_twice_adds_up(self):
        row = self.row([tool_call('npm run build', '2026-09-01T10:01:00.000Z', 'a'), tool_result('2026-09-01T10:01:10.000Z', 'a'),
                        tool_call('npm run build', '2026-09-01T10:02:00.000Z', 'b'), tool_result('2026-09-01T10:02:30.000Z', 'b')])
        self.assertEqual(row['step_seconds'], 'build=40')

    def test_a_command_that_runs_two_steps_is_split_evenly(self):
        row = self.row([tool_call('npm run build && npm test', '2026-09-01T10:01:00.000Z', 'a'), tool_result('2026-09-01T10:01:20.000Z', 'a')])
        self.assertEqual(row['step_seconds'], 'build=10;unit test=10')

    def test_a_call_over_an_hour_is_dropped_as_a_hang(self):
        row = self.row([tool_call('dotnet build x', '2026-09-01T10:01:00.000Z', 'a'), tool_result('2026-09-01T12:30:00.000Z', 'a')])
        self.assertEqual(row['step_seconds'], '')

    def test_a_call_with_no_result_and_a_non_step_command_add_nothing(self):
        row = self.row([tool_call('dotnet build x', '2026-09-01T10:01:00.000Z', 'a'),
                        tool_call('ls -la', '2026-09-01T10:02:00.000Z', 'b'), tool_result('2026-09-01T10:02:05.000Z', 'b')])
        self.assertEqual(row['step_seconds'], '')

    def test_a_command_that_only_mentions_a_step_is_not_timed(self):
        row = self.row([tool_call('grep -n "dotnet build" README.md', '2026-09-01T10:01:00.000Z', 'a'), tool_result('2026-09-01T10:01:09.000Z', 'a')])
        self.assertEqual(row['step_seconds'], '')

    def test_a_command_that_talks_about_step_stats_is_not_timed(self):
        row = self.row([tool_call('python3 scripts/step-stats.py && dotnet build x', '2026-09-01T10:01:00.000Z', 'a'),
                        tool_result('2026-09-01T10:01:30.000Z', 'a')])
        self.assertEqual(row['step_seconds'], '')

    def test_the_timed_row_passes_every_column_pattern(self):
        row = self.row([tool_call('dotnet test', '2026-09-01T10:01:00.000Z', 'a'), tool_result('2026-09-01T10:01:07.000Z', 'a')])
        self.assertEqual(ledger.problems([row]), [])

    def read_old(self, column_count, values):
        with tempfile.NamedTemporaryFile('w', suffix='.tsv', delete=False) as handle:
            handle.write('\t'.join(ledger.NAMES[:column_count]) + '\n')
            handle.write('\t'.join(values[:column_count]) + '\n')
        try:
            return ledger.read_ledger(handle.name)
        finally:
            os.unlink(handle.name)

    OLD = ['aaaaaaaaaa', '2026-08-01T00:00', 'agent', 'qa', 'm', '1', '0', '0', '0', '0', '1.0000', '0', 'build=2']

    def test_a_ledger_written_before_step_seconds_existed_is_still_read(self):
        rows = self.read_old(13, self.OLD)
        self.assertEqual(rows['aaaaaaaaaa']['steps'], 'build=2')
        for missing in ('step_seconds', 'project', 'ended'):
            self.assertEqual(rows['aaaaaaaaaa'][missing], '')

    def test_a_ledger_written_before_project_and_ended_existed_is_still_read(self):
        rows = self.read_old(14, self.OLD + ['build=42'])
        self.assertEqual(rows['aaaaaaaaaa']['step_seconds'], 'build=42')
        self.assertEqual((rows['aaaaaaaaaa']['project'], rows['aaaaaaaaaa']['ended']), ('', ''))

    def test_the_header_decides_the_column_order_not_the_position(self):
        with tempfile.NamedTemporaryFile('w', suffix='.tsv', delete=False) as handle:
            handle.write('id\tusd\tkind\n' + 'bbbbbbbbbb\t2.0000\tagent\n')     # NAMES has started second and kind third
        try:
            row = ledger.read_ledger(handle.name)['bbbbbbbbbb']
            self.assertEqual((row['kind'], row['usd']), ('agent', '2.0000'))
        finally:
            os.unlink(handle.name)


class LedgerSafety(unittest.TestCase):
    def test_a_role_that_is_not_a_plain_name_becomes_other(self):
        for role in ('../../etc/passwd', 'a b', '', None, 'x' * 60):
            self.assertEqual(ledger.safe_role(role, STATS), 'other')

    def test_old_turkish_role_names_are_normalised(self):
        self.assertEqual(ledger.safe_role('gelistirici', STATS), 'developer')

    def test_a_field_that_fails_its_pattern_is_reported(self):
        row = {name: '0' for name in ledger.NAMES}
        row.update(id='abcdef0123', started='2026-09-01T10:00', kind='agent', role='qa', model='m', usd='1.0000',
                   steps='', step_seconds='', project='groot', ended='')
        self.assertEqual(ledger.problems([row]), [])
        row['role'] = '/Users/x/Project'
        self.assertEqual(ledger.problems([row]), [('abcdef0123', 'role')])
        row.update(role='qa', steps='build=1\tinjected')
        self.assertEqual(ledger.problems([row]), [('abcdef0123', 'steps')])


class LedgerMerge(unittest.TestCase):
    def rows(self, ident, started, usd='1.0000'):
        row = {name: '0' for name in ledger.NAMES}
        row.update(id=ident, started=started, kind='agent', role='qa', model='m', usd=usd, steps='', step_seconds='',
                   project='groot', ended='')
        return row

    def test_history_survives_and_a_running_session_is_updated(self):
        old = {'aaaaaaaaaa': self.rows('aaaaaaaaaa', '2026-08-01T00:00'), 'bbbbbbbbbb': self.rows('bbbbbbbbbb', '2026-09-01T00:00')}
        merged = ledger.merge(old, [self.rows('bbbbbbbbbb', '2026-09-01T00:00', usd='2.0000'),
                                    self.rows('cccccccccc', '2026-09-02T00:00')])
        self.assertEqual([r['id'] for r in merged], ['aaaaaaaaaa', 'bbbbbbbbbb', 'cccccccccc'])
        self.assertEqual(merged[1]['usd'], '2.0000')

    def test_render_and_read_round_trip(self):
        rows = ledger.merge({}, [self.rows('aaaaaaaaaa', '2026-08-01T00:00')])
        with tempfile.NamedTemporaryFile('w', suffix='.tsv', delete=False) as handle:
            handle.write(ledger.render(rows))
        try:
            self.assertEqual(list(ledger.read_ledger(handle.name).values()), rows)
        finally:
            os.unlink(handle.name)


if __name__ == '__main__':
    unittest.main()
