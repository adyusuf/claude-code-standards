"""The typecheck step must follow a solution-style tsconfig's references.

The Vite template's root tsconfig.json is `"files": []` plus `"references"`: it
holds no files of its own. The step ran `tsc -p <dir>` on it, which checked
nothing and always passed. Seen live in gandalf: a broken multi-line import in a
page passed the gate's typecheck and was caught only by `npm run build`
(`tsc -b`). Measured there: with one injected type error `tsc -p .` exits 0 and
`tsc -b .` exits 2.

Each case puts a stub `npx` first on PATH that behaves like tsc on a project
with one type error: build mode (`-b`) reports it, project mode (`-p`) on a
solution-style config does not. The stub also records its arguments.

Mutation-verified: with the old one-line step restored, the references case
turns green — i.e. its test fails. Record: docs/decision-log.md §25.
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GATE = os.path.join(SCRIPTS, 'gate-core.sh')
ANSI = re.compile(r'\x1b\[[0-9;]*m')
BASE_PATH = '/usr/bin:/bin'   # deliberately without the real node tooling

SOLUTION = '{\n  "files": [],\n  "references": [\n    { "path": "./tsconfig.app.json" }\n  ]\n}\n'
PLAIN = '{\n  "compilerOptions": { "strict": true },\n  "include": ["src"]\n}\n'

# Build mode sees the error; project mode on a solution config sees no files.
NPX = """#!/bin/sh
echo "$@" >> "$NPX_LOG"
case " $* " in
  *" -b "*) echo "src/page.tsx(1,14): error TS2322: Type 'string' is not assignable to type 'number'."; exit 2 ;;
  *) exit 0 ;;
esac
"""


def project(tsconfig):
    root = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q', root], check=True)
    os.makedirs(os.path.join(root, 'scripts'))
    web = os.path.join(root, 'frontend')
    os.makedirs(web)
    with open(os.path.join(web, 'package.json'), 'w', encoding='utf-8') as handle:
        handle.write('{ "name": "app", "private": true }\n')
    with open(os.path.join(web, 'tsconfig.json'), 'w', encoding='utf-8') as handle:
        handle.write(tsconfig)
    return root


def install(directory, name, content):
    path = os.path.join(directory, name)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(content)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


class TypecheckStep(unittest.TestCase):
    def setUp(self):
        self.shims = tempfile.mkdtemp()
        self.log = os.path.join(self.shims, 'npx.log')
        install(self.shims, 'npx', NPX)
        self.root = None

    def tearDown(self):
        shutil.rmtree(self.shims, ignore_errors=True)
        if self.root:
            shutil.rmtree(self.root, ignore_errors=True)

    def typecheck(self, tsconfig):
        """Only the lines of the 'typecheck' step, plus every npx call made."""
        self.root = project(tsconfig)
        env = dict(os.environ, PATH=f'{self.shims}:{BASE_PATH}', NPX_LOG=self.log)
        result = subprocess.run(['bash', GATE, 'dev'], cwd=self.root, capture_output=True,
                                text=True, env=env, timeout=120)
        out = ANSI.sub('', result.stdout)
        match = re.search(r'▶ typecheck[^\n]*\n(.*?)\n▶ ', out, re.S)
        calls = open(self.log, encoding='utf-8').read() if os.path.exists(self.log) else ''
        return (match.group(1) if match else out), calls

    def test_a_solution_config_is_checked_in_build_mode(self):
        step, calls = self.typecheck(SOLUTION)
        self.assertIn('tsc -b frontend --noEmit', calls)
        self.assertNotIn('tsc -p', calls)

    def test_a_type_error_behind_references_fails_the_step(self):
        step, _ = self.typecheck(SOLUTION)
        self.assertIn('✗', step)
        self.assertNotIn('✓', step)

    def test_a_plain_config_still_uses_project_mode(self):
        step, calls = self.typecheck(PLAIN)
        self.assertIn('tsc -p frontend --noEmit', calls)
        self.assertNotIn('tsc -b', calls)
        self.assertIn('✓', step)

    def test_no_tsconfig_is_reported_as_skipped(self):
        self.root = project(PLAIN)
        os.remove(os.path.join(self.root, 'frontend', 'tsconfig.json'))
        env = dict(os.environ, PATH=f'{self.shims}:{BASE_PATH}', NPX_LOG=self.log)
        result = subprocess.run(['bash', GATE, 'dev'], cwd=self.root, capture_output=True,
                                text=True, env=env, timeout=120)
        self.assertIn('tsc (frontend): no tsconfig', ANSI.sub('', result.stdout))


if __name__ == '__main__':
    unittest.main()
