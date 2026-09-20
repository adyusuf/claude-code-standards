# Mode X — Team: selective (the team equivalent of B)

Three roles are opened as **teammates**: **`analyst`**, **`test-writer`**,
**`doc-writer`**. Code and review stay with me. I am the leader.

⛔ **Precondition:** `team-rules.md` §0 — the role definitions do not carry the team
tools and the feature is disabled. X does not open until both are resolved.

⚠️ Shared rules: [`team-rules.md`](team-rules.md) — the mechanism, task-list
discipline, the team equivalent of the audit protocol, cost. **Read that first.**

## Rules
- The only permitted teammates are those three. No other role is opened.
- **No code-writing teammate** (the same rationale as B: the same code becomes tokens
  two or three times over).
- Code review is done by **me**.
- At most **3 teammates** and **8 leader→teammate messages** per task
  (`SendMessage` + spawn count; not the teammate's own internal turns — those I
  cannot measure). If I exceed that I stop and ask.
- **I** assign a task's `owner` (`team-rules.md` §2).
- A handoff requires **one clean pass**; if something is missing the task is reopened (§3).

## When to use it
The same work as B, **but when the roles pass data back and forth turn by turn**:
`analyst` finds something, I write the code, `test-writer` writes a test based on
that same finding, and then I ask `analyst` to verify one more thing. For one-shot
work, **B is cheaper**.

## Expected cost
**~1.5–2.5x** (NOT MEASURED — `team-rules.md` §5).
Threshold: ~$25 warning / **~$50 stop**.
