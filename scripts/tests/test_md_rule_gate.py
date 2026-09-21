"""The rule-loss gate (scripts/md-rule-gate.py).

It decides whether a "simplification" of a guidance file dropped a RULE, and it
had no tests at all — 155 statements at 0%. Its own comments record three
blind spots found by mutation, and each one is pinned here, because all three
were of the worst kind: the gate said PASSED while a rule was gone.

  1. The marker pattern only looked for PERMANENT/MANDATORY/FORBIDDEN, so a rule
     written in plain prohibitive prose could be deleted silently.
  2. The rule text was still present but "NO LONGER VALID" had been appended —
     presence alone was checked, so an INVERTED rule passed.
  3. An item's body was deleted and its first six words left behind — the window
     match succeeded, so a TRUNCATED rule passed.

Tests call the module's functions and `main()` directly rather than spawning it,
so the measurement lands on this file and not on a subprocess.
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('md_rule_gate', os.path.join(SCRIPTS, 'md-rule-gate.py'))
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


class Normalize(unittest.TestCase):
    def test_markdown_decoration_and_case_are_stripped(self):
        self.assertEqual(gate.normalize('**Never** push to `prod`'), 'never push to prod')

    def test_emoji_and_punctuation_go(self):
        self.assertEqual(gate.normalize('⚠️ never — really!'), 'never really')

    def test_paths_and_colons_survive_because_they_are_the_substance(self):
        self.assertIn('docs/decision-log.md', gate.normalize('see `docs/decision-log.md`'))

    def test_whitespace_collapses(self):
        self.assertEqual(gate.normalize('a   \n  b'), 'a b')


class NeverDoItems(unittest.TestCase):
    def test_only_lines_with_the_marker_count(self):
        text = '- ❌ never push straight to prod\n- a plain bullet\n'
        items = gate.never_do_items(text)
        self.assertEqual(1, len(items))
        self.assertIn('never push straight to prod', items[0][1])

    def test_a_too_short_item_is_ignored(self):
        # Under 12 normalized characters there is not enough substance to match on.
        self.assertEqual([], gate.never_do_items('- ❌ no\n'))


class RuleLines(unittest.TestCase):
    def test_an_uppercase_label_is_a_rule(self):
        self.assertTrue(gate.rule_lines('This is MANDATORY for every project\n'))

    def test_plain_prohibitive_prose_is_also_a_rule(self):
        # Blind spot 1: most rules carry no label, they carry a mood.
        for line in ('no direct push to `test`/`prod`\n',
                     'business logic must live in the API\n',
                     'the client cannot decide authorization\n',
                     "don't commit dead code that is commented out\n"):
            self.assertTrue(gate.rule_lines(line), f'not recognised as a rule: {line!r}')

    def test_an_ordinary_sentence_is_not_a_rule(self):
        self.assertEqual([], gate.rule_lines('This document describes the layout.\n'))


class Identifiers(unittest.TestCase):
    def test_a_path_is_an_identifier(self):
        self.assertIn('docs/decision-log.md', gate.identifiers('see `docs/decision-log.md`'))

    def test_camel_case_is_an_identifier(self):
        self.assertIn('AddScoped', gate.identifiers('call `AddScoped` here'))

    def test_a_plain_backticked_word_is_not(self):
        self.assertEqual(set(), gate.identifiers('the `dev` branch'))

    def test_a_flag_is_an_identifier(self):
        self.assertIn('--no-verify', gate.identifiers('never pass `--no-verify`'))


class MatchingLine(unittest.TestCase):
    def test_an_exact_containment_wins(self):
        needle = 'never push straight to prod'
        lines = ['unrelated text', 'never push straight to prod ever']
        self.assertEqual('never push straight to prod ever', gate.matching_line(needle, lines))

    def test_a_reformatted_sentence_still_matches_through_a_window(self):
        # The windows are CONTIGUOUS word runs taken from the old line, so a
        # rewrite that keeps a run of the wording matches even though the
        # sentence as a whole changed. A rewrite that reorders every word does
        # not — checked below, because that boundary is the behaviour, not a bug:
        # a window loose enough to survive reordering would match unrelated text.
        needle = 'the api checks authorization on every endpoint and the ui check is ux only'
        kept_run = ['in every case the api checks authorization on every endpoint, ui aside']
        self.assertIsNotNone(gate.matching_line(needle, kept_run))

    def test_a_sentence_with_no_contiguous_run_left_does_not_match(self):
        needle = 'the api checks authorization on every endpoint and the ui check is ux only'
        reordered = ['authorization is verified server-side; interface hints are cosmetic']
        self.assertIsNone(gate.matching_line(needle, reordered))

    def test_nothing_similar_returns_none(self):
        self.assertIsNone(gate.matching_line('never push straight to prod', ['completely different']))

    def test_the_closest_length_wins_not_the_longest(self):
        # The regression the comment records: taking the LONGEST match let an
        # unrelated long item's historical prose supply a false negation.
        needle = 'never push straight to prod'
        short = 'never push straight to prod'
        long = 'never push straight to prod ' + 'x' * 400
        self.assertEqual(short, gate.matching_line(needle, [long, short]))


class IsLost(unittest.TestCase):
    def test_a_deleted_rule_is_lost(self):
        raw, normalized = '- ❌ never push straight to prod', 'never push straight to prod'
        self.assertEqual('LOST', gate.is_lost(raw, normalized, ['something else entirely']))

    def test_a_surviving_rule_is_not_lost(self):
        normalized = 'never push straight to prod'
        self.assertIsNone(gate.is_lost('x', normalized, [normalized]))

    def test_an_inverted_rule_is_caught(self):
        # Blind spot 2: the text is present, with a negation appended.
        normalized = 'never push straight to prod'
        reason = gate.is_lost('x', normalized, ['never push straight to prod no longer valid'])
        self.assertIsNotNone(reason)
        self.assertIn('INVERTED', reason)

    def test_a_truncated_rule_is_caught(self):
        # Blind spot 3: the body is gone, the opening words remain.
        normalized = ('never push straight to prod because the promotion belongs to the user '
                      'and the gate has to have run first')
        reason = gate.is_lost('x', normalized, ['never push straight to prod'])
        self.assertIsNotNone(reason)
        self.assertIn('TRUNCATED', reason)

    def test_a_triaged_rule_is_exempt(self):
        normalized = 'never push straight to prod'
        triage = {normalized[:60]: 'proven wrong in the code on 01/01/2026'}
        self.assertIsNone(gate.is_lost('x', normalized, ['nothing like it'], triage))


class RuleTriage(unittest.TestCase):
    def setUp(self):
        self.original = gate._triage_file

    def tearDown(self):
        gate._triage_file = self.original

    def use(self, data):
        handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(data, handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        import pathlib
        gate._triage_file = lambda: pathlib.Path(handle.name)

    def test_an_entry_with_a_reason_is_an_exemption(self):
        self.use({'rule': {'some key': 'a real reason'}})
        self.assertEqual({'some key': 'a real reason'}, gate.rule_triage())

    def test_an_empty_reason_is_NOT_an_exemption(self):
        # An exemption is granted to a value AND must carry a reason.
        self.use({'rule': {'some key': '   '}})
        self.assertEqual({}, gate.rule_triage())

    def test_a_non_string_reason_is_not_an_exemption(self):
        self.use({'rule': {'some key': True}})
        self.assertEqual({}, gate.rule_triage())

    def test_no_rule_section_means_no_exemptions(self):
        self.use({'other': {}})
        self.assertEqual({}, gate.rule_triage())


class Main(unittest.TestCase):
    """main() is exercised directly so the measurement lands on this file."""

    def setUp(self):
        self.argv = sys.argv
        # ⚠️ BOTH module attributes are saved and restored. One test replaces
        # `rule_triage` and an earlier version of this class restored only
        # `_triage_file`, so the stub leaked into whatever ran next. pytest's
        # ordering happened to hide it; `unittest discover` — which
        # scripts/coverage.sh uses — ran RuleTriage afterwards and it failed.
        # A test that mutates a module and does not put it back is a test that
        # reports on its neighbours.
        self.triage_file = gate._triage_file
        self.rule_triage = gate.rule_triage
        gate._triage_file = lambda: None      # no triage unless a test installs one

    def tearDown(self):
        sys.argv = self.argv
        gate._triage_file = self.triage_file
        gate.rule_triage = self.rule_triage

    def write(self, text):
        handle = tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8')
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def run_main(self, old, new):
        sys.argv = ['md-rule-gate.py', self.write(old), self.write(new)]
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = gate.main()
        return buffer.getvalue(), code

    def test_wrong_argument_count_prints_the_usage(self):
        sys.argv = ['md-rule-gate.py']
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(2, gate.main())
        self.assertIn('Usage', buffer.getvalue())

    def test_an_unchanged_file_passes(self):
        text = '- ❌ never push straight to prod\nEvery endpoint must check authorization.\n'
        out, code = self.run_main(text, text)
        self.assertEqual(0, code, out)
        self.assertIn('Gate passed', out)

    def test_moving_content_to_an_archive_passes(self):
        old = '- ❌ never push straight to prod\n'
        new = '# Rules\n\n- ❌ never push straight to prod\n\n(history moved to the archive)\n'
        out, code = self.run_main(old, new)
        self.assertEqual(0, code, out)

    def test_a_lost_never_do_item_breaks_the_gate(self):
        out, code = self.run_main('- ❌ never push straight to prod\n', '# Rules\n\nnothing here\n')
        self.assertEqual(1, code)
        self.assertIn('LOST/BROKEN NEVER-DO ITEM', out)
        self.assertIn('GATE BROKEN', out)

    def test_a_lost_rule_line_breaks_the_gate(self):
        out, code = self.run_main('Every endpoint must check authorization in the backend.\n',
                                  '# Rules\n\nsomething unrelated entirely\n')
        self.assertEqual(1, code)
        self.assertIn('LOST/BROKEN RULE LINE', out)

    def test_a_dropped_identifier_breaks_the_gate(self):
        out, code = self.run_main('Rules must live in `docs/decision-log.md` and never move.\n',
                                  'Rules must live in the log and never move.\n')
        self.assertEqual(1, code)
        self.assertIn('IDENTIFIER DROPPED WITHOUT A REASON', out)

    def test_the_summary_counts_are_printed(self):
        text = '- ❌ never push straight to prod\n'
        out, _ = self.run_main(text, text)
        for label in ('lines', 'size', 'items', 'rule lines', 'identifiers'):
            self.assertIn(label, out)

    def test_an_identifier_with_a_reason_is_reported_not_failed(self):
        import pathlib
        new_path = self.write('Rules live in the log.\n')
        old_path = self.write('Rules must live in `docs/old-log.md` and never move.\n')
        handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
        json.dump({'*': {'docs/old-log.md': 'moved to the archive on 01/01/2026'}}, handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        gate._triage_file = lambda: pathlib.Path(handle.name)
        sys.argv = ['md-rule-gate.py', old_path, new_path]
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = gate.main()
        out = buffer.getvalue()
        self.assertIn('Identifiers moved with a reason', out)
        self.assertNotIn('IDENTIFIER DROPPED WITHOUT A REASON', out)

    def test_an_unreadable_triage_file_does_NOT_loosen_the_gate(self):
        import pathlib
        handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
        handle.write('{ not json at all')
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        old_path = self.write('Rules must live in `docs/old-log.md` and never move.\n')
        new_path = self.write('Rules live in the log.\n')
        gate.rule_triage = lambda: {}
        gate._triage_file = lambda: pathlib.Path(handle.name)
        sys.argv = ['md-rule-gate.py', old_path, new_path]
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = gate.main()
        self.assertEqual(1, code)
        self.assertIn('triage file could not be read', buffer.getvalue())


if __name__ == '__main__':
    unittest.main()
