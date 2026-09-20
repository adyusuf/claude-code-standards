# docs — index

| File | What it is |
|---|---|
| `decision-log.md` | The decision log: the rationale, measurements and retired text behind each numbered rule |
| `case-01-coverage-illusion.md` | Case: 95% reported coverage was 83% once generated code left the denominator; one codebase sat at ~14% behind an averaged number |
| `case-02-false-e2e-failures.md` | Case: 48 e2e failures that were an API rate limit, not product bugs — and why failures are classified before a re-run |
| `case-03-agent-cost-measurement.md` | Case: agent turns were 7.7% of cost, the orchestrator's cache reads 73% — measuring what agents actually cost |
| `case-04-the-audit-gap.md` | Case: nine roles, only one audited — the fix was mandatory evidence, not another agent |
| `benchmark-method.md` | How the measurements are produced and compared: what is and is not measured, the comparison rules, when a comparison is invalid, the reproduce commands |
| `measurement-log.md` | **Generated.** Aggregate statistics: prefix, per-role cost, how often each step ran (`scripts/step-stats.py`) |
| `measurement-ledger.tsv` | **Generated.** One row per session or agent run (`scripts/measurement-ledger.py`) |

`scripts/doc-check.py` fails when a file in this folder is missing from this table.
