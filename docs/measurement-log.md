# Measurement log — step and agent statistics

> **Generated file** — do not edit by hand; regenerate with
> `python3 scripts/step-stats.py --write`. The estimate table in
> `modes/role-selection.md` §8 is corrected with these numbers (never from a
> single measurement: at least three records, or one real end-to-end round).

Scope: 86 sessions + 253 agent runs, last 30 days  ·  measured: 20/09/2026 12:28

## Session prefix (system prompt + tool/skill listings + CLAUDE.md)

- sessions: **83** · model requests: **76,840**
- prefix median: **92,094 tokens** (min 44,960 · max 182,447)
- the prefix is re-read on every request → ~7.1 billion tokens
- measured total (list price): **$21,508**

## Fixed prefix — configuration cuts (before / after)

| cut | label | before (median · n) | after (median · n) | delta |
|---|---|---|---|---|
| 2026-09-20 09:39 | disabled 10 out-of-stack plugins + CLAUDE.md 41 -> 22 KB | 82,248 · 151 | — | **not measured** — needs a new session |

## Agent roles — how many runs, at what cost

Agent runs account for **$2,221** (**10.3%** of everything)

| role | runs | starting prefix (total) | estimated $ |
|---|---:|---:|---:|
| `test-yazar` | 90 | 5,657,819 | $863.83 |
| `gelistirici` | 60 | 2,943,839 | $757.74 |
| `analiz` | 39 | 2,056,151 | $91.34 |
| `qa` | 35 | 1,487,008 | $309.30 |
| `belge` | 8 | 369,481 | $13.58 |
| `general-purpose` | 7 | 726,502 | $114.85 |
| `Explore` | 4 | 171,978 | $17.14 |
| `mimar` | 4 | 219,076 | $43.26 |
| `devops` | 3 | 201,440 | $6.66 |
| `unknown` | 1 | 46,412 | $1.52 |
| `tasarimci` | 1 | 16,469 | $0.43 |
| `urun-yoneticisi` | 1 | 50,671 | $1.33 |

## SDLC steps — how many times each one ran

| step | runs | dismissed (mentions) | example command |
|---|---:|---:|---|
| build | 1321 | 92 | `dotnet build project-a.Tests/project-a.Tests.csproj 2>&1 | tai` |
| unit test | 3248 | 665 | `npx jest --watchAll=false __tests__/format.test.ts 2>&1 | tail -` |
| typecheck | 731 | 17 | `npx tsc --noEmit 2>&1 | grep -E "error TS"; echo "TSC EXIT ${pip` |
| lint/format | 733 | 327 | `npx eslint src/pages/productDetail/VariantSelector.tsx src/test/` |
| coverage | 535 | 300 | `L=/private/tmp/claude-501/-Users-me-ClaudeCode-project-f--claude-` |
| e2e (playwright) | 329 | 64 | `npx playwright test --list e2e/specs/borc.spec.ts 2>&1 | tail -3` |
| e2e (maestro) | 1 | 11 | `cd /Users/me/ClaudeCode/project-f/.claude/worktrees/plandan-devam` |
| secret scan | 74 | 110 | `gitleaks version; echo "---"; grep -rn "yanlis-parola-123" backe` |
| SAST | 113 | 87 | `codeql pack download codeql/csharp-queries 2>&1 | tail -3 | cut ` |
| dependency CVE | 10 | 25 | `cd /Users/me/ClaudeCode/project-d echo "=== BAĞIMLILIK AÇIĞ` |
| local ci gate | 15 | 15 | `git show HEAD:scripts/ci-local.sh 2>/dev/null | head -100` |
| md size gate | 355 | 34 | `cd ~/.claude && python3 - MD_KOK="$HOME/.claude" bash scripts/md` |
| md rule gate | 179 | 58 | `cd ~/.claude && git add scripts && git commit -q -m "fix(scripts` |
| git merge | 798 | 84 | `git merge --ff-only origin/dev && git log --oneline -1` |
| git push | 733 | 102 | `git push origin d401a71eefa6e931dfad5828b0c4825f33dfea20:refs/he` |
| deploy/publish | 3 | 10 | `echo "=== project-r worker'ının son deploy'ları ==="; npx wrangler d` |

⚠️ "—" means the step was not seen in this scan; it may run from inside another script.
⚠️ "dismissed" counts calls that only MENTION the command (a grep/ps/echo argument, or text written into a file).
