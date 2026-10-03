#!/usr/bin/env bash
# Have the project COPIES of the shared scripts drifted from the canonical ones?
#
# WHY THIS EXISTS. Rule #25 makes every gate script a deliberate TWIN: the
# canonical copy lives in this repository and every project commits a COPY,
# because a project's gate cannot depend on a path outside its own checkout (CI
# runners have no configuration checked out). Twins drift, and they have
# drifted in BOTH directions within a single day:
#
#   · morning — five bugs were fixed and pushed to the eight project copies while
#     the canonical file here was left on the old version, so for a day the single
#     source was the stalest copy of the file;
#   · evening — one line changed here (the missing-e2e-spec check became a
#     warning) and all eight projects were left blocking on it, so the rule text
#     and the running gates disagreed.
#
# Both were found by comparing blobs BY HAND. Nothing compared them on its own,
# and that is what this script is for.
#
# ⚠️ It compares each project's COMMITTED `origin/dev` blob, not its working
# tree. A checkout can be mid-edit or sitting on a feature branch — that is not
# drift, it is work in progress. What matters is what the project's dev branch
# actually carries, because that is what its gate will run.
#
# ⚠️ It compares against THIS working tree's scripts/, which is the branch under
# test — not against ~/.claude, which is pinned to `prod` and is SUPPOSED to lag.
# Comparing with the live copy is what makes a not-yet-promoted change look like
# drift; md-hook.sh does that deliberately for a different purpose (warning a
# developer inside one project) and excludes this repository for exactly that
# reason.
#
# Exit codes: 0 aligned, or no sibling project is visible (then it says so)
#             1 at least one project has drifted
#             2 usage/environment
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not inside a git repository" >&2; exit 2; }
cd "$root" || exit 2

# The twins: scripts/twins.txt, the one list md-hook.sh reads as well (two lists that disagreed would
# mean a script is checked in one place and not the other). TWIN_FILES overrides it, for tests.
TWINS="${TWIN_FILES:-$(grep -vE '^[[:space:]]*(#|$)' "$root/scripts/twins.txt" 2>/dev/null | tr '\n' ' ')}"
if [ -z "$TWINS" ]; then echo "scripts/twins.txt is missing or empty: nothing to compare" >&2; exit 2; fi
search="${TWIN_SEARCH_ROOT:-$(dirname "$root")}"

# A project that carries gate-core.sh must carry the libraries it sources too: gate-core.sh stops
# with "library missing" without them. Reading the names from the canonical gate-core.sh keeps this
# in step with the split by itself. Without it a project that had not taken the libraries was reported
# "aligned" — a twin that is ABSENT looked the same as one that was never needed.
core_libs=""
if [ -f "$root/scripts/gate-core.sh" ]; then
  core_libs="$(grep -oE 'gate-lib[A-Za-z0-9._-]*\.sh' "$root/scripts/gate-core.sh" | sort -u | tr '\n' ' ')"
fi

echo "▶ Twin drift (project copies vs. the canonical set in $(basename "$root"))"

drifted=0 checked=0 projects=0
for candidate in "$search"/*; do
  [ -d "$candidate/.git" ] || [ -f "$candidate/.git" ] || continue
  # Skip this repository and any of its worktrees: it IS the canonical set.
  [ -f "$candidate/standards/README.md" ] && [ -d "$candidate/modes" ] && continue
  name="$(basename "$candidate")"
  had_any=0 lines="" has_core=0
  for tool in $TWINS; do
    [ -f "$root/scripts/$tool" ] || continue            # not canonical here
    ours="$(git hash-object "$root/scripts/$tool")"
    theirs="$(git -C "$candidate" rev-parse "origin/dev:scripts/${tool}" 2>/dev/null)" || continue
    [ -n "$theirs" ] || continue
    had_any=1; checked=$((checked + 1))
    [ "$tool" = gate-core.sh ] && has_core=1
    if [ "$ours" != "$theirs" ]; then
      lines="$lines
    ✗ $tool"
      drifted=$((drifted + 1))
    fi
  done
  if [ "$has_core" = 1 ]; then
    for lib in $core_libs; do
      [ -f "$root/scripts/$lib" ] || continue
      git -C "$candidate" rev-parse -q --verify "origin/dev:scripts/${lib}" >/dev/null 2>&1 && continue
      lines="$lines
    ✗ $lib (missing — gate-core.sh sources it)"
      drifted=$((drifted + 1))
    done
  fi
  [ "$had_any" = 1 ] || continue
  projects=$((projects + 1))
  if [ -n "$lines" ]; then
    printf '  %s%s\n' "$name" "$lines"
  else
    printf '  %s: aligned\n' "$name"
  fi
done

if [ "$projects" = 0 ]; then
  # A CI runner has no sibling checkouts. Saying "aligned" there would be a lie,
  # and failing would make the gate unpassable, so it is reported as not checked.
  echo "  n/a: no sibling project checkout is visible under $search — nothing to compare"
  exit 0
fi

echo "  $projects project(s), $checked file(s) compared"
if [ "$drifted" != 0 ]; then
  echo "  ✗ $drifted copy/copies have DRIFTED from the canonical set."
  echo "    Decide WHICH is current before copying either way — the canonical one has been"
  echo "    the stale side before. Then propagate, one commit per project (#26):"
  echo "      cp scripts/<tool> <project>/scripts/<tool>"
  exit 1
fi
echo "  ✓ every copy matches the canonical set"
