"""Advisory triage for the dependency-audit step (scripts/audit-triage.py + gate-core.sh).

Why: a HIGH advisory in a build-tool-only package, with no fixed release the
parent accepts, left a project's gate red with no honest way to proceed — the only
options were to loosen the audit level or to ship a breaking override (which
broke the Android bundle). The triage file gives a written, EXPIRING acceptance,
and the step stays red for everything not listed.

Two layers: the helper on its own (JSON in, exit code out) and the gate step with a
stub `npm`. Mutation-verified: an always-0 helper, a helper that ignores the expiry
and a gate that never calls the helper each turn at least one case red.
Record: docs/decision-log.md §25.
"""
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
HELPER = os.environ.get('AUDIT_TRIAGE_SRC', os.path.join(SCRIPTS, 'audit-triage.py'))
GATE = os.environ.get('GATE_CORE_SRC', os.path.join(SCRIPTS, 'gate-core.sh'))
ANSI = re.compile(r'\x1b\[[0-9;]*m')
IMG = 'GHSA-5p2g-fcmc-qvqq'
AXI = 'GHSA-vh66-26gq-q6x8'


def advisory(ident, name, severity='high'):
    return {'source': 1, 'name': name, 'title': 'a title', 'severity': severity,
            'url': 'https://github.com/advisories/' + ident}


def report(*advisories, derived=()):
    vulns = {}
    for adv in advisories:
        vulns[adv['name']] = {'name': adv['name'], 'severity': adv['severity'], 'via': [adv]}
    for parent, child, severity in derived:
        vulns[parent] = {'name': parent, 'severity': severity, 'via': [child]}
    return json.dumps({'auditReportVersion': 2, 'vulnerabilities': vulns})


def pnpm_report(*pairs, counts=None):
    """A `pnpm audit --json` report: advisories keyed by numeric id, the GHSA in github_advisory_id."""
    advisories = {}
    for number, (ident, name, severity) in enumerate(pairs, 1000):
        advisories[str(number)] = {'id': number, 'module_name': name, 'severity': severity, 'title': 'a title',
                                   'github_advisory_id': ident, 'url': 'https://github.com/advisories/' + ident}
    levels = counts if counts is not None else {s: sum(1 for p in pairs if p[2] == s) for s in ('high', 'critical')}
    return json.dumps({'advisories': advisories, 'metadata': {'vulnerabilities': levels}})


def triage(*rows):
    return ''.join('\t'.join(r) + '\n' for r in rows)


def run_helper(report_text, triage_text, today='2026-10-01'):
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, 'audit-triage.tsv')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(triage_text)
        result = subprocess.run(['python3', HELPER, path, '--today', today], input=report_text,
                                capture_output=True, text=True, timeout=30)
        return result.returncode, result.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


ROW = (IMG, 'image-size', '2026-12-31', 'build tool only, never shipped')


