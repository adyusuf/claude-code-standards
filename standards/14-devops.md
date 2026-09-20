# DevOps — environments, CI/CD, deployment

## 1. Environments

| Environment | Purpose | Data | Who deploys |
|---|---|---|---|
| **local** | Development | Seed / fake | The developer |
| **dev** | Integration | Seed | Automatic (on every merge) |
| **test** | Acceptance + e2e | Realistic, masked | Promotion with approval |
| **prod** | Live | Real | **Explicit user approval** |

- Every environment has its own config, its own secrets and its own database. Connection strings must never mix (put the environment name in the connection name).
- If test and prod are hosted on the same server there must be a **separate worktree + separate site + separate service + separate backup job**; mixing them writes test code into production.
- Environment variables never live in the repository; only `.env.example` (a valueless template) is committed.

## 2. Branch → environment flow

```
feature/* → dev → (approval) → test → (approval) → prod
```

- One direction only: no merging backwards. Even a hotfix is cut from `dev` and promoted quickly.
- A raw `git push` to `test`/`prod` is blocked (branch protection + a pre-push hook).
- Before every **promotion** (`dev → test`, `test → prod`): the gate is green, review has happened, and the e2e result is fresh.
- **Merging into `dev` is the exception (global rule #25):** only build + fast unit tests run (the formatter/linter runs **once at the end of the task list**, #26); review, security scanning and e2e do not run on `dev`.

## 3. The CI pipeline (fast to slow)

```
1. Lint + format verification      (~1 min)
2. Type checking (tsc / build)     (~2 min)
3. Unit tests                      (~3 min)
4. Secret scan + dependency CVE    (~1 min)
5. Backward-compatibility scan     (~1 min)
--- EVERY PUSH up to here ---
6. Integration tests (a real DB)   — on the PR
7. E2E (Playwright/Maestro)        — before a promotion / nightly
8. Load testing                    — before a release / weekly
```

- The fast gate must stay under 10 minutes; if it does not, parallelize or split it.
- Slow or stateful tests are never mixed into the fast gate.
- Every CI step must be runnable locally with the same command.
- If the hosted runner quota runs out, a self-hosted fallback should be defined (without rewriting the steps — a reusable workflow plus a `runner` parameter).

## 4. Build and artifacts

- The build happens **once** and the same artifact is promoted to every environment. No rebuild per environment (that risks the same code producing a different binary).
- Environment differences come from **configuration**, never from compile time.
- Artifacts are versioned and tagged with the commit SHA — the commit running in production is always knowable (the `/version` endpoint).
- Docker: a multi-stage build, a non-root user, a minimal base image, a `.dockerignore`, a pinned base tag (`:latest` is forbidden), and a health check.

## 5. Deployment

- **Zero downtime** is the goal: rolling or blue-green. If downtime is necessary it is announced in advance.
- Migrations run **separately from and before** the deploy; thanks to expand→migrate→contract (`08-backward-compatibility.md` §5) the old code also works with the new schema.
- An automatic smoke test after the deploy (`/health` plus two or three critical endpoints). If it is red: an automatic rollback or an alert.
- **The rollback plan is written before the deploy.** If there is a "we cannot undo this" situation, it is not deployed; it ships behind a feature flag instead.
- Feature flags: a risky new feature ships disabled and is enabled gradually. Flags are tracked in an inventory and **cleaned up** (a dead flag is technical debt).

## 6. Secrets and configuration

- Secret sources: GitHub Actions Secrets (CI), an env/secret store on the server, User Secrets/`.env` in development (gitignored).
- **If a secret is found in the repository:** **rotate** first, clean the history second. Deleting is not enough — it stays in the history.
- Secret scanning is mandatory in CI (gitleaks/trufflehog) plus a `pre-commit` hook.
- The secret rotation schedule is written down (at least yearly, and immediately when someone leaves).
- The inventory of every secret lives in `SETUP.md` (see `18-setup-and-environment.md`): what it is, where to obtain it, where it is stored, who owns it, when it is rotated.

## 7. Infrastructure

- Server configuration is never done by hand — use a script or IaC (a PowerShell/bash script, Terraform, Ansible). Every setting made by hand is lost on the next server.
- The installation steps live in `DEPLOY.md`; **a from-scratch install on a new server must be possible with that file alone**.
- DNS, certificates and firewall rules are documented too (`19-cloudflare-and-edge.md`, `20-hardening.md`).
- Certificates renew automatically, and a renewal failure **raises an alert** (never let one expire silently).

## 8. Single-origin deployment (the preferred topology)

**The API is served under the UI's domain:** `app.example.com/api/*`
A separate `api.example.com` subdomain is **the exception**, not the default.

Why:
- **No CORS** — preflight, header lists and the credentials tangle all disappear
- **Same-site cookies** work → httpOnly + `SameSite=Strict/Lax` become genuinely usable (you are not forced to put the token in `localStorage`)
- One TLS certificate, one DNS record, one WAF/rate-limit policy
- Where the backend runs (port, internal host, container) is invisible from outside
- Mobile uses the same base URL → one `BASE_URL`, one certificate-pinning target

How:
- A reverse proxy (Cloudflare/Nginx/IIS ARR) routes `/api/*` → the backend and everything else → the static SPA
- The SPA fallback: an unknown path → `index.html`, **but `/api/*` never falls through** (otherwise it returns HTML instead of a 404 and the client gets a JSON parse error)
- `/swagger` is open only in the test environment; in production it is closed or behind authentication
- Detail and the Cloudflare rules: `19-cloudflare-and-edge.md` §4

## 9. Backup and disaster recovery

- A daily automatic database backup plus a **weekly off-server** copy (a backup sitting on the same machine is not a backup).
- **A restore drill once a month** — an untested backup does not count as a backup.
- The RPO/RTO targets are written down: how much data loss and how much downtime are acceptable at most.
- Backups are encrypted, access to them is restricted, and their retention is defined.
- Files uploaded by users (blob/R2/S3) are in scope too — backing up only the database is incomplete.

## 10. Observability

`17-observability.md`. The minimum: central logging, error tracking (Sentry or
similar), an uptime check, a `/health` endpoint, disk/CPU/memory alerts, and a
certificate-expiry alert.

## 11. Never-do list

- ❌ Deploying by copying files to a server by hand
- ❌ A separate build per environment
- ❌ Deploying to production without approval
- ❌ Running a migration at the same time as the deploy, in a way that cannot be undone
- ❌ Writing a secret into the repository, a log, or CI output
- ❌ The `:latest` image tag
- ❌ A risky change with no rollback plan
- ❌ A backup that only ever sits on the same machine
- ❌ An open Swagger / debug endpoint / detailed error page in production
