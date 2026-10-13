"""The rules loader's entry points (scripts/rules-context.py): main() in-process, the command line
as a hook runs it, and the tripwire that fails when CLAUDE.md outgrows the hooks hooks/hooks.json
registers. The pure functions are in test_rules_context.py."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules_context_helpers import (HOOKS, REAL_PARTS, REAL_TEXT, REPO, SCRIPT, SESSION_PARTS,  # noqa: E402
                                   SUBAGENT_PARTS, rc, run_cli, run_main)


class Main(unittest.TestCase):
    def test_session_prints_the_rendered_part_as_plain_text(self):
        code, out, _ = run_main(['session', '2', '4'])
        self.assertEqual(code, 0)
        self.assertEqual(out, rc.render(SESSION_PARTS, 2, 4))

    def test_subagent_prints_json_with_the_event_name_and_the_part_text(self):
        code, out, _ = run_main(['subagent', '2', '4'])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(list(payload), ['hookSpecificOutput'])
        self.assertEqual(payload['hookSpecificOutput']['hookEventName'], 'SubagentStart')
        self.assertEqual(payload['hookSpecificOutput']['additionalContext'], rc.render(SUBAGENT_PARTS, 2, 4))

    def test_unreadable_rules_exit_1_and_print_nothing_to_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run_main(['session', '1', '4'], rules_path=os.path.join(tmp, 'missing.md'))
        self.assertEqual(code, 1)
        self.assertEqual(out, '')
        self.assertIn('cannot read the global rules', err)

    def test_a_part_past_the_end_exits_0_and_prints_nothing(self):
        for mode in ('session', 'subagent'):
            code, out, _ = run_main([mode, '4', '4'], rules_path=self.two_part_rules())
            self.assertEqual((code, out), (0, ''), mode)

    def two_part_rules(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, 'CLAUDE.md')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('## A\n' + 'a' * 9000 + '\n## B\nb\n')
        return path


class Cli(unittest.TestCase):
    def test_session_1_prints_the_part_header(self):
        code, out, err = run_cli('session', '1', '4')
        self.assertEqual(code, 0, err)
        self.assertTrue(out.startswith(f'[Global working rules, part 1/{len(REAL_PARTS)} '), out[:80])
        self.assertIn(REAL_PARTS[0][:200], out)

    def test_subagent_2_prints_valid_json_with_the_part_two_text(self):
        code, out, err = run_cli('subagent', '2', '4')
        self.assertEqual(code, 0, err)
        context = json.loads(out)['hookSpecificOutput']
        self.assertEqual(context['hookEventName'], 'SubagentStart')
        self.assertEqual(context['additionalContext'], rc.render(SUBAGENT_PARTS, 2, 4))

    def test_a_part_past_the_end_prints_nothing_and_exits_0(self):
        code, out, err = run_cli('session', str(len(REAL_PARTS) + 1), str(len(REAL_PARTS) + 1))
        self.assertEqual((code, out), (0, ''), err)

    def test_bad_usage_exits_2_with_a_usage_line(self):
        cases = [('foo', '1', '4'), ('session', 'x', '4'), ('session', '1', 'x'),
                 ('session', '1'), ('session', '1', '4', 'extra'), ()]
        for args in cases:
            code, out, err = run_cli(*args)
            self.assertEqual(code, 2, args)
            self.assertEqual(out, '', args)
            self.assertIn('usage: rules-context.py', err, args)

    def test_a_part_outside_one_to_registered_exits_2(self):
        for args in (('session', '0', '4'), ('session', '5', '4'), ('subagent', '0', '4'), ('subagent', '5', '4')):
            code, out, err = run_cli(*args)
            self.assertEqual(code, 2, args)
            self.assertEqual(out, '', args)
            self.assertIn('outside 1..4', err, args)

    def test_a_copy_without_a_claude_md_next_to_it_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = os.path.join(tmp, 'scripts')
            os.makedirs(scripts)
            copy = os.path.join(scripts, 'rules-context.py')
            shutil.copy(SCRIPT, copy)
            code, out, err = run_cli('session', '1', '4', script=copy)
        self.assertEqual((code, out), (1, ''))
        self.assertIn('cannot read the global rules', err)


class Registration(unittest.TestCase):
    """The tripwire: when CLAUDE.md grows past what the registered hooks can print, a
    maintainer must register another hook (hooks/hooks.json) — this fails first."""
    MODES = {'SessionStart': 'session', 'SubagentStart': 'subagent'}

    @staticmethod
    def rules_commands(event):
        """The rules-context.py commands of an event; SessionStart also carries the legacy-install check."""
        with open(HOOKS, encoding='utf-8') as handle:
            groups = json.load(handle)['hooks'][event]
        return [h['command'] for group in groups for h in group['hooks'] if 'rules-context.py' in h['command']]

    def test_the_rules_need_no_more_parts_per_mode_than_hooks_register_per_event(self):
        for event, mode in self.MODES.items():
            registered = len(self.rules_commands(event))
            self.assertGreater(registered, 0, event)
            needed = len(rc.mode_parts(REAL_TEXT, mode, registered))
            self.assertLessEqual(needed, registered,
                                 f'CLAUDE.md needs {needed} {mode} parts but {event} registers {registered}: '
                                 'add a hook (and bump <registered> in every command) in hooks/hooks.json')

    def test_every_registered_command_prints_under_the_cap_and_together_they_are_claude_md(self):
        for event, mode in self.MODES.items():
            commands = self.rules_commands(event)
            texts = []
            for command in commands:
                part, registered = command.split('rules-context.py"')[1].split()[1:]
                code, out, err = run_cli(mode, part, registered)
                self.assertEqual(code, 0, err)
                self.assertLess(len(out), rc.HOOK_LIMIT, f'{event} part {part}: {len(out)} characters')
                if out:
                    text = out if mode == 'session' else json.loads(out)['hookSpecificOutput']['additionalContext']
                    self.assertNotIn('WARNING', text, f'{event} part {part}')
                    texts.append(text.split('\n', 1)[1])      # the body after the one header line
            self.assertEqual(''.join(texts), REAL_TEXT, event)


class HeaderRoot(unittest.TestCase):
    def test_the_header_the_hook_prints_names_this_checkout_as_the_root(self):
        code, out, err = run_cli('session', '1', '4')
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines()[0].rsplit('; ', 1)[1], f'relative paths start at {REPO}]')

    def test_a_copy_of_the_plugin_names_its_own_root_not_the_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'scripts'))
            copy = os.path.join(tmp, 'scripts', 'rules-context.py')
            shutil.copy(SCRIPT, copy)
            with open(os.path.join(tmp, 'CLAUDE.md'), 'w', encoding='utf-8') as handle:
                handle.write('## A\nthe copy rules\n')
            code, out, err = run_cli('session', '1', '4', script=copy)
            code_json, out_json, _ = run_cli('subagent', '1', '4', script=copy)
        self.assertEqual((code, code_json), (0, 0), err)
        self.assertTrue(out.splitlines()[0].endswith(f'relative paths start at {tmp}]'), out)
        self.assertNotIn(REPO, out)
        self.assertIn(f'relative paths start at {tmp}]', json.loads(out_json)['hookSpecificOutput']['additionalContext'])
        self.assertTrue(out.endswith('the copy rules\n'))


if __name__ == '__main__':
    unittest.main()
