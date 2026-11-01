// What the Status box of the adyusuf pane shows: this session's status table (user decision 01/11/2026), the same table
// `standards/00-working-method.md` §10 asks for in a reply during a long run. Engine-free like boxes.ts, so a test hands in
// a recording factory. The file is written by scripts/adyusuf_status.py; register.tsx reads it and hands its text here.
import type { Ui } from './boxes'

type StatusRow = { item: string; state: string; figure: string; waiting: string }
export type StatusData = { now: string; next: string; rows: StatusRow[]; updated: string }

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
  const str = (value: unknown) => (typeof value === 'string' ? value : '')
  const rows = (Array.isArray(one.rows) ? one.rows : [])
    .filter((row): row is Record<string, unknown> => typeof row === 'object' && row !== null)
    .map(row => ({ item: str(row.item), state: str(row.state), figure: str(row.figure), waiting: str(row.waiting) }))
  return { now: str(one.now), next: str(one.next), rows, updated: str(one.updated) }
}

const busy = (data: StatusData | null): data is StatusData =>
  data !== null && (data.now !== '' || data.next !== '' || data.rows.length > 0)

export function statusSummary(data: StatusData | null): string {
  if (!busy(data)) return 'nothing running'
  return data.now !== '' ? data.now : `${data.rows.length} item${data.rows.length === 1 ? '' : 's'}`
}

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
      h(ui.Text, bold ? { bold: true } : at === 0 ? {} : { dimColor: text === '—' || text === '-' }, text))))
  const said = (title: string, text: string) => (text === ''
    ? null
    : h(ui.Box, { flexDirection: 'row', columnGap: 1 }, h(ui.Box, { minWidth: 6, flexShrink: 0 }, h(ui.Text, { bold: true }, title)), h(ui.Text, {}, text)))
  return h(ui.Box, { flexDirection: 'column' },
    said('Now', data.now),
    said('Next', data.next),
    data.rows.length === 0 ? null : h(ui.Box, { flexDirection: 'column', marginTop: 1 },
      cellsOf(heads, true),
      data.rows.map(row => cellsOf(fields(row), false))))
}
