// What the boxes of the adyusuf pane show, kept apart from the engine so it can be tested without one: no import from
// 'claude-code', no JSX. The element factory `h` and the elements themselves (Box, Text, Button) are handed in as
// `ui`: each surface has its own elements, and a test hands in a recording factory instead of the engine's. A choice among
// several values is a row of options, not a dropdown (user decision 24/10/2026); every setting sits on one line, the label
// first and its pressable parts after it (user decision 28/10/2026). The labels are short and bold, with no trailing colon;
// what is chosen or on is drawn at full strength and the rest dimmed, with no `(•)`/`[x]` marker (user decision 01/11/2026:
// underline was asked for, but the desktop draws a Button as a native button and drops a Text's underline inside it).
import { enabledFor, settingGroups } from './choose'

export type Factory = (type: unknown, props: Record<string, unknown> | null, ...children: unknown[]) => unknown
export type Ui = { h: Factory; Box: unknown; Text: unknown; Button: unknown }
/** `session`: this session only; `saved`: the saved defaults every new session starts from (the user's file). */
export type Scope = 'session' | 'saved'
export type Press = (key: string, value: string, scope?: Scope) => void

type Spec = { key: string; type: 'bool' | 'enum'; label: string; group: string; options?: string[] }
type AgentRow = { role: string; defined: string; runs_on: string; active: boolean; in_mode: boolean; enabled: string; model: string }
type Layer = { values: Record<string, boolean | string>; sources: Record<string, string> }
type SettingsData = Layer & { schema: Spec[]; saved?: Layer; agents: AgentRow[] }
type Stage = { branch: string; origin: string; unpushed: number; waived: string[] }
type PromotionData = { stages: Stage[]; error?: string }

export const SECTIONS = ['settings', 'agents', 'promotion'] as const
export type SectionId = (typeof SECTIONS)[number]

/** Sections that start folded, so the pane opens as a short card and not as one long list. */
export const FOLDED_AT_START: Record<string, boolean> = { agents: true, promotion: true }

const AGENT_MODELS = ['default', 'opus', 'sonnet', 'haiku', 'fable']
const TARGETS = ['dev', 'test', 'prod']

type Item = { key: string; name: string }
type Row = { label: string; items: Item[] } | { label: string; key: string; names?: Record<string, string> }
const targets = (prefix: string, names = TARGETS): Item[] => names.map(name => ({ key: `${prefix}.${name}`, name }))

