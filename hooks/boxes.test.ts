import { expect, test } from 'claude-code/testing'

import { agentsBody, agentsSummary, FOLDED_AT_START, promotionBody, promotionSummary, SECTIONS, section, settingsBody, settingsSummary } from './boxes'

// A recording factory: an element is { type, props, children }, so the tests read what the boxes would draw.
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

const SCHEMA = [
  { key: 'mode', type: 'enum' as const, label: 'Working mode', group: 'Session', options: ['A', 'B', 'C'] },
  { key: 'mode_model', type: 'enum' as const, label: 'Model that replaces Opus in the agents', group: 'Session', options: ['keep', 'sonnet'] },
  { key: 'push.prod', type: 'bool' as const, label: 'Push prod', group: 'Push' },
  { key: 'push.test', type: 'bool' as const, label: 'Push test', group: 'Push' },
  { key: 'agents.qa.enabled', type: 'enum' as const, label: 'qa: enabled', group: 'Agents', options: ['auto', 'on', 'off'] },
]
const agent = (role: string, extra: Record<string, unknown> = {}) => ({
  role, defined: 'sonnet', runs_on: 'sonnet', active: false, in_mode: false, enabled: 'auto', model: 'default', ...extra,
})
function data(over: Record<string, unknown> = {}) {
  return {
    schema: SCHEMA,
    values: { mode: 'B', mode_model: 'sonnet', 'push.prod': true, 'push.test': false },
    sources: { mode: 'user', 'push.prod': 'default', 'push.test': 'session' },
    saved: { values: { mode: 'C', mode_model: 'keep', 'push.prod': false, 'push.test': false }, sources: {} },
    agents: [agent('analyst', { active: true, in_mode: true }), agent('qa'), agent('security', { active: true })],
    ...over,
  }
}

test('the pane has three sections and starts with Agents and Promotion folded', () => {
  expect([...SECTIONS]).toEqual(['settings', 'agents', 'promotion'])
  expect(FOLDED_AT_START).toEqual({ agents: true, promotion: true })
})

test('an unfolded section shows its body under a header that names it and says what it holds', () => {
  const box = section(ui, 'settings', 'Settings', '2 changed', false, () => undefined, 'BODY') as Node
  expect(box.props.borderStyle).toBe('round')
  const header = all(box, 'Button')[0]
  expect(header.props.key).toBe('fold-settings')
  expect(words(header)).toBe('▾ Settings  2 changed')
  expect(flat(box.children).includes('BODY')).toBe(true)
})

test('a folded section keeps its header and its summary and hides the body', () => {
  const box = section(ui, 'agents', 'Agents', 'mode B', true, () => undefined, 'BODY') as Node
  expect(words(all(box, 'Button')[0])).toBe('▸ Agents  mode B')
  expect(flat(box.children).includes('BODY')).toBe(false)
})

test('a header without a summary draws no empty summary text, and pressing it folds or unfolds', () => {
  let pressed = 0
  const box = section(ui, 'promotion', 'Promotion', '', false, () => { pressed += 1 }, 'BODY') as Node
  expect(all(box, 'Text').length).toBe(1)
  all(box, 'Button')[0].props.onPress()
  expect(pressed).toBe(1)
})

test('the summaries say what a folded box holds', () => {
  expect(settingsSummary(null)).toBe('')
  expect(settingsSummary(data())).toBe('1 changed in this session')
  expect(settingsSummary(data({ sources: { mode: 'user' } }))).toBe('')
  expect(agentsSummary(null)).toBe('')
  expect(agentsSummary(data())).toBe('mode B')
  expect(agentsSummary(data({ values: { mode: 'A' } }))).toBe('mode A: no agents')
  expect(promotionSummary(null)).toBe('')
  expect(promotionSummary({ stages: [], error: 'Not inside a git repository' })).toBe('')
  expect(promotionSummary({ stages: [{ branch: 'dev', origin: 'aaa', unpushed: 0, waived: [] }, { branch: 'prod', origin: 'bbb', unpushed: 0, waived: [] }] })).toBe('dev aaa · prod bbb')
})

