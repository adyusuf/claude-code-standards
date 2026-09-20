# Observability — logs, metrics, traces, alerts

> The fundamental question: **"When something breaks, how do we notice, and where
> do we look?"** A feature with no answer to that is half a feature.

## 1. Logs

- **Structured** (JSON/key-value). Not string concatenation but a message template:
  `_log.LogInformation("Order {OrderId} cancelled, member {MemberId}", orderId, memberId)`
- Levels:
  | Level | When | Example |
  |---|---|---|
  | `Debug` | Development only | Query detail |
  | `Information` | A business event | "Member created" |
  | `Warning` | Expected but unwanted | "External service slow, retrying" |
  | `Error` | An operation failed | "Order could not be saved" |
  | `Critical` | The system is at risk | "Cannot connect to the database" |
- **Never written to a log:** passwords, tokens, card numbers, national ID numbers, a full email address or phone number (mask them), a full request body, any secret.
- No logging inside a loop — log a summary instead.
- In production, `Information` and above; `Debug` off (cost plus privacy).
- Log retention and its cost are defined.

## 2. Correlation / trace id

- Every request carries a **correlation id** (`traceparent` / `X-Correlation-Id`).
- If the client sent one it is used, otherwise one is generated; it is **returned in the response** and appears in the error body (`traceId`).
- Background jobs and queue messages carry the id too, so they can be tied back to the triggering request.
- When a user says "I got an error", the traceId on their screen must find the log in a single query.

## 3. Metrics

**The golden signals** (for every service):
- **Latency** — p50/p95/p99, per endpoint
- **Traffic** — requests per second
- **Errors** — the 4xx / 5xx rate
- **Saturation** — CPU, memory, disk, database connection pool, thread pool

**Business metrics** (the genuinely valuable ones):
- Login success rate, sign-ups, orders, payment failures, email delivery success
- If a business metric drops, something is broken even when every technical metric is green.

Tooling: OpenTelemetry → Prometheus/Grafana, or a hosted APM.

## 4. Traces

- End to end with OpenTelemetry: HTTP → service → database → external call.
- The trace must show **where** a slow request became slow.
- Sampling: 1-10% normally, 100% for failing requests.

## 5. Error tracking

- Sentry or similar: uncaught exceptions, client-side JS errors, mobile crashes.
- Every error carries: the version (commit SHA), the environment, a user id (not PII), the correlation id, and breadcrumbs.
- After a new release the error rate is watched **comparatively** (regression detection).
- Noise is cleaned up — an alert everyone ignores is not an alert.

## 6. Health checks

- `/health` — liveness (is the process up)
- `/health/ready` — readiness (are the database, cache and critical external services reachable)
- `/version` — the running version + commit SHA + build time
- The post-deploy smoke test uses these; the load balancer watches readiness.

## 7. Alerts

**Alerts that must exist:**
- [ ] The 5xx rate crossed its threshold
- [ ] p95 latency crossed its threshold
- [ ] The application is down (an uptime check, from outside)
- [ ] Disk / memory filling up
- [ ] **A certificate expires in under 21 days**
- [ ] **The backup job failed, or never ran at all**
- [ ] A queue is backing up / a background job is stuck
- [ ] A critical business metric dropped abnormally (e.g. no logins for an hour)
- [ ] Security: many 403/401 in a short window, many account attempts from one IP

The rules:
- An alert **calls for action**; information that needs no action is a dashboard, not an alert.
- Every alert has a **runbook**: what it means, what to do first, who to notify.
- A false positive is either fixed or removed — alert fatigue makes you miss the real incident.

## 8. Dashboard

One screen must show: request volume, error rate, p95 latency, active users, the
critical business metric, the time and version of the last deploy, and the
current backup status.

After a deploy, that screen is watched for **the first 30 minutes**.

## 9. Incident management

1. **Detection** — an alert or a user report
2. **Assessment** — impact (how many users, is there data loss) and severity
3. **Stop the bleeding** first: roll back / turn off the feature flag / cut the traffic. Root cause **afterwards**.
4. **Communication** — a status notice to affected users (if it will take a while)
5. **Resolution** and verification (did the metrics return to normal)
6. **Post-mortem** — within 48 hours, **blameless**: what happened, the timeline, why it was not noticed, why it took this long, and which two or three actions prevent a repeat

The output of a post-mortem is **action items**; an item with no owner and no date counts as unwritten.

## 10. When adding a new feature

- [ ] Was a business log at `Information` level added to the critical flow?
- [ ] Are the error paths logged at `Error` (with the correlation id)?
- [ ] Is there a business metric worth watching?
- [ ] Which alert will fire when it breaks?
- [ ] Is there anything to add to the dashboard?
