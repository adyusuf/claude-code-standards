// What the boxes of the adyusuf pane show, kept apart from the engine so it can be tested without one: no import from
// 'claude-code', no JSX. The element factory `h` and the elements themselves (Box, Text, Button) are handed in as
// `ui`: each surface has its own elements, and a test hands in a recording factory instead of the engine's. A choice among
// several values is a row of options, not a dropdown (user decision 24/10/2026); every setting sits on one line, the label
// first and its pressable parts after it (user decision 28/10/2026). User decisions of 01/11/2026: the labels are short and
// bold, with no trailing colon, in a column of one width so every row's options start at the same place; what is chosen or on
// is at full strength and the rest dimmed; where the surface draws `Svg` (desktop) each option has a radio or checkbox icon,
// where it does not (terminal) the chosen one is drawn `[in brackets]` (underline was tried first: the desktop draws a Button
// as a native button and drops a Text's underline inside it); a box's body and a block's lines start one step in.
import { enabledFor, settingGroups } from './choose'

export type Factory = (type: unknown, props: Record<string, unknown> | null, ...children: unknown[]) => unknown
/** `Svg` is in the element table only where the surface draws it (desktop, not the terminal). */
export type Ui = { h: Factory; Box: unknown; Text: unknown; Button: unknown; Svg?: unknown }
/** `session`: this session only; `saved`: the saved defaults every new session starts from (the user's file). */
export type Scope = 'session' | 'saved'
export type Press = (key: string, value: string, scope?: Scope) => void

type Spec = { key: string; type: 'bool' | 'enum'; label: string; group: string; options?: string[] }
type AgentRow = {
  role: string; defined: string; runs_on: string; default_model?: string; active: boolean; in_mode: boolean; enabled: string; model: string
}
type Layer = { values: Record<string, boolean | string>; sources: Record<string, string> }
type SettingsData = Layer & { schema: Spec[]; saved?: Layer; agents: AgentRow[] }
type Stage = { branch: string; origin: string; unpushed: number; waived: string[] }
type PromotionData = { stages: Stage[]; error?: string }

export const SECTIONS = ['status', 'settings', 'agents', 'promotion'] as const
export type SectionId = (typeof SECTIONS)[number]

/** Sections that start folded, so the pane opens as a short card and not as one long list. */
export const FOLDED_AT_START: Record<string, boolean> = { agents: true, promotion: true }

/** The radio group of an agent's model; `default` is a checkbox beside it, not one of the radios. */
const AGENT_MODELS = ['opus', 'sonnet', 'haiku', 'fable']
const TARGETS = ['dev', 'test', 'prod']
/** One indentation step, in cells: the width of a box header's `▾ `. */
const INDENT = 2
/** A warning (a waived gate, an unreadable settings file): orange as hex, which the terminal and the desktop both draw. */
const WARN = '#E07B00'
/** The names the Agents box shows; the role (agent file, settings key) keeps its own name. */
const ROLE_NAMES: Record<string, string> = {
  'product-manager': 'product', 'test-writer': 'tester', 'doc-writer': 'doc', 'coverage-auditor': 'coverage', 'e2e-writer': 'e2e',
}
const ICON_ON = '#378ADD'
const ICON_OFF = '#888780'
// Exactly the shape's size: an empty margin inside the image read as a space after the icon (user decision 01/11/2026).
const svg = (body: string) => `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">${body}</svg>`
const ICONS = {
  radio: {
    on: svg(`<circle cx="6" cy="6" r="5" fill="none" stroke="${ICON_ON}" stroke-width="1.2"/><circle cx="6" cy="6" r="2.5" fill="${ICON_ON}"/>`),
    off: svg(`<circle cx="6" cy="6" r="5" fill="none" stroke="${ICON_OFF}" stroke-width="1.2"/>`),
  },
  check: {
    on: svg(`<rect x="1" y="1" width="10" height="10" rx="2" fill="none" stroke="${ICON_ON}" stroke-width="1.2"/><path d="M3.5 6.2l2 2 3.8-4.2" fill="none" stroke="${ICON_ON}" stroke-width="1.5"/>`),
    off: svg(`<rect x="1" y="1" width="10" height="10" rx="2" fill="none" stroke="${ICON_OFF}" stroke-width="1.2"/>`),
  },
}
type Kind = keyof typeof ICONS

