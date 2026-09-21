import os
import re
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


def project(files):
    root = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q', root], check=True)
    os.makedirs(os.path.join(root, 'scripts'))
    for name in ('gate-core.sh',):
        shutil.copy(os.path.join(SCRIPTS, name), os.path.join(root, 'scripts', name))
    for name, text in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
    return root


def gate(root, *args):
    result = subprocess.run(['bash', 'scripts/gate-core.sh', 'dev', *args], cwd=root, capture_output=True, text=True)
    return ANSI.sub('', result.stdout)


def docs_section(output):
    """The lines of the 'project documents' step only."""
    match = re.search(r'▶ project documents[^\n]*\n(.*?)\n▶ ', output, re.S)
    return match.group(1) if match else ''


class ProjectDocumentsStep(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def run_case(self, files):
        self.root = project(files)
        return docs_section(gate(self.root))

    def test_missing_setup_and_env_example_fail(self):
        section = self.run_case({'package.json': '{}'})
        self.assertIn('✗ SETUP.md is missing', section)
        self.assertIn('✗ .env.example is missing', section)

    def test_setup_without_an_inventory_heading_fails(self):
        section = self.run_case({'package.json': '{}', 'SETUP.md': '# Setup\n## Steps\n', '.env.example': ''})
        self.assertIn('✓ SETUP.md', section)
        self.assertIn('✓ .env.example', section)
        self.assertIn('✗ SETUP.md has no secret/token inventory heading', section)

    def test_a_complete_set_passes_every_check(self):
        section = self.run_case({'package.json': '{}', '.env.example': '',
                                 'SETUP.md': '# Setup\n## 3. Secret and token inventory\n'})
        self.assertEqual(section.count('✓'), 3)
        self.assertNotIn('✗', section)

    def test_a_repository_with_no_stack_at_its_root_is_not_applicable_and_not_a_gap(self):
        self.root = project({'README.md': 'x'})
        output = gate(self.root)
        self.assertIn('n/a: project documents', output)
        self.assertNotIn('SKIPPED project documents', output)

    def test_a_missing_document_closes_the_gate(self):
        self.root = project({'package.json': '{}'})
        result = subprocess.run(['bash', 'scripts/gate-core.sh', 'dev'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('GATE CLOSED', ANSI.sub('', result.stdout))

    def test_list_mode_names_the_step_and_runs_nothing(self):
        self.root = project({'package.json': '{}'})
        output = gate(self.root, '--list')
        self.assertIn('SETUP.md, .env.example, secret inventory', output)
        self.assertNotIn('✗', output)


class PreCommitDocCheck(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        subprocess.run(['git', 'init', '-q', self.root], check=True)
        os.makedirs(os.path.join(self.root, 'scripts'))
        for name in ('pre-commit.sh', 'doc-check.py'):
            shutil.copy(os.path.join(SCRIPTS, name), os.path.join(self.root, 'scripts', name))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def commit_gate(self, files):
        for name, text in files.items():
            with open(os.path.join(self.root, name), 'w', encoding='utf-8') as handle:
                handle.write(text)
        return subprocess.run(['bash', 'scripts/pre-commit.sh'], cwd=self.root, capture_output=True, text=True)

    def test_consistent_documentation_lets_the_commit_through(self):
        self.assertEqual(self.commit_gate({'a.md': 'see [b](b.md)', 'b.md': 'x'}).returncode, 0)

    def test_a_broken_link_stops_the_commit(self):
        result = self.commit_gate({'a.md': 'see [gone](missing.md)'})
        self.assertEqual(result.returncode, 1)
        self.assertIn('documentation drift', result.stdout)
        self.assertIn('broken link -> missing.md', result.stdout)

    def test_without_the_script_the_step_is_skipped(self):
        os.remove(os.path.join(self.root, 'scripts', 'doc-check.py'))
        self.assertEqual(self.commit_gate({'a.md': 'see [gone](missing.md)'}).returncode, 0)


if __name__ == '__main__':
    unittest.main()
