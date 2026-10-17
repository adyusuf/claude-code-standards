"""scripts/adyusuf_config.py: the defaults that replace the questions (global rule #34), and how they are changed.

What is pinned: the shipped defaults are exactly the maintainer's list; a project value beats a user value beats a
default; an invalid value or an unknown key writes NOTHING; an unreadable file is reported and never fails a session
(the SessionStart hook runs `context`) and is never overwritten; and the agent listing follows the mode and moves
only the Opus agents to the override.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ROOT = os.path.dirname(SCRIPTS)
_spec = importlib.util.spec_from_file_location('adyusuf_config', os.path.join(SCRIPTS, 'adyusuf_config.py'))
cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfg)

# The maintainer's list of 17/10/2026, key by key.
EXPECTED = {
    'mode': 'C', 'mode_model': 'sonnet', 'monitor.connect': True, 'monitor.message_format': 'short',
    'write.unit_tests': True, 'write.e2e': True,
    'merge.dev': True, 'merge.test': True, 'merge.prod': True,
    'push.dev': True, 'push.test': True, 'push.prod': True,
    'run_before_push.dev.unit': False, 'run_before_push.dev.e2e': False,
    'run_before_push.test.unit': True, 'run_before_push.test.e2e': False,
    'run_before_push.prod.unit': True, 'run_before_push.prod.e2e': False,
}


# Every agent starts as 'follow the mode, run on the default model' (17/10/2026: the agent box is editable).
for _role in cfg.D_ROLES:
    EXPECTED['agents.%s.enabled' % _role] = 'auto'
    EXPECTED['agents.%s.model' % _role] = 'default'


class Shipped(unittest.TestCase):
    def test_the_defaults_are_the_maintainers_list(self):
        values, problem = cfg.read_layer(cfg.DEFAULTS_FILE)
        self.assertIsNone(problem)
        self.assertEqual(EXPECTED, values)

    def test_every_setting_has_a_default_and_every_default_a_setting(self):
        values, _ = cfg.read_layer(cfg.DEFAULTS_FILE)
        self.assertEqual(sorted(cfg.SPECS), sorted(values))

    def test_every_setting_is_a_checkbox_or_a_dropdown_with_a_label(self):
        for spec in cfg.SCHEMA:
            self.assertIn(spec['type'], ('bool', 'enum'), spec)
            self.assertTrue(spec['label'] and spec['group'], spec)
            if spec['type'] == 'enum':
                self.assertGreater(len(spec['options']), 1, spec)


class Tool(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.repo = os.path.join(self.home, 'repo')
        os.makedirs(self.repo)
        subprocess.run(['git', 'init', '-q', self.repo], check=True)
        self.user = os.path.join(self.home, 'user.json')
        self.project = os.path.join(self.repo, '.claude', 'adyusuf.json')

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def run_tool(self, *args, stdin=None):
        env = dict(os.environ, ADYUSUF_CONFIG_USER=self.user)
        result = subprocess.run(['python3', os.path.join(SCRIPTS, 'adyusuf_config.py'), *args], cwd=self.repo,
                                capture_output=True, text=True, env=env, input=stdin)
        return result.stdout, result.stderr, result.returncode

    def values(self):
        out, _, code = self.run_tool('show', '--json')
        self.assertEqual(0, code)
        return json.loads(out)


class Layers(Tool):
    def test_with_no_files_the_defaults_apply(self):
        data = self.values()
        self.assertEqual(EXPECTED, data['values'])
        self.assertEqual({'default'}, set(data['sources'].values()))

    def test_user_beats_default_and_project_beats_user(self):
        self.run_tool('set', 'push.prod', 'no')
        self.assertEqual((False, 'user'), (self.values()['values']['push.prod'], self.values()['sources']['push.prod']))
        self.run_tool('set', 'push.prod', 'yes', '--project')
        data = self.values()
        self.assertEqual((True, 'project'), (data['values']['push.prod'], data['sources']['push.prod']))
        self.run_tool('unset', 'push.prod', '--project')
        self.assertFalse(self.values()['values']['push.prod'])
        self.run_tool('unset', 'push.prod')
        self.assertTrue(self.values()['values']['push.prod'])

    def test_a_set_writes_nested_json_and_keeps_the_other_keys(self):
        self.run_tool('set', 'run_before_push.dev.unit', 'yes')
        self.run_tool('set', 'mode', 'e')
        with open(self.user, encoding='utf-8') as handle:
            self.assertEqual({'run_before_push': {'dev': {'unit': True}}, 'mode': 'E'}, json.load(handle))

    def test_get_prints_the_effective_value(self):
        self.assertEqual('C\n', self.run_tool('get', 'mode')[0])
        self.assertEqual('no\n', self.run_tool('get', 'run_before_push.dev.unit')[0])


class Validation(Tool):
    def test_an_invalid_value_or_unknown_key_is_exit_2_and_writes_nothing(self):
        for args in (('set', 'mode', 'Z'), ('set', 'push.prod', 'maybe'), ('set', 'mode_model', 'gpt'),
                     ('set', 'no.such.key', 'yes'), ('unset', 'no.such.key'), ('get', 'no.such.key'), ('bogus',), ()):
            _, err, code = self.run_tool(*args)
            self.assertEqual(2, code, '%s: %s' % (args, err))
        self.assertFalse(os.path.exists(self.user))

    def test_apply_is_all_or_nothing(self):
        _, err, code = self.run_tool('apply', '-', stdin=json.dumps({'push.prod': False, 'mode': 'Z'}))
        self.assertEqual(2, code, err)
        self.assertFalse(os.path.exists(self.user))
        out, _, code = self.run_tool('apply', '-', stdin=json.dumps({'push.prod': False, 'run_before_push': {'dev': {'unit': True}}}))
        self.assertEqual(0, code, out)
        data = self.values()['values']
        self.assertEqual((False, True), (data['push.prod'], data['run_before_push.dev.unit']))

    def test_apply_rejects_json_that_is_not_an_object(self):
        for text in ('not json', '[1, 2]'):
            self.assertEqual(2, self.run_tool('apply', '-', stdin=text)[2], text)

    def test_project_flag_is_refused_on_read_commands(self):
        self.assertEqual(2, self.run_tool('show', '--project')[2])


class Unreadable(Tool):
    def test_a_corrupt_file_is_reported_ignored_and_never_fails_the_hook(self):
        with open(self.user, 'w', encoding='utf-8') as handle:
            handle.write('{ broken')
        out, _, code = self.run_tool('context')
        self.assertEqual(0, code)
        self.assertIn('user.json', out)                       # reported, with the file named
        self.assertIn('mode C', out)                          # and the layer below still applies

    def test_an_invalid_value_inside_a_file_is_reported_and_the_layer_is_ignored(self):
        with open(self.user, 'w', encoding='utf-8') as handle:
            json.dump({'mode': 'Z', 'push': {'prod': False}}, handle)
        data = self.values()
        self.assertEqual('C', data['values']['mode'])
        self.assertTrue(data['values']['push.prod'])          # the whole layer is dropped, not half-applied
        self.assertTrue(data['problems'])

    def test_set_refuses_to_overwrite_an_unreadable_file(self):
        with open(self.user, 'w', encoding='utf-8') as handle:
            handle.write('{ broken')
        _, err, code = self.run_tool('set', 'mode', 'B')
        self.assertEqual(1, code, err)
        with open(self.user, encoding='utf-8') as handle:
            self.assertEqual('{ broken', handle.read())


class Agents(Tool):
    def test_mode_c_lists_nine_agents_and_only_opus_moves_to_the_override(self):
        rows = {r['role']: r for r in json.loads(self.run_tool('agents', '--json')[0])}
        self.assertEqual(9, len(rows))
        self.assertEqual('sonnet', rows['qa']['runs_on'])               # defined opus -> override
        self.assertEqual('haiku', rows['doc-writer']['runs_on'])        # defined haiku stays
        self.assertEqual('sonnet', rows['analyst']['runs_on'])

    def test_keep_leaves_every_agent_on_its_defined_model(self):
        self.run_tool('set', 'mode_model', 'keep')
        rows = {r['role']: r for r in json.loads(self.run_tool('agents', '--json')[0])}
        self.assertEqual('opus', rows['qa']['runs_on'])

    def test_mode_a_runs_no_agents_and_the_wider_modes_run_more(self):
        counts = {}
        for mode in 'ABCDE':
            self.run_tool('set', 'mode', mode)
            counts[mode] = len(json.loads(self.run_tool('agents', '--json')[0]))
        self.assertEqual({'A': 0, 'B': 3, 'C': 9, 'D': 14, 'E': 14}, counts)

    def test_one_agent_can_be_switched_off_and_another_on_beyond_the_mode(self):
        self.run_tool('set', 'agents.qa.enabled', 'off')
        self.run_tool('set', 'agents.security.enabled', 'on')               # security is outside mode C's set
        rows = {r['role']: r for r in json.loads(self.run_tool('agents', '--json')[0])}
        self.assertNotIn('qa', rows)
        self.assertEqual('sonnet', rows['security']['runs_on'])             # defined opus -> the mode's override
        self.assertEqual(9, len(rows))                                       # nine - qa + security

    def test_a_models_set_for_one_agent_beats_the_modes_override(self):
        self.run_tool('set', 'agents.developer.model', 'haiku')
        self.run_tool('set', 'agents.qa.model', 'opus')                      # explicitly back on opus although the mode says sonnet
        rows = {r['role']: r for r in json.loads(self.run_tool('agents', '--json')[0])}
        self.assertEqual('haiku', rows['developer']['runs_on'])
        self.assertEqual('opus', rows['qa']['runs_on'])
        self.assertEqual('sonnet', rows['architect']['runs_on'])             # untouched agents still follow the mode

    def test_mode_a_runs_no_agent_whatever_the_agent_settings_say(self):
        self.run_tool('set', 'mode', 'A')
        self.run_tool('set', 'agents.qa.enabled', 'on')
        self.assertEqual([], json.loads(self.run_tool('agents', '--json')[0]))

    def test_all_lists_the_inactive_agents_with_the_reason_they_are_off(self):
        self.run_tool('set', 'agents.qa.enabled', 'off')
        rows = {r['role']: r for r in json.loads(self.run_tool('agents', '--json', '--all')[0])}
        self.assertEqual(14, len(rows))
        self.assertEqual((False, True, 'off'), (rows['qa']['active'], rows['qa']['in_mode'], rows['qa']['enabled']))
        self.assertEqual((False, False), (rows['security']['active'], rows['security']['in_mode']))

    def test_reset_agents_removes_every_agent_setting_and_nothing_else(self):
        self.run_tool('set', 'agents.qa.enabled', 'off')
        self.run_tool('set', 'agents.developer.model', 'haiku')
        self.run_tool('set', 'push.prod', 'no')
        out, err, code = self.run_tool('reset-agents')
        self.assertEqual(0, code, err)
        data = self.values()
        self.assertEqual('auto', data['values']['agents.qa.enabled'])
        self.assertEqual('default', data['values']['agents.developer.model'])
        self.assertFalse(data['values']['push.prod'])

    def test_the_context_names_the_agents_and_the_models(self):
        out = self.run_tool('context')[0]
        self.assertIn('agents: product-manager (sonnet)', out)
        self.assertIn('qa (sonnet)', out)
        self.assertIn('doc-writer (haiku)', out)

    def test_panel_data_carries_everything_the_panel_draws(self):
        data = json.loads(self.run_tool('panel-data')[0])
        self.assertEqual(sorted(EXPECTED), sorted(data['values']))
        self.assertEqual(14, len(data['roles']))
        self.assertEqual(14, len(data['agents']))                           # every role, active or not, with its settings
        self.assertEqual({'name': 'qa', 'defined': 'opus', 'modes': ['C', 'D', 'E']}, [r for r in data['roles'] if r['name'] == 'qa'][0])


class Panel(Tool):
    def page(self):
        out, err, code = self.run_tool('panel')
        self.assertEqual(0, code, err)
        return out

    def embedded(self, page):
        import re
        literal = re.search(r'var DATA = (\{.*?\});\n  var TARGETS', page, re.S).group(1)
        return json.loads(literal)

    def test_the_page_embeds_the_data_it_draws_from(self):
        data = self.embedded(self.page())
        self.assertEqual(EXPECTED, data['defaults'])
        self.assertEqual(EXPECTED, data['values'])
        self.assertEqual(sorted(EXPECTED), sorted(spec['key'] for spec in data['schema']))
        self.assertEqual(14, len(data['roles']))

    def test_the_page_follows_the_effective_values_not_only_the_defaults(self):
        self.run_tool('set', 'push.prod', 'no')
        data = self.embedded(self.page())
        self.assertFalse(data['values']['push.prod'])
        self.assertTrue(data['defaults']['push.prod'])          # the reset button still returns to the shipped value

    def test_nothing_in_the_data_can_close_the_script_early(self):
        self.run_tool('set', 'mode', 'B')
        page = self.page()
        body = page.split('<script>', 1)[1]
        self.assertEqual(1, body.count('</script>'))
        self.assertNotIn('__PANEL_DATA__', page)

    def test_every_setting_is_reachable_from_the_page(self):
        page = self.page()
        for key in EXPECTED:
            self.assertIn('"%s"' % key, page, key)


class Notify(Tool):
    """The hook that tells a running session a setting changed: the next task sees it, the current one is not split."""

    def setUp(self):
        super().setUp()
        self.seen = os.path.join(self.home, 'seen')

    def hook(self, session='sess-1', event='UserPromptSubmit'):
        env = dict(os.environ, ADYUSUF_CONFIG_USER=self.user, ADYUSUF_SEEN_DIR=self.seen)
        result = subprocess.run(['python3', os.path.join(SCRIPTS, 'adyusuf_config.py'), 'notify', event], cwd=self.repo,
                                capture_output=True, text=True, env=env, input=json.dumps({'session_id': session}))
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput'] if result.stdout.strip() else None

    def test_the_first_call_of_a_session_says_nothing_it_only_remembers(self):
        self.assertIsNone(self.hook())

    def test_an_unchanged_configuration_stays_silent(self):
        self.hook()
        self.assertIsNone(self.hook())
        self.assertIsNone(self.hook(event='PostToolUse'))

    def test_a_change_is_announced_once_with_what_changed_and_when_it_applies(self):
        self.hook()
        self.run_tool('set', 'push.prod', 'no')
        self.run_tool('set', 'agents.qa.model', 'haiku')
        note = self.hook(event='PostToolUse')
        self.assertEqual('PostToolUse', note['hookEventName'])
        text = note['additionalContext']
        self.assertIn('push.prod: yes -> no', text)
        self.assertIn('agents.qa.model: default -> haiku', text)
        self.assertIn('NEXT task', text)                       # applies from the next task...
        self.assertIn('do not restart or split', text)         # ...and never splits the one running
        self.assertIn('qa (haiku)', text)                      # the new effective picture is attached
        self.assertIsNone(self.hook(event='PostToolUse'))      # once

    def test_each_session_is_told_separately(self):
        self.hook('a')
        self.hook('b')
        self.run_tool('set', 'mode', 'D')
        self.assertIsNotNone(self.hook('a'))
        self.assertIsNotNone(self.hook('b'))
        self.assertIsNone(self.hook('a'))

    def test_a_project_layer_change_is_noticed_too(self):
        self.hook()
        self.run_tool('set', 'mode', 'B', '--project')
        self.assertIn('mode: C -> B', self.hook()['additionalContext'])

    def test_a_broken_payload_or_file_never_fails_the_hook(self):
        env = dict(os.environ, ADYUSUF_CONFIG_USER=self.user, ADYUSUF_SEEN_DIR=self.seen)
        for payload in ('', 'not json', '{"session_id": "../../etc"}'):
            result = subprocess.run(['python3', os.path.join(SCRIPTS, 'adyusuf_config.py'), 'notify', 'UserPromptSubmit'],
                                    cwd=self.repo, capture_output=True, text=True, env=env, input=payload)
            self.assertEqual((0, ''), (result.returncode, result.stdout), payload)
        with open(self.user, 'w', encoding='utf-8') as handle:
            handle.write('{ broken')
        self.assertEqual(0, subprocess.run(['python3', os.path.join(SCRIPTS, 'adyusuf_config.py'), 'notify', 'PostToolUse'],
                                           cwd=self.repo, capture_output=True, text=True, env=env,
                                           input=json.dumps({'session_id': 's'})).returncode)


class RoleSetsMatchTheRepository(unittest.TestCase):
    """The role sets are written in the script; the agent files and the mode documents are the source."""

    def test_every_role_has_an_agent_file_with_a_model(self):
        for role in cfg.D_ROLES:
            self.assertIn(cfg.defined_model(role), ('opus', 'sonnet', 'haiku'), role)

    def test_there_is_no_agent_file_the_modes_do_not_know(self):
        files = {name[:-3] for name in os.listdir(cfg.AGENTS_DIR) if name.endswith('.md')}
        self.assertEqual(files, set(cfg.D_ROLES))

    def test_each_mode_document_names_exactly_its_roles(self):
        for mode, document, start in (('B', 'B-selective.md', None), ('C', 'C-full-team.md', '## The agent set')):
            with open(os.path.join(ROOT, 'modes', document), encoding='utf-8') as handle:
                text = handle.read()
            section = text.split('\n## Rules', 1)[0] if start is None else text.split(start, 1)[1].split('\n## ', 1)[0]
            for role in cfg.D_ROLES:
                if role in cfg.MODE_ROLES[mode]:
                    self.assertIn('`%s`' % role, section, '%s missing from mode %s' % (role, mode))
                else:
                    self.assertNotIn('`%s`' % role, section, '%s should not be in mode %s' % (role, mode))


if __name__ == '__main__':
    unittest.main()
