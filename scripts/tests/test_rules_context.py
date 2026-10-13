"""The rules loader (scripts/rules-context.py): the plugin cannot ship a CLAUDE.md, so
two hooks print it in parts instead. What these tests pin is that NOTHING is lost and
NOTHING is oversize: the parts re-join to the exact text, every emitted hook output
stays under Claude Code's 10,000-character cap, and a CLAUDE.md that outgrows the
registered hooks is caught here (and warned about at run time) rather than silently cut.
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules_context_helpers import (REAL_PARTS, REAL_TEXT, REPO, quote_heavy_text, rc, run_main,  # noqa: E402
                                   synthetic_text)


def is_boundary(line):
    return bool(rc.BOUNDARY.match(line))


class Blocks(unittest.TestCase):
    def test_cut_before_headings_and_numbered_rules_including_ranges(self):
        text = 'intro\n## A\nbody\n26. rule\ncont\n21-23. range\n### sub\n'
        self.assertEqual(rc.blocks(text),
                         ['intro\n', '## A\nbody\n', '26. rule\ncont\n', '21-23. range\n### sub\n'])

    def test_non_boundaries_stay_inside_their_block(self):
        text = '## A\n### sub\n1.5 not a rule\n- 3. nested\n#2 tag\n'
        self.assertEqual(rc.blocks(text), [text])

    def test_joined_blocks_equal_the_text_and_empty_text_has_none(self):
        self.assertEqual(''.join(rc.blocks(REAL_TEXT)), REAL_TEXT)
        self.assertEqual(rc.blocks(''), [])


class SplitLines(unittest.TestCase):
    def test_cut_at_line_ends_within_the_limit(self):
        pieces = rc.split_lines('aaaa\nbbbb\ncccc\n', 10)
        self.assertEqual(pieces, ['aaaa\nbbbb\n', 'cccc\n'])

    def test_a_line_longer_than_the_limit_is_cut_hard_and_loses_nothing(self):
        block = 'ab\n' + 'z' * 25 + '\ncd\n'
        pieces = rc.split_lines(block, 10)
        self.assertEqual(''.join(pieces), block)
        self.assertTrue(all(len(piece) <= 10 for piece in pieces), [len(p) for p in pieces])


class Parts(unittest.TestCase):
    def test_real_parts_are_lossless_and_in_order(self):
        self.assertEqual(''.join(REAL_PARTS), REAL_TEXT)

    def test_real_parts_respect_the_part_limit(self):
        self.assertGreaterEqual(len(REAL_PARTS), 2, 'CLAUDE.md is expected to need several parts')
        for number, part in enumerate(REAL_PARTS, 1):
            self.assertLessEqual(len(part), rc.PART_LIMIT, f'part {number}')

    def test_every_real_part_after_the_first_starts_on_a_boundary(self):
        for number, part in enumerate(REAL_PARTS[1:], 2):
            first_line = part.splitlines()[0]
            self.assertTrue(is_boundary(first_line), f'part {number} starts mid-block: {first_line[:60]!r}')

    def test_synthetic_parts_are_lossless_and_within_the_limit(self):
        text = synthetic_text()
        pieces = rc.parts(text)
        self.assertEqual(''.join(pieces), text)
        self.assertGreater(len(pieces), 3)
        self.assertTrue(all(len(piece) <= rc.PART_LIMIT for piece in pieces), [len(p) for p in pieces])

    def test_small_blocks_are_packed_greedily_not_one_per_part(self):
        self.assertEqual(rc.parts('## A\nxx\n## B\nyy\n## C\nzz\n', limit=18), ['## A\nxx\n## B\nyy\n', '## C\nzz\n'])

    def test_empty_text_has_no_parts(self):
        self.assertEqual(rc.parts(''), [])


class Render(unittest.TestCase):
    def test_a_part_past_the_end_is_empty(self):
        self.assertEqual(rc.render(['a\n', 'b\n'], 3, 4), '')

    def test_header_names_the_part_and_total_then_the_part_text(self):
        out = rc.render(['a\n', 'b\n', 'c\n'], 2, 4)
        self.assertTrue(out.startswith('[Global working rules, part 2/3 '), out)
        self.assertTrue(out.endswith('\nb\n'), out)

    def test_only_the_last_registered_part_carries_the_warning_when_parts_exceed_hooks(self):
        pieces = ['a\n', 'b\n', 'c\n', 'd\n']
        for part in (1, 2):
            self.assertNotIn('WARNING', rc.render(pieces, part, 3), f'part {part}')
        last = rc.render(pieces, 3, 3)
        self.assertIn('WARNING', last)
        self.assertIn('need 4 parts but only 3 hooks', last)
        self.assertNotIn('WARNING', rc.render(pieces, 4, 4))

    def test_no_warning_when_the_parts_fit_the_registered_hooks(self):
        pieces = ['a\n', 'b\n']
        for registered in (2, 3, 4):
            for part in range(1, registered + 1):
                self.assertNotIn('WARNING', rc.render(pieces, part, registered), f'{part}/{registered}')


class Limits(unittest.TestCase):
    def assert_all_outputs_under_limit(self, text):
        """Every hook of an event printed for registered < parts needed (the last one carries
        the WARNING), == parts needed, and > parts needed."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'CLAUDE.md')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(text)
            for mode in ('session', 'subagent'):
                needed = len(rc.mode_parts(text, mode, 50))
                self.assertGreaterEqual(needed, 2, 'the text must need several parts to cover registered < parts')
                for registered in (1, needed - 1, needed, 50):
                    printed = len(rc.mode_parts(text, mode, registered))
                    for part in range(1, min(printed, registered) + 1):
                        code, out, _ = run_main([mode, str(part), str(registered)], rules_path=path)
                        self.assertEqual(code, 0)
                        self.assertLess(len(out), rc.HOOK_LIMIT,
                                        f'{mode} part {part}, {registered} registered: printed {len(out)} characters')

    def test_rendered_text_including_header_is_under_the_cap_for_the_real_rules(self):
        for number in range(1, len(REAL_PARTS) + 1):
            self.assertLess(len(rc.render(REAL_PARTS, number, len(REAL_PARTS))), rc.HOOK_LIMIT, f'part {number}')

    def test_rendered_text_is_under_the_cap_for_oversize_blocks_and_lines(self):
        pieces = rc.parts(synthetic_text())
        for number in range(1, len(pieces) + 1):
            self.assertLess(len(rc.render(pieces, number, len(pieces))), rc.HOOK_LIMIT, f'part {number}')

    def test_what_is_actually_printed_is_under_the_cap_for_the_real_rules_in_both_modes(self):
        # The JSON mode escapes newlines and non-ASCII (\n, ⚠), so the bytes written
        # are more than the text rendered — it is the printed size that counts.
        self.assert_all_outputs_under_limit(REAL_TEXT)

    def test_what_is_actually_printed_is_under_the_cap_for_oversize_blocks_and_lines_in_both_modes(self):
        self.assert_all_outputs_under_limit(synthetic_text())


