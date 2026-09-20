# Cloudflare / the edge layer

## 1. Division of roles

```
User → Cloudflare (DNS + TLS + WAF + rate limiting + cache) → Origin (IIS/Nginx/Docker)
```

Cloudflare is **the first line of defence**, not the only one. The origin must be
secure on its own (`20-hardening.md`) — Cloudflare can be bypassed.

## 2. DNS

- Application records are **Proxied (the orange cloud)** — the origin IP stays hidden.
- Unproxied records (mail, verification TXT) are deliberate and listed; any record that **leaks the origin IP** (an old `direct.`, `ftp.` or cPanel record) is deleted.
- TTL: automatic on proxied records. Lower it (300s) before a migration and restore it afterwards.
- DNSSEC on.
- If you send email: **SPF + DKIM + DMARC** records are defined. Aim for at least `p=quarantine` on DMARC.
- Unused subdomains are deleted (subdomain takeover risk).
- Every DNS record is documented in a table in `DEPLOY.md`.

## 3. TLS

- SSL/TLS mode: **Full (Strict)**. `Flexible` is **forbidden** — it leaves the Cloudflare↔origin hop unencrypted.
- A valid certificate on the origin: Let's Encrypt or a **Cloudflare Origin Certificate** (15 years, accepted only from CF).
- TLS 1.2 minimum (1.3 preferred). Old ciphers off.
- **Always Use HTTPS** on; **HSTS** on (`max-age=31536000; includeSubDomains`, and preload only once you are certain).
- **Authenticated Origin Pulls** on — the origin accepts only requests coming from Cloudflare (which closes the bypass).
- Certificate expiry is wired to an alert (`17-observability.md` §7).

## 4. The single-origin topology — the API under the UI

**Preferred:** `app.example.com/api/*` (not a separate `api.example.com`).

The gains:
- **CORS disappears entirely** (no preflight, no header allowlist, no credentials tangle)
- Same-site cookies work → httpOnly + `SameSite=Lax/Strict` become genuinely usable; you are not forced to put the token in `localStorage` (a smaller XSS surface)
- One certificate, one DNS record, one WAF/rate-limit policy
- Where the backend runs never leaks outward
- Mobile and web use **the same** base URL

On the Cloudflare side:
- **Origin Rules / Load Balancer:** `/api/*` → the backend origin (including the port), every other path → the static/SPA origin
- The SPA fallback rule **must not cover `/api/*`** — if it does, it returns HTML instead of a 404 and the client gets "Unexpected token <"
- **Cache bypass** for `/api/*` (see §5)
- `/swagger`, `/health/detail` and admin endpoints: in production either closed or behind **Cloudflare Access**

A separate `api.` subdomain only for: a different team or release cycle, a public API for third-party consumers, or genuinely different scaling needs. That requires an **ADR**.

## 5. Cache

| Path | Policy |
|---|---|
| `/assets/*`, hashed files | `Cache-Control: public, max-age=31536000, immutable` — long at the edge |
| `index.html` | `no-cache` (always revalidate) — otherwise the user is stuck on an old SPA |
| `/api/*` | **Bypass cache** (the default) |
| Public, rarely changing GETs | A short edge TTL + `stale-while-revalidate`, carefully |

The critical rules:
- **A user-specific or authorization-dependent response is never cached at the edge** — one user's data goes to another. `Cache-Control: private, no-store` + `Vary: Authorization, Cookie`.
- No cache is enabled before the `Vary` header is set up correctly.
- Purge the cache on the relevant paths after a deploy (targeted, rather than purging everything).
- When enabling a cache, write down the answer to "what happens when it goes stale, and who clears it".

## 6. WAF and bot protection

- The Managed Ruleset (OWASP Core) is on; false positives are excepted with a **narrow rule**, never by switching the ruleset off.
- Rate-limiting rules (the minimum):
  - `POST /api/auth/login` → 10/min per IP
  - `POST /api/auth/forgot-password`, OTP → 5/min
  - `/api/*` in general → a sensible upper bound per identity/IP
  - Search/export endpoints → tighter
- Bot Fight Mode / Super Bot Fight: watch it in log mode first so **your own clients and the mobile app are not blocked**.
- A country/ASN block only with a real justification (it risks cutting off legitimate users).
- Admin panels go behind identity with **Cloudflare Access** (Zero Trust) — a password must not be the only defence.
- Rule changes go to **Log** mode first, then **Block**.

## 7. Cloudflare Tunnel (closing the origin completely)

- A `cloudflared` tunnel serves traffic **without opening inbound 80/443** on the origin server.
- The gain: the origin IP is never exposed, there is no inbound port, and the firewall is outbound-only.
- The tunnel token belongs in the secret inventory; `cloudflared` runs as a service and restarts automatically.
- If no tunnel is used: the origin firewall is opened **only to Cloudflare's IP ranges**, plus Authenticated Origin Pulls.

## 8. Workers / Pages / R2

