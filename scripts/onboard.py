#!/usr/bin/env python3
"""Onboarding helper for README's "How to use this" levels 1-3, plus a ready-to-paste
description of this repository for a fresh Claude session in another project.

Usage:
    python3 scripts/onboard.py describe                  # print the paste-into-Claude description
    python3 scripts/onboard.py status                     # report what --home already has (no writes)
    python3 scripts/onboard.py level1 [--apply]           # the five-rule block -> <home>/.claude/CLAUDE.md
    python3 scripts/onboard.py level2 FILE... [--apply]   # chosen standards/*.md -> <home>/.claude/standards/
    python3 scripts/onboard.py level2 --list              # print the standards files level2 can take
    python3 scripts/onboard.py level3 [--apply]            # CLAUDE.md, standards, agents, modes, commands,
                                                             # skills, scripts -> <home>/.claude/

Every subcommand defaults to a DRY RUN: it prints what it would do and writes nothing.
Pass --apply to actually write. This mirrors gate-core.sh --list and install-live-hooks.py
--check, but inverted, because this script's default target is the caller's OWN home
directory rather than a project already opted into the gate.

Level 0 needs no script (read CLAUDE.md and docs/decision-log.md). Level 4 (the live
symlink checkout) has its own script, install-live-hooks.py; this one stops at level 3.

Safe by construction: level1 is idempotent (a marker comment guards the appended block),
and level2/level3 never overwrite an existing destination file unless --force is also given.
"""
import argparse
import datetime
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_REPO = os.path.dirname(HERE)

FIVE_RULES_MARKER = '<!-- claude-code-standards: five-rule block (level 1) -->'
FIVE_RULES = f"""{FIVE_RULES_MARKER}
1. Report the truth. If tests are red, say so with the output; name any step
   that was skipped. Never report completion on the basis of "it probably
   works".
2. Before saying "done", re-read the ORIGINAL request - not a summarised memory
   of it - and check it item by item. Anything knowingly deferred is listed in
   the final report, never skipped silently.
3. A gate that did not run did not pass. A missing tool is reported as SKIPPED
   and the result is INCOMPLETE, never green. The exit code is the gate.
4. A new rule is never left verbal. The moment a permanent decision is made,
   write it to the rule file in the same turn.
5. Line coverage is measured per codebase and never averaged. Only GENERATED
   code may leave the denominator, and the exclusion list carries a reason per
   entry.
"""

LEVEL3_ENTRIES = ('CLAUDE.md', 'standards', 'agents', 'modes', 'commands', 'skills', 'scripts')


