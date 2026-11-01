import { expect, test } from 'claude-code/testing'

import { agentsBody, FOLDED_AT_START, headWidth, isFolded, nextFold, promotionBody, SECTIONS, section, settingsBody } from './boxes'

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
  role, defined: 'sonnet', runs_on: 'sonnet', default_model: 'sonnet', active: false, in_mode: false, enabled: 'auto', model: 'default', ...extra,
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

test('the pane has four sections, Status first, and starts with Agents, Promotion and the System column folded', () => {
  expect([...SECTIONS]).toEqual(['status', 'settings', 'agents', 'promotion'])
  expect(FOLDED_AT_START).toEqual({ agents: true, promotion: true, claude: true })
})

test('a fold state saved before something could fold falls back to how it starts; a saved one wins', () => {
  expect(isFolded({ agents: false, promotion: true }, 'claude')).toBe(true)
  expect(isFolded({ agents: false, promotion: true }, 'status')).toBe(false)
  expect(isFolded({ claude: false }, 'claude')).toBe(false)
  expect(isFolded({ status: true }, 'status')).toBe(true)
  expect(isFolded({}, 'agents')).toBe(true)
})

test('a press turns over what the header reads as now, also for a state saved before the System column could fold', () => {
  const older = { agents: true, promotion: true }
  const once = nextFold(older, 'claude')
  expect(once).toEqual({ agents: true, promotion: true, claude: false })
  expect(nextFold(once, 'claude').claude).toBe(true)
  expect(nextFold(FOLDED_AT_START, 'status').status).toBe(true)
})

test('the System column folds by its arrow: folded, only the heading is left beside Session, and a press asks to unfold', () => {
  let pressed = 0
  const fold = (folded: boolean) => ({ folded, toggle: () => { pressed += 1 } })
  const shut = settingsBody(ui, data(), '', [], () => undefined, fold(true))
  expect(rows(shut)).toEqual(['Session System ▸', 'Mode A [B] C', 'Model* opus [sonnet]', 'Push test [prod]'])
  expect(all(shut, 'Button').some(node => String(node.props.key).startsWith('saved/'))).toBe(false)
  const heading = all(shut, 'Button').find(node => node.props.key === 'fold-claude')!
  heading.props.onPress()
  expect(pressed).toBe(1)
  // Only the arrow is a Button: the desktop drops bold inside one and pads it out of line with the column.
  expect(words(heading)).toBe('▸')
  expect(all(shut, 'Text').find(node => words(node) === 'System')!.props.bold).toBe(true)
  expect(all(shut, 'Button').some(node => words(node).includes('System'))).toBe(false)
  // The arrow sits close to the name: one cell in the terminal, none added on the desktop, whose button pads it already.
  const gap = (body: unknown) => all(body, 'Box').find(node => flat(node.children).some(child => words(child) === 'System'))!.props.columnGap
  expect([gap(shut), gap(settingsBody(desktop, data(), '', [], () => undefined, fold(true)))]).toEqual([1, 0])
  // Folded, the heading follows Session at once; open, it sits over its own column.
  const head = (body: unknown) => all(body, 'Box').find(node => node.props.flexDirection === 'row')!
  const widths = (body: unknown) => flat(head(body).children).map(child => (child as Node).props.minWidth)
  expect(widths(shut)).toEqual(['security'.length + 3, 0, undefined])
  const open = settingsBody(ui, data(), '', [], () => undefined, fold(false))
  expect(rows(open)).toEqual(['Session System ◂', 'Mode A [B] C A B [C]', 'Model* opus [sonnet] [opus] sonnet', 'Push test [prod] test prod'])
  expect(widths(open)).toEqual(['security'.length + 3, 'opus'.length + 'sonnet'.length + 4 + 1 + 2, undefined])
  // Without saved defaults there is no System heading to fold.
  expect(all(settingsBody(ui, data({ saved: undefined }), '', [], () => undefined, fold(true)), 'Button').some(node => node.props.key === 'fold-claude')).toBe(false)
})

