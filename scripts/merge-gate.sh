#!/usr/bin/env bash
# Merge gate for THIS repository — the configuration repository itself.
#
# It was the only repository here without a wrapper: all eight projects had one
# and the canonical set did not, so the extension point #25 describes ("the
# project's own merge-gate.sh stays the orchestrator and CALLS the core") had
# nowhere to put this repository's own extra step.
#
# Usage: scripts/merge-gate.sh <dev|test|prod>
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel)"
target="${1:-dev}"

bash "$ROOT/scripts/gate-core.sh" "$target" || exit 1

# ── This repository's own extra step ─────────────────────────────────────────
# Being the canonical set carries one duty no project has: keeping the copies in
# step. Twins drifted in BOTH directions on 21/09/2026 — the canonical was the
# stale side in the morning and the projects were in the evening — and both times
# it was found by comparing blobs by hand. Now it is a step.
#
# A WARNING, not a failure, and the reason is honest rather than convenient: a CI
# runner has no sibling checkouts to compare with, so failing would make the gate
# unpassable there, and drift in a project is not a defect in THIS commit. The
# script says "n/a" when it can see nothing, so a silent pass is impossible.
echo
if bash "$ROOT/scripts/twin-drift.sh"; then
  :
else
  echo "  ! twin drift is reported, not fatal — propagate it, one commit per project (#26)"
fi
