# Phase 1 — Audit

Output: one report per screen (`templates/screen-report.md`) and the index
(`templates/index.md`). No code changes.

## 0. Before anything

- Read the project `CLAUDE.md` (architecture, test commands, env requirements, the
  "known gaps" list — do not re-report what it already tracks unless it is still open
  and relevant, and then cite it).
- Read the operating mode (`.claude/mode`, default B). Mode A → no agents. Otherwise a
  read-only agent (`analyst`) may collect test names in parallel; you still verify.
- Detect the layers the repository actually has and note the command that lists or
  runs each (`references/list-tests.md`). A layer that does not exist is `—`, not `❌`.

## 1. Choose the screens

If the target is `top N` or `all`, list the routes (router file / navigation catalog)
and rank them by risk, highest first:

1. Money moves (charge, refund, payout, recurring, auto-debit)
2. Anonymous / public entry points (payment pages, links, callbacks)
3. Identity and session (login, password reset, token refresh, SSO hand-off)
4. Authorization-shaping screens (users, roles, permissions)
5. Rules that change an amount or eligibility (pricing groups, limits, licences)
6. Data mutation screens
7. Read-only lists and dashboards

Show the chosen list as a table (screen · route · why) and continue; the user can
reorder. Merge a screen with its satellite routes (result page, detail drawer) when
they share the same use cases.

## 2. Map the surface of one screen

Write down, with paths:

- the page file and the child components it renders (and which of them tests mock);
- every API call the page makes → endpoint → service method(s);
- the mobile counterparts (screen, actions/view-model, submission code);
- the e2e specs and mobile flows that touch the route.

## 3. Collect the tests per layer

Use `references/list-tests.md`. For each layer record file · test count · the test
names. Count `it.each`/`[Theory]` rows as one block unless the runner's count is used,
and say which.

## 4. Measure what is cheap to measure

- Run the web unit suite once with coverage and read per-file line coverage for the
  screen's files (one full run, reused for every screen in this session).
- For uncovered line ranges, open them: each range is either a missing use case, an
  unreachable guard (report it) or dead code (report it).
- Backend/mobile coverage per file is measured only if the project already produces it;
  otherwise write "not measured" — do not estimate.

## 5. Build the use cases from the CODE, not from the tests

Walk the page and the service top to bottom and name every behaviour a user or the
server can trigger: each action, each validation rule, each permission/licence/scope
decision, each state transition, each external call and each of its outcomes
(success · declined · error · timeout), each notification. Group them into UC-1…UC-n
with a one-line title. Categories that must be considered for each UC: happy path ·
boundary · validation error · permission denied · state conflict · external failure ·
concurrency.

## 6. Build the matrix

Rows = use cases, columns = layers. Cells: `✅` tested · `◐` partly (say what is
missing) · `❌` not tested · `—` the layer does not implement it. Under the matrix,
per UC, 2–4 bullets: what the tests actually assert, in plain words, and what they do not.

## 7. Hunt defects and unhandled cases

Go through `references/unhandled-case-checklist.md` for the screen's code paths. This
is where most of the value is: tests that exist can still leave the dangerous path
untested, and code can be wrong while every test is green.

## 8. Verify every finding

For each candidate finding: open the file at the line, read enough context to be sure,
and try to disprove it (is there a guard elsewhere? a global handler? a job that
reconciles?). Keep only what survives. Record the evidence as `path:line` or the
command. Unverifiable → say so, do not upgrade it to a finding.

## 9. Classify and prioritise

| Class | Meaning | Goes to |
|---|---|---|
| **Defect** | The code is wrong or violates a project rule | its own fix task (phase 2 writes the regression test WITH the fix, only if approved) |
| **Unhandled case** | A realistic situation no code path handles | a design decision or fix task |
| **Test gap** | Behaviour is right but no test proves it | phase 2 |
| **Dead code** | Unreachable or unused | deletion proposal |
| **Parity** | A layer lacks the feature | parity backlog, not a test gap |

Priority: 🔴 money, security or data loss · 🟡 wrong behaviour a user can hit or an
unguarded project rule · 🟢 hygiene.

## 10. Report and stop

Write the per-screen file and update the index. In chat: one table (screen · 🔴/🟡/🟢
counts · top finding), the three most serious findings in one sentence each, and the
list of tests proposed for phase 2 with an estimate of count per layer. Ask for
approval of that list — and separately for any defect fix. Then stop.
