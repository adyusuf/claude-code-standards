# Measurement log — step and agent statistics

> **Generated file** — do not edit by hand; regenerate with
> `python3 scripts/step-stats.py --write`. The estimate table in
> `modes/role-selection.md` §8 is corrected with these numbers (never from a
> single measurement: at least three records, or one real end-to-end round).

Scope: 87 sessions + 253 agent runs, last 30 days

## Session prefix (system prompt + tool/skill listings + CLAUDE.md)

- sessions: **84** · model requests: **77,950**
- prefix median: **92,868 tokens** (min 44,960 · max 182,447)
- the prefix is re-read on every request → ~7.2 billion tokens

## Fixed prefix — configuration cuts (before / after)

| cut | label | before (median · n) | after (median · n) | delta |
|---|---|---|---|---|
| cut 1 | disabled 10 out-of-stack plugins + CLAUDE.md 41 -> 22 KB | 82,359 · 152 | — | **not measured** — needs a new session |

## Agent roles — how many runs, at what cost

Agent runs account for **10.2%** of total spend

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
| build | 1345 | 94 | `dotnet build <path>` |
| unit test | 3322 | 678 | `npx jest --watchAll <path>` |
| typecheck | 747 | 19 | `npx tsc --noEmit` |
| lint/format | 751 | 331 | `npx eslint <path> …` |
| coverage | 544 | 306 | `<var> grep -nE <arg> <file> <path>` |
| e2e (playwright) | 329 | 67 | `npx playwright <arg> --list <path>` |
| e2e (maestro) | 1 | 16 | `cd <path>` |
| secret scan | 87 | 124 | `gitleaks <arg> … -rn <arg> <path> --include` |
| SAST | 113 | 92 | `codeql pack <arg> <path>` |
| dependency CVE | 10 | 27 | `cd <path> <arg> <var> <arg> … <file> <var> <arg> … <file> <arg> ` |
| local ci gate | 15 | 17 | `git show <path> …` |
| md size gate | 9 | 9 | `cat <path>` |
| md rule gate | 6 | 12 | `cat` |
| git merge | 808 | 88 | `git merge --ff-only <path>` |
| git push | 746 | 108 | `git push <arg> <path>` |
| deploy/publish | 3 | 12 | `echo <var> <arg> … <var> <arg> … --name <arg>` |

⚠️ "—" means the step was not seen in this scan; it may run from inside another script.
⚠️ "dismissed" counts calls that only MENTION the command (a grep/ps/echo argument, or text written into a file).
