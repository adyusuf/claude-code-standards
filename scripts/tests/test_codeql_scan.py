"""The SAST wrapper (scripts/codeql-scan.sh).

Rule #19 puts SAST in every project and says a critical/high finding blocks the
merge — and that a gate which did not run is reported as skipped, never as a
pass. Both halves are only true if this script behaves that way, so the tests
drive it with a stub `codeql` rather than the real one: a real scan takes minutes
and its findings change with the query pack, which would make these tests measure
CodeQL's release notes instead of our threshold.

The threshold itself is the thing worth pinning. CodeQL puts
`security-severity` on the RULE, not on the result, so a naive reader that looks
at results alone finds no severity at all and blocks on nothing.
"""
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SCAN = os.path.join(SCRIPTS, 'codeql-scan.sh')


def sarif(*findings):
    """A SARIF document with (rule_id, security_severity, line) findings."""
    rules, results = [], []
    for rule_id, severity, line in findings:
        properties = {} if severity is None else {'security-severity': str(severity)}
        rules.append({'id': rule_id, 'properties': properties})
        results.append({
            'ruleId': rule_id,
            'message': {'text': f'{rule_id} says something'},
            'locations': [{'physicalLocation': {
                'artifactLocation': {'uri': 'scripts/thing.py'},
                'region': {'startLine': line}}}],
        })
    return {'runs': [{'tool': {'driver': {'rules': rules}}, 'results': results}]}


class Scan(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        subprocess.run(['git', 'init', '-q', self.root], check=True)
        os.makedirs(os.path.join(self.root, 'scripts'))
        with open(os.path.join(self.root, 'scripts', 'thing.py'), 'w', encoding='utf-8') as handle:
            handle.write('x = 1\n')
        self.bin = os.path.join(self.root, '.stubbin')
        os.makedirs(self.bin)
        self.sarif_path = os.path.join(self.root, 'results.sarif')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def stub_codeql(self, document=None, create_fails=False, analyze_fails=False):
        """A `codeql` that writes the SARIF we hand it, and nothing else."""
        if document is not None:
            with open(self.sarif_path, 'w', encoding='utf-8') as handle:
                json.dump(document, handle)
        body = ['#!/bin/sh', 'case "$1" in']
        body.append('  database)' )
        body.append('    case "$2" in')
        body.append(f'      create) {"exit 1" if create_fails else "exit 0"} ;;')
        if analyze_fails:
            body.append('      analyze) echo "pack not found" >&2; exit 1 ;;')
        else:
            body.append('      analyze)')
            body.append('        for a in "$@"; do')
            body.append('          case "$a" in --output=*) out="${a#--output=}" ;; esac')
            body.append('        done')
            body.append(f'        cp "{self.sarif_path}" "$out"; exit 0 ;;')
        body.append('    esac ;;')
        body.append('esac')
        body.append('exit 0')
        path = os.path.join(self.bin, 'codeql')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(body) + '\n')
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def run_scan(self, without_codeql=False):
        env = dict(os.environ)
        env['PATH'] = self.bin + os.pathsep + env['PATH']
        if without_codeql:
            env['PATH'] = os.pathsep.join(
                entry for entry in env['PATH'].split(os.pathsep)
                if not os.path.exists(os.path.join(entry, 'codeql')))
        result = subprocess.run(['bash', SCAN], cwd=self.root, capture_output=True,
                                text=True, env=env)
        return result.stdout + result.stderr, result.returncode


class TheThreshold(Scan):
    def test_a_high_severity_finding_blocks(self):
        self.stub_codeql(sarif(('py/command-injection', 9.8, 42)))
        out, code = self.run_scan()
        self.assertIn('HIGH/CRITICAL', out)
        self.assertIn('py/command-injection', out)
        self.assertIn('scripts/thing.py:42', out)
        self.assertEqual(1, code)

    def test_exactly_seven_point_zero_blocks(self):
        # 7.0 is the bottom of CodeQL's high band; ">" instead of ">=" here would
        # let the whole boundary through.
        self.stub_codeql(sarif(('py/at-the-boundary', 7.0, 1)))
        self.assertEqual(1, self.run_scan()[1])

    def test_just_below_the_band_is_reported_but_does_not_block(self):
        self.stub_codeql(sarif(('py/medium-thing', 6.9, 1)))
        out, code = self.run_scan()
        self.assertIn('below the high band', out)
        self.assertIn('not blocking', out)
        self.assertEqual(0, code)

    def test_a_rule_with_no_security_severity_does_not_block(self):
        # A quality query is not a security finding; blocking on it would make
        # the gate unusable and teach people to switch it off.
        self.stub_codeql(sarif(('py/unused-import', None, 1)))
        self.assertEqual(0, self.run_scan()[1])

    def test_the_severity_is_read_from_the_RULE_not_the_result(self):
        # SARIF puts security-severity on the rule. A reader that looks at
        # results only finds none, and then blocks on nothing at all.
        document = sarif(('py/command-injection', 9.8, 7))
        self.assertIn('security-severity',
                      document['runs'][0]['tool']['driver']['rules'][0]['properties'])
        self.assertNotIn('properties', document['runs'][0]['results'][0])
        self.stub_codeql(document)
        self.assertEqual(1, self.run_scan()[1])

    def test_a_clean_scan_passes_and_says_how_many_queries_ran(self):
        self.stub_codeql(sarif())
        out, code = self.run_scan()
        self.assertEqual(0, code, out)
        self.assertIn('no high or critical finding', out)
        self.assertIn('queries with a security severity', out)


class WhenItCannotRun(Scan):
    """#19: a gate that did not run did not pass. Exit 3, never 0."""

    def test_no_codeql_is_NOT_RUN_and_blocks(self):
        out, code = self.run_scan(without_codeql=True)
        self.assertIn('NOT RUN', out)
        self.assertIn('did not pass', out)
        self.assertEqual(3, code)

    def test_a_database_that_cannot_be_built_is_NOT_RUN(self):
        self.stub_codeql(create_fails=True)
        out, code = self.run_scan()
        self.assertIn('NOT RUN', out)
        self.assertEqual(3, code)

    def test_an_analysis_that_cannot_complete_is_NOT_RUN(self):
        self.stub_codeql(sarif(), analyze_fails=True)
        out, code = self.run_scan()
        self.assertIn('NOT RUN', out)
        self.assertEqual(3, code)

    def test_a_repository_with_no_python_is_n_a_and_passes(self):
        os.remove(os.path.join(self.root, 'scripts', 'thing.py'))
        self.stub_codeql(sarif())
        out, code = self.run_scan()
        self.assertIn('n/a', out)
        self.assertEqual(0, code)

    def test_outside_a_repository_it_refuses(self):
        loose = tempfile.mkdtemp()
        try:
            result = subprocess.run(['bash', SCAN], cwd=loose, capture_output=True, text=True)
            self.assertEqual(2, result.returncode)
        finally:
            shutil.rmtree(loose, ignore_errors=True)


class WhatItDoesNotCover(Scan):
    def test_it_says_on_every_run_that_shell_is_not_covered(self):
        # CodeQL has no shell analyser. This repository is largely shell, so
        # leaving that unsaid would let "SAST passed" read as "everything was
        # scanned" — the same unstated-gap problem the coverage gate had.
        self.stub_codeql(sarif())
        out, _ = self.run_scan()
        self.assertIn('shell scripts are NOT covered', out)


if __name__ == '__main__':
    unittest.main()
