"""coverage.sh's JavaScript half (#29) — split from test_coverage_tooling.py to keep
both files under the 300-line limit (#9). The fixtures are shared from there."""
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_coverage_tooling import COVERAGE, FakeVenv, executable  # noqa: E402


@unittest.skipUnless(shutil.which('node'), 'node is needed to drive the JavaScript half')
class JavaScriptCoverage(FakeVenv):
    """coverage.sh's JavaScript half, run for real with Node's built-in coverage.

    The trap it guards: Node reports only files a test LOADED. A page script no
    test requires would simply be absent from the report — out of the denominator,
    and the gate green. That case must end as NOT MEASURED, not as a pass.
    """

    MODULE = ('module.exports = { half(x) {\n  if (x > 0) {\n    return "pos";\n  }\n'
              '  const a = 1;\n  const b = 2;\n  const c = 3;\n  const d = 4;\n'
              '  return String(a + b + c + d);\n} };\n')

    def js(self, name, body):
        path = os.path.join(self.root, 'scripts', *name.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(body)

    def spec(self, *calls, failing=False):
        lines = ['const test = require("node:test");',
                 'const assert = require("node:assert");',
                 'const m = require("../lib/m.js");',
                 'test("m", () => {']
        lines += [f'  m.half({c});' for c in calls]
        lines.append('  assert.equal(1, 2);' if failing else '  assert.ok(true);')
        lines.append('});')
        self.js('tests/m.test.js', '\n'.join(lines) + '\n')

    def run_js(self):
        self.js('lib/m.js', self.MODULE)
        return self.run_coverage(self.stub('exit 0', 'TOTAL 100 0 100%', 0))

    def test_fully_exercised_javascript_passes(self):
        self.spec(1, -1)
        out, code = self.run_js()
        self.assertIn('▶ JavaScript', out)
        self.assertIn('m.js', out)
        self.assertEqual(0, code, out)

    def test_below_the_threshold_fails(self):
        self.spec(1)
        out, code = self.run_js()
        self.assertIn('below 80%', out)
        self.assertEqual(1, code, out)

    def test_a_file_no_test_loads_is_NOT_MEASURED_and_blocks(self):
        self.spec(1, -1)
        self.js('lib/orphan.js', 'module.exports = 1;\n')
        out, code = self.run_js()
        self.assertIn('NOT MEASURED: no test loads scripts/lib/orphan.js', out)
        self.assertEqual(3, code, out)

    def test_a_red_suite_is_not_a_coverage_figure(self):
        self.spec(1, -1, failing=True)
        out, code = self.run_js()
        self.assertIn('the tests are red', out)
        self.assertNotIn('at or above 80%\n  shell', out)
        self.assertEqual(1, code, out)

    def test_no_node_is_NOT_MEASURED(self):
        self.spec(1, -1)
        self.js('lib/m.js', self.MODULE)
        venv = self.venv(self.stub('exit 0', 'TOTAL 100 0 100%', 0))
        executable(os.path.join(self.root, 'scripts', 'coverage-shell.sh'),
                   '#!/usr/bin/env bash\nexit 0\n')
        path = os.pathsep.join(entry for entry in os.environ['PATH'].split(os.pathsep)
                               if not os.path.exists(os.path.join(entry, 'node')))
        out, code = self.run_in(COVERAGE, env={'COVERAGE_VENV': venv, 'PATH': path})
        self.assertIn('NOT MEASURED: node is not installed', out)
        self.assertEqual(3, code, out)

    def test_no_javascript_is_n_a(self):
        out, code = self.run_coverage(self.stub('exit 0', 'TOTAL 100 0 100%', 0))
        self.assertIn('n/a: no JavaScript here', out)
        self.assertEqual(0, code, out)


if __name__ == '__main__':
    unittest.main()
