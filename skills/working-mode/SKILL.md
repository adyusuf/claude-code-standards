---
name: working-mode
description: Shows or changes the operating mode (A/B/C/D/E) for this project. The mode determines agent usage, review and the approval policy. Use it when the user says "/working-mode", "change the mode", "which mode are we in", "work as a full team", or "work without agents".
---

# Working mode

## 1. Read the current mode

Priority order: **session-scoped selection** → project file → B.

```bash
S="<the Scratchpad Directory from the system prompt>"   # session-scoped, survives compaction
cat "$S/mode" 2>/dev/null || cat "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.claude/mode" 2>/dev/null || echo B
```

If none of them exists the mode is **B**. B's three agents (`analyst`,
`test-writer`, `doc-writer`) are approved along with the default. If the user
named no mode, **start in B and propose the lowest sufficient mode in one line**
if the work deserves it — never switch on your own (README › "When no mode is given").

⚠️ A mode chosen with `--once` is written **to the scratchpad** (`$S/mode`), not
to `.claude/mode`. Reason: if "apply this for this session only" relies on
memory, it is **forgotten** after context compaction and the project file's mode
silently takes over again. The scratchpad is session-scoped and disappears with
the session — exactly the lifetime required.
(`--tek` is still accepted as a legacy alias of `--once`.)

## 2. Load the mode definitions

`~/.claude/modes/README.md` is the matrix (single source). Read the active mode's
file: `~/.claude/modes/<LETTER>-*.md` (each of the five letters resolves to one
file). **Read only the active mode's file** — reading all five burns context for
nothing. ⚠️ **X/Y/Z are archived** (`modes/archive/README.md`) and are never
offered as a mode.

## 3. If called without an argument

Show the current mode, what it means and the other options **briefly**: letter +
name + agent set + who reviews + cost multiplier. Do not paste the whole matrix;
5-6 lines are enough (A-E).

## 4. If a letter is given (`/working-mode B`)

1. Validate the letter (**A/B/C/D/E**). ⚠️ **D and E swapped places**: D is now the
   14-role wide team and E is fan-out (`Workflow`). Correct any "D = fan-out"
   expectation carried over from older sessions. Reject an invalid letter and
   show the list.
2. If `--once` was not given, write the **single letter** to `.claude/mode` at the
   repository root:
   ```bash
   root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && mkdir -p "$root/.claude" && printf '%s\n' "B" > "$root/.claude/mode" && echo "written: $root/.claude/mode"
   ```
   ⚠️ The fallback is mandatory: in a directory that is not a git repository
   `git rev-parse` exits **128** and breaks the `&&` chain, so the file is never
   written. The read command used to have a fallback while the write did not:
   the user was told "saved permanently" when nothing had been saved. **If the
   write fails, say so** — never confirm it.
   If `--once` was given, do **not** write `.claude/mode`; write the scratchpad
   instead: `printf '%s\n' "B" > "$S/mode"` (session-scoped; it overrides the
   project file in the priority order of §1).
3. Read the new mode's file and **follow its rules from that point on**.
4. Confirm to the user: old mode → new mode, and what changed (agent set, who
   reviews, approval policy, expected multiplier). 4-6 lines.

## Permanent rules

- `.claude/mode` **is committed** — it carries the project default across team
  members and sessions. Use `--once` for a personal, temporary preference.
- **In modes B/C/D/E** choosing the mode **is** the approval for that agent set
  (#27); no separate question before a call. At the end of the turn the number of
  agents that ran and the estimated cost are **reported**.
- **In mode A** no agent is ever invoked; if an agent is needed, propose changing
  the mode instead of starting one.
- The mode **never** loosens any of these: approval for irreversible work, the
  `test`/`prod` promotions belonging to the user, the completeness check before
  "done", secrets staying out of the repository.
- A mode change is **not retroactive** — work done in earlier turns is not
  re-evaluated.
