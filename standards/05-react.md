# React + TypeScript Standards

## 1. Folder structure (feature-based)

```
src/
  api/          → client.ts (THE single config: BASE_URL, SIGNALR_URL), endpoint modules
  components/   → shared presentational components (Button, Modal, EmptyState, Table)
  features/<name>/→ the page, components, hooks and types for that feature
  hooks/        → shared hooks
  lib/          → pure helpers (date, search normalisation, formatting)
  i18n/         → the locale files
  types/        → shared types / types generated from the API
```

Grouped **by feature**, not by technology. Deleting a feature should mean deleting one
folder.

## 2. TypeScript

- `strict: true`. `any` is forbidden (use `unknown` + narrowing). If unavoidable, add a
  justifying comment.
- Do not hand-write API types — generate them from OpenAPI (`openapi-typescript` or
  similar) or define them in one place.
- Use type guards instead of type assertions (`as`). A `!` non-null assertion is an
  exception and needs a reason.
- Model state with a discriminated union: `{status:'loading'} | {status:'error',error} |
  {status:'ok',data}` — not the `isLoading && !error && data` triad.
- An `as const` union is preferred over `enum`.

## 3. Component rules

- Function components + hooks. No class components.
- **A component over 300 lines gets split.** During the split, props, JSX, data calls and
  i18n keys are preserved exactly.
- A component is never defined inside another component (it is recreated on every render →
  state loss).
- Props are destructured; no `props.x.y.z` chains.
- Guard with an early `return` (`if (!data) return <Skeleton/>`); no deeply nested
  ternaries.
- An index is never used as a `key` (if the list can be sorted or items removed) — use a
  stable id.

## 4. State management — in the right place

| Kind of state | Where |
|---|---|
| Server data | TanStack Query (or equivalent) — not manual fetching with `useState`+`useEffect` |
| State that belongs in the URL (filter, tab, page) | Query params (`useSearchParams`) |
| Form state | A form library (react-hook-form) or local state |
| Short-lived UI state | Local `useState` |
| Genuinely global (auth, theme, i18n) | Context — small and split up |

- A derivable value is not kept in state; it is computed during render.
- A frequently changing value is never put in context (the whole tree re-renders) — split
  it or use a store.
- `useEffect` is **only** for synchronising with an external system. Using `useEffect` to
  derive state from props, to compute something, or to react to an event is **wrong**.

## 5. Data fetching

- One API client (`src/api/client.ts`) — base URL, headers, auth and error normalisation
  live there. Components never call `fetch`/`axios` directly.
- Every request handles loading + error + empty states (`02-ui-ux.md` §3).
- Request cancellation (`AbortSignal`) — when the component unmounts or the search term
  changes.
- Search and filter inputs are debounced (around 300ms).
- After a mutation the relevant queries are invalidated; if optimistic updates are used, a
  rollback path is written.
- The server's ProblemDetails error shape is parsed in one place; field errors are bound
  to the form.

## 6. Performance

- Correct structure first, memoisation second. `useMemo`/`useCallback`/`React.memo` are
  for a **measured** problem.
- Long lists are virtualised (`react-virtual` or similar) or paginated.
- Route-based code splitting (`React.lazy` + `Suspense`).
- Images: the right dimensions + `loading="lazy"` + a modern format.
- The bundle budget is tracked (`16-performance.md`).

## 7. Styling

- One approach is chosen (CSS Modules / Tailwind / CSS-in-JS) and not mixed.
- No raw colour or size values → tokens (`02-ui-ux.md` §1).
- Global CSS kept to a minimum; a component's styles live with the component.
- Inline styles only for genuinely dynamic values.

## 8. Forms

- `react-hook-form` + schema validation (zod/yup). The schema is the **single source**:
  the types are derived from it too.
- Server validation errors are bound to fields (`setError`).
- Disabled + spinner during submit; double submission is prevented.

## 9. Routing and authorization

- Route definitions in one file; authorization checked at route level with a guard
  component.
- **Hiding something in the UI is not security** — authorization is always checked in the
  API as well.
- A 401 is handled in a central interceptor (session refresh or redirect to login), not in
  every component.

## 10. Accessibility

- `eslint-plugin-jsx-a11y` enabled.
- Interactive elements are `button`/`a`; `div onClick` is forbidden.
- Modals: focus trap + `Esc` + `aria-modal` + an inert background.
- Detail: `02-ui-ux.md` §7.

## 11. Testing

- **React Testing Library** — test user behaviour, not implementation.
- Query priority: `getByRole` > `getByLabelText` > `getByText` > `getByTestId` (last
  resort).
- The network is faked with MSW, at the real request/response level rather than globally
  mocking `fetch`.
- Snapshot tests are not used as a rule (brittle, and approved without being read).
- Detail: `10-test-strategy.md`.

## 12. Never-do list

- ❌ Setting state inside `useEffect` and listing that same state as a dependency (an
  infinite loop)
- ❌ `dangerouslySetInnerHTML` (if unavoidable, sanitise with DOMPurify + a stated reason)
- ❌ Writing a token to `localStorage` (exposed to XSS — prefer an httpOnly cookie; if
  that is impossible, the risk is accepted in writing)
- ❌ Navigating with `window.location` instead of the router
- ❌ Reading an environment variable inside a component (`import.meta.env` only in
  `api/client.ts`)
- ❌ Manually copying server data into Redux/Context
- ❌ Prop drilling deeper than 3 levels (compose, or use context)
