---
description: Install or update this project's standard documents (CLAUDE.md, SETUP.md, .env.example)
---

Bring this project in line with the `~/.claude/standards/` layout. **Do not delete what exists; fill in what is missing.**

## 1. Discovery (read first, write second)

- The root directory, `package.json` / `*.csproj` / `docker-compose.yml` / `.github/workflows/`
- Any existing `CLAUDE.md`, `README.md`, `SETUP.md`, `DEPLOY.md`, `.env*`
- The real ports, the real service names, the real branch flow (`git branch -a`)

**Never write a guess.** Leave any field you do not know as `<TODO: ...>` and list them at the end.

## 2. `CLAUDE.md`

- If missing: create it from `~/.claude/standards/templates/project-claude-md.md`, filled in with **real** information.
- If present: do not delete it. Add only the missing sections and put this note at the top (if it is not there already):

  ```
  > Global software standards: `~/.claude/standards/` (`~/.claude/CLAUDE.md` is loaded in every session).
  > This file holds only the rules **specific to this project**; a rule here overrides the global standard.
  ```

- Target: under 200 lines. Propose moving long historical detail into `docs/` (with the user's approval).

## 3. `SETUP.md`

From `~/.claude/standards/templates/setup-md.md` — the critical section is **§3, the secret/token inventory**:
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
`~/.claude/scripts/`, with detail in `~/.claude/scripts/README.md`:

```bash
mkdir -p scripts && cp ~/.claude/scripts/md-*.sh ~/.claude/scripts/md-*.py scripts/
bash scripts/md-size-gate.sh --update   # the ceiling becomes TODAY's size
```

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
To request a different agent set: `/working-mode <A|C|D|E>`.
Definitions are in `~/.claude/modes/README.md`, the rule in `~/.claude/CLAUDE.md` #27.
⚠️ `.claude/*` is gitignored in most projects; the mode file **must be committed**
(a narrow `!.claude/mode` exception is needed) — it is a project setting, not
personal session state.

## 7. Report

- Files created / updated
- `<TODO>` fields that could not be filled — as clear questions to the user
- Existing conditions you found that contradict the standards (hard-coded URL, a secret in the repo, no backup, no `SETUP.md`) — **report them, do not fix them**

Make no code changes; produce documents only — **the single exception is the tool
copy in §5**, and that one needs the user's approval. Fixing code is a separate request.
