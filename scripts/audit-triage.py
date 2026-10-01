#!/usr/bin/env python3
"""Advisory triage for the dependency-audit step of the shared gate.

Usage:  npm audit --json | python3 scripts/audit-triage.py <scripts/audit-triage.tsv> [--today YYYY-MM-DD]

Reads the `npm audit --json` report on stdin and the project's triage file, and
decides whether every HIGH / CRITICAL advisory is covered by a written, unexpired
triage entry. The audit step calls this only AFTER `npm audit --audit-level=high`
has already failed, so an empty or missing triage file changes nothing: the step
stays red.

Triage file (tab-separated, `#` starts a comment line):
    <GHSA id> <TAB> <package> <TAB> <expires YYYY-MM-DD> <TAB> <reason>

The reason is mandatory and so is the expiry: an acceptance without a "why" is a
switched-off rule, and one without an end date is a permanent one nobody re-reads.
An expired entry waives nothing.

Exit code:  0 every high/critical advisory is triaged · 1 at least one is not
(or is expired) · 2 the input cannot be trusted (unparseable report, malformed
triage line, empty reason, a high finding with no advisory behind it) — fail closed.
"""
import datetime
import json
import re
import sys

GHSA = re.compile(r'GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}', re.I)
SEVERE = ('high', 'critical')


def canonical(ident):
    """GHSA ids are `GHSA-` plus lowercase groups; compare and print them that way."""
    return 'GHSA-' + ident[5:].lower()


class Untrusted(Exception):
    """The report or the triage file cannot be relied on."""


def load_triage(path):
    entries = {}
    with open(path, encoding='utf-8') as handle:
        for number, raw in enumerate(handle, 1):
            line = raw.rstrip('\n')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            cols = line.split('\t')
            if len(cols) != 4:
                raise Untrusted('%s:%d: need 4 tab-separated columns' % (path, number))
            ident, package, expires, reason = (c.strip() for c in cols)
            if not GHSA.fullmatch(ident):
                raise Untrusted('%s:%d: "%s" is not a GHSA id' % (path, number, ident))
            if not reason:
                raise Untrusted('%s:%d: the reason is empty' % (path, number))
            try:
                entries[canonical(ident)] = (package, datetime.date.fromisoformat(expires), reason)
            except ValueError:
                raise Untrusted('%s:%d: "%s" is not a YYYY-MM-DD date' % (path, number, expires))
    return entries


def severe_advisories(report):
    """{GHSA: (package, title)} for every high/critical advisory in an npm audit report."""
    vulns = report.get('vulnerabilities')
    if not isinstance(vulns, dict):
        raise Untrusted('the report has no "vulnerabilities" object')
    found, any_severe_vuln = {}, False
    for name, vuln in vulns.items():
        if vuln.get('severity') in SEVERE:
            any_severe_vuln = True
        for via in vuln.get('via', []):
            if isinstance(via, dict) and via.get('severity') in SEVERE:
                match = GHSA.search(via.get('url', ''))
                ident = canonical(match.group(0)) if match else 'source-%s' % via.get('source')
                found[ident] = (via.get('name', name), via.get('title', ''))
    if any_severe_vuln and not found:
        raise Untrusted('a high/critical finding is reported but no advisory is behind it')
    return found


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    today = datetime.date.today()
    if '--today' in argv:
        today = datetime.date.fromisoformat(argv[argv.index('--today') + 1])
    try:
        try:
            report = json.load(sys.stdin)
        except ValueError:
            raise Untrusted('stdin is not an npm audit JSON report')
        triage = load_triage(argv[1])
        advisories = severe_advisories(report)
    except (Untrusted, OSError) as error:
        print('  ✗ audit triage cannot be trusted: %s' % error)
        return 2
    open_items = 0
    for ident, (package, title) in sorted(advisories.items()):
        entry = triage.get(ident)
        if entry and entry[1] >= today:
            print('  ~ accepted until %s: %s (%s) — %s' % (entry[1].isoformat(), ident, package, entry[2]))
        else:
            why = 'EXPIRED %s' % entry[1].isoformat() if entry else 'not triaged'
            print('  ✗ %s: %s (%s) %s' % (why, ident, package, title))
            open_items += 1
    return 1 if open_items else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