test('an unfolded section shows its body under a header that is the arrow and the title alone', () => {
  const box = section(ui, 'settings', 'Settings', false, () => undefined, 'BODY') as Node
  expect(box.props.borderStyle).toBe('round')
  const header = all(box, 'Button')[0]
  expect(header.props.key).toBe('fold-settings')
  // The title is a bold Text beside the arrow, not inside the Button, where the desktop would drop the bold.
  expect(words(header)).toBe('▾')
  expect(reads(all(box, 'Box').find(node => node.props.flexDirection === 'row'))).toEqual(['▾', 'Settings'])
  expect(all(box, 'Text').find(node => words(node) === 'Settings')!.props.bold).toBe(true)
  expect([box, ...all(box, 'Box')].some(node => flat(node.children).includes('BODY'))).toBe(true)
})

test('a folded section keeps only its header: nothing beside the title, no body', () => {
  const box = section(ui, 'agents', 'Agents', true, () => undefined, 'BODY') as Node
  // What is drawn: the arrow and the title; the only other Text is the hidden hover card's.
  const shown = (node: Node): boolean => node.props.display !== 'none' && flat(node.children).every(child => typeof child !== 'object' || child === null || shown(child as Node))
  expect(all(box, 'Text').filter(node => node.props.color !== 'inverseText').map(words)).toEqual(['Agents'])
  expect(all(box, 'Box').filter(node => node.props.display === 'none').length).toBe(1)
  expect(shown(box)).toBe(false)
  expect([box, ...all(box, 'Box')].some(node => flat(node.children).includes('BODY'))).toBe(false)
})

test('pressing the arrow folds or unfolds', () => {
  let pressed = 0
  const box = section(ui, 'promotion', 'Promotion', false, () => { pressed += 1 }, 'BODY') as Node
  all(box, 'Button')[0].props.onPress()
  expect(pressed).toBe(1)
})

test('Settings waits, and says why when the script could not be read', () => {
  expect(words(settingsBody(ui, null, '', [], () => undefined))).toBe('Reading the configuration…')
  expect(words(settingsBody(ui, null, 'script missing', [], () => undefined))).toBe('script missing')
})

test('Settings is one table: a label, the options of this session, then those of the saved defaults, under a Session/System head', () => {
  const body = settingsBody(ui, data(), '', ['a layer is unreadable'], () => undefined)
  const heads = all(body, 'Text').filter(node => node.props.bold).map(words)
  expect(heads).toEqual(['Session', 'System', 'Mode', 'Model*', 'Push'])
  expect(rows(body)).toEqual([
    'Session System ◂', 'Mode A [B] C A B [C]', 'Model* opus [sonnet] [opus] sonnet', 'Push test [prod] test prod',
  ])
  expect(words(all(body, 'Text').find(node => node.props.color === '#E07B00'))).toBe('! a layer is unreadable')
})

test('Main model shows keep as opus, because Opus agents then run on the model their file defines', () => {
  const body = settingsBody(ui, data({ values: { mode: 'B', mode_model: 'sonnet' } }), '', [], () => undefined)
  expect(all(body, 'Button').filter(node => String(node.props.key).startsWith('session/mode_model=')).map(words)).toEqual(['opus', '[sonnet]'])
  expect(all(body, 'Button').find(node => String(node.props.key) === 'session/mode_model=keep')).toBeDefined()
})