type Item = { key: string; name: string }
type Row = { label: string; items: Item[] } | { label: string; key: string; names?: Record<string, string> }
const targets = (prefix: string, names = TARGETS): Item[] => names.map(name => ({ key: `${prefix}.${name}`, name }))

/** The lines of a settings block, in order. A setting the schema has and no row names is still drawn (see `block`). */
const ROWS: Row[] = [
  { label: 'Mode', key: 'mode' },
  { label: 'Model', key: 'mode_model', names: { keep: 'opus' } },
  { label: 'Pod', items: [{ key: 'pod.connect', name: 'on' }] },
  { label: 'Format', key: 'pod.message_format' },
  { label: 'Tests', items: [{ key: 'write.unit_tests', name: 'unit' }, { key: 'write.e2e', name: 'e2e' }] },
  { label: 'Merge', items: targets('merge') },
  { label: 'Push', items: targets('push') },
  { label: 'Gates', items: targets('gates_before_push') },
  { label: 'Coverage', items: targets('coverage_before_push') },
  { label: 'CI', items: targets('ci_after_push') },
  // Display names only: the stored values stay `hosted` / `self-hosted`, which CI and sdlc_settings.py read.
  { label: 'Runner', key: 'ci.runner', names: { hosted: 'cloud', 'self-hosted': 'local' } },
  { label: 'Deploy', items: targets('deploy_after_push', ['test', 'prod']) },
  { label: 'E2E', items: targets('e2e_before_deploy', ['test', 'prod']) },
]

/** The width of the label column of a settings block, in cells: the longest label and a gap. */
const LABEL_WIDTH = Math.max(...ROWS.map(row => row.label.length)) + 2

/**
 * One line: its head (a label, a role) in a column of `width` cells, then one column of parts per layer, side by side.
 * Every column but the last is `columnWidth` cells at least, so the next one starts at the same place on every line.
 */
function line(ui: Ui, head: unknown, columns: unknown[], width = LABEL_WIDTH, columnWidth = 0) {
  const { h } = ui
  return h(ui.Box, { flexDirection: 'row', columnGap: 1 },
    h(ui.Box, { minWidth: width, flexShrink: 0 }, head),
    columns.map((parts, at) => h(ui.Box, {
      flexDirection: 'row', flexWrap: 'wrap', columnGap: 1, ...(at < columns.length - 1 ? { minWidth: columnWidth, flexShrink: 0 } : {}),
    }, parts)))
}

const label = (ui: Ui, text: string) => (text === '' ? null : ui.h(ui.Text, { bold: true }, text))

/**
 * One pressable part. `chosen` fills its icon (desktop) or puts it in brackets (terminal) and draws it at full strength,
 * the rest dimmed. The icon sits beside the Button: a Button holds text only.
 */
function option(ui: Ui, key: string, text: string, kind: Kind, chosen: boolean, onPress: () => void) {
  const { h } = ui
  const button = h(ui.Button, { key, plain: true, dimColor: !chosen, onPress }, ui.Svg || !chosen ? text : `[${text}]`)
  if (!ui.Svg) return button
  return h(ui.Box, { flexDirection: 'row', alignItems: 'center' },
    h(ui.Svg, { source: ICONS[kind][chosen ? 'on' : 'off'], alt: chosen ? `${text}, chosen` : text, width: 12, height: 12 }), button)
}

/** The options of one setting, the chosen one marked. */
function choices(ui: Ui, scope: Scope, key: string, options: Item[], value: string, press: Press) {
  return options.map(one =>
    option(ui, `${scope}/${key}=${one.key}`, one.name, 'radio', one.key === value, () => press(key, one.key, scope)))
}

/** The yes/no settings of one line, each marked while it is on; pressing asks for the opposite. */
function checks(ui: Ui, scope: Scope, items: Item[], values: Layer['values'], press: Press) {
  return items.map(item => {
    const on = values[item.key] === true
    return option(ui, `${scope}/${item.key}`, item.name, 'check', on, () => press(item.key, on ? 'no' : 'yes', scope))
  })
}