test('Settings waits, and says why when the script could not be read', () => {
  expect(words(settingsBody(ui, null, '', [], () => undefined))).toBe('Reading the configuration…')
  expect(words(settingsBody(ui, null, 'script missing', [], () => undefined))).toBe('script missing')
})

test('Settings draws the session block and the Claude block, one line per row, the second from the saved defaults', () => {
  const body = settingsBody(ui, data(), '', ['a layer is unreadable'], () => undefined)
  const heads = all(body, 'Text').filter(node => node.props.bold).map(words)
  expect(heads).toEqual(['Session settings', 'Claude settings'])
  const lines = all(body, 'Box').filter(node => node.props.flexDirection === 'row').map(node => flat(node.children).map(words).join(' '))
  expect(lines).toEqual([
    'Working mode ( )A (•)B ( )C', 'Main model (•)opus ( )sonnet', 'After merge push [ ]test [x]prod',
    'Working mode ( )A ( )B (•)C', 'Main model (•)opus ( )sonnet', 'After merge push [ ]test [ ]prod',
  ])
  expect(words(all(body, 'Text').find(node => node.props.color === 'yellow'))).toBe('! a layer is unreadable')
})

test('Main model shows keep as opus, because Opus agents then run on the model their file defines', () => {
  const body = settingsBody(ui, data({ values: { mode: 'B', mode_model: 'sonnet' } }), '', [], () => undefined)
  expect(all(body, 'Button').map(words).slice(3, 5)).toEqual(['( )opus', '(•)sonnet'])
  expect(all(body, 'Button').find(node => String(node.props.key) === 'session/mode_model=keep')).toBeDefined()
})

test('the Claude block is left out until the saved defaults are read', () => {
  const body = settingsBody(ui, data({ saved: undefined }), '', [], () => undefined)
  expect(all(body, 'Text').filter(node => node.props.bold).map(words)).toEqual(['Session settings'])
})

test('a problem is shown in red above the blocks', () => {
  const body = settingsBody(ui, data(), 'could not read', [], () => undefined)
  expect(words(all(body, 'Text').find(node => node.props.color === 'red'))).toBe('could not read')
})

test('a setting no row names is still drawn, so a newer plugin never hides one', () => {
  const schema = [...SCHEMA, { key: 'future.flag', type: 'bool' as const, label: 'Future flag', group: 'Later' },
    { key: 'future.kind', type: 'enum' as const, label: 'Future kind', group: 'Later', options: ['x', 'y'] }]
  const values = { mode: 'B', mode_model: 'sonnet', 'future.flag': true, 'future.kind': 'y' }
  const body = settingsBody(ui, data({ schema, values }), '', [], () => undefined)
  const buttons = all(body, 'Button').map(words)
  expect(buttons.includes('[x]Future flag')).toBe(true)
  expect(buttons.includes('( )x') && buttons.includes('(•)y')).toBe(true)
  expect(all(body, 'Text').map(words).includes('Future kind:')).toBe(true)
})

test('pressing a yes/no setting asks for the opposite and an option asks for that option, each on the block it was pressed in', () => {
  const calls: string[][] = []
  const body = settingsBody(ui, data(), '', [], (key, value, scope) => { calls.push([key, value, String(scope)]) })
  const press = (key: string) => all(body, 'Button').find(node => node.props.key === key)!.props.onPress()
  press('session/push.prod')
  press('session/push.test')
  press('session/mode=C')
  press('saved/push.prod')
  press('saved/mode=A')
  expect(calls).toEqual([
    ['push.prod', 'no', 'session'], ['push.test', 'yes', 'session'], ['mode', 'C', 'session'],
    ['push.prod', 'yes', 'saved'], ['mode', 'A', 'saved'],
  ])
  expect(all(body, 'Select').length).toBe(0)
})

