# Documentation sync — the last step of EVERY phase

A phase is not finished while any Markdown file still describes the state before it.
Run this checklist at the end of phases 1, 2, 3 and 4 (and at the end of every 3 ⇄ 4
round), before the chat report. The chat report states that the sync ran and lists the
files it changed.

## 1. The inventory itself

| File | What must be true after the phase |
|---|---|
| Findings register | Every finding touched in this phase has its new status and evidence; findings discovered during the phase are added with the phase that found them; a finding proven wrong is corrected **in place** with a dated note (never silently rewritten) and its priority re-evaluated. |
| Each screen report | Header names the current phase and branch; the "what is wrong / what is missing" tables match the register (same ids, priorities, wording); the phase has its own section at the end (phase 2: tests written per finding with branch and commit; phase 3: the run table, failures, mutation proof; phase 4: fixes per round). Matrix cells change ✅ only after a phase-3 run proved the test green — a written but unrun test is not ✅. |
| Index | Phase column per screen (a screen with nothing to do in a phase says so); per-screen 🔴/🟡/🟢 counts of NOT-closed findings, the open · in progress · closed split, and the totals — all **recomputed from the register** (script below), never edited by hand; the root-cause and backlog sections still true. A red count that does not move between phases must be explainable from the status split. |

## 2. Project documents the phase can make stale

Check each; change only what the phase measured or proved.

- **Project `CLAUDE.md`** — test counts and coverage figures in the commands section
  (update only with numbers measured in this session, with the date), the known-gaps
  list (a gap closed or a new 🔴 found), any rule the phase showed to be false.
- **`SETUP.md` / `.env.example` / secret inventory** — anything the phase needed to make
  a suite run (an SDK path, an env var, a service) that the setup document does not say
  or says wrongly (global #16).
- **Decision docs** the findings reference (`docs/*-kararlar.md`, ADRs) — when a finding
  shows a documented decision is not what the code does, the finding says so; the doc is
  changed only when the user decides.

## 3. Stale-statement sweep

For every finding whose text, priority or status changed in this phase, search every
Markdown file for its id and for the old wording, and fix each hit:

```bash
grep -rn "F-0NN" <docs-dir> <project CLAUDE.md>        # every mention of a changed finding
grep -rn "<old phrase>" <docs-dir>                       # the superseded wording itself
```

## 4. Recompute the index counts

```python
import re, collections
rows = [[c.strip() for c in l.split('|')] for l in open(REGISTER) if l.startswith('| F-')]
# column 3 = screens (comma-separated names), column 4 = priority emoji
# column 9 = status: open / in progress / closed / won't fix / not a finding
prio = collections.defaultdict(collections.Counter)   # priority counts, closed excluded
stat = collections.defaultdict(collections.Counter)   # open · in progress · closed
for r in rows:
    status = r[9].split()[0].lower()
    for screen in SCREENS_BY_NAME:               # {'name as written in the register': index-row}
        if screen in r[3]:
            stat[SCREENS_BY_NAME[screen]][status] += 1
            if status not in ('closed', 'fixed', "won't", 'not'):
                prio[SCREENS_BY_NAME[screen]][r[4]] += 1
# write both back into the index rows; totals = the same counters over all rows
```

## 5. Report the sync

In the chat report, one line per changed file (`path — what changed`) and, if the
project documents were not touched, say why ("no measured count changed", "no setup
step was needed").