- **Workers:** edge logic (routing, A/B, header injection, a lightweight API). Business logic never moves into a Worker — the real logic stays in the backend.
- Worker secrets are set with `wrangler secret put`; no secret is written into `wrangler.toml`. `wrangler.toml` is committed, the secrets are not.
- Environments are separated with Worker environments (`[env.test]`, `[env.production]`), not by copying Workers.
- **Pages:** suitable for deploying a static SPA; preview deployments are **closed to search engines** and behind Access where necessary.
- **R2:** user files. The bucket is never made public; use a **signed URL** or a Worker proxy. Upload size and type limits are validated on the application side too. R2 content is within backup scope (`21-backup-and-recovery.md`).
- Cloudflare resources are managed with Terraform/wrangler where possible; any change made by hand in the console is written into `DEPLOY.md`.

## 9. API tokens

- The Global API Key is **never used**. Create a narrowly scoped **Custom Token** (only the zone and permissions needed).
- Tokens live in the secret inventory (`18-setup-and-environment.md` §4); rotation every six months.
- In CI, a separate token per operation (cache purge, a DNS record).

## 10. The real client IP

- On the origin, read the `CF-Connecting-IP` header; never trust `X-Forwarded-For` blindly.
- In .NET, the `ForwardedHeaders` middleware runs **only with a list of trusted proxies** — otherwise the IP can be spoofed and rate limiting and logs are misled.
- Logging and rate limiting use the real IP.

## 11. Setup checklist (a new domain)

- [ ] The DNS record is proxied; no old record leaks the origin IP
- [ ] SSL mode is **Full (Strict)**; the origin has a valid certificate
- [ ] Always Use HTTPS + HSTS on
- [ ] Authenticated Origin Pulls or a Tunnel is active
- [ ] The `/api/*` origin rule is correct; the SPA fallback does not cover `/api/*`
- [ ] `/api/*` bypasses cache; `index.html` is `no-cache`; static assets are immutable
- [ ] The WAF managed ruleset is on; rate-limit rules are defined
- [ ] Admin endpoints are behind Access or closed; Swagger is off in production
- [ ] Security headers verified end to end (`curl -I https://...`)
- [ ] SPF/DKIM/DMARC (if there is mail), DNSSEC on
- [ ] Certificate-expiry and uptime alerts are set up
- [ ] Every record, rule and token is documented in `DEPLOY.md` + the secret inventory

## 12. Next.js / OpenNext ISR — choosing the cache store

In a Next.js application deployed to Cloudflare Workers with OpenNext, ISR needs
**three pieces**; if one is missing it breaks silently:

1. `open-next.config.ts` → the `incrementalCache` override
2. `open-next.config.ts` → the `queue` override
3. `export const revalidate = <seconds>` on the pages

The symptom of each missing piece:

| Symptom | Cause |
|---|---|
| `x-nextjs-cache: MISS` on every request, high TTFB | No `incrementalCache` → a "dummy" cache, so the page renders on every request |
| `x-nextjs-cache: STALE` forever, content frozen | No `queue` → the stale page is never refreshed |
| The cache holds but the content never changes | No `revalidate` on the page → Next treats it as valid forever |

⚠️ A route showing as `○ Static` in the build output does **not** mean it is
served statically at runtime. The behaviour is measured from the
`x-nextjs-cache` header with `curl -sI`, never inferred from the build output.

### The cache store: R2, not KV

If the cache is purged when content is published (a CMS webhook → a purge
endpoint), **do not use KV**:

- **Consistency:** KV is eventually consistent; a delete propagates worldwide in roughly 60 seconds. You purge, and other regions still serve the old page. R2 is strongly consistent — a deleted object is gone everywhere at once.
- **Quota:** the KV free tier is **daily** and narrow (1,000 writes, 1,000 deletes, 1,000 lists, 100,000 reads per day). Since one purge deletes hundreds of objects, in practice you get **a few purges a day**. The R2 free tier is **monthly**: 1M Class A (write/delete/list), 10M Class B (read), 10 GB.

Create the bucket with a location hint near your audience (`--location eeur`, for example).

⚠️ The `withRegionalCache` wrapper is **not used** in a purge scenario: it puts a
per-data-centre Cache API layer in front of R2, and by OpenNext's own warning that
layer may fall out of sync with the store when cache purging is not in effect —
so you purge and the old page is still served.

⚠️ **Turn off the CDN in the CMS client** (`useCdn: false` in Sanity, for
example). With ISR in play the client is called per revalidation, not per request,
so the CDN's load benefit is gone. In exchange, a render right after a purge reads
**stale** data from the CDN and caches that, pushing freshness to the next cycle.

### Verification

`wrangler dev` locally, then in production:
`MISS` (first) → `HIT` → `STALE` after the `revalidate` window → `HIT` + new content.
Also measure the **publish-to-visible time** (a change in the CMS → it appears on the site).

## 13. Never-do list

- ❌ SSL mode `Flexible`
- ❌ Using the Global API Key
- ❌ Leaving the origin open to the whole internet (with no CF IP restriction or tunnel)
- ❌ Caching an authorization-dependent response at the edge
- ❌ Caching `index.html` for a long time
- ❌ Moving business logic into a Worker
- ❌ Making an R2 bucket public
- ❌ Building rate limiting on top of `X-Forwarded-For`
- ❌ Failing to document a change made by hand in the console
- ❌ Keeping a purged ISR cache in KV (eventual consistency + the daily quota)
- ❌ Enabling an incremental cache without defining a `queue` (the content freezes forever)
- ❌ Assuming runtime cache behaviour from the build output — `x-nextjs-cache` is measured
