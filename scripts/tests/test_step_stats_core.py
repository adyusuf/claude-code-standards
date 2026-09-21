"""step-stats.py's measurement core — 164 of its 308 statements were uncovered.

The existing test file covers role labels. This one covers the parts that decide
what gets WRITTEN, and the most important of those is the sanitiser: this script
reads every session transcript on the machine and generates a document from
them. If a project name, a home path, a SHA or a password survives the reduction,
it is published. The script knows that — it has a canary and refuses to write
when the canary leaks — and none of that machinery was tested.

The second theme is `count_steps` deciding what actually RAN. A command inside a
heredoc body, or behind `grep`/`echo`, is a MENTION, not a run, and counting
mentions inflates every figure the document reports.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('step_stats_core', os.path.join(SCRIPTS, 'step-stats.py'))
stats = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stats)


class Shape(unittest.TestCase):
    """Every VALUE must become a placeholder; only the shape of a command is kept."""

    def test_a_path_argument_becomes_a_placeholder(self):
        self.assertEqual('cat <path>', stats.shape('cat /Users/someone/secret.txt', deny=None))

    def test_a_leading_variable_assignment_is_not_mistaken_for_a_command(self):
        # The recorded regression: `L=/tmp/x.log; cmd` — taking the basename kept
        # the path tail, so the value rode along inside the "command name".
        shaped = stats.shape('L=/private/tmp/run.log; dotnet build', deny=None)
        self.assertTrue(shaped.startswith('<var>'), shaped)
        self.assertNotIn('run.log', shaped)

    def test_flags_are_kept_because_they_are_shape_not_value(self):
        shaped = stats.shape('npm test -- --run --coverage', deny=None)
        self.assertIn('--run', shaped)
        self.assertIn('--coverage', shaped)

    def test_a_flag_value_is_dropped(self):
        self.assertNotIn('secret', stats.shape('curl --token=secret123', deny=None))

    def test_a_sha_becomes_a_placeholder(self):
        shaped = stats.shape('git checkout d401a71eefa6e931dfad5828b0c4825f33dfea20', deny=None)
        self.assertIn('<sha>', shaped)
        self.assertNotIn('d401a71', shaped)

    def test_repeated_placeholders_collapse(self):
        shaped = stats.shape('cp /a/one /b/two /c/three /d/four', deny=None)
        self.assertIn('…', shaped, shaped)

    def test_the_result_is_length_capped(self):
        self.assertLessEqual(len(stats.shape('cmd ' + 'x' * 500, deny=None)), 64)

    def test_only_the_first_shell_segment_is_kept(self):
        # What follows a `&&` is a different command and is summarised separately;
        # keeping it here would let a later argument leak into this shape.
        shaped = stats.shape('ls && cat /Users/someone/secret.txt', deny=None)
        self.assertNotIn('secret', shaped)


class TheSanitiserGate(unittest.TestCase):
    """A mutation-style self-check: the script refuses to write if a synthetic
    identifier survives its own reduction."""

    def test_the_canary_survives_nothing(self):
        produced = stats.sanitizer_gate()
        for marker in stats.LEAK_MARKERS:
            self.assertNotIn(marker.lower(), produced.lower(),
                             f'{marker!r} survived the reduction: {produced!r}')

    def test_the_canary_contains_every_marker_it_claims_to_test(self):
        # A canary that does not actually carry a marker tests nothing about it,
        # and the gate would pass by accident.
        for marker in stats.LEAK_MARKERS:
            self.assertIn(marker.lower(), stats.CANARY.lower(),
                          f'LEAK_MARKERS names {marker!r} but the canary lacks it')

    def test_the_gate_EXITS_when_a_marker_survives(self):
        # The brake itself: break `shape` so it returns the input untouched, and
        # the gate must refuse rather than write.
        original = stats.shape
        stats.shape = lambda command, deny=None: command
        try:
            with self.assertRaises(SystemExit) as caught:
                stats.sanitizer_gate()
            self.assertIn('sanitiser gate FAILED', str(caught.exception))
        finally:
            stats.shape = original

    def test_scan_output_finds_a_home_path_in_the_document(self):
        self.assertTrue(stats.scan_output('text /Users/someone/thing more'))

    def test_scan_output_finds_a_long_hex_string(self):
        self.assertTrue(stats.scan_output('sha d401a71eefa6e931dfad5828b0c4825f33dfea'))

    def test_scan_output_is_clean_for_ordinary_prose(self):
        self.assertEqual([], stats.scan_output('The gate ran and every step passed.'))


class CommandPart(unittest.TestCase):
    """Heredoc BODIES are dropped; what surrounds them is real."""

    def test_a_heredoc_body_is_dropped(self):
        command = 'cat > f.sh <<EOF\nnpm test\nEOF'
        self.assertNotIn('npm test', stats.command_part(command))

    def test_a_real_command_after_the_heredoc_survives(self):
        command = 'cat > f.sh <<EOF\nbody\nEOF\nnpm test'
        self.assertIn('npm test', stats.command_part(command))

    def test_an_unterminated_heredoc_swallows_the_rest(self):
        # Fail safe: with no closing marker the remainder is body, so a step
        # inside it is not counted as having run.
        command = 'cat <<EOF\nnpm test'
        self.assertNotIn('npm test', stats.command_part(command))

    def test_a_command_with_no_heredoc_is_unchanged(self):
        self.assertIn('npm test', stats.command_part('npm test'))


class CountSteps(unittest.TestCase):
    """A MENTION is not a RUN. Counting mentions inflates every figure."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def transcript(self, *commands):
        path = os.path.join(self.dir, 'session.jsonl')
        with open(path, 'w', encoding='utf-8') as handle:
            for command in commands:
                handle.write(json.dumps({'message': {'content': [
                    {'type': 'tool_use', 'input': {'command': command}}]}}) + '\n')
        return [path]

    def test_a_real_run_is_counted(self):
        counts, _, _ = stats.count_steps(self.transcript('npm test -- --run'))
        self.assertTrue(sum(counts.values()) > 0, counts)

    def test_a_command_inside_a_heredoc_is_dismissed_not_counted(self):
        counts, _, dismissed = stats.count_steps(
            self.transcript('cat > x.sh <<EOF\nnpm test -- --run\nEOF'))
        self.assertEqual(0, sum(counts.values()), counts)
        self.assertTrue(sum(dismissed.values()) > 0, 'it was not even recorded as dismissed')

    def test_a_command_behind_grep_is_dismissed(self):
        counts, _, dismissed = stats.count_steps(self.transcript('grep -r "npm test -- --run" .'))
        self.assertEqual(0, sum(counts.values()), counts)

    def test_the_script_ignores_its_own_output(self):
        # step-stats reading a transcript of itself would count its own examples.
        counts, _, _ = stats.count_steps(self.transcript('python3 scripts/step-stats.py'))
        self.assertEqual(0, sum(counts.values()), counts)

    def test_a_corrupt_line_does_not_stop_the_count(self):
        path = self.transcript('npm test -- --run')[0]
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write('{ not json\n')
        counts, _, _ = stats.count_steps([path])
        self.assertTrue(sum(counts.values()) > 0)

    def test_the_sample_kept_for_a_step_is_SHAPED(self):
        # The document shows one example per step; an unshaped one would publish
        # whatever path happened to be in the winning command.
        _, samples, _ = stats.count_steps(
            self.transcript('npm test -- --run /Users/someone/project'))
        for sample in samples.values():
            self.assertNotIn('/Users/', sample)


