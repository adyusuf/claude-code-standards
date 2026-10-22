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
