#!/usr/bin/env python3
"""Validate the completeness-check evidence block (modes/role-selection.md §7).

Usage:
    python3 scripts/evidence-check.py report.md        # validate every block in a file
    some-command | python3 scripts/evidence-check.py -  # ... or stdin
    python3 scripts/evidence-check.py report.md --json  # print the parsed blocks

Exit codes: 0 every block valid · 1 a block is invalid, or the report has NO block
(a role's output without its evidence block is unaudited, not clean) · 2 usage.

The structural rules live in evidence-block.schema.json (next to this file); the
few rules a schema cannot express are in `semantic_errors`. No third-party
packages: only the schema keywords listed in the schema's $comment are supported.
"""
import json
import os
import re
import sys

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'evidence-block.schema.json')

HEADING = re.compile(r'^#{1,6}\s*Completeness check\s*[—–-]+\s*pass\s+(\d+)\s*$', re.I)
KEYS = (('verification', re.compile(r'^\s*-\s*Verification\s*→?\s*(.*)$', re.I)),
        ('item_mapping', re.compile(r'^\s*-\s*Item mapping\s*→?\s*(.*)$', re.I)),
        ('not_covered', re.compile(r'^\s*-\s*Not covered\s*→?\s*(.*)$', re.I)),
        ('result', re.compile(r'^\s*→?\s*Result\s*:\s*(.*)$', re.I)))
YES = re.compile(r'^YES\b\s*(?:→|->)?\s*(?:BACK TO\s*:)?\s*(.*)$', re.I)
CLEAN = re.compile(r'^(?:serious gap\s+)?(?:clean\s+)?NO\b', re.I)
NOT_VERIFIED = re.compile(r'not\s+verified', re.I)


def parse_blocks(text):
    """Return one dict per completeness-check block found in `text`."""
    blocks, current, key = [], None, None
    for line in text.splitlines():
        heading = HEADING.match(line.strip())
        if heading:
            current = {'pass': int(heading.group(1)), '_raw': {}}
            blocks.append(current)
            key = None
            continue
        if current is None:
            continue
        for name, pattern in KEYS:
            match = pattern.match(line)
            if match:
                key = name
                current['_raw'][name] = [match.group(1).strip()] if match.group(1).strip() else []
                break
        else:
            if key and line.strip() and not line.startswith('#'):
                current['_raw'][key].append(line.strip())
            elif line.startswith('#'):
                current, key = None, None
    return [build(b) for b in blocks]


def build(block):
    raw = block['_raw']
    out = {'pass': block['pass']}
    if 'verification' in raw:
        out['verification'] = ' '.join(raw['verification'])
    if 'item_mapping' in raw:
        out['item_mapping'] = [re.sub(r'^[-*]\s*', '', x) for x in raw['item_mapping'] if x]
    if 'not_covered' in raw:
        out['not_covered'] = ' '.join(raw['not_covered'])
    if 'result' in raw:
        out['result'] = parse_result(' '.join(raw['result']))
    return out


def parse_result(text):
    text = text.strip()
    yes = YES.match(text)
    if yes:
        parts = [p.strip() for p in re.split(r'\s*[·|]\s*', yes.group(1)) if p.strip()]
        result = {'serious_gap': 'YES'}
        if len(parts) >= 3:
            result['back_to'] = {'who': parts[0], 'what': parts[1], 'closing_evidence': ' · '.join(parts[2:])}
        return result
    if CLEAN.match(text):
        return {'serious_gap': 'NO'}
    return {'serious_gap': text or ''}


def check(value, schema, path='$'):
    """A minimal validator for the schema keywords this repo uses."""
    errors = []
    kind = schema.get('type')
    checkers = {'object': dict, 'array': list, 'string': str, 'integer': int}
    if kind and not isinstance(value, checkers[kind]):
        return [f'{path}: expected {kind}']
    if kind == 'object':
        for name in schema.get('required', []):
            if name not in value:
                errors.append(f'{path}.{name}: missing')
        for name, sub in schema.get('properties', {}).items():
            if name in value:
                errors += check(value[name], sub, f'{path}.{name}')
    if kind == 'array':
        if len(value) < schema.get('minItems', 0):
            errors.append(f'{path}: needs at least {schema["minItems"]} item(s)')
        for i, item in enumerate(value):
            errors += check(item, schema.get('items', {}), f'{path}[{i}]')
    if kind == 'string':
        if len(value) < schema.get('minLength', 0):
            errors.append(f'{path}: empty')
        if 'enum' in schema and value not in schema['enum']:
            errors.append(f'{path}: {value!r} is not one of {schema["enum"]}')
        if 'pattern' in schema and value and not re.search(schema['pattern'], value):
            errors.append(f'{path}: carries no command, file:line or line range')
    return errors


def semantic_errors(block):
    """Rules a schema cannot express."""
    errors = []
    result = block.get('result', {})
    if result.get('serious_gap') == 'NO' and NOT_VERIFIED.search(block.get('not_covered', '')):
        errors.append('$.not_covered: says "not verified" but the result is clean — what cannot be verified is not fine')
    if result.get('serious_gap') == 'YES' and 'back_to' not in result:
        errors.append('$.result: YES needs BACK TO: <who> · <what to fix> · <closing evidence>')
    return errors


def validate(text):
    """Return (blocks, errors). No block at all is itself an error."""
    with open(SCHEMA_PATH, encoding='utf8') as handle:
        schema = json.load(handle)
    blocks = parse_blocks(text)
    if not blocks:
        return blocks, ['no "## Completeness check — pass N" block found: an unaudited report is not clean']
    errors = []
    for block in blocks:
        for message in check(block, schema) + semantic_errors(block):
            errors.append(f'pass {block["pass"]}: {message}')
    return blocks, errors


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    if len(args) != 1:
        print(__doc__)
        return 2
    text = sys.stdin.read() if args[0] == '-' else open(args[0], encoding='utf8').read()
    blocks, errors = validate(text)
    if '--json' in argv:
        print(json.dumps(blocks, ensure_ascii=False, indent=2))
    for message in errors:
        print(f'✗ {message}', file=sys.stderr)
    if not errors:
        print(f'✓ {len(blocks)} evidence block(s) valid')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
