# Engineering Standards — index

This folder is the detail layer behind `~/.claude/CLAUDE.md`. It is **not loaded
automatically** — only the file matching the task at hand is read, which is why the
token cost stays low.

| File | Topic |
|---|---|
| `00-working-method.md` | The protocol for working with Claude: planning, approval, verification, context management |
| `01-product-design.md` | Problem definition, user stories, acceptance criteria, scope, MVP, ADRs |
| `02-ui-ux.md` | Design system, state design, responsive layout, accessibility, i18n |
| `03-coding-general.md` | Naming, file size, error handling, logging, dead code, comments |
| `04-dotnet.md` | .NET Web API layers, DI, EF Core, async, validation, configuration |
| `05-react.md` | React + TS structure, state, data fetching, forms, performance, tests |
| `06-mobile.md` | React Native / Expo, web-mobile parity, offline, store releases |
| `07-api-design.md` | REST contract, one API, pagination, error format, idempotency |
| `08-backward-compatibility.md` | Additive evolution, the deprecation lifecycle, expand/contract |
| `09-database.md` | Schema, migrations, indexes, transactions, auditing, soft delete |
| `10-test-strategy.md` | The test pyramid, unit-test rules, contract tests, the flaky policy |
| `11-playwright.md` | Web e2e: selectors, fixtures, isolation, CI |
| `12-maestro.md` | Mobile e2e: flow structure, testIDs, the device matrix |
| `13-pr-and-review.md` | Commits, branches, PR size, the review checklist and severity levels |
| `14-devops.md` | Environments, branching flow, CI/CD, containers, deploys, rollback, backups |
| `15-security.md` | AuthN/AuthZ, OWASP, secret management, data protection/PII, dependency scanning |
| `16-performance.md` | Budgets, N+1, caching, bundles, Core Web Vitals, load testing |
| `17-observability.md` | Logs, metrics, traces, correlation ids, alerts, incidents |
| `18-setup-and-environment.md` | Prerequisites, `SETUP.md`, **the secret/token inventory**, `.env`, the port map |
| `19-cloudflare-and-edge.md` | DNS, TLS, WAF, rate limiting, caching, **single-origin `/api`**, Tunnel, Workers, R2 |
| `20-hardening.md` | Security headers, firewall, SSH/RDP, IIS, Docker, DB, CI hardening |
| `21-backup-and-recovery.md` | 3-2-1, the inventory of what is backed up, RPO/RTO, **restore drills**, runbooks |
| `../docs/decision-log.md` | **The decision log** — rationale, measurements and retired rule text moved out of `CLAUDE.md` |
| `templates/` | Project CLAUDE.md, **module CLAUDE.md**, **SETUP.md**, PR, ADR and user-story templates |

## Order of precedence (when things conflict)

1. The user's explicit instruction in the moment
2. The project's own `CLAUDE.md` (a subdirectory beats the root)
3. `~/.claude/CLAUDE.md`
4. The standards in this folder

⛔ **One exception, and it is absolute: rule #29.** The 80% line-coverage threshold
per codebase grants no exceptions and **a project's `CLAUDE.md` cannot override it** —
level 2 does not beat it. `gate-core.sh` enforces this by refusing `coverage` as an
accepted gap by name, so the rule survives a conf file that tries to waive it.

If you are deliberately violating a standard, **write the reason in the code or the
PR**. No silent exceptions.
