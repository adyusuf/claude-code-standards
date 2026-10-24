"""coverage.sh's TypeScript half (#29, the narrow exception of 22/10/2026): the mod's engine-free logic is MEASURED with
Deno, the engine glue is the one listed exclusion, and anything else is NOT MEASURED. Fixtures are shared from
test_coverage_tooling.py. Cases that need a real Deno are skipped without one (the others use a fake or no Deno)."""
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_coverage_tooling import COVERAGE, SCRIPTS, FakeVenv, executable  # noqa: E402

GLUE = "import { register } from 'claude-code'\nexport const glue = register\n"
LOGIC = "export function twice(n: number): number {\n  return n * 2\n}\n\nexport function never(): number {\n  return 0\n}\n"
TEST_ALL = "import { expect, test } from 'claude-code/testing'\nimport { never, twice } from './logic'\n" \
           "test('twice', () => expect(twice(2)).toBe(4))\ntest('never', () => expect(never()).toBe(0))\n"
TEST_HALF = "import { expect, test } from 'claude-code/testing'\nimport { twice } from './logic'\n" \
            "test('twice', () => expect(twice(2)).toBe(4))\n"


def without_deno(path):
    return os.pathsep.join(entry for entry in path.split(os.pathsep) if not os.path.exists(os.path.join(entry, 'deno')))


class TypeScriptStep(FakeVenv):
    def put(self, name, text):
        path = os.path.join(self.root, 'hooks', name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)

    def run_ts(self, path=None):
        venv = self.venv(self.stub('exit 0', 'TOTAL 100 0 100%', 0))
        executable(os.path.join(self.root, 'scripts', 'coverage-shell.sh'), '#!/usr/bin/env bash\nexit 0\n')
        shutil.copytree(os.path.join(SCRIPTS, 'ts-shim'), os.path.join(self.root, 'scripts', 'ts-shim'))
        env = {'COVERAGE_VENV': venv}
        if path is not None:
            env['PATH'] = path
        return self.run_in(COVERAGE, env=env)

    def test_no_typescript_is_not_applicable(self):
        out, code = self.run_ts()
        self.assertIn('n/a: no TypeScript here', out)
        self.assertEqual(0, code, out)

    def test_typescript_without_deno_is_NOT_MEASURED_and_blocks(self):
        self.put('logic.ts', LOGIC)
        out, code = self.run_ts(without_deno(os.environ['PATH']))
        self.assertIn('NOT MEASURED: deno is not installed', out)
        self.assertEqual(3, code, out)

    def test_an_engine_file_that_is_not_the_listed_glue_is_NOT_MEASURED(self):
        self.put('register.tsx', GLUE)
        self.put('other.ts', GLUE)
        out, code = self.run_ts()
        self.assertIn('NOT MEASURED: hooks/other.ts imports the engine but is not the listed glue file', out)
        self.assertEqual(3, code, out)

    @unittest.skipUnless(shutil.which('deno'), 'needs Deno')
    def test_logic_at_full_coverage_passes_and_the_glue_is_reported_as_not_measured(self):
        self.put('register.tsx', GLUE)
        self.put('logic.ts', LOGIC)
        self.put('logic.test.ts', TEST_ALL)
        out, code = self.run_ts()
        self.assertIn('hooks/logic.ts', out)
        self.assertIn('✓ at or above 80%', out)
        self.assertIn('not measured, listed exclusion (rule #29, narrow exception): hooks/register.tsx', out)
        self.assertEqual(0, code, out)

    @unittest.skipUnless(shutil.which('deno'), 'needs Deno')
    def test_logic_below_the_threshold_fails(self):
        self.put('logic.ts', LOGIC)
        self.put('logic.test.ts', TEST_HALF)
        out, code = self.run_ts()
        self.assertIn('✗ below 80%', out)
        self.assertEqual(1, code, out)

    @unittest.skipUnless(shutil.which('deno'), 'needs Deno')
    def test_a_logic_file_no_test_loads_is_NOT_MEASURED(self):
        self.put('logic.ts', LOGIC)
        self.put('logic.test.ts', "import { test } from 'claude-code/testing'\ntest('empty', () => {})\n")
        out, code = self.run_ts()
        self.assertIn('NOT MEASURED: no test loads hooks/logic.ts', out)
        self.assertEqual(3, code, out)

    def test_hand_written_script_files_anywhere_under_hooks_cannot_hide(self):
        # Found by QA: only hooks/*.ts and hooks/*.tsx were looked at, so logic moved into a subfolder (or into .mts, .cts,
        # .js, .jsx) and imported by the glue was never listed, never measured, and the run passed.
        for name in ('lib/helper.ts', 'extra.mts', 'extra.cts', 'extra.js', 'lib/deep/extra.jsx'):
            with self.subTest(name=name):
                self.setUp()
                self.put('register.tsx', GLUE)
                self.put(name, LOGIC)
                out, code = self.run_ts()
                self.assertEqual(3, code, out)
                self.assertTrue('NOT MEASURED' in out or 'n/a' not in out, out)
                self.tearDown()

    def test_every_way_of_naming_the_engine_marks_a_file_as_engine_code(self):
        for text in ('import type { X } from "claude-code"\n', "const m = await import('claude-code')\n",
                     "const m = require('claude-code')\n", "import { y } from 'claude-code/testing'\n"):
            with self.subTest(text=text):
                self.setUp()
                self.put('register.tsx', GLUE)
                self.put('other.ts', text)
                out, code = self.run_ts()
                self.assertIn('hooks/other.ts imports the engine but is not the listed glue file', out)
                self.assertEqual(3, code, out)
                self.tearDown()

    @unittest.skipUnless(shutil.which('deno'), 'needs Deno')
    def test_a_red_logic_test_is_not_a_measurement(self):
        self.put('logic.ts', LOGIC)
        self.put('logic.test.ts', "import { expect, test } from 'claude-code/testing'\ntest('bad', () => expect(1).toBe(2))\n")
        out, code = self.run_ts()
        self.assertIn('the tests are red', out)
        self.assertNotIn('No such file', out)    # the failing run's own log must still be there to print
        self.assertEqual(1, code, out)


if __name__ == '__main__':
    unittest.main()
