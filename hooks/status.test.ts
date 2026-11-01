import { expect, test } from 'claude-code/testing'

import { parseStatus, statusBody, statusSummary } from './status'

// A recording factory: an element is { type, props, children }, so the tests read what the box would draw.
type Node = { type: unknown; props: Record<string, any>; children: unknown[] }
const h = (type: unknown, props: Record<string, unknown> | null, ...children: unknown[]): Node => ({ type, props: props ?? {}, children })
const ui = { h, Box: 'Box', Text: 'Text', Button: 'Button' }

function flat(items: unknown[]): unknown[] {
  return items.flatMap(item => (Array.isArray(item) ? flat(item) : item === null || item === '' ? [] : [item]))
}
function all(node: unknown, type: string): Node[] {
  if (typeof node !== 'object' || node === null) return []
  const one = node as Node
  const here = one.type === type ? [one] : []
  return here.concat(...flat(one.children).map(child => all(child, type)))
}
function words(node: unknown): string {
  if (typeof node === 'string') return node
  if (typeof node !== 'object' || node === null) return ''
  return flat((node as Node).children).map(words).join('')
}

const FILE = JSON.stringify({
  now: 'prod gate', next: 'plugin update', updated: '2026-11-01T18:00:00Z',
  rows: [
    { item: 'dev', state: 'pushed', figure: '4a45bda (promote.log)', waiting: '—' },
    { item: 'prod', state: 'gate running', figure: 'coverage step (gate-prod.log)', waiting: 'promote.sh' },
  ],
})

test('the status file is read as text: only strings are kept, anything else is nothing running', () => {
  expect(parseStatus(FILE)?.rows.length).toBe(2)
  expect(parseStatus('not json')).toBe(null)
  expect(parseStatus('[1, 2]')).toBe(null)
  expect(parseStatus('null')).toBe(null)
  const odd = parseStatus(JSON.stringify({ now: 5, rows: [{ item: 'a', state: 1 }, 'x', null] }))
  expect(odd).toEqual({ now: '', next: '', updated: '', rows: [{ item: 'a', state: '', figure: '', waiting: '' }] })
})

test('the summary says what runs now, else how many items, else nothing running', () => {
  expect(statusSummary(null)).toBe('nothing running')
  expect(statusSummary(parseStatus('{}'))).toBe('nothing running')
  expect(statusSummary(parseStatus(FILE))).toBe('prod gate')
  expect(statusSummary(parseStatus(JSON.stringify({ rows: [{ item: 'a' }] })))).toBe('1 item')
  expect(statusSummary(parseStatus(JSON.stringify({ rows: [{ item: 'a' }, { item: 'b' }] })))).toBe('2 items')
})

test('the body shows now and next, then the table under its four headings', () => {
  const body = statusBody(ui, parseStatus(FILE))
  const lines = all(body, 'Box').filter(node => node.props.flexDirection === 'row').map(node => all(node, 'Text').map(words).join(' | '))
  expect(lines).toEqual([
    'Now | prod gate',
    'Next | plugin update',
    'Item | State | Measured figure (signal) | Waiting on',
    'dev | pushed | 4a45bda (promote.log) | —',
    'prod | gate running | coverage step (gate-prod.log) | promote.sh',
  ])
  expect(all(body, 'Text').filter(node => node.props.bold).map(words)).toEqual(['Now', 'Next', 'Item', 'State', 'Measured figure (signal)', 'Waiting on'])
  expect(all(body, 'Text').find(node => words(node) === '—')!.props.dimColor).toBe(true)
})

test('the columns have one width on every row, capped so a long text wraps inside its column', () => {
  const long = 'x'.repeat(80)
  const body = statusBody(ui, parseStatus(JSON.stringify({ rows: [{ item: 'a', state: long, figure: 'f', waiting: 'w' }] })))
  const rows = all(body, 'Box').filter(node => node.props.flexDirection === 'row')
  const widths = rows.map(row => flat(row.children).map(cell => (cell as Node).props.width))
  expect(widths).toEqual([[5, 37, 25, undefined], [5, 37, 25, undefined]])
})

test('an empty table, or none, says nothing running', () => {
  expect(words(statusBody(ui, null))).toBe('nothing running')
  expect(words(statusBody(ui, parseStatus('{"now": "", "rows": []}')))).toBe('nothing running')
  const onlyNow = statusBody(ui, parseStatus('{"now": "tests"}'))
  expect(all(onlyNow, 'Text').map(words)).toEqual(['Now', 'tests'])
})
