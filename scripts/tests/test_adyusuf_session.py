"""The session layer: what the rail boxes change applies to ONE session and is gone with it.

A new session has a new id, so it finds no file and starts from the saved defaults; the user's and the project's files
are never touched by a --session write.
"""
import importlib.util
import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_adyusuf_config as base  # noqa: E402

SCRIPTS = base.SCRIPTS

_spec = importlib.util.spec_from_file_location('adyusuf_session', os.path.join(SCRIPTS, 'adyusuf_session.py'))
sessions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sessions)


class SessionLayer(base.Tool):
    def value(self, key, *scope):
        out, _, code = self.run_tool('show', '--json', *scope)
        self.assertEqual(0, code)
        data = json.loads(out)
        return data['values'][key], data['sources'][key]

    def test_a_session_write_changes_that_session_only_and_touches_no_saved_file(self):
        out, _, code = self.run_tool('set', '--session', 'sess-1', 'push.prod', 'no')
        self.assertEqual(0, code)
        self.assertIn('push.prod = no', out)
        self.assertEqual((False, 'session'), self.value('push.prod', '--session', 'sess-1'))
        self.assertEqual((True, 'default'), self.value('push.prod'))                       # a new session
        self.assertEqual((True, 'default'), self.value('push.prod', '--session', 'sess-2'))   # another session
        self.assertFalse(os.path.exists(self.user))
        self.assertFalse(os.path.exists(self.project))

    def test_the_session_beats_the_project_beats_the_user(self):
        self.run_tool('set', 'push.test', 'no')
        self.run_tool('set', 'push.test', 'yes', '--project')
        self.run_tool('set', '--session', 's1', 'push.test', 'no')
        self.assertEqual((False, 'session'), self.value('push.test', '--session', 's1'))
        self.assertEqual((True, 'project'), self.value('push.test'))

    def test_a_later_change_of_the_saved_default_does_not_move_a_session_that_set_it(self):
        self.run_tool('set', '--session', 's1', 'push.dev', 'no')
        self.run_tool('set', 'push.dev', 'yes')
        self.assertEqual((False, 'session'), self.value('push.dev', '--session', 's1'))

    def test_unset_falls_back_to_the_saved_layer(self):
        self.run_tool('set', 'push.dev', 'no')
        self.run_tool('set', '--session', 's1', 'push.dev', 'yes')
        self.run_tool('unset', '--session', 's1', 'push.dev')
        self.assertEqual((False, 'user'), self.value('push.dev', '--session', 's1'))

    def test_apply_and_reset_agents_work_on_the_session_layer(self):
        _, _, code = self.run_tool('apply', '-', '--session', 's1', stdin=json.dumps({'gates_before_push': {'test': True}, 'agents.qa.enabled': 'on'}))
        self.assertEqual(0, code)
        self.assertEqual((True, 'session'), self.value('gates_before_push.test', '--session', 's1'))
        self.run_tool('reset-agents', '--session', 's1')
        self.assertEqual(('auto', 'default'), self.value('agents.qa.enabled', '--session', 's1'))
        self.assertEqual((True, 'session'), self.value('gates_before_push.test', '--session', 's1'))

    def test_get_and_agents_read_the_session_layer_too(self):
        self.run_tool('set', '--session', 's1', 'mode', 'D')
        self.assertEqual('D', self.run_tool('get', 'mode', '--session', 's1')[0].strip())
        self.assertIn('mode D', self.run_tool('agents', '--session', 's1')[0])
        self.assertNotIn('mode D', self.run_tool('agents')[0])

    def test_a_bad_session_id_is_refused_and_nothing_is_written(self):
        for bad in ('../x', 'a b', 'a/b', ''):
            _, err, code = self.run_tool('set', '--session', bad, 'push.prod', 'no')
            self.assertEqual(2, code, bad)
            self.assertIn('--session needs a session id', err)
        _, err, code = self.run_tool('set', 'push.prod', 'no', '--session')
        self.assertEqual(2, code)
        self.assertFalse(os.path.exists(os.path.join(self.home, 'sessions')))

    def test_project_and_session_cannot_be_combined(self):
        _, err, code = self.run_tool('set', '--session', 's1', '--project', 'push.prod', 'no')
        self.assertEqual(2, code)
        self.assertIn('cannot be combined', err)

    def test_an_invalid_value_in_the_session_is_refused_like_anywhere_else(self):
        _, err, code = self.run_tool('set', '--session', 's1', 'push.prod', 'maybe')
        self.assertEqual(2, code)
        self.assertFalse(os.path.exists(os.path.join(self.home, 'sessions', 's1.json')))

    def test_an_unreadable_session_file_is_reported_and_never_overwritten(self):
        os.makedirs(os.path.join(self.home, 'sessions'))
        path = os.path.join(self.home, 'sessions', 's1.json')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('{')
        _, err, code = self.run_tool('set', '--session', 's1', 'push.prod', 'no')
        self.assertEqual(1, code)
        with open(path, encoding='utf-8') as handle:
            self.assertEqual('{', handle.read())
        self.assertEqual((True, 'default'), self.value('push.prod', '--session', 's1'))   # the layer below wins

    def test_context_names_the_session_and_the_override_when_the_hook_payload_carries_the_id(self):
        self.run_tool('set', '--session', 'sess-9', 'push.prod', 'no')
        out, _, _ = self.run_tool('context', '--stdin', stdin=json.dumps({'session_id': 'sess-9'}))
        self.assertIn('this session is sess-9', out)
        self.assertIn('set --session sess-9', out)
        self.assertIn('prod: merge yes, gates before push yes, coverage before push yes, push no', out)
        plain, _, _ = self.run_tool('context', '--stdin', stdin='')
        self.assertNotIn('this session is', plain)
        junk, _, code = self.run_tool('context', '--stdin', stdin='not json')
        self.assertEqual(0, code)
        self.assertNotIn('this session is', junk)
        unread, _, code = self.run_tool('context', stdin=json.dumps({'session_id': 'sess-9'}))   # without --stdin nothing is read
        self.assertEqual(0, code)
        self.assertNotIn('this session is', unread)


