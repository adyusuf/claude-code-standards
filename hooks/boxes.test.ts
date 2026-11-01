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
// What a person reads on one line, in order: each Button and each Text outside one, an icon as ● ○ ☑ ☐.
function reads(node: unknown): string[] {
  if (typeof node !== 'object' || node === null) return typeof node === 'string' && node !== '' ? [node] : []
  const one = node as Node
  if (one.type === 'Button' || one.type === 'Text') return [words(one)]
  if (one.type === 'Svg') {
    const on = String(one.props.alt).endsWith(', chosen')
    return [String(one.props.source).includes('<circle') ? (on ? '●' : '○') : (on ? '☑' : '☐')]
  }
  return flat(one.children).flatMap(reads)
}
// The lines of a body: a row Box whose first child is the head column (a Box with a minWidth).
function rows(body: unknown): string[] {
  return all(body, 'Box')
    .filter(node => node.props.flexDirection === 'row' && (flat(node.children)[0] as Node | undefined)?.props?.minWidth !== undefined)
    .map(node => reads(node).join(' '))
}
const desktop = { ...ui, Svg: 'Svg' }

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
  expect([box, ...all(box, 'Box')].some(node => flat(node.children).includes('BODY'))).toBe(true)
})

test('a folded section keeps its header and its summary and hides the body', () => {
  const box = section(ui, 'agents', 'Agents', 'mode B', true, () => undefined, 'BODY') as Node
  expect(words(all(box, 'Button')[0])).toBe('▸ Agents  mode B')
  expect([box, ...all(box, 'Box')].some(node => flat(node.children).includes('BODY'))).toBe(false)
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
  expect(heads).toEqual(['Session settings', 'Mode', 'Model', 'Push', 'Claude settings', 'Mode', 'Model', 'Push'])
  expect(rows(body)).toEqual([
    'Mode A [B] C', 'Model opus [sonnet]', 'Push test [prod]',
    'Mode A B [C]', 'Model [opus] sonnet', 'Push test prod',
  ])
  expect(words(all(body, 'Text').find(node => node.props.color === '#E07B00'))).toBe('! a layer is unreadable')
})

test('Main model shows keep as opus, because Opus agents then run on the model their file defines', () => {
  const body = settingsBody(ui, data({ values: { mode: 'B', mode_model: 'sonnet' } }), '', [], () => undefined)
  expect(all(body, 'Button').map(words).slice(3, 5)).toEqual(['opus', '[sonnet]'])
  expect(all(body, 'Button').find(node => String(node.props.key) === 'session/mode_model=keep')).toBeDefined()
})

test('the Claude block is left out until the saved defaults are read', () => {
  const body = settingsBody(ui, data({ saved: undefined }), '', [], () => undefined)
  expect(all(body, 'Text').filter(node => node.props.bold).map(words)).toEqual(['Session settings', 'Mode', 'Model', 'Push'])
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
  expect(buttons.includes('[Future flag]')).toBe(true)
  expect(buttons.includes('x') && buttons.includes('[y]')).toBe(true)
  expect(all(body, 'Text').map(words).includes('Future kind')).toBe(true)
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
  expect(rows(body)).toEqual([
    '[analyst] [default] opus sonnet haiku fable',
    'qa',
    '[security (added)] [default] opus sonnet haiku fable',
  ])
  const models = all(body, 'Button').filter(node => String(node.props.key).includes('.model='))
  expect(models.map(node => node.props.key).filter(key => String(key).endsWith('=default'))).toEqual(['agents.analyst.model=default', 'agents.security.model=default'])
})

test('a pinned model is the only one lit; with default, the model it resolves to is lit too but not marked chosen', () => {
  const body = agentsBody(ui, data({ agents: [
    agent('qa', { active: true, in_mode: true, model: 'opus', runs_on: 'opus' }),
    agent('doc-writer', { active: true, in_mode: true, runs_on: 'haiku' }),
  ] }), () => undefined)
  expect(rows(body)).toEqual(['[qa] default [opus] sonnet haiku fable', '[doc] [default] opus sonnet haiku fable'])
  const lit = all(body, 'Button').filter(node => node.props.dimColor === false).map(node => String(node.props.key))
  expect(lit).toEqual(['on-qa', 'agents.qa.model=opus', 'on-doc-writer', 'agents.doc-writer.model=default', 'agents.doc-writer.model=haiku'])
})

test('the Agents box shows the short role names and keeps the role in the key it writes', () => {
  const roles = ['product-manager', 'test-writer', 'doc-writer', 'coverage-auditor', 'e2e-writer', 'analyst']
  const calls: string[][] = []
  const body = agentsBody(ui, data({ agents: roles.map(role => agent(role)) }), (key, value) => { calls.push([key, value]) })
  expect(rows(body)).toEqual(['product', 'tester', 'doc', 'coverage', 'e2e', 'analyst'])
  all(body, 'Button')[0].props.onPress()
  expect(calls).toEqual([['agents.product-manager.enabled', 'on']])
})

