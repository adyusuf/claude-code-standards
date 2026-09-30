"""The dependency-CVE step must scan a pnpm workspace, and must never pass without scanning.

Seen live (30/09/2026): in a pnpm workspace the gate ran `npm audit`, which needs a
package-lock.json, so it printed "npm error code ENOLOCK" and the step failed for the WRONG
reason on every run — for months nobody read the scan because it could not run. When the
audit was finally run by hand (`pnpm audit`) the production dependencies carried 2 critical
and 27 high advisories the gate had never shown.

Each case puts stub `npm` / `pnpm` first on PATH. `npm audit` behaves like the real one
without a lockfile (ENOLOCK, exit 1) unless a package-lock.json exists; `pnpm audit` follows
the scenario. Every other call exits 0 silently: this file checks one step.

Mutation-verified: with the old npm-only loop restored, the pnpm cases fail (the step
reports the npm ENOLOCK error instead of a pnpm verdict).
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GATE = os.path.join(SCRIPTS, 'gate-core.sh')
ANSI = re.compile(r'\x1b\[[0-9;]*m')
BASE_PATH = '/usr/bin:/bin'

NPM = """#!/bin/sh
# like the real npm: `audit` needs a package-lock.json
case "$*" in
  *audit*) if [ -f package-lock.json ] || [ -f "$2/package-lock.json" ]; then echo 'found 0 vulnerabilities'; exit 0; fi
           echo 'npm error code ENOLOCK'; echo 'npm error audit This command requires an existing lockfile.'; exit 1 ;;
  *) exit 0 ;;
esac
"""


def pnpm(audit_body):
    # the gate calls `pnpm --dir <d> audit ...`, so match `audit` anywhere in the arguments
    return '#!/bin/sh\ncase " $* " in\n  *" audit "*) ' + audit_body + ' ;;\n  *) exit 0 ;;\nesac\n'


def install(directory, name, content):
    path = os.path.join(directory, name)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(content)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def project(lockfile):
    root = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q', root], check=True)
    os.makedirs(os.path.join(root, 'scripts'))
    with open(os.path.join(root, 'package.json'), 'w', encoding='utf-8') as handle:
        handle.write('{"name": "app", "private": true, "scripts": {}}\n')
    with open(os.path.join(root, lockfile), 'w', encoding='utf-8') as handle:
        handle.write('lockfileVersion: 9\n' if lockfile.endswith('.yaml') else '{}\n')
    return root


def cve_step(root, shim_dir):
    """Only the lines of the 'dependency CVE' step."""
    env = dict(os.environ, PATH=':'.join(p for p in (shim_dir, BASE_PATH) if p))
    result = subprocess.run(['bash', GATE, 'dev'], cwd=root, capture_output=True,
                            text=True, env=env, timeout=120)
    out = ANSI.sub('', result.stdout)
    match = re.search(r'▶ dependency CVE[^\n]*\n(.*?)\n▶ ', out, re.S)
    return match.group(1) if match else out


class PnpmAuditStep(unittest.TestCase):
    def setUp(self):
        self.shims = tempfile.mkdtemp()
        install(self.shims, 'npm', NPM)
        self.root = None

    def tearDown(self):
        shutil.rmtree(self.shims, ignore_errors=True)
        if self.root:
            shutil.rmtree(self.root, ignore_errors=True)

    def step(self, lockfile, pnpm_body=None):
        self.root = project(lockfile)
        if pnpm_body is not None:
            install(self.shims, 'pnpm', pnpm(pnpm_body))
        return cve_step(self.root, self.shims)

    def test_a_pnpm_workspace_is_scanned_with_pnpm_and_a_clean_scan_passes(self):
        step = self.step('pnpm-lock.yaml', "echo 'No known vulnerabilities found'; exit 0")
        self.assertIn('✓ pnpm audit (.)', step)
        self.assertNotIn('ENOLOCK', step)   # npm audit is not what ran

    def test_a_high_or_critical_finding_in_a_pnpm_workspace_closes_the_gate(self):
        step = self.step('pnpm-lock.yaml', "echo '2 critical | 27 high'; exit 1")
        self.assertIn('✗ pnpm audit (.): high or critical', step)
        self.assertIn('27 high', step)

    def test_a_scan_that_could_not_run_is_not_green(self):
        # a registry/network failure is a non-zero exit too: fail closed, never a pass
        step = self.step('pnpm-lock.yaml', "echo 'ERR_PNPM_AUDIT_BAD_RESPONSE'; exit 1")
        self.assertNotIn('✓ pnpm audit', step)
        self.assertIn('✗ pnpm audit (.)', step)

    def test_a_missing_pnpm_is_reported_as_skipped_not_passed(self):
        step = self.step('pnpm-lock.yaml')   # no pnpm shim at all
        self.assertIn('SKIPPED: pnpm audit (.): pnpm missing', step)
        self.assertNotIn('✓', step)

    def test_an_npm_project_still_uses_npm_audit(self):
        step = self.step('package-lock.json', "echo 'pnpm must not run'; exit 1")
        self.assertIn('✓ npm audit (.)', step)
        self.assertNotIn('pnpm', step)

    def test_a_project_with_no_lockfile_at_all_still_fails_closed(self):
        self.root = project('package-lock.json')
        os.remove(os.path.join(self.root, 'package-lock.json'))
        step = cve_step(self.root, self.shims)
        self.assertIn('✗ npm audit (.)', step)   # ENOLOCK: no scan is possible, and that is a failure


if __name__ == '__main__':
    unittest.main()
