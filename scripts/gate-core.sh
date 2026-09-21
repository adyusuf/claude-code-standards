#!/usr/bin/env bash
# Shared gate CORE — one definition of the step set for every project.
#
# Usage:  scripts/gate-core.sh <dev|test|prod> [--list]
#
# Two layers, deliberately: this file owns the SHARED STEPS, while a project's own
# scripts/merge-gate.sh stays the orchestrator (it pulls, merges, pushes and adds
# whatever that project needs) and CALLS this file for the shared set. That way the
# step definition lives in one place and a project can ADD steps without forking it.
# `--list` prints the steps that WOULD run, with the command each one resolves to,
# and runs nothing — use it when rolling the gate into a project.
#
# ⚠️ The canonical copy lives in the configuration repository; every project takes
# a COPY into its own scripts/ and commits it. A project's gate cannot depend on a
# path outside the repository — CI runners do not have the configuration checked
# out. The drift test in md-hook.sh covers this file too.
#
# What runs where:
#
#   dev, test : EVERYTHING EXCEPT RUNNING E2E — formatter/linter, typecheck,
#               build, unit tests, coverage (the 80% threshold per codebase),
#               secret scan, dependency CVE, SAST, backward-compatibility scan,
#               the CLAUDE.md size and rule gates, and a CHECK for missing e2e
#               specs (a warning on dev, blocking on test).
#   prod      : the code must already be deployed to the TEST environment, the
#               FULL e2e suite runs against it, and only a completely green run
#               allows the promotion.
#
# ⚠️ A STEP THAT DID NOT RUN DID NOT PASS. A missing tool is reported as SKIPPED
# and the result is INCOMPLETE, never green. The exit code is the gate: 0 only
# when every applicable step passed.
#
# Per-project settings are optional and live in scripts/merge-gate.conf (sourced
# if present); everything else is auto-detected:
#
#   TEST_VERSION_URL="https://test.example.com/version https://admin.test.example.com/version"
#                                                       # one or more; EVERY site must report the
#                                                       # deployed SHA, and a project with several
#                                                       # sites on test counts as deployed only when
#                                                       # all of them do. HTML back = the SPA fallback
#                                                       # is swallowing it (standards/14 §8).
#   TEST_DEPLOY_SHA_CMD="ssh deploy@host cat /srv/app/REVISION"
#                                                       # alternative source when there is no
#                                                       # /version endpoint yet
#   TEST_BASE_URL=https://test.example.com              # documentation + the e2e base URL
#   E2E_WEB_CMD="npx playwright test"                   # default when e2e/ exists
#   E2E_MOBILE_CMD="bash scripts/mobile-e2e.sh"         # default when .maestro/ exists
#   COVERAGE_CMD="node scripts/coverage-budget.cjs"     # must exit non-zero below the threshold
#   COVERAGE_MIN=80
#   SAST_CMD="bash scripts/codeql-scan.sh"              # default: scripts/codeql-scan.sh
#   BACKCOMPAT_CMD="bash scripts/api-compat.sh"         # default: scripts/backward-compat-scan.sh
#   SECRET_CMD="gitleaks detect --no-banner --redact"   # default: the same
#   LINT_CMD / TYPECHECK_CMD / BUILD_CMD / UNIT_CMD     # override the auto-detected ones
#   SKIP_STACKS="mobile"                                # codebases this project does not have
#   ACCEPTED_GAPS="SAST|backward"                       # gaps the USER has accepted, with a reason
#   ACCEPTED_GAPS_REASON="no SAST tooling yet; tracked in docs/gates.md, review 01/11/2026"
#
# ⚠️ ACCEPTED_GAPS is the only way a missing step stops failing the gate, and it is
# not a silence: every accepted gap is printed as an ACCEPTED GAP with its reason
# and counted separately. A gap with no reason is not accepted — the gate still
# fails. This is the written, time-boxed risk acceptance the security standard asks
# for, not a switch that turns a step off.
#
# ⚠️ ONE STEP CANNOT BE ACCEPTED AT ALL: coverage. Rule #29 grants it no
# exceptions and says a project cannot override it, so listing it in
# ACCEPTED_GAPS does nothing but print that it cannot be accepted, and the gate
# stays INCOMPLETE. Install the measurement (scripts/coverage.sh) instead.
set -uo pipefail

