"""step-stats.py's REPORTING half — the part that turns measurements into a document.

The sanitiser and the step counting are covered elsewhere. What was not covered is
everything downstream of them: which role a run belongs to, and whether a cut's delta
may be published at all. Both decide what the generated measurement log CLAIMS, and a
wrong claim there is worse than a missing one — the document is the evidence the README
points at.

`cut_delta` carries two regressions in its own docstring: a hard-coded '-' that
published a prefix which GREW as a saving, and a delta published from a single session
after the cut when the method requires three. Those are exactly the two things a test
has to hold down, because both were shipped once.
"""
import importlib.util
import json
import os
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('step_stats_report', os.path.join(SCRIPTS, 'step-stats.py'))
stats = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stats)


class CutDelta(unittest.TestCase):
    """A cut's delta cell: publishable, or explicitly 'not measured'."""

    def test_a_prefix_that_shrank_is_a_saving(self):
        self.assertEqual(stats.cut_delta(100_000, 5, 80_000, 5), '**-20,000 (-20%)**')

    def test_a_prefix_that_GREW_carries_a_plus_not_a_minus(self):
        # Hard-coding '-' published +8,598 as "--8,598 (--10%)": a regression that read
        # as a win. The sign comes from the number.
        cell = stats.cut_delta(80_000, 5, 88_598, 5)
        self.assertEqual(cell, '**+8,598 (+11%)**')
        self.assertNotIn('--', cell)

    def test_no_session_after_the_cut_is_not_measured(self):
        self.assertIn('not measured', stats.cut_delta(100_000, 5, 0, 0))

    def test_fewer_than_three_sessions_after_the_cut_is_not_measured(self):
        cell = stats.cut_delta(100_000, 9, 50_000, 2)
        self.assertIn('not measured', cell)
        self.assertIn('2 session(s) after', cell)
        self.assertNotIn('%', cell, 'a percentage here would be a published claim')

    def test_fewer_than_three_sessions_BEFORE_the_cut_is_not_measured_either(self):
        cell = stats.cut_delta(100_000, 1, 50_000, 9)
        self.assertIn('not measured', cell)
        self.assertIn('before', cell)

    def test_three_a_side_is_the_boundary_and_publishes(self):
        self.assertEqual(stats.MIN_CUT_ROWS, 3)
        self.assertIn('%', stats.cut_delta(100_000, 3, 90_000, 3))

    def test_a_missing_before_median_is_not_measured(self):
        self.assertIn('not measured', stats.cut_delta(0, 5, 90_000, 5))


class RoleIds(unittest.TestCase):
    """An agent run is attributed by matching the Agent call to the agentId it returns."""

    def transcript(self, records):
        handle = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False, encoding='utf-8')
        for record in records:
            handle.write(json.dumps(record) + '\n')
        handle.close()
        self.addCleanup(os.remove, handle.name)
        return handle.name

    @staticmethod
    def call(tool_use_id, role):
        return {'message': {'content': [
            {'type': 'tool_use', 'id': tool_use_id, 'name': 'Agent', 'input': {'subagent_type': role}}]}}

    @staticmethod
    def result(tool_use_id, agent_id):
        return {'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': tool_use_id, 'content': f'agentId: {agent_id}'}]}}

    def test_a_call_and_its_result_are_matched(self):
        path = self.transcript([self.call('t1', 'qa'), self.result('t1', 'aaaaaaaa')])
        self.assertEqual(stats.role_ids([path]), {'aaaaaaaa': 'qa'})

    def test_two_roles_in_one_transcript_stay_apart(self):
        path = self.transcript([self.call('t1', 'qa'), self.call('t2', 'analyst'),
                                self.result('t2', 'bbbbbbbb'), self.result('t1', 'aaaaaaaa')])
        self.assertEqual(stats.role_ids([path]), {'aaaaaaaa': 'qa', 'bbbbbbbb': 'analyst'})

    def test_a_result_with_no_matching_call_is_unknown_not_dropped(self):
        # Attributing it to the wrong role would move real spend onto an innocent one;
        # dropping it would lose the run. It is named.
        path = self.transcript([self.result('orphan', 'cccccccc')])
        self.assertEqual(stats.role_ids([path]), {'cccccccc': 'unknown'})

    def test_an_agent_call_with_no_subagent_type_is_unknown(self):
        path = self.transcript([{'message': {'content': [
            {'type': 'tool_use', 'id': 't1', 'name': 'Agent', 'input': {}}]}},
            self.result('t1', 'dddddddd')])
        self.assertEqual(stats.role_ids([path]), {'dddddddd': 'unknown'})

    def test_a_Task_call_is_read_as_an_Agent_call(self):
        path = self.transcript([{'message': {'content': [
            {'type': 'tool_use', 'id': 't1', 'name': 'Task', 'input': {'subagent_type': 'devops'}}]}},
            self.result('t1', 'eeeeeeee')])
        self.assertEqual(stats.role_ids([path]), {'eeeeeeee': 'devops'})

    def test_a_tool_that_is_neither_is_ignored(self):
        path = self.transcript([{'message': {'content': [
            {'type': 'tool_use', 'id': 't1', 'name': 'Bash', 'input': {'command': 'ls'}}]}}])
        self.assertEqual(stats.role_ids([path]), {})

    def test_unparsable_lines_and_odd_shapes_do_not_stop_the_scan(self):
        # A transcript is append-only and can end mid-write; one bad line must not cost
        # the whole file.
        handle = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False, encoding='utf-8')
        handle.write('{not json\n')
        handle.write(json.dumps({'message': {'content': 'a string, not a list'}}) + '\n')
        handle.write(json.dumps({'message': {'content': ['not a dict']}}) + '\n')
        handle.write(json.dumps(self.call('t1', 'security')) + '\n')
        handle.write(json.dumps(self.result('t1', 'ffffffff')) + '\n')
        handle.close()
        self.addCleanup(os.remove, handle.name)
        self.assertEqual(stats.role_ids([handle.name]), {'ffffffff': 'security'})


if __name__ == '__main__':
    unittest.main()
