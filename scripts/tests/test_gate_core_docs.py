import os
import re
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ANSI = re.compile(r'\x1b\[[0-9;]*m')

# Run the gate from its real path, not a copy — see the note in
# test_gate_core_fixes.py: a copy is invisible to a coverage tracer.
GATE = os.path.join(SCRIPTS, 'gate-core.sh')


def project(files):
    root = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q', root], check=True)
    os.makedirs(os.path.join(root, 'scripts'))
    for name, text in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
    return root


def gate(root, *args):
    result = subprocess.run(['bash', GATE, 'dev', *args], cwd=root, capture_output=True, text=True)
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
        result = subprocess.run(['bash', GATE, 'dev'], cwd=self.root, capture_output=True, text=True)
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


class LiveConfigExemption(unittest.TestCase):
    """~/.claude is exempt from steps 3 (doc-check) and 4 (real names); every other repository is not."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.other = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.other, ignore_errors=True)

    def repo(self, root):
        os.makedirs(root, exist_ok=True)
        subprocess.run(['git', 'init', '-q', root], check=True)
        os.makedirs(os.path.join(root, 'scripts'), exist_ok=True)
        os.makedirs(os.path.join(root, 'docs'), exist_ok=True)
        for name in ('pre-commit.sh', 'doc-check.py', 'real-name-check.sh'):
            shutil.copy(os.path.join(SCRIPTS, name), os.path.join(root, 'scripts', name))
        with open(os.path.join(root, 'docs', 'project-nicknames.tsv'), 'w') as handle:
            handle.write('Zorbexico\tryan\n')
        with open(os.path.join(root, 'notes.md'), 'w') as handle:
            handle.write('a broken [link](missing.md) and the name Zorbexico\n')
        subprocess.run(['git', '-C', root, 'add', 'scripts', 'notes.md'], check=True)
        return root

    def run_hook(self, root):
        return subprocess.run(['bash', os.path.join(root, 'scripts', 'pre-commit.sh')], cwd=root, capture_output=True,
                              text=True, env=dict(os.environ, HOME=self.home))

    def test_the_live_config_repository_is_not_blocked_by_doc_check_or_real_names(self):
        root = self.repo(os.path.join(self.home, '.claude'))
        result = self.run_hook(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('documentation drift', result.stdout)

    def test_the_same_content_in_any_other_repository_is_blocked_by_both_steps(self):
        root = self.repo(os.path.join(self.other, 'proj'))
        result = self.run_hook(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn('documentation drift', result.stdout)
        self.assertIn('real project name', result.stdout + result.stderr)

    def test_a_symlinked_home_directory_is_still_recognised(self):
        real = os.path.join(self.home, 'real-config')
        self.repo(real)
        os.symlink(real, os.path.join(self.home, '.claude'))
        self.assertEqual(self.run_hook(real).returncode, 0)


if __name__ == '__main__':
    unittest.main()
