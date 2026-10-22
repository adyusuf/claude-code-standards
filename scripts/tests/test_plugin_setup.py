"""scripts/plugin-setup.py — a fresh install, an already-current plugin and --check (every external command faked).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plugin_setup_helpers import Case, Fake, NEW, OLD, github_market, setup  # noqa: E402


class FreshInstall(Case):
    def test_without_the_plugin_or_the_link_it_links_the_marketplace_then_installs(self):
        fake = Fake(self.home)
        code, out, _ = self.go(fake)
        self.assertEqual(code, 0)
        self.assertEqual(fake.verbs(), ['claude plugin marketplace', 'git', 'claude plugin marketplace',
                                        'claude plugin install'])
        self.assertIn(['claude', 'plugin', 'marketplace', 'add', f'{setup.REPO}#prod'], fake.commands)
        self.assertIn('✓ adyusuf@adyusuf-marketplace', out)
        self.assertEqual(len(self.logs()), 1)

    def test_with_the_link_already_there_it_refreshes_it_instead_of_adding_it_again(self):
        fake = Fake(self.home, market=github_market())
        self.assertEqual(self.go(fake)[0], 0)
        self.assertNotIn('add', [c[3] for c in fake.commands if c[:3] == ['claude', 'plugin', 'marketplace']])
        self.assertIn(['claude', 'plugin', 'marketplace', 'update', setup.MARKETPLACE], fake.commands)

    def test_a_failing_install_is_exit_two_with_the_retry_command(self):
        code, out, _ = self.go(Fake(self.home, fail=('claude plugin install',)))
        self.assertEqual(code, 2)
        self.assertIn('retry: claude plugin install', out)

    def test_a_failing_marketplace_add_installs_nothing(self):
        fake = Fake(self.home, fail=('claude plugin marketplace add',))
        self.assertEqual(self.go(fake)[0], 2)
        self.assertNotIn('install', [c[2] for c in fake.commands])

    def test_an_install_that_leaves_the_old_commit_is_reported_not_passed(self):
        code, out, _ = self.go(Fake(self.home, stale=True))
        self.assertEqual(code, 2)
        self.assertIn('✗ the plugin is not at', out)


class AlreadyCurrent(Case):
    def test_the_newest_version_changes_nothing(self):
        fake = Fake(self.home, installed=NEW, market=github_market())
        code, out, _ = self.go(fake)
        self.assertEqual(code, 0)
        self.assertIn('✓ the installed plugin is the newest', out)
        self.assertEqual(fake.verbs(), ['claude plugin marketplace', 'git'])

    def test_the_newest_version_without_its_link_gets_the_link_back(self):
        fake = Fake(self.home, installed=NEW)
        self.assertEqual(self.go(fake)[0], 0)
        self.assertIn(['claude', 'plugin', 'marketplace', 'add', f'{setup.REPO}#prod'], fake.commands)

    def test_the_short_version_alone_is_enough_to_recognise_the_commit(self):
        fake = Fake(self.home, installed=NEW, market=github_market())
        with open(fake.record, 'w', encoding='utf-8') as handle:
            json.dump({'plugins': {setup.PLUGIN_ID: {'version': NEW[:12]}}}, handle)    # a dict, not a list
        self.assertIn('✓ the installed plugin is the newest', self.go(fake)[1])


class CheckOnly(Case):
    def test_check_reports_a_due_update_with_exit_one_and_changes_nothing(self):
        fake = Fake(self.home, installed=OLD, market=github_market())
        code, out, _ = self.go(fake, '--check')
        self.assertEqual(code, 1)
        self.assertIn('! a new version is due', out)
        self.assertEqual(fake.verbs(), ['claude plugin marketplace', 'git'])
        self.assertEqual(self.logs(), [])

    def test_check_reports_a_missing_plugin_with_exit_one(self):
        code, out, _ = self.go(Fake(self.home, market=github_market()), '--check')
        self.assertEqual((code, '! the plugin is not installed' in out), (1, True))

    def test_check_on_the_newest_version_is_exit_zero(self):
        self.assertEqual(self.go(Fake(self.home, installed=NEW, market=github_market()), '--check')[0], 0)

    def test_check_on_the_newest_version_without_its_link_is_exit_one_and_adds_nothing(self):
        fake = Fake(self.home, installed=NEW)
        self.assertEqual(self.go(fake, '--check')[0], 1)
        self.assertNotIn('add', [c[3] for c in fake.commands if c[:3] == ['claude', 'plugin', 'marketplace']])


if __name__ == '__main__':
    unittest.main()
