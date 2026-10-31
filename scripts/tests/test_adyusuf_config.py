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
    'mode': 'C', 'mode_model': 'sonnet', 'pod.connect': False, 'pod.message_format': 'short',
    'write.unit_tests': True, 'write.e2e': True,
    'merge.dev': True, 'merge.test': True, 'merge.prod': True,
    'push.dev': True, 'push.test': True, 'push.prod': True,
    'gates_before_push.dev': False, 'gates_before_push.test': True, 'gates_before_push.prod': True,
    'coverage_before_push.dev': False, 'coverage_before_push.test': True, 'coverage_before_push.prod': True,
    'ci_after_push.dev': False, 'ci_after_push.test': True, 'ci_after_push.prod': True,
    'ci.runner': 'hosted', 'deploy_after_push.test': True, 'deploy_after_push.prod': False,
    'e2e_before_deploy.test': False, 'e2e_before_deploy.prod': False,
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


class NoPanel(unittest.TestCase):
    """The settings page (an Artifact built from panel.template.html) was removed 22/10/2026."""

    def test_the_template_and_the_commands_are_gone(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, 'skills', 'config', 'panel.template.html')))
        for command in ('panel', 'panel-data'):
            result = subprocess.run(['python3', os.path.join(SCRIPTS, 'adyusuf_config.py'), command],
                                    capture_output=True, text=True)
            self.assertEqual(2, result.returncode, command)
            self.assertEqual('', result.stdout)


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
        env = dict(os.environ, ADYUSUF_CONFIG_USER=self.user, ADYUSUF_SESSION_DIR=os.path.join(self.home, 'sessions'))
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

    def test_show_user_leaves_out_the_project_and_session_layers(self):
        self.run_tool('set', 'push.prod', 'no')
        self.run_tool('set', 'push.test', 'no', '--project')
        self.run_tool('set', 'mode', 'B', '--session', 'abc-1')
        out, _, code = self.run_tool('show', '--json', '--user')
        data = json.loads(out)
        self.assertEqual(0, code)
        self.assertEqual((False, 'user'), (data['values']['push.prod'], data['sources']['push.prod']))
        self.assertEqual((True, 'default'), (data['values']['push.test'], data['sources']['push.test']))
        self.assertEqual((EXPECTED['mode'], 'default'), (data['values']['mode'], data['sources']['mode']))

    def test_user_only_applies_to_show_without_a_session(self):
        for args in (('set', 'mode', 'B', '--user'), ('get', 'mode', '--user'), ('show', '--user', '--session', 'abc-1')):
            self.assertEqual(2, self.run_tool(*args)[2], args)

    def test_a_set_writes_nested_json_and_keeps_the_other_keys(self):
        self.run_tool('set', 'gates_before_push.dev', 'yes')
        self.run_tool('set', 'mode', 'e')
        with open(self.user, encoding='utf-8') as handle:
            self.assertEqual({'gates_before_push': {'dev': True}, 'mode': 'E'}, json.load(handle))

    def test_get_prints_the_effective_value(self):
        self.assertEqual('C\n', self.run_tool('get', 'mode')[0])
        self.assertEqual('no\n', self.run_tool('get', 'gates_before_push.dev')[0])


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
        out, _, code = self.run_tool('apply', '-', stdin=json.dumps({'push.prod': False, 'gates_before_push': {'dev': True}}))
        self.assertEqual(0, code, out)
        data = self.values()['values']
        self.assertEqual((False, True), (data['push.prod'], data['gates_before_push.dev']))

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


