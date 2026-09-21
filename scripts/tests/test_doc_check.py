import importlib.util
import os
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('doc_check', os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'doc-check.py')))
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)

RULES = "1. **One.** text\n2. **Two.** text\n21-23. **[Delegated]** text\n33. **Last.** text\n"


def build(files):
    root = tempfile.mkdtemp()
    for name, text in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
    return root


def consistent():
    return {
        'CLAUDE.md': RULES,
        'README.md': '| Rules | `CLAUDE.md` | 33 rules |\n| Standards | `standards/` | 2 documents + 1 templates |\n| Roles | `agents/` | 1 roles |\n| Scripts | `scripts/` | 2 scripts |\n| Modes | `modes/` | 1 modes |\n',
        'standards/00-a.md': 'see [b](01-b.md) and `standards/01-b.md`, rule #33',
        'standards/01-b.md': 'x',
        'standards/README.md': '| `00-a.md` | a |\n| `01-b.md` | b |\n',
        'standards/templates/t.md': 'x',
        'agents/qa.md': 'x',
        'scripts/a.sh': 'x',
        'scripts/b.py': 'x',
        'scripts/tests/t.py': 'x',
        'modes/A-skill.md': 'x',
        'modes/README.md': '[A](A-skill.md)',
    }


class DocCheck(unittest.TestCase):
    def test_a_consistent_tree_has_no_findings(self):
        self.assertEqual(dc.run(build(consistent())), [])

    def test_a_broken_relative_link_is_found(self):
        files = consistent()
        files['standards/00-a.md'] += ' [gone](02-missing.md)'
        self.assertIn('standards/00-a.md: broken link -> 02-missing.md', dc.run(build(files)))

    def test_links_inside_a_code_fence_and_external_ones_are_ignored(self):
        files = consistent()
        files['standards/00-a.md'] += '\n```\n[x](nowhere.md)\n```\n[web](https://example.org/x.md) [top](#section)'
        self.assertEqual(dc.run(build(files)), [])

    def test_a_referenced_path_that_does_not_exist_is_found(self):
        files = consistent()
        files['CLAUDE.md'] += 'see `docs/decision-log.md`'
        self.assertIn('CLAUDE.md: referenced path does not exist -> docs/decision-log.md', dc.run(build(files)))

    def test_docs_paths_inside_standards_name_a_project_file_and_are_not_checked(self):
        files = consistent()
        files['standards/00-a.md'] += ' `docs/glossary.md`'
        self.assertEqual(dc.run(build(files)), [])

    def test_an_unlisted_document_is_found(self):
        files = consistent()
        files['standards/02-c.md'] = 'x'
        files['README.md'] = files['README.md'].replace('2 documents', '3 documents')
        self.assertEqual(dc.run(build(files)), ['standards/README.md: does not list 02-c.md'])

    def test_a_stale_count_is_found_for_each_claim(self):
        files = consistent()
        files['README.md'] = '| a | b | 30 rules |\n| c | d | 9 documents + 4 templates |\n| e | f | 5 roles |\n'
        found = dc.run(build(files))
        self.assertEqual(sorted(f.split(': ')[1] for f in found), [
            'states 30 rules, the repository has 33', 'states 4 templates, the repository has 1',
            'states 5 agent roles, the repository has 1', 'states 9 standards documents, the repository has 2'])

    def test_a_rule_reference_past_the_last_rule_is_found(self):
        files = consistent()
        files['agents/qa.md'] = 'per rule #34 and issue-like &#39; and rule #7'
        self.assertEqual(dc.run(build(files)), ['agents/qa.md: refers to rule #34, but the last rule is #33'])

    def test_rule_range_counts_its_upper_bound(self):
        files = consistent()
        files['CLAUDE.md'] = '1. **One.**\n21-23. **[Delegated]**\n'
        files['standards/00-a.md'] = 'see [b](01-b.md)'
        files['README.md'] = '| a | b | 23 rules |\n'
        self.assertEqual(dc.run(build(files)), [])

    def test_stale_scripts_and_modes_claims_are_found_and_nested_test_files_do_not_count(self):
        files = consistent()
        files['README.md'] = files['README.md'].replace('2 scripts', '3 scripts').replace('1 modes', '5 modes')
        found = dc.run(build(files))
        self.assertEqual(sorted(f.split(': ')[1] for f in found), [
            'states 3 scripts, the repository has 2', 'states 5 modes, the repository has 1'])

    def test_home_config_references_are_only_checked_in_the_configuration_repository(self):
        project = {'CLAUDE.md': 'see `~/.claude/standards/15-security.md` and `docs/glossary.md`'}
        self.assertEqual(dc.run(build(project)), ['CLAUDE.md: referenced path does not exist -> docs/glossary.md'])
        files = consistent()
        files['CLAUDE.md'] += 'see `~/.claude/modes/autonomous-run.md`'
        self.assertEqual(dc.run(build(files)),
                         ['CLAUDE.md: referenced path does not exist -> modes/autonomous-run.md'])

    def test_a_missing_path_that_git_ignores_is_a_local_file_not_a_broken_reference(self):
        files = consistent()
        files['.gitignore'] = 'docs/local-ledger.tsv\n'
        files['CLAUDE.md'] += ' see `docs/local-ledger.tsv` and [it](docs/local-ledger.tsv)'
        root = build(files)
        subprocess.run(['git', 'init', '-q', root], check=True)
        self.assertEqual(dc.run(root), [])

    def test_a_missing_path_that_git_does_not_ignore_is_still_found(self):
        files = consistent()
        files['.gitignore'] = 'docs/other.tsv\n'
        files['CLAUDE.md'] += ' see `docs/local-ledger.tsv`'
        root = build(files)
        subprocess.run(['git', 'init', '-q', root], check=True)
        self.assertEqual(dc.run(root), ['CLAUDE.md: referenced path does not exist -> docs/local-ledger.tsv'])

    def test_inside_a_git_repository_a_markdown_file_in_an_ignored_tree_is_never_read(self):
        files = consistent()
        files['.gitignore'] = 'plugins/\n'
        files['plugins/cache/x/README.md'] = 'see [gone](nowhere.md) and `docs/missing.md`'
        root = build(files)
        subprocess.run(['git', 'init', '-q', root], check=True)
        self.assertEqual(dc.run(root), [])

    def test_inside_a_git_repository_a_new_unstaged_file_is_still_checked(self):
        files = consistent()
        files['notes.md'] = 'see [gone](nowhere.md)'
        root = build(files)
        subprocess.run(['git', 'init', '-q', root], check=True)
        self.assertEqual(dc.run(root), ['notes.md: broken link -> nowhere.md'])

    def test_a_tracked_file_deleted_from_disk_is_not_read_and_does_not_crash(self):
        files = consistent()
        files['gone.md'] = 'see [missing](nowhere.md)'
        root = build(files)
        subprocess.run(['git', 'init', '-q', root], check=True)
        subprocess.run(['git', '-C', root, 'add', '-A'], check=True)
        os.remove(os.path.join(root, 'gone.md'))
        self.assertEqual(dc.run(root), [])


if __name__ == '__main__':
    unittest.main()
