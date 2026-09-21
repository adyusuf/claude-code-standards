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
import glob, json, os, pathlib, re, sys, datetime, statistics, collections

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
    ('local ci gate',    r'merge-gate\.sh|gate-core\.sh|ci-local\.sh'),
    ('md size gate',     r'md-size-gate\.sh'),
    ('md rule gate',     r'md-rule-gate\.py'),
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

# --- Sanitiser: an example command must never carry an identifier ---------------
# Layer 1: publish the SHAPE, not the arguments — you cannot leak what you never emit.
# Layer 2: a deny-set DERIVED AT RUNTIME from the machine. Project names are never
#          written into this file: doing so would publish the very names we redact.
# Layer 3: a canary gate. If the sanitiser stops working, nothing is written.

SHELL_OP = re.compile(r"\s(\||\|\||&&|;|>>?|2>&1)")
HEXISH = re.compile(r"^[0-9a-f]{7,40}$", re.I)
SAFE_WORDS = {'src', 'test', 'tests', 'docs', 'doc', 'scripts', 'script', 'build',
              'dist', 'node_modules', 'main', 'dev', 'test', 'prod', 'claude',
              'claude-code-standards', 'claude-code-standards-dev', 'code', 'home',
              'users', 'tmp', 'private', 'backend', 'frontend', 'mobile', 'web', 'api',
              'config', 'plugin', 'plugins', 'role', 'roles', 'scan', 'agent', 'agents',
              'session', 'sessions', 'step', 'steps', 'cut', 'cuts', 'measurement',
              'worktrees', 'worktree', 'project', 'projects', 'standards', 'modes'}
_DENY = False


