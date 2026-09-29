# 23 — Tuning the delivery flow: cost, quality and speed (GUIDANCE, all projects)

> Moved verbatim from `00-working-method.md` §13 / §13a (29/09/2026, #9: that file
> had passed 300 lines). The old section numbers are kept below so existing
> references still resolve.

This is a **menu, not a mandate.** Each project first **measures its own flow**, then picks what fits and records its
choice in its own memory or `CLAUDE.md`. The worked example below (gandalf, 29/09/2026) is a source of ideas, not a
template to copy.

**Step 1 — measure before changing anything.** For a handful of finished tasks, record where the wall-clock went:
code · separate test writing · review (`qa`) · gate · waiting/re-runs. Without that split, every "speed-up" is a guess
(`00-working-method.md` §12.7). gandalf measured: code 36% · tests 33% · qa 18% · gate 14%; median ~1 h 40 min per finding, gate 11–14 min.

**Step 2 — sort each candidate with the quality test.** An option **lowers quality** if it reduces the number of
checks, the number of independent eyes, or a threshold. It **keeps quality** if it only removes waiting, ordering or
repetition. Only the second kind is taken without a separate user decision.

**Step 3 — score every candidate on all three axes** (↑ / ↓ / = for cost · quality · speed, with the evidence or
"estimate") and choose the balanced set. Typical candidates:

| Candidate | Cost | Quality | Speed | Watch out for |
|---|---|---|---|---|
| **Separate test database for agents / parallel runs** (the gate keeps its own) | ↓ fewer invalid re-runs; a little RAM | ↑ false reds stop hiding real ones | ↑ large where runs overlap | Changing containers is the user's call; document it in `SETUP.md` (#16) |
| **Test-writer in parallel with the developer**, writing from the contract, not the code | ↑ 10–20% of test-writer tokens (rework when the contract drifts) | = / ↑ tests cannot copy the implementation's mistake | ↑ test time overlaps code time | Only when the contract is clear (fix it in the prompt); otherwise code → tests |
| **`qa` in parallel with the test run** instead of after it | = (some test work wasted on a send-back) | = same diff, same depth | ↑ review stops being a wait | — |
| **Remove repetition inside the gate** (one run feeds both unit and coverage steps; scans alongside tests) | ↓ machine time | = same steps, same thresholds | ↑ measure first | Obey §12 (resource-based parallelism, stamped reuse) |
| **Batch 3–4 ready branches through one gate** on the combined tree (the default since 29/09/2026, #26) | ↓ fewer gate runs | ↑ interactions between branches get tested | ↑ throughput; ↓ one item waits for its batch | A red batch needs attribution |
| **Fix a flaky test the day it appears** (root cause, never retries) | ↑ small per flake | ↑ | ↑ no more false-red re-runs | — |
| ~~Same agent writes code and its tests~~ | ↓ | **↓ loses the independent eye** | ↑ | Withdrawn in gandalf: an independent test found a real ordering bug |
| ~~Skip `qa` for "low-severity" items~~ | ↓ | **↓ severity is known only after reading the code** | ↑ | Withdrawn in gandalf: a "low" channel choice hid a cross-tenant takeover |

**Step 4 — re-measure** after 3–4 tasks and report actual before/after figures; drop an option whose gain did not
appear. The gandalf balanced set: separate agent DB + `qa` parallel + batching + same-day flaky fixes in full; parallel
test writing only for medium/high items with a clear contract; gate de-duplication only after measuring the steps.

## 13a. The flow-research task — MANDATORY (PERMANENT, all projects)

The menu above is optional; **researching it is not.** Every project owns a standing research task: *how can our runs
(tests, gate, agent chain) become cheaper, faster and higher quality?* It is never skipped and never answered from
memory.

- **When:** at adoption (the first session in a project, alongside the #29 coverage measurement) · again after every
  **10 finished tasks or once a month**, whichever comes first · and immediately when a day produces **two invalid
  runs** (environment limits, false reds) or a gate exceeds its usual wall-clock by 50%.
- **What it covers, at minimum:** (1) the measured split of Step 1; (2) test infrastructure — database isolation per
  runner, template-database cloning instead of migrating per test, container reuse, sharding, affected-test selection;
  (3) the gate — repeated work, resource-based parallelism, stamped reuse (`00-working-method.md` §12); (4) the agent chain — which roles run
  in parallel, prompt size, batching, model choice per role; (5) flaky tests and their root causes.
- **Output:** a dated note in the project (e.g. `docs/flow-research.md`) — every candidate scored ↑/↓/= on cost ·
  quality · speed with its **evidence or the word "estimate"**, run through the quality test of Step 2, and a
  recommended balanced set. Options that keep quality are applied; options that lower quality, touch shared resources
  (containers, databases, CI) or change a gate's steps go to the **user's decision**.
- **Not done = open.** A due research task that did not run is listed as an **open item** in the end-of-turn report,
  never silently deferred. The next re-measurement (Step 4) closes the loop with before/after figures.

## 13b. Model per job — run on Sonnet, diagnose on Opus (PERMANENT, all projects)

Running a test suite, a coverage run or a merge gate and reporting its result is
**mechanical**: start it, wait, read the result block into the §10 table. Deciding
what a red or incomplete result MEANS is not.

| Job | Model | Who, by mode |
|---|---|---|
| Run a suite / coverage / gate; return the exit code, the result block and the command | **Sonnet** | **B:** `analyst` · **C/D/E:** `devops` · **A:** no agents — the orchestrator runs it |
| Classify a red result (#31: product bug · stale spec · data/fixture · environment), find the root cause, choose the fix | **Opus** | the orchestrator (or `qa` in C/D/E) |

- ⚠️ **The runner never diagnoses and never says green** for a step that did not run
  or was interrupted — it reports "did not run" / "interrupted" and hands back.
- ⚠️ **Diagnosis is a controlled comparison, not a first reading.** Measured
  29/09/2026: a red shell-coverage run was first read as "already red on `dev`";
  the real cause (a kcov long-path limit) only showed when the SAME commit was run
  from a short path and a long one side by side.
- The run's output goes to a log file and only the result block is read (§10); the
  full log is opened only for diagnosis.
- A turn that runs gates for long stretches may also run on Sonnet as a session
  model and switch to Opus when a result is red — the user's choice in the app.
- ⚠️ **A short gate is run directly, not delegated** (user decision 29/09/2026). A gate whose last
  measured run took **under a minute** — e.g. the `prod` gate of a repository with no e2e (21 s) —
  is run by the orchestrator: a fresh runner agent costs a fixed ~18k tokens whatever the gate's
  length, more than the gate itself. If the permission mode refuses the orchestrator (a `prod`
  gate is often classed as a production deploy), the USER runs it — it is never routed to an agent.
- ⚠️ **One runner agent per promotion chain** (user decision 29/09/2026). The first long gate
  (feature → `dev`) opens the runner; the following gates of the same chain (`dev → test`, and the
  next batch) are sent to that SAME agent (`SendMessage`), not to a new one.
- **Cost, measured 29/09/2026:** a fresh runner agent **17.7–18.3k tokens**, 3 tool calls, for a
  3-10 min gate (6 runs); the same agent resumed for another gate **2.6–2.7k tokens** (2 runs).
  The Opus side (the orchestrator running the same gate itself) is still not measured.
