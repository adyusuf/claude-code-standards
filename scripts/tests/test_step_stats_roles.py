"""role_label: a plugin agent's name must not carry the plugin identifier.

Why this test exists: the report's role table is passed through the sanitiser
before docs/measurement-log.md is written, and the sanitiser's deny-set is
derived from this machine. A plugin-provided agent (`<plugin>:<agent>`) put the
plugin's name in the table, so `--write` refused every time — the measurement
could not be recorded at all (measured: 'agent-skills').
"""
import importlib.util
import os
import unittest

spec = importlib.util.spec_from_file_location(
    'step_stats', os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'step-stats.py')))
step_stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step_stats)


class RoleLabel(unittest.TestCase):
    def test_plugin_agent_loses_the_plugin_name(self):
        self.assertEqual(step_stats.role_label('agent-skills:code-reviewer'),
                         'ext:code-reviewer')

    def test_plugin_name_never_survives(self):
        for role in ('some-plugin:qa', 'a:b:c'):
            self.assertNotIn(role.split(':', 1)[0], step_stats.role_label(role))

    def test_a_mode_role_is_unchanged(self):
        self.assertEqual(step_stats.role_label('qa'), 'qa')

    def test_an_old_turkish_role_name_is_translated(self):
        self.assertEqual(step_stats.role_label('analiz'), 'analyst')

    def test_an_unknown_bare_role_passes_through(self):
        self.assertEqual(step_stats.role_label('brand-new-role'), 'brand-new-role')


if __name__ == '__main__':
    unittest.main()


class CutDelta(unittest.TestCase):
    """The delta of a configuration cut: correct sign, and no verdict below the floor."""

    def test_a_drop_is_negative(self):
        self.assertEqual(step_stats.cut_delta(100_000, 10, 90_000, 5), '**-10,000 (-10%)**')

    def test_a_rise_is_positive_not_a_saving(self):
        cell = step_stats.cut_delta(82_359, 152, 90_957, 5)
        self.assertTrue(cell.startswith('**+8,598'), cell)
        self.assertNotIn('--', cell)

    def test_below_the_floor_is_not_measured(self):
        cell = step_stats.cut_delta(82_359, 152, 90_957, 2)
        self.assertIn('not measured', cell)
        self.assertIn('2 session', cell)

    def test_no_session_after_the_cut(self):
        self.assertIn('needs a new session', step_stats.cut_delta(82_359, 152, 0, 0))
