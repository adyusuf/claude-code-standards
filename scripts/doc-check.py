#!/usr/bin/env python3
"""Documentation consistency check — links, referenced paths, indexes, stated counts.

Usage:
    python3 scripts/doc-check.py            # check the repository this file lives in
    python3 scripts/doc-check.py <root>     # check another root (a project's copy, a fixture)

Exit 0 = consistent, 1 = at least one finding (each printed as `file: message`).

What it checks (each one is a drift the rule set actually suffers from):
  1. every relative Markdown link  [text](path)  resolves to a file;
  2. every backticked repo path under standards/ modes/ docs/ agents/ commands/ skills/
     scripts/ — .md .tsv .sh .py .json .conf — exists. ⚠️ The pattern used to cover
     only .md and .tsv under the six folders, so scripts/ and every script extension
     were INVISIBLE: 51 references here were never checked, and removing four scripts
     left 20 dead references the gate reported as consistent (unless git ignores it: a generated, local-only file is absent in a clean clone; and
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
     last numbered rule;
  6. the SHARED CORE of the completeness-check block is identical in every role that
     owes it. The block is copied into each role file on purpose — the file is what
     enters that agent's context, and an agent cannot be relied on to go and read a
     reference — so the copies have to be held together by something. Five roles add
     one line of their own, which is allowed: additions are free, edits to the shared
     part are not.
Only the standard library; no network.
"""
import difflib
import os
import re
import subprocess
import sys

LINK = re.compile(r'\]\(([^)\s]+)\)')
PATH = re.compile(r'`(~/\.claude/)?((?:standards|modes|docs|agents|commands|skills|scripts)/'
                  r'[A-Za-z0-9._/-]+\.(?:md|tsv|sh|py|json|conf))`')
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
    # (?<!\w) so a digit glued to a word is not read as a count: `python3 scripts/x.py`
    # was reported as "states 3 scripts", and the finding was unfixable without
    # rewording a correct shell command. A count is always preceded by a space,
    # a pipe or the start of a line.
    claims = (('rules', r'(?<!\w)(\d+) rules', rule_count(root)),
              ('standards documents', r'(?<!\w)(\d+) documents \+ \d+ templates', standards),
              ('templates', r'\d+ documents \+ (?<!\w)(\d+) templates', templates),
              ('agent roles', r'(?<!\w)(\d+) roles', roles),
              ('scripts', r'(?<!\w)(\d+) scripts', scripts),
              ('modes', r'(?<!\w)(\d+) modes', modes))
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


BLOCK_HEADING = '## Completeness check'


def evidence_block(text):
    """The completeness-check block of a role file, or None when it has no block.

    From its heading to the next top-level heading. The block is deliberately
    INLINE in every role file that owes it rather than behind a reference: the file
    is what enters that agent's context, and an agent cannot be relied on to go and
    read a second document. The cost of inlining is drift, which is what this
    reads for.
    """
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(BLOCK_HEADING)), None)
    if start is None:
        return None
    # The block PRINTS a '## Completeness check — pass N' heading inside a fenced
    # example, so the end cannot be found by looking for the next '## ' — that hit
    # the fence and cut the block to its first four lines, which is how the first
    # version of this check passed a mutation it should have caught.
    out, fenced = [], False
    for line in lines[start:]:
        if line.startswith('```'):
            fenced = not fenced
        elif line.startswith('## ') and out and not fenced:
            break
        out.append(line)
    return '\n'.join(out).strip()


def check_evidence_block_drift(root, findings):
    """The SHARED CORE of the completeness-check block must be identical everywhere.

    Not the whole block: five roles deliberately add one line of their own (`qa`
    does not fix what it finds, `test-writer` does not bend a test to a product
    gap, and so on). Demanding byte-identity would report those as drift, and a
    check that fires on correct files is a check that gets switched off. So the
    invariant is the one that matters: every line of the shared core is present, in
    order, in every role that owes the block. Additions are free; edits are not.
    """
    roles_dir = os.path.join(root, 'agents')
    source = os.path.join(root, 'modes', 'completeness-check-core.md')
    if not (os.path.isdir(roles_dir) and os.path.isfile(source)):
        return
    # ⚠️ The core is read from a FILE, not derived from the role files. Deriving it as
    # the intersection of the copies was the first attempt and it cannot work: edit a
    # line in one copy and that line simply drops out of the intersection, so every
    # copy still "matches" the smaller core. A check whose reference comes from the
    # data it validates cannot detect a change in that data.
    core = [l for l in evidence_block(read(source)).splitlines() if l.strip()]
    if not core:
        return
    for name in sorted(os.listdir(roles_dir)):
        if not name.endswith('.md'):
            continue
        block = evidence_block(read(os.path.join(roles_dir, name)))
        if block is None:
            continue
        lines = [l for l in block.splitlines() if l.strip()]
        matcher = difflib.SequenceMatcher(None, core, lines, autojunk=False)
        kept = sum(size for _, _, size in matcher.get_matching_blocks())
        if kept != len(core):
            findings.append(
                f'agents/{name}: the completeness-check block no longer carries the canonical core '
                f'({len(core) - kept} of {len(core)} lines missing or reworded) — a role may ADD a '
                f'line of its own, it may not change one from modes/completeness-check-core.md')


def run(root):
    findings = []
    check_links_and_paths(root, findings)
    check_indexes(root, findings)
    check_counts(root, findings)
    check_rule_refs(root, findings)
    check_evidence_block_drift(root, findings)
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
