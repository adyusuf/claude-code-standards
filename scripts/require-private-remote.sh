#!/usr/bin/env bash
# pre-push hook: refuse to push to a GitHub repository that is not PRIVATE.
#
# Why: ~/.claude (claude-config) tracks per-project memory folders whose names are real project
# names, and the real names are what make that memory usable — so the repository is safe only
# while it stays private. GitHub can turn a repository public with one click; this asks GitHub,
# authenticated, on every push, and stops when the answer is anything but "private".
#
# Fails CLOSED: if gh is missing, not logged in, offline, or the remote is not on github.com, the
# push is refused, because "could not check" is not "it is private". A deliberate exception is
# the user's to make (git push --no-verify); there is no environment switch.
#
# Install for the config repository (one symlink, no copy to drift):
#   ln -s <checkout>/scripts/require-private-remote.sh ~/.claude/.git/hooks/pre-push
# git passes: $1 = the remote's name, $2 = its URL.
set -uo pipefail

url="${2:-}"
case "$url" in
  https://github.com/*|https://*@github.com/*|git@github.com:*|ssh://git@github.com/*) ;;
  *) echo "✗ push refused: '$url' is not a github.com remote, so its visibility cannot be checked." >&2; exit 1 ;;
esac
slug="$(printf '%s' "$url" | sed -E 's#^(https?://([^@/]+@)?github\.com/|git@github\.com:|ssh://git@github\.com/)##; s#\.git$##; s#/$##')"
case "$slug" in
  */*) ;;
  *) echo "✗ push refused: could not read owner/repo from '$url'." >&2; exit 1 ;;
esac

if ! command -v gh >/dev/null 2>&1; then
  echo "✗ push refused: gh is not installed, so the repository's visibility cannot be checked." >&2; exit 1
fi
answer="$(gh api "repos/$slug" --jq .private 2>&1)"
if [ "$answer" = "true" ]; then
  exit 0
fi
if [ "$answer" = "false" ]; then
  echo "✗ push refused: github.com/$slug is PUBLIC. It holds real project names. Make it private first." >&2
else
  echo "✗ push refused: could not confirm that github.com/$slug is private (gh said: $(printf '%s' "$answer" | head -1))." >&2
fi
exit 1
