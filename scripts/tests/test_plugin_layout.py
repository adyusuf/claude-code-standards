"""The `adyusuf` plugin (standards/00 §7a): our skills and commands load as one
skills-dir plugin, so every one of them is invoked as /adyusuf:<name>."""
import json
import os
import re
import subprocess
import unittest

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PLUGIN = os.path.join(REPO, 'plugin')
NAMESPACE = 'adyusuf'
DOC_SUFFIXES = ('.md', '.py', '.sh', '.js', '.json')
SELF = 'scripts/tests/test_plugin_layout.py'  # its fixtures are unprefixed on purpose


def own_names():
    skills = [d for d in os.listdir(os.path.join(REPO, 'skills'))
              if os.path.isfile(os.path.join(REPO, 'skills', d, 'SKILL.md'))]
    commands = [f[:-3] for f in os.listdir(os.path.join(REPO, 'commands')) if f.endswith('.md')]
    return sorted(skills + commands)


def unprefixed(text, names):
    """Slash invocations of our names that lack the namespace (paths like skills/x are fine)."""
    pattern = re.compile(r'(^|[^A-Za-z0-9_./:-])/(' + '|'.join(map(re.escape, names)) + r')\b')
    return [m.group(2) for m in pattern.finditer(text)]


class ManifestTest(unittest.TestCase):
    def test_manifest_names_the_namespace(self):
        with open(os.path.join(PLUGIN, '.claude-plugin', 'plugin.json'), encoding='utf-8') as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest['name'], NAMESPACE)

    def test_components_link_back_to_the_repository_folders(self):
        for part in ('skills', 'commands'):
            link = os.path.join(PLUGIN, part)
            self.assertTrue(os.path.islink(link), f'plugin/{part} must be a link, not a copy')
            self.assertEqual(os.readlink(link), f'../{part}', 'relative, so it follows the checkout')
            self.assertEqual(os.path.realpath(link), os.path.realpath(os.path.join(REPO, part)))

    def test_no_agents_component(self):
        # A plugin agents/ would load a second, prefixed copy of every role (never-do list).
        self.assertFalse(os.path.exists(os.path.join(PLUGIN, 'agents')))

    def test_each_skill_is_named_after_its_folder(self):
        for name in os.listdir(os.path.join(REPO, 'skills')):
            path = os.path.join(REPO, 'skills', name, 'SKILL.md')
            if not os.path.isfile(path):
                continue
            with open(path, encoding='utf-8') as handle:
                front = handle.read().split('---')[1]
            self.assertIn(f'\nname: {name}\n', front, path)


class ReferenceTest(unittest.TestCase):
    def test_unprefixed_detects_and_ignores(self):
        names = ['working-mode']
        self.assertEqual(unprefixed('run `/working-mode B`', names), ['working-mode'])
        self.assertEqual(unprefixed('/working-mode', names), ['working-mode'])
        self.assertEqual(unprefixed('run `/adyusuf:working-mode B`', names), [])
        self.assertEqual(unprefixed('see skills/working-mode/SKILL.md', names), [])
        self.assertEqual(unprefixed('/working-modes', names), [])

    def test_every_invocation_in_the_repository_is_prefixed(self):
        names = own_names()
        self.assertGreaterEqual(len(names), 7)
        files = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True,
                               text=True, check=True).stdout.splitlines()
        stale = {}
        for rel in files:
            path = os.path.join(REPO, rel)
            if rel == SELF or not rel.endswith(DOC_SUFFIXES) or os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, encoding='utf-8') as handle:
                found = unprefixed(handle.read(), names)
            if found:
                stale[rel] = found
        self.assertEqual(stale, {}, 'write /adyusuf:<name>')


if __name__ == '__main__':
    unittest.main()