TARGET="${1:-}"
LIST_ONLY=0
[ "${2:-}" = "--list" ] && LIST_ONLY=1
case "$TARGET" in
  dev|test|prod) ;;
  *) echo "usage: $0 <dev|test|prod> [--list]"; exit 2 ;;
esac

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 2
[ -f scripts/merge-gate.conf ] && . scripts/merge-gate.conf
COVERAGE_MIN="${COVERAGE_MIN:-80}"

PASS=(); FAIL=(); SKIP=(); WARN=()
say()  { printf '\n\033[1m▶ %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; PASS+=("$1"); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; FAIL+=("$1"); }
NA=()
na()   { printf '  \033[90m–\033[0m n/a: %s\n' "$1"; NA+=("$1"); }   # nothing to check here — not a gap
ACCEPTED=()
# Rule #29 grants the coverage threshold NO exceptions and says a project cannot
# override it — so ACCEPTED_GAPS cannot waive it either. That was where the rule
# was quietly losing: several projects listed `coverage` as an accepted gap and
# their gates printed GREEN while nothing measured coverage at all. Measured on
# 21/09/2026 across the projects carrying this gate.
NEVER_ACCEPTABLE='coverage'
skip() {
  local what="$1"
  if [ -n "${ACCEPTED_GAPS:-}" ] && [ -n "${ACCEPTED_GAPS_REASON:-}" ] && printf '%s' "$what" | grep -qiE "${ACCEPTED_GAPS}"; then
    if printf '%s' "$what" | grep -qiE "$NEVER_ACCEPTABLE"; then
      printf '  \033[33m·\033[0m SKIPPED (this gap CANNOT be accepted — rule #29): %s\n' "$what"; SKIP+=("$what"); return 0
    fi
    printf '  \033[33m~\033[0m ACCEPTED GAP: %s\n' "$what"; ACCEPTED+=("$what"); return 0
  fi
  printf '  \033[33m·\033[0m SKIPPED: %s\n' "$what"; SKIP+=("$what")
}
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; WARN+=("$1"); }
have() { command -v "$1" >/dev/null 2>&1; }
run()  { # run <label> <command...>
  local label="$1"; shift
  if [ "$LIST_ONLY" = 1 ]; then printf '  → %-42s %s\n' "$label" "$*"; PASS+=("$label"); return 0; fi
  if "$@" >/tmp/mg.$$ 2>&1; then ok "$label"; else bad "$label"; tail -20 /tmp/mg.$$ | sed 's/^/      /'; fi
  rm -f /tmp/mg.$$
}

# ── Stack detection ──────────────────────────────────────────────────────────
#
# ⚠️ This block decides whether a whole tier is checked AT ALL, so a miss here is
# silent and total. Both halves used to miss:
#   · `ls ./*.sln` did not know about `.slnx`, the newer solution format;
#   · `ls ./**/*.csproj` is ONE level deep in a plain shell (globstar is off), so
#     a project at src/Api/X.csproj was invisible.
# Measured on 21/09/2026: a repository with a .slnx, 673 backend tests, a build
# that was RED and two high-severity advisories reported GATE GREEN, because
# HAS_DOTNET came out 0 and not one .NET step ran.
SLN="$(ls ./*.sln ./*.slnx 2>/dev/null | head -1)"
HAS_DOTNET=0
if [ -n "$SLN" ] || [ -n "$(find . -name '*.csproj' -not -path '*/obj/*' -not -path '*/bin/*' -not -path '*/node_modules/*' -print -quit 2>/dev/null)" ]; then
  HAS_DOTNET=1
