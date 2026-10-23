#!/usr/bin/env python3
"""Builds the Session Settings page (an Artifact for the side panel) from the template and the live configuration.

    adyusuf_page.py build --session <id> [--out FILE]    write the page; without --out it is printed

The page is for surfaces that cannot draw the rail boxes (the Claude desktop app does not load the plugin's mod). It shows
the Settings and Agents boxes with this session's effective values, stages clicks, and sends them to Claude in ONE comment
("Apply to this session"); Claude then runs `adyusuf_config.py apply --session <id> -` and republishes the page. Nothing
in the page can write a file or run a command itself. Template: skills/config/session-panel.html.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adyusuf_config as cfg  # noqa: E402
import adyusuf_session as sessions  # noqa: E402

TEMPLATE = os.path.join(cfg.ROOT, 'skills', 'config', 'session-panel.html')
PLACEHOLDER = '__DATA__'
WAIVED_SHOWN = 3


def git(args):
    """stdout of a read-only git command, or '' when git or the repository is missing."""
    try:
        done = subprocess.run(['git', *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ''
    return done.stdout.strip() if done.returncode == 0 else ''


def promotion():
    """[{branch, origin, waived}]: the dev/test/prod tips on origin and the Gate-Waived lines on the way in."""
    stages, previous = [], None
    for branch in cfg.TARGETS:
        tip = git(['rev-parse', '--short', 'origin/' + branch])
        if not tip:
            continue
        waived = []
        if previous:
            log = git(['log', '--format=%B', 'origin/%s..origin/%s' % (branch, previous)])
            waived = sorted({line.strip()[:160] for line in log.splitlines() if line.startswith('Gate-Waived:')})
        stages.append({'branch': branch, 'origin': tip, 'waived': waived[:WAIVED_SHOWN]})
        previous = branch
    return stages


def data(session, now=None):
    effective, problems = cfg.load(session=session)
    values = {key: value[0] for key, value in effective.items()}
    return {'session': session, 'made': (now or datetime.datetime.now()).strftime('%d/%m/%Y %H:%M'),
            'schema': cfg.SCHEMA, 'values': values, 'sources': {key: value[1] for key, value in effective.items()},
            'agents': cfg.agents(values, include_inactive=True), 'promotion': promotion(), 'problems': problems}


def embed(payload):
    """JSON safe inside a <script> element: no '</script>', no '<!--', no line separators that end a JS string."""
    text = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return text.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def build(session, now=None):
    if not sessions.valid(session):
        raise ValueError('not a usable session id: %r' % (session,))
    with open(TEMPLATE, encoding='utf-8') as handle:
        template = handle.read()
    if template.count(PLACEHOLDER) != 1:
        raise ValueError('the template must hold %s exactly once' % PLACEHOLDER)
    return template.replace(PLACEHOLDER, embed(data(session, now)))


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('command', choices=['build'])
    parser.add_argument('--session', required=True)
    parser.add_argument('--out')
    args = parser.parse_args(argv)
    try:
        page = build(args.session)
    except (OSError, ValueError) as error:
        sys.stderr.write('%s\n' % error)
        return 2
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as handle:
            handle.write(page)
        print('%s (%d bytes)' % (args.out, len(page.encode('utf-8'))))
    else:
        sys.stdout.write(page)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
