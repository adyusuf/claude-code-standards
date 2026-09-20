# Server and application hardening

> Cloudflare is the first line but **not the only line**. The origin can be
> bypassed; the origin has to stand on its own.

## 1. Application level — what must be off in production

- [ ] Detailed error pages / stack traces (`ASPNETCORE_ENVIRONMENT=Production`)
- [ ] Swagger / the OpenAPI UI (or put it behind Cloudflare Access)
- [ ] The developer exception page, hot reload, source maps (no publicly reachable source maps)
- [ ] Seed/demo endpoints, test users, `/debug`, `/admin/tools`
- [ ] The `Server`, `X-Powered-By` and `X-AspNet-Version` headers
- [ ] Directory listing
- [ ] Default passwords (the database, any console, the admin account)

## 2. HTTP security headers (verified in production with `curl -I`)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()
Cross-Origin-Opener-Policy: same-origin
```

- CSP is rolled out in **Report-Only** first, violations are watched, and only then is it enforced.
- `unsafe-inline`/`unsafe-eval` are not acceptable; use a nonce or a hash if you must.
- The headers are defined in one place (middleware or the edge), never page by page.

## 3. TLS

- TLS 1.2 minimum, 1.3 preferred. SSLv3/TLS1.0/1.1 off.
- Weak ciphers (RC4, 3DES, CBC-SHA1) off.
- Certificates renew automatically, and **a renewal failure raises an alert**.
- HTTP → HTTPS permanent redirect (301).
- Internal traffic is encrypted too (Cloudflare↔origin: Full Strict).

## 4. Network / firewall

- Inbound only on the necessary ports. Ideally: **no inbound at all** (a Cloudflare Tunnel).
- Without a tunnel, 80/443 are open **only to Cloudflare's IP ranges**; the IP list is refreshed periodically.
- The database port (5432/1433) is **never open to the internet** — localhost or a private network only.
- Administrative access (SSH/RDP): closed to the public; behind a VPN / Cloudflare Access / an IP restriction.
- SSH: password authentication off, keys only; root login off; `fail2ban`.
- RDP: NLA on. Changing the default port is not security by itself — restricting access is what matters.

## 5. Operating system

- Automatic security updates on; critical patches within seven days.
- The application runs as a dedicated **non-root/non-Administrator** user.
- Least-privilege file permissions: write access to the application directory only where it is needed; the upload folder has **no execute permission**.
- Unused services and roles are disabled.
- Disk encryption; the backup disk is encrypted too.
- Time synchronization (NTP) — token validation and log correlation depend on it.
- Logs are centralized (if the server is compromised, local logs can be deleted).

## 6. IIS specifics (Windows)

- The application pool identity is separate and low-privilege; pools are isolated (one pool per site).
- **Test and production get separate sites + separate pools + separate physical directories** — mixing them writes test code into production.
- In `web.config`: `customErrors` on, `httpErrors` detail hidden, request filtering (request size, extensions).
- Request Filtering blocks hidden files (`.env`, `.git`, `appsettings*.json`, `*.bak`, `*.pdb`).
- Auto-pull/deploy jobs log which directory they updated, and there is a guard against the wrong environment.

## 7. Docker / containers

- A non-root user (`USER app`); a read-only root filesystem where possible.
- A minimal base image (alpine/distroless/`-slim`); the base tag is **pinned** (`:latest` is forbidden).
- `.dockerignore` keeps `.env`, `.git`, `node_modules` and secrets out of the image.
- Image security scanning (Trivy/Docker Scout) in CI.
- Secrets arrive through an environment variable or a secret mount; they are **never baked into an image layer** (a secret passed through `ARG` stays in the layers).
- Resource limits (CPU/memory) are set, so a runaway container cannot take down the whole machine.
- A health check is defined.

## 8. Database hardening

- The application user is **least privilege** (no DDL rights; migrations use a separate user).
- The application never connects as the `postgres`/`sa` superuser.
- Connections use SSL/TLS; `sslmode=require` (preferably `verify-full`).
- The listen address is restricted; `pg_hba.conf` is narrow.
- Default and sample databases and users are removed.
- Backups are encrypted with restricted access (`21-backup-and-recovery.md`).

## 9. CI/CD hardening

- Actions permissions default to `permissions: contents: read`; anything more is opened per job.
- Third-party actions are pinned to a **commit SHA**.
- Secrets must be **unreachable** in `pull_request_target` and in PRs from forks.
- A self-hosted runner is never used on a public repository (arbitrary code execution risk).
- Deploy keys are narrowly scoped and separate per environment.
- Secret masking in build logs is verified.

## 10. Periodic review (quarterly)

- [ ] Dependency CVE scan and upgrades
- [ ] OS + Docker image patches
- [ ] TLS configuration (SSL Labs / `testssl.sh`) — target A
- [ ] Security headers (securityheaders.com) — target A
- [ ] An open-port scan (`nmap` from outside)
- [ ] Access review: who has access to which console, and were the leavers removed
- [ ] The secret rotation schedule
- [ ] A backup restore drill
- [ ] A sample check of the logs for PII leakage
- [ ] Cleaning up unused subdomains / DNS records

## 11. Never-do list

- ❌ Running the application as root/Administrator
- ❌ Exposing the database port to the internet
- ❌ Swagger / detailed errors / source maps in production
- ❌ SSH with a password
- ❌ The `:latest` image tag
- ❌ Baking a secret into an image through a Dockerfile `ARG`/`ENV`
- ❌ Trusting Cloudflare and leaving the origin open
- ❌ Postponing security headers with "we'll add them later"
- ❌ Granting execute permission on the upload folder
