// What the chat is told when a setting changes, kept apart from the engine so it can be tested without one: no import from
// 'claude-code'. Every change becomes one warning line: the setting, its old and new value, and the numbered rules of the
// global rule set that the setting steers (user decision 28/10/2026).

type Values = Record<string, boolean | string>
type Layer = { values: Values }
type Spec = { key: string; label: string }
/** What the pane has read: the session's effective settings, the saved defaults (once read) and the schema that labels them. */
export type View = Layer & { schema: Spec[]; saved?: Layer }
export type Change = { key: string; from: unknown; to: unknown }

/** The rules a setting can steer, each in a few words (the full text is in CLAUDE.md). */
export const RULES: Record<string, string> = {
  '#8': 'tests get updated',
  '#19': 'security scanning is automatic',
  '#25': 'the shared gate runs at every promotion',
  '#26': 'work off dev, one commit per task, merged through a gate',
  '#27': 'the operating mode is selectable and the selection is the approval',
  '#28': 'the auditor checks, sends work back and gets it fixed',
  '#29': 'line coverage of at least 80% in every codebase, never waived: with the gate off it runs alone',
  '#31': 'the run cycle: full run, fix, rerun what was fixed',
  '#32': 'all the code first, then the unit tests, then run them',
  '#33': 'e2e is optional and never blocks a promotion',
  '#34': 'merges, pushes and gates follow the configuration, not questions',
}

const RULES_OF: Array<[RegExp, string[]]> = [
  [/^mode$/, ['#27', '#28']],
  [/^mode_model$/, ['#27']],
  [/^agents\./, ['#27', '#28']],
  [/^write\.unit_tests$/, ['#8', '#32', '#29']],
  [/^write\.e2e$/, ['#33', '#31']],
  [/^merge\./, ['#34', '#26']],
  [/^push\./, ['#34', '#26']],
  [/^gates_before_push\./, ['#34', '#25', '#29']],
  [/^ci_after_push\./, ['#34', '#19']],
  [/^e2e_before_deploy\./, ['#33', '#34', '#31']],
]

/** The rule numbers a setting steers (empty when no rule reads it, as with the pod settings). */
export function rulesFor(key: string): string[] {
  const found = RULES_OF.find(([pattern]) => pattern.test(key))
  return found ? found[1] : []
}

/** The keys whose value differs between two reads; nothing when there is no earlier read to compare with. */
export function changesBetween(before: Layer | null | undefined, after: Layer): Change[] {
  if (!before) return []
  return Object.keys(after.values)
    .filter(key => before.values[key] !== after.values[key])
    .map(key => ({ key, from: before.values[key], to: after.values[key] }))
}

const shown = (value: unknown) => (value === true ? 'yes' : value === false ? 'no' : value === undefined ? 'unset' : String(value))

/** One warning line for one change; `scope` says whether it is this session's layer or the saved defaults. */
export function warning(change: Change, scope: string, schema: Spec[]): string {
  const label = schema.find(spec => spec.key === change.key)?.label ?? change.key
  const rules = rulesFor(change.key)
  const tail = rules.length === 0
    ? 'No rule reads this setting.'
    : `Rules in play: ${rules.map(rule => `${rule} ${RULES[rule] ?? ''}`.trim()).join('; ')}.`
  return `⚠ adyusuf setting changed (${scope}): ${label} (${change.key}) ${shown(change.from)} → ${shown(change.to)}. ${tail}`
}

/**
 * The warning lines for what changed between two reads. A saved default that also moved the session's effective value is
 * said once, as the saved change, not again as a session change to the same value.
 */
export function warnings(before: View | null, after: View): string[] {
  if (!before) return []
  const saved = after.saved ? changesBetween(before.saved, after.saved) : []
  const said = new Set(saved.map(change => `${change.key}=${shown(change.to)}`))
  const session = changesBetween(before, after).filter(change => !said.has(`${change.key}=${shown(change.to)}`))
  return [
    ...session.map(change => warning(change, 'this session', after.schema)),
    ...saved.map(change => warning(change, 'saved defaults', after.schema)),
  ]
}

/** The rules of the real operations a shell command can carry (user decision 28/10/2026): a merge, a push, a gate run. */
const OPERATION_RULES: Record<string, string[]> = { merge: ['#26', '#34'], push: ['#34', '#26'], gate: ['#25', '#19', '#29', '#33'] }
const GATE_SCRIPT = /(gate-core|merge-gate|codeql-scan|coverage|gitleaks)/
const STAGES = ['dev', 'test', 'prod']

/** Whether one command segment RUNS a gate or scan script (`bash scripts/gate-core.sh dev`, `gitleaks detect`), past any
 * `VAR=value` prefixes and a `bash`/`sh`/`zsh` launcher; reading or listing one (`cat scripts/coverage.sh`) is not a run. */
function runsGateScript(tokens: string[]): boolean {
  let at = 0
  while (at < tokens.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[at])) at += 1
  if (['bash', 'sh', 'zsh'].includes(tokens[at])) {
    at += 1
    while (at < tokens.length && tokens[at].startsWith('-')) at += 1
  }
  const script = tokens[at] ?? ''
  return GATE_SCRIPT.test(script) && /\.sh$|(^|\/)gitleaks$/.test(script)
}

/** The git subcommand of one command segment ('' when it is not a git call), skipping `-C <dir>` / `-c <k=v>` and other global flags. */
function gitSubcommand(tokens: string[]): string {
  if (tokens[0] !== 'git') return ''
  for (let at = 1; at < tokens.length; at += 1) {
    if (tokens[at] === '-C' || tokens[at] === '-c') at += 1
    else if (!tokens[at].startsWith('-')) return tokens[at]
  }
  return ''
}

/**
 * One warning line per real operation in a shell command - `git merge`, `git push`, a gate or scan script - naming the stages
 * it touches, a forced push, and the rules in play. A command with none of them gives no line.
 */
export function operationWarnings(command: string): string[] {
  const found = new Map<string, Set<string>>()
  for (const segment of command.split(/&&|\|\||[;|\n]/)) {
    const tokens = segment.trim().split(/\s+/).filter(token => token !== '')
    const sub = gitSubcommand(tokens)
    const name = sub === 'merge' || sub === 'push' ? sub : runsGateScript(tokens) ? 'gate' : ''
    if (name === '') continue
    const details = found.get(name) ?? new Set<string>()
    for (const token of tokens) {
      if (name !== 'gate' && /^(--force(-with-lease)?(=.*)?|-f)$/.test(token)) details.add('FORCED')
      // A push touches the DESTINATION of a `src:dst` refspec only: `push origin dev:prod` pushes prod.
      const target = name === 'push' && token.includes(':') ? token.slice(token.lastIndexOf(':') + 1) : token
      for (const part of target.split(/[:/]/)) if (name !== 'gate' && STAGES.includes(part)) details.add(part)
    }
    found.set(name, details)
  }
  return [...found.entries()].map(([name, details]) => {
    const what = name === 'gate' ? 'gate / scan run' : `git ${name}`
    const where = details.size > 0 ? ` (${[...details].join(', ')})` : ''
    const rules = OPERATION_RULES[name].map(rule => `${rule} ${RULES[rule] ?? ''}`.trim()).join('; ')
    const never = details.has('FORCED') ? ' A force push is on the never-do list.' : ''
    return `⚠ adyusuf operation: ${what}${where}. Rules in play: ${rules}.${never}`
  })
}