fi
# Node detection is only used for the rule-#16 document step (below), and it was
# root-only while .NET detection now looks at any depth. A repository whose only
# JS lives in frontend/ therefore skipped that step entirely — measured
# 21/09/2026: one repo had no SETUP.md and its gate said "no stack at the
# repository root, nothing to check". WEB_DIR/MOBILE_DIR keep their own job of
# deciding WHICH tier gets linted, built and tested.
HAS_NODE=0
if [ -f package.json ] || [ -n "$(find . -maxdepth 3 -name package.json -not -path '*/node_modules/*' -print -quit 2>/dev/null)" ]; then
  HAS_NODE=1
fi
WEB_DIR=""; for d in web frontend .; do [ -f "$d/package.json" ] && { WEB_DIR="$d"; break; }; done
MOBILE_DIR=""; for d in mobile app; do [ -f "$d/package.json" ] && { MOBILE_DIR="$d"; break; }; done
case " ${SKIP_STACKS:-} " in *" mobile "*) MOBILE_DIR="" ;; esac
HAS_E2E_WEB=0;    [ -d e2e ] || [ -d tests/e2e ] && HAS_E2E_WEB=1
HAS_E2E_MOBILE=0; [ -d .maestro ] || [ -d "${MOBILE_DIR:-mobile}/.maestro" ] && HAS_E2E_MOBILE=1

echo "merge gate → $TARGET   ($(git rev-parse --short HEAD), $ROOT)"
echo "stacks: dotnet=$HAS_DOTNET node=$HAS_NODE web=${WEB_DIR:-none} mobile=${MOBILE_DIR:-none} e2e=web:$HAS_E2E_WEB/mobile:$HAS_E2E_MOBILE"

