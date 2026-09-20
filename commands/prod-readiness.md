---
description: Security, hardening, backup and observability audit before a production release
---

Audit whether this project is **ready to go live**. Do not guess — **verify**.
Mark anything you cannot verify as "could not be verified"; never count it as passed.

Read: `~/.claude/standards/` → `15-security.md` (§12 OWASP, §15 checklist), `20-hardening.md`,
`21-backup-and-recovery.md`, `17-observability.md`, `14-devops.md`, `19-cloudflare-and-edge.md`.
Also the project's own `CLAUDE.md` + `DEPLOY.md` + `SETUP.md`.

## 1. Security

- [ ] Any unauthenticated endpoint — list every `[AllowAnonymous]` / auth-free route and justify each one
- [ ] IDOR: which endpoints check resource ownership and which do not
- [ ] Secret scan clean (including the repository history)
- [ ] Dependency CVE scan: `dotnet list package --vulnerable`, `npm audit`
- [ ] The OWASP Top 10 mapping table (`15-security.md` §12) has been reviewed
- [ ] No PII/tokens in a sample of the logs

## 2. Hardening (verify with a real request where possible)

- [ ] `curl -I https://<prod>` → HSTS, CSP, nosniff, Referrer-Policy, Permissions-Policy present
- [ ] No `Server` / `X-Powered-By` leakage
- [ ] Swagger / debug / detailed errors **disabled** in production
- [ ] TLS: minimum version, certificate expiry
- [ ] Cloudflare: SSL mode Full (Strict), `/api/*` cache bypass, WAF + rate-limit rules
- [ ] Database port closed to the outside, the application running as a non-root user

## 3. Backup

- [ ] An automatic backup job exists **and the time it last ran** is known
- [ ] An offsite copy exists
- [ ] User files + configuration + certificates are in scope too
- [ ] **When the last restore drill was performed and how long it took** (is there a record)
- [ ] Alerts exist for a failed backup **and** for a backup that never ran
- [ ] RPO/RTO are written down

## 4. Observability

- [ ] `/health`, `/health/ready`, `/version` respond
- [ ] Central logging + error tracking (Sentry or similar) is active
- [ ] Alerts: 5xx rate, latency, uptime, disk, **certificate expiry**, backup
- [ ] A correlation id can be followed from the client all the way into the logs

## 5. Release and rollback

- [ ] Is the migration reversible; does it contain a `DROP`; was a backup taken
- [ ] Is the rollback plan written down; is there a feature flag
- [ ] Is the last e2e run **fresh and green**
- [ ] Do older mobile versions still work against this API (`08-backward-compatibility.md`)
- [ ] Are `SETUP.md`/`DEPLOY.md` current (could a from-scratch setup be done with them)

## Output

A **GO / NO-GO** decision with its reasoning. Then:
- 🔴 **Blocking** items (must be resolved before shipping)
- 🟡 **Risky** items (acceptable, but require written acceptance)
- ⚪ **Could not be verified** (no access or tooling — the user must check manually)

For every item, write concretely what needs to be done.
