"""step-stats.py's transcript readers: prices, step patterns, per-transcript cost, agent roles.

Loaded by step-stats.py, which re-exports every name here; read them from there.
Nothing here reads TRANSCRIPTS: every reader takes the paths it is given.
"""
import collections, json, os, re

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


def measure(paths):
    """path -> (first-request prefix, request count, estimated $, model)"""
    result = {}
    for path in paths:
        first = model = None
        count, cost = 0, 0.0
        with open(path, errors='ignore') as handle:
            for line in handle:
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


def role_ids(sessions):
    """agentId (8 hex) -> the role named in the Agent call that started it."""
    id_to_role = {}
    for path in sessions:
        pending = {}
        with open(path, errors='ignore') as handle:
            for line in handle:
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
