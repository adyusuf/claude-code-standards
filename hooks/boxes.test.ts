import { expect, test } from 'claude-code/testing'

import { agentsBody, agentsSummary, FOLDED_AT_START, promotionBody, promotionSummary, radio, SECTIONS, section, settingsBody, settingsSummary } from './boxes'

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
  const box = section(ui, 'agents', 'Agents', 'mode B: 2 of 14 active', true, () => undefined, 'BODY') as Node
  expect(words(all(box, 'Button')[0])).toBe('▸ Agents  mode B: 2 of 14 active')
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
  expect(settingsSummary(data({ sources: { mode: 'user' } }))).toBe('this session only')
  expect(agentsSummary(null)).toBe('')
  expect(agentsSummary(data())).toBe('mode B: 2 of 3 active')
  expect(agentsSummary(data({ values: { mode: 'A' } }))).toBe('mode A: no agents')
  expect(promotionSummary(null)).toBe('')
  expect(promotionSummary({ stages: [], error: 'Not inside a git repository' })).toBe('')
  expect(promotionSummary({ stages: [{ branch: 'dev', origin: 'aaa', unpushed: 0, waived: [] }, { branch: 'prod', origin: 'bbb', unpushed: 0, waived: [] }] })).toBe('dev aaa · prod bbb')
})

test('Settings waits, and says why when the script could not be read', () => {
  expect(words(settingsBody(ui, null, '', [], () => undefined))).toBe('Reading the configuration…')
  expect(words(settingsBody(ui, null, 'script missing', [], () => undefined))).toBe('script missing')
})

test('Settings groups the settings in schema order, leaves the agents out and marks where a value comes from', () => {
  const body = settingsBody(ui, data(), '', ['! a layer is unreadable'.slice(2)], () => undefined)
  const heads = all(body, 'Text').filter(node => node.props.bold).map(words)
  expect(heads).toEqual(['Session', 'Push'])
  const buttons = all(body, 'Button').map(words)
  expect(buttons).toEqual(['( ) A', '(•) B', '( ) C', '[x] Push prod', '[ ] Push test (session)'])
  expect(words(all(body, 'Text').find(node => words(node) === 'Working mode (user):'))).toBe('Working mode (user):')
  expect(words(all(body, 'Text').find(node => node.props.color === 'yellow'))).toBe('! a layer is unreadable')
})

test('a problem is shown in red above the groups', () => {
  const body = settingsBody(ui, data(), 'could not read', [], () => undefined)
  expect(words(all(body, 'Text').find(node => node.props.color === 'red'))).toBe('could not read')
})

test('pressing a yes/no setting asks for the opposite, and pressing a radio option asks for that option', () => {
  const calls: string[][] = []
  const body = settingsBody(ui, data(), '', [], (key, value) => { calls.push([key, value]) })
  const [, , modeC, prod, test_] = all(body, 'Button')
  prod.props.onPress()
  test_.props.onPress()
  modeC.props.onPress()
  expect(calls).toEqual([['push.prod', 'no'], ['push.test', 'yes'], ['mode', 'C']])
  expect(all(body, 'Select').length).toBe(0)
})

test('a radio list marks the chosen option, keys every option by setting and value, and can lay them in a row', () => {
  const opts = [{ value: 'a', label: 'one' }, { value: 'b', label: 'two' }]
  const column = radio(ui, 'k', 'Pick:', opts, 'b', () => undefined) as Node
  expect(all(column, 'Button').map(words)).toEqual(['( ) one', '(•) two'])
  expect(all(column, 'Button').map(node => node.props.key)).toEqual(['k=a', 'k=b'])
  expect(all(column, 'Box')[1].props.flexDirection).toBe('column')
  const row = radio(ui, 'k', 'Pick:', opts, 'zzz', () => undefined, true) as Node
  expect(all(row, 'Button').map(words)).toEqual(['( ) one', '( ) two'])
  expect(all(row, 'Box')[1].props.flexDirection).toBe('row')
  expect(all(row, 'Box')[1].props.flexWrap).toBe('wrap')
})

test('Agents waits until the configuration is read', () => {
  expect(words(agentsBody(ui, null, () => undefined))).toBe('Reading the configuration…')
})

test('Agents lists each role with its state, a model choice only for the active ones', () => {
  const body = agentsBody(ui, data(), () => undefined)
  const toggles = all(body, 'Button').filter(node => String(node.props.key).startsWith('on-'))
  expect(toggles.map(words)).toEqual(['[x] analyst', '[ ] qa', '[x] security (added)'])
  const models = all(body, 'Button').filter(node => String(node.props.key).includes('.model='))
  expect(models.map(node => node.props.key).filter(key => String(key).endsWith('=default'))).toEqual(['agents.analyst.model=default', 'agents.security.model=default'])
  expect(words(models[0])).toBe('(•) default (sonnet)')
  expect(words(all(body, 'Text')[0])).toBe('Opus agents run on sonnet unless one is set below')
})

test('an agent of the mode that is switched off says so, and keep means the defined model', () => {
  const body = agentsBody(ui, data({ values: { mode: 'B', mode_model: 'keep' }, agents: [agent('analyst', { in_mode: true })] }), () => undefined)
  expect(words(all(body, 'Button').find(node => String(node.props.key).startsWith('on-')))).toBe('[ ] analyst (off)')
  expect(words(all(body, 'Text')[0])).toBe('Opus agents run on their defined model unless one is set below')
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