# ── Everything except e2e: dev and test ──────────────────────────────────────
if [ "$TARGET" != "prod" ]; then

  say "formatter / linter"
  [ "$HAS_DOTNET" = 1 ] && { have dotnet && run "dotnet format" dotnet format --verify-no-changes || skip "dotnet format (dotnet missing)"; }
  for d in "$WEB_DIR" "$MOBILE_DIR"; do
    [ -n "$d" ] || continue
    if [ -f "$d/node_modules/.bin/eslint" ] || grep -q '"lint"' "$d/package.json" 2>/dev/null; then
      run "lint ($d)" npm --prefix "$d" run lint
    else skip "lint ($d): no lint script"; fi
  done

  say "typecheck"
  for d in "$WEB_DIR" "$MOBILE_DIR"; do
    [ -n "$d" ] || continue
    if [ -f "$d/tsconfig.json" ]; then run "tsc ($d)" npx --prefix "$d" tsc -p "$d" --noEmit
    else skip "tsc ($d): no tsconfig"; fi
  done

  say "build"
  [ "$HAS_DOTNET" = 1 ] && { have dotnet && run "dotnet build" dotnet build ${SLN:+"$SLN"} -warnaserror || skip "dotnet build (dotnet missing)"; }
  for d in "$WEB_DIR" "$MOBILE_DIR"; do
    [ -n "$d" ] || continue
    grep -q '"build"' "$d/package.json" 2>/dev/null && run "build ($d)" npm --prefix "$d" run build || skip "build ($d): no build script"
  done

  say "unit tests"
  [ "$HAS_DOTNET" = 1 ] && { have dotnet && run "dotnet test" dotnet test ${SLN:+"$SLN"} --nologo || skip "dotnet test (dotnet missing)"; }
  for d in "$WEB_DIR" "$MOBILE_DIR"; do
    [ -n "$d" ] || continue
    if grep -q '"test"' "$d/package.json" 2>/dev/null; then
      # `--run` belongs to VITEST. Handing it to a jest project fails with
      # "Unrecognized option run", and the gate then reports a green test suite
      # as FAILING — measured on 21/09/2026: one project's 10 mobile tests pass on
      # their own and this step called them red, purely because of this argument.
      # CI=true is what both runners understand: vitest does a single run instead
      # of watching, and jest is single-run anyway.
      if grep -qE '"test"[[:space:]]*:[[:space:]]*"[^"]*vitest' "$d/package.json"; then
        run "test ($d)" env CI=true npm --prefix "$d" test -- --run
      else
        run "test ($d)" env CI=true npm --prefix "$d" test
      fi
    else skip "test ($d): no test script"; fi
  done

  say "coverage (>= ${COVERAGE_MIN}% lines, per codebase)"
  if [ -n "${COVERAGE_CMD:-}" ]; then run "coverage" bash -c "$COVERAGE_CMD"
  elif [ -x scripts/coverage.sh ]; then run "coverage" bash scripts/coverage.sh
  else skip "coverage: set COVERAGE_CMD in scripts/merge-gate.conf — the threshold is NOT measured"; fi

  say "secret scan"
  if [ -n "${SECRET_CMD:-}" ]; then run "secret scan" bash -c "$SECRET_CMD"
  elif have gitleaks; then run "gitleaks detect" gitleaks detect --no-banner --redact
  else skip "gitleaks is not installed"; fi

  say "dependency CVE"
  if [ "$LIST_ONLY" = 1 ]; then
    [ "$HAS_DOTNET" = 1 ] && { printf '  → %-42s %s\n' "dotnet vulnerable packages" "dotnet list package --vulnerable"; PASS+=("dotnet cve"); }
    for d in "$WEB_DIR" "$MOBILE_DIR"; do [ -n "$d" ] && { printf '  → %-42s %s\n' "npm audit ($d)" "npm --prefix $d audit --audit-level=high"; PASS+=("npm audit $d"); }; done
  else
  [ "$HAS_DOTNET" = 1 ] && have dotnet && {
    if dotnet list package --vulnerable 2>/dev/null | grep -qi 'critical\|high'; then bad "dotnet vulnerable packages (critical/high)"; else ok "dotnet packages"; fi
  }
  for d in "$WEB_DIR" "$MOBILE_DIR"; do
    [ -n "$d" ] || continue
    if have npm; then
      if npm --prefix "$d" audit --audit-level=high >/tmp/mg.$$ 2>&1; then ok "npm audit ($d)"; else bad "npm audit ($d): high or critical"; tail -10 /tmp/mg.$$ | sed 's/^/      /'; fi
      rm -f /tmp/mg.$$
    else skip "npm audit ($d): npm missing"; fi
  done
  fi

  say "SAST"
  if [ -n "${SAST_CMD:-}" ]; then run "SAST" bash -c "$SAST_CMD"
  elif [ -x scripts/codeql-scan.sh ]; then run "SAST" bash scripts/codeql-scan.sh
  else skip "SAST: set SAST_CMD in scripts/merge-gate.conf"; fi

  say "backward compatibility"
  if [ -n "${BACKCOMPAT_CMD:-}" ]; then run "backward compatibility" bash -c "$BACKCOMPAT_CMD"
  elif [ -x scripts/backward-compat-scan.sh ]; then run "backward compatibility" bash scripts/backward-compat-scan.sh
  else skip "backward-compatibility scan: set BACKCOMPAT_CMD in scripts/merge-gate.conf"; fi

  say "CLAUDE.md gates"
  if [ -x scripts/md-size-gate.sh ]; then run "md-size-gate.sh" bash scripts/md-size-gate.sh
  else skip "md-size-gate.sh is missing"; fi
  [ -f scripts/md-rule-gate.py ] && ok "md-rule-gate.py present (run by hand when splitting)" \
    || skip "md-rule-gate.py is missing"

  say "project documents (rule #16 — fail closed)"
  if [ "$LIST_ONLY" = 1 ]; then
    printf '  → %-42s %s\n' "SETUP.md, .env.example, secret inventory" "file and heading checks"
    PASS+=("project documents")
  elif [ "$HAS_DOTNET" = 0 ] && [ "$HAS_NODE" = 0 ]; then
    na "project documents: no stack at the repository root, nothing to check"
  else
    [ -f SETUP.md ] && ok "SETUP.md" || bad "SETUP.md is missing (rule #16: a clean machine must be set up from the document)"
    [ -f .env.example ] && ok ".env.example" || bad ".env.example is missing (rule #16)"
    if [ -f SETUP.md ]; then
      grep -qE '^#{1,4} .*[Ii]nventory' SETUP.md && ok "secret/token inventory in SETUP.md" \
        || bad "SETUP.md has no secret/token inventory heading (rule #16)"
    fi
  fi

  say "e2e specs — CHECK ONLY, nothing is run here"
  missing=0
  if [ "$LIST_ONLY" = 1 ]; then
    printf '  → %-42s %s\n' "e2e spec check" "git diff --name-only <base>..HEAD (no e2e run)"
    PASS+=("e2e spec check")
  else
  if [ "$HAS_E2E_WEB" = 1 ] || [ "$HAS_E2E_MOBILE" = 1 ]; then
    base="$(git merge-base HEAD "origin/$TARGET" 2>/dev/null || git rev-parse HEAD~1 2>/dev/null)"
    changed="$(git diff --name-only "$base"..HEAD 2>/dev/null)"
    behaviour="$(printf '%s\n' "$changed" | grep -Ev '^(docs/|\.github/|scripts/|e2e/|.*\.md$)' | grep -E '\.(cs|ts|tsx|js|jsx|kt|swift)$' || true)"
    specs_touched="$(printf '%s\n' "$changed" | grep -E '^(e2e/|tests/e2e/|.*\.maestro/|.*\.spec\.ts)' || true)"
    if [ -n "$behaviour" ] && [ -z "$specs_touched" ]; then
      missing=1
      warn "behaviour changed in $(printf '%s\n' "$behaviour" | wc -l | tr -d ' ') file(s) but no e2e spec was touched"
      printf '%s\n' "$behaviour" | head -8 | sed 's/^/      /'
    else
      ok "e2e specs: nothing missing for this change"
    fi
  else
    skip "e2e spec check: this project has no e2e suite"
  fi
  if [ "$missing" = 1 ] && [ "$TARGET" = "test" ]; then
    bad "missing e2e spec blocks the test promotion (write it, or record the reason)"
  fi
  fi
