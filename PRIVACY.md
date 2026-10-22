# Privacy policy — the `adyusuf` plugin

Last updated: 22/10/2026 · Maintainer: Adnan Yusuf (<https://github.com/adyusuf>)

The `adyusuf` plugin is a set of working rules, skills, commands, role agents, hooks and scripts for Claude
Code. It has **no service of its own**: nothing it contains runs on a server the maintainer operates, and the
maintainer receives no data from it. The full inventory is in
[README › What this does to your machine](README.md#what-this-does-to-your-machine).

## What it reads

All reading happens on your own machine. Nothing read is sent anywhere by the plugin.

- **The hooks** read this plugin's `CLAUDE.md`, your `~/.claude` folder (links and `settings.json`, to warn
  about an old install), the command Claude is about to run (to refuse destructive ones) and a `CLAUDE.md` you
  edit (to check its size).
- **The settings and the rail boxes** (`scripts/adyusuf_config.py`, `hooks/register.tsx`) read your own and a project's
  `adyusuf.json`, `~/.claude/plugins/installed_plugins.json` (to find the installed copy of this plugin) and, for the
  Promotion box, the branch names, commit messages and `Gate-Waived:` lines of the repository you are in, through
  read-only `git` commands.
- **`scripts/step-stats.py`** reads Claude Code's local session transcripts (`~/.claude/projects`), and only
  when you run it. Transcripts can contain personal data.

## What it stores

- `step-stats.py` writes only aggregate counts (steps, tokens) to `docs/measurement-log.md`. A sanitiser
  removes project names and paths, and the script refuses to write when one survives.
- `install.py` and `plugin-setup.py` write logs (and `plugin-setup.py` a copy of your `adyusuf.json` before it replaces
  the plugin) under `~/.claude-standards/` on your machine.
- Changing a setting (in the rail boxes or with `/adyusuf:config`) writes `~/.claude/adyusuf.json`, or a project's
  `.claude/adyusuf.json` when you ask for the project layer. A short lock file goes to your temp folder while it writes.
- Nothing is retained anywhere else.

## What it sends

The plugin itself sends nothing. Data leaves your machine only through steps **you** start:

- **The gate**, which you run in your own project, can do three things that reach the network:
  - install your dependencies and fetch security advisories from your package registries;
  - call a test-deploy URL that you set (`TEST_VERSION_URL`);
  - ask GitHub, when you run `scripts/plugin-setup.py`, for the newest commit of the plugin's branch (`git ls-remote`),
    and let the `claude plugin` commands it starts fetch the marketplace from GitHub; it sends nothing of yours;
  - ask GitHub through `gh api` whether a repository is private (`require-private-remote.sh`, a hook you
    install yourself).

## Your choices

Disable or uninstall the plugin with `/plugin`.

## Contact

Questions about this policy: open an issue at <https://github.com/adyusuf/claude-code-standards/issues>.