class Helper(unittest.TestCase):
    def test_every_high_advisory_triaged_passes_and_prints_the_reason(self):
        code, out = run_helper(report(advisory(IMG, 'image-size')), triage(ROW))
        self.assertEqual(code, 0)
        self.assertIn('build tool only', out)

    def test_an_untriaged_high_advisory_fails(self):
        code, out = run_helper(report(advisory(IMG, 'image-size'), advisory(AXI, 'axios')), triage(ROW))
        self.assertEqual(code, 1)
        self.assertIn(AXI, out)

    def test_an_empty_triage_file_waives_nothing(self):
        self.assertEqual(run_helper(report(advisory(IMG, 'image-size')), '')[0], 1)

    def test_an_expired_entry_waives_nothing(self):
        code, out = run_helper(report(advisory(IMG, 'image-size')), triage(ROW), today='2027-01-01')
        self.assertEqual(code, 1)
        self.assertIn('EXPIRED', out)

    def test_the_last_day_still_counts(self):
        self.assertEqual(run_helper(report(advisory(IMG, 'image-size')), triage(ROW), today='2026-12-31')[0], 0)

    def test_a_critical_advisory_is_triaged_the_same_way(self):
        self.assertEqual(run_helper(report(advisory(IMG, 'image-size', 'critical')), triage(ROW))[0], 0)

    def test_moderate_advisories_are_not_this_steps_business(self):
        self.assertEqual(run_helper(report(advisory(AXI, 'axios', 'moderate')), '')[0], 0)

    def test_a_derived_high_finding_is_covered_by_its_triaged_leaf(self):
        leaf = advisory(IMG, 'image-size')
        code, _ = run_helper(report(leaf, derived=[('metro', leaf, 'high')]), triage(ROW))
        self.assertEqual(code, 0)

    def test_an_empty_reason_cannot_be_trusted(self):
        bad = (IMG, 'image-size', '2026-12-31', '')
        self.assertEqual(run_helper(report(advisory(IMG, 'image-size')), triage(bad))[0], 2)

    def test_a_malformed_line_cannot_be_trusted(self):
        self.assertEqual(run_helper(report(advisory(IMG, 'image-size')), 'GHSA-only-one-column\n')[0], 2)

    def test_a_bad_date_cannot_be_trusted(self):
        bad = (IMG, 'image-size', '31/12/2026', 'a reason')
        self.assertEqual(run_helper(report(advisory(IMG, 'image-size')), triage(bad))[0], 2)

    def test_a_non_ghsa_id_cannot_be_trusted(self):
        bad = ('CVE-2026-0001', 'image-size', '2026-12-31', 'a reason')
        self.assertEqual(run_helper(report(advisory(IMG, 'image-size')), triage(bad))[0], 2)

    def test_unparseable_input_fails_closed(self):
        self.assertEqual(run_helper('npm ERR! network', triage(ROW))[0], 2)

    def test_a_high_finding_with_no_advisory_behind_it_fails_closed(self):
        bare = json.dumps({'vulnerabilities': {'metro': {'name': 'metro', 'severity': 'high', 'via': ['image-size']}}})
        self.assertEqual(run_helper(bare, triage(ROW))[0], 2)

    def test_comments_and_blank_lines_are_ignored(self):
        text = '# why\n\n' + triage(ROW)
        self.assertEqual(run_helper(report(advisory(IMG, 'image-size')), text)[0], 0)


class PnpmHelper(unittest.TestCase):
    def test_a_triaged_pnpm_advisory_passes_and_prints_the_reason(self):
        code, out = run_helper(pnpm_report((IMG, 'image-size', 'high')), triage(ROW))
        self.assertEqual(code, 0)
        self.assertIn('build tool only', out)

    def test_an_untriaged_pnpm_advisory_fails_and_is_named(self):
        code, out = run_helper(pnpm_report((IMG, 'image-size', 'high'), (AXI, 'axios', 'critical')), triage(ROW))
        self.assertEqual(code, 1)
        self.assertIn(AXI, out)

    def test_an_expired_entry_waives_nothing_for_pnpm_either(self):
        code, out = run_helper(pnpm_report((IMG, 'image-size', 'high')), triage(ROW), today='2027-01-01')
        self.assertEqual(code, 1)
        self.assertIn('EXPIRED', out)

    def test_moderate_pnpm_advisories_are_not_this_steps_business(self):
        self.assertEqual(run_helper(pnpm_report((AXI, 'axios', 'moderate')), '')[0], 0)

    def test_a_pnpm_high_count_with_no_advisory_behind_it_fails_closed(self):
        bare = json.dumps({'advisories': {}, 'metadata': {'vulnerabilities': {'high': 1}}})
        self.assertEqual(run_helper(bare, triage(ROW))[0], 2)

    def test_a_pnpm_report_without_an_advisories_object_cannot_be_trusted(self):
        self.assertEqual(run_helper(json.dumps({'advisories': []}), triage(ROW))[0], 2)