test('every pressable part is keyed by block, setting and value, so the two blocks never collide', () => {
  const keys = all(settingsBody(ui, data(), '', [], () => undefined), 'Button').map(node => String(node.props.key))
  expect(new Set(keys).size).toBe(keys.length)
  expect(keys.filter(key => key.startsWith('session/')).length).toBe(keys.filter(key => key.startsWith('saved/')).length)
})

test('Agents waits until the configuration is read', () => {
  expect(words(agentsBody(ui, null, () => undefined))).toBe('Reading the configuration…')
})

test('Agents puts each role on one line with its state and, for the active ones, the model choice', () => {
  const body = agentsBody(ui, data(), () => undefined)
  const lines = all(body, 'Box').filter(node => node.props.flexDirection === 'row').map(node => flat(node.children).map(words).join(' '))
  expect(lines).toEqual([
    '[x]analyst (•)sonnet ( )opus ( )sonnet ( )haiku ( )fable',
    '[ ]qa',
    '[x]security (added) (•)sonnet ( )opus ( )sonnet ( )haiku ( )fable',
  ])
  const models = all(body, 'Button').filter(node => String(node.props.key).includes('.model='))
  expect(models.map(node => node.props.key).filter(key => String(key).endsWith('=default'))).toEqual(['agents.analyst.model=default', 'agents.security.model=default'])
})

test('an agent of the mode that is switched off says so', () => {
  const body = agentsBody(ui, data({ values: { mode: 'B', mode_model: 'keep' }, agents: [agent('analyst', { in_mode: true })] }), () => undefined)
  expect(words(all(body, 'Button').find(node => String(node.props.key).startsWith('on-')))).toBe('[ ]analyst (off)')
})

test('pressing an agent writes what makes it the other way round, and mode A ignores the press', () => {
  const calls: string[][] = []
  const body = agentsBody(ui, data(), (key, value) => { calls.push([key, value]) })
  const [analyst, qa, security] = all(body, 'Button').filter(node => String(node.props.key).startsWith('on-'))
  analyst.props.onPress()
  qa.props.onPress()
  security.props.onPress()
  all(body, 'Button').find(node => node.props.key === 'agents.analyst.model=opus')!.props.onPress()
  expect(calls).toEqual([
    ['agents.analyst.enabled', 'off'], ['agents.qa.enabled', 'on'], ['agents.security.enabled', 'auto'], ['agents.analyst.model', 'opus'],
  ])
  const quiet: string[][] = []
  const modeA = agentsBody(ui, data({ values: { mode: 'A', mode_model: 'sonnet' } }), (key, value) => { quiet.push([key, value]) })
  all(modeA, 'Button').filter(node => String(node.props.key).startsWith('on-'))[1].props.onPress()
  expect(quiet).toEqual([])
})

test('Promotion waits, shows an error, and lists each stage with its waived gates', () => {
  expect(words(promotionBody(ui, null))).toBe('Reading the branches…')
  expect(words(promotionBody(ui, { stages: [], error: 'Not inside a git repository' }))).toBe('Not inside a git repository')
  expect(words(promotionBody(ui, { stages: [] }))).toBe('No dev, test or prod branch here.')
  const body = promotionBody(ui, {
    stages: [
      { branch: 'dev', origin: 'aaa1111', unpushed: 0, waived: [] },
      { branch: 'test', origin: 'bbb2222', unpushed: 2, waived: ['abc1234 gates (neden: configuration)'] },
    ],
  })
  const lines = all(body, 'Text').map(words)
  expect(lines).toEqual([
    'dev   origin aaa1111  pushed', 'no waived gate on the way in',
    'test  origin bbb2222  2 not pushed', 'waived abc1234 gates (neden: configuration)',
  ])
})
