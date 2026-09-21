"""session-cost.py and prefix-measure.py — the two measurement tools, 84
statements between them and previously 0% covered.

These are the scripts that make a budget ceiling real. modes/autonomous-run.md
says the spend is written on every turn and the run stops at the ceiling; a
ceiling nobody measures is not a ceiling, so a silent arithmetic error here turns
straight into an overrun. The arithmetic is therefore checked against figures
worked out independently, not against whatever the code happens to return.

Both read ~/.claude/projects/**/*.jsonl, so every test builds a fake HOME with
transcripts in it. Nothing touches the real one.
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('session_cost', os.path.join(SCRIPTS, 'session-cost.py'))
cost = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cost)

PREFIX_MEASURE = os.path.join(SCRIPTS, 'prefix-measure.py')


class FakeHome(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.projects = os.path.join(self.home, '.claude', 'projects', 'someproject')
        os.makedirs(self.projects)
        self._home = os.environ.get('HOME')
        os.environ['HOME'] = self.home

    def tearDown(self):
        if self._home is not None:
            os.environ['HOME'] = self._home
        shutil.rmtree(self.home, ignore_errors=True)

    def transcript(self, name, records):
        path = os.path.join(self.projects, name)
        with open(path, 'w', encoding='utf-8') as handle:
            for record in records:
                handle.write(json.dumps(record) + '\n')
        return path

    @staticmethod
    def assistant(session, model, usage, sidechain=False, timestamp='2026-09-21T10:00:00Z'):
        record = {'sessionId': session, 'timestamp': timestamp,
                  'message': {'model': model, 'usage': usage}}
        if sidechain:
            record['isSidechain'] = True
        return record


class Arithmetic(FakeHome):
    def test_input_and_output_are_priced_at_the_list_rate(self):
        # opus-5 is (5, 25): 1M input = $5, 1M output = $25  ->  $30.00
        self.transcript('a.jsonl', [self.assistant('s1', 'claude-opus-5',
                                                   {'input_tokens': 1_000_000,
                                                    'output_tokens': 1_000_000})])
        self.assertEqual(30.0, cost.measure('s1')['total'])

    def test_a_cache_write_costs_one_and_a_quarter_of_input(self):
        # 1M cache-creation on opus-5: 5 * 1.25 = $6.25
        self.transcript('a.jsonl', [self.assistant('s1', 'claude-opus-5',
                                                   {'cache_creation_input_tokens': 1_000_000})])
        self.assertEqual(6.25, cost.measure('s1')['total'])

    def test_a_cache_read_costs_a_tenth_on_opus(self):
        self.transcript('a.jsonl', [self.assistant('s1', 'claude-opus-5',
                                                   {'cache_read_input_tokens': 1_000_000})])
        self.assertEqual(0.5, cost.measure('s1')['total'])

    def test_a_cache_read_costs_2_5_percent_on_fable_5_1(self):
        # The cheaper cache is the whole reason the rate is per model: 10 * 0.025
        self.transcript('a.jsonl', [self.assistant('s1', 'claude-fable-5-1',
                                                   {'cache_read_input_tokens': 1_000_000})])
        self.assertEqual(0.25, cost.measure('s1')['total'])

    def test_an_unknown_model_is_priced_as_opus_AND_flagged(self):
        # Silently pricing it at zero would understate a real bill.
        self.transcript('a.jsonl', [self.assistant('s1', 'claude-future-9',
                                                   {'input_tokens': 1_000_000})])
        result = cost.measure('s1')
        self.assertEqual(5.0, result['total'])
        self.assertEqual(['claude-future-9'], result['unknown_models'])


class SplitAndSelection(FakeHome):
    def test_subagent_spend_is_counted_separately(self):
        self.transcript('a.jsonl', [
            self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000}),
            self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000}, sidechain=True),
        ])
        result = cost.measure('s1')
        self.assertEqual(5.0, result['main'])
        self.assertEqual(5.0, result['subagent'])
        self.assertEqual(10.0, result['total'])
        self.assertEqual(1, result['assistant_messages'], 'only main-chain messages are counted')

    def test_another_session_in_the_same_file_is_not_counted(self):
        self.transcript('a.jsonl', [
            self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000}),
            self.assistant('other', 'claude-opus-5', {'input_tokens': 9_000_000}),
        ])
        self.assertEqual(5.0, cost.measure('s1')['total'])

    def test_transcripts_are_found_across_project_directories(self):
        second = os.path.join(self.home, '.claude', 'projects', 'another')
        os.makedirs(second)
        with open(os.path.join(second, 'b.jsonl'), 'w', encoding='utf-8') as handle:
            handle.write(json.dumps(self.assistant('s1', 'claude-opus-5',
                                                   {'input_tokens': 1_000_000})) + '\n')
        self.transcript('a.jsonl', [self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000})])
        self.assertEqual(10.0, cost.measure('s1')['total'])

    def test_a_corrupt_line_is_skipped_not_fatal(self):
        path = self.transcript('a.jsonl', [self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000})])
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write('{ not json\n')
        self.assertEqual(5.0, cost.measure('s1')['total'])

    def test_records_with_no_usage_are_ignored(self):
        self.transcript('a.jsonl', [{'sessionId': 's1', 'message': {'model': 'claude-opus-5'}},
                                    self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000})])
        self.assertEqual(1, cost.measure('s1')['assistant_messages'])

    def test_per_model_is_broken_down(self):
        self.transcript('a.jsonl', [
            self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000}),
            self.assistant('s1', 'claude-haiku-4-5', {'input_tokens': 1_000_000}),
        ])
        per_model = cost.measure('s1')['per_model']
        self.assertEqual(5.0, per_model['claude-opus-5'])
        self.assertEqual(1.0, per_model['claude-haiku-4-5'])


class SessionCostMain(FakeHome):
    def setUp(self):
        super().setUp()
        self.argv = sys.argv

    def tearDown(self):
        sys.argv = self.argv
        super().tearDown()

    def run_main(self, *args):
        sys.argv = ['session-cost.py', *args]
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cost.main()
        return buffer.getvalue(), code

    def test_no_argument_prints_the_usage(self):
        out, code = self.run_main()
        self.assertEqual(2, code)
        self.assertIn('Usage', out)

    def test_a_session_that_is_not_there_is_reported_not_zero(self):
        # "$0.00" for a mistyped id would read as "this session was free".
        out, code = self.run_main('nosuchsession')
        self.assertEqual(1, code)
        self.assertIn('session not found', out)

    def test_the_text_report_shows_main_subagent_and_total(self):
        self.transcript('a.jsonl', [
            self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000}),
            self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000}, sidechain=True),
        ])
        out, code = self.run_main('s1')
        self.assertEqual(0, code)
        self.assertIn('$5.00', out)
        self.assertIn('TOTAL $10.00', out)
        self.assertIn('per model', out)

    def test_json_output_is_machine_readable(self):
        self.transcript('a.jsonl', [self.assistant('s1', 'claude-opus-5', {'input_tokens': 1_000_000})])
        out, code = self.run_main('s1', '--json')
        self.assertEqual(0, code)
        self.assertEqual(5.0, json.loads(out)['total'])

    def test_an_unknown_model_is_called_out_in_the_report(self):
        self.transcript('a.jsonl', [self.assistant('s1', 'claude-future-9', {'input_tokens': 1_000_000})])
        out, _ = self.run_main('s1')
        self.assertIn('no price', out)


class PrefixMeasure(FakeHome):
    """prefix-measure.py is module-level code, so it is exercised as a process."""

    def run_it(self, *args):
        result = subprocess.run([sys.executable, PREFIX_MEASURE, *args],
                                capture_output=True, text=True,
                                env=dict(os.environ, HOME=self.home))
        return result.stdout + result.stderr, result.returncode

    def session(self, name, started, prefix_tokens):
        self.transcript(name, [
            {'timestamp': started, 'message': {}},
            {'timestamp': started, 'message': {'usage': {'input_tokens': prefix_tokens}}},
        ])

    def test_it_reports_the_first_usage_of_each_session(self):
        self.session('a.jsonl', '2026-09-20T10:00:00Z', 41_234)
        out, code = self.run_it()
        self.assertEqual(0, code, out)
        self.assertIn('41,234 tokens', out)

    def test_agent_transcripts_are_excluded(self):
        # A subagent's prefix is not the session's fixed prefix.
        self.session('agent-x.jsonl', '2026-09-20T10:00:00Z', 99_999)
        out, _ = self.run_it()
        self.assertNotIn('99,999', out)

    def test_sessions_are_sorted_by_START_not_by_file_time(self):
        # The documented trap: the most recently WRITTEN transcript is usually an
        # OLDER session, and sorting by file time reads it as "after".
        self.session('old.jsonl', '2026-09-01T10:00:00Z', 11_111)
        self.session('new.jsonl', '2026-09-20T10:00:00Z', 22_222)
        os.utime(os.path.join(self.projects, 'old.jsonl'), None)   # touch the OLD one last
        out, _ = self.run_it()
        self.assertLess(out.index('22,222'), out.index('11,111'),
                        'sorted by file timestamp instead of session start')

    def test_a_cut_marks_only_the_sessions_after_it(self):
        self.session('before.jsonl', '2026-09-01T10:00:00Z', 11_111)
        self.session('after.jsonl', '2026-09-20T10:00:00Z', 22_222)
        out, _ = self.run_it('2026-09-10 00:00')
        after_line = [l for l in out.splitlines() if '22,222' in l][0]
        before_line = [l for l in out.splitlines() if '11,111' in l][0]
        self.assertIn('after the cut', after_line)
        self.assertNotIn('after the cut', before_line)
        self.assertIn('median prefix', out)

    def test_a_cut_after_every_session_says_a_new_session_is_needed(self):
        # The point of the tool: a config change is only visible in a NEW session.
        self.session('a.jsonl', '2026-09-01T10:00:00Z', 11_111)
        out, _ = self.run_it('2026-09-20 00:00')
        self.assertIn('a new session is needed', out)

    def test_a_corrupt_line_does_not_stop_the_measurement(self):
        self.session('a.jsonl', '2026-09-20T10:00:00Z', 33_333)
        with open(os.path.join(self.projects, 'a.jsonl'), 'a', encoding='utf-8') as handle:
            handle.write('{ not json\n')
        out, code = self.run_it()
        self.assertEqual(0, code)
        self.assertIn('33,333', out)


if __name__ == '__main__':
    unittest.main()
