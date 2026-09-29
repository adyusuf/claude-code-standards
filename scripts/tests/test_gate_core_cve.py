"""The .NET dependency-CVE step must fail CLOSED.

It used to be `dotnet list ... --vulnerable | grep -qi 'critical\\|high'` and a
pass for everything else — so a listing that never happened passed too. Seen
live: the NuGet vulnerability feed hung on a network that black-holes IPv6, the
process was killed after 13 minutes and the gate printed "✓ dotnet packages".
A machine without dotnet made the step vanish from the report altogether.

Each case puts a stub `dotnet` first on PATH. Only `dotnet list` follows the
scenario; every other call (format, build, test) exits 0 silently, because this
file checks one step, not the whole gate.

Mutation-verified: with the old one-line step restored, the failing-listing,
empty-output, error-line and timeout cases turn green — i.e. these tests fail —
and the missing-dotnet case finds no line at all. Record: docs/decision-log.md §25.
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
BASE_PATH = '/usr/bin:/bin'   # deliberately without the real dotnet

CLEAN = "The given project `App` has no vulnerable packages given the current sources."
HIGH = """The following sources were used:
   https://api.nuget.org/v3/index.json

Project `App` has the following vulnerable packages
   [net10.0]:
   Top-level Package      Requested   Resolved   Severity   Advisory URL
   > Some.Package         1.0.0       1.0.0      High       https://github.com/advisories/GHSA-xxxx"""
MODERATE = HIGH.replace('High  ', 'Moderate')


def stub(body):
    """A `dotnet` whose `list` subcommand runs `body`; everything else exits 0."""
    return '#!/bin/sh\ncase "$1" in\n  list) ' + body + ' ;;\n  *) exit 0 ;;\nesac\n'


def project():
    root = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q', root], check=True)
    os.makedirs(os.path.join(root, 'scripts'))
    with open(os.path.join(root, 'App.slnx'), 'w', encoding='utf-8') as handle:
        handle.write('<Solution />\n')
    return root


def install(directory, name, content):
    path = os.path.join(directory, name)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(content)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def cve_step(root, shim_dir, extra_path='', env=None):
    """Only the lines of the 'dependency CVE' step."""
    run_env = dict(os.environ, PATH=':'.join(p for p in (shim_dir, extra_path, BASE_PATH) if p))
    run_env.update(env or {})
    result = subprocess.run(['bash', GATE, 'dev'], cwd=root, capture_output=True,
                            text=True, env=run_env, timeout=120)
    out = ANSI.sub('', result.stdout)
    match = re.search(r'▶ dependency CVE[^\n]*\n(.*?)\n▶ ', out, re.S)
    return match.group(1) if match else out


class DotnetCveStep(unittest.TestCase):
    def setUp(self):
        self.root = project()
        self.shims = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.shims, ignore_errors=True)

    def listing(self, body, **kwargs):
        install(self.shims, 'dotnet', stub(body))
        return cve_step(self.root, self.shims, **kwargs)

    def test_a_clean_listing_passes(self):
        step = self.listing(f"echo '{CLEAN}'; exit 0")
        self.assertIn('✓ dotnet packages', step)

    def test_a_failing_listing_with_no_output_is_not_green(self):
        step = self.listing('exit 1')
        self.assertNotIn('✓ dotnet packages', step)
        self.assertIn('✗ dotnet vulnerable packages: the listing failed (exit 1)', step)

    def test_an_empty_listing_that_exits_0_is_not_green(self):
        step = self.listing('exit 0')
        self.assertNotIn('✓ dotnet packages', step)
        self.assertIn('no verdict in the output', step)

    def test_an_error_line_fails_even_with_exit_0(self):
        step = self.listing("echo 'error: Unable to load the service index for source'; exit 0")
        self.assertNotIn('✓ dotnet packages', step)
        self.assertIn('the listing failed', step)

    def test_a_high_advisory_closes_the_gate(self):
        step = self.listing(f"cat <<'EOF'\n{HIGH}\nEOF\nexit 0")
        self.assertIn('✗ dotnet vulnerable packages (critical/high)', step)
        self.assertIn('Some.Package', step)

    def test_a_moderate_advisory_does_not_block(self):
        step = self.listing(f"cat <<'EOF'\n{MODERATE}\nEOF\nexit 0")
        self.assertIn('✓ dotnet packages', step)

    def test_a_listing_that_never_answers_times_out_as_a_failure(self):
        timer = shutil.which('timeout') or shutil.which('gtimeout')
        if not timer:
            self.skipTest('neither timeout nor gtimeout is installed')
        step = self.listing('sleep 30', extra_path=os.path.dirname(timer),
                            env={'GATE_CVE_TIMEOUT': '2'})
        self.assertNotIn('✓ dotnet packages', step)
        self.assertIn('no answer in 2s', step)

    def test_a_missing_dotnet_is_reported_as_skipped(self):
        # No stub at all: the step must SAY it did not run, not vanish.
        step = cve_step(self.root, self.shims)
        self.assertIn('SKIPPED: dotnet vulnerable packages: dotnet missing', step)
        self.assertNotIn('✓ dotnet packages', step)


if __name__ == '__main__':
    unittest.main()
