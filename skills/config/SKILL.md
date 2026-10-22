---
name: config
description: Shows or changes the adyusuf defaults that replace questions - working mode and the model for the Opus agents, whether unit tests and e2e specs are written, which of dev/test/prod are merged and pushed, and which tests run before a push. Also shows which agents the mode enables and the model each one runs on. Use it when the user says "/adyusuf:config", "change the defaults", "stop asking me", "don't push prod", "run e2e before test", "show the settings" or "which agents are active".
---

# adyusuf configuration

Claude does not ask what a setting already answers (global rule #34). These settings are the answers. The user
changes them here; everything else in this skill is mechanics.

Layers, lowest first: the plugin's `defaults/adyusuf.json` < the user's `~/.claude/adyusuf.json` < the project's
`.claude/adyusuf.json` (committed, like `.claude/mode`). A change is written to the **user** layer unless the user says
"for this project", which writes the project layer.

The tool is `${CLAUDE_PLUGIN_ROOT}/scripts/adyusuf_config.py` (`python3`):

| The user says | Run |
|---|---|
| "show the settings" | `show` (add `--json` for a machine view), then `agents` |
| no argument / "change the settings" / "open the settings" | `show`, then the clickable questions below ("Changing settings with clicks") |
| "which agents are active" | `agents` (`--all` includes the inactive ones): the roles that run and the model each runs on |
| "don't push prod" / "push prod: no" | `set push.prod no` |
| "run unit tests before dev" | `set run_before_push.dev.unit yes` |
| "mode D, haiku" | `set mode D` and `set mode_model haiku` |
| "turn qa off" / "developer on haiku" | `set agents.qa.enabled off` / `set agents.developer.model haiku` |
| "all agents back to the mode" | `reset-agents` (add `--project` for the project layer) |
| "for this project only" | add `--project` |
| "back to the default" | `unset <key>` (add `--project` for the project layer) |
| several at once | `apply <file or ->` with a JSON object `{"push.prod": false, ...}` |
| "what can I change" | `schema` |
| "update the plugin" / "get the new version" | Run, in this order, with Bash: `claude plugin marketplace update adyusuf-marketplace`, then `claude plugin update adyusuf@adyusuf-marketplace`, then `claude plugin list` and report the version. Tell the user to run `/reload-plugins` (a plugin loads into a session only after that). The slash form `/plugin marketplace update ...` only opens the plugin page, which is why this goes through the shell. If the plugin is not installed at all: `claude plugin install adyusuf@adyusuf-marketplace`. |

A value that is not valid is refused and **nothing is written** (exit 2); an unreadable file is never overwritten
(exit 1) - say which file and let the user fix or delete it. After a change, print the changed line and say which layer it
went to. Never edit the JSON files by hand when the tool can do it.

## The settings, and who reads them

| Key | Values | Meaning |
|---|---|---|
| `mode` | A-E | The operating mode (`modes/README.md`). A per-session choice (`$S/mode`) or a project `.claude/mode` beats it. |
| `mode_model` | keep, sonnet, haiku, fable | What the Opus-defined agents run on (`keep` = as defined). Same override order as `mode`. |
| `agents.<role>.enabled` | auto, on, off | One of the 14 roles: `auto` follows the mode's set, `on` adds it, `off` removes it (mode A runs none). |
| `agents.<role>.model` | default, opus, sonnet, haiku, fable | The model that one agent runs on; `default` follows its definition and the mode's Opus override. |
| `write.unit_tests` | yes/no | Write unit tests when the code is done (#32). |
| `write.e2e` | yes/no | Write e2e specs (optional to run, #33). |
| `merge.dev` `merge.test` `merge.prod` | yes/no | Merge finished code into that branch (#26, #34). |
| `push.dev` `push.test` `push.prod` | yes/no | Push that branch after its merge. |
| `run_before_push.<t>.unit` / `.e2e` | yes/no | Run that gate before pushing `<t>`. Not run = recorded as `Gate-Waived:` on the merge commit (#34). |

## Changing settings with clicks

When the user wants to change settings without naming them (no argument, "change the settings", "open the settings"),
do not ask in prose and do not build a page: show `show`, then ask with the `AskUserQuestion` tool, which draws
clickable buttons, checkboxes and dropdowns in the app. Put the current value in each question or option ("now: yes"),
because the tool cannot pre-select.

1. **One question, `multiSelect: true` (checkboxes): "Which settings do you want to change?"** with four options:
   *Mode and model* · *Writing* (unit tests, e2e) · *Merge, push and gates* · *One agent*.
2. **One `AskUserQuestion` call for each ticked group** (at most four questions per call, two to four options each):
   - *Mode and model*: mode as buttons A / B / C / D (E through "Other"), then `mode_model` as buttons keep / sonnet /
     haiku / fable.
   - *Writing*: `write.unit_tests` and `write.e2e`, each as yes / no buttons.
   - *Merge, push and gates*: four checkbox questions (`multiSelect: true`), options dev / test / prod: "Merge into",
     "Push", "Run unit tests before the push", "Run e2e before the push". A ticked box is yes, an unticked one no.
   - *One agent*: the role (qa, developer, architect, security, any other through "Other"), then `enabled` as buttons
     auto / on / off and `model` as buttons default / sonnet / haiku / opus (fable through "Other").
3. **Write all the answers with one `apply`** (validated all-or-nothing), print `show`, and say which layer it went to.
   Skip a question the user did not tick in step 1, and never ask again for what they answered.

## When a change takes effect

At once, but never in the middle of a step. The files change immediately. A `UserPromptSubmit` hook and a `PostToolUse` hook (agent calls and shell
commands, the task boundaries) run `adyusuf_config.py notify`: the first time a session sees different effective settings it
receives a note naming what changed, and the note says to apply them **from the next task** and not to restart or split the
step in progress. A note is sent once per change and per session; a session that never saw the settings stays silent.

## What reads the settings

- The `SessionStart` hook prints `context`: the effective values and the agents, so every session starts knowing them.
- Rule #34 (`CLAUDE.md`): the merge/push/gate behaviour. A gate set to no is **not run and recorded**, never skipped
  silently; a red gate that was asked for still blocks. Force pushes, DROP, deploys and `main` stay out of reach of every
  setting (`guard-destructive.sh`, #20, #27).
- `adyusuf:working-mode` falls back to `mode` / `mode_model` when no session or project choice exists.
