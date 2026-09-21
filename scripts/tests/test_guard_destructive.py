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

