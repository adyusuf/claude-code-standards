import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
spec = importlib.util.spec_from_file_location('ledger', os.path.join(SCRIPTS, 'measurement-ledger.py'))
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)

HOUR = 3600


def usage(ts, output=10):
    return {'timestamp': ts, 'message': {'model': 'claude-sonnet-5', 'usage': {
        'input_tokens': 10, 'output_tokens': output, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 500}}}


def agent_call(role, agent_id):
    return [{'message': {'content': [{'type': 'tool_use', 'name': 'Agent', 'id': 't1', 'input': {'subagent_type': role}}]}},
            {'message': {'content': [{'type': 'tool_result', 'tool_use_id': 't1', 'content': f'agentId: {agent_id} finished'}]}}]


class Fixture(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.projects = os.path.join(self.root, 'projects', 'p')
        os.makedirs(self.projects)
        self.ledger_path = os.path.join(self.root, 'ledger.tsv')
        self.stats = ledger.load_stats()
        self.stats.TRANSCRIPTS = os.path.join(self.root, 'projects', '**', '*.jsonl')
        self.now = time.time()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def transcript(self, name, records, age=2 * HOUR):
        path = os.path.join(self.projects, name)
        with open(path, 'w', encoding='utf-8') as handle:
            for record in records:
                handle.write(json.dumps(record) + '\n')
        os.utime(path, (self.now - age, self.now - age))
        return path

    def append(self, path, records, age=0):
        with open(path, 'a', encoding='utf-8') as handle:
            for record in records:
                handle.write(json.dumps(record) + '\n')
        os.utime(path, (self.now - age, self.now - age))

    def age_ledger(self, seconds=HOUR):
        os.utime(self.ledger_path, (self.now - seconds, self.now - seconds))

    def run_auto(self, min_interval=0):
        return ledger.auto_update(self.ledger_path, self.stats, days=30, min_interval=min_interval, now=self.now)

    def rows(self):
        return ledger.read_ledger(self.ledger_path)

    def session_and_agent(self):
        self.session = self.transcript('s1.jsonl', [usage('2026-09-01T10:00:00Z')] + agent_call('qa', 'abcd1234'))
        self.agent = self.transcript('agent-abcd1234.jsonl', [usage('2026-09-01T10:05:00Z')])


class AutoUpdate(Fixture):
    def test_first_run_writes_every_row_with_the_agent_role_resolved(self):
        self.session_and_agent()
        self.assertEqual(self.run_auto(), 2)
        roles = sorted((r['kind'], r['role']) for r in self.rows().values())
        self.assertEqual(roles, [('agent', 'qa'), ('session', 'main')])

    def test_a_run_inside_the_minimum_interval_does_nothing(self):
        self.session_and_agent()
        self.run_auto()
        before = os.path.getmtime(self.ledger_path)
        self.append(self.session, [usage('2026-09-01T10:30:00Z')])      # there IS something new
        self.assertIsNone(self.run_auto(min_interval=600))
        self.assertEqual(os.path.getmtime(self.ledger_path), before)
        self.assertEqual(self.rows()[ledger.hash_id(self.session)]['requests'], '1')
        self.age_ledger(700)                                              # 700 s later...
        self.assertEqual(self.run_auto(min_interval=600), 1)             # ...it is picked up
        self.assertEqual(self.rows()[ledger.hash_id(self.session)]['requests'], '2')

    def test_nothing_modified_since_the_last_write_means_no_rewrite(self):
        self.session_and_agent()
        self.run_auto()
        self.age_ledger()
        before = os.path.getmtime(self.ledger_path)
        self.assertIsNone(self.run_auto())
        self.assertEqual(os.path.getmtime(self.ledger_path), before)

    def test_only_the_modified_transcript_is_re_read(self):
        self.session_and_agent()
        self.run_auto()
        self.age_ledger()
        agent_before = dict(self.rows()[ledger.hash_id(self.agent)])
        self.append(self.session, [usage('2026-09-01T10:30:00Z', output=99)])
        self.assertEqual(self.run_auto(), 1)
        rows = self.rows()
        self.assertEqual(rows[ledger.hash_id(self.session)]['requests'], '2')
        self.assertEqual(rows[ledger.hash_id(self.agent)], agent_before)

    def test_a_changed_agent_keeps_the_role_an_earlier_run_resolved(self):
        self.session_and_agent()
        self.run_auto()
        self.age_ledger()
        self.append(self.agent, [usage('2026-09-01T10:40:00Z')])
        self.run_auto()
        self.assertEqual(self.rows()[ledger.hash_id(self.agent)]['role'], 'qa')

    def test_a_new_agent_whose_parent_did_not_change_still_gets_its_role(self):
        self.session = self.transcript('s1.jsonl', [usage('2026-09-01T10:00:00Z')] + agent_call('security', 'beef0001'))
        self.run_auto()
        self.age_ledger()
        agent = self.transcript('agent-beef0001.jsonl', [usage('2026-09-01T10:05:00Z')], age=0)
        self.run_auto()
        self.assertEqual(self.rows()[ledger.hash_id(agent)]['role'], 'security')

    def test_history_survives_when_a_transcript_disappears(self):
        self.session_and_agent()
        self.run_auto()
        self.age_ledger()
        os.remove(self.agent)
        self.append(self.session, [usage('2026-09-01T11:00:00Z')])
        self.run_auto()
        self.assertEqual(len(self.rows()), 2)


class Safety(Fixture):
    def test_a_fresh_lock_blocks_a_second_run_and_a_stale_one_is_taken_over(self):
        self.session_and_agent()
        lock = self.ledger_path + '.lock'
        os.mkdir(lock)
        self.assertIsNone(self.run_auto())
        self.assertFalse(os.path.exists(self.ledger_path))
        os.utime(lock, (self.now - 2000, self.now - 2000))
        self.assertEqual(self.run_auto(), 2)
        self.assertFalse(os.path.exists(lock))

    def test_a_row_that_fails_its_pattern_writes_nothing(self):
        self.session_and_agent()
        original = ledger.problems
        ledger.problems = lambda rows: [('x', 'role')]
        try:
            self.assertIsNone(self.run_auto())
        finally:
            ledger.problems = original
        self.assertFalse(os.path.exists(self.ledger_path))

    def test_no_temporary_file_or_lock_is_left_behind(self):
        self.session_and_agent()
        self.run_auto()
        self.assertEqual(sorted(os.listdir(self.root)), ['ledger.tsv', 'projects'])


class DetachedFromASymlink(unittest.TestCase):
    """The Stop hook runs a symlink; the ledger must land in the repository the script really lives in."""

    def test_detached_auto_run_returns_at_once_and_writes_beside_the_real_script(self):
        repo, home = tempfile.mkdtemp(), tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(repo, 'scripts'))
            os.makedirs(os.path.join(repo, 'docs'))
            for name in ('measurement-ledger.py', 'step-stats.py'):
                shutil.copy(os.path.join(SCRIPTS, name), os.path.join(repo, 'scripts', name))
            projects = os.path.join(home, '.claude', 'projects', 'p')
            os.makedirs(projects)
            with open(os.path.join(projects, 's1.jsonl'), 'w', encoding='utf-8') as handle:
                handle.write(json.dumps(usage('2026-09-01T10:00:00Z')) + '\n')
            hooks = os.path.join(home, '.claude', 'hooks')
            os.makedirs(hooks)
            link = os.path.join(hooks, 'measurement-ledger.py')
            os.symlink(os.path.join(repo, 'scripts', 'measurement-ledger.py'), link)
            started = time.time()
            result = subprocess.run([sys.executable, link, '--auto', '--detach'], env=dict(os.environ, HOME=home),
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0)
            self.assertLess(time.time() - started, 5)
            target = os.path.join(repo, 'docs', 'measurement-ledger.tsv')
            for _ in range(100):
                if os.path.exists(target):
                    break
                time.sleep(0.1)
            self.assertTrue(os.path.exists(target), 'the detached child never wrote the ledger')
            self.assertFalse(os.path.exists(os.path.join(hooks, '..', 'docs')))
        finally:
            shutil.rmtree(repo, ignore_errors=True)
            shutil.rmtree(home, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
