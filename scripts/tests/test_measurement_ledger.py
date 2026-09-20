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


class LedgerSafety(unittest.TestCase):
    def test_a_role_that_is_not_a_plain_name_becomes_other(self):
        for role in ('../../etc/passwd', 'a b', '', None, 'x' * 60):
            self.assertEqual(ledger.safe_role(role, STATS), 'other')

    def test_old_turkish_role_names_are_normalised(self):
        self.assertEqual(ledger.safe_role('gelistirici', STATS), 'developer')

    def test_a_field_that_fails_its_pattern_is_reported(self):
        row = {name: '0' for name in ledger.NAMES}
        row.update(id='abcdef0123', started='2026-09-01T10:00', kind='agent', role='qa', model='m', usd='1.0000',
                   steps='')
        self.assertEqual(ledger.problems([row]), [])
        row['role'] = '/Users/x/Project'
        self.assertEqual(ledger.problems([row]), [('abcdef0123', 'role')])
        row.update(role='qa', steps='build=1\tinjected')
        self.assertEqual(ledger.problems([row]), [('abcdef0123', 'steps')])


class LedgerMerge(unittest.TestCase):
    def rows(self, ident, started, usd='1.0000'):
        row = {name: '0' for name in ledger.NAMES}
        row.update(id=ident, started=started, kind='agent', role='qa', model='m', usd=usd, steps='')
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
