---
name: config
description: Shows or changes the adyusuf defaults that replace questions - working mode and the model for the Opus agents, monitor connection and message format, whether unit tests and e2e specs are written, which of dev/test/prod are merged and pushed, and which tests run before a push. Also shows which agents the mode enables and the model each one runs on. Use it when the user says "/adyusuf:config", "change the defaults", "stop asking me", "don't push prod", "run e2e before test", "show the settings" or "which agents are active".
---

# adyusuf configuration

Claude does not ask what a setting already answers (global rule #34). These settings are the answers. The user
changes them here, or in the panel (below); everything else in this skill is mechanics.

Layers, lowest first: the plugin's `defaults/adyusuf.json` < the user's `~/.claude/adyusuf.json` < the project's
`.claude/adyusuf.json` (committed, like `.claude/mode`). A change is written to the **user** layer unless the user says
"for this project", which writes the project layer.

The tool is `${CLAUDE_PLUGIN_ROOT}/scripts/adyusuf_config.py` (`python3`):

| The user says | Run |
|---|---|
| "show the settings" / no argument | `show` (add `--json` for a machine view), then `agents` |
| "which agents are active" | `agents`: the role set of the mode and the model each runs on |
| "don't push prod" / "push prod: no" | `set push.prod no` |
| "run unit tests before dev" | `set run_before_push.dev.unit yes` |
| "mode D, haiku" | `set mode D` and `set mode_model haiku` |
| "for this project only" | add `--project` |
| "back to the default" | `unset <key>` (add `--project` for the project layer) |
| several at once | `apply <file or ->` with a JSON object `{"push.prod": false, ...}` |
| "what can I change" | `schema` |

A value that is not valid is refused and **nothing is written** (exit 2); an unreadable file is never overwritten
(exit 1) - say which file and let the user fix or delete it. After a change, print the changed line and say which layer it
went to. Never edit the JSON files by hand when the tool can do it.

## The settings, and who reads them

| Key | Values | Meaning |
|---|---|---|
| `mode` | A-E | The operating mode (`modes/README.md`). A per-session choice (`$S/mode`) or a project `.claude/mode` beats it. |
| `mode_model` | keep, sonnet, haiku, fable | What the Opus-defined agents run on (`keep` = as defined). Same override order as `mode`. |
| `monitor.connect` | yes/no | Whether the installer connects the monitor agent (`scripts/install.py`; `no` = `--no-monitor`). |
| `monitor.message_format` | short, full | The format of messages that come from the monitor. Stored here; the agent's own setting is in the claude-monitor project. |
| `write.unit_tests` | yes/no | Write unit tests when the code is done (#32). |
| `write.e2e` | yes/no | Write e2e specs (optional to run, #33). |
| `merge.dev` `merge.test` `merge.prod` | yes/no | Merge finished code into that branch (#26, #34). |
| `push.dev` `push.test` `push.prod` | yes/no | Push that branch after its merge. |
| `run_before_push.<t>.unit` / `.e2e` | yes/no | Run that gate before pushing `<t>`. Not run = recorded as `Gate-Waived:` on the merge commit (#34). |

## The panel

"Show the settings in the right-hand boxes" means the settings panel: an Artifact with a checkbox for every yes/no
setting, a dropdown for every list, and a box listing the agents the mode enables with the model each runs on. Build it
from `panel-data` (never hard-code the keys), publish it with the Artifact tool in the current session, open it in the side
pane, and keep what the user changes in the artifact's own database. To apply the user's changes ("apply the panel"):
read the panel's values with `ArtifactData` (collection `settings`, document `current`, field `values`; no document means nothing was
changed in the panel), then `apply` them as one JSON object - validated all-or-nothing - and print `show`. When a setting changes from the command line, update the panel's stored values too, so the two never disagree.

## What reads the settings

- The `SessionStart` hook prints `context`: the effective values and the agents, so every session starts knowing them.
- Rule #34 (`CLAUDE.md`): the merge/push/gate behaviour. A gate set to no is **not run and recorded**, never skipped
  silently; a red gate that was asked for still blocks. Force pushes, DROP, deploys and `main` stay out of reach of every
  setting (`guard-destructive.sh`, #20, #27).
- `adyusuf:working-mode` falls back to `mode` / `mode_model` when no session or project choice exists.
