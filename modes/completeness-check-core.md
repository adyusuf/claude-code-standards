# The completeness-check block — canonical core

> **Generated-adjacent, but hand-edited: this file is the SOURCE.** The block below
> is copied verbatim into every role in `agents/` that owes it (`role-selection.md`
> §7 says which). It is inlined rather than referenced because a role file is what
> enters that agent's context, and an agent cannot be relied on to go and read a
> second document — the guarantee #28 needs is that the text is already in front of
> it.
>
> The price of inlining is drift, so `scripts/doc-check.py` reads this file and
> checks that every one of those blocks still contains these lines, in order. A role
> may **add** a line of its own (five do); it may not reword a line that is here.
> Change the wording here first, then propagate it, and the gate will tell you which
> copies you missed.

## Completeness check (mandatory — at the VERY END of your report, every time)

Close your report with this block; write it even when the pass is clean — an
invisible check is an unperformed check.

```
## Completeness check — pass N
- Verification   → command run / line range read + raw result
- Item mapping   → each requested item → where it is (file:line)
- Not covered    → what you could not verify + what you deliberately left out
→ Result: clean NO  |  YES → BACK TO: <who> · <what to fix> · <closing evidence>
```

- ⚠️ **This is a check, not a question** — you never ask anyone "is anything missing?".
- **It carries evidence, not a template.** The `Verification` line **must** carry
  the command you ran or the range you read; what you could not verify does not
  count as fine — write "not verified" under `Not covered`.
- **On "YES" you do not hand over:** you send it back (what is missing · with what
  evidence · what to do) and when the fix arrives you **re-run the same
  verification** (closing evidence; a claim of "fixed" is not closure). No finding
  is ever dropped silently.
- **One** "no serious gap" is enough for a handoff. **Ceiling: 2 hand-backs.**

The full rule, who sends work back to whom, and the paths to closure:
`~/.claude/modes/role-selection.md` §7.
