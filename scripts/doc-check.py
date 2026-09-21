#!/usr/bin/env python3
"""Documentation consistency check — links, referenced paths, indexes, stated counts.

Usage:
    python3 scripts/doc-check.py            # check the repository this file lives in
    python3 scripts/doc-check.py <root>     # check another root (a project's copy, a fixture)

Exit 0 = consistent, 1 = at least one finding (each printed as `file: message`).

What it checks (each one is a drift the rule set actually suffers from):
  1. every relative Markdown link  [text](path)  resolves to a file;
  2. every backticked repo path under standards/ modes/ docs/ agents/ commands/ skills/
     exists (unless git ignores it: a generated, local-only file is absent in a clean clone; and
     inside a git repository only files git does not ignore are read at all);
     the same holds for a relative link's target (a `~/.claude/` prefix is read as the repository root, and only checked when
     the root IS the configuration repository; `docs/...` inside standards/ names a
     PROJECT's file and is not checked);
  3. every index (standards/README.md, docs/README.md, modes/README.md) mentions every
     file that sits next to it — a document nobody can find is not documentation;
  4. the counts README.md states ("N rules", "N documents + M templates", "N roles",
     "N scripts", "N modes")
     equal what is on disk;
  5. no `#NN` rule reference in CLAUDE.md / standards / modes / agents points past the
     last numbered rule.
Only the standard library; no network.
"""
import os
import re
import subprocess
import sys

LINK = re.compile(r'\]\(([^)\s]+)\)')
PATH = re.compile(r'`(~/\.claude/)?((?:standards|modes|docs|agents|commands|skills)/[A-Za-z0-9._/-]+\.(?:md|tsv))`')
RULE_LINE = re.compile(r'^(\d+)(?:-(\d+))?\.\s+\*\*', re.M)
RULE_REF = re.compile(r'(?<![\w&/])#(\d{1,2})\b')
INDEXES = {'standards/README.md': 'standards', 'docs/README.md': 'docs', 'modes/README.md': 'modes'}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'archive'}


def git_markdown_files(root):
    """Markdown files git tracks or would track (not ignored), or None when root is not a repository."""
    try:
        result = subprocess.run(['git', '-C', root, 'ls-files', '-c', '-o', '--exclude-standard', '-z', '--', '*.md'],
                                capture_output=True)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    found = []
    for name in result.stdout.decode('utf-8', 'replace').split('\0'):
        parts = name.split('/')
        if name and os.path.exists(os.path.join(root, name)) and not any(p in SKIP_DIRS or p.startswith('.') for p in parts[:-1]):
            found.append(os.path.join(root, name))
    return found


def markdown_files(root):
    tracked = git_markdown_files(root)
    if tracked is not None:          # a cache, a vendored tree or a plugin folder that git ignores is not documentation
        yield from tracked
        return
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for name in names:
            if name.endswith('.md'):
                yield os.path.join(base, name)


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def in_code_fence(text):
    """The text with fenced code blocks removed (a sample link in a fence is not a link)."""
    return re.sub(r'```.*?```', '', text, flags=re.S)


def is_configuration_repo(root):
    return os.path.isfile(os.path.join(root, 'standards', 'README.md')) and os.path.isdir(os.path.join(root, 'modes'))


def is_git_ignored(root, relative):
    """True when git ignores the path: a generated, local-only file is absent in a clean clone by design."""
    try:
        return subprocess.run(['git', '-C', root, 'check-ignore', '-q', relative], capture_output=True).returncode == 0
    except OSError:
        return False