def origin_url(repo):
    try:
        out = subprocess.run(['git', '-C', repo, 'remote', 'get-url', 'origin'],
                              capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def describe(repo):
    source = origin_url(repo) or repo
    print(f"""Paste this into a fresh Claude session in the project you want to bring these
rules to:

---
This project should follow the engineering rules in {source}
("claude-code-standards"). Read its README.md "How to use this" section and pick
the smallest level that is useful here - usually level 1 (five rules pasted into
CLAUDE.md) or level 2 (the standards/*.md documents matching this project's
stack). If we are adopting it into this repository specifically, run the
/apply-project-standards command (its definition is at
commands/apply-project-standards.md in that repository) to install or update
CLAUDE.md, SETUP.md and .env.example here - it never deletes what already
exists, only fills in what is missing.
---""")


def standards_files(repo):
    directory = os.path.join(repo, 'standards')
    return sorted(f for f in os.listdir(directory) if f.endswith('.md') and f != 'README.md')


def claude_dir(home):
    return os.path.join(home, '.claude')


def status(repo, home):
    claude = claude_dir(home)
    print(f'onboarding status (repo: {repo}, home: {home})')
    claude_md = os.path.join(claude, 'CLAUDE.md')
    if os.path.exists(claude_md):
        has_marker = FIVE_RULES_MARKER in open(claude_md, encoding='utf-8').read()
        print(f'  level1 (CLAUDE.md): present' + (', five-rule block found' if has_marker else ', five-rule block NOT found'))
    else:
        print('  level1 (CLAUDE.md): missing')
    have = set()
    standards_dir = os.path.join(claude, 'standards')
    if os.path.isdir(standards_dir):
        have = {f for f in os.listdir(standards_dir) if f.endswith('.md')}
    want = set(standards_files(repo))
    print(f'  level2 (standards/): {len(have & want)}/{len(want)} of this repo\'s documents present')
    missing3 = [e for e in LEVEL3_ENTRIES if not os.path.exists(os.path.join(claude, e))]
    level3_state = 'all present' if not missing3 else 'missing ' + ', '.join(missing3)
    print(f'  level3 (whole config): {level3_state}')
    print('  level4 (live symlink): see install-live-hooks.py --check')


def append_once(path, block, marker, apply_):
    existing = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
    if marker in existing:
        print(f'{path}: five-rule block already present, nothing to do')
        return 0
    action = 'would append' if not apply_ else 'appending'
    print(f'{action} the five-rule block to {path}')
    if not apply_:
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    separator = '' if not existing or existing.endswith('\n\n') else ('\n' if existing.endswith('\n') else '\n\n')
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write(separator + block)
    return 0


def level1(home, apply_):
    return append_once(os.path.join(claude_dir(home), 'CLAUDE.md'), FIVE_RULES, FIVE_RULES_MARKER, apply_)


def copy_one(source, dest, home, apply_, force):
    if not os.path.exists(source):
        print(f'refusing — source does not exist: {source}', file=sys.stderr)
        return 1
    if os.path.exists(dest) and not force:
        print(f'skipping (already exists, use --force to overwrite): {dest}')
        return 0
    action = 'would copy' if not apply_ else 'copying'
    print(f'{action} {source} -> {dest}')
    if not apply_:
        return 0
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.isdir(source):
        shutil.copytree(source, dest, dirs_exist_ok=force)
    else:
        if os.path.exists(dest):
            backup_dir = os.path.join(claude_dir(home), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            shutil.copy2(dest, os.path.join(backup_dir, f'{os.path.basename(dest)}.{stamp}.bak'))
        shutil.copy2(source, dest)
    return 0


def level2(repo, home, names, list_only, apply_, force):
    available = standards_files(repo)
    if list_only:
        print('standards documents this repository offers:')
        for name in available:
            print(f'  {name}')
        return 0
    if not names:
        print('level2 needs at least one FILE (see level2 --list), or pass --list', file=sys.stderr)
        return 2
    unknown = [n for n in names if n not in available]
    if unknown:
        print(f'refusing — not in standards/: {", ".join(unknown)}', file=sys.stderr)
        return 2
    status_code = 0
    dest_dir = os.path.join(claude_dir(home), 'standards')
    for name in names:
        status_code |= copy_one(os.path.join(repo, 'standards', name), os.path.join(dest_dir, name), home, apply_, force)
    return status_code


def level3(repo, home, apply_, force):
    status_code = 0
    for name in LEVEL3_ENTRIES:
        status_code |= copy_one(os.path.join(repo, name), os.path.join(claude_dir(home), name), home, apply_, force)
    if apply_:
        print('settings.example.json was NOT copied — read it and take only the "hooks" block (see README '
              '"Level 3", the file also carries this repository owner\'s personal plugin selection).')
    return status_code


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--repo', default=DEFAULT_REPO)
    parser.add_argument('--home', default=os.path.expanduser('~'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('describe')
    sub.add_parser('status')
    p1 = sub.add_parser('level1')
    p1.add_argument('--apply', action='store_true')
    p2 = sub.add_parser('level2')
    p2.add_argument('files', nargs='*')
    p2.add_argument('--list', action='store_true')
    p2.add_argument('--apply', action='store_true')
    p2.add_argument('--force', action='store_true')
    p3 = sub.add_parser('level3')
    p3.add_argument('--apply', action='store_true')
    p3.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    repo, home = os.path.realpath(args.repo), os.path.abspath(args.home)
    if args.command == 'describe':
        describe(repo)
        return 0
    if args.command == 'status':
        status(repo, home)
        return 0
    if args.command == 'level1':
        return level1(home, args.apply)
    if args.command == 'level2':
        return level2(repo, home, args.files, args.list, args.apply, args.force)
    return level3(repo, home, args.apply, args.force)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
