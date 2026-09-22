"""The twin-drift check (scripts/twin-drift.sh).

Rule #25 makes every gate script a deliberate TWIN — canonical here, a committed
copy in each project — and nothing compared them until now. They drifted in BOTH
directions inside one day: the canonical was the stale side in the
morning, the projects were in the evening, and both times it was found by hand.

The two design choices worth pinning, because getting either wrong makes the
check useless in a way that still looks like it is working:

  · it compares the project's COMMITTED origin/dev blob, not its working tree —
    a checkout mid-edit or on a feature branch is work in progress, not drift;
  · with no sibling checkout visible it reports n/a and exits 0. A CI runner has
    none, so failing would make the gate unpassable; claiming "aligned" would be
    a lie. Saying "nothing to compare" is the only honest third answer.
"""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DRIFT = os.path.join(SCRIPTS, 'twin-drift.sh')


def git(cwd, *args, check=True):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=check)


class Fleet(unittest.TestCase):
    """A fake canonical repository with fake sibling projects beside it."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        # The canonical repo is recognised by standards/README.md + modes/, the
        # same signal md-hook.sh uses to exclude it from its own comparison.
        self.canon = os.path.join(self.home, 'config-repo')
        os.makedirs(os.path.join(self.canon, 'scripts'))
        os.makedirs(os.path.join(self.canon, 'standards'))
        os.makedirs(os.path.join(self.canon, 'modes'))
        self.write(self.canon, 'standards/README.md', '# index\n')
        self.write(self.canon, 'scripts/gate-core.sh', '#!/usr/bin/env bash\necho canonical\n')
        shutil.copy(DRIFT, os.path.join(self.canon, 'scripts', 'twin-drift.sh'))
        git(self.canon, 'init', '-q', '.')
        git(self.canon, 'config', 'user.email', 't@t')
        git(self.canon, 'config', 'user.name', 't')
        git(self.canon, 'add', '-A')
        git(self.canon, 'commit', '-qm', 'canonical')

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def write(self, root, relative, text):
        path = os.path.join(root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)

    def project(self, name, gate_body, commit=True, on_branch='dev'):
        """A sibling project whose origin/dev carries `gate_body`."""
        origin = os.path.join(self.home, name + '.git')
        work = os.path.join(self.home, name)
        os.makedirs(os.path.join(work, 'scripts'))
        self.write(work, 'scripts/gate-core.sh', gate_body)
        git(work, 'init', '-q', '-b', on_branch, '.')
        git(work, 'config', 'user.email', 't@t')
        git(work, 'config', 'user.name', 't')
        if commit:
            git(work, 'add', '-A')
            git(work, 'commit', '-qm', 'copy')
        git(self.home, 'init', '-q', '--bare', origin)
        git(work, 'remote', 'add', 'origin', origin)
        if commit:
            git(work, 'push', '-q', 'origin', f'{on_branch}:dev')
            git(work, 'fetch', '-q', 'origin')
        return work

    def run_drift(self, search=None):
        env = dict(os.environ, TWIN_SEARCH_ROOT=search or self.home,
                   TWIN_FILES='gate-core.sh')
        result = subprocess.run(['bash', DRIFT], cwd=self.canon, capture_output=True,
                                text=True, env=env)
        return result.stdout + result.stderr, result.returncode


class Alignment(Fleet):
    def test_an_identical_copy_is_aligned(self):
        self.project('alpha', '#!/usr/bin/env bash\necho canonical\n')
        out, code = self.run_drift()
        self.assertIn('alpha: aligned', out)
        self.assertIn('every copy matches', out)
        self.assertEqual(0, code)

    def test_a_changed_copy_is_reported_and_fails(self):
        self.project('alpha', '#!/usr/bin/env bash\necho STALE\n')
        out, code = self.run_drift()
        self.assertIn('gate-core.sh', out)
        self.assertIn('DRIFTED', out)
        self.assertEqual(1, code)

    def test_it_names_which_project_drifted(self):
        self.project('good', '#!/usr/bin/env bash\necho canonical\n')
        self.project('bad', '#!/usr/bin/env bash\necho STALE\n')
        out, code = self.run_drift()
        self.assertIn('good: aligned', out)
        self.assertRegex(out, r'bad\n\s+✗ gate-core\.sh')
        self.assertEqual(1, code)

    def test_the_canonical_repository_is_not_compared_with_itself(self):
        # It IS the canonical set; comparing would always be trivially aligned and
        # would hide a fleet of zero behind a reassuring line. Its name appears in
        # the header — that is the point of the header — so the assertion is that
        # it is never listed as a COMPARED project.
        self.project('alpha', '#!/usr/bin/env bash\necho canonical\n')
        out, _ = self.run_drift()
        self.assertIn('alpha: aligned', out)
        self.assertNotIn('config-repo: aligned', out)
        self.assertIn('1 project(s)', out)


class WhatCountsAsDrift(Fleet):
    def test_the_committed_blob_decides_not_the_working_tree(self):
        # A project mid-edit is work in progress. Reporting it as drift would make
        # the check cry wolf on every open editor.
        work = self.project('alpha', '#!/usr/bin/env bash\necho canonical\n')
        self.write(work, 'scripts/gate-core.sh', '#!/usr/bin/env bash\necho EDITED\n')
        out, code = self.run_drift()
        self.assertIn('alpha: aligned', out)
        self.assertEqual(0, code)

    def test_a_project_on_a_feature_branch_is_still_judged_by_its_dev(self):
        work = self.project('alpha', '#!/usr/bin/env bash\necho canonical\n')
        git(work, 'checkout', '-q', '-b', 'feature/x')
        self.write(work, 'scripts/gate-core.sh', '#!/usr/bin/env bash\necho WIP\n')
        git(work, 'add', '-A')
        git(work, 'commit', '-qm', 'wip')
        out, code = self.run_drift()
        self.assertIn('alpha: aligned', out)
        self.assertEqual(0, code)

    def test_a_project_that_never_copied_the_file_is_not_drift(self):
        work = os.path.join(self.home, 'nocopy')
        os.makedirs(work)
        git(work, 'init', '-q', '.')
        out, code = self.run_drift()
        self.assertNotIn('nocopy', out)
        self.assertEqual(0, code)


class NothingToCompare(Fleet):
    def test_no_sibling_checkout_is_n_a_and_passes(self):
        empty = tempfile.mkdtemp()
        try:
            out, code = self.run_drift(search=empty)
            self.assertIn('n/a', out)
            self.assertIn('nothing to compare', out)
            self.assertEqual(0, code, 'a CI runner has no fleet; failing would be unpassable')
            self.assertNotIn('every copy matches', out)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_outside_a_repository_it_refuses(self):
        loose = tempfile.mkdtemp()
        try:
            result = subprocess.run(['bash', DRIFT], cwd=loose, capture_output=True, text=True)
            self.assertEqual(2, result.returncode)
        finally:
            shutil.rmtree(loose, ignore_errors=True)


class TheWrapper(unittest.TestCase):
    """scripts/merge-gate.sh — this repository's own orchestrator.

    It was the only repository here without one: all eight projects had a wrapper
    and the canonical set did not, so the extension point #25 describes ("the
    project's own merge-gate.sh stays the orchestrator and CALLS the core") had
    nowhere to put the drift check.

    Two things are pinned. The core's failure must STOP the run — a wrapper that
    carries on past a failed gate turns the gate into a suggestion. And the drift
    check must NOT be able to fail the gate: a CI runner has no sibling
    checkouts, and drift in another project is not a defect in this commit.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, 'scripts'))
        git(self.root, 'init', '-q', '.')
        shutil.copy(os.path.join(SCRIPTS, 'merge-gate.sh'),
                    os.path.join(self.root, 'scripts', 'merge-gate.sh'))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def stub(self, name, body):
        path = os.path.join(self.root, 'scripts', name)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(body)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def run_wrapper(self, target='dev'):
        result = subprocess.run(['bash', 'scripts/merge-gate.sh', target],
                                cwd=self.root, capture_output=True, text=True)
        return result.stdout + result.stderr, result.returncode

    def test_a_failing_core_stops_the_run(self):
        self.stub('gate-core.sh', '#!/usr/bin/env bash\necho "GATE CLOSED"\nexit 1\n')
        self.stub('twin-drift.sh', '#!/usr/bin/env bash\necho "drift ran"\nexit 0\n')
        out, code = self.run_wrapper()
        self.assertEqual(1, code)
        self.assertNotIn('drift ran', out, 'the wrapper continued past a failed gate')

    def test_the_target_is_passed_through_to_the_core(self):
        self.stub('gate-core.sh', '#!/usr/bin/env bash\necho "core got: $1"\n')
        self.stub('twin-drift.sh', '#!/usr/bin/env bash\nexit 0\n')
        out, _ = self.run_wrapper('test')
        self.assertIn('core got: test', out)

    def test_drift_is_reported_but_cannot_fail_the_gate(self):
        self.stub('gate-core.sh', '#!/usr/bin/env bash\necho "GATE GREEN"\n')
        self.stub('twin-drift.sh', '#!/usr/bin/env bash\necho "DRIFTED"\nexit 1\n')
        out, code = self.run_wrapper()
        self.assertIn('DRIFTED', out)
        self.assertIn('not fatal', out)
        self.assertEqual(0, code, 'drift in another project is not a defect in this commit')

    def test_a_clean_run_says_nothing_extra(self):
        self.stub('gate-core.sh', '#!/usr/bin/env bash\necho "GATE GREEN"\n')
        self.stub('twin-drift.sh', '#!/usr/bin/env bash\necho "every copy matches"\n')
        out, code = self.run_wrapper()
        self.assertEqual(0, code)
        self.assertNotIn('not fatal', out)


if __name__ == '__main__':
    unittest.main()
