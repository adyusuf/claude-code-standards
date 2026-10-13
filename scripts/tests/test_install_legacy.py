"""install.py — finding and unlinking the OLD linked install (legacy_links, remove_links, unlink, is_checkout).

A link is ours only when it sits at a place the old install used, carries the name it was made with, and either
points into a checkout of this repository or points at nothing. Everything else in ~/.claude is yours.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_install import LINKS, PLUGIN_LINK, Fixture, install  # noqa: E402


class IsCheckout(Fixture):
    def test_both_fingerprint_files_make_a_checkout(self):
        self.assertTrue(install.is_checkout(self.repo))

    def test_one_fingerprint_file_alone_is_not_enough(self):
        for part in install.FINGERPRINT:
            with self.subTest(missing=part):
                folder = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, folder, True)
                other = [p for p in install.FINGERPRINT if p != part][0]
                self.put(os.path.join(folder, other), 'x')
                self.assertFalse(install.is_checkout(folder))


class LegacyLinks(Fixture):
    def foreign_dir(self, name):
        """A folder that is NOT a checkout, holding a child called `name`: a link to it keeps the right name."""
        top = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, top, True)
        os.makedirs(os.path.join(top, name))
        return os.path.join(top, name)

    def test_every_place_the_old_install_used_is_found_with_its_target(self):
        expected = {self.claude(name): self.link_legacy(name) for name in LINKS + (PLUGIN_LINK,)}
        self.assertEqual(dict(install.legacy_links(self.home)), expected)

    def test_a_link_into_something_else_is_kept(self):
        self.link_legacy('docs', self.foreign_dir('docs'))
        self.link_legacy('agents')
        self.assertEqual([link for link, _ in install.legacy_links(self.home)], [self.claude('agents')])

    def test_a_link_into_a_checkout_with_another_name_is_kept(self):
        # The old install made CLAUDE.md -> <checkout>/CLAUDE.md; a link to some other file of the checkout is yours.
        self.link_legacy('CLAUDE.md', os.path.join(self.repo, 'agents', 'qa.md'))
        self.assertEqual(install.legacy_links(self.home), [])

    def test_the_plugin_link_must_point_at_the_plugin_folder(self):
        self.link_legacy(PLUGIN_LINK, os.path.join(self.repo, 'docs'))
        self.assertEqual(install.legacy_links(self.home), [])

    def test_a_dangling_link_with_the_expected_name_is_found(self):
        gone = os.path.join(self.home, 'removed-checkout', 'standards')
        self.link_legacy('standards', gone)
        self.link_legacy(PLUGIN_LINK, os.path.join(self.home, 'removed-checkout', 'plugin'))
        self.assertEqual(sorted(install.legacy_links(self.home)),
                         sorted([(self.claude('standards'), gone),
                                 (self.claude(PLUGIN_LINK), os.path.join(self.home, 'removed-checkout', 'plugin'))]))

    def test_a_dangling_link_with_a_foreign_name_is_kept(self):
        self.link_legacy('standards', os.path.join(self.home, 'removed-checkout', 'my-notes'))
        self.assertEqual(install.legacy_links(self.home), [])

    def test_a_relative_link_resolves_from_the_links_folder(self):
        relative = os.path.relpath(os.path.join(self.repo, 'modes'), self.claude())
        os.symlink(relative, self.claude('modes'))
        self.assertEqual(install.legacy_links(self.home), [(self.claude('modes'), os.path.join(self.repo, 'modes'))])

    def test_a_relative_dangling_link_is_found_and_a_relative_foreign_one_kept(self):
        os.symlink(os.path.join('..', 'gone', 'docs'), self.claude('docs'))
        os.symlink(self.foreign_dir('agents'), self.claude('agents'))
        self.assertEqual([link for link, _ in install.legacy_links(self.home)], [self.claude('docs')])

    def test_a_real_file_or_folder_is_never_found_even_if_it_looks_like_a_checkout(self):
        self.put(self.claude('CLAUDE.md'), 'my own rules\n')
        self.put(self.claude('standards', '00-working-method.md'), 'mine\n')
        self.put(self.claude('modes', 'README.md'), 'mine\n')
        self.assertEqual(install.legacy_links(self.home), [])

    def test_a_home_without_claude_has_none(self):
        shutil.rmtree(self.claude())
        self.assertEqual(install.legacy_links(self.home), [])

    def test_the_windows_extended_prefix_is_dropped_before_the_name_is_compared(self):
        link = self.claude('docs')
        os.symlink('placeholder', link)
        with mock.patch.object(install.os, 'readlink', return_value='\\\\?\\' + os.path.join(self.repo, 'docs')):
            self.assertEqual([found for found, _ in install.legacy_links(self.home)], [link])


class Unlink(Fixture):
    def test_a_link_is_removed_and_its_target_stays(self):
        source = self.link_legacy('agents')
        install.unlink(self.claude('agents'))
        self.assertFalse(os.path.lexists(self.claude('agents')))
        self.assertTrue(os.path.isfile(os.path.join(source, 'qa.md')))

    def test_a_dangling_link_is_removed(self):
        os.symlink(os.path.join(self.home, 'gone'), self.claude('docs'))
        install.unlink(self.claude('docs'))
        self.assertFalse(os.path.lexists(self.claude('docs')))

    def test_when_remove_is_refused_rmdir_takes_a_directory_link_out(self):
        # Windows removes a DIRECTORY symlink with rmdir only.
        with mock.patch.object(install.os, 'remove', side_effect=PermissionError('is a directory link')), \
                mock.patch.object(install.os, 'rmdir') as rmdir:
            install.unlink('some-link')
        rmdir.assert_called_once_with('some-link')

    def test_rmdir_is_not_tried_when_remove_worked(self):
        with mock.patch.object(install.os, 'remove') as remove, mock.patch.object(install.os, 'rmdir') as rmdir:
            install.unlink('some-link')
        remove.assert_called_once_with('some-link')
        rmdir.assert_not_called()


class RemoveLinks(Fixture):
    def run_remove_links(self):
        out = io.StringIO()
        with redirect_stdout(out):
            install.remove_links(self.home)
        return out.getvalue()

    def test_ours_go_foreign_and_real_stay_and_the_checkout_is_untouched(self):
        for name in ('CLAUDE.md', 'agents', 'standards', PLUGIN_LINK):
            self.link_legacy(name)
        foreign = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, foreign, True)
        os.symlink(foreign, self.claude('docs'))                       # not ours: the target has another name
        self.put(self.claude('modes', 'mine.md'), 'mine\n')            # a real folder
        before = self.tree(self.repo)
        out = self.run_remove_links()
        for name in ('CLAUDE.md', 'agents', 'standards', PLUGIN_LINK):
            self.assertFalse(os.path.lexists(self.claude(name)), name)
            self.assertIn(f'unlinked  {self.claude(name)}', out)
        self.assertTrue(os.path.islink(self.claude('docs')))
        self.assertTrue(os.path.isfile(self.claude('modes', 'mine.md')))
        self.assertEqual(self.tree(self.repo), before)

    def test_a_dangling_link_is_taken_out_too(self):
        self.link_legacy('scripts', os.path.join(self.home, 'gone', 'scripts'))
        self.run_remove_links()
        self.assertFalse(os.path.lexists(self.claude('scripts')))

    def test_nothing_to_remove_says_so(self):
        self.assertIn('none      no link of the old install is left', self.run_remove_links())

    def test_running_it_twice_removes_nothing_the_second_time(self):
        self.link_legacy('docs')
        self.run_remove_links()
        self.assertIn('none      ', self.run_remove_links())


if __name__ == '__main__':
    unittest.main()
