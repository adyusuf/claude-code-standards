---
description: Audit the current changes against the global software standards
---

Audit the **pending changes** in this repository (`git diff` + `git diff --staged`;
if there is nothing, the last commit) against the standards under `~/.claude/standards/`.

If an argument is given ($ARGUMENTS), review only that scope (a file path, a directory or a topic name).

## Steps

1. Determine the scope of the changes with `git status` and `git diff`. If there are no changes, say so and stop.
2. Decide which standards the scope touches and read **only those**:
   - Backend/.NET → `04-dotnet.md`, `09-database.md`
   - Web/React → `05-react.md`, `02-ui-ux.md`
   - Mobile → `06-mobile.md`
   - Endpoint/DTO change → `07-api-design.md` + **`08-backward-compatibility.md` (mandatory)**
   - Test files → `10-test-strategy.md`, `11-playwright.md`, `12-maestro.md`
   - CI/deploy/infrastructure → `14-devops.md`, `19-cloudflare-and-edge.md`, `20-hardening.md`
   - Auth/data/authorization → `15-security.md`
   - A new env var/tool/secret → `18-setup-and-environment.md`
   - Backup / a migration `DROP` → `21-backup-and-recovery.md`
3. Also read the project's own `CLAUDE.md` — **a project rule overrides the global standard**.
4. Apply the §5 checklist in `13-pr-and-review.md`.

## Look specifically for

- A deleted or renamed field, endpoint or enum value; a new required field; a tightened validation
- Hard-coded URL/IP/port/key
- An unauthenticated endpoint, an IDOR hole, a fail-open permission
- N+1, `SELECT *`, a list without pagination
- A silently swallowed exception, PII/tokens leaking into the logs
- A 300+ line file, dead code, commented-out code
- A missing or loosened test
- An out-of-date `.env.example` / `SETUP.md` / Swagger / CLAUDE.md

## Output

Report the findings with the severity levels in `13-pr-and-review.md` §6:
**Blocking / Important / Suggestion / Note** — each finding with `file:line`, what is wrong,
why it matters, and the proposed fix.

If there is a blocking finding, warn prominently at the top. If there are no findings at all,
say that explicitly too; never manufacture findings.
