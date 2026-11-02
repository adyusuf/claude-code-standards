"""The Status box's steps (user decisions 02/11/2026): every task is split into steps first, each with its state, how much
of it is done and what blocks it; a subagent writes its own; a new request goes in among them; with `steps.enforce` on
`block`, a code edit or a commit waits for the steps.

Each test runs the scripts as commands with the status folder, the user's settings and the session layer in a temporary
directory, so no real file is read or written.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SCRIPTS, 'adyusuf_status.py')
SESSION = 'abc-123'


class Steps(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = dict(os.environ, ADYUSUF_STATUS_DIR=self.dir, ADYUSUF_CONFIG_USER=os.path.join(self.dir, 'u.json'),
                        ADYUSUF_SESSION_DIR=os.path.join(self.dir, 'sessions'))

    def run_tool(self, *args):
        done = subprocess.run([sys.executable, SCRIPT, '--session', SESSION, *args], env=self.env, capture_output=True, text=True)
        return done.stdout, done.stderr, done.returncode

    def run_hook(self, event, payload):
        done = subprocess.run([sys.executable, SCRIPT, 'hook', event], env=self.env, capture_output=True,
                              input=json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        return done.stdout.decode(), done.stderr.decode(), done.returncode

    def rows(self):
        return json.loads(self.run_tool('show', '--json')[0])['rows']

    def test_a_step_has_a_state_a_percentage_a_blocker_and_who_runs_it(self):
        self.run_tool('step', '1. plan', 'done', '100')
        self.run_tool('step', '2. build', 'running', '45%', '--blocker', 'qa review')
        self.run_tool('step', 'review', 'running', '150', '--agent', 'qa a9f3c2')
        self.run_tool('step', '3. ship', 'not started', 'soon')
        self.assertEqual([(r['item'], r['state'], r['percent'], r['blocker'], r['agent']) for r in self.rows()], [
            ('1. plan', 'done', '100', '', ''), ('2. build', 'running', '45', 'qa review', ''),
            ('review', 'running', '100', '', 'qa a9f3c2'), ('3. ship', 'not started', '', '', '')])

    def test_a_new_request_goes_in_after_the_step_named_and_a_step_is_replaced_in_place(self):
        for step in ('1. plan', '2. build', '3. ship'):
            self.run_tool('step', step, 'not started', '0')
        self.run_tool('step', '2a. new request', 'not started', '0', '--after', '2. build')
        self.run_tool('step', '2. build', 'done', '100')
        self.run_tool('step', '9. unknown anchor', 'not started', '0', '--after', 'nowhere')
        self.assertEqual([r['item'] for r in self.rows()], ['1. plan', '2. build', '2a. new request', '3. ship', '9. unknown anchor'])
        self.assertEqual('100', self.rows()[1]['percent'])

    def test_two_runners_may_name_a_step_alike_and_drop_takes_the_runners(self):
        self.run_tool('step', 'tests', 'running', '10')
        self.run_tool('step', 'tests', 'running', '60', '--agent', 'qa a9f3c2')
        self.assertEqual([(r['agent'], r['percent']) for r in self.rows()], [('', '10'), ('qa a9f3c2', '60')])
        self.run_tool('drop', 'tests', '--agent', 'qa a9f3c2')
        self.assertEqual([r['agent'] for r in self.rows()], [''])

    def test_show_prints_a_step_with_its_runner_and_an_older_row_as_before(self):
        self.run_tool('row', 'gate', 'running', '3/12 steps', 'promote.sh')
        self.run_tool('step', '1. plan', 'running', '40', '--blocker', 'approval')
        out = self.run_tool('show')[0]
        self.assertIn('gate | running | 3/12 steps | promote.sh', out)
        self.assertIn('session | 1. plan | running | 40% | approval', out)

    def test_each_user_message_reminds_claude_to_analyse_it_into_steps_first(self):
        out = json.loads(self.run_hook('prompt', {'session_id': SESSION, 'prompt': 'add tabs'})[0])['hookSpecificOutput']
        self.assertEqual('UserPromptSubmit', out['hookEventName'])
        for part in ('analyse it', 'write its steps into the Status box first', '--session abc-123 step', '--after', 'steps.enforce: block'):
            self.assertIn(part, out['additionalContext'])
        self.assertEqual('', self.run_hook('prompt', {'session_id': SESSION, 'prompt': 'x', 'source': 'system'})[0])

    def test_a_subagent_is_told_to_write_its_own_steps_under_its_name(self):
        out = json.loads(self.run_hook('subagent', {'session_id': SESSION, 'agent_type': 'qa', 'agent_id': 'a9f3c2d1e0'})[0])
        text = out['hookSpecificOutput']['additionalContext']
        self.assertEqual('SubagentStart', out['hookSpecificOutput']['hookEventName'])
        self.assertIn('you are "qa a9f3c2"', text)
        self.assertIn('--session abc-123 step "<n. step>" "not started" 0 --agent "qa a9f3c2"', text)

    def guard(self, tool, given):
        return self.run_hook('guard', {'session_id': SESSION, 'tool_name': tool, 'tool_input': given})

    def test_with_block_a_code_edit_or_a_commit_waits_for_the_steps(self):
        code_file = {'file_path': os.path.join(SCRIPTS, 'x.py')}
        _, err, code = self.guard('Edit', code_file)
        self.assertEqual(2, code)
        self.assertIn('write its steps into the Status box first', err)
        self.assertEqual(2, self.guard('Bash', {'command': 'git add -A && git commit -m x'})[2])
        # Not code work: reading, a plain command, Claude's notes in ~/.claude, a temp file.
        self.assertEqual(0, self.guard('Bash', {'command': 'git status'})[2])
        self.assertEqual(0, self.guard('Write', {'file_path': os.path.expanduser('~/.claude/projects/p/memory/a.md')})[2])
        self.assertEqual(0, self.guard('Write', {'file_path': '/tmp/scratch/a.txt'})[2])
        # Once this session has an open step, the edit runs; another agent's step alone does not count.
        self.run_tool('step', 'review', 'running', '0', '--agent', 'qa a9f3c2')
        self.assertEqual(2, self.guard('Edit', code_file)[2])
        self.run_tool('step', '1. plan', 'running', '0')
        self.assertEqual((0, ''), (self.guard('Edit', code_file)[2], self.guard('Edit', code_file)[1]))
        # A plan whose steps are all over does not let the next task through, nor does an older `row`.
        self.run_tool('step', '1. plan', 'done', '100')
        self.run_tool('row', 'gate', 'running', '3/12', '-')
        self.assertEqual(2, self.guard('Edit', code_file)[2])

    def test_what_counts_as_code_work_and_what_is_bookkeeping(self):
        code = lambda tool, given: self.guard(tool, given)[2]     # noqa: E731
        # Commits only where a command starts, options allowed; a mention, a log or commit-tree is not one.
        for command in ('git commit -m x', 'cd a; git -C repo commit -am x', 'make && git commit'):
            self.assertEqual(2, code('Bash', {'command': command}), command)
        for command in ('echo "remember to git commit later"', 'git log --grep commit', 'git commit-tree HEAD^{tree}'):
            self.assertEqual(0, code('Bash', {'command': command}), command)
        # Notebooks by their own key; an edit with no path is not work.
        self.assertEqual(2, code('NotebookEdit', {'notebook_path': os.path.join(SCRIPTS, 'n.ipynb')}))
        self.assertEqual(0, code('NotebookEdit', {'notebook_path': '/private/tmp/scratch/n.ipynb'}))
        self.assertEqual(0, code('Edit', {}))
        # Bookkeeping: a project's mode files, the session scratchpad; code under ~/.claude is code work.
        self.assertEqual(0, code('Write', {'file_path': os.path.join(SCRIPTS, '..', '.claude', 'mode')}))
        self.assertEqual(0, code('Write', {'file_path': os.path.join(tempfile.gettempdir(), 'claude-501', 'scratchpad', 'a.sh')}))
        self.assertEqual(2, code('Edit', {'file_path': os.path.expanduser('~/.claude/dev-mods/x/hooks/register.tsx')}))

    def test_a_subagent_goes_on_under_its_own_steps_and_is_told_to_sign_them(self):
        payload = {'session_id': SESSION, 'tool_name': 'Edit', 'tool_input': {'file_path': os.path.join(SCRIPTS, 'x.py')},
                   'agent_id': 'a1b2c3d4', 'agent_type': 'developer'}
        _, err, code = self.run_hook('guard', payload)
        self.assertEqual(2, code)
        self.assertIn('--agent "developer a1b2c3"', err)
        self.run_tool('step', '1. write x', 'running', '0', '--agent', 'developer a1b2c3')
        self.assertEqual(0, self.run_hook('guard', payload)[2])

    def test_an_unusable_session_lets_the_edit_through_and_an_unreadable_file_says_how_to_mend_it(self):
        given = {'tool_name': 'Edit', 'tool_input': {'file_path': os.path.join(SCRIPTS, 'x.py')}}
        self.assertEqual(0, self.run_hook('guard', dict(given, session_id='../x'))[2])
        with open(os.path.join(self.dir, SESSION + '.json'), 'w', encoding='utf-8') as handle:
            handle.write('[1, 2]')
        _, err, code = self.run_hook('guard', dict(given, session_id=SESSION))
        self.assertEqual(2, code)
        self.assertIn('clear', err)

    def test_an_older_writer_keeps_a_steps_percentage_and_blocker_in_the_older_fields(self):
        self.run_tool('step', '1. plan', 'running', '40', '--blocker', 'approval')
        path = os.path.join(self.dir, SESSION + '.json')
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        # What an older plugin's rewrite keeps: the four older fields only.
        data['rows'] = [{key: row[key] for key in ('item', 'state', 'figure', 'waiting')} for row in data['rows']]
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle)
        row = self.rows()[0]
        self.assertEqual(('40%', 'approval', '40', ''), (row['figure'], row['waiting'], row['percent'], row['agent']))

    def test_past_fifty_rows_finished_subagent_steps_go_first_and_this_sessions_open_steps_last(self):
        path = os.path.join(self.dir, SESSION + '.json')
        rows = [{'item': 'mine %d' % n, 'state': 'running', 'percent': '0'} for n in range(3)]
        rows += [{'item': 'theirs %d' % n, 'state': 'done' if n < 10 else 'running', 'percent': '0', 'agent': 'qa x'} for n in range(48)]
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({'now': '', 'next': '', 'rows': rows, 'updated': ''}, handle)
        self.run_tool('step', 'mine 3', 'running', '0')
        kept = self.rows()
        self.assertEqual(50, len(kept))
        self.assertEqual(['mine 0', 'mine 1', 'mine 2', 'mine 3'], [row['item'] for row in kept if not row['agent']])
        self.assertEqual(8, sum(1 for row in kept if row['agent'] and row['state'] == 'done'))

    def test_with_remind_nothing_is_refused_and_a_bad_payload_never_is(self):
        with open(os.path.join(self.dir, 'u.json'), 'w', encoding='utf-8') as handle:
            json.dump({'steps': {'enforce': 'remind'}}, handle)
        self.assertEqual(0, self.guard('Edit', {'file_path': os.path.join(SCRIPTS, 'x.py')})[2])
        for payload in ('not json', {'tool_name': 'Edit'}):
            done = subprocess.run([sys.executable, SCRIPT, 'hook', 'guard'], env=self.env, capture_output=True,
                                  input=(payload if isinstance(payload, str) else json.dumps(payload)).encode())
            self.assertEqual(0, done.returncode)


if __name__ == '__main__':
    unittest.main()
