# .NET Standards (Web API)

## 1. Layers

```
Controllers/Endpoints  → the HTTP contract, model binding, authorization, status codes
Services               → business logic, the transaction boundary, domain rules
Data (DbContext/Repo)  → queries, persistence
Contracts (DTO)        → the types exposed outward
Domain (Entity/Enum)   → the model
```

Rules:
- A controller stays **thin**: validate → call the service → translate the result to
  HTTP. Business logic never lives in a controller.
- **Entities never leak outward.** Separate DTOs for requests and responses. A
  `DbSet<Member>` is never returned directly (lazy loading, over-posting, cyclic
  references, backward-compatibility risk).
- Services use the DbContext; controllers never touch it.
- Dependencies between layers flow one way. If a service needs `HttpContext`, it goes
  behind an interface (`ICurrentUser`).

## 2. Project settings

```xml
<Nullable>enable</Nullable>
<TreatWarningsAsErrors>true</TreatWarningsAsErrors>
<ImplicitUsings>enable</ImplicitUsings>
<AnalysisLevel>latest-recommended</AnalysisLevel>
```

- `.editorconfig` is in the repo; `dotnet format` is mandatory before a PR.
- Suppressing a warning (`#pragma warning disable`) without a justifying comment is
  forbidden.

## 3. Dependency Injection

- Lifetimes: `Scoped` (DbContext, services), `Singleton` (stateless helpers, config),
  `Transient` (lightweight, stateless).
- **No captive dependencies:** a Scoped service is never injected into a Singleton.
- No Service Locator anti-pattern (`IServiceProvider.GetService` in business code) —
  constructor injection.
- Not every service has to sit behind an interface; an interface is introduced **only**
  when there is more than one implementation or a test double is needed.

## 4. Configuration

- Strongly typed options: `IOptions<T>` / `IOptionsSnapshot<T>` + `ValidateOnStart()`.
- Secrets are never in `appsettings.json`: User Secrets (dev), env variables / a secret
  store (prod).
- `IConfiguration["x"]` is never read inside business code — it is bound to an options
  class.
- A missing required setting fails **at application startup**, not on the first request.

## 5. EF Core

- **`AsNoTracking()` on read-only queries.**
- **No N+1.** Related data is fetched in one query with `Include`/`ThenInclude` or a
  projection. No query inside a loop.
- A list endpoint **always** projects to a DTO with `Select` — the whole entity is never
  fetched.
- `IQueryable` never crosses the service boundary (returning `IQueryable` to a controller
  is forbidden).
- A query that falls back to client-side evaluation is fixed (a warning appears in the
  log).
- Migrations are named and reviewed; the generated SQL is read. Detail: `09-database.md`.
- For bulk work use `ExecuteUpdateAsync`/`ExecuteDeleteAsync` or batching; no loop of
  individual `SaveChanges` calls.
- `SaveChangesAsync` is called **once per unit of work** (the transaction boundary is the
  service method).
- If global query filters are in use (tenant, soft delete), any query bypassing them must
  be deliberate and commented.

## 6. Validation

- Model validation at the DTO level (DataAnnotations or FluentValidation) — **one
  approach** is chosen and not mixed.
- Business-rule validation in the service (e.g. "this email is already registered").
- A validation failure → `400` + `ValidationProblemDetails` (a per-field error
  dictionary).
- **Adding a new required field is breaking** — see `08-backward-compatibility.md`.

## 7. Error handling and HTTP

- A central exception-handler middleware; no try/catch repeated in every controller.
- The error body is **ProblemDetails** (RFC 7807) + a `traceId`.
- Status codes: `200/201/204`, `400` validation, `401` no identity, `403` not authorized,
  `404` not found, `409` conflict, `422` business rule, `429` rate limit, `500`
  unexpected.
- No throwing an exception for an expected condition (exceptions are not control flow).
- Stack traces are never exposed in production.

## 8. Async

- All I/O is async; `async Task`, never `void` (except event handlers).
- The `CancellationToken` is **propagated** from the controller to the service and on to
  EF/HttpClient.
- `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` are forbidden.
- `HttpClient` comes from **IHttpClientFactory** (a named or typed client) — `new
  HttpClient()` is forbidden. Timeout + retry (on idempotent calls) + circuit breaker via
  Polly.

## 9. Security (detail: `15-security.md`)

- Every endpoint is `[Authorize]`; open endpoints are **explicitly** `[AllowAnonymous]`.
  The default policy is fail-closed.
- Authorization also covers resource ownership (IDOR): "may this user see this record?"
- A separate input DTO guards against over-posting (never bind directly to an entity).
- If raw SQL is used it is **parameterised**; string concatenation is forbidden.
- CORS uses an allowlist; `AllowAnyOrigin` combined with credentials is forbidden.
- File upload: type + size + content checks, a sanitised file name, stored outside the web
  root.

## 10. Background work

- `IHostedService`/`BackgroundService`; graceful shutdown is supported (`stoppingToken`).
- No fire-and-forget work tied to a request's lifetime — a durable queue is used.
- A scheduled job must be **idempotent**; running twice must not break anything.
- A background job opens its own scope via `IServiceScopeFactory`.

## 11. Testability

- `DateTime.UtcNow` is never used directly → inject `TimeProvider` / `IClock`.
- `Guid.NewGuid()`, `Random`, the file system and the network go behind interfaces.
- Service tests run against a real DB (Testcontainers) or in-memory; if in-memory is used,
  the **relational behaviour differences** are understood (see `10-test-strategy.md`).

## 12. Observability

- Structured logging via Serilog/`ILogger<T>`, using message templates
  (`_log.LogInformation("Member {MemberId} updated", id)`) — never string interpolation.
- Traces and metrics via OpenTelemetry; business steps marked with `Activity`.
- `/health` (liveness) and `/health/ready` (readiness — DB, cache, external services)
  endpoints.

## 13. Performance

- On a hot path, one query instead of a LINQ chain; no unnecessary materialisation
  (`ToList()` followed by `Where`).
- A large response requires pagination (`07-api-design.md`).
- Response compression + output caching where appropriate.
- `IAsyncEnumerable`/streaming for large data sets.
- Never optimise without measuring; measure with BenchmarkDotNet or a profiler.
