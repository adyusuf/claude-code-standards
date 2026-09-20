# Mode B — Selective agents **(DEFAULT)**

⚠️ **Every project without a mode file is in B.** The default
itself is the approval for these three agents — I do not ask separately. To work
without agents: `/working-mode A`.

Three agents are enabled: **`analyst`**, **`test-writer`**, **`doc-writer`**. Code
and review stay with me.

## Rules
- The only permitted agents are those three. I do not call any other agent type.
- **No code-writing agent.** Reason: I re-read code an agent wrote, and so do you —
  the same code becomes tokens two or three times over.
- Code review is done by **me** (#27: in A/B review is mine). ⚠️ **There is no
  review in the `feature/* → dev` direction** — neither by hand nor by agent (#25);
  the exception is the security/backup/gate item in `role-selection.md` §3.
- At most **4** agent turns per task; if I exceed that I stop and ask.
- I do not ask before an agent call; I pass a cost line at **every handoff**
  (`↳ analyst done · ~$3 · turn total ~$3 · threshold ~$25 (B)`) and total it at the
  end of the turn. The threshold is two-stage: a warning at ~$12, a **stop at ~$25**
  (§8).
- `analyst` and `test-writer` close their reports with the **completeness-check**
  block; if anything is missing or wrong the work is **sent back and fixed**
  (closure = re-running the same verification), and a handoff requires **one clean
  pass** (`role-selection.md` §7). If it is not closed within 2 hand-backs the chain
  stops and I **inform** you.
- `analyst` also returns the **command** that produced its finding; without the
  command the finding counts as "not verified".

## When to use it
- A "how does this work / where is this defined" question spanning several tiers → `analyst`
- Behaviour changed, tests need writing, and the work is isolated → `test-writer`
- CLAUDE.md / docs updates have piled up → `doc-writer`

## Expected cost
**1.15–1.35x**. The measured average per agent turn is ~$6.9; `analyst` and
`doc-writer` stay below it on sonnet/haiku.
