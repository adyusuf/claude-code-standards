"""scripts/adyusuf_page.py — the Session Settings page is built from the template and the live configuration."""
import contextlib
import datetime
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, SCRIPTS)
_spec = importlib.util.spec_from_file_location('adyusuf_page', os.path.join(SCRIPTS, 'adyusuf_page.py'))
page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(page)

NOW = datetime.datetime(2026, 10, 23, 21, 49)


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {'ADYUSUF_CONFIG_USER': os.path.join(self.tmp.name, 'user.json'),
               'ADYUSUF_SESSION_DIR': os.path.join(self.tmp.name, 'sessions')}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        project = mock.patch.object(page.cfg, 'project_file', return_value=os.path.join(self.tmp.name, 'project.json'))
        project.start()
        self.addCleanup(project.stop)

    def embedded(self, text):
        match = re.search(r'<script id="data" type="application/json">(.*?)</script>', text, re.S)
        self.assertIsNotNone(match)
        return json.loads(match.group(1))


class Build(Isolated):
    def test_the_page_carries_the_session_the_schema_the_values_and_the_agents(self):
        text = page.build('sess-1', NOW)
        data = self.embedded(text)
        self.assertEqual('sess-1', data['session'])
        self.assertEqual('23/10/2026 21:49', data['made'])
        self.assertEqual(len(page.cfg.SCHEMA), len(data['schema']))
        self.assertIn('push.prod', data['values'])
        self.assertEqual({'default'}, set(data['sources'].values()))
        self.assertEqual(14, len(data['agents']))
        self.assertNotIn(page.PLACEHOLDER, text)

    def test_a_session_override_shows_with_its_source(self):
        page.cfg.write_layer(page.sessions.session_file('sess-1'), {'push.prod': False})
        data = self.embedded(page.build('sess-1', NOW))
        self.assertEqual((False, 'session'), (data['values']['push.prod'], data['sources']['push.prod']))
        other = self.embedded(page.build('sess-2', NOW))
        self.assertEqual((True, 'default'), (other['values']['push.prod'], other['sources']['push.prod']))

    def test_an_unusable_session_id_is_refused(self):
        for bad in ('../x', '', 'a b'):
            with self.assertRaises(ValueError):
                page.build(bad)

    def test_the_template_must_hold_the_placeholder_exactly_once(self):
        for body in ('<title>x</title>', '__DATA__ __DATA__'):
            path = os.path.join(self.tmp.name, 't.html')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(body)
            with mock.patch.object(page, 'TEMPLATE', path), self.assertRaises(ValueError):
                page.build('sess-1')

    def test_the_real_template_sends_one_comment_and_writes_nothing_itself(self):
        text = page.build('sess-1', NOW)
        self.assertIn('sendToClaude', text)
        self.assertIn('canSendToClaude', text)
        for forbidden in ('fetch(', 'XMLHttpRequest', 'localStorage', 'document.cookie', 'eval('):
            self.assertNotIn(forbidden, text)


class Embed(unittest.TestCase):
    def test_nothing_can_close_the_script_element_or_end_a_js_string(self):
        text = page.embed({'a': '</script><script>alert(1)</script><!--', 'b': 'x y z'})
        self.assertNotIn('<', text)
        self.assertNotIn(' ', text)
        self.assertNotIn(' ', text)
        self.assertEqual({'a': '</script><script>alert(1)</script><!--', 'b': 'x y z'}, json.loads(text))


class Promotion(unittest.TestCase):
    def test_the_stages_follow_dev_test_prod_with_the_waived_lines_on_the_way_in(self):
        answers = {
            ('rev-parse', '--short', 'origin/dev'): 'aaa1111',
            ('rev-parse', '--short', 'origin/test'): 'bbb2222',
            ('rev-parse', '--short', 'origin/prod'): 'ccc3333',
            ('log', '--format=%B', 'origin/test..origin/dev'): 'x\nGate-Waived: gates (neden: configuration)\nGate-Waived: gates (neden: configuration)\ny',
            ('log', '--format=%B', 'origin/prod..origin/test'): 'Gate-Waived: ci (neden: configuration)',
        }
        with mock.patch.object(page, 'git', side_effect=lambda args: answers.get(tuple(args), '')):
            stages = page.promotion()
        self.assertEqual(['dev', 'test', 'prod'], [s['branch'] for s in stages])
        self.assertEqual([[], ['Gate-Waived: gates (neden: configuration)'], ['Gate-Waived: ci (neden: configuration)']],
                         [s['waived'] for s in stages])

    def test_a_missing_branch_is_left_out_and_no_repository_gives_no_stages(self):
        with mock.patch.object(page, 'git', return_value=''):
            self.assertEqual([], page.promotion())

    def test_git_that_fails_or_is_missing_answers_an_empty_string(self):
        with mock.patch.object(page.subprocess, 'run', side_effect=OSError('no git')):
            self.assertEqual('', page.git(['status']))
        self.assertEqual('', page.git(['rev-parse', '--verify', 'no-such-ref-at-all']))


class Cli(Isolated):
    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = page.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_build_to_a_file_reports_the_size(self):
        path = os.path.join(self.tmp.name, 'page.html')
        code, out, _ = self.run_main('build', '--session', 'sess-1', '--out', path)
        self.assertEqual(0, code)
        self.assertIn('bytes', out)
        with open(path, encoding='utf-8') as handle:
            self.assertIn('<title>Session Settings</title>', handle.read())

    def test_build_without_out_prints_the_page(self):
        code, out, _ = self.run_main('build', '--session', 'sess-1')
        self.assertEqual(0, code)
        self.assertIn('Session Settings', out)

    def test_a_bad_session_is_exit_two_and_prints_nothing(self):
        code, out, err = self.run_main('build', '--session', '../x')
        self.assertEqual((2, ''), (code, out))
        self.assertIn('not a usable session id', err)


if __name__ == '__main__':
    unittest.main()
