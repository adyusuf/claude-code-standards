// Pure decisions of the boxes, kept apart from the drawing so they can be tested without an engine.

/**
 * The folder the plugin manager says `id` is installed in, from the text of installed_plugins.json ('' when it
 * names none). Not the newest folder in the cache: a replaced version is marked and then becomes the newest.
 */
export function installPathOf(text: string, id: string): string {
  try {
    const entry = (JSON.parse(text) as { plugins?: Record<string, unknown> }).plugins?.[id]
    const entries = Array.isArray(entry) ? entry : entry ? [entry] : []
    for (const one of entries) {
      const path = (one as { installPath?: unknown }).installPath
      if (typeof path === 'string' && path !== '') return path.replace(/\/$/, '')
    }
  } catch {
    // an unreadable record names nothing
  }
  return ''
}

/** Whether the value the script now reports is the one that was asked for (yes/no settings are booleans). */
export function isWanted(value: unknown, wanted: string): boolean {
  if (typeof value === 'boolean') return value === (wanted === 'yes')
  return String(value) === wanted
}

/** What to write into `agents.<role>.enabled` so that the agent ends up `want` (on/off), given the mode's own set. */
export function enabledFor(want: boolean, inMode: boolean): 'auto' | 'on' | 'off' {
  if (want === inMode) return 'auto'
  return want ? 'on' : 'off'
}

/** `<short sha> <gates> (neden: ...)` for every `Gate-Waived:` line of a `git log --format=@@%h%n%B` output. */
export function waivedLines(log: string): string[] {
  const out: string[] = []
  let sha = ''
  for (const line of log.split('\n')) {
    if (line.startsWith('@@')) sha = line.slice(2)
    else if (line.startsWith('Gate-Waived:')) out.push(`${sha} ${line.slice('Gate-Waived:'.length).trim()}`)
  }
  return out
}

/** The message for a click that changed nothing because a higher layer wins ('' when the click took effect). */
export function overrideNote(key: string, wanted: string, value: unknown, source: string | undefined): string {
  if (isWanted(value, wanted)) return ''
  const from = source && source !== 'default' ? `the ${source} layer` : 'another layer'
  return `${key} stays ${String(value)}: ${from} sets it, and it wins over the user's file`
}

/**
 * The newest installed copy of the plugin that is not marked as replaced, from the lines `live <dir>` / `orphaned <dir>`
 * that register.tsx's shell loop prints newest first ('' when there is none). Only used when the plugin manager's
 * record names no folder.
 */
export function newestLiveDir(output: string): string {
  for (const line of output.split('\n')) {
    const [state, ...rest] = line.trim().split(/\s+/)
    if (state === 'live' && rest.length > 0) return rest.join(' ').replace(/\/$/, '')
  }
  return ''
}

/** The folder that holds the configuration script: the recorded one, else the newest live one in the cache. */
export function scriptDir(recordText: string, id: string, cacheListing: string): string {
  return installPathOf(recordText, id) || newestLiveDir(cacheListing)
}

/** The sections of the Settings box: the groups in schema order, and the settings that are shown (agents have their own box). */
export function settingGroups<T extends { key: string; group: string }>(schema: T[]): { groups: string[]; shown: T[] } {
  const shown = schema.filter(spec => !spec.key.startsWith('agents.'))
  const groups: string[] = []
  for (const spec of shown) if (!groups.includes(spec.group)) groups.push(spec.group)
  return { groups, shown }
}

export type PlannedStage = { branch: string; previous: string; local: boolean }

/** The promotion stages to read, in order: a stage exists when `origin/<branch>` does; `previous` is the stage before it. */
export function plannedStages(have: Set<string>, order: readonly string[] = ['dev', 'test', 'prod']): PlannedStage[] {
  const out: PlannedStage[] = []
  order.forEach((branch, index) => {
    if (!have.has(`origin/${branch}`)) return
    const previous = index > 0 && have.has(`origin/${order[index - 1]}`) ? order[index - 1] : ''
    out.push({ branch, previous, local: have.has(branch) })
  })
  return out
}

/** The git range of commits that reached `branch`'s origin from its previous stage's origin ('' for the first stage). */
export function waivedRange(stage: PlannedStage): string {
  return stage.previous ? `origin/${stage.branch}..origin/${stage.previous}` : ''
}

/** The number in git's `--count` output (0 when it is not one). */
export function countOf(text: string): number {
  return Number(text.trim()) || 0
}

/** The refs git printed, one per line, as a set. */
export function refSet(text: string): Set<string> {
  return new Set(text.split('\n').map(line => line.trim()).filter(Boolean))
}
