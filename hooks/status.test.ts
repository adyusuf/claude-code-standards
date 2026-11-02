import { expect, test } from 'claude-code/testing'

import { donePercent, parseStatus, statusBody, stepGroups, statusDir, statusScript, statusStep } from './status'

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
  expect(odd).toEqual({ now: '', next: '', updated: '', rows: [{ item: 'a', state: '', figure: '', waiting: '', percent: '', blocker: '', agent: '' }] })
  // A percentage is digits only; anything else reads as not given.
  expect(parseStatus(JSON.stringify({ rows: [{ item: 'a', percent: '45' }, { item: 'b', percent: '45%' }, { item: 'c', percent: 7 }] }))!.rows.map(row => row.percent)).toEqual(['45', '', ''])
})

test('the body shows now and next, then the steps under step and state, with done and -> blocker under each step', () => {
  const body = statusBody(ui, parseStatus(FILE))
  const lines = all(body, 'Box').filter(node => node.props.flexDirection === 'row').map(node => all(node, 'Text').map(words).join(' | '))
  expect(lines).toEqual(['Now | prod gate', 'Next | plugin update', 'Step | State', 'dev | pushed', 'prod | gate running'])
  // Under a step, no heading: the done line (an older row's figure) and the arrow to what it waits on; a placeholder is left out.
  const under = all(body, 'Box').filter(node => node.props.marginLeft === 2).map(node => all(node, 'Text').map(words))
  expect(under).toEqual([['4a45bda (promote.log)'], ['coverage step (gate-prod.log)', '-> promote.sh']])
  expect(all(body, 'Text').filter(node => node.props.bold).map(words)).toEqual(['Now', 'Next', 'Step', 'State'])
  // A step is a step: its % under it, -> its blocker, the running one bold.
  const steps = statusBody(ui, parseStatus(JSON.stringify({ rows: [
    { item: '1. data', state: 'done', percent: '100' }, { item: '2. pane', state: 'running', percent: '40', blocker: 'qa review' }] })))
  expect(all(steps, 'Box').filter(node => node.props.marginLeft === 2).map(node => all(node, 'Text').map(words))).toEqual([['100%'], ['40%', '-> qa review']])
  expect(all(steps, 'Text').filter(node => node.props.bold).map(words)).toEqual(['Step', 'State', '2. pane', 'running'])
  expect(all(steps, 'Box').filter(node => node.props.marginLeft === 2).every(node => all(node, 'Text').every(text => text.props.dimColor))).toBe(true)
})

test('the columns have one width on every row, capped so a long text wraps inside its column', () => {
  const long = 'x'.repeat(80)
  const body = statusBody(ui, parseStatus(JSON.stringify({ rows: [{ item: 'a', state: long, figure: 'f', waiting: 'w' }] })))
  const rows = all(body, 'Box').filter(node => node.props.flexDirection === 'row')
  const widths = rows.map(row => flat(row.children).map(cell => (cell as Node).props.width))
  expect(widths).toEqual([[5, undefined], [5, undefined]])
})

test('an empty table, or none, says nothing running', () => {
  expect(words(statusBody(ui, null))).toBe('nothing running')
  expect(words(statusBody(ui, parseStatus('{"now": "", "rows": []}')))).toBe('nothing running')
  const onlyNow = statusBody(ui, parseStatus('{"now": "tests"}'))
  expect(all(onlyNow, 'Text').filter(node => node.props.color !== 'inverseText').map(words)).toEqual(['Now', 'tests'])
})

test('the file is untrusted text: control characters go, each field is one capped line, rows are capped at 50', () => {
  const data = parseStatus(JSON.stringify({ now: 'a\u001b[2Jb\u0007c\u009bd', next: 'x'.repeat(400),
    rows: Array.from({ length: 55 }, (_, at) => ({ item: `i${at}` })).concat([[1, 2] as never]) }))!
  expect(data.now).toBe('a [2Jb c d')
  expect(data.next.length).toBe(300)
  expect(data.next.endsWith('…')).toBe(true)
  expect([data.rows.length, data.rows[0]!.item, data.rows[49]!.item]).toEqual([50, 'i5', 'i54'])
})

