# Global Working Rules

> This file enters context **in every project, every session and every agent
> turn** — it is the most expensive instruction file there is. Only **the rule
> itself** goes here; rationale, history and measurements move to
> `docs/decision-log.md` (`standards/00` §6a).
> Size gate: `scripts/md-budget.tsv`. Detailed standards live in
> `~/.claude/standards/` — index: `standards/README.md` or the
> `software-standards` skill.
> Project-specific rules live in the project's own `CLAUDE.md` and **override**
> the rules here — with one exception, #29.

## Language

- **English throughout** — prose, headings, file and folder names, identifiers,
  commit messages and comments. There is no second language in this rule set.
- User-facing text is never a raw string → an i18n key (the primary locale is
  mandatory, the secondary one ships as a placeholder).

## Default stack

.NET (Web API) + PostgreSQL/SQLite · React + Vite + TypeScript · React Native/Expo · Playwright (web e2e) · Maestro (mobile e2e) · GitHub Actions.

## Invariant rules (apply to every project)

1. **Small step first.** Before a large refactor, propose a small patch and wait for approval. No unrequested "while I was in there" improvements.
2. **Single source of truth.** Hard-coded URL / IP / port / host / API key is **forbidden**. Each tier has exactly one config module; other files never read `process.env` / `import.meta.env` / `IConfiguration` directly, they take a named import from that module. Fallbacks exist for DEV only and are defined in one place.
3. **Secrets never enter the repository.** Passwords, tokens, connection strings, certificates → env / secret store. The repo holds only `.env.example`. If a secret leaks: rotate first, clean up second.
4. **Backward compatibility is mandatory.** APIs and databases evolve **additively only**. Fields and endpoints are never deleted, renamed or retyped; they are marked obsolete and keep returning real values. → `standards/08-backward-compatibility.md`
5. **One API — web and mobile consume the same contract.** No platform-specific endpoints; differences are resolved in the UI layer. Business logic **never** lives on the client. → `standards/07-api-design.md`
6. **Authorization is fail-closed.** Default is DENIED. Never build semantics where "I forgot to configure it" means "open to everyone". Every endpoint checks authorization in the backend; the check in the UI is UX only.
7. **Validation in two places.** On the client for UX, in the API for security. Client-side validation is never sufficient on its own.
8. **Tests get updated.** If a file that has tests was touched, its tests are updated. If there are no tests, **say so explicitly**. A behaviour change is never merged untested.
9. **Never leave a 300+ line file.** Split it at its natural boundaries (modal, list renderer, form, sub-service). Splitting must not change behaviour; the main file stays an orchestrator.
10. **Ask before adding a dependency.** Write down why it is needed, what the alternative is, and its maintenance cost, then wait for approval.
11. **No magic strings.** Constants become enums/consts. Enum switches always carry a `default` branch (forward compatibility).
12. **Date format `dd/mm/yyyy`.** Locale-aware `toLocaleDateString`/`Intl` and dot-separated formats are forbidden. Transport and storage are always UTC ISO-8601.
13. **Search is always case- and accent-insensitive.** "sisman" ↔ "Şişman", "istanbul" ↔ "İstanbul" must match. Raw `.Contains` / `.ToLower.Contains` / `LIKE` is forbidden; a central normalizer is used.
14. **A new rule is never left verbal.** Once a permanent decision is made, write it **in the same turn** to the relevant `CLAUDE.md` (project) or to `~/.claude/standards/` (global). Do not finish the task while skipping this step.
15. **Report the truth.** If tests are red, say so with the output; name any step that was skipped. Never report completion on the basis of "it probably works".
16. **Setup is documented.** Every project carries `SETUP.md` + `.env.example` + a **secret/token inventory** (what it is, where to get it, where it is stored, who owns it, rotation). Any change that adds a tool, env var or secret updates these **in the same PR**. A clean machine must be set up by following the document, without guesswork.
17. **A single origin is preferred.** The API is served **under** the UI's domain (`app.example.com/api/*`); a separate `api.` subdomain is the exception and requires an ADR. The SPA fallback must **not** cover `/api/*`.
18. **A backup is only a backup if it has been tested.** 3-2-1 rule (one copy off-server), encrypted, **one restore drill per month**, and a record of the drill. A failed backup **and** a backup that never ran are alarmed separately. Not just the database: user files, configuration, certificates and secrets are all in scope. Take a manual backup before any `DROP` or bulk update.
19. **Security scanning is automatic.** Secret scan + dependency CVE on every push; SAST on pull requests; **OWASP ZAP** baseline after the test deploy. Before a release, the **OWASP Top 10 mapping table** is reviewed (`standards/15-security.md` §12). Critical/high findings block the merge. **SAST and SECRET SCANNING are steps in every project and also run locally** (`scripts/codeql-scan.sh`, `gitleaks detect`); CI calls the same script with the same thresholds — never two different rules in two places. A script that runs every gate in the pipeline locally must exist (`scripts/ci-local.sh`) so verification does not stop when CI is down. **A gate that did not run did not pass** — it is reported as "skipped" and the result is not green. False positives are suppressed only through **justified** triage; the rule itself is never switched off. → `standards/15-security.md` §13a-13c
20. **An autonomous background agent is never started without asking.** Nothing that keeps running turn after turn without user intervention — `/loop` autonomous mode, a self-retriggering `ScheduleWakeup` loop, a cron/schedule-based agent — is set up **without explicit prior approval**. If such a job is already running, **report it proactively**: what it is doing, what it is waiting for, what it is consuming, how to stop it. Never leave it running silently.
 - ⚠️ **APPROVED, but CONDITIONALLY.** The conditions and stop rules are in `~/.claude/modes/autonomous-run.md` — task list, definition of done, **$100** budget ceiling, stall brake, STOP on any irreversible action. If any condition is absent the run does not start and this rule applies in full again.
