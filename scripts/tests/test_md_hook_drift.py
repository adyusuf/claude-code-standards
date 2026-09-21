import json
import os
import shutil
import subprocess
import tempfile
import unittest

HOOK = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'md-hook.sh'))


class MdHookDrift(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.project = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.home, '.claude', 'scripts'))
        os.makedirs(os.path.join(self.project, 'scripts'))
        subprocess.run(['git', 'init', '-q', self.project], check=True)
        # The hook calls the canonical size gate first; a silent stub keeps this test about drift only.
        self.write(self.canonical('md-size-gate.sh'), '#!/usr/bin/env bash\nexit 0\n')

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.project, ignore_errors=True)

    def canonical(self, name):
        return os.path.join(self.home, '.claude', 'scripts', name)

    def copy(self, name):
        return os.path.join(self.project, 'scripts', name)

    def write(self, path, text):
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)

    def stop_event(self):
        env = dict(os.environ, HOME=self.home)
        result = subprocess.run(['bash', HOOK], input='{}', cwd=self.project, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)           # a behavioural warning, never a block
        return result.stdout

    def test_an_identical_copy_is_silent(self):
        for path in (self.canonical('gate-core.sh'), self.copy('gate-core.sh')):
            self.write(path, 'same\n')
        self.assertEqual(self.stop_event(), '')

    def test_every_copied_script_is_compared_not_only_the_md_tools(self):
        for name in ('gate-core.sh', 'guard-destructive.sh', 'doc-check.py', 'evidence-block.schema.json', 'real-name-check.sh',
                     'commit-msg.sh'):
            self.write(self.canonical(name), 'canonical\n')
            self.write(self.copy(name), 'edited in the project\n')
        output = self.stop_event()
        for name in ('gate-core.sh', 'guard-destructive.sh', 'doc-check.py', 'evidence-block.schema.json', 'real-name-check.sh',
                     'commit-msg.sh'):
            self.assertIn(name, output)
        self.assertIn('DRIFTED', output)

    def test_a_script_the_project_did_not_copy_is_ignored(self):
        self.write(self.canonical('gate-core.sh'), 'canonical\n')
        self.assertEqual(self.stop_event(), '')

    def test_a_copy_with_no_canonical_counterpart_is_ignored(self):
        self.write(self.copy('gate-core.sh'), 'only here\n')
        self.assertEqual(self.stop_event(), '')

    def test_a_file_that_is_not_a_twin_is_ignored(self):
        self.write(self.canonical('step-stats.py'), 'a\n')
        self.write(self.copy('step-stats.py'), 'b\n')
        self.assertEqual(self.stop_event(), '')

    def test_the_configuration_repository_itself_is_exempt(self):
        os.makedirs(os.path.join(self.project, 'standards'))
        os.makedirs(os.path.join(self.project, 'modes'))
        self.write(os.path.join(self.project, 'standards', 'README.md'), 'x')
        self.write(self.canonical('gate-core.sh'), 'live (prod)\n')
        self.write(self.copy('gate-core.sh'), 'dev, not yet promoted\n')
        self.assertEqual(self.stop_event(), '')


class MdHookPathsAndBudget(unittest.TestCase):
    """The hook's other half: which call it reacts to, and what it says about the
    budget. Only the drift comparison was covered before.

    The asymmetry pinned here is deliberate and easy to lose: when no budget is
    installed the hook stays SILENT on a Stop event (suggesting an install every
    turn is noise) but says it ONCE when a CLAUDE.md was explicitly edited.
    """

    BUDGET_ABSENT = ('#!/usr/bin/env bash\n'
                     'echo "· No CLAUDE.md budget is installed in this project (md-budget.tsv is missing)."\n'
                     'exit 0\n')
    BUDGET_EXCEEDED = ('#!/usr/bin/env bash\n'
                       'echo "CLAUDE.md  ✗ CEILING EXCEEDED (+4 KB)"\n'
                       'exit 1\n')

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.project = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.home, '.claude', 'scripts'))
        os.makedirs(os.path.join(self.project, 'scripts'))
        subprocess.run(['git', 'init', '-q', self.project], check=True)

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.project, ignore_errors=True)

    def size_gate(self, body):
        path = os.path.join(self.home, '.claude', 'scripts', 'md-size-gate.sh')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(body)

    def run_hook(self, payload, cwd=None):
        env = dict(os.environ, HOME=self.home)
        result = subprocess.run(['bash', HOOK], input=payload, cwd=cwd or self.project,
                                env=env, capture_output=True, text=True)
        return result.stdout + result.stderr, result.returncode

    def edit_of(self, name):
        return json.dumps({'tool_input': {'file_path': os.path.join(self.project, name)}})

    def test_an_edit_to_another_file_is_ignored(self):
        # The hook must not run the gate for every file write.
        self.size_gate(self.BUDGET_EXCEEDED)
        out, code = self.run_hook(self.edit_of('README.md'))
        self.assertEqual(0, code)
        self.assertEqual('', out.strip())

    def test_an_edit_to_CLAUDE_md_runs_the_gate(self):
        self.size_gate(self.BUDGET_EXCEEDED)
        out, code = self.run_hook(self.edit_of('CLAUDE.md'))
        self.assertEqual(0, code, 'a behavioural warning must never block')
        self.assertIn('CEILING EXCEEDED', out)
        self.assertIn('--update', out)

    def test_a_stop_event_also_runs_the_gate(self):
        self.size_gate(self.BUDGET_EXCEEDED)
        out, code = self.run_hook('{}')
        self.assertEqual(0, code)
        self.assertIn('CEILING EXCEEDED', out)

    def test_no_budget_is_SILENT_on_a_stop_event(self):
        self.size_gate(self.BUDGET_ABSENT)
        out, _ = self.run_hook('{}')
        self.assertEqual('', out.strip(), 'suggesting an install every turn is noise')

    def test_no_budget_IS_reported_when_a_CLAUDE_md_was_edited(self):
        self.size_gate(self.BUDGET_ABSENT)
        out, _ = self.run_hook(self.edit_of('CLAUDE.md'))
        self.assertIn('No CLAUDE.md budget is installed', out)

    def test_unparseable_input_does_not_break_the_hook(self):
        self.size_gate('#!/usr/bin/env bash\nexit 0\n')
        out, code = self.run_hook('not json at all')
        self.assertEqual(0, code)

    def test_outside_a_repository_it_exits_quietly(self):
        self.size_gate(self.BUDGET_EXCEEDED)
        loose = tempfile.mkdtemp()
        try:
            out, code = self.run_hook('{}', cwd=loose)
            self.assertEqual(0, code)
            self.assertEqual('', out.strip())
        finally:
            shutil.rmtree(loose, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
