# API design — one contract, two clients

## 1. Core principle

**One API; web and mobile consume the same contract.** No platform-specific
endpoint is created. Clients may display different fields but they receive the
same response.

The consequences:
- A response must be **rich enough to satisfy every client**, yet narrow enough not to carry useless data.
- If a client-specific variation is needed: the same endpoint plus an optional `?include=` / `?fields=` parameter. Not a new endpoint.
- A contract change affects **both clients at once**, and mobile can be stuck on an old version → `08-backward-compatibility.md` is required reading.

## 2. Resources and URLs

- Plural nouns, lower case, kebab-case: `/api/members`, `/api/work-orders`.
- No verbs in the URL; the HTTP method is the verb. The exception is a genuine action → `POST /api/orders/{id}/cancel`.
- Hierarchy never goes deeper than two levels: `/api/members/{id}/orders` is fine, anything deeper becomes a query parameter.
- The resource id goes in the path as `{id}`; filtering, sorting and pagination go in the query string.

| Method | Meaning | Idempotent |
|---|---|---|
| GET | Read, no side effects | ✅ |
| POST | Create / action | ❌ |
| PUT | Full replacement | ✅ |
| PATCH | Partial update | ✅ (it must be designed that way) |
| DELETE | Delete | ✅ |

## 3. Status codes

| Code | When |
|---|---|
| 200 | A successful read or update |
| 201 | Created (+ a `Location` header + the created record) |
| 202 | Accepted, will be processed asynchronously (+ a link to poll the status) |
| 204 | Success with no body (DELETE) |
| 400 | A malformed request or a validation error |
| 401 | No identity, or an invalid one |
| 403 | Identity present, authorization absent |
| 404 | The resource does not exist **or** the user must not see it (so as not to leak information) |
| 409 | A conflict (a concurrent change, a duplicate record) |
| 422 | The shape is right but a business rule was violated |
| 429 | Rate limited (+ `Retry-After`) |
| 5xx | A server error — the client may retry |

## 4. Error format — one shape

RFC 7807 ProblemDetails:

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation error",
  "status": 400,
  "detail": "Some of the submitted fields are invalid.",
  "traceId": "00-8f3c...-01",
  "errors": { "email": ["Enter a valid email address."] }
}
```

- Every error response carries a **`traceId`** — the user quotes it in a support request and it is findable in the logs.
- The error text must be safe to show to a user; technical detail and stack traces **never**.
- A client must be able to distinguish errors by **code** (`type` or `errorCode`), not by text (text changes with i18n).

## 5. Pagination, filtering, sorting

- **A list endpoint without pagination is forbidden.** The default is `pageSize=20` with an upper bound of `100` (enforced by the server).
- The standard response envelope:

```json
{ "items": [...], "page": 1, "pageSize": 20, "totalCount": 137, "totalPages": 7 }
```

- For very large or continuously streaming data, cursor-based pagination (`?after=<cursor>`) is preferred.
- Filtering: `?status=active&departmentId=3`. Sorting: `?sort=createdAt:desc`. Both validated against an allowlist (the risks are SQL injection and unindexed sorts).
- Search: `?q=...` — **case- and accent-insensitive** (global rule #13).

## 6. Contract details

- Date/time: **ISO-8601 UTC** (`2026-07-29T10:15:00Z`). A local format is for display only.
- Money: the amount and the currency are separate fields; `decimal`/string, never float.
- Enums travel as **strings** (`"Active"`), never as numbers — numbers break silently when the ordering changes.
- Boolean field names start with `is`/`has`/`can`.
- The difference between null and an absent field is deliberate: in PATCH, "clear this field" and "leave it alone" must be distinguishable (JSON Merge Patch, or an explicitly documented `null` semantic).
- Field names are `camelCase`, consistently across the whole API. The serializer setting is **global** and changing it is a breaking change.

## 7. Idempotency

- Operations created with `POST` that must not be repeated (an order, a payment, a notification) accept an `Idempotency-Key` header.
- A second request with the same key returns **the same result** and creates no second record.
- A mobile offline queue and any retry mechanism are unsafe without this.

## 8. Concurrency

- Where an update risks a lost update, use `ETag` + `If-Match` or a `rowVersion` field.
- A conflict → `409` plus information about which field changed.

## 9. Auth

- Bearer JWT (a short-lived access token plus a refresh token) or an httpOnly cookie. Never mixed; every client uses the same flow.
- The token carries identity and a coarse role only; **the authorization decision is made on the server** (a claim in the token is never trusted blindly).
- The refresh flow lives in one place; concurrent 401s trigger a single refresh.
- Detail: `15-security.md`.

## 10. Documentation

- OpenAPI/Swagger is updated **together with the code**; if it is missing from a PR, review blocks it.
- For every endpoint: what it does, which permission it needs, which errors it returns, and an example request and response.
- A deprecated endpoint or field is marked `deprecated` in Swagger, along with what to use instead.

## 11. Versioning

- Preferred: **no versioning plus additive evolution** (`08-backward-compatibility.md`). This is almost always sufficient.
- If a break is genuinely unavoidable, `/api/v2/...` is introduced and **v1 lives on for at least six months and until every mobile version that uses it is retired**.
- Introducing a version requires an ADR.

## 12. Rate limits and size

- A rate limit per identity; on exceeding it, `429` + `Retry-After`.
- A request body size limit; file upload is a separate endpoint with streaming.
- Bulk endpoints have a defined and documented upper bound.

## 13. Never-do list

- ❌ A platform-specific endpoint (`/api/mobile/...`)
- ❌ A list without pagination
- ❌ Returning an entity directly
- ❌ Returning `200 + {success:false}` for an error
- ❌ Carrying an enum as a number
- ❌ Deleting or renaming a field or endpoint
- ❌ Changing the global serializer setting (it breaks every client)
- ❌ Granting authorization purely from a token claim
- ❌ Causing a side effect with GET
