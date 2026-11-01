"""The session's status table: what the pane's Status box shows, written by Claude and by background runs.

Each test runs the script as a command, with ADYUSUF_STATUS_DIR pointed at a temporary directory, so no real status file
is read or written.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import importlib.util

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SCRIPTS, 'adyusuf_status.py')

_spec = importlib.util.spec_from_file_location('adyusuf_status', SCRIPT)
status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(status)

SESSION = 'abc-123'


class StatusTable(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = dict(os.environ, ADYUSUF_STATUS_DIR=self.dir)

    def run_tool(self, *args, session=SESSION):
        done = subprocess.run([sys.executable, SCRIPT, '--session', session, *args], env=self.env,
                              capture_output=True, text=True)
        return done.stdout, done.stderr, done.returncode

    def table(self):
        out, _, code = self.run_tool('show', '--json')
        self.assertEqual(0, code)
        return json.loads(out)

    def test_an_unwritten_session_shows_nothing_running(self):
        out, _, code = self.run_tool('show')
        self.assertEqual((0, 'nothing running\n'), (code, out))
        self.assertEqual([], self.table()['rows'])

    def test_now_next_and_rows_are_stored_and_a_row_with_the_same_item_is_replaced_in_place(self):
        self.run_tool('now', 'prod gate')
        self.run_tool('next', 'plugin update')
        self.run_tool('row', 'dev', 'pushed', '4a45bda (promote.log)', '-')
        self.run_tool('row', 'prod', 'gate running', 'coverage step', 'promote.sh')
        self.run_tool('row', 'dev', 'pushed again', 'b0b0b0b', '-')
        data = self.table()
        self.assertEqual(('prod gate', 'plugin update'), (data['now'], data['next']))
        self.assertEqual([['dev', 'pushed again'], ['prod', 'gate running']], [[r['item'], r['state']] for r in data['rows']])
        self.assertRegex(data['updated'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')
        out, _, _ = self.run_tool('show')
        self.assertEqual('now:  prod gate\nnext: plugin update\ndev | pushed again | b0b0b0b | -\n'
                         'prod | gate running | coverage step | promote.sh\n', out)

    def test_drop_removes_one_row_and_clear_empties_the_table(self):
        self.run_tool('row', 'a', 's', 'f', 'w')
        self.run_tool('row', 'b', 's', 'f', 'w')
        self.run_tool('drop', 'a')
        self.assertEqual(['b'], [r['item'] for r in self.table()['rows']])
        self.run_tool('now', 'x')
        self.run_tool('clear')
        self.assertEqual(('', []), (self.table()['now'], self.table()['rows']))

    def test_a_field_is_one_line_and_clipped(self):
        self.run_tool('now', 'two\nlines   and  spaces')
        self.assertEqual('two lines and spaces', self.table()['now'])
        self.run_tool('next', 'x' * 1000)
        self.assertEqual(status.MAX_TEXT, len(self.table()['next']))
        self.assertTrue(self.table()['next'].endswith('…'))

    def test_an_unusable_session_id_is_refused_and_nothing_is_written(self):
        for bad in ('../escape', 'a/b', '', 'x' * 101):
            _, err, code = self.run_tool('now', 'x', session=bad)
            self.assertEqual(2, code, bad)
            self.assertIn('not a usable session id', err)
        self.assertEqual([], os.listdir(self.dir))

    def test_an_unreadable_file_is_refused_not_overwritten(self):
        path = os.path.join(self.dir, SESSION + '.json')
        with open(path, 'w') as handle:
            handle.write('[1, 2]')
        _, err, code = self.run_tool('now', 'x')
        self.assertEqual(2, code)
        self.assertIn('not a status table', err)
        with open(path) as handle:
            self.assertEqual('[1, 2]', handle.read())

    def test_the_write_is_atomic_and_leaves_no_temporary_file(self):
        self.run_tool('row', 'a', 's', 'f', 'w')
        self.assertEqual([SESSION + '.json'], os.listdir(self.dir))

    def test_files_nobody_wrote_to_for_keep_days_are_pruned_on_a_write(self):
        old = os.path.join(self.dir, 'old.json')
        with open(old, 'w') as handle:
            handle.write('{}')
        stale = time.time() - (status.KEEP_DAYS + 1) * 86400
        os.utime(old, (stale, stale))
        self.run_tool('now', 'x')
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(os.path.join(self.dir, SESSION + '.json')))


if __name__ == '__main__':
    unittest.main()
