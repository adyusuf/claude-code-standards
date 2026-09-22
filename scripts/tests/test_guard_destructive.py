import json
import os
import json
import shutil
import tempfile
import subprocess
import unittest

GUARD = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'guard-destructive.sh'))


def code(command):
    payload = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command}})
    return subprocess.run(['bash', GUARD], input=payload, capture_output=True, text=True).returncode


BLOCKED = [
    "psql <<EOF\nDROP TABLE t;\nEOF", "cat > f <<EOF\nx\nEOF\ngit push --force",
    'git push --force origin feature/x', 'git push -f', 'git push origin dev --force-with-lease',
    'git push origin main', 'git push origin HEAD:prod', 'git push -u origin prod',
    'git commit --no-verify -m x', 'git push --no-verify',
    'psql -c "DROP TABLE users"', 'sqlite3 db "drop database x"', 'psql -c "TRUNCATE TABLE t"',
    'rm -rf /', 'rm -rf ~', 'rm -rf $HOME', 'rm -fr .', 'rm -rf *', 'cd x && git push -f',
]
ALLOWED = [
    "cat > pre-commit.sh <<'EOF'\ngit commit --no-verify is forbidden\nEOF", "cat <<EOF\ngit push origin prod\nEOF",
    'ls -la', 'git push origin feature/agentic-coding', 'git push -u origin dev', 'git push origin feature/prod-notes',
    'git push origin feature/main-menu', 'rm -rf node_modules', 'rm -rf ./build', 'rm file.txt',
    'git commit -m "wip"', 'git status', 'npm run build', 'echo drop the idea', 'grep -rn "no-verify" .',
    'git pull --force-with-lease-check-doc',
]


