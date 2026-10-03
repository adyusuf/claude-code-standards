"""The gate is four twin files (scripts/gate-core.sh + gate-lib*.sh), split so that no file passes
300 lines (global rule #9). What matters is not that the split exists but that it cannot rot:

  · a copy of the core WITHOUT its libraries must refuse to run (exit 2), never run a partial gate;
  · the libraries must be in the twin list, or a project could keep a stale one unnoticed;
  · no gate file may grow back past the limit.

That the split changed no behaviour was checked once by running the old and the new gate over fixture
projects (--list and real runs, serial and parallel, dev/test/prod): 48 runs, identical output.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FILES = ('gate-core.sh', 'gate-lib.sh', 'gate-lib-node.sh', 'gate-lib-prod.sh')
LIMIT = 300


def twins():
    with open(os.path.join(SCRIPTS, 'twins.txt'), encoding='utf-8') as handle:
        return [ln.strip() for ln in handle if ln.strip() and not ln.lstrip().startswith('#')]


class TheSplit(unittest.TestCase):
    def test_no_gate_file_passes_the_limit(self):
        for name in FILES:
            with open(os.path.join(SCRIPTS, name), encoding='utf-8') as handle:
                lines = sum(1 for _ in handle)
            self.assertLessEqual(lines, LIMIT, f'{name} has {lines} lines (rule #9: {LIMIT})')

    def test_every_gate_file_is_a_twin(self):
        listed = twins()
        for name in FILES:
            self.assertIn(name, listed, f'{name} is not in twins.txt: a project could keep a stale copy unnoticed')

    def test_every_listed_twin_exists_here(self):
        for name in twins():
            self.assertTrue(os.path.isfile(os.path.join(SCRIPTS, name)), f'twins.txt names {name}, which does not exist')


class ACopyNeedsItsLibraries(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.project = os.path.join(self.tmp, 'project')
        os.makedirs(os.path.join(self.project, 'scripts'))
        subprocess.run(['git', 'init', '-q', self.project], check=True)

    def run_gate(self, *args):
        gate = os.path.join(self.project, 'scripts', 'gate-core.sh')
        return subprocess.run(['bash', gate, *args], cwd=self.project, capture_output=True, text=True)

    def test_the_core_alone_refuses_to_run(self):
        shutil.copy(os.path.join(SCRIPTS, 'gate-core.sh'), os.path.join(self.project, 'scripts'))
        done = self.run_gate('dev', '--list')
        self.assertEqual(2, done.returncode)
        self.assertIn('is missing next to it', done.stderr)
        self.assertNotIn('GATE GREEN', done.stdout)

    def test_each_missing_library_is_named(self):
        for missing in FILES[1:]:
            for name in FILES:
                if name != missing:
                    shutil.copy(os.path.join(SCRIPTS, name), os.path.join(self.project, 'scripts'))
            gate_dir = os.path.join(self.project, 'scripts')
            if os.path.exists(os.path.join(gate_dir, missing)):
                os.remove(os.path.join(gate_dir, missing))
            done = self.run_gate('dev', '--list')
            self.assertEqual(2, done.returncode, missing)
            self.assertIn(missing, done.stderr)
            for name in FILES:
                path = os.path.join(gate_dir, name)
                if os.path.exists(path):
                    os.remove(path)

    def test_all_four_together_run(self):
        for name in FILES:
            shutil.copy(os.path.join(SCRIPTS, name), os.path.join(self.project, 'scripts'))
        done = self.run_gate('dev', '--list')
        self.assertIn('merge gate', done.stdout)
        self.assertIn('── result ──', done.stdout)      # it got all the way to the verdict in gate-lib.sh
        self.assertNotIn('is missing next to it', done.stderr)

    def test_the_core_finds_its_libraries_through_a_relative_path(self):
        for name in FILES:
            shutil.copy(os.path.join(SCRIPTS, name), os.path.join(self.project, 'scripts'))
        done = subprocess.run(['bash', 'scripts/gate-core.sh', 'dev', '--list'], cwd=self.project,
                              capture_output=True, text=True)
        self.assertIn('merge gate', done.stdout)
        self.assertNotIn('is missing next to it', done.stderr)


if __name__ == '__main__':
    unittest.main()