/** One settings row: its label, the names it draws (to size the column) and how it draws its options for one layer. */
type SettingLine = { label: string; names: string[]; draw: (scope: Scope, layer: Layer) => unknown[] }

/** The rows of the settings table, in order. */
function settingLines(ui: Ui, schema: Spec[], press: Press): SettingLine[] {
  const { shown } = settingGroups(schema)
  const has = new Set(shown.map(spec => spec.key))
  const covered = new Set<string>()
  const lines: SettingLine[] = []
  const radios = (text: string, key: string, options: Item[]): SettingLine => ({
    label: text, names: options.map(one => one.name),
    draw: (scope, layer) => choices(ui, scope, key, options, String(layer.values[key]), press),
  })
  for (const row of ROWS) {
    if ('items' in row) {
      const items = row.items.filter(item => has.has(item.key))
      items.forEach(item => covered.add(item.key))
      if (items.length > 0) {
        lines.push({ label: row.label, names: items.map(item => item.name), draw: (scope, layer) => checks(ui, scope, items, layer.values, press) })
      }
      continue
    }
    const spec = shown.find(one => one.key === row.key)
    if (!spec) continue
    covered.add(row.key)
    lines.push(radios(row.label, row.key, (spec.options ?? []).map(option => ({ key: option, name: row.names?.[option] ?? option }))))
  }
  // A setting no row names (a newer plugin than this pane) must not vanish from view.
  for (const spec of shown.filter(one => !covered.has(one.key))) {
    const items = [{ key: spec.key, name: spec.label }]
    lines.push(spec.type === 'bool'
      ? { label: '', names: [spec.label], draw: (scope, layer) => checks(ui, scope, items, layer.values, press) }
      : radios(spec.label, spec.key, (spec.options ?? []).map(option => ({ key: option, name: option }))))
  }
  return lines
}

/** The cells one row's options take: each name with its brackets or icon, a gap between them. */
const cells = (names: string[]) => names.reduce((sum, name) => sum + name.length + 2, 0) + Math.max(0, names.length - 1)

/** One bordered box with a header that folds it; the summary stays visible while it is folded. */
export function section(ui: Ui, id: SectionId, title: string, summary: string, folded: boolean, toggle: () => void, body: unknown) {
  const { h } = ui
  return h(
    ui.Box,
    { flexDirection: 'column', borderStyle: 'round', paddingX: 1, marginBottom: 1 },
    h(ui.Button, { key: `fold-${id}`, plain: true, onPress: toggle },
      folded ? '▸ ' : '▾ ',
      h(ui.Text, { bold: true }, title),
      summary ? h(ui.Text, { dimColor: true }, `  ${summary}`) : ''),
    folded ? null : h(ui.Box, { flexDirection: 'column', marginLeft: INDENT }, body),
  )
}

export function settingsSummary(data: SettingsData | null): string {
  if (!data) return ''
  const changed = Object.values(data.sources).filter(source => source === 'session').length
  return changed > 0 ? `${changed} changed in this session` : ''
}

export function agentsSummary(data: SettingsData | null): string {
  if (!data) return ''
  const mode = String(data.values.mode)
  return mode === 'A' ? 'mode A: no agents' : `mode ${mode}`
}

export function promotionSummary(data: PromotionData | null): string {
  if (!data || data.error) return ''
  return data.stages.map(stage => `${stage.branch} ${stage.origin}`).join(' · ')
}

/**
 * The settings as one table (user decision 01/11/2026): a label, this session's options (a press changes this session
 * only), then the saved defaults' options (a press changes `~/.claude/adyusuf.json`, which new sessions start from).
 */
