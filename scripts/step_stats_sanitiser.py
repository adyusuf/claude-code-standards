"""step-stats.py's sanitiser: an example command must never carry an identifier.

Loaded by step-stats.py, which re-exports every public name here; read them from there.

Layer 1: publish the SHAPE, not the arguments — you cannot leak what you never emit.
Layer 2: a deny-set DERIVED AT RUNTIME from the machine. Project names are never
         written into this file: doing so would publish the very names we redact.
Layer 3: a canary gate. If the sanitiser stops working, nothing is written
         (`sanitizer_gate`, in step-stats.py).
"""
import glob, os, pathlib, re

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