class Output(unittest.TestCase):
    def test_session_is_the_rendered_text(self):
        pieces = ['a\n', 'b\n']
        self.assertEqual(rc.output('session', pieces, 2, 2), rc.render(pieces, 2, 2))

    def test_subagent_is_json_with_non_ascii_written_literally(self):
        pieces = ['warn \u26a0 \u2192 "q"\n']
        out = rc.output('subagent', pieces, 1, 4)
        self.assertIn('\u26a0', out)
        self.assertIn('\u2192', out)
        self.assertNotIn('\\u26a0', out)
        self.assertEqual(json.loads(out)['hookSpecificOutput'],
                         {'hookEventName': 'SubagentStart', 'additionalContext': rc.render(pieces, 1, 4)})

    def test_a_part_past_the_end_is_empty_in_both_modes(self):
        for mode in ('session', 'subagent'):
            self.assertEqual(rc.output(mode, ['a\n'], 2, 4), '', mode)


class ModeParts(unittest.TestCase):
    """The JSON envelope escapes quotes and newlines, so the subagent parts shrink."""

    def test_session_parts_are_the_unshrunk_parts(self):
        text = quote_heavy_text()
        self.assertEqual(rc.mode_parts(text, 'session', 4), rc.parts(text))
        self.assertEqual(len(rc.parts(text)), 1)

    def test_subagent_parts_are_smaller_more_lossless_and_every_printed_output_fits(self):
        text = quote_heavy_text()
        session = rc.mode_parts(text, 'session', 4)
        subagent = rc.mode_parts(text, 'subagent', 4)
        self.assertGreater(len(subagent), len(session))
        self.assertEqual(''.join(subagent), text)
        # the unshrunk single part really is too big once enveloped (else this proves nothing)
        self.assertGreaterEqual(len(rc.output('subagent', session, 1, 4)), rc.HOOK_LIMIT)
        for number in range(1, len(subagent) + 1):
            self.assertLess(len(rc.output('subagent', subagent, number, 4)), rc.HOOK_LIMIT, number)

    def test_the_overflow_warning_is_counted_when_fewer_hooks_are_registered_than_parts_needed(self):
        # Regression: measuring with max(registered, len(cut)) never counted the WARNING that
        # the last registered part carries, so that part printed 10,064 characters.
        long_path = os.path.join('x' * 700, 'CLAUDE.md')  # the WARNING names the rules path
        session_text = ''.join(f'## B{n}\n' + ('s' * 39 + '\n') * 235 for n in range(4))
        cases = [('subagent', quote_heavy_text(), 1), ('session', session_text, 2), ('subagent', session_text, 2)]
        for mode, text, registered in cases:
            with mock.patch.object(rc, 'RULES', long_path):
                cut = rc.mode_parts(text, mode, registered)
                self.assertGreater(len(cut), registered, f'{mode}: the text must overflow the hooks')
                self.assertEqual(''.join(cut), text)
                for part in range(1, registered + 1):
                    out = rc.output(mode, cut, part, registered)
                    self.assertLess(len(out), rc.HOOK_LIMIT, f'{mode} part {part}/{registered}: {len(out)} characters')
                self.assertIn('WARNING', rc.output(mode, cut, registered, registered))

    def test_the_shrink_stops_at_the_floor_instead_of_looping(self):
        # A limit below the floor can never be reached: each hook-output header alone is larger.
        with mock.patch.object(rc, 'HOOK_LIMIT', 50):
            pieces = rc.mode_parts('## A\n' + 'x\n' * 3000, 'session', 4)
        self.assertEqual(''.join(pieces), '## A\n' + 'x\n' * 3000)
        self.assertTrue(all(len(piece) <= 1000 for piece in pieces))


