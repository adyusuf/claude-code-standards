# Defect and unhandled-case checklist

Walk each item against the screen's code path (client → endpoint → service → external
call → callback). Each item names what to look for and how it usually hides. Every hit
must be verified at `path:line` before it is reported (phase 1 §8).

## Money and external calls

- **Double submission.** Does EVERY client that starts a money movement (web, Android,
  iOS, public page) send an idempotency key, and does the server honour it on EVERY
  such endpoint (charge, order pay, link pay, refund)? One client or one endpoint
  without it is enough for a double charge.
- **Key lifecycle, not key presence.** A key generated fresh on every tap/attempt
  protects nothing — the second tap is a new charge. The key must stay the same for the
  same payment signature and change only when the signature changes. A test that only
  asserts "the header is not blank" passes on the broken version; the test must send
  twice and assert the SAME key.
- **Race on the same resource.** Two requests for the same link/order/payment at once:
  is there a lock, a concurrency token or a unique constraint — or do both pass the
  "is it still payable / refundable" check and both call the gateway?
- **External call throws after the local record is written** (timeout, DNS, 5xx
  without body). What status is the record left in? Does anything ever move it on
  (webhook, reconciliation job)? Can the user retry and be charged twice?
- **External call returns failure.** Is the failure path tested at all? A shared fake
  that always succeeds (`Success: true`) means no failure path is tested anywhere.
- **Callback twice / callback for a finished resource.** A second 3-D Secure return, a
  second webhook, a success for a link that another attempt already paid — is it
  detected, or does it silently overwrite the first result?
- **Amount shown = amount charged = amount recorded.** Is the same function used for
  display and charge? Rounding, currency, surcharge, partial refunds scaled correctly?
- **Setup paths tested only by seeding.** If callback tests insert the pending record
  directly into the database, the path that CREATES it is untested. The same holds for
  any state a test writes by hand (a locked account, an expired link): the rule that
  produces that state needs its own test.
- **Unattended runs.** A background run (auto-debit, scheduled send) charges without a
  user: what happens when the gateway still demands 3-D Secure, when the call throws,
  and who schedules the run at all — is the scheduled task in the deploy scripts and the
  setup document, or does the feature silently never run?

## Authorization and exposure

- Permission decided **after** a policy (e.g. void vs refund): is each branch's
  permission tested, not only "no permission at all"?
- Scope on **list AND single read AND every mutation** (a user who cannot see a record
  must not act on it by id).
- Licence / feature gates on every entry path, including the alternative endpoints that
  reach the same service (order pay vs direct charge vs link pay).
- Anonymous endpoints: responses and error messages must not leak internal names
  (package names, account ids), account existence, or other people's data. Check the
  messages of exceptions the anonymous path can throw — not only its happy response.
- Rate-limit metadata on money and auth endpoints — and a test that lists them (a list
  that forgets one endpoint protects nothing). Count the endpoints carrying the policy
  (`grep` the policy name) and compare with the test's list.
- **Pre-authentication disclosure.** Does login (or any credential check) reveal account
  state — disabled, locked, unverified — BEFORE the password is verified? An attacker
  learns that the account exists without knowing the password.
- **Internal text reaching a customer.** Follow every exception message that can flow
  into a customer-facing channel (e-mail, SMS, push, public page): raw `e.Message`,
  licence/package names, host names.
- **Every write path asks the same scope as the list.** A user-level restriction applied
  to lists and single reads is often forgotten on a CREATE that takes a foreign id (a
  subscription created on a card the user cannot see).

## Validation and contract

- Client and server validation parity; a server rule without a client message, or a
  client rule the server does not enforce.
- Fields the API accepts that no client ever sends (dead contract) — and the reverse:
  fields a page shows but never submits (e.g. a "payer chooses amount" link with no
  amount input).
- Sensitive data that must never be stored or echoed (card number, CVV, tokens,
  passwords): is there a test asserting the record, the response and the audit log do
  NOT contain it?

## State and lifecycle

- Every state × every action: what happens on a cancelled, expired, already-paid,
  failed, pending item? Retry after failure allowed and tested? Can an update endpoint
  set ANY status (re-activate a stopped item) because the status field is free?
- Expiry computed from the clock abstraction, and tested with a fake clock at the
  boundary.
- **Date-only inputs.** A `yyyy-MM-dd` turned into `new Date(x).toISOString()` (or
  `…T00:00:00Z`) is UTC midnight — in a UTC+3 business zone "valid until 30/09" dies at
  03:00 on the 30th and "today" is rejected as past. Check every client that sends a
  date-only value and the server rule that compares it.
- **Soft delete and revival.** When a soft-deleted row is revived (a webhook re-sends
  the same card), do old flags come back with it — consent, default, active? Does a
  partial unique index (`IsDefault AND DeletedAt IS NULL`) then collide and drop the
  revival?

## Project rules

- Read the project `CLAUDE.md` rule list and check the screen's code against each
  rule that applies (e.g. "passwords are written only through the password authority",
  "amounts are decimal", "no raw lower-case contains in search"). A violated written
  rule is a 🟡 defect even when every test is green.
- The global never-do list applies to every screen: a list endpoint without paging, a
  swallowed exception (`catch {}`), search that is not accent-insensitive (including
  client-side `toLowerCase().includes`).
- **Tests that lock in the defect.** When a finding is a defect, search the tests for
  the wrong value (the UTC-midnight date, the base amount, the accent-sensitive match).
  Those tests are green BECAUSE of the bug; they change together with the fix and the
  report must name them.

## Client specifics

- Mocked children: when page tests mock a child component, is the child's own real
  behaviour (forms, submit, error) tested anywhere?
- Uncovered line ranges: missing use case, unreachable guard, or dead code?
- Mobile parity: does the mobile flow implement the same safeguards as web (idempotency,
  validation order, 3-D Secure handling)? Compare Android with iOS as well — the two
  often diverge (one keeps the key in state, the other regenerates it; one asks for
  confirmation, the other does not).
- **A parity claim is verified before it is written.** "The mobile app does not have
  X" is written only after grepping the endpoint path in the mobile sources (and the
  mobile tests). Features often live on a different screen than on web (a summary on
  the home screen instead of the list).
