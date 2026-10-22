# Setup

How to bring this repository up on a clean machine and prove it works, in one
sitting and without guessing (rule #16, `standards/18-setup-and-environment.md`).

This repository is a rule set, a set of agent and mode definitions and the gate
scripts that enforce them. It has **no server, no database, no API and no web or
mobile client**, so there is no `.env` file to fill in and no port to open. What
"setup" means here depends on what you want to do with it:

| You want to... | Do this |
|---|---|
| Read it, or take a few rules into your own `~/.claude` | Nothing to install. Follow Levels 0-3 in [`README.md`](README.md#how-to-use-this) |
| Use it in every session (the `adyusuf` plugin) | §6 below |
| Change it (rules, scripts, agents) and pass its own gate | §1-§5 |
| Put the gate into another project | [`README.md`](README.md#putting-the-gate-in-a-project-of-your-own) |

## 1. Prerequisites

The version column is what this setup was **last verified with** (01/10/2026, macOS);
older versions are not claimed to work. Pin your own in `.tool-versions` if you
want it enforced.

| Tool | Version | Install (macOS) | Why |
|---|---|---|---|
| git | 2.42 | `xcode-select --install` | Worktrees, the promotion flow |
| Python | 3.9.13 | `brew install python` | Every script under `scripts/` and the unit tests |
| bash | 5.3 | `brew install bash` | The gate scripts; the shell coverage tracer cannot trace macOS's `/bin/bash` (SIP) |
| gitleaks | 8.30 | `brew install gitleaks` | Secret scan: pre-commit hook and the gate |
| ShellCheck | 0.11.0 | `brew install shellcheck` | SAST for the shell scripts |
| CodeQL CLI | 2.27.1 | `brew install --cask codeql` | SAST for the Python |
| kcov | 43 | `brew install kcov` | Line coverage of the shell scripts |
| Deno | 2.x | `brew install deno` | Line coverage of the mod's engine-free TypeScript logic (`hooks/choose.ts`, rule #29 exception, `standards/10` §7.2a) |
| `coverage` (Python package) | 7.10.7 | §2, step 3 | Line coverage of the Python scripts |
| Node.js | 22 | `brew install node` | Only to run the coverage step on a copy of the scripts that carries JavaScript; this repository has none |
| GitHub CLI (`gh`) | 2.23.0 | `brew install gh` | Only for `require-private-remote.sh` and opening pull requests |
| Claude Code | 2.1.294 | <https://claude.com/claude-code> | The plugin (§6); its hooks call `python3` and `bash` by name |

**Windows** (the plugin, §6; last verified 04/10/2026 on Windows Server 2022 with Python 3.12.10 and
Git 2.54): `bash` is **Git for Windows**' (`C:\Program Files\Git\bin\bash.exe`; it does not have to be on
`PATH`, Claude Code finds it). The python.org installer provides `python` but **no `python3`**: the guard falls
back to `python`, but the plugin's other hooks call `python3` by name — **without it every session runs with no
global rules** — so create it once from an administrator shell —
`mklink /H "C:\Program Files\Python312\python3.exe" "C:\Program Files\Python312\python.exe"` (adjust the
version).
To run the unit tests on Windows, put Git's `usr\bin` **before** its `bin` on `PATH` — `bin\bash.exe` is a
launcher that puts `/mingw64/bin` first and hides the tests' stub tools — and set `PYTHONUTF8=1`
(`scripts/coverage.sh` sets it; without it the cp1252 console codec garbles every ✓/✗):

```powershell
$env:PATH = "C:\Program Files\Git\usr\bin;C:\Program Files\Git\bin;$env:PATH"; $env:PYTHONUTF8 = '1'
python -m unittest discover -s scripts/tests -p 'test_*.py'
```

Two tests need a real ShellCheck and fail without it (it is a prerequisite, §1); five need a real Node 22+ and are
skipped without it; five that simulate a kcov run are skipped on Windows. ⚠️ **The test and prod gates cannot be green on Windows:** kcov does not exist
there, so shell coverage is NOT MEASURED and #29 blocks the promotion, as it must. Promote from macOS.

**CodeQL on Windows** (no package manager entry): download `codeql-win64.zip` of the version in §1 from the
`github/codeql-cli-binaries` releases (`gh release download v2.27.1 --repo github/codeql-cli-binaries --pattern
'codeql-win64.zip*'`), compare `sha256sum codeql-win64.zip` with the `.checksum.txt` beside it, unzip it to
`%USERPROFILE%\tools\codeql-<version>` and put a two-line wrapper named `codeql` on Git Bash's `PATH`
(`%USERPROFILE%\bin`): `#!/usr/bin/env bash` and `exec "<that folder>/codeql/codeql.exe" "$@"`. The query packs
are downloaded by the first scan (`--download`). Last verified 18/10/2026 on Windows Server 2022.

A missing tool is never silent: the gate reports the step as **NOT RUN**, the
result is INCOMPLETE and the exit code is not 0 (#19, #25). You can start with
just git and Python and add the rest as the gate asks for it.

## 2. Clone and install

```bash
git clone https://github.com/adyusuf/claude-code-standards
cd claude-code-standards
```

1. Install the commit hooks (the `CLAUDE.md` size gate, `gitleaks` over staged
   content, the documentation check, the real-name check on file names, added
   lines and the commit message). **Run this once, in the main checkout you just
   cloned, not in a linked worktree**: there `.git` is a file, not a directory,
   and the installer fails. The hooks are symlinks in the shared git directory
   that point at `scripts/` of that main checkout, so they run that checkout's
   scripts whichever worktree you commit from:

   ```bash
   bash scripts/pre-commit.sh --install
   ```

2. Work on a branch off `dev`, in a worktree, never on `prod` (#26):

   ```bash
   git fetch origin
   git worktree add ../claude-code-standards-wt-<topic> -b <type>/<topic> origin/dev
   ```

3. Create the Python environment the coverage step expects. It is kept **outside**
   the repository so no interpreter of yours is touched:

   ```bash
   python3 -m venv ~/.cache/claude-standards/venv
   ~/.cache/claude-standards/venv/bin/pip install coverage
   ```

4. Create your local real-name map (see §4). Without it the real-name check
   warns and does nothing.

There is no dependency manifest: the scripts use only the Python standard
library and the tools in §1.

## 3. Secret and token inventory

**This repository holds no secrets and needs none to run.** Nothing reads a `.env`
file: the optional settings in §4 are plain shell variables. [`.env.example`](.env.example)
lists all of them, commented, for the checklist in rule #16; it is documentation
and nothing loads it.

| Name | What it is for | Where to obtain it | Where it is stored | Owner | Rotation |
|---|---|---|---|---|---|
| GitHub CLI login (`gh auth login`) | `require-private-remote.sh` asks GitHub whether a remote is private; opening pull requests | GitHub → your account; `gh auth login` and follow the prompts | `~/.config/gh/hosts.yml`, a plain-text file written by `gh` (check with `gh auth status`) | The person running the commands | Whenever the token is revoked; `gh auth refresh` |
| `TEST_VERSION_URL` (optional) | A test-deploy version endpoint the gate may `curl` | Your own test environment. **Not a secret**, and unused by this repository | Your shell, only if you set it | The person running the gate | n/a |

Rules that apply here and are enforced by the hooks: a secret never enters the
repository (#3); a leak is rotated first and cleaned up second.

## 4. Environment variables (all optional)

Set them in your shell or on the command line. None has to be set; the same list, commented, is in [`.env.example`](.env.example).

| Variable | Default | Effect |
|---|---|---|
| `COVERAGE_VENV` | `~/.cache/claude-standards/venv` | Where `scripts/coverage.sh` looks for `coverage` |
| `COVERAGE_MIN` | `80` (also set in `scripts/merge-gate.conf`) | Line-coverage threshold per codebase. #29 forbids lowering it; the gate does not enforce that, so a lowered value is caught in review |
| `REAL_NAMES_MAP` | `docs/project-nicknames.tsv` in this or the main worktree | Path of the real-name map |
| `REAL_NAMES_STRICT` | `0` | `1` makes a missing map a failure instead of a warning |
| `GATE_PARALLEL_NODE` | `0` | `1` runs the Node track in parallel (only meaningful for a project with a Node codebase) |
| `GATE_CHECK_TEST_DEPLOY` | `0` | `1` makes the prod gate verify the deployed SHA on test (`TEST_VERSION_URL` / `TEST_DEPLOY_SHA_CMD`); by default it does not look at test and warns |
| `TEST_VERSION_URL`, `TEST_DEPLOY_SHA_CMD`, `E2E_WEB_CMD`, `E2E_MOBILE_CMD` | unset | Test-environment hooks of the gate (read only with `GATE_CHECK_TEST_DEPLOY=1` / `GATE_RUN_E2E=1`). Here the "test tier" is the pushed `test` branch (`scripts/merge-gate.conf`) |

**The real-name map.** `docs/project-nicknames.tsv` is git-ignored and local. One
line per project you work on, tab-separated: `<folder key>`, `<nickname>`, an
optional comma-separated list of aliases, and an optional `public` marker for a
name that is not secret. The check blocks a commit whose staged content or
message contains a folder key or alias; a deliberate exception is made with
`git commit --no-verify` and is yours to make, never an environment switch.

## 5. Verification

Each command is runnable and exits 0 when the step is healthy.

```bash
# 1. The unit tests (standard library only)
python3 -m unittest discover -s scripts/tests -p 'test_*.py'

# 2. What the gate would run, without running it
bash scripts/gate-core.sh dev --list

# 3. The real gate for a promotion to dev; the exit code is the verdict.
#    It reports and does not merge or push. Its twin-drift step compares this
#    repository with sibling project checkouts and prints n/a when there are none.
bash scripts/merge-gate.sh dev

# 4. Coverage of the scripts, per codebase (Python and shell, threshold 80%)
bash scripts/coverage.sh

# 5. The hooks are installed
ls -l "$(git rev-parse --git-common-dir)/hooks/pre-commit" "$(git rev-parse --git-common-dir)/hooks/commit-msg"

# 6. The personal settings file is untracked: prints the .gitignore rule that matches
git check-ignore -v .claude/settings.local.json
```

Then prove the pre-commit hook is wired, because a gate you have never watched
fail is a gate you do not yet know is wired: in a throwaway branch stage a file
containing a fake-looking key and confirm that `git commit` is **refused**.

A step that reports NOT RUN is a missing tool from §1, not a pass.

## 6. Installing the rule set: the `adyusuf` plugin

The rule set installs like every other Claude Code plugin — copied into Claude Code's plugin cache, no links, no
install script. In a Claude Code session (or the same words after `claude plugin` in a shell):

```
/plugin marketplace add adyusuf/claude-code-standards#prod
/plugin install adyusuf@adyusuf-marketplace
```

Start a new session. **Verify:** the session's context carries `[Global working rules, part 1/…` (ask Claude to
quote it), `/adyusuf:software-standards` opens, and `python3 <checkout>/scripts/plugin-setup.py --check` ends
with `✓ the installed plugin is the newest`. **Where it works:** fully in Claude Code (terminal, desktop app, IDEs) and in
Cowork, which loads hooks and agents. In claude.ai chat only the skills and commands work: chat skips hooks and
agents, so the global rules, the guard and the 14 roles are not there. The plugin brings the global rules (its `SessionStart` and
`SubagentStart` hooks print `CLAUDE.md` through `scripts/rules-context.py`), every `/adyusuf:*` skill and command,
the 14 role agents as `adyusuf:<role>`, the destructive-command guard and the `CLAUDE.md` size hook. Nothing is
written into `~/.claude` by hand; read the warning in
[`README.md` Level 4](README.md#level-4--run-it-live-the-way-i-do) first.

- **The right-hand boxes (part of the plugin):** the Settings, Agents and Promotion boxes open in the rail at session start
  and with `/adyusuf:panels`. They run `git` and `python3` locally and contact no server. They show the settings of the
  installed copy, so `/plugin update adyusuf` brings new settings into them. Where mods are not switched on, the session
  asks once ("Turn on the mods…"); the config skill falls back to clickable questions in the chat.
- **Update:** `/plugin marketplace update adyusuf-marketplace`, then `/plugin update adyusuf` and `/reload-plugins`
  (or turn auto-update on for the marketplace under `/plugin` › Marketplaces). The plugin has no `version`, so every
  commit on `prod` is a new version. Never edit the cache: the next update replaces it.
- **Another branch:** `/plugin marketplace add adyusuf/claude-code-standards#test`. To try a working copy without
  installing it: `claude --plugin-dir <worktree>` (it takes precedence over the installed plugin for that session).
**One script for install and update:** `scripts/plugin-setup.py` (standalone, standard library only; download and run it with the
macOS/Linux or Windows commands at [the top of `README.md`](README.md#install)). It asks GitHub for the newest
commit of `prod`, then: not installed → links the marketplace and installs; already newest → nothing; older →
asks "Remove the old one and install the new one?" and on yes removes it (`--keep-data`), installs the new one and
checks that `~/.claude/adyusuf.json`, the enabled state and the marketplace link are unchanged. `--check` reports only
(exit 1 when work is due), `--yes` skips the question, `--ref <branch>` picks the branch for a first link. It needs
`git` on `PATH` and the `claude` program: on `PATH`, in the installers' usual folders, in the copy the Claude desktop
app keeps for its Code tab, or given with `--claude <path>`; with only the desktop app and none of those found it
prints the two `/plugin` commands to type in the app's Code tab. It reaches GitHub; log: `~/.claude-standards/logs/plugin-setup-<stamp>.log`, backup of
your settings file: `~/.claude-standards/backups/plugin-setup-<stamp>/`.

## 7. Common errors

| Symptom | Cause | Fix |
|---|---|---|
| Gate prints `NOT RUN` and exits 3 | A tool from §1 is missing | Install it and rerun. The step did not pass |
| `coverage.sh`: `NOT MEASURED: no coverage in ...` | The venv from §2 step 3 does not exist | Create it |
| Shell coverage `NOT MEASURED` | kcov missing, or only macOS `/bin/bash` available | `brew install kcov bash` |
| Commit refused by the real-name check | A folder key or alias from your map is in the staged change or message | Use the nickname. The exception is `--no-verify`, and yours alone |
| Real-name check prints a warning and passes | No `docs/project-nicknames.tsv` | Create it (§4), or set `REAL_NAMES_STRICT=1` to make this a failure |
| `CLAUDE.md` size gate refuses a commit | The file grew past its ceiling in `scripts/md-budget.tsv` | Move the rule into `standards/<topic>.md` first; raise the ceiling only with a written reason |
| A session has no `[Global working rules` in its context | `python3` not on `PATH` (Windows, §1), or the plugin is disabled | Add `python3`; `/plugin` › Installed › enable `adyusuf` |
| Every Bash call mentioning push/rm/drop is BLOCKED with "no Python 3 interpreter" | Neither `python3` nor a Python 3 `python` on the hook's `PATH` | Install Python 3; on Windows add `python3.exe` (§1) |
| Gate runs on stale branches | The local `dev`/`test` are behind `origin` | `git fetch`, and branch off `origin/dev` |

## 8. When this file must change

In the same change as the cause, never after it (#16): a new tool in a script
means a new row in §1; a new environment variable means a row in §4; a new
secret or token means a row in §3; a changed install or hook step means §2 or §6.