class SessionStorage(unittest.TestCase):
    def test_ids_become_file_names_only_when_they_are_safe(self):
        for good in ('abc', 'a-b_c', '0123'):
            self.assertTrue(sessions.valid(good))
        for bad in ('', None, 5, 'a b', '../x', 'a/b', 'a.json', 'x' * 101):
            self.assertFalse(sessions.valid(bad), bad)
        with self.assertRaises(ValueError):
            sessions.session_file('../x')

    def test_the_directory_defaults_under_dot_claude_and_follows_the_environment(self):
        saved = os.environ.pop('ADYUSUF_SESSION_DIR', None)
        try:
            self.assertTrue(sessions.session_dir().endswith(os.path.join('.claude', 'adyusuf-session')))
            os.environ['ADYUSUF_SESSION_DIR'] = '/somewhere'
            self.assertEqual('/somewhere', sessions.session_dir())
        finally:
            os.environ.pop('ADYUSUF_SESSION_DIR', None)
            if saved is not None:
                os.environ['ADYUSUF_SESSION_DIR'] = saved

    def test_prune_removes_only_old_json_files(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            os.environ['ADYUSUF_SESSION_DIR'] = folder
            try:
                old, fresh, other = (os.path.join(folder, n) for n in ('old.json', 'fresh.json', 'keep.txt'))
                for path in (old, fresh, other):
                    open(path, 'w').close()
                long_ago = time.time() - 30 * 86400
                os.utime(old, (long_ago, long_ago))
                os.utime(other, (long_ago, long_ago))
                self.assertEqual(1, sessions.prune())
                self.assertEqual(['fresh.json', 'keep.txt'], sorted(os.listdir(folder)))
                os.environ['ADYUSUF_SESSION_DIR'] = os.path.join(folder, 'missing')
                self.assertEqual(0, sessions.prune())            # no folder: nothing to do, no error
            finally:
                os.environ.pop('ADYUSUF_SESSION_DIR', None)


class SessionNotify(base.Notify):
    def test_a_session_change_is_announced_to_that_session_only(self):
        self.hook('sess-1')
        self.hook('sess-2')
        self.run_tool('set', '--session', 'sess-1', 'push.prod', 'no')
        note = self.hook('sess-1')
        self.assertIsNotNone(note)
        self.assertIn('push.prod: yes -> no', note['additionalContext'])
        self.assertIn('this session is sess-1', note['additionalContext'])
        self.assertIsNone(self.hook('sess-2'))

    def test_a_saved_default_change_still_reaches_every_session(self):
        self.hook('sess-1')
        self.run_tool('set', 'push.dev', 'no')
        self.assertIn('push.dev: yes -> no', self.hook('sess-1')['additionalContext'])


if __name__ == '__main__':
    unittest.main()
