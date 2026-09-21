#!/usr/bin/env python3
"""Cost by DAY and PROJECT, ROLE, KIND or MODEL — from the measurement ledger, one file each.

Usage:
    python3 scripts/measurement-report.py                    # ledger beside this repo -> both report files beside it
    python3 scripts/measurement-report.py --ledger PATH      # another ledger
    python3 scripts/measurement-report.py --out PATH         # the by-project file elsewhere
    python3 scripts/measurement-report.py --role-out PATH    # the by-role file elsewhere
    python3 scripts/measurement-report.py --kind-out PATH    # the by-kind file elsewhere
    python3 scripts/measurement-report.py --model-out PATH   # the by-model file elsewhere

Files:  measurement-daily-by-project.md   day x project (nicknames)
        measurement-daily-by-role.md      day x role (main = the conversation itself; the rest are agent roles)
        measurement-daily-by-kind.md      day x kind (session = a conversation, agent = a delegated run)
        measurement-daily-by-model.md     day x model (a row is filed under the FIRST model it used)

measurement-ledger.py rewrites the report whenever it writes the ledger, so it is always
as fresh as the ledger.

⚠️ Projects appear only under their NICKNAME (project-nicknames.tsv, local and git-ignored);
   a project without one shows as unmapped-xxxxxx. The report holds no real project name.
⚠️ A day is a LOCAL calendar day, and a row is charged WHOLE to the day its session ENDED (the
   last record of the transcript). A session that runs past midnight therefore lands on its last
   day, and a session still running moves forward with it. A row with no recorded end (written
   before the ledger kept one) is charged to the day it STARTED and marked ≈.
⚠️ USD is the API LIST price, a proxy for consumption, not a bill.
"""
import collections
import datetime
import importlib.util
import os
import statistics
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
OUT_NAME = 'measurement-daily-by-project.md'
ROLE_OUT_NAME = 'measurement-daily-by-role.md'
KIND_OUT_NAME = 'measurement-daily-by-kind.md'
MODEL_OUT_NAME = 'measurement-daily-by-model.md'


