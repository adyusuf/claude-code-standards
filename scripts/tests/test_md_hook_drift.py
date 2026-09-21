import os
import shutil
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'md-hook.sh')


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


if __name__ == '__main__':
    unittest.main()