class GuardDestructive(unittest.TestCase):
    def test_blocks(self):
        for command in BLOCKED:
            with self.subTest(command=command):
                self.assertEqual(code(command), 2)

    def test_allows(self):
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(code(command), 0)

    def test_unparseable_payload_still_judges_the_raw_text(self):
        result = subprocess.run(['bash', GUARD], input='not json git push --force', capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_message_names_the_reason(self):
        payload = json.dumps({'tool_input': {'command': 'git push -f'}})
        result = subprocess.run(['bash', GUARD], input=payload, capture_output=True, text=True)
        self.assertIn('forced push', result.stderr)


if __name__ == '__main__':
    unittest.main()

class InvokedThroughASymlink(unittest.TestCase):
    """The hook is INSTALLED as a symlink: ~/.claude/hooks/guard-destructive.sh
    points into the repository's scripts/. $BASH_SOURCE is then the link, not the
    target, so anything derived from it with `dirname` lands in hooks/ — where the
    inspector does not exist.

    That is not hypothetical. It shipped for one commit: `guard-inspect.py` was
    looked up beside $BASH_SOURCE, the direct call worked perfectly, and every
    call through the installed symlink came back BLOCKED with "guard-inspect.py is
    missing" — a plainly allowed command refused. Fail-closed made it a work
    stoppage rather than a hole, which is the right failure but still the whole
    hook down.

    A chained symlink is covered too: an install that points a link at a link is
    not exotic, and a single readlink would stop one hop short.
    """

    ALLOWED = json.dumps({'tool_input': {'command': 'git ' + 'pu' + 'sh' + ' origin dev'}})
    BANNED = json.dumps({'tool_input': {'command': 'git ' + 'pu' + 'sh' + ' --fo' + 'rce origin dev'}})

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_through(self, path, payload):
        result = subprocess.run(['bash', path], input=payload, capture_output=True, text=True)
        return result.stdout + result.stderr, result.returncode

    def link(self, name, target):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        os.symlink(target, path)
        return path

    def test_an_allowed_command_is_allowed_through_a_symlink(self):
        link = self.link('hooks/guard-destructive.sh', GUARD)
        out, code = self.run_through(link, self.ALLOWED)
        self.assertEqual(0, code, f'allowed command refused through a symlink:\n{out}')
        self.assertNotIn('missing', out)

    def test_an_allowed_command_is_allowed_through_a_CHAIN_of_symlinks(self):
        first = self.link('hooks/guard-destructive.sh', GUARD)
        second = self.link('deep/chain.sh', first)
        out, code = self.run_through(second, self.ALLOWED)
        self.assertEqual(0, code, f'a chained symlink broke the lookup:\n{out}')

    def test_a_banned_command_is_still_blocked_through_a_symlink(self):
        # The control: the fix must not have made the guard permissive.
        link = self.link('hooks/guard-destructive.sh', GUARD)
        out, code = self.run_through(link, self.BANNED)
        self.assertEqual(2, code)
        self.assertIn('forced push', out)

    def test_the_direct_call_still_works(self):
        out, code = self.run_through(GUARD, self.ALLOWED)
        self.assertEqual(0, code, out)

class GuardFailsClosed(unittest.TestCase):
    """The paths where the guard cannot judge. Every one of them must BLOCK.

    These are the lines that matter most: a guard that fails OPEN stops guarding without
    saying so, and the next `rm -rf` goes through. A guard that fails CLOSED is merely
    annoying.

    ⚠️ These tests run a COPY of the script and therefore add NOTHING to its measured
    coverage — it stays at 65%. That is not an oversight and it is not fixable by
    running the original: the cases under test are "guard-inspect.py is not beside the
    script" and "the inspector answers wrongly", and both need a directory that does not
    contain the real inspector. A symlink does not help either, because the script
    resolves symlinks on purpose and walks back to the real directory. The alternative —
    an environment variable that redirects the inspector — would put a way to redirect
    the guard into the guard, which is worse than an unmeasured line.

    So the behaviour is verified by mutation instead: making either branch `exit 0`
    turns these tests red. The 65% figure is recorded in docs/coverage-gap.md with this
    reason, because a number without its reason invites someone to "fix" it by deleting
    the check.
    """

    BANNED = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'git push --force'}})
    ALLOWED = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'git push origin feature/x'}})

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.guard = os.path.join(self.dir, 'guard-destructive.sh')
        shutil.copy(GUARD, self.guard)

    def run_guard(self, payload, env=None):
        result = subprocess.run(['bash', self.guard], input=payload, capture_output=True,
                                text=True, env=env or dict(os.environ))
        return result.stdout + result.stderr, result.returncode

    def with_inspector(self, body):
        path = os.path.join(self.dir, 'guard-inspect.py')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(body)
        return path

    def test_a_missing_inspector_BLOCKS_and_says_so(self):
        # The copy has no guard-inspect.py beside it. Nothing can be judged, so nothing
        # is allowed.
        out, code = self.run_guard(self.BANNED)
        self.assertEqual(2, code)
        self.assertIn('guard-inspect.py is missing', out)

    def test_a_missing_inspector_blocks_an_ALLOWED_command_too(self):
        # Deliberate: without the inspector the guard cannot tell the two apart, and
        # guessing in the permissive direction is the failure this test exists to stop.
        out, code = self.run_guard(self.ALLOWED)
        self.assertEqual(2, code)
        self.assertIn('missing', out)

    def test_an_inspector_that_crashes_BLOCKS(self):
        self.with_inspector('import sys\nsys.exit(1)\n')
        out, code = self.run_guard(self.BANNED)
        self.assertEqual(2, code)
        self.assertIn('could not inspect', out)

    def test_an_inspector_exiting_with_an_unexpected_status_BLOCKS(self):
        self.with_inspector('import sys\nsys.exit(42)\n')
        _, code = self.run_guard(self.ALLOWED)
        self.assertEqual(2, code, 'an unknown verdict must not be read as approval')

    def test_no_python3_BLOCKS(self):
        # A PATH with everything the script needs EXCEPT python3. Emptying PATH outright
        # would only prove that a guard with no shell cannot run, which is not the case
        # under test: the case is an interpreter that is gone while the rest works.
        self.with_inspector('import sys\nsys.exit(0)\n')
        bin_dir = os.path.join(self.dir, 'bin')
        os.makedirs(bin_dir, exist_ok=True)
        for tool in ('cat', 'grep', 'readlink', 'dirname'):
            found = shutil.which(tool)
            if found:
                os.symlink(found, os.path.join(bin_dir, tool))
        self.assertIsNone(shutil.which('python3', path=bin_dir), 'the fixture must not expose python3')
        env = dict(os.environ, PATH=bin_dir)
        result = subprocess.run([shutil.which('bash') or '/bin/bash', self.guard],
                                input=self.BANNED, capture_output=True, text=True, env=env)
        out = result.stdout + result.stderr
        self.assertEqual(2, result.returncode, out)
        self.assertIn('could not inspect', out)

    def test_an_inspector_that_approves_lets_the_command_through(self):
        # The control: these tests must not have made the guard block everything.
        self.with_inspector('import sys\nsys.exit(0)\n')
        _, code = self.run_guard(self.ALLOWED)
        self.assertEqual(0, code)

    def test_a_payload_with_no_trigger_word_never_reaches_the_inspector(self):
        # The cheap early exit: no inspector present, and `ls -la` is still allowed.
        _, code = self.run_guard(json.dumps({'tool_input': {'command': 'ls -la'}}))
        self.assertEqual(0, code)

