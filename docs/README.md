# docs — index

| File | What it is |
|---|---|
| `decision-log.md` | The decision log: the rationale, measurements and retired text behind each numbered rule |
| `case-01-coverage-illusion.md` | Case: 95% reported coverage was 83% once generated code left the denominator; one codebase sat at ~14% behind an averaged number |
| `case-02-false-e2e-failures.md` | Case: 48 e2e failures that were an API rate limit, not product bugs — and why failures are classified before a re-run |
| `case-03-agent-cost-measurement.md` | Case: agent turns were 7.7% of cost, the orchestrator's cache reads 73% — measuring what agents actually cost |
| `case-04-the-audit-gap.md` | Case: nine roles, only one audited — the fix was mandatory evidence, not another agent |
| `benchmark-method.md` | How the measurements are produced and compared: what is and is not measured, the comparison rules, when a comparison is invalid, the reproduce commands |
| `coverage-gap.md` | Line coverage of this repository's own scripts against the 80% rule (#29): the measured numbers per script, the plan to close the gap, and why shell is not measured |
| `measurement-log.md` | **Generated.** Aggregate statistics: prefix, per-role cost, how often each step ran (`scripts/step-stats.py`) |
| `project-nicknames.tsv` | **Local and git-ignored — holds real project folder keys, never commit it.** `<folder key><TAB><nickname>[<TAB><aliases>[<TAB>public]]`; the ledger and the reports show only the nickname, and `real-name-check.sh` searches the key and the aliases in every commit and message. A nickname may not contain a real project name |
| `measurement-daily-by-project.md` | **Generated, local, git-ignored.** Cost by day × project (nicknames), rewritten whenever the ledger is |
| `measurement-daily-by-role.md` | **Generated, local, git-ignored.** Cost by day × role (`main` = the conversation, the rest are agent roles) |
| `measurement-daily-by-kind.md` | **Generated, local, git-ignored.** Cost by day × kind (session / agent) |
| `measurement-daily-by-model.md` | **Generated, local, git-ignored.** Cost by day × model (a row is filed under the first model it used) |

`scripts/doc-check.py` fails when a file in this folder is missing from this table.
