#!/usr/bin/env python3
"""Which checkout of this repository is on the `prod` branch (default), `test` or `dev`.

install.py used this to pick the checkout it linked ~/.claude to; since the rule set became a plugin
(13/10/2026) install.py links nothing and no longer calls it. `resolve` is kept for any caller that needs it.

The user's own checkout is never switched — it may hold work. Resolution, in order:
    1. the given checkout, when it is already on that branch;
    2. any existing worktree of this repository on that branch (`git worktree list`).
Nothing is ever created: the branch that made a NEW worktree beside the checkout served only the old install.
An existing worktree is used as it is, never pulled: updating it is a decision (#26).
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


def resolve(repo, channel, create=False):
    """(checkout path, what was found) — or (None, why not). `create` is accepted and ignored: nothing is created."""
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
    return None, f'there is no {channel} checkout of this repository (no worktree is created)'
