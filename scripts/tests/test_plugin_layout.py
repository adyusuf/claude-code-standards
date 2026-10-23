"""The `adyusuf` plugin: the repository root IS the plugin (.claude-plugin/ + hooks/hooks.json) and
our skills and commands are invoked as /adyusuf:<name>. The layout invariants live here: no plugin/
directory, no symlink, the exact hook set, and every ${CLAUDE_PLUGIN_ROOT} path in a skill, command,
agent or hook resolves to a tracked file (a path that does not resolve is a broken install)."""
import json
import os
import re
import subprocess
import unittest

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
NAMESPACE = 'adyusuf'
DOC_SUFFIXES = ('.md', '.py', '.sh', '.js', '.json')
SELF = 'scripts/tests/test_plugin_layout.py'  # its fixtures are unprefixed on purpose
COMPONENT_DIRS = ('skills', 'commands', 'agents', 'hooks')
PLUGIN_PATH = re.compile(r'\$\{CLAUDE_PLUGIN_ROOT\}"?((?:/[A-Za-z0-9_.<>*-]+)*)')
OLD_HOME_PATH = re.compile(r'(?:~|\$HOME|\$\{HOME\})/\.claude/'
                           r'(?:CLAUDE\.md|standards|modes|agents|docs|scripts|skills/adyusuf)')
FRONTMATTER_NAME = re.compile(r'^name:\s*(\S+)\s*$', re.MULTILINE)
ROOT = '${CLAUDE_PLUGIN_ROOT}'
RULES_CTX = f'python3 "{ROOT}/scripts/rules-context.py"'


def tracked(stage=False):
    args = ['git', 'ls-files'] + (['-s'] if stage else [])
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, check=True).stdout.splitlines()


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding='utf-8') as handle:
        return handle.read()


def own_names():
    skills = [d for d in os.listdir(os.path.join(REPO, 'skills'))
              if os.path.isfile(os.path.join(REPO, 'skills', d, 'SKILL.md'))]
    commands = [f[:-3] for f in os.listdir(os.path.join(REPO, 'commands')) if f.endswith('.md')]
    return sorted(skills + commands)


def unprefixed(text, names):
    """Slash invocations of our names that lack the namespace (paths like skills/x are fine)."""
    pattern = re.compile(r'(^|[^A-Za-z0-9_./:-])/(' + '|'.join(map(re.escape, names)) + r')\b')
    return [m.group(2) for m in pattern.finditer(text)]


def plugin_paths(text):
    """The paths written after ${CLAUDE_PLUGIN_ROOT}, `<PLACEHOLDER>` read as a glob; the bare root is skipped."""
    found = [re.sub(r'<[^>]*>', '*', m.group(1)).rstrip('.').strip('/') for m in PLUGIN_PATH.finditer(text)]
    return [path for path in found if path]


def resolves(path, files):
    """True if `path` names a tracked file or directory; `*` stays inside one path segment."""
    parts = path.split('/')
    regex = re.compile('/'.join(re.escape(part).replace(r'\*', '[^/]*') for part in parts))
    return any(regex.fullmatch('/'.join(f.split('/')[:len(parts)])) for f in files if f.count('/') + 1 >= len(parts))


def normalised_hooks():
    """hooks.json as {event: [(matcher, [commands])]} — the whole registration, nothing implied."""
    events = json.loads(read('hooks', 'hooks.json'))['hooks']
    out = {}
    for event, groups in events.items():
        out[event] = [(group.get('matcher'), [(h['type'], h['command']) for h in group['hooks']]) for group in groups]
    return out


def commands_of(event):
    return [(matcher, [command for _, command in hooks]) for matcher, hooks in normalised_hooks()[event]]


class SkillTest(unittest.TestCase):
    def test_each_skill_is_named_after_its_folder(self):
        for name in os.listdir(os.path.join(REPO, 'skills')):
            path = os.path.join(REPO, 'skills', name, 'SKILL.md')
            if not os.path.isfile(path):
                continue
            with open(path, encoding='utf-8') as handle:
                front = handle.read().split('---')[1]
            self.assertIn(f'\nname: {name}\n', front, path)


class ReferenceTest(unittest.TestCase):
    def test_unprefixed_detects_and_ignores(self):
        names = ['working-mode']
        self.assertEqual(unprefixed('run `/working-mode B`', names), ['working-mode'])
        self.assertEqual(unprefixed('/working-mode', names), ['working-mode'])
        self.assertEqual(unprefixed('run `/adyusuf:working-mode B`', names), [])
        self.assertEqual(unprefixed('see skills/working-mode/SKILL.md', names), [])
        self.assertEqual(unprefixed('/working-modes', names), [])

    def test_every_invocation_in_the_repository_is_prefixed(self):
        names = own_names()
        self.assertGreaterEqual(len(names), 7)
        stale = {}
        for rel in tracked():
            path = os.path.join(REPO, rel)
            if rel == SELF or not rel.endswith(DOC_SUFFIXES) or os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, encoding='utf-8') as handle:
                found = unprefixed(handle.read(), names)
            if found:
                stale[rel] = found
        self.assertEqual(stale, {}, 'write /adyusuf:<name>')


