# Autonomous runs — leaving long work to finish on its own

> This layers **on top of** mode C or D. It is not a mode by itself: the agent set
> and review are decided by the mode underneath, and this file only adds the rules
> for **running without stopping** and for **reaching you**.

## The approval record (global #20)

Global rule #20 forbids autonomous background work without **explicit approval**.
Approval **has been given**: long work may be handed over and left to run without
stopping until it is finished, and if a question comes up, the user is to be reached
— including on mobile.

⚠️ The approval is **conditional on the conditions in this file**. If one of them is
not met (no task list, no budget, no definition of done) the run **does not start** —
#20 applies again.

## Before starting (all three are MANDATORY)

1. **A task list + a definition of done.** Every item is tied to **evidence**: a
   command that was run, a test that passed, a number that was measured. *"I looked,
   it's fine"* is not evidence (#15). If there is no list, `product-manager` produces
   one first, I show it to you, and only then does the run start.
2. **Budget: $100 — MEASURED, not estimated.** The rules:
   - **On reaching $100, or coming very close:** the run stops, the session state is
     saved (a handover note is written) and the user is asked to **OPEN A NEW
     SESSION**. Work does not continue in the same session — a long session is both
     expensive and unreliable once context is compacted.
   - **To start a new item there must be room for roughly 2x that item's estimated
     cost** (e.g. ≥$20 remaining for an item estimated at $10). If less remains, the
     item is not started and permission is asked. Reason: work abandoned half-done
     costs more than work never started.
     ⚠️ A fixed floor does not work here: with a $100 ceiling, a fixed $75 floor means
     no new item can be started the moment spending passes $25 — the promise of "hand
     it over and let it run to the end" would end at $28. The headroom has to scale
     with the item.
   - ⚠️ **This is a stop reason too** and is listed below.
   At the end of every turn:
   ```bash
   python3 ~/.claude/scripts/session-cost.py <session-id>
   ```
   ⚠️ Without running this command, "~$X so far" is **never written** —
   an unmeasured ceiling is not a ceiling, and the next session will just say
   "roughly" and move on. The output is API list price (a proxy for consumption, not
   the subscription invoice).
3. **The channel to reach you is verified.** `PushNotification` always reaches the
   terminal; it reaches **the phone only when Remote Control is connected**. If it is
   not, I say so BEFORE the run — starting out with "I'll reach you on mobile" and
   then failing to means leaving work silently waiting.

## If a question comes up

| Decision | Behaviour |
|---|---|
| **Reversible** (a name, a scope detail, a design preference, a library choice) | **Assume → continue → report.** The assumption is written out explicitly in the notification. If it turns out wrong when you return, that piece is redone. |
| **Irreversible** (deploy, `DROP`, force push, sending anything outward, a `test`/`prod` promotion, deleting files) | **STOP and wait.** An autonomous run **never** loosens this. |

⚠️ Assumptions **accumulate and are listed together in the final report** — so they
do not get lost among individual notifications.

## Stop conditions

The run stops and sends a notification when:

- Every item on the task list is tied to evidence → **done**.
- The **budget ceiling** is exceeded.
- An **irreversible** action has been reached.
- **A stall:** the same error has repeated for **2 turns** in a row. Trying a third
  time is not learning, it is a loop.
- **The scope changed** — the work is turning into something other than what was asked.
- An unresolvable conflict between agents (`role-selection.md` §4).
- **There is not enough budget headroom for the next item** (see the 2x rule above).
- **A completeness check did not close** — a finding was sent back twice and still did
  not reach clean in 3 passes (`role-selection.md` §5, §7). An unclosed finding is
  **never dropped into the "reversible assumption" bucket**; the run stops and the
  open findings are listed individually.

## Mode scope and teams

An autonomous run layers on top of **C/D and Y/Z**. **A `/loop` autonomous run is
not started in A/B/X** — the mandatory first step (`product-manager` producing the
task list) cannot be performed in those modes: agents are forbidden in A, and in
B/X that role is not in the set. If the user wants an autonomous run in A/B/X, **a
mode change is proposed first**; the run is never started on its own (#20).

**Extra rule for Y/Z (teams — archived):** teammates do not survive across sessions,
but the team and the task list **persist on disk**. When the budget fills and a new
session is requested, the handover note carries: that no task was left `in_progress`
(all are `completed` or `pending`), the team name (the same name cannot be reused),
and the list of open findings.

## Visibility

- **Every turn:** what was done · spending so far · the next item.
- **Notifications only when needed:** when an assumption is made, when the run stops,
  when it finishes. Routine progress produces **no** notification — unnecessary
  notifications teach the reader to ignore the necessary ones.
- **At the end:** the completed items with their evidence · **every assumption that
  was made** · what was not done, and why.

## Starting / stopping

**The user starts** the run — I cannot start one myself (#20):

```
/loop <task description>
```

To stop it: cancel the `/loop` task, or say "stop" on the next turn. When the run
stops itself, it names the reason from the list above.