fi

# ── prod: deployed to test, then the full e2e suite ──────────────────────────
if [ "$TARGET" = "prod" ]; then

  say "is this code deployed to the TEST environment?"
  HEAD_SHA="$(git rev-parse HEAD)"
  if [ "$LIST_ONLY" = 1 ]; then
    if [ -n "${TEST_DEPLOY_SHA_CMD:-}" ]; then printf '  → %-42s %s\n' "deploy verification" "$TEST_DEPLOY_SHA_CMD"
    elif [ -n "${TEST_VERSION_URL:-}" ]; then printf '  → %-42s %s\n' "deploy verification" "curl ${TEST_VERSION_URL} == ${HEAD_SHA:0:7}"
    else printf '  → %-42s %s\n' "deploy verification" "<no source configured — would block>"; fi
    PASS+=("deploy verification")
  else
    deployed=""
    if [ -n "${TEST_DEPLOY_SHA_CMD:-}" ]; then
      # A project-specific command that prints the SHA deployed to test, e.g. a
      # deploy record on the server or a GitHub deployment API query.
      deployed="$(bash -c "$TEST_DEPLOY_SHA_CMD" 2>/dev/null | grep -oE '[0-9a-f]{7,40}' | head -1)"
    elif [ -n "${TEST_VERSION_URL:-}" ]; then
      # Every URL in the list must report the same SHA: a project with several
      # sites on test is only "deployed" when all of them are.
      allsame=1
      for u in $TEST_VERSION_URL; do
        body="$(curl -fsS --max-time 10 "$u" 2>/dev/null)"
        case "$body" in *'<!doctype'*|*'<!DOCTYPE'*) bad "$u returned HTML, not a version — the SPA fallback is swallowing it (standards/14 §8)"; allsame=0; continue ;; esac
        one="$(printf '%s' "$body" | grep -oE '[0-9a-f]{7,40}' | head -1)"
        if [ -z "$one" ]; then bad "$u reports no commit SHA"; allsame=0; continue; fi
        [ -z "$deployed" ] && deployed="$one"
        [ "$one" != "$deployed" ] && { bad "$u reports $one while another site reports $deployed"; allsame=0; }
      done
      [ "$allsame" = 0 ] && deployed=""
    fi
    if [ -z "$deployed" ]; then
      skip "the deployed SHA cannot be read: set TEST_VERSION_URL (a /version endpoint per standards/17 §6) or TEST_DEPLOY_SHA_CMD in scripts/merge-gate.conf"
    elif [ "${HEAD_SHA#$deployed}" != "$HEAD_SHA" ] || [ "${deployed#${HEAD_SHA:0:7}}" != "$deployed" ]; then
      ok "the test environment is running this code ($deployed)"
    else
      bad "the test environment is running $deployed, not ${HEAD_SHA:0:7} — deploy to test first and wait for it"
    fi
  fi

  say "full e2e suite against the test environment"
  ran=0
  if [ "$HAS_E2E_WEB" = 1 ]; then
    ran=1
    if [ -n "${E2E_WEB_CMD:-}" ]; then run "web e2e ($E2E_WEB_CMD)" bash -c "$E2E_WEB_CMD"
    else run "web e2e (playwright)" npx playwright test; fi
  fi
  if [ "$HAS_E2E_MOBILE" = 1 ]; then
    ran=1
    if [ -n "${E2E_MOBILE_CMD:-}" ]; then run "mobile e2e ($E2E_MOBILE_CMD)" bash -c "$E2E_MOBILE_CMD"
    else skip "mobile e2e: set E2E_MOBILE_CMD (maestro needs a device/emulator)"; fi
  fi
  [ "$ran" = 0 ] && skip "e2e: this project has no e2e suite — nothing proves this promotion"