class TreeShapeTest(unittest.TestCase):
    def test_there_is_no_plugin_directory_any_more(self):
        self.assertFalse(os.path.exists(os.path.join(REPO, 'plugin')))
        self.assertEqual([f for f in tracked() if f.startswith('plugin/')], [])

    def test_no_tracked_path_is_a_symlink(self):
        # Mode 120000 in the index: a symlink needs Developer Mode on Windows, and the plugin is COPIED to a cache.
        links = [line.split('\t', 1)[1] for line in tracked(stage=True) if line.startswith('120000 ')]
        self.assertEqual(links, [])


class RootPluginTest(unittest.TestCase):
    """The marketplace layout at the repository root: .claude-plugin/ manifest + marketplace, hooks/hooks.json."""
    def test_manifest_names_the_namespace_and_carries_no_version(self):
        manifest = json.loads(read('.claude-plugin', 'plugin.json'))
        self.assertEqual(manifest['name'], NAMESPACE)
        # No version on purpose: every commit on the installed branch is a new version.
        self.assertNotIn('version', manifest)

    def test_marketplace_lists_exactly_the_one_plugin_at_the_repository_root(self):
        # The right-hand rail boxes are NOT a second plugin (user decision 22/10/2026): they are the mod inside this one.
        marketplace = json.loads(read('.claude-plugin', 'marketplace.json'))
        self.assertEqual(marketplace['name'], 'adyusuf-marketplace')
        self.assertEqual([(p['name'], p['source']) for p in marketplace['plugins']], [(NAMESPACE, './')])

    def test_the_mod_is_listed_in_hooks_json_beside_the_command_hooks_and_its_files_exist(self):
        hooks = json.loads(read('hooks', 'hooks.json'))
        self.assertEqual(hooks['modules'], ['./register.tsx'])
        self.assertIn('SessionStart', hooks['hooks'])                    # the command hooks are still there
        for name in ('register.tsx', 'choose.ts', 'choose.test.ts', 'register.test.tsx'):
            self.assertTrue(os.path.isfile(os.path.join(REPO, 'hooks', name)), name)
        manifest = json.loads(read('.claude-plugin', 'plugin.json'))
        self.assertEqual(manifest['types'], './types/index.d.ts')
        self.assertTrue(os.path.isfile(os.path.join(REPO, 'types', 'index.d.ts')))
        self.assertIn("name: 'adyusuf:panels'", read('hooks', 'register.tsx'))

    def test_panels_command_exists_as_a_file_so_it_is_there_where_mods_do_not_load(self):
        # The mod registers /adyusuf:panels only where it runs; the file is the fallback everywhere else.
        self.assertIn('panels', own_names())
        self.assertIn('adyusuf_config.py', read('commands', 'panels.md'))

    def test_hook_events_are_exactly_the_six(self):
        self.assertEqual(sorted(normalised_hooks()),
                         ['PostToolUse', 'PreToolUse', 'SessionStart', 'Stop', 'SubagentStart', 'UserPromptSubmit'])

    def test_rules_parts_one_to_four_and_the_configuration_on_session_start_and_nothing_else(self):
        rules = [f'{RULES_CTX} session {n} 4' for n in range(1, 5)]
        rules.append(f'python3 "{ROOT}/scripts/adyusuf_config.py" context --stdin')    # the effective defaults (rule #34)
        self.assertEqual(commands_of('SessionStart'), [(None, rules)])

    def test_rules_parts_one_to_four_on_subagent_start(self):
        self.assertEqual(commands_of('SubagentStart'), [(None, [f'{RULES_CTX} subagent {n} 4' for n in range(1, 5)])])

    def test_the_guard_runs_before_a_bash_call_and_nothing_else_does(self):
        self.assertEqual(commands_of('PreToolUse'), [('Bash', [f'bash "{ROOT}/scripts/guard-destructive.sh"'])])

    def test_the_size_hook_runs_after_an_edit_or_write_and_at_stop(self):
        size_hook = [f'bash "{ROOT}/scripts/md-hook.sh"']
        notify = lambda event: [f'python3 "{ROOT}/scripts/adyusuf_config.py" notify {event}']  # noqa: E731
        # After a task boundary (an agent call, a shell command) and before each prompt, a changed setting is announced.
        self.assertEqual(commands_of('PostToolUse'), [('Edit|Write', size_hook), ('Agent|Bash', notify('PostToolUse'))])
        self.assertEqual(commands_of('UserPromptSubmit'), [(None, notify('UserPromptSubmit'))])
        self.assertEqual(commands_of('Stop'), [(None, size_hook)])

    def test_every_hook_is_a_command_hook(self):
        types = {kind for groups in normalised_hooks().values() for _, hooks in groups for kind, _ in hooks}
        self.assertEqual(types, {'command'})

    def test_every_script_a_hook_runs_exists_and_is_tracked(self):
        files = set(tracked())
        scripts = {path for groups in normalised_hooks().values() for _, hooks in groups
                   for _, command in hooks for path in plugin_paths(command)}
        self.assertEqual(sorted(scripts), ['scripts/adyusuf_config.py', 'scripts/guard-destructive.sh',
                                           'scripts/md-hook.sh', 'scripts/rules-context.py'])
        for script in scripts:
            self.assertIn(script, files)
            self.assertTrue(os.path.isfile(os.path.join(REPO, script)), script)


