"""scripts/plugin-setup.py — replacing an older version: the question, the order, and your settings surviving.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plugin_setup_helpers import CONFIG, Case, Fake, OLD, github_market, setup  # noqa: E402


class Replace(Case):
    def fake(self, **kw):
        return Fake(self.home, installed=OLD, market=github_market(), **kw)

    def test_yes_removes_the_old_one_keeping_its_data_then_installs_the_new_one(self):
        self.settings()
        fake = self.fake()
        code, out, _ = self.go(fake, answer='yes')
        self.assertEqual(code, 0)
        order = [c[2] for c in fake.commands if c[1] == 'plugin' and c[2] != 'marketplace']
        self.assertEqual(order, ['uninstall', 'install'])
        self.assertIn(['claude', 'plugin', 'uninstall', setup.PLUGIN_ID, '--keep-data', '--scope', 'user'],
                      fake.commands)
        self.assertIn(['claude', 'plugin', 'marketplace', 'update', setup.MARKETPLACE], fake.commands)
        self.assertIn('✓ settings, enabled state and marketplace link are as they were', out)

    def test_the_settings_file_is_backed_up_and_survives_byte_for_byte(self):
        self.settings()
        self.go(self.fake())
        with open(os.path.join(self.home, '.claude', 'adyusuf.json'), 'rb') as handle:
            self.assertEqual(handle.read(), CONFIG)
        backups = os.listdir(os.path.join(self.home, '.claude-standards', 'backups'))
        self.assertEqual(len(backups), 1)

    def test_a_disturbed_settings_file_is_put_back(self):
        self.settings()
        fake = self.fake()
        fake.wipe = True
        code, out, _ = self.go(fake)
        self.assertEqual(code, 0)
        self.assertIn('restored', out)
        with open(os.path.join(self.home, '.claude', 'adyusuf.json'), 'rb') as handle:
            self.assertEqual(handle.read(), CONFIG)

    def test_a_plugin_that_was_disabled_is_disabled_again(self):
        self.settings(enabled=False)
        fake = self.fake()
        self.go(fake)
        self.assertIn(['claude', 'plugin', 'disable', setup.PLUGIN_ID], fake.commands)

    def test_a_vanished_marketplace_link_is_a_failure(self):
        fake = self.fake()
        original = fake.marketplace

        def vanishing(action):
            if action == 'list' and any(c[2] == 'install' for c in fake.commands):
                return 0, '[]'
            return original(action)
        fake.marketplace = vanishing
        code, out, _ = self.go(fake)
        self.assertEqual(code, 2)
        self.assertIn('the marketplace link is gone', out)

    def test_no_leaves_everything_as_it_is(self):
        fake = self.fake()
        code, out, _ = self.go(fake, answer='')
        self.assertEqual(code, 0)
        self.assertIn('left as it is', out)
        self.assertNotIn('uninstall', [c[2] for c in fake.commands])

    def test_without_a_terminal_it_refuses_to_ask_and_changes_nothing(self):
        fake = self.fake()
        code, out, _ = self.go(fake, tty=False)
        self.assertEqual(code, 2)
        self.assertIn('rerun with --yes', out)
        self.assertNotIn('uninstall', [c[2] for c in fake.commands])

    def test_yes_flag_replaces_without_a_terminal_and_without_asking(self):
        fake = self.fake()
        code, _, _ = self.go(fake, '--yes', tty=False, answer='n')
        self.assertEqual(code, 0)
        self.assertIn('uninstall', [c[2] for c in fake.commands])

    def test_a_failing_refresh_removes_nothing(self):
        fake = self.fake(fail=('claude plugin marketplace update',))
        self.assertEqual(self.go(fake)[0], 2)
        self.assertNotIn('uninstall', [c[2] for c in fake.commands])

    def test_a_failing_removal_installs_nothing(self):
        fake = self.fake(fail=('claude plugin uninstall',))
        self.assertEqual(self.go(fake)[0], 2)
        self.assertNotIn('install', [c[2] for c in fake.commands])

    def test_a_failing_install_after_the_removal_names_the_recovery_command(self):
        code, out, _ = self.go(self.fake(fail=('claude plugin install',)))
        self.assertEqual(code, 2)
        self.assertIn('the old version is removed but the new one failed', out)

    def test_a_project_scope_install_is_replaced_in_the_same_scope(self):
        fake = self.fake()
        fake.write(OLD, scope='project')
        self.go(fake)
        self.assertIn(['claude', 'plugin', 'install', setup.PLUGIN_ID, '--scope', 'project'], fake.commands)


if __name__ == '__main__':
    unittest.main()