def load_ledger_module():
    spec = importlib.util.spec_from_file_location('measurement_ledger', os.path.join(HERE, 'measurement-ledger.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def charged_day(row):
    """(local calendar day, guessed?) a row is charged to: the day the session ENDED; if the ledger
    did not record an end (older rows), the day it started, and the day is marked as a guess."""
    stamp, guessed = (row['ended'], False) if row.get('ended') else (row['started'], True)
    when = datetime.datetime.strptime(stamp, '%Y-%m-%dT%H:%M').replace(tzinfo=datetime.timezone.utc)
    return when.astimezone().strftime('%Y-%m-%d'), guessed


def step_hours(row):
    if not row.get('step_seconds'):
        return 0.0
    return sum(int(part.rsplit('=', 1)[1]) for part in row['step_seconds'].split(';')) / 3600


def money(value):
    if value <= 0:
        return '·'
    if value >= 100:
        return f'${value:,.0f}'
    return f'${value:,.1f}' if value >= 1 else f'${value:,.2f}'


def dmy(day):
    year, month, date = day.split('-')
    return f'{date}/{month}/{year}'


def aggregate(rows, key=lambda row: row.get('project') or 'unknown'):
    cost = collections.defaultdict(lambda: collections.defaultdict(float))
    approx = set()
    sessions = collections.defaultdict(lambda: collections.Counter())
    agents = collections.defaultdict(lambda: collections.Counter())
    per_project = collections.defaultdict(lambda: collections.Counter())
    approx_rows = 0
    runs = collections.defaultdict(list)
    for row in rows:
        project = key(row)
        day, guessed = charged_day(row)
        value = float(row['usd'])
        approx_rows += guessed
        cost[day][project] += value
        (sessions if row['kind'] == 'session' else agents)[day][project] += 1
        if guessed:
            approx.add((day, project))
        totals = per_project[project]
        totals['usd'] += value
        totals['requests'] += int(row['requests'])
        totals['step_hours'] += step_hours(row)
        totals['sessions' if row['kind'] == 'session' else 'agents'] += 1
        totals['agent_usd' if row['kind'] == 'agent' else 'session_usd'] += value
        runs[project].append(value)
    return cost, approx, sessions, agents, per_project, approx_rows, runs


def render(rows, now=None):
    cost, approx, sessions, agents, per_project, approx_rows, _runs = aggregate(rows)
    now = now or datetime.datetime.now()
    days = sorted(cost, reverse=True)
    projects = sorted(per_project, key=lambda p: -per_project[p]['usd'])
    total = sum(t['usd'] for t in per_project.values())
    out = [
        '# Measurement report — cost by day and project',
        '',
        f'> Generated {now.strftime("%d/%m/%Y %H:%M")} from {len(rows)} ledger rows · list-price USD, a proxy not a bill · '
        'nicknames only · a day is the local calendar day a session ENDED.',
        '> Generated file, local and git-ignored: do not edit.',
    ]
    if approx_rows:
        out.append(f'> {approx_rows} of {len(rows)} rows have no recorded end time: each is charged to the day it '
                   'started and marked ≈. Rebuild them with `measurement-ledger.py --write --days N` while their transcripts exist.')
    unmapped = [p for p in projects if p.startswith('unmapped-') or p == 'unknown']
    if unmapped:
        out.append(f'> ⚠️ No nickname for: {", ".join(unmapped)} — add `<real folder key><TAB><nickname>` to `project-nicknames.tsv`.')
    out += ['', f'## Cost by project — ${total:,.0f} over {len(days)} day(s)', '',
            '| project | $ | share | days | sessions | agent runs | agent $ share | requests | step hours |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for project in projects:
        t = per_project[project]
        active = sum(1 for day in days if cost[day].get(project))
        out.append(f'| {project} | {money(t["usd"])} | {100 * t["usd"] / total:.0f}% | {active} | {t["sessions"]} | {t["agents"]} | '
                   f'{100 * t["agent_usd"] / t["usd"]:.0f}% | {t["requests"]:,} | {t["step_hours"]:.1f} |' if total and t['usd'] else
                   f'| {project} | · | · | 0 | {t["sessions"]} | {t["agents"]} | · | {t["requests"]:,} | {t["step_hours"]:.1f} |')
    out += ['', '## Day × project ($)', '', '| day | ' + ' | '.join(projects) + ' | **day total** |',
            '|---|' + '---:|' * (len(projects) + 1)]
    for day in days:
        cells = [('≈' if (day, p) in approx and cost[day].get(p) else '') + money(cost[day].get(p, 0)) for p in projects]
        out.append(f'| {dmy(day)} | ' + ' | '.join(cells) + f' | **{money(sum(cost[day].values()))}** |')
    out.append('| **project total** | ' + ' | '.join(f'**{money(per_project[p]["usd"])}**' for p in projects) + f' | **{money(total)}** |')
    out += ['', '## By day']
    for day in days:
        out += ['', f'### {dmy(day)} — {money(sum(cost[day].values()))}', '', '| project | $ | sessions | agent runs |', '|---|---:|---:|---:|']
        for project in sorted(cost[day], key=lambda p: -cost[day][p]):
            mark = '≈' if (day, project) in approx else ''
            out.append(f'| {project} | {mark}{money(cost[day][project])} | {sessions[day][project]} | {agents[day][project]} |')
    return '\n'.join(out) + '\n'


def render_by(rows, noun, key, extra_note, now=None):
    """One day x <noun> report; `key` picks the group of a row."""
    cost, approx, _sessions, _agents, per_role, approx_rows, runs = aggregate(rows, key=key)
    now = now or datetime.datetime.now()
    days = sorted(cost, reverse=True)
    roles = sorted(per_role, key=lambda r: -per_role[r]['usd'])
    total = sum(t['usd'] for t in per_role.values())
    out = [
        f'# Measurement report — cost by day and {noun}',
        '',
        f'> Generated {now.strftime("%d/%m/%Y %H:%M")} from {len(rows)} ledger rows · list-price USD, a proxy not a bill · '
        'a day is the local calendar day a run ENDED.',
        f'> {extra_note}Generated file, local and git-ignored: do not edit.',
    ]
    if approx_rows:
        out.append(f'> {approx_rows} of {len(rows)} rows have no recorded end time: each is charged to the day it '
                   'started and marked ≈. Rebuild them with `measurement-ledger.py --write --days N` while their transcripts exist.')
    out += ['', f'## Cost by {noun} — ${total:,.0f} over {len(days)} day(s)', '',
            f'| {noun} | $ | share | days | runs | median $/run | requests | step hours |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for role in roles:
        t = per_role[role]
        active = sum(1 for day in days if cost[day].get(role))
        count = t['sessions'] + t['agents']
        out.append(f'| {role} | {money(t["usd"])} | {100 * t["usd"] / total:.0f}% | {active} | {count} | '
                   f'{money(statistics.median(runs[role]))} | {t["requests"]:,} | {t["step_hours"]:.1f} |' if total else
                   f'| {role} | · | · | 0 | {count} | · | {t["requests"]:,} | {t["step_hours"]:.1f} |')
    out += ['', f'## Day × {noun} ($)', '', '| day | ' + ' | '.join(roles) + ' | **day total** |', '|---|' + '---:|' * (len(roles) + 1)]
    for day in days:
        cells = [('≈' if (day, r) in approx and cost[day].get(r) else '') + money(cost[day].get(r, 0)) for r in roles]
        out.append(f'| {dmy(day)} | ' + ' | '.join(cells) + f' | **{money(sum(cost[day].values()))}** |')
    out.append(f'| **{noun} total** | ' + ' | '.join(f'**{money(per_role[r]["usd"])}**' for r in roles) + f' | **{money(total)}** |')
    out += ['', '## By day']
    for day in days:
        out += ['', f'### {dmy(day)} — {money(sum(cost[day].values()))}', '', f'| {noun} | $ | runs |', '|---|---:|---:|']
        for role in sorted(cost[day], key=lambda r: -cost[day][r]):
            mark = '≈' if (day, role) in approx else ''
            out.append(f'| {role} | {mark}{money(cost[day][role])} | {_sessions[day][role] + _agents[day][role]} |')
    return '\n'.join(out) + '\n'


def render_by_role(rows, now=None):
    return render_by(rows, 'role', lambda row: row.get('role') or 'unknown',
                     '`main` is the conversation itself; every other role is an agent run. ', now)


def render_by_kind(rows, now=None):
    return render_by(rows, 'kind', lambda row: row.get('kind') or 'unknown',
                     '`session` is a conversation; `agent` is a delegated run started from one. ', now)


def write_report(ledger_path, out_path=None, now=None):
    ledger = load_ledger_module()
    rows = [r for r in ledger.read_ledger(ledger_path).values() if r.get('usd')]
    out_path = out_path or os.path.join(os.path.dirname(ledger_path), OUT_NAME)
    ledger.write_atomically(out_path, render(sorted(rows, key=lambda r: (r['started'], r['id'])), now))
    return out_path


def render_by_model(rows, now=None):
    return render_by(rows, 'model', lambda row: row.get('model') or 'unknown',
                     'The ledger keeps ONE model per row (the first the run used): a run that switched models is filed whole '
                     'under the first. ', now)


def write_model_report(ledger_path, out_path=None, now=None):
    return _write(ledger_path, out_path or os.path.join(os.path.dirname(ledger_path), MODEL_OUT_NAME), render_by_model, now)


def write_role_report(ledger_path, out_path=None, now=None):
    return _write(ledger_path, out_path or os.path.join(os.path.dirname(ledger_path), ROLE_OUT_NAME), render_by_role, now)


def write_kind_report(ledger_path, out_path=None, now=None):
    return _write(ledger_path, out_path or os.path.join(os.path.dirname(ledger_path), KIND_OUT_NAME), render_by_kind, now)


def _write(ledger_path, out_path, renderer, now):
    ledger = load_ledger_module()
    rows = [r for r in ledger.read_ledger(ledger_path).values() if r.get('usd')]
    ledger.write_atomically(out_path, renderer(sorted(rows, key=lambda r: (r['started'], r['id'])), now))
    return out_path


def write_reports(ledger_path, now=None):
    """All report files (by project, role, kind and model); returns their paths."""
    return (write_report(ledger_path, now=now), write_role_report(ledger_path, now=now),
            write_kind_report(ledger_path, now=now), write_model_report(ledger_path, now=now))


def main(argv):
    ledger_module = load_ledger_module()
    ledger_path = argv[argv.index('--ledger') + 1] if '--ledger' in argv else ledger_module.LEDGER
    out_path = argv[argv.index('--out') + 1] if '--out' in argv else None
    role_out = argv[argv.index('--role-out') + 1] if '--role-out' in argv else None
    kind_out = argv[argv.index('--kind-out') + 1] if '--kind-out' in argv else None
    model_out = argv[argv.index('--model-out') + 1] if '--model-out' in argv else None
    print('written:', write_report(ledger_path, out_path))
    print('written:', write_role_report(ledger_path, role_out))
    print('written:', write_kind_report(ledger_path, kind_out))
    print('written:', write_model_report(ledger_path, model_out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
