import { expect, test } from 'claude-code/testing'

import { agentsBody, ROW_LABELS, ROWS, SECTIONS, section, settingsBody } from './boxes'
import { COLUMN_HELP, ROW_HELP, SECTION_HELP, STATUS_HELP } from './help'
import { parseStatus, statusBody } from './status'

// The hover cards (user decision 01/11/2026): a label joins a hover group, and a hidden row of the same group, right after
// the label's line, opens while the pointer rests on it. A recording factory lets the tests read what would be drawn.
type Node = { type: unknown; props: Record<string, any>; children: unknown[] }
const h = (type: unknown, props: Record<string, unknown> | null, ...children: unknown[]): Node => ({ type, props: props ?? {}, children })
const ui = { h, Box: 'Box', Text: 'Text', Button: 'Button' }

function flat(items: unknown[]): unknown[] {
  return items.flatMap(item => (Array.isArray(item) ? flat(item) : item === null || item === '' ? [] : [item]))
}
function all(node: unknown, type: string): Node[] {
  if (typeof node !== 'object' || node === null) return []
  const one = node as Node
  return (one.type === type ? [one] : []).concat(...flat(one.children).map(child => all(child, type)))
}
function words(node: unknown): string {
  if (typeof node === 'string') return node
  if (typeof node !== 'object' || node === null) return ''
  return flat((node as Node).children).map(words).join('')
}
const isCard = (node: unknown) => (node as Node).props?.display === 'none'
const scope = (node: Node) => String(node.props.hover?.scope)
/** The label a card belongs to: the visible Box of the same hover group. */
const labelOf = (body: unknown, card: Node) =>
  words(all(body, 'Box').find(node => !isCard(node) && node.props.hover?.scope === scope(card)))
/** Each card with the line it follows in the same container (the nearest sibling before it that is not a card). */
function placed(body: unknown): Array<[string, string]> {
  return all(body, 'Box').flatMap(box => {
    const kids = flat(box.children)
    return kids.flatMap((kid, at) => {
      if (!isCard(kid)) return []
      const before = kids.slice(0, at).reverse().find(one => !isCard(one))
      return before === undefined ? [] : [[labelOf(body, kid as Node), words(before)] as [string, string]]
    })
  })
}

// One spec for every key a Settings row draws, so every row shows.
type Spec = { key: string; type: 'bool' | 'enum'; label: string; group: string; options?: string[] }
const SCHEMA = ROWS.flatMap((row): Spec[] => ('items' in row
  ? row.items.map(item => ({ key: item.key, type: 'bool' as const, label: item.name, group: 'g' }))
  : [{ key: row.key, type: 'enum' as const, label: row.label, group: 'g', options: ['one', 'two'] }]))
const data = (over: Record<string, unknown> = {}) => ({
  schema: [{ key: 'mode', type: 'enum' as const, label: 'Working mode', group: 'Session', options: ['A', 'B', 'C'] }],
  values: { mode: 'B' }, sources: {}, saved: { values: { mode: 'C' }, sources: {} }, agents: [], ...over,
})

test('every Settings row label has a card text, and every card text a row', () => {
  expect(Object.keys(ROW_HELP).sort()).toEqual([...ROW_LABELS].sort())
  expect(Object.values({ ...ROW_HELP, ...SECTION_HELP, ...COLUMN_HELP, ...STATUS_HELP }).every(text => text.length > 10)).toBe(true)
})

test('a card is a hidden row of its label hover group, readable in either theme, not placed over other rows', () => {
  const box = section(ui, 'settings', 'Settings', false, () => undefined, 'BODY') as Node
  const card = flat(box.children).find(isCard) as Node
  expect(card.props.hover).toEqual({ scope: 'adyusuf-help-section-settings', display: 'flex' })
  expect([card.props.position, card.props.top, card.props.width]).toEqual([undefined, undefined, undefined])
  expect([card.props.backgroundColor, all(card, 'Text')[0]!.props.color]).toEqual(['text', 'inverseText'])
  expect(words(card)).toBe(SECTION_HELP.settings)
  // The Settings card says the settings are for code work, and what a task with no code still uses.
  expect(['for code in a project', 'no code uses only Replies and Status'].every(part => SECTION_HELP.settings.includes(part))).toBe(true)
})

test('a box title card sits right after the header, before the body, folded or open', () => {
  for (const id of SECTIONS) {
    for (const folded of [false, true]) {
      const box = section(ui, id, id, folded, () => undefined, 'BODY') as Node
      const kids = flat(box.children)
      expect(isCard(kids[1])).toBe(true)
      expect(labelOf(box, kids[1] as Node)).toBe(id)
    }
  }
})

test('each Settings card follows its own label line; the System card only when System is drawn', () => {
  const body = settingsBody(ui, data({ schema: SCHEMA, values: {} }), '', [], () => undefined)
  const pairs = placed(body)
  // Every row's card follows the line that starts with its own label.
  for (const label of ROW_LABELS) expect(pairs.some(([owner, before]) => owner === label && before.startsWith(label))).toBe(true)
  // The column cards follow the heading line.
  expect(pairs.filter(([owner]) => owner === 'Session' || owner.startsWith('System')).map(([, before]) => before.startsWith('Session'))).toEqual([true, true])
  const bare = settingsBody(ui, data({ schema: SCHEMA, values: {}, saved: undefined }), '', [], () => undefined)
  expect(all(bare, 'Box').filter(isCard).some(card => scope(card) === 'adyusuf-help-column-System')).toBe(false)
})

test('an Agents role card is its file description, right after the role line; no description, no card', () => {
  const agent = (role: string, description?: string) =>
    ({ role, defined: 'sonnet', runs_on: 'sonnet', active: true, in_mode: true, enabled: 'auto', model: 'default', description })
  const body = agentsBody(ui, data({ agents: [agent('qa', 'Reviews a change.'), agent('analyst'), agent('doc-writer', 'Writes docs.')] }), () => undefined)
  expect(placed(body)).toEqual([['[qa]', '[qa]opus[sonnet]haikufable'], ['[doc]', '[doc]opus[sonnet]haikufable']])
  expect(all(body, 'Box').filter(isCard).map(words)).toEqual(['Reviews a change.', 'Writes docs.'])
})

test('the Status labels and table headings have cards, each right after its own line', () => {
  const body = statusBody(ui, parseStatus(JSON.stringify({ now: 'gate', next: 'push', rows: [{ item: 'dev', state: 'ok', figure: '1', waiting: '-' }] })))
  const pairs = placed(body)
  expect(pairs.map(([owner]) => owner)).toEqual(['Now', 'Next', 'Item', 'State', 'Measured figure (signal)', 'Waiting on'])
  expect(pairs.slice(0, 2).map(([, before]) => before)).toEqual(['Nowgate', 'Nextpush'])
  expect(pairs.slice(2).every(([, before]) => before.startsWith('Item'))).toBe(true)
})
