"""The live board's launchers (scripts/board/): the stable hook paths hand over to the claude-monitor
install, and a missing install never stops a session. The hook block documented in standards/22 is the
one `.claude/settings.json` carries."""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / "scripts" / "board"
sys.path.insert(0, str(BOARD))

import board_launcher as launcher  # noqa: E402

SCRIPTS = ("board.py", "board_ensure.py", "board_hook.py", "board_open.py", "board_server.py")
ECHO = ("import json, sys\n"
        "print(json.dumps({'argv': sys.argv[1:], 'stdin': sys.stdin.read(), 'me': __file__}))\n")


def run(script, *argv, home=None, user_home=None, stdin=""):
    env = {k: v for k, v in os.environ.items() if k != launcher.HOME_ENV}
    if home is not None:
        env[launcher.HOME_ENV] = str(home)
    if user_home is not None:
        env["HOME"] = str(user_home)
        env["USERPROFILE"] = str(user_home)     # what expanduser reads on Windows
    return subprocess.run([sys.executable, str(BOARD / script), *argv], input=stdin,
                          capture_output=True, text=True, env=env)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name).resolve()
        self.monitor = self.tmp_path / "monitor"
        (self.monitor / "scripts" / "board").mkdir(parents=True)
        for name in SCRIPTS:
            (self.monitor / "scripts" / "board" / name).write_text(ECHO)

    def test_every_entry_point_hands_over_to_the_installed_script_with_args_and_stdin(self):
        for name in SCRIPTS:
            with self.subTest(script=name):
                out = run(name, "enable", "--x", home=self.monitor, stdin='{"cwd": "/p"}')
                self.assertEqual(out.returncode, 0, out.stderr)
                got = json.loads(out.stdout)
                self.assertEqual(got["argv"], ["enable", "--x"])
                self.assertEqual(got["stdin"], '{"cwd": "/p"}')
                self.assertEqual(Path(got["me"]), self.monitor / "scripts" / "board" / name)

    def test_the_exit_code_of_the_installed_script_is_the_launchers(self):
        (self.monitor / "scripts" / "board" / "board.py").write_text("import sys\nsys.exit(7)\n")
        self.assertEqual(run("board.py", home=self.monitor).returncode, 7)

    def test_without_the_env_the_default_location_under_home_is_used(self):
        default = self.tmp_path / "ClaudeCode" / "claude-monitor" / "scripts" / "board"
        default.mkdir(parents=True)
        (default / "board.py").write_text(ECHO)
        out = run("board.py", "list", user_home=self.tmp_path)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["argv"], ["list"])

    def test_a_missing_install_keeps_the_hook_silent_and_successful(self):
        out = run("board_hook.py", home=self.tmp_path / "nowhere", stdin="{}")
        self.assertEqual((out.returncode, out.stdout, out.stderr), (0, "", ""))

    def test_a_missing_install_makes_session_start_say_so_in_one_line(self):
        out = run("board_ensure.py", home=self.tmp_path / "nowhere", stdin="{}")
        self.assertEqual(out.returncode, 0)
        self.assertEqual(len(out.stdout.strip().splitlines()), 1)
        self.assertIn("git clone " + launcher.REPO_URL, out.stdout)

    def test_a_missing_install_fails_a_command_with_the_clone_line(self):
        for name in ("board.py", "board_open.py", "board_server.py"):
            with self.subTest(script=name):
                out = run(name, home=self.tmp_path / "nowhere")
                self.assertEqual(out.returncode, launcher.EXIT_MISSING)
                self.assertIn("git clone", out.stderr)
                self.assertEqual(out.stdout, "")

    def test_an_install_without_that_script_counts_as_missing(self):
        (self.monitor / "scripts" / "board" / "board_open.py").unlink()
        self.assertEqual(run("board_open.py", home=self.monitor).returncode, launcher.EXIT_MISSING)

    def test_a_clone_without_the_board_says_it_was_removed_not_clone_again(self):
        # claude-monitor removed the Python board (86684df): an updated clone has no scripts/board/board.py.
        for name in SCRIPTS:
            (self.monitor / "scripts" / "board" / name).unlink()
        out = run("board_ensure.py", home=self.monitor, stdin="{}")
        self.assertEqual(out.returncode, 0)
        self.assertIn("archive/board-final", out.stdout)
        self.assertNotIn("git clone", out.stdout)
        self.assertEqual(run("board_hook.py", home=self.monitor, stdin="{}").stdout, "")

    def test_an_unknown_script_name_fails_closed(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.main("nope.py"), launcher.EXIT_MISSING)

    def test_there_is_a_launcher_for_every_script_the_settings_call(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
        called = set(re.findall(r"scripts/board/(\w+\.py)", json.dumps(settings)))
        self.assertTrue(called)
        for name in called:
            self.assertTrue((BOARD / name).is_file(), name)
            self.assertIn(name, launcher.ON_MISSING)


class DocumentedBlockTests(unittest.TestCase):
    def test_the_hook_block_in_standards_22_is_the_one_this_repository_uses(self):
        doc = (ROOT / "standards" / "22-live-board.md").read_text()
        block = re.search(r"```json\n(\{\n  \"hooks\": \{.*?\n\})\n```", doc, re.S).group(1)
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
        self.assertEqual(json.loads(block)["hooks"], settings["hooks"])


if __name__ == "__main__":
    unittest.main()