class Measure(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def transcript(self, *usages):
        path = os.path.join(self.dir, 's.jsonl')
        with open(path, 'w', encoding='utf-8') as handle:
            for model, usage in usages:
                handle.write(json.dumps({'message': {'model': model, 'usage': usage}}) + '\n')
        return path

    def test_the_first_request_prefix_and_the_count_are_reported(self):
        path = self.transcript(
            ('claude-opus-5', {'input_tokens': 10, 'cache_read_input_tokens': 90}),
            ('claude-opus-5', {'input_tokens': 5}))
        first, count, cost, model = stats.measure([path])[path]
        self.assertEqual(100, first, 'the prefix is the whole first request')
        self.assertEqual(2, count)
        self.assertEqual('claude-opus-5', model)
        self.assertGreater(cost, 0)

    def test_a_transcript_with_no_usage_is_left_out(self):
        path = self.transcript(('claude-opus-5', {}))
        self.assertEqual({}, stats.measure([path]))

    def test_the_cost_uses_the_model_s_own_cache_rate(self):
        # fable-5-1 reads cache at 2.5%, opus at 10% — one flat rate would
        # overstate the cheaper model by four times.
        usage = {'cache_read_input_tokens': 1_000_000}
        opus = self.transcript(('claude-opus-5', usage))
        cost_opus = stats.measure([opus])[opus][2]
        shutil.rmtree(self.dir); self.dir = tempfile.mkdtemp()
        fable = self.transcript(('claude-fable-5-1', usage))
        cost_fable = stats.measure([fable])[fable][2]
        self.assertAlmostEqual(0.5, cost_opus, places=4)
        self.assertAlmostEqual(0.25, cost_fable, places=4)


if __name__ == '__main__':
    unittest.main()
