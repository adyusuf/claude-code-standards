"""The two-layer splitter (scripts/md-split.py) — 84 statements, previously 0%.

Its whole promise is that it MOVES content and never rewrites it: the detail file
gets every item verbatim and in full, and only lines carrying no rule marker drop
out of the active file. That promise is what these tests pin — especially the
invariant that **nothing is ever paraphrased**, because paraphrase is the common
route to rule loss and md-rule-gate.py would then refuse the result.
"""
import importlib.util
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
_spec = importlib.util.spec_from_file_location('md_split', os.path.join(SCRIPTS, 'md-split.py'))
split = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(split)


class Slug(unittest.TestCase):
    def test_turkish_letters_are_folded(self):
        self.assertEqual('sisman-istanbul', split.slug('Şişman İstanbul'))

    def test_punctuation_goes_and_spaces_become_dashes(self):
        self.assertEqual('never-push-to-prod', split.slug('Never push to prod!'))

    def test_it_is_capped_and_never_ends_in_a_dash(self):
        result = split.slug('word ' * 40)
        self.assertLessEqual(len(result), 60)
        self.assertFalse(result.endswith('-'))

    def test_an_empty_title_still_produces_an_anchor(self):
        self.assertEqual('decision', split.slug('!!!'))


class TitleOf(unittest.TestCase):
    def test_bold_text_becomes_the_title(self):
        self.assertEqual('Small step first', split.title_of('- **Small step first:** do it'))

    def test_without_bold_the_first_line_is_used(self):
        self.assertEqual('a plain item', split.title_of('- a plain item\n  more text'))

    def test_a_multiline_bold_title_is_collapsed_to_one_line(self):
        self.assertEqual('two words', split.title_of('- **two\n  words**'))


class ItemsOf(unittest.TestCase):
    def test_each_dash_starts_an_item_and_keeps_its_body(self):
        items = split.items_of('- first\n  body of first\n- second\n')
        self.assertEqual(2, len(items))
        self.assertIn('body of first', items[0])

    def test_text_before_the_first_item_is_not_an_item(self):
        self.assertEqual(1, len(split.items_of('intro prose\n- only item\n')))

    def test_no_items_gives_an_empty_list(self):
        self.assertEqual([], split.items_of('just prose\n'))


class IsKept(unittest.TestCase):
    def test_a_rule_line_stays(self):
        self.assertTrue(split.is_kept('- the client must never decide authorization'))

    def test_a_line_with_an_identifier_stays_even_with_no_rule_word(self):
        # `MemberTierInfo.HiddenTiers` carries no marker but IS the rule.
        self.assertTrue(split.is_kept('  see `docs/decision-log.md` for the table'))
        self.assertTrue(split.is_kept('  the field is `MemberTierInfo.HiddenTiers`'))

    def test_pure_narrative_drops(self):
        self.assertFalse(split.is_kept('  We discovered this while reviewing a PR.'))

    def test_a_blank_line_drops(self):
        self.assertFalse(split.is_kept('   '))

    def test_the_pattern_matches_md_rule_gate(self):
        # The two tools are twins on purpose: if the splitter drops what the gate
        # protects, the gate breaks — and is right to.
        rule_gate_spec = importlib.util.spec_from_file_location(
            'md_rule_gate_twin', os.path.join(SCRIPTS, 'md-rule-gate.py'))
        twin = importlib.util.module_from_spec(rule_gate_spec)
        rule_gate_spec.loader.exec_module(twin)
        for line in ('every endpoint must check authorization',
                     "don't commit dead code",
                     'no direct push to prod',
                     'this is MANDATORY'):
            self.assertTrue(split.RULE.search(line), line)
            self.assertTrue(twin.RULE_MARKER.search(line), line)


class Main(unittest.TestCase):
    SOURCE = '''# Title

## Permanent decisions

- **Small step first:** a large refactor must be proposed first.
  We found this out the hard way during a migration.
  It cost two days.
- **Never push to prod:** the promotion belongs to the user.
  This came from an incident in March.

## Another section

untouched text
'''

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.argv = sys.argv
        self.source = pathlib.Path(self.dir) / 'CLAUDE.md'
        self.source.write_text(self.SOURCE, encoding='utf-8')
        self.detail = pathlib.Path(self.dir) / 'docs' / 'detail.md'

    def tearDown(self):
        sys.argv = self.argv
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_main(self, heading='## Permanent decisions'):
        sys.argv = ['md-split.py', str(self.source), heading, str(self.detail), 'docs/detail.md']
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = split.main()
        return buffer.getvalue(), code

    def test_wrong_argument_count_prints_the_usage(self):
        sys.argv = ['md-split.py', 'one']
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(2, split.main())
        self.assertIn('Usage', buffer.getvalue())

    def test_a_heading_that_is_not_there_is_an_error(self):
        out, code = self.run_main('## No Such Section')
        self.assertEqual(1, code)
        self.assertIn('not found', out)

    def test_a_section_with_no_items_is_an_error(self):
        out, code = self.run_main('## Another section')
        self.assertEqual(1, code)
        self.assertIn('no items found', out)

    def test_the_detail_file_gets_every_item_VERBATIM(self):
        # The promise of the whole tool. Not "roughly", verbatim.
        out, code = self.run_main()
        self.assertEqual(0, code, out)
        detail = self.detail.read_text(encoding='utf-8')
        for sentence in ('We found this out the hard way during a migration.',
                         'It cost two days.',
                         'This came from an incident in March.'):
            self.assertIn(sentence, detail, f'lost from the detail file: {sentence!r}')

    def test_narrative_leaves_the_active_file_and_rules_stay(self):
        self.run_main()
        active = self.source.read_text(encoding='utf-8')
        self.assertIn('Small step first', active)
        self.assertIn('Never push to prod', active)
        self.assertNotIn('It cost two days.', active)

    def test_a_link_to_the_detail_is_left_behind_for_each_item(self):
        self.run_main()
        active = self.source.read_text(encoding='utf-8')
        self.assertEqual(2, active.count('[rationale & history](docs/detail.md#'))

    def test_the_other_section_is_untouched(self):
        self.run_main()
        self.assertIn('## Another section\n\nuntouched text', self.source.read_text(encoding='utf-8'))

    def test_duplicate_titles_get_distinct_anchors(self):
        self.source.write_text('# T\n\n## S\n\n- **Same:** one must stay\n- **Same:** two must stay\n',
                               encoding='utf-8')
        sys.argv = ['md-split.py', str(self.source), '## S', str(self.detail), 'docs/detail.md']
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, split.main())
        active = self.source.read_text(encoding='utf-8')
        self.assertIn('#same)', active)
        self.assertIn('#same-2)', active)

    def test_an_item_that_is_all_narrative_keeps_its_first_line(self):
        # Otherwise the item would vanish from the active file entirely.
        self.source.write_text('# T\n\n## S\n\n- Something happened once.\n  And then more prose.\n',
                               encoding='utf-8')
        sys.argv = ['md-split.py', str(self.source), '## S', str(self.detail), 'docs/detail.md']
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, split.main())
        self.assertIn('Something happened once.', self.source.read_text(encoding='utf-8'))

    def test_the_summary_reports_what_moved(self):
        out, _ = self.run_main()
        for label in ('items', 'lines dropped', 'detail file', 'active file'):
            self.assertIn(label, out)

    def test_the_detail_directory_is_created_if_missing(self):
        self.assertFalse(self.detail.parent.exists())
        self.run_main()
        self.assertTrue(self.detail.exists())


if __name__ == '__main__':
    unittest.main()
