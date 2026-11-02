import { expect, test } from 'claude-code/testing'

import { outsideRepository, paneFor, SECTIONS, settingsBody } from './boxes'

// Outside a git repository no code work happens, so the pane shows only Status and Settings, and Settings only Replies
// (user decision 01/11/2026; standards/13 §8a). A recording factory lets the tests read what would be drawn.
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
/** The label of every Settings line that is drawn (hidden hover cards left out). */
const labels = (body: unknown) => all(body, 'Text').filter(node => node.props.bold && node.props.color !== 'inverseText').map(words)

const enumSpec = (key: string, label: string, options: string[]) => ({ key, type: 'enum' as const, label, group: 'Session', options })
const data = {
  schema: [enumSpec('mode', 'Working mode', ['A', 'B']), enumSpec('reply.length', 'Reply length', ['short', 'normal', 'long']),
    { key: 'push.prod', type: 'bool' as const, label: 'Push prod', group: 'Push' }],
  values: { mode: 'B', 'reply.length': 'short', 'push.prod': true }, sources: {}, agents: [],
}

test('outside a repository only Status and Settings show, with no code work; inside one, or before the folder is read, all', () => {
  expect(paneFor({ stages: [], error: 'Not inside a git repository', outside: true })).toEqual({ sections: ['status', 'settings'], codeWork: false })
  expect(paneFor(null)).toEqual({ sections: [...SECTIONS], codeWork: true })
  expect(paneFor({ stages: [] })).toEqual({ sections: [...SECTIONS], codeWork: true })
  // A git failure that is not "outside" (dubious ownership, a moved main repository) hides nothing.
  expect(paneFor({ stages: [], error: 'git failed: fatal: detected dubious ownership' })).toEqual({ sections: [...SECTIONS], codeWork: true })
})

test('only the engine saying "no repository" (null) counts as outside; an unknown answer does not', () => {
  expect(outsideRepository(null)).toBe(true)
  expect(outsideRepository(undefined)).toBe(false)
  expect(outsideRepository({ root: '/r', remote: null, internal: false })).toBe(false)
})

test('with no code work, Settings shows only Replies and says why; with code work, every row as before', () => {
  const none = settingsBody(ui, data, '', [], () => undefined, undefined, false)
  expect(labels(none)).toEqual(['Replies'])
  expect(all(none, 'Text').find(node => node.props.dimColor)!.children).toEqual(['No repository here: only Replies shows. Change the rest with /adyusuf:config.'])
  const code = settingsBody(ui, data, '', [], () => undefined)
  expect(labels(code)).toEqual(['Mode', 'Replies', 'Push'])
  expect(all(code, 'Text').some(node => words(node).startsWith('No repository here'))).toBe(false)
})