def deny_pattern():
    """Identifiers to redact, computed locally. Never hard-coded — a blocklist of
    client names living in a public repo would publish exactly what it hides."""
    global _DENY
    if _DENY is not False:
        return _DENY
    names = set()
    here = pathlib.Path(__file__).resolve().parent.parent
    for parent in (here.parent, pathlib.Path.home() / 'ClaudeCode'):
        try:
            names |= {d.name for d in parent.iterdir() if d.is_dir()}
        except OSError:
            pass
    for path in glob.glob(os.path.expanduser('~/.claude/projects/*')):
        # '-Users-me-ClaudeCode-acme' → only the last segment is the project name;
        # splitting on every '-' produced generic words and blocked the gate on prose.
        segments = [seg for seg in os.path.basename(path).split('-') if seg]
        if segments:
            names.add(segments[-1])
    names = {n for n in names
             if len(n) > 3 and not n.isdigit() and n.lower() not in SAFE_WORDS}
    _DENY = (re.compile('|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)), re.I)
             if names else None)
    return _DENY


def shape(command, deny=None):
    """Reduce a command to executable + subcommand + flag names. Every value
    becomes a placeholder, so paths, project names, SHAs and secrets cannot ride along."""
    head = SHELL_OP.split(command.strip(), 1)[0]
    out = []
    for index, token in enumerate(head.split()):
        if index == 0:
            if '=' in token:
                out.append('<var>')          # L=/tmp/x.log; cmd — basename would keep the tail
            elif '/' in token or token.startswith(('~', '$')):
                out.append('<path>')
            else:
                base = os.path.basename(token)
                out.append(base if re.fullmatch(r"[A-Za-z0-9._+-]{1,20}", base) else '<cmd>')
        elif token.startswith('-'):
            out.append(token.split('=')[0])
        elif index == 1 and token.isalpha():
            out.append(token)
        elif '/' in token or token.startswith('~') or token.startswith('$'):
            out.append('<path>')
        elif HEXISH.match(token):
            out.append('<sha>')
        elif '=' in token:
            out.append('<var>')
        elif '.' in token:
            out.append('<file>')
        else:
            out.append('<arg>')
    text = ' '.join(out)
    if deny is None:
        deny = deny_pattern()
    if deny is not None:
        text = deny.sub('<project>', text)
    text = re.sub(r"(<\w+>)( \1)+", r"\1 …", text)
    return text[:64]


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


def scan_output(text):
    """Belt: scan the generated document itself. The gate has to live in the
    generator, because the file says 'do not edit by hand, regenerate'.

    Hard patterns run over the whole document. The deny-set runs ONLY inside
    backticked spans, i.e. where command samples live — applied to prose it fired
    on ordinary words ('config', 'role', 'scan') and blocked every write, and a
    brake that always fires gets switched off."""
    hits = re.findall(r"/Users/\S+|/home/\S+|/private/tmp\S*|\b[0-9a-f]{20,40}\b", text)
    deny = deny_pattern()
    if deny is not None:
        for span in re.findall(r"`([^`]*)`", text):
            hits += deny.findall(span)
    return sorted(set(hits))



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
                        best[name] = (score, shape(command))
    return counts, {k: v[1] for k, v in best.items()}, dismissed


ROLE_ALIASES = {'analiz': 'analyst', 'belge': 'doc-writer', 'e2e-yazar': 'e2e-writer',
                'gelistirici': 'developer', 'gozlemlenebilirlik': 'observability',
                'guvenlik': 'security', 'kapsam-denetcisi': 'coverage-auditor',
                'mimar': 'architect', 'tasarimci': 'designer', 'test-yazar': 'test-writer',
                'urun-yoneticisi': 'product-manager', 'veri': 'data'}


def role_label(role):
    """How a role is PRINTED.

    A plugin-provided agent's subagent_type is `<plugin>:<agent>` and the plugin
    part is a machine identifier — exactly what the sanitiser refuses to publish,
    so it would block the whole write (measured: one `agent-skills`
    run made `--write` impossible). Only the agent part is printed, marked
    `ext:` so it is never confused with a mode role.
    """
    if ':' in role:
        return 'ext:' + role.split(':', 1)[1]
    return ROLE_ALIASES.get(role, role)


def role_ids(sessions):
    """agentId (8 hex) -> the role named in the Agent call that started it."""
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
    return id_to_role


def map_roles(sessions, agents):
    """Match the role named in the Agent call with the agentId in its result."""
    id_to_role = role_ids(sessions)
    stats = collections.defaultdict(lambda: [0, 0, 0.0])   # runs, prefix tokens, $
    for path, (first, _count, cost, _model) in measure(agents).items():
        role = id_to_role.get(os.path.basename(path)[6:14], 'unknown')
        row = stats[role]
        row[0] += 1
        row[1] += first or 0
        row[2] += cost
    return stats


MIN_CUT_ROWS = 3   # docs/benchmark-method.md: a side with fewer than three rows makes the comparison invalid


def cut_delta(before_median, before_n, after_median, after_n):
    """The delta cell of one cut row. Pure, so it can be tested.

    Two rules this used to break, both measured:
      · the sign was hard-coded to '-', so a prefix that GREW was published as a
        saving ("--8,598 (--10%)" for +8,598);
      · a delta was published from a single session after the cut, although
        docs/benchmark-method.md calls a side with fewer than three rows invalid.
    """
    if not after_n:
        return "**not measured** — needs a new session"
    if before_n < MIN_CUT_ROWS or after_n < MIN_CUT_ROWS:
        side = 'after' if after_n < MIN_CUT_ROWS else 'before'
        return (f"**not measured** — only {min(before_n, after_n)} session(s) {side} the cut, "
                f"{MIN_CUT_ROWS} needed (docs/benchmark-method.md)")
    if not before_median:
        return "**not measured** — no before median"
    diff = after_median - before_median
    sign = '+' if diff > 0 else ''
    return f"**{sign}{diff:,} ({sign}{100 * diff / before_median:.0f}%)**"


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
    index = 0
    for line in open(cuts_file, encoding='utf-8'):
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
