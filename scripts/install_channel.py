#!/usr/bin/env python3
"""Which checkout `install.py` links ~/.claude to: the `prod` branch (default, --prod), `test` (--test) or
`dev` (--dev).

The user's own checkout is never switched — it may hold work, and on Windows a branch switch rewrites the
plugin/ symlinks. Resolution, in order:
    1. the checkout install.py runs from, when it is already on that branch;
    2. any existing worktree of this repository on that branch (`git worktree list`);
    3. a NEW worktree beside it, `<checkout>-<branch>`, from origin/<branch> (install only; --check and
       --remove never create one).
An existing worktree is used as it is, never pulled: updating the live rules is a decision (#26).
"""
import os
import subprocess

CHANNELS = ('prod', 'test', 'dev')


def git(repo, *args):
    try:
        return subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True)
    except OSError as error:
        return subprocess.CompletedProcess(args, 127, '', str(error))


def branch_of(repo):
    result = git(repo, 'symbolic-ref', '--short', 'HEAD')
    return result.stdout.strip() if result.returncode == 0 else None


def worktree_on(repo, branch):
    """The path of a worktree of `repo` that has `branch` checked out, or None."""
    path = None
    for line in git(repo, 'worktree', 'list', '--porcelain').stdout.splitlines():
        if line.startswith('worktree '):
            path = line[len('worktree '):]
        elif line == f'branch refs/heads/{branch}' and path:
            return os.path.normpath(path)
    return None


def sibling(repo, branch):
    return os.path.normpath(repo).rstrip('\\/') + '-' + branch


def resolve(repo, channel, create=True):
    """(checkout path, what was done) — or (None, why not)."""
    if channel not in CHANNELS:
        return None, f'unknown channel {channel!r} (one of {", ".join(CHANNELS)})'
    if git(repo, 'rev-parse', '--git-dir').returncode != 0:
        # A download without git (a GitHub ZIP): there is no branch to read or to switch to.
        if channel == 'prod':
            return repo, f'{repo} (NOT a git checkout — used as it is; its branch cannot be verified)'
        return None, f'{repo} is not a git checkout, so --{channel} cannot pick a branch: clone the repository'
    if branch_of(repo) == channel:
        return repo, f'{repo} (on {channel})'
    found = worktree_on(repo, channel)
    if found:
        return found, f'{found} (the existing {channel} worktree, used as it is)'
    target = sibling(repo, channel)
    if not create:
        return None, f'there is no {channel} checkout yet (an install creates {target})'
    if os.path.exists(target):
        return None, f'{target} exists but is not a {channel} worktree of this repository — move it aside'
    git(repo, 'fetch', '-q', 'origin', channel)                 # offline is fine when the branch is local
    local = git(repo, 'rev-parse', '--verify', '-q', f'refs/heads/{channel}').returncode == 0
    added = git(repo, 'worktree', 'add', target, channel) if local else \
        git(repo, 'worktree', 'add', '--track', '-b', channel, target, f'origin/{channel}')
    if added.returncode:
        return None, f'could not create the {channel} worktree: {added.stderr.strip() or added.stdout.strip()}'
    return target, f'{target} (a new {channel} worktree)'