test('a refresh reads on a new modification time, keeps on the same one, clears once when the file goes', () => {
  expect(statusStep(-1, { kind: 'file', mtimeMs: 5 })).toEqual({ action: 'read', stamp: 5 })
  expect(statusStep(5, { kind: 'file', mtimeMs: 5 })).toEqual({ action: 'keep', stamp: 5 })
  expect(statusStep(5, { kind: 'file', mtimeMs: 6 })).toEqual({ action: 'read', stamp: 6 })
  expect(statusStep(5, { kind: 'missing' })).toEqual({ action: 'clear', stamp: 0 })
  expect(statusStep(-1, { kind: 'missing' })).toEqual({ action: 'clear', stamp: 0 })
  expect(statusStep(0, { kind: 'missing' })).toEqual({ action: 'keep', stamp: 0 })
})

test('an error keeps the table and resets the stamp, so the next look reads again', () => {
  expect(statusStep(5, { kind: 'error' })).toEqual({ action: 'keep', stamp: -1 })
  expect(statusStep(0, { kind: 'error' })).toEqual({ action: 'keep', stamp: -1 })
  expect(statusStep(-1, { kind: 'file', mtimeMs: 5 }).action).toBe('read')
})

test('the folder: an absolute ADYUSUF_STATUS_DIR, else USERPROFILE, else HOME; nothing usable gives none', () => {
  expect(statusDir('/tmp/st/', 'C:\\Users\\u', '/home/u')).toBe('/tmp/st')
  expect(statusDir('D:\\st', undefined, '/home/u')).toBe('D:\\st')
  expect(statusDir('relative/dir', undefined, '/home/u')).toBe('')
  expect(statusDir(undefined, 'C:\\Users\\u', '/home/u')).toBe('C:\\Users\\u/.claude/adyusuf-status')
  expect(statusDir(undefined, undefined, '/home/u/')).toBe('/home/u/.claude/adyusuf-status')
  expect(statusDir('', '', '')).toBe('')
  expect(statusDir(undefined, undefined, undefined)).toBe('')
})

test('the status script sits beside the configuration script the pane found; none found, none run', () => {
  expect(statusScript('/cache/adyusuf/1a2b/scripts/adyusuf_config.py')).toBe('/cache/adyusuf/1a2b/scripts/adyusuf_status.py')
  expect(statusScript('')).toBe('')
  expect(statusScript('/elsewhere/other.py')).toBe('')
})

test('steps group by who runs them, this session first, each subagent group named with how much of it is done', () => {
  const data = parseStatus(JSON.stringify({ rows: [
    { item: '1. plan', state: 'done', percent: '100' }, { item: 'review', state: 'running', percent: '50', agent: 'qa a9f3c2' },
    { item: '2. build', state: 'running', percent: '20' }, { item: 'scan', state: 'not started', percent: '0', agent: 'qa a9f3c2' }] }))!
  expect(stepGroups(data.rows).map(group => [group.agent, group.rows.map(row => row.item)])).toEqual([
    ['', ['1. plan', '2. build']], ['qa a9f3c2', ['review', 'scan']]])
  expect([donePercent(data.rows.slice(0, 1)), donePercent([]), donePercent(stepGroups(data.rows)[1]!.rows)]).toEqual(['100%', '', '25%'])
  // The mean is rounded, not cut (62.5 -> 63); this session's group comes first even when a subagent wrote first.
  const half = parseStatus(JSON.stringify({ rows: [{ item: 'a', agent: 'qa x', percent: '50' }, { item: 'b', agent: 'qa x', percent: '75' }, { item: 'c', percent: '0' }] }))!
  expect(donePercent(half.rows.slice(0, 2))).toBe('63%')
  expect(stepGroups(half.rows).map(group => group.agent)).toEqual(['', 'qa x'])
  // An older row's placeholder figure is left out under the step, as a placeholder blocker is.
  const older = statusBody(ui, parseStatus(JSON.stringify({ rows: [{ item: 'x', state: 'done', figure: '—', waiting: '-' }] })))
  expect(all(older, 'Box').filter(node => node.props.marginLeft === 2).length).toBe(0)
  const titles = all(statusBody(ui, data), 'Text').filter(node => node.props.dimColor && /·/.test(words(node))).map(words)
  expect(titles).toEqual(['this session · 60%', 'qa a9f3c2 · 25%'])
  // With this session's steps alone, no group line.
  const alone = statusBody(ui, parseStatus(JSON.stringify({ rows: [{ item: '1. plan', state: 'done', percent: '100' }] })))
  expect(all(alone, 'Text').some(node => words(node).startsWith('this session'))).toBe(false)
})