class HeaderRoot(unittest.TestCase):
    """The part header names the plugin root: the rules say `standards/...`, `modes/...`, and a model
    in any project can only open those if it is told what they are relative to (8707197)."""
    LONG_ROOT = os.path.join(os.sep + 'r' * 1000, 'cache', 'adyusuf')

    def test_the_root_is_the_directory_above_scripts_and_the_rules_are_its_claude_md(self):
        self.assertEqual(rc.ROOT, REPO)
        self.assertEqual(rc.RULES, os.path.join(REPO, 'CLAUDE.md'))

    def test_the_first_line_ends_with_the_root_in_both_modes(self):
        with mock.patch.object(rc, 'ROOT', '/cache/adyusuf'):
            session = rc.output('session', ['a\n'], 1, 4)
            subagent = json.loads(rc.output('subagent', ['a\n'], 1, 4))['hookSpecificOutput']['additionalContext']
        for text in (session, subagent):
            self.assertEqual(text.splitlines()[0],
                             '[Global working rules, part 1/1 (adyusuf plugin, CLAUDE.md); '
                             'relative paths start at /cache/adyusuf]')
            self.assertEqual(text.splitlines()[1], 'a')

    def test_the_overflow_warning_names_the_rules_file_not_only_the_root(self):
        with mock.patch.object(rc, 'ROOT', '/cache/adyusuf'), mock.patch.object(rc, 'RULES', '/cache/adyusuf/CLAUDE.md'):
            self.assertIn('read the rest in /cache/adyusuf/CLAUDE.md]', rc.render(['a\n', 'b\n'], 1, 1))

    def test_every_printed_real_part_stays_under_the_cap_in_both_modes_for_the_registered_four(self):
        for mode in ('session', 'subagent'):
            cut = rc.mode_parts(REAL_TEXT, mode, 4)
            self.assertLessEqual(len(cut), 4, mode)
            for part in range(1, 5):
                printed = rc.output(mode, cut, part, 4)
                self.assertLess(len(printed), rc.HOOK_LIMIT, f'{mode} part {part}')
                self.assertEqual(bool(printed), part <= len(cut), f'{mode} part {part}')

    def test_a_deep_cache_path_shrinks_the_parts_instead_of_overflowing_the_cap(self):
        # The header grows with the root, so the cut is measured WITH it: a 1,000-character root on the
        # 9,481-character part is past 10,000. Lossless, every output under the cap, and really smaller.
        with mock.patch.object(rc, 'ROOT', self.LONG_ROOT):
            for mode in ('session', 'subagent'):
                cut = rc.mode_parts(REAL_TEXT, mode, 8)
                self.assertEqual(''.join(cut), REAL_TEXT, mode)
                self.assertLess(max(map(len, cut)), max(map(len, REAL_PARTS)), mode)
                for part in range(1, len(cut) + 1):
                    self.assertLess(len(rc.output(mode, cut, part, 8)), rc.HOOK_LIMIT, f'{mode} part {part}')


if __name__ == '__main__':
    unittest.main()
