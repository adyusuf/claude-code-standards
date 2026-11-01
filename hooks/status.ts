// What the Status box of the adyusuf pane shows: this session's status table (user decision 01/11/2026), the same table
// `standards/00-working-method.md` §10 asks for in a reply during a long run. Engine-free like boxes.ts, so a test hands in
// a recording factory. The file is written by scripts/adyusuf_status.py; register.tsx reads it and hands its text here.
import type { Ui } from './boxes'
import { helpCard, hoverable } from './controls'
import { STATUS_HELP } from './help'

type StatusRow = { item: string; state: string; figure: string; waiting: string }
export type StatusData = { now: string; next: string; rows: StatusRow[]; updated: string }

/** The same caps as scripts/adyusuf_status.py: the file is read as untrusted text, so a foreign file cannot flood the box. */
const MAX_ROWS = 50
const MAX_TEXT = 300
// eslint-disable-next-line no-control-regex
const CONTROL = /[\u0000-\u001f\u007f-\u009f]/g

/** One line, no control characters (an escape sequence must not reach the terminal), at most MAX_TEXT characters. */
function clean(value: unknown): string {
  if (typeof value !== 'string') return ''
  const flat = value.replace(CONTROL, ' ').split(/\s+/).filter(Boolean).join(' ')
  return flat.length <= MAX_TEXT ? flat : `${flat.slice(0, MAX_TEXT - 1)}…`
}

/**
 * The status folder (user decision 01/11/2026): an absolute ADYUSUF_STATUS_DIR, else `.claude/adyusuf-status` in the home
 * folder, USERPROFILE first as Python's expanduser takes it on Windows, then HOME. '' when none is usable: a relative
 * folder would resolve against another directory here than in the script that writes it.
 */
export function statusDir(chosen?: string, profile?: string, home?: string): string {
  if (chosen) return /^([A-Za-z]:)?[\\/]/.test(chosen) ? chosen.replace(/[\\/]+$/, '') : ''
  const base = profile || home
  return base ? `${base.replace(/[\\/]+$/, '')}/.claude/adyusuf-status` : ''
}

/** What a refresh found: no file, a file and its modification time, or an error (unreadable, denied). */
export type StatusProbe = { kind: 'missing' } | { kind: 'error' } | { kind: 'file'; mtimeMs: number }

/**
 * What a refresh does, from the stamp of the last read and what it found now: `read` the file (a new modification time),
 * `clear` the box (the file went away), or `keep` it. An error keeps the box as it was and resets the stamp, so the
 * next look reads again instead of trusting an old stamp.
 */
export function statusStep(stamp: number, probe: StatusProbe): { action: 'keep' | 'clear' | 'read'; stamp: number } {
  if (probe.kind === 'error') return { action: 'keep', stamp: -1 }
  if (probe.kind === 'missing') return stamp === 0 ? { action: 'keep', stamp: 0 } : { action: 'clear', stamp: 0 }
  return probe.mtimeMs === stamp ? { action: 'keep', stamp } : { action: 'read', stamp: probe.mtimeMs }
}

/**
 * The status file as the box reads it; null for an empty, unreadable or foreign file, which the box shows as nothing
 * running. Only strings are kept: the file is written by a script, but read here as untrusted text.
 */
export function parseStatus(text: string): StatusData | null {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    return null
  }
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) return null
  const one = raw as Record<string, unknown>
  const rows = (Array.isArray(one.rows) ? one.rows : [])
    .filter((row): row is Record<string, unknown> => typeof row === 'object' && row !== null && !Array.isArray(row))
    .slice(-MAX_ROWS)
    .map(row => ({ item: clean(row.item), state: clean(row.state), figure: clean(row.figure), waiting: clean(row.waiting) }))
  return { now: clean(one.now), next: clean(one.next), rows, updated: clean(one.updated) }
}

const busy = (data: StatusData | null): data is StatusData =>
  data !== null && (data.now !== '' || data.next !== '' || data.rows.length > 0)

/** A cap on one table column, in cells: a longer text wraps inside its column instead of pushing the next one away. */
const STATUS_COLUMN = 36

/** The status table (user decision 01/11/2026): what runs now and next, then item · state · figure · waiting on. */
export function statusBody(ui: Ui, data: StatusData | null) {
  const { h } = ui
  if (!busy(data)) return h(ui.Text, { dimColor: true }, 'nothing running')
  const heads = ['Item', 'State', 'Measured figure (signal)', 'Waiting on']
  const fields = (row: StatusRow) => [row.item, row.state, row.figure, row.waiting]
  const widths = heads.map((head, at) =>
    Math.min(STATUS_COLUMN, Math.max(head.length, ...data.rows.map(row => (fields(row)[at] ?? '').length))) + 1)
  const cellsOf = (texts: string[], bold: boolean) => h(ui.Box, { flexDirection: 'row', columnGap: 1 },
    texts.map((text, at) => h(ui.Box, at < texts.length - 1 ? { width: widths[at], flexShrink: 0 } : { flexGrow: 1 },
      bold ? hoverable(ui, `status-${text}`, h(ui.Text, { bold: true }, text)) : h(ui.Text, at === 0 ? {} : { dimColor: text === '—' || text === '-' }, text))))
  const said = (title: string, text: string) => (text === ''
    ? null
    : [h(ui.Box, { flexDirection: 'row', columnGap: 1 },
      h(ui.Box, { minWidth: 6, flexShrink: 0 }, hoverable(ui, `status-${title}`, h(ui.Text, { bold: true }, title))), h(ui.Text, {}, text)),
    helpCard(ui, `status-${title}`, STATUS_HELP[title])])
  return h(ui.Box, { flexDirection: 'column' },
    said('Now', data.now),
    said('Next', data.next),
    data.rows.length === 0 ? null : h(ui.Box, { flexDirection: 'column', marginTop: 1 },
      cellsOf(heads, true),
      heads.map(head => helpCard(ui, `status-${head}`, STATUS_HELP[head])),
      data.rows.map(row => cellsOf(fields(row), false))))
}
