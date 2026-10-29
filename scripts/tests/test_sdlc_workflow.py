"""The shared SDLC workflow (.github/workflows/sdlc.yml) and the caller template.

User decision 29/10/2026: every project's CI is this one file, steered by the panel's settings committed in the
project (.claude/sdlc-settings.json). The workflow cannot run here (hosted runners are off while the account's
payments fail, and a workflow is not unit-testable), so what is pinned is:

  · actionlint passes (skipped, and said so, when actionlint is not installed);
  · the `plan` step - the one place the panel's settings change what CI does - is run for real as a script: CI off
    for a branch gives ci=false, on gives ci=true, a missing settings file FAILS CLOSED (the checks run);
  · a fork's pull request is kept off the runners, every third-party action is pinned to a commit SHA, and the
    caller template pins the standards the same way.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
WORKFLOW = os.path.join(ROOT, '.github', 'workflows', 'sdlc.yml')
CALLER = os.path.join(ROOT, 'standards', 'templates', 'sdlc-caller.yml')


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def plan_script():
    """The `run:` block of the step with `id: read` (indentation stripped)."""
    lines = read(WORKFLOW).splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == '- id: read')
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == 'run: |')
    body = []
    for line in lines[run + 1:]:
        if line.strip() and not line.startswith(' ' * 10):
            break
        body.append(line[10:])
    return '\n'.join(body)


class Workflow(unittest.TestCase):
    def test_actionlint_is_clean(self):
        if shutil.which('actionlint') is None:
            self.skipTest('actionlint is not installed - the workflow was NOT linted')
        done = subprocess.run(['actionlint', WORKFLOW], capture_output=True, text=True)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)

    def test_every_action_is_pinned_to_a_commit_sha(self):
        for line in read(WORKFLOW).splitlines():
            match = re.search(r'uses:\s*(\S+)', line)
            if match:
                self.assertRegex(match.group(1), r'@[0-9a-f]{40}$', line)

    def test_a_fork_pull_request_stays_off_the_runners(self):
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", read(WORKFLOW))

    def test_a_local_runner_never_installs_or_uses_sudo(self):
        """Tools are installed only on Linux; any other runner (the Mac's own, scripts/runner-setup.sh) must already have them."""
        text = read(WORKFLOW)
        self.assertIn('"$RUNNER_OS" = Linux', text)
        installs = text.split('"$RUNNER_OS" = Linux', 1)[1].split('else', 1)
        self.assertIn('sudo', installs[0])
        self.assertNotIn('sudo', installs[1].split('- name:', 1)[0])

    def test_code_review_is_not_a_ci_job(self):
        self.assertNotIn('ANTHROPIC_API_KEY', read(WORKFLOW))

    def test_the_caller_pins_the_standards_twice_and_takes_the_runner_from_the_panel_variable(self):
        text = read(CALLER)
        self.assertEqual(2, text.count('<standards-sha>'))
        self.assertIn("vars.SDLC_RUNNER_LABELS || '[\"ubuntu-latest\"]'", text)
        self.assertIn('uses: adyusuf/claude-code-standards/.github/workflows/sdlc.yml@', text)


class PlanStep(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.project, ignore_errors=True)
        os.makedirs(os.path.join(self.project, '.claude'))

    def settings(self, ci, deploy='test'):
        text = '{"version": 1, "settings": {"ci_after_push": %s, "deploy_after_push": "%s"}}' % (ci, deploy)
        with open(os.path.join(self.project, '.claude', 'sdlc-settings.json'), 'w', encoding='utf-8') as handle:
            handle.write(text)

    def plan(self, branch):
        out = os.path.join(self.project, 'out.txt')
        env = dict(os.environ, BASE=branch, GITHUB_OUTPUT=out, GITHUB_STEP_SUMMARY=os.path.join(self.project, 'sum.md'))
        done = subprocess.run(['bash', '-c', plan_script()], cwd=self.project, capture_output=True, text=True, env=env)
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        with open(out, encoding='utf-8') as handle:
            return dict(line.split('=', 1) for line in handle.read().splitlines()), done.stdout

    def test_ci_off_for_a_branch_plans_no_ci(self):
        self.settings('{"dev": false, "test": true, "prod": true}')
        self.assertEqual('false', self.plan('dev')[0]['ci'])

    def test_ci_on_for_a_branch_plans_ci_and_names_the_deploy_target(self):
        self.settings('{"dev": false, "test": true, "prod": true}', deploy='prod')
        plan, _ = self.plan('test')
        self.assertEqual('true', plan['ci'])
        self.assertEqual('prod', plan['deploy'])
        self.assertEqual('test', plan['target'])

    def test_a_branch_that_is_not_dev_test_or_prod_is_planned_as_dev(self):
        self.settings('{"dev": true, "test": false, "prod": false}')
        plan, _ = self.plan('feature/x')
        self.assertEqual('dev', plan['target'])
        self.assertEqual('true', plan['ci'])

    def test_a_missing_settings_file_fails_closed_the_checks_run(self):
        plan, out = self.plan('prod')
        self.assertEqual('true', plan['ci'])
        self.assertIn('missing', out)


if __name__ == '__main__':
    unittest.main()
