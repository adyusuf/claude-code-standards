"""Shared fixtures of the md-size-gate tests (test_md_size_gate.py: the gate and --update;
test_md_size_gate_init.py and test_md_size_gate_init_guards.py: --init).
Not a test module itself: the discover pattern is test_*.py."""
import datetime
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GATE = os.path.join(SCRIPTS, 'md-size-gate.sh')


def kb_of(text):
    """What the gate will report for this content: CR excluded, rounded up."""
    raw = text.encode()
    return (len(raw) - raw.count(b'\r') + 1023) // 1024


class Gate(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, relative, text):
        path = os.path.join(self.root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
        return path

    def budget(self, *lines):
        return self.write('scripts/md-budget.tsv', ''.join(l + '\n' for l in lines))

    def run_gate(self, *args, budget=None):
        env = dict(os.environ, MD_ROOT=self.root)
        if budget:
            env['MD_BUDGET'] = budget
        result = subprocess.run(['bash', GATE, *args], capture_output=True, text=True, env=env)
        return result.stdout + result.stderr, result.returncode


def today_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y')


class Init(Gate):
    """`--init`: a project adopting the gate has no budget.

    Copying this repository's md-budget.tsv and running `--update` failed
    ("No budget file") or, with the file copied, left the project's own CLAUDE.md
    files "NO BUDGET" — `--update` only lowers rows that already exist. `--init`
    writes a fresh budget: one row per CLAUDE.md, ceiling = target = today's size.
    """

    def budget_path(self):
        return os.path.join(self.root, 'scripts', 'md-budget.tsv')

    def rows(self, path=None):
        """The data rows of the written budget, as (path, ceiling, target, note)."""
        with open(path or self.budget_path(), encoding='utf-8', newline='') as handle:
            lines = handle.read().split('\n')
        return [tuple(l.split('\t')) for l in lines if l and not l.startswith('#')]

    def read_bytes(self, path):
        with open(path, 'rb') as handle:
            return handle.read()
