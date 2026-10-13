"""scripts/md-hook.sh, the CLAUDE.md size ratchet and twin-drift hook of the adyusuf plugin.

It is self-relative: its siblings (md-size-gate.sh, twins.txt and the canonical copies of the twins) are the
files NEXT TO IT, whichever plugin root it runs from. Three fixtures say so:
  PluginRootCopy  - md-hook.sh copied into a throwaway <root>/scripts/ with stub siblings (drift semantics);
  Real*           - the real script by its real path with the real gate and a real budget (what the hook does);
  OldLayout       - a ~/.claude/scripts symlink to the plugin's scripts (an old install still calling it).
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
HOOK = os.path.join(SCRIPTS, 'md-hook.sh')
TWINS = os.path.join(SCRIPTS, 'twins.txt')   # the one list of copied scripts, shared with twin-drift.sh
GATE_LIBS = ('gate-core.sh', 'gate-lib.sh', 'gate-lib-node.sh', 'gate-lib-prod.sh')
EXCEEDED = '#!/usr/bin/env bash\necho "CLAUDE.md  ✗ CEILING EXCEEDED (+4 KB)"\nexit 1\n'
QUIET = '#!/usr/bin/env bash\nexit 0\n'


def write(path, text):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def run_hook(hook, payload, cwd, **env):
    result = subprocess.run(['bash', hook], input=payload, cwd=cwd, env=dict(os.environ, **env),
                            capture_output=True, text=True)
    return result.stdout + result.stderr, result.returncode


class Base(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = os.path.join(self.base, 'home')
        self.project = os.path.join(self.base, 'project')
        os.makedirs(os.path.join(self.home, '.claude'))
        os.makedirs(os.path.join(self.project, 'scripts'))
        subprocess.run(['git', 'init', '-q', self.project], check=True)

    def copy(self, name):
        return os.path.join(self.project, 'scripts', name)

    def edit_of(self, name):
        return json.dumps({'tool_input': {'file_path': os.path.join(self.project, name)}})

    def run_hook(self, payload='{}', hook=HOOK, cwd=None, **env):
        out, code = run_hook(hook, payload, cwd or self.project, HOME=self.home, **env)
        self.assertEqual(code, 0, out)                       # a behavioural warning, never a block
        return out


class PluginRoot(Base):
    """<plugin>/scripts/ holds a COPY of md-hook.sh, a silent stub gate, the real twin list and the canonical twins."""
    def setUp(self):
        super().setUp()
        self.scripts = os.path.join(self.base, 'plugin', 'scripts')
        os.makedirs(self.scripts)
        self.hook = os.path.join(self.scripts, 'md-hook.sh')
        shutil.copy(HOOK, self.hook)
        shutil.copy(TWINS, os.path.join(self.scripts, 'twins.txt'))
        write(self.canonical('md-size-gate.sh'), QUIET)      # the drift tests are not about the budget

    def canonical(self, name):
        return os.path.join(self.scripts, name)

    def stop_event(self, **env):
        return self.run_hook(hook=self.hook, **env)


class PluginRootCopy(PluginRoot):
    def test_an_identical_copy_is_silent(self):
        for path in (self.canonical('gate-core.sh'), self.copy('gate-core.sh')):
            write(path, 'same\n')
        self.assertEqual(self.stop_event(), '')

    def test_every_copied_script_is_compared_not_only_the_md_tools(self):
        names = ('gate-core.sh', 'guard-destructive.sh', 'doc-check.py', 'evidence-block.schema.json',
                 'real-name-check.sh', 'commit-msg.sh')
        for name in names:
            write(self.canonical(name), 'canonical\n')
            write(self.copy(name), 'edited in the project\n')
        output = self.stop_event()
        for name in names:
            self.assertIn(name, output)
        self.assertIn('DRIFTED', output)
        self.assertIn(f'Canonical: the adyusuf plugin\'s scripts/ ({self.scripts}/)', output)

    def test_a_drifted_gate_library_is_reported_like_the_gate_itself(self):
        # gate-core.sh is split over four files; a copy of the core with a stale library is a stale gate.
        for name in GATE_LIBS:
            write(self.canonical(name), 'canonical\n')
            write(self.copy(name), 'canonical\n')
        self.assertEqual(self.stop_event(), '')
        write(self.copy('gate-lib-node.sh'), 'stale\n')
        output = self.stop_event()
        self.assertIn('gate-lib-node.sh', output)
        self.assertNotIn('gate-lib.sh', output)

    def test_a_missing_twin_list_is_announced_not_silently_skipped(self):
        os.remove(self.canonical('twins.txt'))
        write(self.canonical('gate-core.sh'), 'canonical\n')
        write(self.copy('gate-core.sh'), 'edited\n')
        output = self.stop_event()
        self.assertIn('twin list is missing', output)
        self.assertNotIn('DRIFTED', output)           # nothing was compared, and it says so

    def test_a_script_the_project_did_not_copy_is_ignored(self):
        write(self.canonical('gate-core.sh'), 'canonical\n')
        self.assertEqual(self.stop_event(), '')

    def test_a_copy_with_no_canonical_counterpart_is_ignored(self):
        write(self.copy('gate-core.sh'), 'only here\n')
        self.assertEqual(self.stop_event(), '')

    def test_a_file_that_is_not_a_twin_is_ignored(self):
        write(self.canonical('step-stats.py'), 'a\n')
        write(self.copy('step-stats.py'), 'b\n')
        self.assertEqual(self.stop_event(), '')

    def test_the_configuration_repository_itself_is_exempt(self):
        os.makedirs(os.path.join(self.project, 'standards'))
        os.makedirs(os.path.join(self.project, 'modes'))
        write(os.path.join(self.project, 'standards', 'README.md'), 'x')
        write(self.canonical('gate-core.sh'), 'live (prod)\n')
        write(self.copy('gate-core.sh'), 'dev, not yet promoted\n')
        self.assertEqual(self.stop_event(), '')

    def test_the_siblings_are_the_files_next_to_the_script_never_the_ones_under_home(self):
        decoy = os.path.join(self.home, '.claude', 'scripts')
        os.makedirs(decoy)
        write(os.path.join(decoy, 'md-size-gate.sh'), EXCEEDED)
        write(os.path.join(decoy, 'twins.txt'), 'gate-core.sh\n')
        write(os.path.join(decoy, 'gate-core.sh'), 'decoy canonical\n')
        write(self.canonical('gate-core.sh'), 'plugin canonical\n')
        write(self.copy('gate-core.sh'), 'plugin canonical\n')
        self.assertEqual(self.stop_event(), '')          # neither the decoy gate's warning nor drift against the decoy
        write(self.copy('gate-core.sh'), 'decoy canonical\n')
        self.assertIn('gate-core.sh', self.stop_event())  # and the real comparison is against the plugin's copy

    def test_the_twin_list_beside_the_script_is_the_one_read(self):
        write(self.canonical('twins.txt'), '# only these\nmine.sh\n')
        for name in ('mine.sh', 'gate-core.sh'):
            write(self.canonical(name), 'canonical\n')
            write(self.copy(name), 'edited\n')
        output = self.stop_event()
        self.assertIn('mine.sh', output)
        self.assertNotIn('gate-core.sh', output)

    def test_the_gate_beside_the_script_runs_with_the_project_as_its_root(self):
        write(self.canonical('md-size-gate.sh'), '#!/usr/bin/env bash\necho "root=$MD_ROOT ✗ CEILING EXCEEDED"\n')
        output = self.stop_event()
        self.assertIn(f'root={os.path.realpath(self.project)} ✗ CEILING EXCEEDED', output)


class OldLayout(PluginRoot):
    """An old install still calls ~/.claude/scripts/md-hook.sh, a directory symlink into the plugin's scripts/."""
    def setUp(self):
        super().setUp()
        self.via_link = os.path.join(self.home, '.claude', 'scripts')
        os.symlink(self.scripts, self.via_link)

    def test_the_siblings_are_found_through_the_directory_link_and_the_link_path_is_what_is_reported(self):
        write(self.canonical('gate-core.sh'), 'canonical\n')
        write(self.copy('gate-core.sh'), 'edited\n')
        output = self.run_hook(hook=os.path.join(self.via_link, 'md-hook.sh'))
        self.assertIn('DRIFTED', output)
        self.assertIn(f'({self.via_link}/)', output)

    def test_the_gate_behind_the_link_runs_too(self):
        write(self.canonical('md-size-gate.sh'), EXCEEDED)
        output = self.run_hook(hook=os.path.join(self.via_link, 'md-hook.sh'))
        self.assertIn('CEILING EXCEEDED', output)


