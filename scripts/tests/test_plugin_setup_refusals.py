"""scripts/plugin-setup.py — what it refuses to do, and its small helpers.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plugin_setup_helpers import Case, Fake, NEW, OLD, github_market, setup  # noqa: E402


class Refusals(Case):
    def test_github_not_answering_changes_nothing(self):
        fake = Fake(self.home, installed=OLD, market=github_market(), fail=('git',))
        code, out, _ = self.go(fake)
        self.assertEqual(code, 2)
        self.assertIn('GitHub did not answer', out)
        self.assertEqual(fake.verbs(), ['claude plugin marketplace', 'git'])

    def test_an_answer_that_is_not_a_commit_is_not_trusted(self):
        fake = Fake(self.home, remote='not-a-sha', market=github_market())
        self.assertEqual(self.go(fake)[0], 2)

    def test_an_unreadable_marketplace_list_stops_before_anything_else(self):
        fake = Fake(self.home, fail=('claude plugin marketplace list',))
        code, out, _ = self.go(fake)
        self.assertEqual(code, 2)
        self.assertIn('cannot read the marketplace list', out)
        self.assertEqual(fake.verbs(), ['claude plugin marketplace'])

    def test_a_marketplace_list_that_is_not_json_is_not_guessed_at(self):
        fake = Fake(self.home)
        fake.marketplace = lambda action: (0, 'oops')
        self.assertEqual(self.go(fake)[0], 2)

    def test_a_marketplace_with_our_name_from_a_local_folder_is_left_alone(self):
        fake = Fake(self.home, installed=OLD, market=github_market(source='directory'))
        code, out, _ = self.go(fake)
        self.assertEqual(code, 2)
        self.assertIn('not GitHub', out)

    def test_a_bad_ref_never_reaches_a_command(self):
        fake = Fake(self.home)
        for ref in ('--upload-pack=x', 'a b', ''):
            code, _, err = self.go(fake, f'--ref={ref}')
            self.assertEqual(code, 2)
            self.assertIn('not a branch name', err)
        self.assertEqual(fake.commands, [])

    def test_missing_tools_stop_the_run_before_any_command(self):
        fake = Fake(self.home)
        code, _, err = self.go(fake, which=lambda tool: None if tool == 'claude' else '/bin/git')
        self.assertEqual(code, 2)
        self.assertIn('claude is not on PATH', err)
        self.assertEqual(fake.commands, [])

    def test_another_branch_is_used_only_while_no_marketplace_is_linked(self):
        fake = Fake(self.home)
        self.go(fake, '--ref', 'test')
        self.assertIn(['claude', 'plugin', 'marketplace', 'add', f'{setup.REPO}#test'], fake.commands)

    def test_an_existing_link_keeps_its_branch_and_the_run_says_so(self):
        fake = Fake(self.home, installed=NEW, market=github_market(ref='dev'))
        _, out, _ = self.go(fake, '--ref', 'test')
        self.assertIn('already linked to "dev"', out)

    def test_a_link_without_a_ref_follows_the_default_branch(self):
        market = github_market()
        del market['ref']
        fake = Fake(self.home, installed=NEW, market=market)
        self.assertEqual(self.go(fake)[0], 0)
        self.assertIn(['git', 'ls-remote', setup.GIT_URL, 'HEAD'], fake.commands)


class Helpers(unittest.TestCase):
    def test_run_reports_a_missing_program_as_exit_127(self):
        code, out = setup.run(['/nonexistent/definitely-not-here'])
        self.assertEqual(code, 127)
        self.assertTrue(out)

    def test_run_returns_the_exit_code_and_both_streams(self):
        code, out = setup.run([sys.executable, '-c', 'import sys; print("a"); print("b", file=sys.stderr); sys.exit(3)'])
        self.assertEqual((code, out.split()), (3, ['a', 'b']))

    def test_run_never_lets_git_prompt(self):
        code, out = setup.run([sys.executable, '-c', 'import os; print(os.environ["GIT_TERMINAL_PROMPT"])'])
        self.assertEqual(out, '0')

    def test_read_json_of_a_missing_or_broken_file_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = os.path.join(tmp, 'x.json')
            with open(broken, 'w', encoding='utf-8') as handle:
                handle.write('{')
            self.assertIsNone(setup.read_json(broken))
            self.assertIsNone(setup.read_json(os.path.join(tmp, 'missing.json')))

    def test_installed_entry_of_a_missing_or_foreign_record_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(setup.installed_entry(tmp))
            folder = os.path.join(tmp, '.claude', 'plugins')
            os.makedirs(folder)
            with open(os.path.join(folder, 'installed_plugins.json'), 'w', encoding='utf-8') as handle:
                json.dump({'plugins': {'other@x': [{'scope': 'user'}]}}, handle)
            self.assertIsNone(setup.installed_entry(tmp))

    def test_the_user_scope_entry_wins_over_a_project_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, '.claude', 'plugins')
            os.makedirs(folder)
            entries = [{'scope': 'project', 'version': 'p' * 12}, {'scope': 'user', 'version': 'u' * 12}]
            with open(os.path.join(folder, 'installed_plugins.json'), 'w', encoding='utf-8') as handle:
                json.dump({'plugins': {setup.PLUGIN_ID: entries}}, handle)
            self.assertEqual(setup.installed_entry(tmp)['version'], 'u' * 12)

    def test_a_too_short_version_never_counts_as_current(self):
        self.assertFalse(setup.is_current({'sha': '', 'version': 'a'}, NEW))
        self.assertFalse(setup.is_current({'sha': '', 'version': ''}, NEW))

    def test_main_builds_its_own_context_when_none_is_given(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(setup, 'run', side_effect=lambda c: (1, 'x')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--home', tmp, '--check']), 2)

    def test_nothing_but_github_is_named_as_a_server(self):
        with open(setup.__file__, encoding='utf-8') as handle:
            text = handle.read()
        self.assertEqual(sorted(set(__import__('re').findall(r'https?://[^/\s\'"]+', text))), ['https://github.com'])


if __name__ == '__main__':
    unittest.main()
