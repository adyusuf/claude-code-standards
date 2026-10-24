"""hooks/choose.ts: the Python the Settings box runs instead of a shell (the engine's process runner could not find `sh`
on Windows, 24/10/2026). The TypeScript tests cannot execute it (no process in their environment), so this test lifts
the two source strings out of choose.ts and runs them for real against a fake ~/.claude/plugins tree."""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

CHOOSE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'hooks', 'choose.ts'))


def source_of(name):
    """The Python source of `export const <name> = ...` — a quoted string, or an array of quoted lines joined by newlines."""
    with open(CHOOSE, encoding='utf-8') as handle:
        text = handle.read()
    joined = re.search(r"export const %s = \[\n(.*?)\n\]\.join\('\\n'\)" % name, text, re.S)
    if joined:
        return '\n'.join(ast.literal_eval(line.strip().rstrip(',')) for line in joined.group(1).split('\n'))
    single = re.search(r"export const %s = ('.*')$" % name, text, re.M)
    return ast.literal_eval(single.group(1))


class Discover(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.plugins = os.path.join(self.home, '.claude', 'plugins')
        self.root = os.path.join(self.plugins, 'cache', 'mkt', 'plug')

    def version(self, name, age, orphaned=False):
        path = os.path.join(self.root, name)
        os.makedirs(path)
        if orphaned:
            open(os.path.join(path, '.orphaned_at'), 'w').close()
        os.utime(path, (1_000_000 + age, 1_000_000 + age))
        return path

    def run_py(self, code, *args):
        env = {**os.environ, 'HOME': self.home, 'USERPROFILE': self.home, 'PYTHONUTF8': '1'}
        return subprocess.run([sys.executable, '-c', code, *args], capture_output=True, text=True, encoding='utf-8', env=env)

    def discover(self):
        done = self.run_py(source_of('DISCOVER_PY'), 'mkt', 'plug')
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_the_cache_is_listed_newest_first_with_the_replaced_ones_marked_and_forward_slashes(self):
        old = self.version('49eb', 1, orphaned=True)
        new = self.version('3a60', 2)
        os.makedirs(self.plugins, exist_ok=True)
        with open(os.path.join(self.plugins, 'installed_plugins.json'), 'w', encoding='utf-8') as handle:
            handle.write('{"plugins": {}}')
        found = self.discover()
        self.assertEqual(found['record'], '{"plugins": {}}')
        self.assertEqual(found['cache'], [['live', new.replace(os.sep, '/')], ['orphaned', old.replace(os.sep, '/')]])

    def test_a_file_in_the_cache_folder_is_not_a_version(self):
        self.version('3a60', 1)
        open(os.path.join(self.root, 'stray.txt'), 'w').close()
        self.assertEqual([state for state, _ in self.discover()['cache']], ['live'])

    def test_no_record_and_no_cache_print_an_empty_answer_and_still_succeed(self):
        self.assertEqual(self.discover(), {'record': '', 'cache': []})

    def test_the_file_check_exits_0_for_a_file_and_1_for_anything_else(self):
        code = source_of('IS_FILE_PY')
        present = os.path.join(self.home, 'present.py')
        open(present, 'w').close()
        self.assertEqual(self.run_py(code, present).returncode, 0)
        self.assertEqual(self.run_py(code, self.home).returncode, 1)
        self.assertEqual(self.run_py(code, os.path.join(self.home, 'missing.py')).returncode, 1)


if __name__ == '__main__':
    unittest.main()