class RealHook(Base):
    """The real script by its real path, the real size gate and a real budget: what runs in a session."""
    def budget(self, ceiling_kb, claude_md_kb=2, extra=''):
        write(os.path.join(self.project, 'CLAUDE.md'), 'x' * (claude_md_kb * 1024 - 100))
        write(self.copy('md-budget.tsv'), f'CLAUDE.md\t{ceiling_kb}\t{ceiling_kb}\tnote\n{extra}')

    def test_an_edit_to_another_file_is_ignored(self):
        self.budget(1)                                      # over its ceiling: a hook that ran the gate would say so
        self.assertEqual(self.run_hook(self.edit_of('README.md')).strip(), '')

    def test_an_edit_to_CLAUDE_md_runs_the_gate(self):
        self.budget(1)
        out = self.run_hook(self.edit_of('CLAUDE.md'))
        self.assertIn('CEILING EXCEEDED', out)
        self.assertIn('--update', out)

    def test_a_stop_event_also_runs_the_gate(self):
        self.budget(1)
        self.assertIn('CEILING EXCEEDED', self.run_hook('{}'))

    def test_within_budget_is_silent_on_both_events(self):
        self.budget(4)
        for payload in ('{}', self.edit_of('CLAUDE.md')):
            self.assertEqual(self.run_hook(payload).strip(), '', payload)

    def test_a_claude_md_without_a_budget_row_and_a_row_without_a_file_are_both_reported(self):
        self.budget(4, extra='gone/CLAUDE.md\t1\t1\tn\n')
        os.makedirs(os.path.join(self.project, 'web'))
        write(os.path.join(self.project, 'web', 'CLAUDE.md'), 'new\n')
        out = self.run_hook('{}')
        self.assertIn('NO BUDGET', out)
        self.assertIn('FILE MISSING', out)

    def test_no_budget_is_SILENT_on_a_stop_event(self):
        self.assertEqual(self.run_hook('{}').strip(), '', 'suggesting an install every turn is noise')

    def test_no_budget_IS_reported_when_a_CLAUDE_md_was_edited(self):
        self.assertIn('No CLAUDE.md budget is installed', self.run_hook(self.edit_of('CLAUDE.md')))

    def test_the_path_key_is_read_too_and_the_repository_is_the_files_not_the_working_directory(self):
        self.budget(1)
        out = self.run_hook(json.dumps({'tool_input': {'path': os.path.join(self.project, 'CLAUDE.md')}}), cwd=self.base)
        self.assertIn('CEILING EXCEEDED', out)

    def test_unparseable_input_is_a_stop_event_and_does_not_break_the_hook(self):
        self.budget(1)
        self.assertIn('CEILING EXCEEDED', self.run_hook('not json at all'))

    def test_outside_a_repository_it_exits_quietly(self):
        self.budget(1)
        loose = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, loose, True)
        self.assertEqual(self.run_hook('{}', cwd=loose).strip(), '')

    def test_a_copy_that_matches_the_real_script_is_silent_and_an_edited_one_is_drifted(self):
        self.budget(4)
        for name in GATE_LIBS:
            shutil.copy(os.path.join(SCRIPTS, name), self.copy(name))
        self.assertEqual(self.run_hook('{}'), '')
        write(self.copy('gate-lib-prod.sh'), 'stale\n')
        out = self.run_hook('{}')
        self.assertIn('DRIFTED', out)
        self.assertIn('gate-lib-prod.sh', out)
        self.assertNotIn('gate-core.sh', out)

    def test_the_twin_list_can_be_pointed_elsewhere_and_a_missing_one_is_announced(self):
        self.budget(4)
        write(self.copy('gate-core.sh'), 'edited\n')
        out = self.run_hook('{}', TWINS_FILE=os.path.join(self.base, 'no-such-twins.txt'))
        self.assertIn('twin list is missing or empty', out)
        self.assertNotIn('DRIFTED', out)


if __name__ == '__main__':
    unittest.main()
