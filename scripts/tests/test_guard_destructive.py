import json
import os
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