def install(path, content):
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(content)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def gate_audit_lines(with_triage, json_report, helper_present=True, tool='npm'):
    """Run the gate in a stub project with a failing `<tool> audit`; return the audit step's lines."""
    root, shims = tempfile.mkdtemp(), tempfile.mkdtemp()
    try:
        subprocess.run(['git', 'init', '-q', root], check=True)
        os.makedirs(os.path.join(root, 'scripts'))
        with open(os.path.join(root, 'package.json'), 'w', encoding='utf-8') as handle:
            handle.write('{"name":"x","version":"1.0.0","scripts":{}}\n')
        if helper_present:
            shutil.copy(HELPER, os.path.join(root, 'scripts', 'audit-triage.py'))
        if with_triage is not None:
            with open(os.path.join(root, 'scripts', 'audit-triage.tsv'), 'w', encoding='utf-8') as handle:
                handle.write(with_triage)
        report_file = os.path.join(shims, 'report.json')
        with open(report_file, 'w', encoding='utf-8') as handle:
            handle.write(json_report)
        if tool == 'pnpm':
            with open(os.path.join(root, 'pnpm-lock.yaml'), 'w', encoding='utf-8') as handle:
                handle.write('lockfileVersion: 9\n')
        install(os.path.join(shims, tool),
                '#!/bin/sh\ncase "$*" in\n  *audit*--json*) cat "%s"; exit 1 ;;\n  *audit*) echo "high severity"; exit 1 ;;\n  *) exit 0 ;;\nesac\n' % report_file)
        env = dict(os.environ, PATH=shims + ':/usr/bin:/bin:' + os.path.dirname(shutil.which('python3')))
        result = subprocess.run(['bash', GATE, 'dev'], cwd=root, capture_output=True, text=True, env=env, timeout=120)
        out = ANSI.sub('', result.stdout)
        return '\n'.join(l for l in out.splitlines() if '%s audit' % tool in l)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(shims, ignore_errors=True)


class GateStep(unittest.TestCase):
    RED = '✗ npm audit (.): high or critical'

    def test_a_triaged_advisory_turns_the_step_green_and_says_why(self):
        lines = gate_audit_lines(triage(('GHSA-5p2g-fcmc-qvqq', 'image-size', '2999-01-01', 'build tool only')),
                                 report(advisory(IMG, 'image-size')))
        self.assertIn('✓ npm audit (.): every high advisory is triaged', lines)
        self.assertNotIn(self.RED, lines)

    def test_without_a_triage_file_the_step_stays_red(self):
        self.assertIn(self.RED, gate_audit_lines(None, report(advisory(IMG, 'image-size'))))

    def test_an_unlisted_advisory_stays_red_and_is_named(self):
        lines = gate_audit_lines(triage(('GHSA-5p2g-fcmc-qvqq', 'image-size', '2999-01-01', 'build tool only')),
                                 report(advisory(IMG, 'image-size'), advisory(AXI, 'axios')))
        self.assertIn(self.RED, lines)

    def test_an_expired_entry_stays_red(self):
        lines = gate_audit_lines(triage(('GHSA-5p2g-fcmc-qvqq', 'image-size', '2020-01-01', 'build tool only')),
                                 report(advisory(IMG, 'image-size')))
        self.assertIn(self.RED, lines)

    def test_a_missing_helper_never_waives(self):
        lines = gate_audit_lines(triage(('GHSA-5p2g-fcmc-qvqq', 'image-size', '2999-01-01', 'build tool only')),
                                 report(advisory(IMG, 'image-size')), helper_present=False)
        self.assertIn(self.RED, lines)


class PnpmGateStep(unittest.TestCase):
    RED = '✗ pnpm audit (.): high or critical'
    ROWS = triage(('GHSA-5p2g-fcmc-qvqq', 'image-size', '2999-01-01', 'build tool only'))

    def lines(self, rows, text, **kw):
        return gate_audit_lines(rows, text, tool='pnpm', **kw)

    def test_a_triaged_pnpm_advisory_turns_the_step_green_and_says_why(self):
        lines = self.lines(self.ROWS, pnpm_report((IMG, 'image-size', 'high')))
        self.assertIn('✓ pnpm audit (.): every high advisory is triaged', lines)
        self.assertNotIn(self.RED, lines)

    def test_without_a_triage_file_the_pnpm_step_stays_red(self):
        self.assertIn(self.RED, self.lines(None, pnpm_report((IMG, 'image-size', 'high'))))

    def test_an_unlisted_pnpm_advisory_stays_red(self):
        self.assertIn(self.RED, self.lines(self.ROWS, pnpm_report((IMG, 'image-size', 'high'), (AXI, 'axios', 'high'))))

    def test_an_expired_pnpm_entry_stays_red(self):
        expired = triage(('GHSA-5p2g-fcmc-qvqq', 'image-size', '2020-01-01', 'build tool only'))
        self.assertIn(self.RED, self.lines(expired, pnpm_report((IMG, 'image-size', 'high'))))

    def test_a_missing_helper_never_waives_for_pnpm(self):
        self.assertIn(self.RED, self.lines(self.ROWS, pnpm_report((IMG, 'image-size', 'high')), helper_present=False))


if __name__ == '__main__':
    unittest.main()
