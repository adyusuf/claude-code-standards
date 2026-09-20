---
name: software-standards
description: Loads the software standards that apply to every project (product design, UI/UX, .NET, React, mobile, API, backward compatibility, database, testing, Playwright, Maestro, PR/review, DevOps, security/OWASP, performance, observability, setup/secret inventory, Cloudflare/edge, hardening, backup). Use it before writing code, while reviewing, when planning a setup or deploy, or whenever "best practice", "standard" or "the rules" come up.
---

# Software standards

The standards live under `~/.claude/standards/`, **one file per topic**. Do not
read them all — read **the one the task is about**.

## Index

| Task | Read |
|---|---|
| New feature, scope, acceptance criteria, ADR | `01-product-design.md` |
| Screen, component, styling, accessibility, i18n | `02-ui-ux.md` |
| General coding, naming, error handling, logging | `03-coding-general.md` |
| .NET endpoint/service/EF Core/DI/config | `04-dotnet.md` |
| React page/component/state/data fetching/forms | `05-react.md` |
| React Native / Expo / store release | `06-mobile.md` |
| Endpoint contract, error format, pagination, idempotency | `07-api-design.md` |
| Changing a field/endpoint, deprecation, expand-contract | `08-backward-compatibility.md` |
| Schema, migration, index, transaction, soft delete | `09-database.md` |
| Unit/integration/contract tests, flaky policy | `10-test-strategy.md` |
| Web e2e | `11-playwright.md` |
| Mobile e2e | `12-maestro.md` |
| Commit, branch, PR, code review | `13-pr-and-review.md` |
| Environments, CI/CD, deploy, rollback, single-origin topology | `14-devops.md` |
| AuthN/AuthZ, OWASP Top 10, the scanning chain, data-protection law | `15-security.md` |
| Slowness, cache, bundle, Core Web Vitals, load testing | `16-performance.md` |
| Logs, metrics, traces, alerts, incidents, post-mortem | `17-observability.md` |
| Setup, prerequisites, **secret/token inventory**, `.env` | `18-setup-and-environment.md` |
| Cloudflare DNS/TLS/WAF/cache/Tunnel/Workers/R2 | `19-cloudflare-and-edge.md` |
| Server + application hardening, security headers, IIS/Docker | `20-hardening.md` |
| Backup, restore drill, RPO/RTO, disaster recovery | `21-backup-and-recovery.md` |

Templates: `~/.claude/standards/templates/`
(`project-claude-md.md`, `setup-md.md`, `pr-template.md`, `adr-template.md`, `user-story-template.md`)

## Common combinations

- **New feature (end to end):** 01 → 07 → 08 → (04 or 05/06) → 10 → 02
- **Code review / merge:** 13 → 08 → 15
- **New project setup:** 18 → 14 → 19 → 20 → 21
- **Preparing a production release:** 15 (§15 checklist) → 20 → 21 → 17 → 14
- **A "it's slow" complaint:** 16 → 09 → 17
- **Security review:** 15 (OWASP §12-13) → 20 → 19

## Precedence

The user's instruction right now > the project's `CLAUDE.md` > `~/.claude/CLAUDE.md`
> these standards. If you are knowingly breaking a standard, **write the reason
into the code or the PR** — there are no silent exceptions.
