# <Project name> — Claude Code guide

> This file is the main entry point Claude Code reads automatically in every
> session. **Keep it short** (target: under 200 lines). Leave the detail to the
> `docs/` folder and to the `CLAUDE.md` files of the subdirectories.
> The global software standards live under `~/.claude/standards/` — this file
> holds **only what is specific to this project**. A rule here overrides the
> global standard.

## The project in one sentence

<What it does, who for, which problem it solves — one sentence.>

## Core principles (the project's DNA)

- **<Principle>.** <One sentence of explanation and its consequence.>
- **<Principle>.** ...

## Architecture

- **`backend/`** — <technology>, <database>. Port `<port>`.
- **`web/`** — <technology>. Port `<port>`.
- **`mobile/`** — <technology>.

Clients consume the API only. Business logic is **never** performed on a client.

### Which API / which environment

| Situation | URL |
|---|---|
| Local API | `http://localhost:<port>` |
| Test | `https://<test-domain>` |
| Production | `https://<prod-domain>` |
| Swagger (test only) | `https://<test-domain>/swagger` |

Topology: <single origin (`/api` under the UI) or a separate subdomain — and why>

## Setup

Setting up from scratch: **`SETUP.md`**. The secret inventory, the prerequisites
and the port map are there. Deployment and servers: **`DEPLOY.md`**.

## Branch and deploy flow

```
feature branch → dev → (approval) → test → (approval) → prod
```

- **No** direct commit or PR to `test`/`prod`; only from the previous stage, **with the user's approval**.
- The "merge" command means <what it means in this project, and which script runs>
- No merge without passing the gate (build + tests + format + lint + backward-compatibility scan).

## Context routing

| Kind of task | Read first |
|---|---|
| Backend endpoint / service / migration | `backend/CLAUDE.md` |
| Web page / component / styling | `web/CLAUDE.md` |
| Mobile screen / navigation | `mobile/CLAUDE.md` |
| A new feature (end to end) | `docs/vision.md`, `docs/requirements.md` |
| A domain / business-logic question | `docs/modules/<module>.md` |

## Modules

1. **<Module>** — <one line>
2. ...

> ⚠️ **REMOVED MODULES:** <if any — listed so they are not re-added>

## Project-specific rules

> The global rules are in `~/.claude/CLAUDE.md`. Only **what differs** goes here.

1. **<Rule>.** <Why — a rule whose reason is unwritten gets reverted by accident later.> (<Date>, PERMANENT)
2. ...

## Never-do list

- ❌ <Something specifically forbidden in this project, and why>
- ❌ ...

## Backward-compatibility inventory

| Field/Endpoint | Obsoleted on | Replaced by | Condition for removal | Status |
|---|---|---|---|---|
| | | | | |

## Automation

The hooks in `.claude/settings.json`:
- `<hook>` — <what it does>

## Quick reference

- Setup: `SETUP.md`
- Deploy / servers / DNS / certificates: `DEPLOY.md`
- Backup drills: `docs/backup-drills.md`
- Vision / requirements: `docs/vision.md`, `docs/requirements.md`
- Glossary: `docs/glossary.md`
- Decisions: `docs/adr/`
