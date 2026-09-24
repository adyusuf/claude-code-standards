# Defect and unhandled-case checklist

Walk each item against the screen's code path (client → endpoint → service → external
call → callback). Each item names what to look for and how it usually hides. Every hit
must be verified at `path:line` before it is reported (phase 1 §8).

## Money and external calls

- **Double submission.** Does EVERY client that starts a money movement (web, Android,
  iOS, public page) send an idempotency key, and does the server honour it on EVERY
  such endpoint (charge, order pay, link pay, refund)? One client or one endpoint
  without it is enough for a double charge.
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
  directly into the database, the path that CREATES it is untested.

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
  that forgets one endpoint protects nothing).

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
  failed, pending item? Retry after failure allowed and tested?
- Expiry computed from the clock abstraction, and tested with a fake clock at the
  boundary.

## Project rules

- Read the project `CLAUDE.md` rule list and check the screen's code against each
  rule that applies (e.g. "passwords are written only through the password authority",
  "amounts are decimal", "no raw lower-case contains in search"). A violated written
  rule is a 🟡 defect even when every test is green.

## Client specifics

- Mocked children: when page tests mock a child component, is the child's own real
  behaviour (forms, submit, error) tested anywhere?
- Uncovered line ranges: missing use case, unreachable guard, or dead code?
- Mobile parity: does the mobile flow implement the same safeguards as web (idempotency,
  validation order, 3-D Secure handling)?