def check_links_and_paths(root, findings):
    config_repo = is_configuration_repo(root)
    for path in markdown_files(root):
        rel = os.path.relpath(path, root)
        text = in_code_fence(read(path))
        for target in LINK.findall(text):
            if re.match(r'^(https?:|mailto:|#)', target):
                continue
            file_part = target.split('#', 1)[0]
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), file_part)) if file_part else ''
            if file_part and not os.path.exists(resolved) and not is_git_ignored(root, os.path.relpath(resolved, root)):
                findings.append(f'{rel}: broken link -> {target}')
        for prefix, target in set(PATH.findall(text)):
            # `~/.claude/...` is the user's configuration directory: it can be verified only
            # when this root IS the configuration repository.
            if prefix and not config_repo:
                continue
            # standards/ describes what a PROJECT's docs/ holds, not this repository's.
            if rel.startswith('standards' + os.sep) and target.startswith('docs/'):
                continue
            if not os.path.exists(os.path.join(root, target)) and not is_git_ignored(root, target):
                findings.append(f'{rel}: referenced path does not exist -> {target}')


def check_indexes(root, findings):
    for index, folder in INDEXES.items():
        index_path = os.path.join(root, index)
        if not os.path.exists(index_path):
            continue
        listed = read(index_path)
        for name in sorted(os.listdir(os.path.join(root, folder))):
            full = os.path.join(root, folder, name)
            if os.path.isfile(full) and name != 'README.md' and not name.startswith('.') and name not in listed:
                findings.append(f'{index}: does not list {name}')


def rule_count(root):
    path = os.path.join(root, 'CLAUDE.md')
    if not os.path.exists(path):
        return 0
    return max((int(b or a) for a, b in RULE_LINE.findall(read(path))), default=0)


def check_counts(root, findings):
    path = os.path.join(root, 'README.md')
    if not os.path.exists(path):
        return
    text = read(path)
    standards = len([n for n in os.listdir(os.path.join(root, 'standards')) if re.match(r'\d\d-.*\.md$', n)]) \
        if os.path.isdir(os.path.join(root, 'standards')) else 0
    templates_dir = os.path.join(root, 'standards', 'templates')
    templates = len(os.listdir(templates_dir)) if os.path.isdir(templates_dir) else 0
    scripts_dir = os.path.join(root, 'scripts')
    scripts = len([n for n in os.listdir(scripts_dir) if n.endswith(('.sh', '.py'))]) if os.path.isdir(scripts_dir) else 0
    modes_dir = os.path.join(root, 'modes')
    modes = len([n for n in os.listdir(modes_dir) if re.match(r'[A-Z]-.*\.md$', n)]) if os.path.isdir(modes_dir) else 0
    roles_dir = os.path.join(root, 'agents')
    roles = len([n for n in os.listdir(roles_dir) if n.endswith('.md')]) if os.path.isdir(roles_dir) else 0
    claims = (('rules', r'(\d+) rules', rule_count(root)),
              ('standards documents', r'(\d+) documents \+ \d+ templates', standards),
              ('templates', r'\d+ documents \+ (\d+) templates', templates),
              ('agent roles', r'(\d+) roles', roles),
              ('scripts', r'(\d+) scripts', scripts),
              ('modes', r'(\d+) modes', modes))
    for label, pattern, actual in claims:
        for stated in re.findall(pattern, text):
            if int(stated) != actual:
                findings.append(f'README.md: states {stated} {label}, the repository has {actual}')


def check_rule_refs(root, findings):
    last = rule_count(root)
    if not last:
        return
    for path in markdown_files(root):
        rel = os.path.relpath(path, root)
        if not (rel == 'CLAUDE.md' or rel.split(os.sep)[0] in ('standards', 'modes', 'agents')):
            continue
        for number in set(RULE_REF.findall(in_code_fence(read(path)))):
            if int(number) > last:
                findings.append(f'{rel}: refers to rule #{number}, but the last rule is #{last}')


def run(root):
    findings = []
    check_links_and_paths(root, findings)
    check_indexes(root, findings)
    check_counts(root, findings)
    check_rule_refs(root, findings)
    return sorted(set(findings))


def main(argv):
    root = os.path.abspath(argv[0]) if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    findings = run(root)
    for finding in findings:
        print(f'✗ {finding}')
    print(f'{"✓ documentation consistent" if not findings else str(len(findings)) + " finding(s)"} ({root})')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
