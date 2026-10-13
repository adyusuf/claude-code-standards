---
description: Install or update this project's standard documents (CLAUDE.md, SETUP.md, .env.example)
---

Bring this project in line with the `${CLAUDE_PLUGIN_ROOT}/standards/` layout. **Do not delete what exists; fill in what is missing.**

## 1. Discovery (read first, write second)

- The root directory, `package.json` / `*.csproj` / `docker-compose.yml` / `.github/workflows/`
- Any existing `CLAUDE.md`, `README.md`, `SETUP.md`, `DEPLOY.md`, `.env*`
- The real ports, the real service names, the real branch flow (`git branch -a`)

**Never write a guess.** Leave any field you do not know as `<TODO: ...>` and list them at the end.

## 2. `CLAUDE.md`

- If missing: create it from `${CLAUDE_PLUGIN_ROOT}/standards/templates/project-claude-md.md`, filled in with **real** information. A large module (`backend/`, `web/`, `mobile/`, `infra/`) gets its own small `CLAUDE.md` from `module-claude-md.md`, so its detail is loaded only when Claude works there.
- If present: do not delete it. Add only the missing sections and put this note at the top (if it is not there already):

  ```
  > Global rules and standards: the `adyusuf` Claude Code plugin (https://github.com/adyusuf/claude-code-standards) — its rules load in every session, its standards through `/adyusuf:software-standards`.
  > This file holds only the rules **specific to this project**; a rule here overrides the global standard.
  ```

- Target: under 200 lines. Propose moving long historical detail into `docs/` (with the user's approval).

## 3. `SETUP.md`

From `${CLAUDE_PLUGIN_ROOT}/standards/templates/setup-md.md` — the critical section is **§3, the secret/token inventory**:
for every secret, its name, what it is for, **where to obtain it (the menu path)**, where it is stored, who owns it, its rotation, and whether it is secret or public.

Scan the code for existing env usage (`process.env`, `import.meta.env`, `IConfiguration`, `appsettings*.json`)
and put **all of it** in the table. **Never** write the values.

## 4. `.env.example`

Every variable found in the code, with a comment and a required/optional distinction. Check that `.env` is in `.gitignore`.

## 5. CLAUDE.md gates (tool installation — ASK FIRST)

⚠️ This step installs a **tool**, not a document; ask the user and do not proceed without approval.

`CLAUDE.md` files enter context in **every session and every subagent turn** in
that directory; bloat is both a cost and a **visibility** problem (nobody finds a
rule in a 170 KB file). Two gates hold the line — the canonical copies live in
`${CLAUDE_PLUGIN_ROOT}/scripts/`, with detail in `${CLAUDE_PLUGIN_ROOT}/scripts/README.md`:

```bash
mkdir -p scripts && cp "${CLAUDE_PLUGIN_ROOT}"/scripts/md-*.sh "${CLAUDE_PLUGIN_ROOT}"/scripts/md-*.py scripts/
bash scripts/md-size-gate.sh --init     # writes scripts/md-budget.tsv: every CLAUDE.md, ceiling = TODAY's size
```

- **Never copy this repository's `md-budget.tsv`:** its ceilings and exclusions are ours,
  and `--update` only lowers rows that already exist, so the project's own `CLAUDE.md`
  files would stay "NO BUDGET". `--init` writes the project's budget and refuses to
  overwrite one that exists.
- The tools are **copied into the project and committed there** — a project's gate
  cannot depend on a path outside the repository (this happened once: the tool was
  in no repository at all and the line pointing to it referenced a dead path for
  three weeks).
- Add a `bash scripts/md-size-gate.sh` step to the project's merge/CI gate.
  If there is no gate, **do not create one — report it**; installing a gate is a
  separate request.
- If a size gate already exists, **do not install a second one**; use the existing
  one. **The test (run it, do not guess):** if
  `grep -rlE 'md-size-gate|md-budget|claude-md-budget' scripts/ .github/ 2>/dev/null`
  is not empty, a gate exists — skip the installation and report it. (This exact
  check was once skipped: a second gate was written next to the existing one and
  their baselines contradicted each other.)

⚠️ **Do not propose shrinking.** A ratcheted ceiling stops growth, which is the
whole point. Splitting happens only if the **root** `CLAUDE.md` is very large, and
only by **moving** content (never by summarising it); the result is verified with
`md-rule-gate.py`.

## 6. Working mode (optional)

If the project carries no `.claude/mode` file, mode **B** applies.
To request a different agent set: `/adyusuf:working-mode <A|C|D|E>`; to run the Opus
agents on another model, add it: `/adyusuf:working-mode C sonnet` (written to
`.claude/mode-model`; the letter alone removes it).
Definitions are in `${CLAUDE_PLUGIN_ROOT}/modes/README.md`, the rule in `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md` #27.
⚠️ `.claude/*` is gitignored in most projects; the mode file **must be committed**
(narrow `!.claude/mode` and `!.claude/mode-model` exceptions are needed) — they are a
project setting, not personal session state.

## 6a. Plan file (`${CLAUDE_PLUGIN_ROOT}/standards/22-live-board.md`)

`/adyusuf:board-plan` keeps each session's plan in `.claude/board/plan-<session>.md`.

1. `.gitignore`: `.claude/board/` must be ignored (runtime data). Verify:
   `git check-ignore -v .claude/board/x` matches.
2. A project wired to the OLD live board still has its hooks in `.claude/settings.json`
   (commands running `scripts/board/board_*.py`): remove those entries — **merge, never
   overwrite**, keep every other hook — and check `python3 -m json.tool .claude/settings.json`.
   Report it; the board they fed no longer exists (`standards/22` §2).

## 7. Report

- Files created / updated
- `<TODO>` fields that could not be filled — as clear questions to the user
- Existing conditions you found that contradict the standards (hard-coded URL, a secret in the repo, no backup, no `SETUP.md`) — **report them, do not fix them**

Make no code changes; produce documents only — **the single exception is the tool
copy in §5**, and that one needs the user's approval. Fixing code is a separate request.

## Why this command exists

A project that only one session knows how to run is a project nobody else can pick up.
Every project should carry the same baseline: a `CLAUDE.md` with its own rules, a
`SETUP.md` that sets up a clean machine without guesswork (with the secret/token
inventory), and an `.env.example`. This command brings a new or existing project to
that baseline — it fills in what is missing and never deletes what is there — so every
later session, agent or person starts from the same written facts instead of rediscovering them.

Contributions are welcome: https://github.com/adyusuf/claude-code-standards
