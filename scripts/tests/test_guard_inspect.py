"""The guard's judgement (scripts/guard-inspect.py), tested directly.

Until recently this logic was a heredoc inside guard-destructive.sh: every case
cost a subprocess, and a bash coverage tracer counted the whole program as ONE
statement, so the file measured 3/19 while every rule was being exercised.

What is pinned here is the SHAPE of the guard, not a list of commands:

  * it blocks on the never-do list's irreversible operations;
  * it FAILS CLOSED — an unparseable payload is judged as raw text, never waved
    through, because an unparseable payload is the case an attacker would want;
  * heredoc BODIES are ignored for the git rules (a heredoc that writes a script
    mentioning a banned flag is not a commit) but NOT for the destructive-SQL and
    rm rules, because those really do execute inside a heredoc;
  * a command that merely MENTIONS a banned phrase — a commit message, an echo —
    is still blocked. That is deliberate over-blocking: the model rewords it, and
    a guard tuned to allow mentions is one string away from allowing the act.

Test inputs are ASSEMBLED FROM FRAGMENTS on purpose. A literal banned command in
this file would be blocked by the live hook the moment anyone writes the file.
"""
import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('guard_inspect', os.path.join(SCRIPTS, 'guard-inspect.py'))
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

PUSH = 'git ' + 'pu' + 'sh'
FORCE = '--fo' + 'rce'
NO_VERIFY = '--no-' + 'verify'
DROP = 'DR' + 'OP'
TRUNC = 'TRUN' + 'CATE'
RM = 'rm ' + '-rf'
TABLE = 'TAB' + 'LE'


class Blocked(unittest.TestCase):
    def assertBlocked(self, command, expect=None):
        reason = guard.verdict(command)
        self.assertIsNotNone(reason, f'NOT blocked: {command!r}')
        if expect:
            self.assertIn(expect, reason)

    def assertAllowed(self, command):
        self.assertIsNone(guard.verdict(command), f'blocked but should not be: {command!r}')

    def test_a_forced_push_is_blocked_in_every_spelling(self):
        for flag in (FORCE, '-' + 'f', FORCE + '-with-lease'):
            self.assertBlocked(f'{PUSH} {flag} origin dev', 'forced push')

    def test_a_push_straight_to_the_protected_branches_is_blocked(self):
        for branch in ('main', 'prod'):
            self.assertBlocked(f'{PUSH} origin {branch}', 'straight to')
            self.assertBlocked(f'{PUSH} origin HEAD:{branch}', 'straight to')

    def test_pushing_to_dev_or_test_is_allowed(self):
        for branch in ('dev', 'test'):
            self.assertAllowed(f'{PUSH} origin {branch}')

    def test_skipping_the_pre_commit_hook_is_blocked_for_each_verb(self):
        for verb in ('commit', 'push', 'merge'):
            self.assertBlocked(f'git {verb} {NO_VERIFY}', 'gitleaks')

    def test_destructive_sql_is_blocked_for_each_object(self):
        for verb in (DROP, TRUNC):
            for obj in ('TABLE', 'DATABASE', 'SCHEMA'):
                self.assertBlocked(f'psql -c "{verb} {obj} users"', 'backup')

    def test_a_recursive_delete_of_a_dangerous_root_is_blocked(self):
        for path in ('/', '~', '$HOME', '.', '*'):
            self.assertBlocked(f'{RM} {path}', 'recursive delete')

    def test_a_recursive_delete_inside_a_project_is_allowed(self):
        self.assertAllowed(f'{RM} build/artifacts')

    def test_the_git_rules_are_SCOPED_to_the_git_verb(self):
        # Measured, not assumed: a commit message that mentions the push flag is
        # ALLOWED, because the pattern requires the push verb in front of it. The
        # guard is more precise here than its header's "a command that only
        # MENTIONS one of these words" suggests.
        self.assertAllowed(f'git commit -m "never {FORCE} anything"')

    def test_inside_a_push_command_a_mention_DOES_match(self):
        # The scope is the verb, not the intent: the flag named anywhere in a
        # PUSH command matches, message or not. Measured, including the boundary
        # — the pattern needs whitespace or end-of-string after the flag, so
        # `"no --force"` (quote straight after) slips past while
        # `"no --force here"` does not. Over-blocking on a push is the safe side
        # of that line and the model can reword; relying on the gap would not be.
        self.assertBlocked(f'{PUSH} origin dev -m "no {FORCE} here"', 'forced push')
        self.assertAllowed(f'{PUSH} origin dev -m "no {FORCE}"')

    def test_but_the_sql_and_rm_rules_are_NOT_scoped(self):
        # The asymmetry is real and worth knowing before someone "fixes" it: an
        # echo or a comment that merely names the SQL verb IS blocked, because
        # those rules match the whole command with no verb in front. Blunter on
        # purpose — a heredoc fed to psql executes, and there is no reliable way
        # to tell one from a sentence about it.
        self.assertBlocked(f'echo "do not {DROP} {TABLE} users"')
        self.assertBlocked(f'# a comment about {DROP} SCHEMA public')


