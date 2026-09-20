# Benchmark method — how the numbers in this repository are produced and compared

Every cost, prefix and step figure here comes from the session transcripts in
`~/.claude/projects`, through two generated files: `measurement-log.md` (aggregates)
and `measurement-ledger.tsv` (one row per session or agent run). This page says what
they measure, what they cannot, and when a comparison between two of them is invalid.
A number that breaks these rules is not reported as a finding.

## What is measured

| Quantity | Source | Where |
|---|---|---|
| Tokens per request: input, output, cache write, cache read | the `usage` field of each assistant record | ledger columns `input` … `cache_read` |
| Cost | those tokens × the **API list price** table in `scripts/step-stats.py` | ledger column `usd` |
| Fixed prefix (system prompt + tool/skill listings + `CLAUDE.md`) | the first request of a session | `measurement-log.md`, prefix section |
| Role of an agent run | the `subagent_type` of the `Agent` call that started it | ledger column `role` (`main` for a session) |
| How often an SDLC step ran | shell-command patterns in `tool_use` blocks | ledger column `steps`, `measurement-log.md` |
| Configuration change points | `scripts/measurement-cuts.tsv` | ledger column `cut` |

## What is NOT measured

- **A bill.** `usd` is a list-price proxy for consumption. A subscription, a
  discount or a price change makes it differ from what anyone paid.
- **Wall-clock time.** The mode documents' speed claims (C 20–40%, E 50–70%) are estimates.
- **Quality.** No column says whether an agent's output was right. Cost is not value.
- **The mode multipliers** in `modes/README.md` (1.15x … 14x). No mode comparison
  has been measured; they are labelled estimates there and stay estimates here.
- **A step run from inside another script** (a gate that calls `gitleaks` itself is
  invisible). That is "not seen", never "zero".
- **Anything before the oldest surviving transcript.** Claude Code deletes old
  transcripts; the ledger keeps a row once it has been written, but cannot write one
  it never saw.

## How to compare

1. **Same cut only.** Rows with different `cut` values ran under different
   configurations. The point of a cut is to compare the medians before and after it.
2. **Medians, and always the count.** Report `median · n`. A mean is dragged by one
   long session; a figure without `n` cannot be judged.
3. **At least three records** before a figure changes a table or a rule, or one real
   end-to-end round (the floor `modes/role-selection.md` §8 already applies). A single
   run is an anecdote.
4. **Same kind, same role, same model.** A `session` row is the whole conversation, an
   `agent` row one delegated run. Different models have different prices: compare
   token counts across models, dollars only within one.
5. **Ignore the row of a session that is still running.** Its totals grow until it
   ends; the next `--write` replaces it.
6. **Record every configuration change as a cut** (append a line to
   `scripts/measurement-cuts.tsv`) *before* working under it. The "after" side fills
   itself from new sessions; until it has three rows the result is "not measured".

## When a comparison is invalid

- The two sides differ in **more than the one thing** you changed (a new model and a
  smaller `CLAUDE.md` in the same period cannot be told apart).
- One side has **fewer than three rows**.
- The cut falls **inside** the window and the boundary session is counted on both sides.
- The workloads differ in kind (a documentation task against a migration).
- A **pricing table change** in `step-stats.py` sits between the two sides: recompute
  both, or compare tokens.
- The step counts of scripts renamed since (`step-stats.py` says which) are compared
  across the rename.

## Reproduce

```bash
python3 scripts/measurement-ledger.py --write     # merge new rows into the ledger
python3 scripts/step-stats.py --write             # regenerate the aggregate log
python3 - <<'PY'                                  # median list-price cost per kind/role/cut
import csv, statistics, collections
rows = csv.DictReader((l for l in open('docs/measurement-ledger.tsv') if not l.startswith('#')), delimiter='\t')
groups = collections.defaultdict(list)
for r in rows:
    groups[(r['kind'], r['role'], r['cut'])].append(float(r['usd']))
for key, values in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    print(key, 'n=%d' % len(values), 'median=$%.2f' % statistics.median(values))
PY
```

`modes/role-selection.md` §8 also holds a hand-written ledger of early `qa` turns.
New records belong in `measurement-ledger.tsv`, which needs no hand entry.