21-23. **[Delegated to #27 / removed]** The numbers are preserved so references do not break; the original text and rationale are in `docs/decision-log.md` §21-23.
24. **A self-administered completeness check is mandatory before saying "done".** Immediately before reporting a task as "done / finished / complete", in the same turn and without being asked, I apply this checklist to myself:
 - Re-read the user's **original request** (do not rely on a summarised memory of it) and verify item by item that every point in it is satisfied.
 - Were **edge cases and error paths** considered? (empty list, null, unauthorized access, concurrency, backward compatibility.)
 - Were **tests** (#8), **build/lint/format**, and where relevant the **SETUP.md/.env.example/secret inventory** updates (#16) actually run?
 - If the task spans multiple files or layers (API + client, migration + code, i18n `tr`+`en`), did **all** of them change?
 - If something is knowingly deferred, **list it explicitly in the final report** — never skip it silently.
 - Say "done" only after passing the check; do not narrate the check, fold its result into the report.
 → rationale and application notes: `docs/decision-log.md` §24
25. **The gate is SHARED and runs at every promotion; only running e2e is deferred to `prod`.** Two layers: `scripts/gate-core.sh <dev|test|prod>` owns the SHARED STEP SET (canonical copy in the configuration repository, a committed copy in every project), and the project's own `scripts/merge-gate.sh` stays the orchestrator (pull, merge, push, project extras) and CALLS the core. A project's gate cannot depend on a path outside the repository, because CI runners do not have the configuration checked out. `gate-core.sh <target> --list` prints what would run without running it.
 - **`feature/* → dev` and `dev → test`:** EVERYTHING EXCEPT RUNNING E2E — formatter/linter, typecheck, build, unit tests, **coverage: the 80% threshold per codebase (#29)**, secret scan, dependency CVE, SAST, backward-compatibility scan, the CLAUDE.md size and rule gates, and a **CHECK for missing e2e specs** (a warning on `dev`, blocking on `test`).
 - **`test → prod`:** the code must already be **deployed to the test environment** and the **FULL e2e suite** must run green against it (#33).
 - **A step that did not run did not pass.** A missing tool is reported as SKIPPED and the result is INCOMPLETE, never green; the exit code is the gate.
 - A project may ADD steps to the shared gate; it may never remove one. → the step list: `standards/13-pr-and-review.md` §4; rationale: `docs/decision-log.md` §25
26. **Once the work is planned: pull `dev` → branch/worktree off `dev` → work there → merge each task to `dev` SEPARATELY.** The order is binding:
 1. **First `git fetch` and update `dev`.** Do not branch from a stale base.
 2. **Create a new branch (or worktree) off `dev` and work there.** Never commit directly on `dev`.
 3. **When a task is finished, merge that task to `dev` on its own.** Do not collect several tasks into one commit/merge.
 4. **The USER decides on the `test` and `prod` promotions.** There is NO self-initiated merge to `test`/`prod`.
 5. **The formatter/linter runs once at the END of the task list**, not on every merge (#25).
 - ⚠️ **The configuration repository's own layout:** branches `dev` / `test` / `prod`. The live `~/.claude` is a **symlink into the main worktree, which stays on `prod`**; work happens in a separate `dev` worktree and reaches the live config only by promotion, which the **user** decides (`standards/00-working-method.md` §7a). Commit only your own diff. → rationale: `docs/decision-log.md` §26
27. **The operating mode (A/B/C/D/E) is selectable per project; the selection IS the approval.** The mode determines agent usage, review and approval policy together. Single source: `~/.claude/modes/README.md`; the selection lives in the project's `.claude/mode` file. To change it: `/working-mode <letter>`.
 - **A** Skill (no agents) · **B** Selective (`analyst`/`test-writer`/`doc-writer`) — **DEFAULT** · **C** Full team (9 roles) · **D** Wide team (14 roles) · **E** Fan-out (`Workflow`). The Agent Teams modes (X/Y/Z) are **archived** and not offered — `modes/archive/`.
 - ⚠️ **No agents in A; in B/C/D/E choosing the mode is the approval** — no separate question before a call, and the agent count plus estimated cost are **reported** at the end of the turn. Automatic delegation counts as a call too. **In C/D/E review is two-layered:** the `qa` agent performs the first pass and I verify the critical findings.
 - ⚠️ The mode **never** loosens any of these: approval on irreversible work (deploy, `DROP`, force push, sending anything to the outside world), the `test`/`prod` promotions belonging to the user (#26), the completeness check before "done" (#24), secrets staying out of the repo (#3).
 - **How to apply:** at the start of a session read the mode **in this order**: **a session-scoped selection** (written with `--tek`, not to the project file) → the project's `.claude/mode` → **B**. Otherwise **start in B and, if the work deserves it, PROPOSE the lowest sufficient mode in one line** — do not switch on your own. In a project with no mode file, B's three agents may be invoked without asking; the other eleven roles require C/D/E. If a mode name is given, run `/working-mode`. → rationale and measurements: `docs/decision-log.md` §27
28. **On every pass the auditor CHECKS for gaps and errors, SENDS WORK BACK, and GETS IT FIXED; cost is reported at every handoff.** On every turn that uses agents:
 - **The completeness-check block is mandatory.** Every role whose output someone else will rely on (`qa`, `analyst`, `devops`, `test-writer`, `product-manager`) closes its report with an **evidence block**: *Verification (command run / range read) · Item mapping (each requested item → file:line) · Not covered → Result: serious gap NO | YES.* The block is written even when the pass is clean. **The orchestrator writes one line per handoff** (evidenced `✅ clean` + cost) and the full block **at the end of the turn** and on every **"YES"**; it never swallows the role's own block. ⚠️ **This is a check, not a question:** the auditor does not ask "is anything missing?" — not the user, not the producing role. **What cannot be verified does not count as fine.**
 - **If something is missing it is SENT BACK, not escalated to the user.** The work returns to its producer (`qa` → `developer`/me → `qa` again); the hand-back carries **what is missing · with what evidence · what to do**. It reaches the user only for the stop reasons in §5 and at the ceiling — and even then as a **status report, not a question**.
 - **One clean pass is enough.** A single "no serious gap" is sufficient for a handoff. The `Verification` line **must** carry the command that was run or the range that was read. On "YES" the work goes back; when the fix arrives, **the same verification that surfaced the finding is re-run**. **Ceiling: the same work is sent back at most twice (3 passes)**; if it is still not resolved the chain stops and the user is **informed**, with unclosed findings listed individually as **open findings**. A "serious gap" is anything that affects behaviour, security, backward compatibility or data, or that leaves a requested item unmet.
 - **No handoff while a finding is open — the auditor gets it fixed.** A hand-back is not a note, it is **an order**. A finding closes only by (a) being fixed and evidenced, (b) the user explicitly saying "don't", or (c) being **reported as an open finding** with an out-of-scope justification — no finding is ever dropped silently. The end-of-turn report shows **closed vs. still open**.
 - **Cost is not deferred to the end of the turn.** One line per role handoff: that role's estimated cost + the turn's running total + distance to the threshold. Thresholds are **mode-dependent and two-stage**: B ~$12/**$25** · C ~$75/**$150** · D ~$130/**$260** · E ~$200/**$400** — a warning at half, a **stop** at the full figure. The autonomous run's $100 ceiling is independent.
 - **Three audit gaps are closed:** `analyst` also returns the **command** that produced its finding · `devops` output **goes through `qa`** · `product-manager` output goes to **user approval**. → detail `modes/role-selection.md` §2a, §3, §5-§8; rationale `docs/decision-log.md` §28
29. **Line coverage of AT LEAST 80% in every codebase — no exceptions.**
 - **The measure:** line coverage, **every codebase SEPARATELY** — backend · web · mobile Android · mobile iOS. Never averaged. An unmeasured codebase does not count as passing; it is reported as **"not measured"** and still blocks promotion.
 - **The denominator must be honest:** only **generated** code is excluded (EF migrations + `ModelSnapshot`, `obj/`, `*.g.cs`, `*.Designer.cs`, `.d.ts`, the tests, e2e/config). The exclusion list lives **in one place, with a reason per entry**. Removing hand-written product code from the list is loosening the threshold → **forbidden**.
 - **The gate:** it runs inside the shared `scripts/merge-gate.sh` at **every** promotion, `dev` included; below the threshold → exit code ≠ 0. CI calls the same script with the same threshold (#25).
 - **No loosening:** the threshold is not lowered and no exceptions are granted. **A project's `CLAUDE.md` CANNOT override this rule.**
 - **Fake coverage is forbidden:** e2e does not count towards this figure. Writing assertion-free tests is the same as loosening the threshold — an added test must catch a fault under mutation (`standards/10-test-strategy.md` §7).
 - **Adoption:** the **first session** opened in a project **measures** coverage, **installs** the gate if there is none, and reports the gap along with a plan to close it. No promotion is possible until the gap is closed. → rationale: `docs/decision-log.md` §29
30. **Email in test data goes to a REAL mailbox: `<account>+<variable>@gmail.com`.**
 - **Scope:** EVERY test address the system might send a message to — e2e (web and mobile), seed/e2e accounts in the test environment, data entered by hand in the integration environment, invitation/link recipients.
 - **Forbidden:** fake domains — `.test`, `.local`, `example.com`, `sample.*`.
 - **Single source:** the address is produced by **one helper** in the tests (the base is overridable via env, e.g. `E2E_EMAIL_BASE`); addresses are never written by hand into a spec or seed (#2).
 - **Out of scope:** tests whose sender is faked. → detail `standards/11-playwright.md` §4; rationale `docs/decision-log.md` §30
31. **The e2e run cycle: full run → identify failures → fix → run only what was fixed → I decide on a full re-run.**
 - **The WHOLE suite runs first**, without stopping at the first failure. Failures are **classified**: product bug · stale spec · data/fixture · environment.
 - **Failures are fixed** — each fix on its own branch with its own merge (#26). Raising retries or loosening assertions does not count as a fix.
 - **Then ONLY the fixed tests** (and those they could affect) run.
 - ⚠️ **E2E runs only against code that has reached the `test` environment.** While a fix is on `dev`, verification means **unit tests + tsc/lint** (#25).
 - ⛔ **Nothing ships to `prod` without e2e.** **The only exception is a hotfix:** when the user explicitly says "hotfix" it ships without e2e and the report reads "e2e skipped (hotfix)" — which does not count as passing.
 - **I decide whether to repeat the full suite** and report the reasoning: repeat it if the fix touched something shared · if the promotion record requires a full run · if some failures were environmental; if the fix is limited to a single spec, a targeted run is enough.
 - **A run that hit an environment limit is invalid**; it is not read as a product failure — parallelism is lowered and the run repeated. → detail `standards/11-playwright.md` §9a; rationale `docs/decision-log.md` §31
32. **Order: ALL the code first → then unit tests are written → then unit tests run; e2e is WRITTEN and run once the code reaches `test`.**
 - The planned work's code is written **in full**; tests are not run after every small change.
 - When the code is done, unit tests are written (#8), then the tests run **once**; anything red is fixed and only the relevant tests re-run.
 - **E2E is neither written nor run at the `dev` stage** — #33 narrowed this further: writing and running e2e belong to the pre-production gate.
 - #26 still holds: each task is written on its own branch and merged to `dev` **separately** once its unit run is green. → rationale: `docs/decision-log.md` §32
33. **E2E runs at the `prod` gate only, and the code must be on `test` first.**
 - **`feature → dev` and `dev → test`:** e2e is not RUN. The gate only CHECKS whether a spec is missing (#25) — no deploy wait, no status file.
 - **`test → prod`, in order:** 1) the code is deployed to `test` and the deploy is **verified** (the version endpoint reports this SHA) · 2) any missing spec is written and verified against the test environment · 3) the **WHOLE** e2e suite runs against `test` (#31's cycle applies to failures) · 4) nothing red ⇒ merge to `prod`. Red, stale or absent ⇒ no merge.
 - **No test environment (`E2E_BASE_URL` unset):** start the app locally (API + web, own test DB) and run the FULL suite there — this is the fallback, not a skip. The report reads "e2e ran locally (no test env)"; the version check is against the local SHA.
 - **The only exception is a hotfix:** the report reads "e2e skipped (hotfix)", which does not count as passing.
 → `docs/decision-log.md` §33

## Never-do list

The full list, including the items tied to numbered rules: `docs/decision-log.md` § Never-do list.

- ❌ Business logic / validation / authorization decided on the client alone
- ❌ Connecting to the database directly from a client
- ❌ Committing dead code that has been commented out
- ❌ Opening a PR without running the formatter (`dotnet format`, Prettier/ESLint)
- ❌ Deleting or renaming a field/endpoint (= delete + add)
- ❌ `SELECT *`, N+1 queries, a list endpoint without pagination
- ❌ A swallowed exception (`catch {}`), an error with no log
- ❌ Writing PII / tokens / passwords to the log
- ❌ Loosening tests "so they pass", papering over a flaky test with `retry`
- ❌ Pushing directly to `main`/`prod`
- ❌ Without user approval: production deploy, DB `DROP`, `git push --force`, deleting data, sending a message or publishing to an external service
- ❌ An untested backup ("we have backups" is not enough — a restore drill is performed)
- ❌ Invoking the `test-writer` and `migration-reviewer` subagents — strictly forbidden. The real protection is **the mode's role set**: no agent outside the mode's roles is ever invoked → #27, #28

## Working method (for Claude)

The full protocol is in `standards/00-working-method.md` (plan → approval →
execute, verification, context discipline, parallel sessions, work that requires
approval). In short: read a file before editing it · for work touching multiple
files, present a short plan first · never say "it works" without running build +
the relevant tests + lint/format, and if you did not run them **say "I did not
run them"** · when uncertain, finish the independent work first, then ask one
clear question · commit only your own diff and never use `--force` · get approval
for irreversible work (deploy, `DROP`, sending anything outward, deleting files).

## LIVE DASHBOARD during a long gate/run (PERMANENT, all projects)

When you start a gate, run or deploy that takes minutes (merge gate, CI, test
battery, deploy chain, migration), **publish an Artifact dashboard and keep it
current by republishing to the SAME URL throughout the run.** A text report does
not replace the dashboard; give both. The dashboard **must** contain: a weighted
overall percentage · per-item breakdowns · a live measurement (timestamp + raw
data) · open risks.

⚠️ **The percentage is MEASURED, not invented** — the dashboard states which
signal it was read from; if it cannot be measured, it says "cannot be measured".
The output of a long run is never piped into something that buffers
(`tail`/`head`) — it is written to a log file and the dashboard is fed from that.

→ Detailed rules: `standards/00-working-method.md` §10.
