"""The five gate-core fixes of 21/09/2026, each pinned by a test.

Why this file exists at all: the fixes were written and propagated to the
project copies before any test covered them, and the gate they fix is the thing
that decides whether code may leave for the outside world. Every test here was
checked by reverting its fix and watching the test fail — the list of reverts is
in docs/decision-log.md §25.

The tests use `--list` (the gate's dry mode) wherever they only need to know
WHICH command the gate would run, and they put stub `dotnet`/`npm` executables on
PATH so that `have dotnet` is satisfied without the real toolchains. Nothing is
built and nothing is downloaded.
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ANSI = re.compile(r'\x1b\[[0-9;]*m')

STUB = '#!/bin/sh\nexit 0\n'

# Rule #16 is fail-closed, so a fixture without these two files makes the gate
# CLOSED before it can reach the INCOMPLETE verdict a skip produces. Any test
# that asserts on the verdict has to satisfy #16 first.
RULE_16_DOCS = {
    'SETUP.md': '# Setup\n## Secret and token inventory\n',
    '.env.example': '',
}


def project(files, stubs=('dotnet', 'npm')):
    """A throwaway git repository containing `files`, plus stub toolchains."""
    root = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q', root], check=True)
    os.makedirs(os.path.join(root, 'scripts'), exist_ok=True)
    shutil.copy(os.path.join(SCRIPTS, 'gate-core.sh'), os.path.join(root, 'scripts', 'gate-core.sh'))
    binary_dir = os.path.join(root, '.stubbin')
    os.makedirs(binary_dir)
    for name in stubs:
        path = os.path.join(binary_dir, name)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(STUB)
        os.chmod(path, 0o755)
    for name, text in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
    return root


def gate(root, *args, target='dev'):
    env = dict(os.environ)
    env['PATH'] = os.path.join(root, '.stubbin') + os.pathsep + env['PATH']
    result = subprocess.run(['bash', 'scripts/gate-core.sh', target, *args],
                            cwd=root, capture_output=True, text=True, env=env)
    return ANSI.sub('', result.stdout), result.returncode


def stacks_line(output):
    for line in output.splitlines():
        if line.startswith('stacks:'):
            return line
    return ''


class StackDetection(unittest.TestCase):
    """A miss here is silent and total: the whole tier goes unchecked."""

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def detect(self, files):
        self.root = project(files)
        return stacks_line(gate(self.root, '--list')[0])

    def test_a_solution_at_the_root_is_found(self):
        self.assertIn('dotnet=1', self.detect({'App.sln': ''}))

    def test_the_newer_slnx_format_is_found(self):
        # `ls ./*.sln` did not match `.slnx`, so a repository using the new
        # format had its entire backend skipped while the gate printed green.
        self.assertIn('dotnet=1', self.detect({'App.slnx': ''}))

    def test_a_csproj_below_the_root_is_found(self):
        # `ls ./**/*.csproj` is one level deep without globstar, so a project at
        # src/Api/Api.csproj was invisible.
        self.assertIn('dotnet=1', self.detect({'src/Api/Api.csproj': ''}))

    def test_a_package_json_below_the_root_is_found(self):
        self.assertIn('node=1', self.detect({'web/package.json': '{}'}))

    def test_a_repository_with_neither_stack_detects_neither(self):
        line = self.detect({'README.md': '#\n'})
        self.assertIn('dotnet=0', line)
        self.assertIn('node=0', line)

    def test_obj_and_node_modules_are_not_mistaken_for_a_project(self):
        # Build output must not make the gate think there is a project here.
        line = self.detect({'obj/Debug/Ghost.csproj': '', 'web/node_modules/pkg/package.json': '{}'})
        self.assertIn('dotnet=0', line)
        self.assertIn('node=0', line)


class SolutionIsPassedAsTheTarget(unittest.TestCase):
    """Detecting a project is not enough — `dotnet build` with no argument
    builds the current directory and dies with MSB1003 when the solution is
    below the root, which is how four of five .NET repositories are laid out."""

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def commands(self, files):
        self.root = project(files)
        return gate(self.root, '--list')[0]

    def test_a_nested_solution_becomes_the_dotnet_target(self):
        output = self.commands({'api/App.sln': ''})
        self.assertIn('api/App.sln', stacks_line(output))
        for step in ('dotnet format', 'dotnet build', 'dotnet test'):
            line = [l for l in output.splitlines() if step in l and '→' in l]
            self.assertTrue(line, f'{step} was never planned')
            self.assertIn('api/App.sln', line[0], f'{step} did not receive the solution')

    def test_the_build_still_asks_for_warnings_as_errors(self):
        output = self.commands({'api/App.sln': ''})
        build = [l for l in output.splitlines() if 'dotnet build' in l and '→' in l][0]
        self.assertIn('-warnaserror', build)


class CoverageCannotBeAccepted(unittest.TestCase):
    """Rule #29 grants the coverage threshold no exceptions and says a project
    cannot override it. Several projects had listed `coverage` in ACCEPTED_GAPS
    and their gates printed GREEN while nothing measured coverage at all."""

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    CONF_ACCEPTING_COVERAGE = (
        'ACCEPTED_GAPS="coverage|SAST"\n'
        'ACCEPTED_GAPS_REASON="a reason that looks legitimate"\n'
    )

    def run_gate(self, conf):
        self.root = project({'App.sln': '', 'scripts/merge-gate.conf': conf, **RULE_16_DOCS})
        return gate(self.root)

    def test_listing_coverage_does_not_accept_it(self):
        output, code = self.run_gate(self.CONF_ACCEPTING_COVERAGE)
        self.assertIn('CANNOT be accepted', output)
        self.assertNotIn('ACCEPTED GAP: coverage', output)
        self.assertIn('GATE INCOMPLETE', output)
        self.assertNotEqual(code, 0, 'an unmeasured threshold must not exit 0')

    def test_another_gap_in_the_same_list_is_still_accepted(self):
        # The refusal is targeted: it must not void a legitimate acceptance
        # sitting in the same ACCEPTED_GAPS expression.
        output, _ = self.run_gate(self.CONF_ACCEPTING_COVERAGE)
        self.assertIn('ACCEPTED GAP: SAST', output)

    def test_a_measured_project_passes_the_step_normally(self):
        self.root = project({'App.sln': '',
                             'scripts/merge-gate.conf': 'COVERAGE_CMD="true"\n', **RULE_16_DOCS})
        output, _ = gate(self.root)
        self.assertIn('✓ coverage', output)
        self.assertNotIn('CANNOT be accepted', output)

    def test_a_measurement_below_the_threshold_closes_the_gate(self):
        self.root = project({'App.sln': '',
                             'scripts/merge-gate.conf': 'COVERAGE_CMD="false"\n', **RULE_16_DOCS})
        output, code = gate(self.root)
        self.assertIn('✗ coverage', output)
        self.assertIn('GATE CLOSED', output)
        self.assertNotEqual(code, 0)


class JsTestStep(unittest.TestCase):
    """`npm test -- --run` is vitest's flag. Passed to a project whose test
    script is jest, it reaches jest as an unknown argument and the step fails
    for a reason that has nothing to do with the tests."""

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def planned_test_command(self, test_script):
        self.root = project({
            'web/package.json': '{"scripts": {"test": "%s"}}' % test_script,
        })
        output = gate(self.root, '--list')[0]
        lines = [l for l in output.splitlines() if 'test (web)' in l and '→' in l]
        self.assertTrue(lines, 'the web test step was never planned')
        return lines[0]

    def test_vitest_gets_the_run_flag(self):
        self.assertIn('--run', self.planned_test_command('vitest'))

    def test_jest_does_not_get_the_run_flag(self):
        self.assertNotIn('--run', self.planned_test_command('jest --ci'))

    def test_both_runners_get_ci_in_the_environment(self):
        # CI=true is the setting both runners understand as "single run".
        for script in ('vitest', 'jest --ci'):
            self.assertIn('CI=true', self.planned_test_command(script))


if __name__ == '__main__':
    unittest.main()
