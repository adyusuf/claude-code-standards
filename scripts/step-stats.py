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
"""
import glob, json, os, re, sys, datetime, statistics, collections

PRICES = {'claude-fable-5-1': (10, 50, .025), 'claude-opus-5': (5, 25, .10),
          'claude-opus-4-8': (5, 25, .10), 'claude-sonnet-5': (2, 10, .10),
          'claude-haiku-4-5': (1, 5, .10)}

def price(model):
    for key, value in PRICES.items():
        if key in (model or ''):
            return value
    return (5, 25, .10)

# step name -> command pattern (the gates of the SDLC flow)
STEPS = [
    ('build',            r'dotnet build|npm run build|yarn build|pnpm build|expo prebuild'),
    ('unit test',        r'dotnet test|npm (run )?test|vitest|jest|pytest'),
    ('typecheck',        r'tsc --noEmit|tsc -p'),
    ('lint/format',      r'dotnet format|eslint|prettier|ruff|biome'),
    ('coverage',         r'coverage|XPlat Code Coverage|--coverage'),
    ('e2e (playwright)', r'playwright test|npx playwright'),
    ('e2e (maestro)',    r'maestro test'),
    ('secret scan',      r'gitleaks|trufflehog'),
    ('SAST',             r'codeql|semgrep'),
    ('dependency CVE',   r'npm audit|dotnet list package --vulnerable|osv-scanner'),
    ('local ci gate',    r'ci-local\.sh'),
    ('md size gate',     r'md-size-gate\.sh|md-boyut-kapisi\.sh'),
    ('md rule gate',     r'md-rule-gate\.py|md-kural-kapisi\.py'),
    ('git merge',        r'git merge'),
    ('git push',         r'git push'),
    ('deploy/publish',   r'dotnet publish|vercel deploy|wrangler deploy|docker push'),
]

# Contexts that MENTION a command instead of running it.
NOISE_COMMAND = re.compile(r"step-stats|STEPS\s*=", re.I)
NOISE_PREFIX = re.compile(r"(grep|rg|ps\s+-|echo|awk|sed|comment|#)[^;&\n]{0,60}$", re.I)
# A heredoc body is data, not a command: `python3 - <<'PY' … gitleaks … PY`
HEREDOC = re.compile(r"<<-?\s*['\"]?\w+['\"]?")
SEGMENT = re.compile(r"(^|&&|\|\||;|\||\n|\(|`|\$\()\s*"
                     r"(sudo\s+|npx\s+|npm\s+|yarn\s+|pnpm\s+|dotnet\s+|git\s+|bash\s+|python3?\s+)?$")

TRANSCRIPTS = os.path.expanduser('~/.claude/projects/**/*.jsonl')


def command_part(command):
    """Drop heredoc BODIES, keep the rest: a `npm test` after the heredoc is a real run."""
    parts, index = [], 0
    while True:
        match = HEREDOC.search(command, index)
        if not match:
            parts.append(command[index:])
            break
        parts.append(command[index:match.start()])
        marker = re.sub(r"""[<\-\s'"]""", "", match.group(0))
        end = re.search(rf"^\s*{re.escape(marker)}\s*$", command[match.end():], re.M)
        index = match.end() + (end.end() if end else len(command))
    return " ".join(parts)


def collect(days=None):
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp() if days else 0
    sessions, agents = [], []
    for path in glob.glob(TRANSCRIPTS, recursive=True):
        if os.path.getmtime(path) < cutoff:
            continue
        (agents if os.path.basename(path).startswith('agent-') else sessions).append(path)
    return sessions, agents


def measure(paths):
    """path -> (first-request prefix, request count, estimated $, model)"""
    result = {}
    for path in paths:
        first = model = None
        count, cost = 0, 0.0
        for line in open(path, errors='ignore'):
            try:
                record = json.loads(line)
            except Exception:
                continue
            message = record.get('message') or {}
            usage = message.get('usage')
            if not usage:
                continue
            p_in, p_out, cache_rate = price(message.get('model'))
            model = model or message.get('model')
            tokens_in = usage.get('input_tokens', 0) or 0
            tokens_out = usage.get('output_tokens', 0) or 0
            cache_write = usage.get('cache_creation_input_tokens', 0) or 0
            cache_read = usage.get('cache_read_input_tokens', 0) or 0
            cost += (tokens_in * p_in + tokens_out * p_out
                     + cache_write * p_in * 1.25 + cache_read * p_in * cache_rate) / 1e6
            if first is None:
                first = tokens_in + cache_write + cache_read
            count += 1
        if count:
            result[path] = (first, count, cost, model)
    return result


def count_steps(sessions):
    """Per step: how many calls actually RAN it (false positives are filtered out)."""
    counts, dismissed, best = collections.Counter(), collections.Counter(), {}
    for path in sessions:
        for line in open(path, errors='ignore'):
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
                        sample = re.sub(r"\s+", " ", command.strip())
                        sample = re.sub(r"(/Users/[^/]+|/home/[^/]+|/private/tmp/[^\s]*)", "…", sample)
                        best[name] = (score, sample[:64])
    return counts, {k: v[1] for k, v in best.items()}, dismissed


def map_roles(sessions, agents):
    """Match the role named in the Agent call with the agentId in its result."""
    id_to_role = {}
    for path in sessions:
        pending = {}
        for line in open(path, errors='ignore'):
            try:
                record = json.loads(line)
            except Exception:
                continue
            content = (record.get('message') or {}).get('content')
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use' and block.get('name') in ('Agent', 'Task'):
                    pending[block.get('id')] = (block.get('input') or {}).get('subagent_type') or 'unknown'
                if block.get('type') == 'tool_result':
                    text = json.dumps(block.get('content'), ensure_ascii=False)
                    found = re.search(r'agentId: ([0-9a-f]{8})', text)
                    if found:
                        id_to_role[found.group(1)] = pending.get(block.get('tool_use_id'), 'unknown')
    stats = collections.defaultdict(lambda: [0, 0, 0.0])   # runs, prefix tokens, $
    for path, (first, _count, cost, _model) in measure(agents).items():
        role = id_to_role.get(os.path.basename(path)[6:14], 'unknown')
        row = stats[role]
        row[0] += 1
        row[1] += first or 0
        row[2] += cost
    return stats


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
        for line in open(path, errors='ignore'):
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
    for line in open(cuts_file, encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            continue
        try:
            timestamp, label = line.rstrip('\n').split('\t', 1)
        except ValueError:
            continue
        cut = datetime.datetime.fromisoformat(timestamp).timestamp()
        before = [value for when, value in rows if when <= cut]
        after = [value for when, value in rows if when > cut]
        b = int(statistics.median(before)) if before else 0
        a = int(statistics.median(after)) if after else 0
        delta = f"**-{b - a:,} (-{100 * (b - a) / b:.0f}%)**" if (b and a) else "**not measured** — needs a new session"
        after_cell = f"{a:,} · {len(after)}" if a else "—"
        out.append(f"| {timestamp} | {label} | {b:,} · {len(before)} | {after_cell} | {delta} |")
    return out


def report(days=None):
    sessions, agents = collect(days)
    lines = [f"Scope: {len(sessions)} sessions + {len(agents)} agent runs"
             + (f", last {days} days" if days else ", all records")
             + f"  ·  measured: {datetime.datetime.now():%d/%m/%Y %H:%M}\n"]
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
    lines.append(f"- measured total (list price): **${total:,.0f}**\n")
    lines += compare_cuts()
    lines.append("")
    agent_total = sum(v[2] for v in measure(agents).values())
    lines.append("## Agent roles — how many runs, at what cost\n")
    if total:
        lines.append(f"Agent runs account for **${agent_total:,.0f}** "
                     f"(**{100 * agent_total / total:.1f}%** of everything)\n")
    lines.append("| role | runs | starting prefix (total) | estimated $ |")
    lines.append("|---|---:|---:|---:|")
    for role, (runs, prefix_tokens, cost) in sorted(map_roles(sessions, agents).items(), key=lambda x: -x[1][0]):
        lines.append(f"| `{role}` | {runs} | {prefix_tokens:,} | ${cost:,.2f} |")
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
    text = report(window)
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
