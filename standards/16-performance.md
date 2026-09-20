# Performance standards

## 1. Measure first

- **Never optimize without measuring.** Optimization based on a guess complicates the code and does not fix the problem.
- When a slowness report arrives: which endpoint/screen, what data size, which user, how long it takes, and what was expected.
- Profiling tools: APM/tracing on the server, `EXPLAIN ANALYZE` on the database, DevTools Performance + Lighthouse in the browser.

## 2. Budgets (exceeding one means work to do)

| Metric | Target |
|---|---|
| API p95 (simple read) | < 200 ms |
| API p95 (list/report) | < 500 ms |
| API p99 | < 1 s |
| LCP (web, 4G) | < 2.5 s |
| INP | < 200 ms |
| CLS | < 0.1 |
| Initial JS bundle (gzip) | < 250 KB |
| Mobile cold start | < 3 s |
| The fast CI gate | < 10 min |

Exceeding a budget is **a defect**, not a "we'll look at it later".

## 3. The database (the most common source)

- **N+1** — the most widespread problem. No queries inside a loop; use `Include` or a projection.
- No `SELECT *`; only the columns you need → a DTO projection.
- Pagination is mandatory; use keyset/cursor instead of a deep `OFFSET`.
- Indexes: on the columns you filter and sort by frequently. `EXPLAIN` shows the missing one.
- A `COUNT` is expensive — do not compute a total if infinite scrolling does not need one.
- In a read-heavy system, consider a read replica.
- Put a `statement_timeout` on long queries.

## 4. Cache — layer by layer

| Layer | What for | Watch out for |
|---|---|---|
| Browser/CDN | Static assets | A long `max-age` + content-hashed filenames |
| Edge (Cloudflare) | Static and rarely changing GETs | `19-cloudflare-and-edge.md` |
| Application (memory/Redis) | Expensive to compute, read often | **No cache without an invalidation plan** |
| Database | Query plans, materialized views | A freshness strategy |

- Every cache's **TTL and invalidation path** is written down. If "when does it go stale, who clears it?" has no answer, the cache is not added.
- User-specific data is never cached at the edge (`Cache-Control: private`). A response that varies by authorization never enters a shared cache — **that is a data-leak risk**.
- The cache key includes the tenant/user/locale dimension.
- Against a cache stampede: jitter plus a single recomputation (a lock).

## 5. Backend

- Async I/O; no synchronous blocking (it exhausts the thread pool).
- Response compression (Brotli/gzip).
- A large response → pagination or streaming (`IAsyncEnumerable`).
- On a hot path: no needless allocation, no needless `ToList()`, no needless serialization.
- Bulk work: batch it instead of one at a time; no `SaveChanges` inside a loop.
- An external service call: a timeout plus a circuit breaker; a slow dependency must not slow down the whole system.
- An expensive report or export → a background job + `202` + a status endpoint.

## 6. Frontend

- Route-based code splitting; lazy-import heavy libraries.
- Bundle analysis is done regularly; a large dependency is justified (moment→date-fns, lodash→single imports).
- A long list is virtualized or paginated.
- Images: the right size, a modern format (WebP/AVIF), `loading="lazy"`, and `width/height` set to prevent CLS.
- Fonts: `font-display: swap`, preload, subset.
- Needless renders: get the state placement right first, memoise second. Do not put frequently changing values in a context.
- Third-party scripts (analytics, chat) are deferred/async and justified — each one takes space from the budget.

## 7. Mobile

- `FlatList`/`FlashList`; `ScrollView`+`map` is forbidden.
- Images are cached and sized (`expo-image`).
- Animations run on the UI thread through Reanimated.
- No heavy synchronous work at start-up; a screen fetches data as it needs it.
- Reduce the number of network requests — mobile latency is high; one combined response instead of five small ones (but without multiplying endpoints, via `?include=`).

## 8. Load and resilience testing

- A k6/JMeter scenario for critical endpoints: the expected load, 2× the load, and the breaking point.
- What is measured: p95/p99, error rate, saturation (CPU/memory/connection pool).
- It runs before a release or weekly; the result is recorded and the **trend** is watched.
- The connection pool, the thread pool and the database's `max_connections` are tuned consistently with each other.

## 9. Catching a performance regression

- A bundle-size threshold in CI (a warning or a block when exceeded).
- p95 latency and error rate on a production dashboard; an alert when a threshold is crossed (`17-observability.md`).
- Metrics are watched for the first 24 hours after a new feature ships.

## 10. Never-do list

- ❌ Optimizing without measuring
- ❌ N+1, `SELECT *`, a list without pagination
- ❌ A cache with no invalidation plan
- ❌ Putting user-specific data into a shared cache
- ❌ Synchronous blocking (`.Result`, `.Wait()`)
- ❌ Adding a heavy library for a single function
- ❌ A 1000-row list without virtualization
- ❌ Sacrificing correctness for performance (a race condition, a missing lock)
