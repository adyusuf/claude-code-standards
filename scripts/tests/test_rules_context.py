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
import shutil
import subprocess
import sys
import tempfile
import unittest
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

    def test_every_hook_of_an_event_sees_the_same_parts(self):
        # Parts depend on text, mode and <registered> (the WARNING is part of the measured
        # output); all hooks of one event pass the same <registered>, so they agree.
        text = quote_heavy_text()
        for mode in ('session', 'subagent'):
            first = rc.mode_parts(text, mode, 4)
            self.assertEqual(first, rc.mode_parts(text, mode, 4), mode)
            for part in range(1, 5):
                code, _, _ = run_main([mode, str(part), '4'])
                self.assertEqual(code, 0)

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


class Main(unittest.TestCase):
    def test_session_prints_the_rendered_part_as_plain_text(self):
        code, out, _ = run_main(['session', '2', '4'])
        self.assertEqual(code, 0)
        self.assertEqual(out, rc.render(SESSION_PARTS, 2, 4))

    def test_subagent_prints_json_with_the_event_name_and_the_part_text(self):
        code, out, _ = run_main(['subagent', '2', '4'])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(list(payload), ['hookSpecificOutput'])
        self.assertEqual(payload['hookSpecificOutput']['hookEventName'], 'SubagentStart')
        self.assertEqual(payload['hookSpecificOutput']['additionalContext'], rc.render(SUBAGENT_PARTS, 2, 4))

    def test_unreadable_rules_exit_1_and_print_nothing_to_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run_main(['session', '1', '4'], rules_path=os.path.join(tmp, 'missing.md'))
        self.assertEqual(code, 1)
        self.assertEqual(out, '')
        self.assertIn('cannot read the global rules', err)

    def test_a_part_past_the_end_exits_0_and_prints_nothing(self):
        for mode in ('session', 'subagent'):
            code, out, _ = run_main([mode, '4', '4'], rules_path=self.two_part_rules())
            self.assertEqual((code, out), (0, ''), mode)

    def two_part_rules(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, 'CLAUDE.md')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('## A\n' + 'a' * 9000 + '\n## B\nb\n')
        return path


class Cli(unittest.TestCase):
    def test_session_1_prints_the_part_header(self):
        code, out, err = run_cli('session', '1', '4')
        self.assertEqual(code, 0, err)
        self.assertTrue(out.startswith(f'[Global working rules, part 1/{len(REAL_PARTS)} '), out[:80])
        self.assertIn(REAL_PARTS[0][:200], out)

    def test_subagent_2_prints_valid_json_with_the_part_two_text(self):
        code, out, err = run_cli('subagent', '2', '4')
        self.assertEqual(code, 0, err)
        context = json.loads(out)['hookSpecificOutput']
        self.assertEqual(context['hookEventName'], 'SubagentStart')
        self.assertEqual(context['additionalContext'], rc.render(SUBAGENT_PARTS, 2, 4))

    def test_a_part_past_the_end_prints_nothing_and_exits_0(self):
        code, out, err = run_cli('session', str(len(REAL_PARTS) + 1), str(len(REAL_PARTS) + 1))
        self.assertEqual((code, out), (0, ''), err)

    def test_bad_usage_exits_2_with_a_usage_line(self):
        cases = [('foo', '1', '4'), ('session', 'x', '4'), ('session', '1', 'x'),
                 ('session', '1'), ('session', '1', '4', 'extra'), ()]
        for args in cases:
            code, out, err = run_cli(*args)
            self.assertEqual(code, 2, args)
            self.assertEqual(out, '', args)
            self.assertIn('usage: rules-context.py', err, args)

    def test_a_part_outside_one_to_registered_exits_2(self):
        for args in (('session', '0', '4'), ('session', '5', '4'), ('subagent', '0', '4'), ('subagent', '5', '4')):
            code, out, err = run_cli(*args)
            self.assertEqual(code, 2, args)
            self.assertEqual(out, '', args)
            self.assertIn('outside 1..4', err, args)

    def test_a_copy_without_a_claude_md_next_to_it_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = os.path.join(tmp, 'scripts')
            os.makedirs(scripts)
            copy = os.path.join(scripts, 'rules-context.py')
            shutil.copy(SCRIPT, copy)
            code, out, err = run_cli('session', '1', '4', script=copy)
        self.assertEqual((code, out), (1, ''))
        self.assertIn('cannot read the global rules', err)


class Registration(unittest.TestCase):
    """The tripwire: when CLAUDE.md grows past what the registered hooks can print, a
    maintainer must register another hook (hooks/hooks.json) — this fails first."""

    def test_the_rules_need_no_more_parts_per_mode_than_hooks_register_per_event(self):
        with open(HOOKS, encoding='utf-8') as handle:
            events = json.load(handle)['hooks']
        self.assertEqual(sorted(events), ['SessionStart', 'SubagentStart'])
        modes = {'SessionStart': 'session', 'SubagentStart': 'subagent'}
        for event, groups in events.items():
            registered = sum(len(group['hooks']) for group in groups)
            needed = len(rc.mode_parts(REAL_TEXT, modes[event], registered))
            self.assertLessEqual(needed, registered,
                                 f'CLAUDE.md needs {needed} {modes[event]} parts but {event} registers {registered}: '
                                 'add a hook (and bump <registered> in every command) in hooks/hooks.json')


if __name__ == '__main__':
    unittest.main()