/** The lines of a settings block, in order. A setting the schema has and no row names is still drawn (see `block`). */
const ROWS: Row[] = [
  { label: 'Mode', key: 'mode' },
  { label: 'Model', key: 'mode_model', names: { keep: 'opus' } },
  { label: 'Pod', items: [{ key: 'pod.connect', name: 'connected' }] },
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

/** One line: the label, then its pressable parts side by side (they wrap when the pane is narrow). */
function line(ui: Ui, label: string, parts: unknown) {
  const { h } = ui
  return h(ui.Box, { flexDirection: 'row', flexWrap: 'wrap', columnGap: 1 }, label === '' ? null : h(ui.Text, { bold: true }, label), parts)
}

/** One pressable part: at full strength when it is the chosen option or a setting that is on, dimmed otherwise. */
function option(ui: Ui, key: string, text: string, chosen: boolean, onPress: () => void) {
  return ui.h(ui.Button, { key, plain: true, dimColor: !chosen, onPress }, text)
}

/** The options of one setting, the chosen one at full strength. */
function choices(ui: Ui, scope: Scope, key: string, options: Item[], value: string, press: Press) {
  return options.map(one =>
    option(ui, `${scope}/${key}=${one.key}`, one.name, one.key === value, () => press(key, one.key, scope)))
}

/** The yes/no settings of one line, each at full strength while it is on; pressing asks for the opposite. */
function checks(ui: Ui, scope: Scope, items: Item[], values: Layer['values'], press: Press) {
  return items.map(item => {
    const on = values[item.key] === true
    return option(ui, `${scope}/${item.key}`, item.name, on, () => press(item.key, on ? 'no' : 'yes', scope))
  })
}

/** One block of settings (the session's, or the saved defaults) as one line per row. */
function block(ui: Ui, title: string, scope: Scope, schema: Spec[], layer: Layer, press: Press) {
  const { h } = ui
  const { shown } = settingGroups(schema)
  const has = new Set(shown.map(spec => spec.key))
  const covered = new Set<string>()
  const lines: unknown[] = []
  for (const row of ROWS) {
    if ('items' in row) {
      const items = row.items.filter(item => has.has(item.key))
      items.forEach(item => covered.add(item.key))
      if (items.length > 0) lines.push(line(ui, row.label, checks(ui, scope, items, layer.values, press)))
      continue
    }
    const spec = shown.find(one => one.key === row.key)
    if (!spec) continue
    covered.add(row.key)
    const options = (spec.options ?? []).map(option => ({ key: option, name: row.names?.[option] ?? option }))
    lines.push(line(ui, row.label, choices(ui, scope, row.key, options, String(layer.values[row.key]), press)))
  }
  // A setting no row names (a newer plugin than this pane) must not vanish from view.
  for (const spec of shown.filter(one => !covered.has(one.key))) {
    lines.push(spec.type === 'bool'
      ? line(ui, '', checks(ui, scope, [{ key: spec.key, name: spec.label }], layer.values, press))
      : line(ui, spec.label, choices(ui, scope, spec.key, (spec.options ?? []).map(option => ({ key: option, name: option })),
        String(layer.values[spec.key]), press)))
  }
  return h(ui.Box, { flexDirection: 'column', marginBottom: 1 }, h(ui.Text, { bold: true }, title), lines)
}

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
    folded ? null : body,
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

export function settingsBody(ui: Ui, data: SettingsData | null, problem: string, problems: string[], press: Press) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, problem || 'Reading the configuration…')
  return h(
    ui.Box,
    { flexDirection: 'column' },
    problem !== '' ? h(ui.Text, { color: 'red' }, problem) : null,
    problems.map(line => h(ui.Text, { color: 'yellow' }, `! ${line}`)),
    block(ui, 'Session settings', 'session', data.schema, data, press),
    data.saved ? block(ui, 'Claude settings', 'saved', data.schema, data.saved, press) : null,
  )
}

export function agentsBody(ui: Ui, data: SettingsData | null, press: Press) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, 'Reading the configuration…')
  const mode = String(data.values.mode)
  return h(
    ui.Box,
    { flexDirection: 'column' },
    data.agents.map(agent =>
      line(ui, '', [
        option(ui, `on-${agent.role}`,
          `${agent.role}${!agent.in_mode && agent.active ? ' (added)' : ''}${agent.in_mode && !agent.active && mode !== 'A' ? ' (off)' : ''}`,
          agent.active, () => {
            if (mode === 'A') return
            press(`agents.${agent.role}.enabled`, enabledFor(!agent.active, agent.in_mode))
          }),
        // `default` is the choice; the model it resolves to is at full strength too, so the model the role runs on stays visible.
        agent.active
          ? AGENT_MODELS.map(model =>
            option(ui, `agents.${agent.role}.model=${model}`, model,
              model === agent.model || (agent.model === 'default' && model === agent.runs_on), () => press(`agents.${agent.role}.model`, model)))
          : null,
      ])),
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
        stage.waived.length === 0
          ? h(ui.Text, { dimColor: true }, 'no waived gate on the way in')
          : stage.waived.map(line => h(ui.Text, { color: 'yellow' }, `waived ${line}`)))),
    data.stages.length === 0 ? h(ui.Text, { dimColor: true }, 'No dev, test or prod branch here.') : null,
  )
}