class PluginPathTest(unittest.TestCase):
    """Every ${CLAUDE_PLUGIN_ROOT}/<path> a skill, command, agent or hook mentions must exist in the copy."""
    FILES = ['modes/README.md', 'modes/A-skill.md', 'modes/archive/X-y.md', 'standards/templates/setup-md.md']

    def test_paths_are_read_after_the_variable_with_placeholders_as_globs(self):
        text = ('`${CLAUDE_PLUGIN_ROOT}/modes/<LETTER>-*.md` and `${CLAUDE_PLUGIN_ROOT}/standards/`. '
                'cp "${CLAUDE_PLUGIN_ROOT}"/scripts/md-*.sh x; the root ${CLAUDE_PLUGIN_ROOT} alone; '
                'see ${CLAUDE_PLUGIN_ROOT}/CLAUDE.md.')
        self.assertEqual(plugin_paths(text), ['modes/*-*.md', 'standards', 'scripts/md-*.sh', 'CLAUDE.md'])

    def test_a_missing_file_is_not_resolved_and_a_directory_is(self):
        self.assertTrue(resolves('modes/README.md', self.FILES))
        self.assertTrue(resolves('standards/templates', self.FILES))
        self.assertFalse(resolves('modes/README.mdx', self.FILES))
        self.assertFalse(resolves('standards/missing.md', self.FILES))

    def test_a_star_does_not_cross_a_directory(self):
        self.assertTrue(resolves('modes/A-*.md', self.FILES))
        self.assertFalse(resolves('modes/X-*.md', self.FILES))     # only modes/archive/X-y.md matches across '/'
        self.assertFalse(resolves('modes/*.md/x', self.FILES))

    def test_every_plugin_path_in_skills_commands_agents_and_hooks_resolves(self):
        files = tracked()
        seen = []
        for rel in files:
            if rel.split('/')[0] not in COMPONENT_DIRS:
                continue
            for path in plugin_paths(read(*rel.split('/'))):
                seen.append(path)
                self.assertTrue(resolves(path, files), f'{rel}: ${{CLAUDE_PLUGIN_ROOT}}/{path} is not in the plugin')
        self.assertGreaterEqual(len(seen), 25, 'the scan found suspiciously few references')

    def test_each_mode_letter_resolves_to_exactly_one_mode_file(self):
        for letter in 'ABCDE':
            matches = [f for f in tracked() if re.fullmatch(rf'modes/{letter}-[^/]*\.md', f)]
            self.assertEqual(len(matches), 1, f'{letter}: {matches}')

    def test_old_home_paths_are_gone_from_skill_command_and_agent_bodies(self):
        self.assertTrue(OLD_HOME_PATH.search('open ~/.claude/standards/x.md'))
        self.assertTrue(OLD_HOME_PATH.search('$HOME/.claude/skills/adyusuf/x'))
        self.assertIsNone(OLD_HOME_PATH.search('edit ~/.claude/settings.json'))
        stale = {}
        for rel in tracked():
            if rel.split('/')[0] in ('skills', 'commands', 'agents'):
                found = OLD_HOME_PATH.findall(read(*rel.split('/')))
                if found:
                    stale[rel] = found
        self.assertEqual(stale, {}, 'use ${CLAUDE_PLUGIN_ROOT}/<path>')


class AgentsTest(unittest.TestCase):
    def agent_files(self):
        return sorted(f for f in tracked() if re.fullmatch(r'agents/[^/]+\.md', f))

    def test_there_are_fourteen_agents(self):
        self.assertEqual(len(self.agent_files()), 14)

    def test_each_agent_is_named_after_its_file(self):
        for rel in self.agent_files():
            front = read(*rel.split('/')).split('---')[1]
            names = FRONTMATTER_NAME.findall(front)
            self.assertEqual(names, [os.path.basename(rel)[:-3]], rel)

    def test_every_role_the_modes_table_names_is_an_agent(self):
        stems = {os.path.basename(f)[:-3] for f in self.agent_files()}
        rows = [line for line in read('modes', 'README.md').splitlines() if re.match(r'\| `[a-z0-9-]+` \|', line)]
        roles = {re.match(r'\| `([a-z0-9-]+)`', line).group(1) for line in rows}
        self.assertEqual(roles, stems, 'the "Who audits whom" table and agents/ must name the same 14 roles')
        mode_b = next(line for line in read('modes', 'README.md').splitlines() if line.startswith('| [**B**]'))
        self.assertLessEqual(set(re.findall(r'`([a-z0-9-]+)`', mode_b)), stems)


if __name__ == '__main__':
    unittest.main()