fi

# ── Result ───────────────────────────────────────────────────────────────────
printf '\n\033[1m── result ──\033[0m\n'
printf '  passed  : %d\n' "${#PASS[@]}"
printf '  warnings: %d\n' "${#WARN[@]}"
printf '  n/a     : %d\n' "${#NA[@]}"
printf '  accepted: %d\n' "${#ACCEPTED[@]}"
printf '  skipped : %d\n' "${#SKIP[@]}"
printf '  failed  : %d\n' "${#FAIL[@]}"
for x in "${WARN[@]+"${WARN[@]}"}"; do printf '  ! %s\n' "$x"; done
for x in "${ACCEPTED[@]+"${ACCEPTED[@]}"}"; do printf '  ~ ACCEPTED GAP %s\n' "$x"; done
[ "${#ACCEPTED[@]}" -gt 0 ] && printf '    reason: %s\n' "${ACCEPTED_GAPS_REASON:-}"
for x in "${SKIP[@]+"${SKIP[@]}"}"; do printf '  · SKIPPED %s\n' "$x"; done
for x in "${FAIL[@]+"${FAIL[@]}"}"; do printf '  ✗ %s\n' "$x"; done

if [ "${#FAIL[@]}" -gt 0 ]; then
  printf '\n\033[31mGATE CLOSED\033[0m — %d step(s) failed. No merge to %s.\n' "${#FAIL[@]}" "$TARGET"
  exit 1
fi
if [ "${#SKIP[@]}" -gt 0 ]; then
  printf '\n\033[33mGATE INCOMPLETE\033[0m — %d step(s) did not run. A step that did not run did not pass;\n' "${#SKIP[@]}"
  printf 'the result is not green. Install the tool, or record the reason and get the user to accept it.\n'
  exit 1
fi
if [ "${#ACCEPTED[@]}" -gt 0 ]; then
  printf '\n\033[32mGATE GREEN\033[0m (with %d accepted gap(s)) — %s promotion is allowed.\n' "${#ACCEPTED[@]}" "$TARGET"
  exit 0
fi
printf '\n\033[32mGATE GREEN\033[0m — every applicable step passed. %s promotion is allowed.\n' "$TARGET"
exit 0
