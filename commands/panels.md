---
description: Open the adyusuf settings, agents and promotion boxes in the right-hand rail
---

Open the three right-hand rail boxes (*Settings*, *Agents*, *Promotion*) of this plugin.

The boxes are drawn by the plugin's mod (`${CLAUDE_PLUGIN_ROOT}/hooks/register.tsx`), which answers this command itself
when mods are loaded. If you are reading this text, the mod did not answer: this session does not load mods or draw
panes (for example a client that has not switched mods on).

1. Say in one sentence that the boxes cannot be shown in this session.
2. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/adyusuf_config.py" show` and print the result as a short table
   (setting, value).
3. Tell the user to change a setting with `/adyusuf:config`, which asks with clickable questions in the chat.

Change nothing yourself. Never build a page or an Artifact for this.
