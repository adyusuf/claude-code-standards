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
not met (no task list, no definition of done) the run **does not start** —
#20 applies again.

## Before starting (items 1 and 3 are MANDATORY)

1. **A task list + a definition of done.** Every item is tied to **evidence**: a
   command that was run, a test that passed, a number that was measured. *"I looked,
   it's fine"* is not evidence (#15). If there is no list, `product-manager` produces
   one first, I show it to you, and only then does the run start.
2. **[Removed — the money budget is no longer a condition or a stop]** The money budget stops nothing (user decision 06/11/2026); the spend is followed in the podium plugin's Status box (`budget:` line, podium-flow). The original rules are in git history.
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
- An **irreversible** action has been reached.
- **A stall:** the same error has repeated for **2 turns** in a row. Trying a third
  time is not learning, it is a loop.
- **The scope changed** — the work is turning into something other than what was asked.
- An unresolvable conflict between agents (`role-selection.md` §4).
- **A completeness check did not close** — a finding was sent back twice and still did
  not reach clean in 3 passes (`role-selection.md` §5, §7). An unclosed finding is
  **never dropped into the "reversible assumption" bucket**; the run stops and the
  open findings are listed individually.

## Mode scope

An autonomous run layers on top of **C, D and E**. **A `/loop` autonomous run is not
started in A or B** — the mandatory first step (`product-manager` producing the task
list) cannot be performed there: agents are forbidden in A, and in B that role is not
in the set. If the user wants an autonomous run in A or B, **a mode change is proposed
first**; the run is never started on its own (#20).

⛔ The Y/Z handover rules that used to sit here have moved to the archive
(`modes/archive/team-rules.md` §9). X/Y/Z are not offered and cannot be started (that
file's §0), so a rule for them in an active document is a rule that can never fire,
and a reader looking up autonomous runs had to work out which half applied. If the
team modes ever open, §9 comes back with them.

## Visibility

- **Every turn:** what was done · the next item (the spend is in the Status box).
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
