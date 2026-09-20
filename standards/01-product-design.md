# Product Design

**What** and **why** are settled before any code is written. This file defines the
shape of that clarity.

## 1. Every feature starts with a problem

When a feature request arrives, no code is written until these three are written down:

| Question | Output |
|---|---|
| Whose problem, and which one? | A 1–2 sentence problem statement + the user role |
| How will we know it is solved? | A measurable success criterion (a metric or an observation) |
| What is out of scope? | An explicit "not in this release" list |

If the user has not provided these, **ask briefly** — do not guess. But do not block
all the work either: do the part that is clear and flag the part that is not.

## 2. User story format

```
As a <role>, I want <capability> so that <benefit>.
```

Bad: "Add a reports page."
Good: "As an HR officer I want to filter the candidate pool by pipeline stage and
export it, so that I can walk into the weekly board meeting with a ready list."

Every story must be:
- **Independent** (testable without another story being finished)
- **Small** (one person, 1–3 days; split it if larger)
- **Accompanied by acceptance criteria** (below)

## 3. Acceptance criteria — Given/When/Then

```
Given  the candidate list has 3 members at "Interview" and 2 at "Active"
When   the user selects the "Interview" filter
Then   only 3 records are listed and the total counter shows "3"
And    the filter stays in the URL as ?status=interview (preserved on reload)
```

Rules:
- Acceptance criteria describe **behaviour**, not implementation.
- Every criterion must be **verifiable** — translatable one-to-one into an automated test.
- **The happy path is not enough:** empty list, error, unauthorized access, very long
  text and concurrent-change scenarios are written too.

## 4. Scope discipline

- **MVP = the smallest valuable slice**, not "half of a complete product".
- A "not in v1" list is written for every feature. The list you do not write turns into
  scope creep later.
- "While we're adding this, let's also do that" → a separate story, a separate PR.
- Configurability is **not** added before it is asked for (YAGNI). A need that recurs
  three times gets generalised.

## 5. One domain language

- A project glossary (`docs/glossary.md`) is maintained: the domain term ↔ its code
  identifier.
- The same concept never gets two names (the `Member`/`User` confusion, for example).
- The user-facing term and the term in the code may differ; the mapping lives in the
  glossary.

## 6. Decision records (ADRs)

Every decision that is expensive to reverse gets an ADR: the database choice, the auth
strategy, the multi-tenancy model, a payment integration, a change to an architectural
boundary.

Template: `templates/adr-template.md`. Keep it short (one page), but always write the
**rejected alternatives** and the **consequences**. An ADR is never deleted; if it is
cancelled it is marked "Superseded by ADR-00X".

## 7. A product decision is not a technical decision

Claude does **not** make these decisions on its own — it asks the user:
- Whether a field is required or optional
- Delete behaviour (soft or hard delete, who is allowed to delete)
- The authorization matrix (which role sees what)
- Anything involving money, payments or invoicing
- The text and the trigger of any notification or email sent to a user
- Data retention periods and anonymisation

## 8. Definition of Done

- [ ] Every acceptance criterion is met (happy path + error paths)
- [ ] The API contract is backward compatible, Swagger/OpenAPI is up to date
- [ ] Web + mobile parity was reviewed (any difference is deliberate and written down)
- [ ] Unit tests and any necessary e2e tests were written, CI is green
- [ ] i18n keys were added (the primary locale is mandatory, the secondary is a placeholder)
- [ ] Accessibility was checked (`02-ui-ux.md` §7)
- [ ] Logs/metrics were added (if this is a new critical flow)
- [ ] Documentation and CLAUDE.md were updated
- [ ] A rollback path was considered (a feature flag? is the migration reversible?)
