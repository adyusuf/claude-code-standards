# Security standards

## 1. Authentication (AuthN)

- Passwords: **never in plain text or reversible encryption**. Argon2id (preferred) or bcrypt (cost ≥ 12) / the ASP.NET Identity default.
- A minimum length of 12; prefer length plus a breached-password check over imposing complexity rules.
- Rate limiting on login attempts plus account lockout (with progressive delay). User enumeration must be impossible: "email or password is incorrect" (never which one).
- The password reset token: single use, short-lived (15-60 minutes), stored **hashed** in the database.
- MFA for sensitive roles (admin), at least TOTP.
- Tokens: a short-lived access token (5-15 minutes) + a refresh token (rotated, replaced when used, with reuse detection so theft is noticed).
- On logout the refresh token is invalidated server-side (deleting it on the client is not enough).

## 2. Authorization (AuthZ)

- **Fail-closed:** deny by default. `[Authorize]` as a global policy; open endpoints are explicitly `[AllowAnonymous]`.
- Authorization is checked **on every request** — hiding something in the UI is not security.
- **The IDOR check:** "may this user see or modify this record?" Resource ownership is verified on every access. `GET /orders/123` — whose is 123?
- A token claim is never trusted blindly; critical authorization is verified server-side against fresh data.
- Authorization logic lives in one place (a policy/handler); `if (role == "Admin")` is never scattered across controllers.
- If there is a union of a role group and a tier group: never put a permission in **the base** that the lowest tier must not have.
- An authorization change is protected by a test ("role X cannot see record Y").

## 3. Input validation and injection

- **Everything** from the outside world is validated: the HTTP body/query/headers/cookies, files, webhooks, and old data read back from the database.
- SQL: **always parameterized**. String concatenation is forbidden. Where an ORM is used, the raw SQL sections get extra scrutiny.
- Sort and filter field names are mapped through an **allowlist** (`?sort=` never reaches SQL directly).
- Shell execution is avoided entirely where possible; if it is unavoidable, use an argument array with no shell interpolation.
- Deserialization: loading unknown types (polymorphic deserialization) is disabled.
- Path traversal: a filename from a user is never appended to a path directly; normalize it and check it against the root directory.
- SSRF: no request is made to a URL supplied by a user; if it is unavoidable, use a scheme/host allowlist and block internal IP ranges.

## 4. XSS and the browser side

- React escapes by default — `dangerouslySetInnerHTML` is not used without justification, and where it is, DOMPurify goes with it.
- A Content-Security-Policy header is defined (`default-src 'self'`, no inline script — use a nonce or a hash).
- Token storage: **an httpOnly + Secure + SameSite cookie is preferred**. `localStorage` is exposed to XSS; if it is used, the risk is accepted in writing. (A single-origin deployment makes cookies easy — `14-devops.md` §8.)
- CSRF: with cookie-based auth, an anti-forgery token plus `SameSite=Lax/Strict`.
- Open redirect: `returnUrl` is restricted to an allowlist or to the same origin.

