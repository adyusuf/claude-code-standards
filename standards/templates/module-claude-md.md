# <module> — module guide (`<backend|web|mobile|infra>/CLAUDE.md`)

> Claude Code loads this file **only when it works inside this directory**, so a
> module's detail costs nothing in a session that never touches it. That is the whole
> point: keep the root `CLAUDE.md` small and move module-specific detail here.
>
> **This file only ADDS.** It never restates a root rule or a standard, it can tighten
> a rule but never loosen one, and it **cannot override #29** (80% line coverage).
> Every `CLAUDE.md` needs a line in `scripts/md-budget.tsv` — a file with no budget is
> red (`scripts/md-size-gate.sh`). Target: under 60 lines.

## What this module is

<One sentence: what it holds, who consumes it, what it must never do.>

## Commands (the ones that work from THIS directory)

| Task | Command |
|---|---|
| Install | `<command>` |
| Run | `<command>` |
| Unit tests | `<command>` |
| Coverage (must stay ≥ 80%, measured for this codebase on its own) | `<command>` |
| Lint / format | `<command>` |

## Conventions specific to this module

- <A convention that is true here and not elsewhere — a folder layout, a naming rule,
  a layering direction. If it is true everywhere it belongs in the root file.>
- <...>

## Never in this module

- <A prohibition that only makes sense here — e.g. "no EF entity leaves the
  repository layer", "no `fetch` outside `src/api/`".>

## Read before changing this module

Pick the rows that apply and delete the rest:

| Module | Standards |
|---|---|
| `backend/` | `04-dotnet.md` · `07-api-design.md` · `08-backward-compatibility.md` · `09-database.md` |
| `web/` | `05-react.md` · `02-ui-ux.md` · `07-api-design.md` |
| `mobile/` | `06-mobile.md` · `12-maestro.md` · `02-ui-ux.md` |
| `infra/` | `14-devops.md` · `19-cloudflare-and-edge.md` · `20-hardening.md` · `21-backup-and-recovery.md` |
