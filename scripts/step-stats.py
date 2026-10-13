#!/usr/bin/env python3
"""Step and agent statistics — HOW MANY TIMES a step ran and HOW MANY TOKENS it cost.

Usage:
    python3 scripts/step-stats.py               # print
    python3 scripts/step-stats.py --write       # also write docs/measurement-log.md
    python3 scripts/step-stats.py --days 30     # limit the window

Why it exists: the cost table in modes/role-selection.md §8 is an ESTIMATE.
This script is the measurement that corrects it. Source: the `usage` fields and
`tool_use` blocks inside ~/.claude/projects/**/*.jsonl.

⚠️ Prices are API LIST prices, not a subscription bill — a proxy for consumption.
⚠️ Step counting is based on shell command patterns: a step that runs from inside
   another script is invisible here. A missing step is "not seen", not "zero".
⚠️ The scripts were renamed to English. Runs recorded under the
   previous names are no longer counted, so md-gate counts from before that date
   are not comparable with later ones.
"""
import glob, importlib.util, json, os, re, sys, datetime, statistics, collections

HERE = os.path.dirname(os.path.realpath(__file__))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The parts live beside this file (rule #9). Every name is re-exported HERE: the tests and
# ~/.claude/measurement/measurement-ledger.py load this file by path and read them from it.
# What reads TRANSCRIPTS or `shape` stays in this file, so a caller that replaces either
# one on this module (the ledger's tests, the sanitiser-gate test) still changes what runs.
sanitiser = load('step_stats_sanitiser', 'step_stats_sanitiser.py')
transcripts = load('step_stats_transcripts', 'step_stats_transcripts.py')
cells = load('step_stats_cells', 'step_stats_cells.py')
SHELL_OP, HEXISH, SAFE_WORDS = sanitiser.SHELL_OP, sanitiser.HEXISH, sanitiser.SAFE_WORDS
deny_pattern, shape, scan_output = sanitiser.deny_pattern, sanitiser.shape, sanitiser.scan_output
PRICES, price, STEPS = transcripts.PRICES, transcripts.price, transcripts.STEPS
NOISE_COMMAND, NOISE_PREFIX = transcripts.NOISE_COMMAND, transcripts.NOISE_PREFIX
HEREDOC, SEGMENT, command_part = transcripts.HEREDOC, transcripts.SEGMENT, transcripts.command_part
measure, role_ids, map_roles = transcripts.measure, transcripts.role_ids, transcripts.map_roles
ROLE_ALIASES, role_label = cells.ROLE_ALIASES, cells.role_label
MIN_CUT_ROWS, cut_delta = cells.MIN_CUT_ROWS, cells.cut_delta

TRANSCRIPTS = os.path.expanduser('~/.claude/projects/**/*.jsonl')


# Every shape that actually occurs must appear here: a var-assignment prefix hid a
# path tail from an earlier version of this gate.
# ⚠️ Every marker in LEAK_MARKERS must actually OCCUR here, or the gate passes
# by accident for that marker. `/home/` was listed and missing from the canary,
# so a Linux home path was never exercised by the self-check — found by a test
# that compares the two lists. If a marker is added below, add a
# token carrying it here.
CANARY = ("L=/private/tmp/sess-AcmeCorp/run.log; dotnet build AcmeCorp.Tests/x.csproj "
          "&& cd /Users/zzz/Code/AcmeCorp && cp /home/zzz/.env . "
          "&& git push origin d401a71eefa6e931dfad5828b0c4825f33dfea20 # pw=hunter2")
LEAK_MARKERS = ('/Users/', '/home/', '/private/tmp', 'zzz', 'AcmeCorp',
                'd401a71', 'hunter2', '.csproj')


def sanitizer_gate():
    """Mutation-style check: if a synthetic identifier survives, refuse to write."""
    produced = shape(CANARY)
    leaked = [m for m in LEAK_MARKERS if m.lower() in produced.lower()]
    if leaked:
        sys.exit(f"sanitiser gate FAILED — these survived {leaked}: {produced!r}")
    return produced


def collect(days=None):
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp() if days else 0
    sessions, agents = [], []
    for path in glob.glob(TRANSCRIPTS, recursive=True):
        if os.path.getmtime(path) < cutoff:
            continue
        (agents if os.path.basename(path).startswith('agent-') else sessions).append(path)
    return sessions, agents


def count_steps(sessions):
    """Per step: how many calls actually RAN it (false positives are filtered out)."""
    counts, dismissed, best = collections.Counter(), collections.Counter(), {}
    for path in sessions:
        with open(path, errors='ignore') as handle:
            for line in handle:
                if '"tool_use"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                content = (record.get('message') or {}).get('content')
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not (isinstance(block, dict) and block.get('type') == 'tool_use'):
                        continue
                    raw = str((block.get('input') or {}).get('command') or '')
                    if not raw or NOISE_COMMAND.search(raw):
                        continue
                    command = command_part(raw)
                    for name, pattern in STEPS:
                        match = re.search(pattern, command, re.I)
                        if not match:
                            if re.search(pattern, raw, re.I):
                                dismissed[name] += 1      # only inside a heredoc body
                            continue
                        before = command[max(0, match.start() - 60):match.start()]
                        if NOISE_PREFIX.search(before):
                            dismissed[name] += 1
                            continue
                        counts[name] += 1
                        score = (2 if SEGMENT.search(before) else 0) + (1 if len(command) < 120 else 0)
                        if score > best.get(name, (-1, ''))[0]:
                            best[name] = (score, shape(command))
    return counts, {k: v[1] for k, v in best.items()}, dismissed


def compare_cuts():
    """For every configuration change in scripts/measurement-cuts.tsv, the prefix
    median BEFORE and AFTER. A new session fills the "after" column on its own —
    nobody has to remember to measure."""
    here = os.path.dirname(os.path.abspath(__file__))
    cuts_file = os.path.join(here, 'measurement-cuts.tsv')
    if not os.path.exists(cuts_file):
        return []
    rows = []
    for path in glob.glob(TRANSCRIPTS, recursive=True):
        if os.path.basename(path).startswith('agent-'):
            continue
        first = started = None
        with open(path, errors='ignore') as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except Exception:
                    continue
                if started is None and record.get('timestamp'):
                    started = record['timestamp']
                usage = (record.get('message') or {}).get('usage')
                if usage:
                    first = sum(usage.get(k, 0) or 0 for k in
                                ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
                    break
        if first and started:
            rows.append((datetime.datetime.fromisoformat(started.replace('Z', '+00:00')).timestamp(), first))
    out = ["## Fixed prefix — configuration cuts (before / after)\n",
           "| cut | label | before (median · n) | after (median · n) | delta |",
           "|---|---|---|---|---|"]
    index = 0
    with open(cuts_file, encoding='utf-8') as handle:
        for line in handle:
            if line.startswith('#') or not line.strip():
                continue
            index += 1
            try:
                timestamp, label = line.rstrip('\n').split('\t', 1)
            except ValueError:
                continue
            cut = datetime.datetime.fromisoformat(timestamp).timestamp()
            before = [value for when, value in rows if when <= cut]
            after = [value for when, value in rows if when > cut]
            b = int(statistics.median(before)) if before else 0
            a = int(statistics.median(after)) if after else 0
            delta = cut_delta(b, len(before), a, len(after))
            after_cell = f"{a:,} · {len(after)}" if a else "—"
            # The cut's timestamp stays in the local tsv; the published table shows its order.
            out.append(f"| cut {index} | {label} | {b:,} · {len(before)} | {after_cell} | {delta} |")
    return out


def report(days=None):
    sessions, agents = collect(days)
    lines = [f"Scope: {len(sessions)} sessions + {len(agents)} agent runs"
             + (f", last {days} days" if days else ", all records")
             + "\n"]   # no timestamp: the repo carries no dates
    measured = measure(sessions)
    prefixes = [v[0] for v in measured.values() if v[0]]
    requests = sum(v[1] for v in measured.values())
    total = sum(v[2] for v in measured.values())
    lines.append("## Session prefix (system prompt + tool/skill listings + CLAUDE.md)\n")
    lines.append(f"- sessions: **{len(prefixes)}** · model requests: **{requests:,}**")
    if prefixes:
        median = int(statistics.median(prefixes))
        lines.append(f"- prefix median: **{median:,} tokens** (min {min(prefixes):,} · max {max(prefixes):,})")
        lines.append(f"- the prefix is re-read on every request → ~{median * requests / 1e9:.1f} billion tokens")
    # The absolute total is deliberately not published; the ratios below carry the meaning.
    lines.append("")
    lines += compare_cuts()
    lines.append("")
    agent_total = sum(v[2] for v in measure(agents).values())
    lines.append("## Agent roles — how many runs, at what cost\n")
    if total:
        lines.append(f"Agent runs account for **{100 * agent_total / total:.1f}%** "
                     f"of total spend\n")
    lines.append("| role | runs | starting prefix (total) | estimated $ |")
    lines.append("|---|---:|---:|---:|")
    # Historical transcripts carry the old role names; report them as they are called
    # today, and SUM the rows that end up with the same label — two plugins can both
    # provide a `code-reviewer`, and two rows with one name cannot be told apart.
    by_label = {}
    for role, (runs, prefix_tokens, cost) in map_roles(sessions, agents).items():
        label = role_label(role)
        was = by_label.get(label, (0, 0, 0.0))
        by_label[label] = (was[0] + runs, was[1] + prefix_tokens, was[2] + cost)
    for label, (runs, prefix_tokens, cost) in sorted(by_label.items(), key=lambda x: -x[1][0]):
        lines.append(f"| `{label}` | {runs} | {prefix_tokens:,} "
                     f"| ${cost:,.2f} |")
    lines.append("")
    lines.append("## SDLC steps — how many times each one ran\n")
    lines.append("| step | runs | dismissed (mentions) | example command |")
    lines.append("|---|---:|---:|---|")
    counts, examples, dismissed = count_steps(sessions)
    for name, _pattern in STEPS:
        runs = counts.get(name, 0)
        lines.append(f"| {name} | {runs if runs else '—'} | {dismissed.get(name, 0) or ''} "
                     f"| `{examples.get(name, '(not seen)')}` |")
    lines.append('\n⚠️ "—" means the step was not seen in this scan; it may run from inside another script.')
    lines.append('⚠️ "dismissed" counts calls that only MENTION the command '
                 '(a grep/ps/echo argument, or text written into a file).')
    return "\n".join(lines)


if __name__ == '__main__':
    window = None
    if '--days' in sys.argv:
        window = int(sys.argv[sys.argv.index('--days') + 1])
    print("sanitiser gate:", sanitizer_gate())
    text = report(window)
    dirty = scan_output(text)
    if dirty:
        sys.exit(f"refusing to write — {len(dirty)} identifier(s) in the output: {dirty[:5]}")
    if '--write' in sys.argv:
        target = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              'docs', 'measurement-log.md')
        header = ("# Measurement log — step and agent statistics\n\n"
                  "> **Generated file** — do not edit by hand; regenerate with\n"
                  "> `python3 scripts/step-stats.py --write`. The estimate table in\n"
                  "> `modes/role-selection.md` §8 is corrected with these numbers (never from a\n"
                  "> single measurement: at least three records, or one real end-to-end round).\n\n")
        open(target, 'w').write(header + text + "\n")
        print("written:", target)
    print(text)