## 5. Security headers (the minimum)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=()
X-Frame-Options: DENY            (alongside CSP frame-ancestors)
```

- The `Server`, `X-Powered-By` and `X-AspNet-Version` headers are removed.
- Detail and the edge side: `20-hardening.md`.

## 6. Secret management

- A secret **never** enters the code, `appsettings.json`, a log, an error message, CI output or a screenshot.
- Storage: dev → User Secrets / a gitignored `.env`; CI → Actions Secrets; production → env / a secret store.
- The inventory lives in `SETUP.md` (`18-setup-and-environment.md`): what it is, where to obtain it, where it lives, who owns it, its validity/rotation.
- **The leak procedure:** 1) rotate immediately 2) impact analysis (was it used, per the logs) 3) clean the history 4) why it leaked → the preventive measure.
- Secret scanning in CI (gitleaks) plus a `pre-commit` hook are mandatory.
- No secret is embedded in a mobile bundle — there is no real secret on a mobile client (the bundle can be opened).

## 7. Personal data (data-protection law)

- **Data minimization:** personal data that is not needed is neither collected nor stored.
- Sensitive data (national ID, health, biometrics) is stored encrypted and access to it is logged.
- No PII in logs; where it is unavoidable it is masked (`a***@gmail.com`, `+90 5** *** ** 34`).
- Retention periods are defined; deletion or anonymization is automatic once the period expires.
- There must be a working technical path for a deletion request (the right to be forgotten) — including what it means for the backups.
- Production data is never copied into development or test **unmasked**.
- Third parties that process data (Cloudflare, the email provider, an AI API) are in the inventory and in the privacy notice.
- **Data sent to an AI/LLM:** customer PII is masked before it reaches the provider, or consent is obtained; what data goes out is documented.

## 8. Dependencies and the supply chain

- The lock file is committed; versions are pinned.
- CVE scanning in CI (`dotnet list package --vulnerable`, `npm audit`, Dependabot/Renovate).
- A critical/high vulnerability → the merge is blocked. If there is no patch, the risk acceptance is written down and time-boxed.
- For a new package: is it maintained, how many downloads, the last commit, the licence, the number of transitive dependencies.
- A typosquatting check — read the package name twice.
- CI actions are pinned to a commit SHA (`uses: actions/checkout@<sha>`), never to a tag.

## 9. File upload

- Allowed types come from an **allowlist** (the extension **and** the content/magic bytes).
- A size limit; a total quota.
- The filename is sanitized or regenerated (a GUID); the original name is kept in a separate field.
- Files are stored outside the web root or in object storage and are **never served directly** — use a signed URL or a proxy endpoint.
- User-uploaded content is served from a different origin where possible — XSS isolation.
- Virus scanning where feasible.

## 10. Rate limiting and abuse

- Rate limits per identity and per IP; tighter on sensitive endpoints (login, password reset, OTP, search).
- On exceeding: `429` + `Retry-After`.
- Bot/automation protection at the edge layer (`19-cloudflare-and-edge.md`).
- Expensive queries (reports, exports) are queued or limited.

## 11. Logging and detection

- Security events get their own logging: failed logins, authorization denials, password changes, role changes, secret access, bulk data downloads.
- The audit log is **immutable** (append-only); who, when, what.
- Abnormal patterns are wired to alerts (many 403s in a short window, many account attempts from one IP).

## 12. OWASP Top 10 — the mapping table

This table is reviewed before every release. Even "not applicable to us" has to be
written down.

| # | Risk | Our equivalent / control |
|---|---|---|
| **A01** | Broken Access Control | The fail-closed policy, `[Authorize]` on every endpoint, **IDOR testing** (resource ownership), authorization logic in one place, "role X cannot see Y" tests. The most common and most expensive class — the first thing looked at in review. |
| **A02** | Cryptographic Failures | TLS 1.2+ end to end (Full Strict), passwords with Argon2id/bcrypt, sensitive data encrypted, backups encrypted, tokens stored hashed, no money/PII in the logs |
| **A03** | Injection | Parameterized SQL, an ORM, an **allowlist** for sort/filter, no shell calls, React escaping + CSP for XSS, a template-injection check |
| **A04** | Insecure Design | An ADR + a threat model (§14 below), rate limiting, business rules on the server, idempotency in critical flows |
| **A05** | Security Misconfiguration | The whole of `20-hardening.md`: Swagger/debug off in production, security headers, no default passwords, directory listing off, CORS narrow |
| **A06** | Vulnerable & Outdated Components | The lock file, CVE scanning in CI (`npm audit`, `dotnet list package --vulnerable`, Dependabot), a critical vulnerability blocks the merge, actions pinned to a SHA |
| **A07** | Identification & Auth Failures | Rate limiting + lockout, error messages closed to enumeration, refresh rotation + reuse detection, MFA for admins, sessions terminated server-side |
| **A08** | Software & Data Integrity Failures | The lock file + SHA-pinned CI actions, signed artifacts, unsafe deserialization disabled, supply-chain checks (typosquatting) |
| **A09** | Security Logging & Monitoring Failures | `17-observability.md`: security events are logged, the audit log is append-only, abnormal-pattern alerts, a correlation id |
| **A10** | Server-Side Request Forgery | No request is made to a user-supplied URL; if it is unavoidable, a scheme+host allowlist, internal IP ranges (169.254/10./172.16./192.168.) blocked, redirect following disabled |

**API-specific (OWASP API Security Top 10):** BOLA/BFLA (object- and
function-level authorization), excessive data exposure (a DTO instead of the
entity), resource consumption (pagination + rate limiting), mass assignment
(over-posting → a separate input DTO). These are covered by the rules in
`07-api-design.md`.

**Mobile (OWASP MASVS):** secrets embedded in the bundle, insecure local storage
(tokens belong in `SecureStore`), weak TLS or disabled certificate validation
(`trustAllCerts` is **forbidden**), assuming a rooted/jailbroken device — there is
no real secret on a mobile client.

## 13. The scanning chain (automatic in CI)

> **Scope (global rule #25):** this chain runs **in full** on the `dev → test` and
> `test → prod` promotions. On a `feature/* → dev` merge it **does not run** — the
> single exception is the **pre-commit gitleaks** hook: it is local, takes seconds,
> and a leaked secret cannot be undone (it requires rotation), so it stays on for
> every branch.

| Kind | What it finds | Tool | When |
|---|---|---|---|
| **Secret scanning** | A secret that leaked into the repository | gitleaks / trufflehog | Every push + pre-commit |
| **SCA** | A vulnerable dependency | `dotnet list package --vulnerable`, `npm audit`, Dependabot/Renovate, OWASP Dependency-Check | Every push + weekly |
| **SAST** | Vulnerable patterns in the code | CodeQL, SonarQube, Roslyn analyzers, `eslint-plugin-security` | On the PR |
| **DAST** | Vulnerabilities in the running application | **OWASP ZAP** (a baseline scan in CI, a full scan periodically) | After deploying to the test environment |
| **Container** | CVEs in the image | Trivy / Docker Scout | On the image build |
| **IaC/config** | Misconfiguration | Checkov / tfsec | On an infrastructure change |

The rules:
- **A critical/high finding blocks the merge.** If there is no patch, the risk acceptance is **written down and time-boxed**.
- **SAST is a step in every project and must also be runnable LOCALLY.** A scan that depends on CI only speaks after the push, and usually in front of someone else; a scan you can run locally speaks before the commit. Hence every project carries `scripts/codeql-scan.sh` (or the language's equivalent), and CI calls the same script with the same threshold — never two different rules in two places. Detail: **§13a**.
- The ZAP baseline scan runs after every deploy to the test environment; a new "High" alert is posted as a comment on the PR.
- False positives are suppressed with a **narrow** exception (never by switching the rule off), with the reason in the comment.
- Scan results are retained — the trend is watched and the "always the same 40 warnings" situation is cleaned up.

### 13a. Running SAST locally (a mandatory step)

In every project SAST runs **the same way in two places**: on the developer's
machine and in CI. The single-source principle applies here too — the threshold,
the triage list and the reporter live in **one** file, and CI calls it.

**Setup (the CodeQL example):**

```bash
brew install --cask codeql          # macOS
codeql pack download codeql/<language>-queries
./scripts/codeql-scan.sh            # the scan + the gate
```

**What the script must satisfy:**

1. **The exit code is the gate.** It returns `1` if there is an untriaged finding with `sev >= 7.0` (CVSS high). "Printing a report and returning 0" is not a gate.
2. **A false positive is suppressed narrowly and WITH A REASON.** The rule is never switched off; the finding goes into the triage file by `ruleId + file`, with **why it is not real** written down. Line numbers are not used — as code shifts, the triage silently shifts with it.
3. **The database is built while watching the compile.** In compiled languages, if an incremental build compiles nothing, the database comes out **empty** and the scan looks "clean" — the most dangerous false negative. `/t:Rebuild` (or the language's equivalent) is mandatory.
4. **Generated and dead code is excluded** (`obj/`, `bin/`, `generated/`, `node_modules/`, old applications waiting to be ported). Otherwise real findings drown in the noise.
5. **If rule metadata cannot be read, the scan counts as FAILED.** In SARIF the rule list can live in two different places: `tool.driver.rules` (the CodeQL CLI) and `tool.extensions[].rules` (the GitHub codeql-action). A reporter that reads only one of them finds no severity at all in the other format and **passes everything**; CI turns green while nothing is protected. Read both, and error out if neither is present.
6. **The gate is verified by mutation testing.** With the triage list emptied, the gate must genuinely return `1`. If it does not, the gate is decorative.

**A note on private repositories (GitHub):** CodeQL **analysis is free**; what
costs money is **uploading** the findings to the "Security" tab (GitHub Advanced
Security). On a private repository the upload fails with
`422 Advanced security has not been purchased`. The right answer is not to remove
SAST but to keep analysing with `upload: false` and enforce the gate with your own
reporter. Even with `upload: false`, codeql-action reads the Actions API: the job
needs `permissions: actions: read`, or it fails with
`Resource not accessible by integration`.

### 13b. Running secret scanning locally (a mandatory step)

SAST's sibling, with the same discipline: it runs **the same way in two places**,
from one configuration file, and the exit code is the gate.

```bash
brew install gitleaks                                   # macOS
gitleaks detect --no-banner --redact --config .gitleaks.toml
```

**The requirements:**

1. **It scans the history, not the working directory.** Once a secret has been committed, deleting it in a later commit does not remove it from the history. `detect` (history) and `protect` (staged) are different jobs; the gate is `detect`.
2. **A false positive is suppressed BY VALUE, not BY PATH.** A blanket exemption such as "do not scan test files" is **forbidden**: test files are exactly where secrets leak most easily. The allowance is granted to the string itself, with its reason.
3. **The narrowness of the allowance is verified by mutation.** The SAME allowed pattern with a DIFFERENT value must still be caught. If it is not, the allowance is too wide and has effectively closed the gate.
4. **If the tool is not installed the result is "SKIPPED", not "PASSED".** A gate that did not run did not pass; the report must show that separately and the result must not be green.
5. **If a secret is found, the order is: rotate first, clean up second.** Removing it from the history (filter-repo/BFG) is the second step; the leaked key is valid until it is rotated.

**What happened once:** a repository produced two findings; both were test
constants, and one of them was the basis of a "is the key stored ENCRYPTED" test —
removing the value would have made the test meaningless. The right answer was not
to switch off the rule but to add those two strings to the allowlist with their
reason.

---

### 13c. Being able to run the pipeline locally

When CI is down (billing, quota, the network, a provider outage), verification
must not stop. Every project carries a single script that runs **the same gates in
the same order** as the pipeline: `scripts/merge-gate.sh <dev|test|prod>`, which
calls the shared `scripts/gate-core.sh` (#25). `gate-core.sh <target> --list`
prints the step list without running anything.

⚠️ This was called ci-local.sh (unbackticked on purpose — it is a name being
discussed, not a path that resolves) while it was still a plan, and nothing by
that name was ever written: the local runner and the merge gate turned out to be
the same script. Two names for one file is how a reference goes dead.

- The local run **may not be weaker** than the pipeline; two different rules in two places is where "it worked on my machine" comes from.
- It may be **stronger** locally: dependencies the pipeline does not install (a browser, say) are often present locally, so those tests run too.
- **A skipped step never passes silently.** The report says "SKIPPED" and the result is not green but **INCOMPLETE**.

**What happened once:** while the pipeline was not running at all because of
billing, the local script found a real break on its first run — the frontend build
was failing and had been pushed to two branches in that state.

---

**The in-depth checklist:** for sensitive or new modules, go through the OWASP
**ASVS Level 2** checklist by hand (identity, sessions, access control, input
validation, cryptography, errors/logging, data protection, communication,
malicious code, business logic, files, APIs, configuration).

## 14. Threat model (a new module / a risky change)

Short and practical — four questions:
1. **What are we protecting?** (data, money, reputation) Which record is the most valuable?
2. **Who attacks?** (an unauthenticated outsider, an authenticated but malicious member, a compromised account, an insider)
3. **How?** A quick pass with STRIDE: Spoofing / Tampering / Repudiation / Information disclosure / Denial of service / Elevation of privilege
4. **How would we notice?** Which log, which alert?

The output is 10-15 lines, added to the ADR or the module document.

## 15. Pre-release security checklist

- [ ] Every endpoint is authorized; the `AllowAnonymous` list was reviewed
- [ ] The IDOR check was tested on critical resources
- [ ] The secret scan is clean; new secrets were added to the inventory
- [ ] The dependency scan shows no critical vulnerability
- [ ] Security headers were verified in production (with a real `curl -I`)
- [ ] Swagger/debug/detailed errors are off in production
- [ ] Rate limiting is active on sensitive endpoints
- [ ] No PII/tokens in the logs (a sample was read)
- [ ] The TLS configuration and certificate expiry were checked
- [ ] Backups and the restore drill are current (`21-backup-and-recovery.md`)
