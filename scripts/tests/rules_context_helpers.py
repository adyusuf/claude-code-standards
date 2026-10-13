"""Shared fixtures of the rules-loader tests (test_rules_context.py: the pure functions;
test_rules_context_cli.py: main(), the command line and the hook registration).
Not a test module itself: the discover pattern is test_*.py."""
import importlib.util
import io
import os
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SCRIPT = os.path.join(REPO, 'scripts', 'rules-context.py')
HOOKS = os.path.join(REPO, 'hooks', 'hooks.json')
_spec = importlib.util.spec_from_file_location('rules_context', SCRIPT)
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

with open(rc.RULES, encoding='utf-8') as _handle:
    REAL_TEXT = _handle.read()
REAL_PARTS = rc.parts(REAL_TEXT)
SESSION_PARTS = rc.mode_parts(REAL_TEXT, 'session', 4)
SUBAGENT_PARTS = rc.mode_parts(REAL_TEXT, 'subagent', 4)


def synthetic_text():
    """One block over the limit (many short lines) and one single line over the limit."""
    big_block = '## Big\n' + ('x' * 79 + '\n') * 200
    long_line = '26. Long\n' + 'y' * (rc.PART_LIMIT * 2 + 123) + '\n'
    return 'intro\n## Small\nsmall body\n' + big_block + long_line + '## Tail\n21-23. last\n'


def quote_heavy_text():
    """About 9,400 characters in 30 sections: one session part, but every `"` and newline
    doubles in the JSON envelope, so the subagent envelope of that single part is over the cap."""
    section = '## S{n:02d}\n' + 'q"q"q"q"q"q"q"q"q"q"q"q"\n' * 12
    text = ''.join(section.format(n=n) for n in range(30))
    assert 9000 < len(text) <= rc.PART_LIMIT, len(text)
    return text


def run_main(argv, rules_path=None):
    """main() in-process: (exit code, stdout, stderr). RULES is pointed at rules_path if given."""
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(rc, 'RULES', rules_path or rc.RULES), redirect_stdout(out), redirect_stderr(err):
        code = rc.main(['rules-context.py'] + argv)
    return code, out.getvalue(), err.getvalue()


def run_cli(*args, script=SCRIPT):
    result = subprocess.run([sys.executable, script, *args], capture_output=True,
                            text=True, encoding='utf-8', env={**os.environ, 'PYTHONUTF8': '1'})
    return result.returncode, result.stdout, result.stderr
