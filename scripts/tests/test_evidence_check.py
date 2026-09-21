import os
import sys
import unittest

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))
import importlib.util

spec = importlib.util.spec_from_file_location(
    'evidence_check', os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'evidence-check.py')))
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

CLEAN = """report body

## Completeness check — pass 1
- Verification   → `bash scripts/gate-core.sh dev --list` exit 0; read gate-core.sh lines 90-120
- Item mapping   → fail-closed check → scripts/gate-core.sh:112
- Not covered    → prod path not run; deliberately left out: NIST column
→ Result: clean NO
"""

YES_BLOCK = """## Completeness check — pass 2
- Verification   → `grep -n SETUP scripts/gate-core.sh`
- Item mapping   → 
  - inventory heading → scripts/gate-core.sh:118
  - .env.example → scripts/gate-core.sh:116
- Not covered    → nothing
→ Result: YES → BACK TO: developer · add the inventory check · re-run `grep -n inventory scripts/gate-core.sh`
"""


def problems(text):
    return ev.validate(text)[1]


class EvidenceCheck(unittest.TestCase):
    def test_clean_block_is_valid(self):
        self.assertEqual(problems(CLEAN), [])

    def test_yes_block_with_hand_back_is_valid_and_multiline_mapping_parsed(self):
        blocks, errors = ev.validate(YES_BLOCK)
        self.assertEqual(errors, [])
        self.assertEqual(len(blocks[0]['item_mapping']), 2)
        self.assertEqual(blocks[0]['result']['back_to']['who'], 'developer')

    def test_no_block_fails_closed(self):
        self.assertTrue(any('no "## Completeness check' in e for e in problems('just prose')))

    def test_verification_without_evidence_is_rejected(self):
        bad = CLEAN.replace('`bash scripts/gate-core.sh dev --list` exit 0; read gate-core.sh lines 90-120', 'looked fine')
        self.assertTrue(any('verification' in e for e in problems(bad)))

    def test_clean_with_not_verified_is_rejected(self):
        bad = CLEAN.replace('prod path not run', 'prod path not verified')
        self.assertTrue(any('not verified' in e for e in problems(bad)))

    def test_yes_without_hand_back_is_rejected(self):
        bad = YES_BLOCK.replace('developer · add the inventory check · re-run `grep -n inventory scripts/gate-core.sh`', '')
        self.assertTrue(any('BACK TO' in e for e in problems(bad)))

    def test_missing_item_mapping_is_rejected(self):
        bad = CLEAN.replace('- Item mapping   → fail-closed check → scripts/gate-core.sh:112\n', '')
        self.assertTrue(any('item_mapping' in e for e in problems(bad)))

    def test_unknown_result_is_rejected(self):
        bad = CLEAN.replace('clean NO', 'looks good')
        self.assertTrue(any('serious_gap' in e for e in problems(bad)))

    def test_every_block_in_a_report_is_checked(self):
        errors = problems(CLEAN + '\n' + CLEAN.replace('clean NO', 'maybe').replace('pass 1', 'pass 2'))
        self.assertTrue(errors and all(e.startswith('pass 2') for e in errors))


if __name__ == '__main__':
    unittest.main()