function table(ui: Ui, data: SettingsData, press: Press) {
  const { h } = ui
  const lines = settingLines(ui, data.schema, press)
  const width = Math.max(0, ...lines.map(one => cells(one.names))) + 2
  const layers: [Scope, Layer][] = [['session', data], ...(data.saved ? [['saved', data.saved] as [Scope, Layer]] : [])]
  const heads = layers.map(([scope]) => h(ui.Text, { bold: true }, scope === 'session' ? 'Session' : 'Claude'))
  return h(ui.Box, { flexDirection: 'column' },
    line(ui, null, heads, LABEL_WIDTH, width),
    lines.map(one => line(ui, label(ui, one.label), layers.map(([scope, layer]) => one.draw(scope, layer)), LABEL_WIDTH, width)))
}

export function settingsBody(ui: Ui, data: SettingsData | null, problem: string, problems: string[], press: Press) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, problem || 'Reading the configuration…')
  return h(
    ui.Box,
    { flexDirection: 'column' },
    problem !== '' ? h(ui.Text, { color: 'red' }, problem) : null,
    problems.map(line => h(ui.Text, { color: WARN }, `! ${line}`)),
    table(ui, data, press),
  )
}

export function agentsBody(ui: Ui, data: SettingsData | null, press: Press) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, 'Reading the configuration…')
  const mode = String(data.values.mode)
  const name = (agent: AgentRow) => `${ROLE_NAMES[agent.role] ?? agent.role}${!agent.in_mode && agent.active ? ' (added)' : ''}${agent.in_mode && !agent.active && mode !== 'A' ? ' (off)' : ''}`
  // The role column is as wide as the longest name with its checkbox (icon or brackets) and a gap, so the next columns line up.
  const width = Math.max(0, ...data.agents.map(agent => name(agent).length)) + 3
  // User decision 01/11/2026: a row is the role's checkbox with its name (pressing the name toggles it, as in Settings), a
  // `default` checkbox, then the model as one radio group. The radio of the model the role runs on is chosen; `default`
  // ticked means it runs on the model `default` gives it, and choosing that model's radio ticks `default` again.
  const role = (agent: AgentRow) => option(ui, `on-${agent.role}`, name(agent), 'check', agent.active, () => {
    if (mode === 'A') return
    press(`agents.${agent.role}.enabled`, enabledFor(!agent.active, agent.in_mode))
  })
  const key = (agent: AgentRow) => `agents.${agent.role}.model`
  const byDefault = (agent: AgentRow) => option(ui, `${key(agent)}=default`, 'default', 'check', agent.model === 'default',
    // Unticking keeps the model the role runs on, now pinned; ticking hands it back to `default`.
    () => press(key(agent), agent.model === 'default' ? agent.runs_on : 'default'))
  // The model `default` gives; from an older script without `default_model`, known only while `default` is ticked.
  const givenByDefault = (agent: AgentRow) => agent.default_model ?? (agent.model === 'default' ? agent.runs_on : undefined)
  const models = (agent: AgentRow) => AGENT_MODELS.map(model => option(ui, `${key(agent)}=${model}`, model, 'radio', model === agent.runs_on,
    () => press(key(agent), model === givenByDefault(agent) ? 'default' : model)))
  return h(
    ui.Box,
    { flexDirection: 'column' },
    data.agents.map(agent =>
      line(ui, role(agent), agent.active ? [[byDefault(agent)], models(agent)] : [null], width, cells(['default']) + 1)),
  )
}

export function promotionBody(ui: Ui, data: PromotionData | null) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, 'Reading the branches…')
  if (data.error) return h(ui.Text, { dimColor: true }, data.error)
  return h(
    ui.Box,
    { flexDirection: 'column' },
    data.stages.map(stage =>
      h(ui.Box, { flexDirection: 'column', marginBottom: 1 },
        h(ui.Text, { bold: true }, `${stage.branch.padEnd(5)} origin ${stage.origin}${stage.unpushed > 0 ? `  ${stage.unpushed} not pushed` : '  pushed'}`),
        h(ui.Box, { flexDirection: 'column', marginLeft: INDENT },
          stage.waived.length === 0
            ? h(ui.Text, { dimColor: true }, 'no waived gate on the way in')
            : stage.waived.map(line => h(ui.Text, { color: WARN }, `waived ${line}`))))),
    data.stages.length === 0 ? h(ui.Text, { dimColor: true }, 'No dev, test or prod branch here.') : null,
  )
}
