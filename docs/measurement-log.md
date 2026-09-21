# Measurement log — step and agent statistics

> **Generated file** — do not edit by hand; regenerate with
> `python3 scripts/step-stats.py --write`. The estimate table in
> `modes/role-selection.md` §8 is corrected with these numbers (never from a
> single measurement: at least three records, or one real end-to-end round).

Scope: 163 sessions + 401 agent runs, all records

## Session prefix (system prompt + tool/skill listings + CLAUDE.md)

- sessions: **154** · model requests: **134,069**
- prefix median: **82,526 tokens** (min 36,365 · max 182,447)
- the prefix is re-read on every request → ~11.1 billion tokens

## Fixed prefix — configuration cuts (before / after)

| cut | label | before (median · n) | after (median · n) | delta |
|---|---|---|---|---|
| cut 1 | disabled 10 out-of-stack plugins + CLAUDE.md 41 -> 22 KB | 82,359 · 152 | 90,957 · 2 | **not measured** — only 2 session(s) after the cut, 3 needed (docs/benchmark-method.md) |

## Agent roles — how many runs, at what cost

Agent runs account for **8.3%** of total spend

| role | runs | starting prefix (total) | estimated $ |
|---|---:|---:|---:|
| `test-writer` | 90 | 5,657,819 | $863.83 |
| `general-purpose` | 62 | 3,099,593 | $335.31 |
| `developer` | 60 | 2,943,839 | $757.74 |
| `unknown` | 50 | 2,638,272 | $98.89 |
| `analyst` | 40 | 2,085,670 | $92.90 |
| `qa` | 36 | 1,508,839 | $322.78 |
| `ext:code-reviewer` | 23 | 1,404,997 | $191.07 |
| `Explore` | 8 | 309,965 | $31.20 |
| `doc-writer` | 8 | 369,481 | $13.58 |
| `ext:test-engineer` | 7 | 441,959 | $122.86 |
| `ext:security-auditor` | 5 | 29,601 | $9.34 |
| `architect` | 4 | 219,076 | $43.26 |
| `claude-code-guide` | 3 | 157,384 | $0.77 |
| `devops` | 3 | 201,440 | $6.66 |
| `designer` | 1 | 16,469 | $0.43 |
| `product-manager` | 1 | 50,671 | $1.33 |

## SDLC steps — how many times each one ran

| step | runs | dismissed (mentions) | example command |
|---|---:|---:|---|
| build | 2795 | 159 | `dotnet build <path> -c <arg> --nologo -v <arg>` |
| unit test | 5544 | 810 | `npx jest --watchAll <path>` |
| typecheck | 1182 | 37 | `cd web` |
| lint/format | 1228 | 420 | `dotnet format <path> --verify-no-changes -v <arg>` |
| coverage | 594 | 369 | `<var> grep -nE <arg> <file> <path>` |
| e2e (playwright) | 443 | 78 | `npx playwright <arg> --list <path>` |
| e2e (maestro) | 1 | 16 | `cd <path>` |
| secret scan | 108 | 160 | `gitleaks detect --no-banner --redact` |
| SAST | 202 | 140 | `codeql version --format` |
| dependency CVE | 150 | 51 | `npm audit <arg>` |
| local ci gate | 94 | 41 | `ls <path> … <arg> … -f <path>` |
| md size gate | 30 | 15 | `cat <path>` |
| md rule gate | 17 | 13 | `python3 - <arg> <path> <arg> … <file> …` |
| git merge | 1029 | 100 | `git checkout <arg>` |
| git push | 1027 | 134 | `git push <arg> <path>` |
| deploy/publish | 44 | 23 | `vercel deploy --prod` |

⚠️ "—" means the step was not seen in this scan; it may run from inside another script.
⚠️ "dismissed" counts calls that only MENTION the command (a grep/ps/echo argument, or text written into a file).
