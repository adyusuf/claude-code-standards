#!/usr/bin/env python3
"""MEASURES what a session has spent so far, from its transcript (it does not estimate).

Usage:  python3 ~/.claude/scripts/session-cost.py <session-id>
        python3 ~/.claude/scripts/session-cost.py <session-id> --json

The session id is the last segment of the scratchpad path; Claude reads its own
from the "Scratchpad Directory" line in the system prompt.

WHY IT EXISTS: modes/autonomous-run.md says "the spend so far is written on every
turn" and "it stops when it passes the ceiling". A ceiling nobody measures is not
a ceiling — the next session says "roughly" and walks past it. This script sums
the `usage` field of every assistant message in ~/.claude/projects/**/*.jsonl and
multiplies by the list price. The same method was used to measure 33 sessions.

⚠️ Prices are API LIST prices and are NOT a subscription bill; they are a proxy
for consumption. Cache reads cost 2.5% on Fable 5.1 (10% elsewhere) — verified
against the live documentation. Update the table when a new model ships.
"""
import glob, json, os, sys, collections

# model: (input $/M, output $/M, cache-read ratio). cache-write = input x 1.25
PRICES = {
    'claude-fable-5-1': (10, 50, .025),
    'claude-fable-5':   (10, 50, .10),
    'claude-opus-5':    (5,  25, .10),
    'claude-opus-4-8':  (5,  25, .10),
    'claude-sonnet-5':  (2,  10, .10),
    'claude-haiku-4-5': (1,   5, .10),
}
DEFAULT = (5, 25, .10)   # unknown model: assume Opus pricing and flag it


def measure(session_id):
    main_cost = sidechain_cost = 0.0
    per_model = collections.Counter()
    unknown = set()
    messages = 0
    root = os.path.expanduser('~/.claude/projects')
    for path in glob.glob(os.path.join(root, '**', '*.jsonl'), recursive=True):
        with open(path, errors='ignore') as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                if record.get('sessionId') != session_id:
                    continue
                message = record.get('message') or {}
                usage = message.get('usage')
                if not usage:
                    continue
                model = message.get('model', '?')
                if model not in PRICES:
                    unknown.add(model)
                p_in, p_out, cache_rate = PRICES.get(model, DEFAULT)
                cost = (usage.get('input_tokens', 0) * p_in
                        + usage.get('cache_creation_input_tokens', 0) * p_in * 1.25
                        + usage.get('cache_read_input_tokens', 0) * p_in * cache_rate
                        + usage.get('output_tokens', 0) * p_out) / 1e6
                per_model[model] += cost
                if record.get('isSidechain'):
                    sidechain_cost += cost
                else:
                    main_cost += cost
                    messages += 1
    return dict(session=session_id, main=round(main_cost, 2), subagent=round(sidechain_cost, 2),
                total=round(main_cost + sidechain_cost, 2), assistant_messages=messages,
                per_model={k: round(v, 2) for k, v in per_model.most_common()},
                unknown_models=sorted(unknown))


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        print(__doc__)
        return 2
    result = measure(sys.argv[1])
    if result['assistant_messages'] == 0:
        print(f"✗ session not found: {result['session']}")
        return 1
    if '--json' in sys.argv:
        print(json.dumps(result, ensure_ascii=False))
        return 0
    print(f"session {result['session'][:8]}…  main ${result['main']:.2f} "
          f"+ subagent ${result['subagent']:.2f} = TOTAL ${result['total']:.2f}  "
          f"({result['assistant_messages']} messages)")
    print("  per model:", ', '.join(f"{k[:16]} ${v:.2f}" for k, v in result['per_model'].items()))
    if result['unknown_models']:
        print(f"  ⚠️ model with no price (Opus assumed): {result['unknown_models']} — update the PRICES table")
    return 0


if __name__ == '__main__':
    sys.exit(main())