class ConcurrentWrites(Tool):
    """Clicks in the rail boxes arrive in quick succession; found by QA: 37 of 40 two-way races lost a change."""

    def test_many_simultaneous_sets_all_land_and_leave_no_temp_file(self):
        keys = ['push.dev', 'push.test', 'push.prod', 'merge.dev', 'merge.test', 'merge.prod', 'write.e2e', 'write.unit_tests']
        env = dict(os.environ, ADYUSUF_CONFIG_USER=self.user)
        tool = os.path.join(SCRIPTS, 'adyusuf_config.py')
        for round_ in range(5):
            if os.path.exists(self.user):
                os.remove(self.user)
            procs = [subprocess.Popen(['python3', tool, 'set', key, 'no'], cwd=self.repo, env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for key in keys]
            results = []
            for proc in procs:
                _, err = proc.communicate()
                results.append((proc.returncode, err))
            self.assertEqual([(0, '')] * len(keys), results, 'round %d' % round_)
            with open(self.user, encoding='utf-8') as handle:
                written = cfg.flatten(json.load(handle))
            self.assertEqual({key: False for key in keys}, written, 'round %d lost a change' % round_)
        self.assertEqual([], [name for name in os.listdir(self.home) if name.endswith('.tmp')])

    def test_the_file_is_replaced_not_truncated_in_place(self):
        self.run_tool('set', 'mode', 'B')
        before = os.stat(self.user).st_ino
        self.run_tool('set', 'mode', 'D')
        self.assertNotEqual(before, os.stat(self.user).st_ino)       # a new file took its place (os.replace)


class RetiredKeys(Tool):
    """A file written before a setting was retired still holds it: that key is skipped, the rest of the layer applies."""

    def test_a_file_with_the_retired_monitor_keys_still_applies_its_other_settings(self):
        with open(self.user, 'w', encoding='utf-8') as handle:
            json.dump({'mode': 'B', 'monitor': {'connect': False, 'message_format': 'full'}, 'push': {'prod': False}}, handle)
        data = self.values()
        self.assertEqual([], data['problems'])
        self.assertEqual('B', data['values']['mode'])
        self.assertFalse(data['values']['push.prod'])
        self.assertNotIn('monitor.connect', data['values'])

    def test_a_file_with_the_retired_run_before_push_keys_still_applies_its_other_settings(self):
        with open(self.user, 'w', encoding='utf-8') as handle:
            json.dump({'run_before_push': {'dev': {'unit': True, 'e2e': True}, 'prod': {'e2e': False}}, 'gates_before_push': {'dev': True},
                       'mode': 'B'}, handle)
        data = self.values()
        self.assertEqual([], data['problems'])
        self.assertTrue(data['values']['gates_before_push.dev'])
        self.assertEqual('B', data['values']['mode'])
        self.assertNotIn('run_before_push.dev.e2e', data['values'])
        self.assertNotIn('run_before_push.dev.unit', data['values'])

    def test_a_key_from_a_newer_plugin_does_not_throw_away_the_layer(self):
        # Found by QA 30/10/2026: a user file holding a key this copy did not know was read as EMPTY, so push.prod
        # = no came back as the default yes, with no warning. The unknown key is left out; the rest applies.
        with open(self.user, 'w', encoding='utf-8') as handle:
            json.dump({'push': {'prod': False}, 'from_a_newer_plugin': {'dev': True}}, handle)
        data = self.values()
        self.assertEqual([], data['problems'])
        self.assertFalse(data['values']['push.prod'])
        self.assertNotIn('from_a_newer_plugin.dev', data['values'])
        self.assertEqual('no\n', self.run_tool('get', 'push.prod')[0])

    def test_a_write_keeps_the_key_a_newer_plugin_wrote(self):
        with open(self.user, 'w', encoding='utf-8') as handle:
            json.dump({'from_a_newer_plugin': {'dev': True}}, handle)
        _, _, code = self.run_tool('set', 'push.prod', 'no')
        self.assertEqual(0, code)
        with open(self.user, encoding='utf-8') as handle:
            self.assertEqual({'from_a_newer_plugin': {'dev': True}, 'push': {'prod': False}}, json.load(handle))

    def test_the_deploy_settings_are_checkboxes_and_the_runner_a_radio_choice_with_defaults(self):
        # 30/10/2026: "After pushing update: [x]test [ ]prod" (was a radio on 29/10) and where the shared SDLC workflow runs.
        self.assertEqual(['ci.runner'], [k for k, s in cfg.SPECS.items() if s['type'] == 'enum' and k.startswith('ci.')])
        self.assertEqual(['hosted', 'self-hosted'], cfg.SPECS['ci.runner']['options'])
        self.assertNotIn('deploy_after_push', cfg.SPECS)
        for env in ('test', 'prod'):
            self.assertEqual('bool', cfg.SPECS['deploy_after_push.' + env]['type'])
            self.assertEqual('Deploy after push', cfg.SPECS['deploy_after_push.' + env]['group'])
        values = self.values()['values']
        self.assertIs(values['deploy_after_push.test'], True)
        self.assertIs(values['deploy_after_push.prod'], False)

    def test_the_old_single_choice_deploy_key_is_retired_and_skipped(self):
        self.assertIn('deploy_after_push', cfg.RETIRED_KEYS)
        with open(self.user, 'w', encoding='utf-8') as handle:
            json.dump({'deploy_after_push': 'prod', 'mode': 'B'}, handle)
        data = self.values()
        self.assertEqual([], data['problems'])
        self.assertEqual('B', data['values']['mode'])
        self.assertIs(data['values']['deploy_after_push.prod'], False)

    def test_ci_after_push_exists_for_every_target_and_e2e_before_deploy_for_test_and_prod(self):
        for target in ('dev', 'test', 'prod'):
            self.assertIn('ci_after_push.%s' % target, cfg.SPECS)
        self.assertEqual(sorted(k for k in cfg.SPECS if k.startswith('e2e_before_deploy.')),
                         ['e2e_before_deploy.prod', 'e2e_before_deploy.test'])
        self.assertEqual(cfg.SPECS['e2e_before_deploy.test']['label'], 'Run e2e on dev before deploying test')
        self.assertEqual(cfg.SPECS['e2e_before_deploy.prod']['label'], 'Run e2e on test before deploying prod')
        self.assertEqual(cfg.SPECS['ci_after_push.test']['group'], 'CI after push')
        self.assertEqual(cfg.SPECS['e2e_before_deploy.prod']['group'], 'E2E before deploy')

    def test_the_context_names_the_new_settings(self):
        out, _, code = self.run_tool('context')
        self.assertEqual(0, code)
        self.assertIn('prod: merge yes, gates before push yes, coverage before push yes, push yes, CI after push yes', out)
        self.assertIn('dev: merge yes, gates before push no, coverage before push no, push yes, CI after push no', out)
        self.assertIn('e2e before deploy: on dev before deploying test no, on test before deploying prod no', out)

    def test_the_old_ci_before_merge_and_e2e_after_deploy_keys_are_retired_and_skipped(self):
        for group in ('ci_before_merge', 'e2e_after_deploy'):
            for target in ('dev', 'test', 'prod'):
                key = '%s.%s' % (group, target)
                self.assertIn(key, cfg.RETIRED_KEYS)
                self.assertNotIn(key, cfg.SPECS)
        with open(self.user, 'w', encoding='utf-8') as handle:
            json.dump({'ci_before_merge': {'prod': False}, 'e2e_after_deploy': {'prod': False}, 'ci_after_push': {'test': False}}, handle)
        data = self.values()
        self.assertIs(data['values']['ci_after_push.test'], False)
        self.assertNotIn('ci_before_merge.prod', data['values'])
        self.assertNotIn('e2e_after_deploy.prod', data['values'])

    def test_the_retired_keys_are_not_settings_any_more(self):
        for key in cfg.RETIRED_KEYS:
            self.assertNotIn(key, cfg.SPECS)
            _, err, code = self.run_tool('set', key, 'yes')
            self.assertEqual(2, code, err)

    def test_apply_of_a_file_saved_before_the_retirement_writes_the_rest_and_says_what_it_skipped(self):
        payload = json.dumps({'mode': 'B', 'monitor.connect': True, 'monitor.message_format': 'short', 'push.prod': False})
        out, err, code = self.run_tool('apply', '-', stdin=payload)
        self.assertEqual(0, code, err)
        self.assertIn('2 setting(s) written', out)
        self.assertIn('skipped (retired', out)
        data = self.values()
        self.assertEqual('B', data['values']['mode'])
        self.assertFalse(data['values']['push.prod'])
        with open(self.user, encoding='utf-8') as handle:
            self.assertNotIn('monitor', json.load(handle))

    def test_apply_still_refuses_a_key_that_never_existed(self):
        _, err, code = self.run_tool('apply', '-', stdin=json.dumps({'mode': 'B', 'monitor.nonsense': 1}))
        self.assertEqual(2, code, err)
        self.assertFalse(os.path.exists(self.user))

    def test_the_session_start_block_does_not_mention_the_monitor_and_names_the_pod_settings(self):
        out, _, code = self.run_tool('context')
        self.assertEqual(0, code)
        self.assertNotIn('monitor', out.lower())
        self.assertIn('pod: connect no, message format short (stored only; nothing acts on it)', out)


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


class Notify(Tool):
    """The hook that tells a running session a setting changed: the next task sees it, the current one is not split."""

    def setUp(self):
        super().setUp()
        self.seen = os.path.join(self.home, 'seen')

    def hook(self, session='sess-1', event='UserPromptSubmit'):
        env = dict(os.environ, ADYUSUF_CONFIG_USER=self.user, ADYUSUF_SEEN_DIR=self.seen,
                   ADYUSUF_SESSION_DIR=os.path.join(self.home, 'sessions'))
        result = subprocess.run(['python3', os.path.join(SCRIPTS, 'adyusuf_config.py'), 'notify', event], cwd=self.repo,
                                capture_output=True, text=True, env=env, input=json.dumps({'session_id': session}))
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput'] if result.stdout.strip() else None

    def test_the_first_call_of_a_session_says_nothing_it_only_remembers(self):
        self.assertIsNone(self.hook())

    def test_a_seen_file_that_still_holds_a_retired_key_is_not_a_change(self):
        # A session that started before the retirement recorded the two monitor keys: that alone is not a change.
        self.hook()
        path = os.path.join(self.seen, 'sess-1')
        with open(path, encoding='utf-8') as handle:
            seen = json.load(handle)
        seen.update({'monitor.connect': True, 'monitor.message_format': 'short'})
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(seen, handle)
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

    def test_settings_a_session_never_saw_are_not_a_change(self):
        # Found by QA: after /plugin update a running session's seen-file lacks the new keys, so the first call listed all
        # of them as "None -> value" although the user changed nothing.
        self.hook()
        seen = os.path.join(self.seen, 'sess-1')
        with open(seen, encoding='utf-8') as handle:
            values = json.load(handle)
        for key in [k for k in values if k.startswith(('ci_after_push', 'e2e_before_deploy', 'pod.', 'gates_before_push'))]:
            del values[key]
        values['monitor.connect'] = True                                  # and a retired key the old script wrote
        with open(seen, 'w', encoding='utf-8') as handle:
            json.dump(values, handle)
        self.assertIsNone(self.hook())
        with open(seen, encoding='utf-8') as handle:
            self.assertIn('pod.connect', json.load(handle))               # remembered silently
        self.run_tool('set', 'push.prod', 'no')
        note = self.hook()
        self.assertIn('push.prod: yes -> no', note['additionalContext'])
        self.assertNotIn('pod.connect', note['additionalContext'].split('\n')[0])

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
