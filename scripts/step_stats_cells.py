"""step-stats.py's printed cells: how a role is named and how a cut's delta is written.

Loaded by step-stats.py, which re-exports every name here; read them from there.
Both functions are pure, so they can be tested without a transcript.
"""

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
    `ext:` so it is never confused with a mode role — except our own plugin's
    agents (`adyusuf:<role>`), which ARE the mode roles and print as `<role>`.
    """
    if role.startswith('adyusuf:'):
        role = role.split(':', 1)[1]
    elif ':' in role:
        return 'ext:' + role.split(':', 1)[1]
    return ROLE_ALIASES.get(role, role)


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
