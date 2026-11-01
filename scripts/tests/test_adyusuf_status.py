"""The session's status table: what the pane's Status box shows, written by Claude and by background runs.

Each test runs the script as a command, with ADYUSUF_STATUS_DIR pointed at a temporary directory, so no real status file
is read or written.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

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

    def write_raw(self, text, name=SESSION + '.json'):
        with open(os.path.join(self.dir, name), 'w', encoding='utf-8') as handle:
            handle.write(text)

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
        for bad in ('../escape', 'a/b', '', 'x' * 101, 'é١', 'a b'):
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
        self.assertIn('`clear` replaces it', err)
        with open(path) as handle:
            self.assertEqual('[1, 2]', handle.read())

    def test_the_write_is_atomic_and_leaves_no_temporary_file(self):
        self.run_tool('row', 'a', 's', 'f', 'w')
        self.assertEqual([SESSION + '.json', SESSION + '.lock'], sorted(os.listdir(self.dir)))

    def test_old_status_files_are_pruned_on_a_write_and_no_other_file_is(self):
        stale = time.time() - (status.KEEP_DAYS + 1) * 86400
        files = {
            'old.json': '{"now": "", "rows": [], "updated": "2020-01-01T00:00:00Z"}',  # an old status table: removed
            'old.lock': '',                                                              # its lock: removed with it
            'package.json': '{"name": "x"}',                                             # a foreign JSON file: kept
            'notes.json': '{"rows": []}',                                                # no `updated`: not ours, kept
            'list.json': '[1, 2]',                                                       # not a table: kept
            'a.b.json': '{"rows": [], "updated": "x"}',                                  # not a session's name: kept
        }
        for name, text in files.items():
            self.write_raw(text, name)
            os.utime(os.path.join(self.dir, name), (stale, stale))
        self.run_tool('now', 'x')
        self.assertEqual(sorted(['a.b.json', 'list.json', 'notes.json', 'package.json', SESSION + '.json', SESSION + '.lock']),
                         sorted(os.listdir(self.dir)))

    def test_rows_that_are_not_objects_are_dropped_and_odd_fields_read_as_text(self):
        self.write_raw('{"now": 5, "rows": [1, "x", null, {"item": null, "state": 2}]}')
        out, _, code = self.run_tool('show')
        self.assertEqual((0, 'now:  5\n | 2 |  | \n'), (code, out))
        _, _, code = self.run_tool('row', 'b', 's', 'f', 'w')
        self.assertEqual(0, code)
        self.assertEqual(['', 'b'], [row['item'] for row in self.table()['rows']])

    def test_clear_replaces_a_corrupt_file(self):
        self.write_raw('{bad')
        _, err, code = self.run_tool('now', 'x')
        self.assertEqual(2, code)
        self.assertIn('`clear` replaces it', err)
        _, _, code = self.run_tool('clear')
        self.assertEqual(0, code)
        self.assertEqual([], self.table()['rows'])

    def test_concurrent_writers_keep_every_row(self):
        procs = [subprocess.Popen([sys.executable, SCRIPT, '--session', SESSION, 'row', 'item%d' % i, 's', 'f', 'w'],
                                  env=self.env) for i in range(12)]
        self.assertEqual([0] * 12, [proc.wait() for proc in procs])
        self.assertEqual(sorted('item%d' % i for i in range(12)), sorted(row['item'] for row in self.table()['rows']))

    def test_control_characters_are_removed(self):
        self.run_tool('now', 'a\x1b[2Jb\x07c\x9bd')
        self.assertEqual('a [2Jb c d', self.table()['now'])

    def test_the_table_keeps_the_last_max_rows(self):
        rows = [{'item': 'i%d' % i} for i in range(status.MAX_ROWS + 5)]
        self.write_raw(json.dumps({'rows': rows, 'updated': ''}))
        self.run_tool('now', 'x')
        items = [row['item'] for row in self.table()['rows']]
        self.assertEqual((status.MAX_ROWS, 'i5', 'i%d' % (status.MAX_ROWS + 4)), (len(items), items[0], items[-1]))

    def test_a_relative_status_folder_is_refused(self):
        self.env['ADYUSUF_STATUS_DIR'] = 'relative/dir'
        _, err, code = self.run_tool('now', 'x')
        self.assertEqual(2, code)
        self.assertIn('absolute path', err)


if __name__ == '__main__':
    unittest.main()
