# Measurement log — step and agent statistics

> **Generated file** — do not edit by hand; regenerate with
> `python3 scripts/step-stats.py --write`. The estimate table in
> `modes/role-selection.md` §8 is corrected with these numbers (never from a
> single measurement: at least three records, or one real end-to-end round).

Scope: 86 sessions + 253 agent runs, last 30 days

## Session prefix (system prompt + tool/skill listings + CLAUDE.md)

- sessions: **83** · model requests: **76,840**
- prefix median: **92,094 tokens** (min 44,960 · max 182,447)
- the prefix is re-read on every request → ~7.1 billion tokens

## Fixed prefix — configuration cuts (before / after)

| cut | label | before (median · n) | after (median · n) | delta |
|---|---|---|---|---|
| cut 1 | disabled 10 out-of-stack plugins + CLAUDE.md 41 -> 22 KB | 82,248 · 151 | — | **not measured** — needs a new session |

## Agent roles — how many runs, at what cost

Agent runs account for **10.3%** of total spend

| role | runs | starting prefix (total) | estimated $ |
|---|---:|---:|---:|
| `test-writer` | 90 | 5,657,819 | $863.83 |
| `developer` | 60 | 2,943,839 | $757.74 |
| `analyst` | 39 | 2,056,151 | $91.34 |
| `qa` | 35 | 1,487,008 | $309.30 |
| `doc-writer` | 8 | 369,481 | $13.58 |
| `general-purpose` | 7 | 726,502 | $114.85 |
| `Explore` | 4 | 171,978 | $17.14 |
| `architect` | 4 | 219,076 | $43.26 |
| `devops` | 3 | 201,440 | $6.66 |
| `unknown` | 1 | 46,412 | $1.52 |
| `designer` | 1 | 16,469 | $0.43 |
| `product-manager` | 1 | 50,671 | $1.33 |

## SDLC steps — how many times each one ran

| step | runs | dismissed (mentions) | example command |
|---|---:|---:|---|
| build | 1321 | 92 | `dotnet build <project>.Tests/<project>.Tests.csproj 2>&1 | tai` |
| unit test | 3248 | 665 | `npx jest --watchAll=false __tests__/format.test.ts 2>&1 | tail -` |
| typecheck | 731 | 17 | `npx tsc --noEmit 2>&1 | grep -E "error TS"; echo "TSC EXIT ${pip` |
| lint/format | 733 | 327 | `npx eslint src/pages/<feature>/<Component>.tsx src/test/` |
| coverage | 535 | 300 | `L=<tmp>/<session-dir>/coverage.log; dotnet test --collect:"XPlat` |
| e2e (playwright) | 329 | 64 | `npx playwright test --list e2e/specs/<spec>.spec.ts 2>&1 | tail` |
| e2e (maestro) | 1 | 11 | `cd <project>/.claude/worktrees/<branch> && maestro test` |
| secret scan | 74 | 110 | `gitleaks version; echo "---"; grep -rn "<canary-value>" backend` |
| SAST | 113 | 87 | `codeql pack download codeql/csharp-queries 2>&1 | tail -3 | cut ` |
| dependency CVE | 10 | 25 | `cd <project> && echo "=== dependency CVE scan ==="; dotnet list` |
| local ci gate | 15 | 15 | `git show HEAD:scripts/ci-local.sh 2>/dev/null | head -100` |
| md size gate | 355 | 34 | `cd ~/.claude && MD_ROOT="$HOME/.claude" bash scripts/md-size-gate` |
| md rule gate | 179 | 58 | `cd ~/.claude && git add scripts && git commit -q -m "fix(scripts` |
| git merge | 798 | 84 | `git merge --ff-only origin/dev && git log --oneline -1` |
| git push | 733 | 102 | `git push origin <sha>:refs/heads/<branch>` |
| deploy/publish | 3 | 10 | `echo "=== recent worker deploys ==="; npx wrangler deployments` |

⚠️ "—" means the step was not seen in this scan; it may run from inside another script.
⚠️ "dismissed" counts calls that only MENTION the command (a grep/ps/echo argument, or text written into a file).