test('options line up: every head column of a block, and of the Agents box, is one width', () => {
  const widths = (body: unknown) => all(body, 'Box').filter(node => node.props.minWidth !== undefined).map(node => node.props.minWidth)
  const settings = widths(settingsBody(ui, data(), '', [], () => undefined))
  expect(new Set(settings).size).toBe(1)
  expect(settings[0]).toBe('Coverage'.length + 2)
  const agents = widths(agentsBody(ui, data(), () => undefined))
  expect(new Set(agents).size).toBe(1)
  expect(agents[0]).toBe('security (added)'.length + 3)
})

test('on a surface with Svg each option has a radio or checkbox icon and no brackets', () => {
  expect(rows(settingsBody(desktop, data({ saved: undefined }), '', [], () => undefined))).toEqual([
    'Mode ○ A ● B ○ C', 'Model ○ opus ● sonnet', 'Push ☐ test ☑ prod',
  ])
  const icons = all(settingsBody(desktop, data({ saved: undefined }), '', [], () => undefined), 'Svg')
  expect(icons.every(node => String(node.props.source).startsWith('<svg') && node.props.width === 16)).toBe(true)
  expect(rows(agentsBody(desktop, data(), () => undefined))[0]).toBe('☑ analyst ● default ○ opus ○ sonnet ○ haiku ○ fable')
})

test('a box body, a settings block and a promotion stage start one step in', () => {
  const box = section(ui, 'settings', 'Settings', '', false, () => undefined, 'BODY') as Node
  expect(all(box, 'Box').find(node => flat(node.children).includes('BODY'))!.props.marginLeft).toBe(2)
  const body = settingsBody(ui, data({ saved: undefined }), '', [], () => undefined)
  expect(all(body, 'Box').filter(node => node.props.marginLeft === 2).length).toBe(1)
  const promo = promotionBody(ui, { stages: [{ branch: 'dev', origin: 'aaa', unpushed: 0, waived: ['x'] }] })
  expect(words(all(promo, 'Box').find(node => node.props.marginLeft === 2))).toBe('waived x')
  expect(all(promo, 'Text').find(node => words(node) === 'waived x')!.props.color).toBe('#E07B00')
})

test('an agent of the mode that is switched off says so', () => {
  const body = agentsBody(ui, data({ values: { mode: 'B', mode_model: 'keep' }, agents: [agent('analyst', { in_mode: true })] }), () => undefined)
  expect(words(all(body, 'Button').find(node => String(node.props.key).startsWith('on-')))).toBe('analyst (off)')
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

test('"After pushing update:" is a checkbox line of test and prod, each ticked on its own', () => {
  const schema = [
    ...SCHEMA,
    { key: 'deploy_after_push.test', type: 'bool' as const, label: 'After pushing update, deploy to test', group: 'Deploy after push' },
    { key: 'deploy_after_push.prod', type: 'bool' as const, label: 'After pushing update, deploy to prod', group: 'Deploy after push' },
  ]
  const calls: string[][] = []
  const body = settingsBody(ui, data({ schema, values: { mode: 'B', mode_model: 'sonnet', 'deploy_after_push.test': true, 'deploy_after_push.prod': false } }), '', [], (key, value, scope) => { calls.push([key, value, String(scope)]) })
  const lines = rows(body)
  expect(lines).toContain('Deploy [test] prod')
  const buttons = all(body, 'Button').filter(node => String(node.props.key).includes('deploy_after_push.'))
  buttons.forEach(node => node.props.onPress())
  // Both blocks draw the two boxes (session first, then the saved defaults, where neither is ticked): each press
  // asks for the opposite of its own block's value.
  expect(calls).toEqual([
    ['deploy_after_push.test', 'no', 'session'], ['deploy_after_push.prod', 'yes', 'session'],
    ['deploy_after_push.test', 'yes', 'saved'], ['deploy_after_push.prod', 'yes', 'saved'],
  ])
})

test('labels are short with no trailing colon, and Runner shows cloud/local while pressing writes the stored value', () => {
  const schema = [
    ...SCHEMA,
    { key: 'ci.runner', type: 'enum' as const, label: 'CI runner', group: 'CI after push', options: ['hosted', 'self-hosted'] },
    { key: 'pod.connect', type: 'bool' as const, label: 'Connect to pod', group: 'Pod' },
    { key: 'write.unit_tests', type: 'bool' as const, label: 'Write unit tests', group: 'Write' },
    { key: 'write.e2e', type: 'bool' as const, label: 'Write e2e', group: 'Write' },
  ]
  const calls: string[][] = []
  const values = { mode: 'B', mode_model: 'sonnet', 'ci.runner': 'self-hosted', 'pod.connect': true, 'write.unit_tests': true, 'write.e2e': false }
  const body = settingsBody(ui, data({ schema, values, saved: undefined }), '', [], (key, value) => { calls.push([key, value]) })
  const lines = rows(body)
  expect(lines).toContain('Runner cloud [local]')
  expect(lines).toContain('Pod [connected]')
  expect(lines).toContain('Tests [unit] e2e')
  expect(lines.filter(text => text.split(' ')[0].endsWith(':'))).toEqual([])
  all(body, 'Button').find(node => node.props.key === 'session/ci.runner=hosted')!.props.onPress()
  expect(calls).toEqual([['ci.runner', 'hosted']])
})
