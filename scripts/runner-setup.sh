#!/usr/bin/env bash
# Local GitHub Actions runners for ONE repository (user decision 29/10/2026: CI runs on this machine when
# GitHub-hosted runners are unavailable; a project that has no runner of its own gets at least two).
#
#   runner-setup.sh install <owner/repo> [--count N]   register and start N runners (default and minimum 2)
#   runner-setup.sh status  <owner/repo>               local runner folders + what GitHub reports
#   runner-setup.sh remove  <owner/repo>               stop, unregister, move the folders aside (nothing is deleted)
#
# Environment: RUNNER_HOME (default ~/actions-runners) · RUNNER_VERSION (default: the latest release)
#              RUNNER_PATH_EXTRA (extra PATH entries the service needs, for example a Node bin directory).
#
# Why one set per repository: a runner on a user account serves ONE repository (only an organisation can
# share runners), so every project needs its own pair.
# Security: the runner executes whatever the workflow says, on this machine. On a PUBLIC repository the script
# first sets "approve every outside contributor" and stops if that cannot be set; the shared sdlc.yml also
# refuses fork pull requests. The registration token is requested per runner, used once and never printed.
# Exit codes: 0 done · 1 failed · 2 usage.
set -euo pipefail

die() { echo "runner-setup: $*" >&2; exit 1; }
usage() { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

[ $# -ge 2 ] || usage
cmd="$1"; repo="$2"; shift 2
case "$repo" in */*) ;; *) usage ;; esac
case "$repo" in *[!A-Za-z0-9._/-]*) die "unexpected characters in '$repo'" ;; esac
count=2
while [ $# -gt 0 ]; do
  case "$1" in
    --count) [ $# -ge 2 ] || usage; count="$2"; shift 2 ;;
    *) usage ;;
  esac
done
case "$count" in ''|*[!0-9]*) die "--count must be a number" ;; esac
[ "$count" -ge 2 ] || [ "$cmd" != install ] || die "at least 2 runners per project (user decision 29/10/2026)"

home="${RUNNER_HOME:-$HOME/actions-runners}"
base="$home/${repo//\//-}"
short="${repo#*/}"
# The service captures this PATH when it is installed; the gate needs gitleaks, codeql, uv, shellcheck ...
export PATH="${RUNNER_PATH_EXTRA:+$RUNNER_PATH_EXTRA:}$PATH:/opt/homebrew/bin:/usr/local/bin"

[ "$(uname -s)" = Darwin ] || die "this script installs launchd services; only macOS is supported"
for tool in gh curl tar shasum; do command -v "$tool" >/dev/null || die "$tool is required"; done

platform() {
  case "$(uname -m)" in
    arm64) echo osx-arm64 ;;
    x86_64) echo osx-x64 ;;
    *) die "unsupported CPU $(uname -m)" ;;
  esac
}

# Fail closed on a public repository: outside contributors' workflows need approval before they reach a runner.
protect_public_repo() {
  local private
  private="$(gh api "repos/$repo" --jq .private)" || die "cannot read $repo (is gh logged in with the repo scope?)"
  [ "$private" = true ] && return 0
  echo "$repo is PUBLIC: requiring approval for every outside contributor's workflow run"
  gh api -X PUT "repos/$repo/actions/permissions/fork-pr-contributor-approval" -f approval_policy=all_external_contributors >/dev/null \
    || die "could not set the fork approval policy on a public repository; no runner was installed"
}

# Download the runner once per version; verify the checksum GitHub publishes in the release notes.
fetch_runner() {
  local plat ver rel sum file
  plat="$(platform)"
  rel="$(gh api repos/actions/runner/releases/latest --jq '.tag_name + "\n" + .body')" || die "cannot read the runner release"
  ver="${RUNNER_VERSION:-$(printf '%s\n' "$rel" | head -1 | sed 's/^v//')}"
  sum="$(printf '%s\n' "$rel" | sed -n "s/.*<!-- BEGIN SHA $plat -->\\([0-9a-f]\\{64\\}\\)<!-- END SHA $plat -->.*/\\1/p" | head -1)"
  [ -n "$sum" ] || die "no checksum for $plat in the release notes (version $ver)"
  file="$home/.cache/actions-runner-$plat-$ver.tar.gz"
  mkdir -p "$home/.cache"
  if [ ! -f "$file" ]; then
    echo "downloading actions-runner $ver ($plat) from github.com/actions/runner" >&2
    curl -fsSL -o "$file.part" "https://github.com/actions/runner/releases/download/v$ver/actions-runner-$plat-$ver.tar.gz"
    mv "$file.part" "$file"
  fi
  [ "$(shasum -a 256 "$file" | cut -d' ' -f1)" = "$sum" ] || { mv "$file" "$file.bad"; die "checksum mismatch for $file (kept as .bad)"; }
  echo "$file"
}

install_one() {
  local n="$1" tarball="$2" dir token
  dir="$base/$n"
  if [ -f "$dir/.runner" ]; then echo "runner $n: already configured in $dir"; return 0; fi
  mkdir -p "$dir"
  tar -xzf "$tarball" -C "$dir"
  token="$(gh api -X POST "repos/$repo/actions/runners/registration-token" --jq .token)" || die "cannot get a registration token (needs admin on $repo)"
  (cd "$dir" && ./config.sh --unattended --replace --url "https://github.com/$repo" --token "$token" \
    --name "$(hostname -s)-$short-$n" --work _work >/dev/null) || die "config.sh failed for runner $n"
  (cd "$dir" && ./svc.sh install >/dev/null && ./svc.sh start >/dev/null) || die "could not start the service for runner $n"
  echo "runner $n: $(hostname -s)-$short-$n running from $dir"
}

do_install() {
  local tarball n
  protect_public_repo
  tarball="$(fetch_runner)"
  for n in $(seq 1 "$count"); do install_one "$n" "$tarball"; done
  do_status
}

do_status() {
  local d
  for d in "$base"/*/; do
    [ -f "${d}.runner" ] && echo "local: $d" || true
  done
  gh api "repos/$repo/actions/runners" --jq '.runners[] | "github: \(.name) \(.status) busy=\(.busy)"' || die "cannot list runners of $repo"
}

do_remove() {
  local d token
  for d in "$base"/*/; do
    [ -f "${d}.runner" ] || continue
    (cd "$d" && ./svc.sh stop >/dev/null; ./svc.sh uninstall >/dev/null) || true
    token="$(gh api -X POST "repos/$repo/actions/runners/remove-token" --jq .token)" || die "cannot get a remove token"
    (cd "$d" && ./config.sh remove --token "$token" >/dev/null) || die "could not unregister $d"
    mkdir -p "$home/.removed"
    mv "$d" "$home/.removed/$(basename "$base")-$(basename "$d")-$(date +%s)"
    echo "removed $d (moved to $home/.removed)"
  done
}

case "$cmd" in
  install) do_install ;;
  status) do_status ;;
  remove) do_remove ;;
  *) usage ;;
esac
