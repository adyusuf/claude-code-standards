# Privacy policy — the `adyusuf` plugin

Last updated: 13/10/2026 · Maintainer: Adnan Yusuf (<https://github.com/adyusuf>)

The `adyusuf` plugin is a set of working rules, skills, commands, role agents, hooks and scripts for Claude
Code. It has **no service of its own**: nothing it contains runs on a server the maintainer operates, and the
maintainer receives no data from it. The full inventory is in
[README › What this does to your machine](README.md#what-this-does-to-your-machine).

## What it reads

All reading happens on your own machine. Nothing read is sent anywhere by the plugin.

- **The hooks** read this plugin's `CLAUDE.md`, your `~/.claude` folder (links and `settings.json`, to warn
  about an old install), the command Claude is about to run (to refuse destructive ones) and a `CLAUDE.md` you
  edit (to check its size).
- **`scripts/step-stats.py`** reads Claude Code's local session transcripts (`~/.claude/projects`), and only
  when you run it. Transcripts can contain personal data.

## What it stores

- `step-stats.py` writes only aggregate counts (steps, tokens) to `docs/measurement-log.md`. A sanitiser
  removes project names and paths, and the script refuses to write when one survives.
- `install.py` writes logs and backups under `~/.claude-standards/` on your machine.
- Nothing is retained anywhere else.

## What it sends

The plugin itself sends nothing. Data leaves your machine only through steps **you** start:

- **claude-monitor's agent (optional).** `install.py` installs it, and it stays disabled until you connect it
  to a claude-monitor server (you approve the connection on the web). Once connected, the agent sends that
  server your sessions' activity (sessions, subagents, Claude Code's task tools). While it is connected,
  `/adyusuf:board-plan` also sends one line per task status change through the agent's `monitor_note` tool.
  The agent and the server are separate software; their data handling is described in the claude-monitor
  repository (<https://github.com/adyusuf/claude-monitor>).
- **The gate**, which you run in your own project, can do three things that reach the network:
  - install your dependencies and fetch security advisories from your package registries;
  - call a test-deploy URL that you set (`TEST_VERSION_URL`);
  - ask GitHub through `gh api` whether a repository is private (`require-private-remote.sh`, a hook you
    install yourself).

## Your choices

Disable or uninstall the plugin with `/plugin`. Leave the monitor agent uninstalled (`install.py --no-monitor`),
or disconnect it with `cm-agent logout`.

## Contact

Questions about this policy: open an issue at <https://github.com/adyusuf/claude-code-standards/issues>.