class Heredocs(unittest.TestCase):
    def test_a_heredoc_that_WRITES_a_banned_flag_is_not_a_commit(self):
        script = f'cat > deploy.sh <<EOF\ngit commit {NO_VERIFY}\nEOF'
        self.assertIsNone(guard.verdict(script), 'writing a script is not running it')

    def test_but_destructive_sql_INSIDE_a_heredoc_is_blocked(self):
        # `psql <<EOF ...` really executes, so this body is not stripped.
        sql = f'psql <<EOF\n{DROP} TABLE users;\nEOF'
        self.assertIsNotNone(guard.verdict(sql))

    def test_the_heredoc_tag_is_matched_to_close_the_body(self):
        script = f'cat <<MARKER\ngit commit {NO_VERIFY}\nMARKER\n{PUSH} origin main'
        # The body is skipped, but the line AFTER the closing tag is judged.
        self.assertIn('straight to', guard.verdict(script))

    def test_a_quoted_heredoc_tag_is_recognised(self):
        script = f"cat <<'END'\ngit commit {NO_VERIFY}\nEND"
        self.assertIsNone(guard.verdict(script))


class FailClosed(unittest.TestCase):
    def test_an_unparseable_payload_is_judged_as_RAW_TEXT(self):
        # The case an attacker would want: break the JSON, slip the command past.
        raw = f'not json at all {PUSH} {FORCE} origin main'
        self.assertIsNotNone(guard.verdict(guard.command_of(raw)))

    def test_a_json_payload_is_read_from_tool_input(self):
        payload = json.dumps({'tool_input': {'command': f'{PUSH} {FORCE} origin dev'}})
        self.assertEqual(f'{PUSH} {FORCE} origin dev', guard.command_of(payload))

    def test_json_with_no_command_falls_back_to_the_raw_text(self):
        payload = json.dumps({'tool_input': {}})
        self.assertEqual(payload, guard.command_of(payload))

    def test_an_ordinary_command_is_allowed(self):
        self.assertIsNone(guard.verdict('ls -la && git status'))


class ExitCodes(unittest.TestCase):
    """The wrapper turns 0 into allow, 2 into block and ANYTHING ELSE into a
    block, so these two codes are the contract."""

    def run_main(self, payload):
        stdin, sys.stdin = sys.stdin, io.StringIO(payload)
        try:
            buffer = io.StringIO()
            with redirect_stderr(buffer):
                code = guard.main()
            return buffer.getvalue(), code
        finally:
            sys.stdin = stdin

    def test_an_allowed_command_exits_0_and_says_nothing(self):
        out, code = self.run_main('git status')
        self.assertEqual(0, code)
        self.assertEqual('', out)

    def test_a_blocked_command_exits_2_and_explains_on_stderr(self):
        out, code = self.run_main(f'{PUSH} {FORCE} origin main')
        self.assertEqual(2, code)
        self.assertIn('BLOCKED', out)
        self.assertIn('run it themselves', out)


if __name__ == '__main__':
    unittest.main()
