---
name: working-mode
description: Shows or changes the operating mode (A/B/C/D/E) for this project, optionally with a model that replaces Opus for the Opus agents ("C sonnet"). The mode determines agent usage, review and the approval policy, and so how fast the session spends tokens. Use it when the user says "/adyusuf:working-mode", "change the mode", "which mode are we in", "work as a full team", or "work without agents".
---

# Working mode

## Why this exists

Writing code with agentic AI from Claude Desktop means working with **subagents only**:
Desktop cannot start an agent team, so this skill makes the session itself the
orchestrator and runs subagents in a controlled, synchronous way. And once you work on
more than one project at a time, tokens run out — so the mode is the dial for **how fast
a session spends them**. Pick the smallest mode the work needs:

| Mode | Who works | Agents |
|---|---|---|
| A | The session alone, no agents | 0 |
| B | Selective — `analyst`, `test-writer`, `doc-writer` | 3 roles |
| C | Full team (default) | 9 roles |
| D | Wide team | 14 roles |
| E | Fan-out through `Workflow` | the 14 roles, in parallel |

The work is **audited** in every mode: a producing role closes with an evidence block,
and the auditor checks it and sends gaps back (global #28). In C/D/E the auditor is the
`qa` agent (the session verifies its critical findings); in A/B it is the session itself.

Contributions are welcome: https://github.com/adyusuf/claude-code-standards

## 0. At session start - no question

A session does not ask the mode (user decision 17/10/2026): the read order of §1 decides, and the SessionStart hook has
already printed the effective values. Apply nothing at start. The defaults themselves are changed with `/adyusuf:config`.
Rules: `${CLAUDE_PLUGIN_ROOT}/modes/README.md` › *Session start*.

## 1. Read the current mode

Priority order: **session-scoped selection** → project file → the configuration (`mode`, default C).

```bash
S="<the Scratchpad Directory from the system prompt>"   # session-scoped, survives compaction
root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cfg="${CLAUDE_PLUGIN_ROOT}/scripts/adyusuf_config.py"
if [ -f "$S/mode" ]; then d="$S"; elif [ -f "$root/.claude/mode" ]; then d="$root/.claude"; else d=""; fi
echo "mode: $( [ -n "$d" ] && cat "$d/mode" || python3 "$cfg" get mode )"
echo "opus agents run on: $( if [ -n "$d" ]; then cat "$d/mode-model" 2>/dev/null || echo 'their defined model'; else python3 "$cfg" get mode_model; fi )"
```

The model override is read **from the layer that supplied the letter** — a session
or project letter without its own `mode-model` means "defined models", even if the
configuration has an override. Rules: `${CLAUDE_PLUGIN_ROOT}/modes/README.md` › *Model override*.

If none of them exists the configuration's mode applies (default **C**, `adyusuf:config`); its agents are approved
by the default itself. Propose a lower or higher mode in one line only if the work clearly deserves it - never switch on
your own (README › "When no mode is given").

⚠️ A mode chosen with `--once` is written **to the scratchpad** (`$S/mode`), not
to `.claude/mode`. Reason: if "apply this for this session only" relies on
memory, it is **forgotten** after context compaction and the project file's mode
silently takes over again. The scratchpad is session-scoped and disappears with
the session — exactly the lifetime required.

## 2. Load the mode definitions

`${CLAUDE_PLUGIN_ROOT}/modes/README.md` is the matrix (single source). Read the active mode's
file: `${CLAUDE_PLUGIN_ROOT}/modes/<LETTER>-*.md` (each of the five letters resolves to one
file). **Read only the active mode's file** — reading all five burns context for
nothing. ⚠️ **X/Y/Z are archived** (`modes/archive/README.md`) and are never
offered as a mode.

## 3. If called without an argument

Show the current mode, what it means and the other options **briefly**: letter +
name + agent set + who reviews + cost multiplier. Do not paste the whole matrix;
5-6 lines are enough (A-E).

## 4. If a letter is given (`/adyusuf:working-mode B`, `/adyusuf:working-mode C sonnet`)

0. Split the argument: the letter, an optional **model word**, an optional `--once`/`--tek`.
   The model word must be `sonnet` · `haiku` · `fable` · `opus`; anything else is
   rejected with that list and **nothing is written**. `opus` is the same as no model
   word.
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
2a. Write or clear the model override **in the same directory** as the letter
   (`$root/.claude` or `$S`):
   ```bash
   dir="$root/.claude"   # or "$S" with --once
   if [ -n "$model" ] && [ "$model" != opus ]; then printf '%s\n' "$model" > "$dir/mode-model"; else rm -f "$dir/mode-model"; fi
   ```
   ⚠️ The letter alone **clears** the override — that is how the user returns to the
   defined models. Never keep an old `mode-model` next to a newly written letter.
   `.claude/mode` stays a single letter (other readers parse it).
3. Read the new mode's file and **follow its rules from that point on**.
4. Confirm to the user: old mode → new mode, and what changed (agent set, who
   reviews, approval policy, expected multiplier) **and the model line**: which
   agents are Opus by definition and what they run on now. 4-6 lines.
5. **From then on**, every `Agent` call to an agent whose effective model is Opus
   passes `model: "<model>"` (and every `Workflow` `agent()` for such a role); other
   agents get no override. Report the model that actually ran. A role agent is always
   called by its plugin name, `subagent_type: "adyusuf:<role>"`; a bare `<role>` is not found.

## Permanent rules

- `.claude/mode` **is committed** — it carries the project default across team
  members and sessions. Use `--once` for a personal, temporary preference.
- **In modes B/C/D/E** choosing the mode **is** the approval for that agent set
  (#27); no separate question before a call. At the end of the turn the number of
  agents that ran and the estimated cost are **reported**.
- **In mode A** no agent is ever invoked; if an agent is needed, propose changing
  the mode instead of starting one.
- The mode **never** loosens any of these: approval for irreversible work, the
  promotions over a red or incomplete gate, the completeness check before
  "done", secrets staying out of the repository.
- `.claude/mode-model` is committed with `.claude/mode` (same narrow gitignore
  exception); with no override the file does not exist.
- A mode change is **not retroactive** — work done in earlier turns is not
  re-evaluated.