test('the System column is left out until the saved defaults are read', () => {
  const body = settingsBody(ui, data({ saved: undefined }), '', [], () => undefined)
  expect(all(body, 'Text').filter(node => node.props.bold).map(words)).toEqual(['Session', 'Mode', 'Model*', 'Push'])
  expect(rows(body)).toEqual(['Session', 'Mode A [B] C', 'Model* opus [sonnet]', 'Push test [prod]'])
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

test('Agents puts each role on one line: its checkbox and name, then the model radios; there is no default checkbox', () => {
  const body = agentsBody(ui, data(), () => undefined)
  expect(rows(body)).toEqual([
    '☑ analyst opus [sonnet] haiku fable',
    '☐ qa',
    '☑ security opus [sonnet] haiku fable (added)',
  ])
  expect(all(body, 'Button').some(node => String(node.props.key).endsWith('=default'))).toBe(false)
})

test('a role whose file says opus carries a star, the same as Model*, which replaces exactly those roles', () => {
  const body = agentsBody(ui, data({ agents: [
    agent('qa', { active: true, in_mode: true, defined: 'opus' }),
    agent('architect', { in_mode: true, defined: 'opus' }),
    // A full model id is not replaced by Model* (effective_model), so it carries no star.
    agent('developer', { active: true, in_mode: true, defined: 'claude-opus-5-5', runs_on: 'claude-opus-5-5' }),
    agent('doc-writer', { active: true, in_mode: true, defined: 'haiku', runs_on: 'haiku', default_model: 'haiku' }),
  ] }), () => undefined)
  expect(rows(body)).toEqual(['☑ qa* opus [sonnet] haiku fable', '☐ architect* (off)', '☑ developer opus sonnet haiku fable', '☑ doc opus sonnet [haiku] fable'])
  // The star counts in the role column's width, so the radios of a starred longest name line up with the rest.
  const widths = (one: unknown) => all(one, 'Box').filter(node => node.props.minWidth !== undefined).map(node => node.props.minWidth)
  const longest = agentsBody(ui, data({ agents: [agent('security', { active: true, defined: 'opus' }), agent('qa', { active: true, in_mode: true })] }), () => undefined)
  expect(rows(longest)[0]).toBe('☑ security* opus [sonnet] haiku fable (added)')
  // The (added) mark sits after the radios, so it does not widen the column.
  expect(widths(longest)).toEqual(['security*'.length + 3, 'security*'.length + 3])
})

test('the radio of the model the role runs on is chosen, pinned or not', () => {
  const body = agentsBody(ui, data({ agents: [
    agent('qa', { active: true, in_mode: true, model: 'opus', runs_on: 'opus' }),
    agent('doc-writer', { active: true, in_mode: true, runs_on: 'haiku', default_model: 'haiku' }),
  ] }), () => undefined)
  expect(rows(body)).toEqual(['☑ qa [opus] sonnet haiku fable', '☑ doc opus sonnet [haiku] fable'])
  const lit = all(body, 'Button').filter(node => node.props.dimColor === false).map(node => String(node.props.key))
  expect(lit).toEqual(['on-qa', 'agents.qa.model=opus', 'on-doc-writer', 'agents.doc-writer.model=haiku'])
})

test('the radio of the model default gives writes default, any other pins it', () => {
  const calls: string[][] = []
  const body = agentsBody(ui, data({ agents: [
    agent('qa', { active: true, in_mode: true, model: 'opus', runs_on: 'opus', default_model: 'sonnet' }),
  ] }), (key, value) => { calls.push([key, value]) })
  const press = (key: string) => all(body, 'Button').find(node => node.props.key === key)!.props.onPress()
  press('agents.qa.model=sonnet')            // the model default gives -> default
  press('agents.qa.model=haiku')             // another model -> pinned
  expect(calls).toEqual([['agents.qa.model', 'default'], ['agents.qa.model', 'haiku']])
})

test('the radio that writes default is the model default gives, not the model the role file defines', () => {
  const calls: string[][] = []
  // Defined opus, moved to sonnet by the mode's override (Model = sonnet), pinned to haiku for now.
  const body = agentsBody(ui, data({ agents: [agent('developer', { active: true, in_mode: true, defined: 'opus', default_model: 'sonnet', model: 'haiku', runs_on: 'haiku' })] }),
    (key, value) => { calls.push([key, value]) })
  const press = (key: string) => all(body, 'Button').find(node => node.props.key === key)!.props.onPress()
  press('agents.developer.model=sonnet')
  press('agents.developer.model=opus')
  expect(calls).toEqual([['agents.developer.model', 'default'], ['agents.developer.model', 'opus']])
})

test('from an older script without default_model, the radio of the running model keeps default while the role is on it', () => {
  const calls: string[][] = []
  const old = { active: true, in_mode: true, default_model: undefined }
  const body = agentsBody(ui, data({ agents: [agent('analyst', { ...old, runs_on: 'sonnet' }), agent('qa', { ...old, model: 'opus', runs_on: 'opus' })] }),
    (key, value) => { calls.push([key, value]) })
  const press = (key: string) => all(body, 'Button').find(node => node.props.key === key)!.props.onPress()
  press('agents.analyst.model=sonnet')   // on default: sonnet is what default gives, so default stays
  press('agents.qa.model=sonnet')        // pinned and unknown default: a plain pin
  expect(calls).toEqual([['agents.analyst.model', 'default'], ['agents.qa.model', 'sonnet']])
})

test('the role checkbox is a glyph button left of the name; a role that runs is named in bold', () => {
  const body = agentsBody(ui, data(), () => undefined)
  // Bold cannot sit inside a Button on the desktop, so the name is a Text beside it.
  expect(all(body, 'Text').filter(node => node.props.bold).map(words)).toEqual(['analyst', 'security'])
  expect(all(body, 'Text').find(node => words(node) === 'qa')!.props.dimColor).toBe(true)
  const toggles = all(body, 'Button').filter(node => String(node.props.key).startsWith('on-'))
  expect(toggles.map(node => [words(node), node.props.dimColor])).toEqual([['☑', false], ['☐', true], ['☑', false]])
  // One cell between the checkbox and the name.
  expect(all(body, 'Box').filter(node => flat(node.children).some(child => toggles.includes(child as Node))).map(node => node.props.columnGap)).toEqual([1, 1, 1])
  // The same on the desktop: no Svg icon for a role, only for the model radios.
  expect(all(agentsBody(desktop, data(), () => undefined), 'Svg').every(node => String(node.props.source).includes('<circle'))).toBe(true)
})

test('the Agents box shows the short role names and keeps the role in the key it writes', () => {
  const roles = ['product-manager', 'test-writer', 'doc-writer', 'coverage-auditor', 'e2e-writer', 'analyst']
  const calls: string[][] = []
  const body = agentsBody(ui, data({ agents: roles.map(role => agent(role)) }), (key, value) => { calls.push([key, value]) })
  expect(rows(body)).toEqual(['☐ product', '☐ tester', '☐ doc', '☐ coverage', '☐ e2e', '☐ analyst'])
  all(body, 'Button')[0].props.onPress()
  expect(calls).toEqual([['agents.product-manager.enabled', 'on']])
})

test('options line up: Settings and Agents share one head column, so their options start at the same place', () => {
  const widths = (body: unknown) => all(body, 'Box').filter(node => node.props.minWidth !== undefined).map(node => node.props.minWidth)
  const body = settingsBody(ui, data(), '', [], () => undefined)
  const lines = all(body, 'Box').filter(node => node.props.flexDirection === 'row' && (flat(node.children)[0] as Node).props?.minWidth !== undefined)
  // Each line: the head column (shared with Agents), then the Session column (sized to the widest row's options), then System.
  expect(lines.map(node => flat(node.children).map(child => (child as Node).props.minWidth))).toEqual(
    lines.map(() => [headWidth(data()), 'opus'.length + 'sonnet'.length + 4 + 1 + 2, undefined]))
  expect(widths(body).length).toBe(lines.length * 2)
  // Agents: the same head column on every row; the model radios follow it.
  const agents = widths(agentsBody(ui, data(), () => undefined))
  expect(agents).toEqual([headWidth(data()), headWidth(data()), headWidth(data())])
  expect(headWidth(data())).toBe('security'.length + 3)
})

test('the shared head column is the longest label, or the longest name of a role that is on; an off role does not widen it', () => {
  const on = (role: string, extra: Record<string, unknown> = {}) => agent(role, { active: true, in_mode: true, ...extra })
  // Short names that are on: the Settings labels decide ("Coverage" and a gap).
  expect(headWidth(data({ agents: [on('qa'), on('analyst')] }))).toBe('Coverage'.length + 2)
  // A longer name that is on, star counted: it decides, for Settings too.
  expect(headWidth(data({ agents: [on('architect', { defined: 'opus' }), on('qa')] }))).toBe('architect*'.length + 3)
  // A long name that is off has no radios after it, so it does not count.
  expect(headWidth(data({ agents: [on('qa'), agent('observability', { in_mode: true })] }))).toBe('Coverage'.length + 2)
  // An added role: its (added) mark is drawn after the radios and does not count.
  expect(headWidth(data({ agents: [on('qa'), agent('observability', { active: true })] }))).toBe('observability'.length + 3)
  // Mode A runs no role: the labels decide.
  expect(headWidth(data({ values: { mode: 'A', mode_model: 'keep' }, agents: [agent('observability')] }))).toBe('Coverage'.length + 2)
  // Settings uses it: its label column moves with the Agents column.
  const wide = data({ agents: [on('architect', { defined: 'opus' })] })
  const first = all(settingsBody(ui, wide, '', [], () => undefined), 'Box').find(node => node.props.minWidth !== undefined)!
  expect(first.props.minWidth).toBe('architect*'.length + 3)
})

test('on a surface with Svg each option has a radio or checkbox icon and no brackets', () => {
  expect(rows(settingsBody(desktop, data({ saved: undefined }), '', [], () => undefined))).toEqual([
    'Session', 'Mode ○ A ● B ○ C', 'Model* ○ opus ● sonnet', 'Push ☐ test ☑ prod',
  ])
  const icons = all(settingsBody(desktop, data({ saved: undefined }), '', [], () => undefined), 'Svg')
  expect(icons.every(node => String(node.props.source).startsWith('<svg') && node.props.width === 12 && node.props.height === 12)).toBe(true)
  expect(icons.every(node => String(node.props.source).includes('width="12" height="12" viewBox="0 0 12 12"'))).toBe(true)
  expect(rows(agentsBody(desktop, data(), () => undefined))[0]).toBe('☑ analyst ○ opus ● sonnet ○ haiku ○ fable')
  expect(all(agentsBody(desktop, data(), () => undefined), 'Svg').length).toBe(8)
})

test('a box body and the lines of a promotion stage start one step in', () => {
  const box = section(ui, 'settings', 'Settings', false, () => undefined, 'BODY') as Node
  expect(all(box, 'Box').find(node => flat(node.children).includes('BODY'))!.props.marginLeft).toBe(2)
  const promo = promotionBody(ui, { stages: [{ branch: 'dev', origin: 'aaa', unpushed: 0, waived: ['x'] }] })
  expect(words(all(promo, 'Box').find(node => node.props.marginLeft === 2))).toBe('waived x')
  expect(all(promo, 'Text').find(node => words(node) === 'waived x')!.props.color).toBe('#E07B00')
})

test('an agent of the mode that is switched off says so', () => {
  const body = agentsBody(ui, data({ values: { mode: 'B', mode_model: 'keep' }, agents: [agent('analyst', { in_mode: true })] }), () => undefined)
  expect(words(all(body, 'Button').find(node => String(node.props.key).startsWith('on-')))).toBe('☐')
  expect(rows(body)).toEqual(['☐ analyst (off)'])
  expect(all(body, 'Text').find(node => words(node) === '(off)')!.props.dimColor).toBe(true)
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
  expect(words(all(modeA, 'Text').find(node => node.props.dimColor)!)).toBe('mode A runs no agents')
  expect(all(agentsBody(ui, data(), () => undefined), 'Text').some(node => words(node) === 'mode A runs no agents')).toBe(false)
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
  expect(lines).toContain('Deploy [test] prod test prod')
  const buttons = all(body, 'Button').filter(node => String(node.props.key).includes('deploy_after_push.'))
  buttons.forEach(node => node.props.onPress())
  // Both blocks draw the two boxes (session first, then the saved defaults, where neither is ticked): each press
  // asks for the opposite of its own block's value.
  expect(calls).toEqual([
    ['deploy_after_push.test', 'no', 'session'], ['deploy_after_push.prod', 'yes', 'session'],
    ['deploy_after_push.test', 'yes', 'saved'], ['deploy_after_push.prod', 'yes', 'saved'],
  ])
})

test('Replies sits under Model* and offers short, normal and long; a press writes the level', () => {
  const schema = [...SCHEMA, { key: 'pod.message_format', type: 'enum' as const, label: 'Message format', group: 'Pod', options: ['short', 'full'] },
    { key: 'reply.length', type: 'enum' as const, label: 'Reply length', group: 'Session', options: ['short', 'normal', 'long'] }]
  const calls: string[][] = []
  const body = settingsBody(ui, data({ schema, values: { mode: 'B', mode_model: 'sonnet', 'reply.length': 'short', 'pod.message_format': 'short' }, saved: undefined }), '', [],
    (key, value) => { calls.push([key, value]) })
  expect(rows(body).slice(0, 5)).toEqual(['Session', 'Mode A [B] C', 'Model* opus [sonnet]', 'Replies [short] normal long', 'Format [short] full'])
  all(body, 'Button').find(node => node.props.key === 'session/reply.length=long')!.props.onPress()
  expect(calls).toEqual([['reply.length', 'long']])
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
  expect(lines).toContain('Pod [on]')
  expect(lines).toContain('Tests [unit] e2e')
  expect(lines.filter(text => text.split(' ')[0].endsWith(':'))).toEqual([])
  all(body, 'Button').find(node => node.props.key === 'session/ci.runner=hosted')!.props.onPress()
  expect(calls).toEqual([['ci.runner', 'hosted']])
})
