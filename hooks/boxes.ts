// What the boxes of the adyusuf pane show, kept apart from the engine so it can be tested without one: no import from
// 'claude-code', no JSX. The element factory `h` and the elements themselves (Box, Text, Button) are handed in as
// `ui`: each surface has its own elements, and a test hands in a recording factory instead of the engine's. A choice among
// several values is a radio list (one Button per option, `(•)` on the chosen one), not a dropdown (user decision 24/10/2026).
import { enabledFor, settingGroups } from './choose'

export type Factory = (type: unknown, props: Record<string, unknown> | null, ...children: unknown[]) => unknown
export type Ui = { h: Factory; Box: unknown; Text: unknown; Button: unknown }
export type Press = (key: string, value: string) => void

type Spec = { key: string; type: 'bool' | 'enum'; label: string; group: string; options?: string[] }
type AgentRow = { role: string; defined: string; runs_on: string; active: boolean; in_mode: boolean; enabled: string; model: string }
type SettingsData = { schema: Spec[]; values: Record<string, boolean | string>; sources: Record<string, string>; agents: AgentRow[] }
type Stage = { branch: string; origin: string; unpushed: number; waived: string[] }
type PromotionData = { stages: Stage[]; error?: string }

export const SECTIONS = ['settings', 'agents', 'promotion'] as const
export type SectionId = (typeof SECTIONS)[number]

/** Sections that start folded, so the pane opens as a short card and not as one long list. */
export const FOLDED_AT_START: Record<string, boolean> = { agents: true, promotion: true }

const AGENT_MODELS = ['default', 'opus', 'sonnet', 'haiku', 'fable']

type Option = { value: string; label: string }

/** A radio list: the label, then one pressable line per option, the chosen one marked `(•)`. `wrap` lays the options in a row. */
export function radio(ui: Ui, key: string, label: string, options: Option[], value: string, press: Press, wrap = false) {
  const { h } = ui
  return h(
    ui.Box,
    { flexDirection: 'column' },
    h(ui.Text, {}, label),
    h(ui.Box, wrap ? { flexDirection: 'row', flexWrap: 'wrap', columnGap: 2, paddingLeft: 2 } : { flexDirection: 'column', paddingLeft: 2 },
      options.map(option =>
        h(ui.Button, { key: `${key}=${option.value}`, plain: true, onPress: () => press(key, option.value) },
          `${option.value === value ? '(•)' : '( )'} ${option.label}`))),
  )
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
  return changed > 0 ? `${changed} changed in this session` : 'this session only'
}

export function agentsSummary(data: SettingsData | null): string {
  if (!data) return ''
  const mode = String(data.values.mode)
  return mode === 'A' ? 'mode A: no agents' : `mode ${mode}: ${data.agents.filter(agent => agent.active).length} of ${data.agents.length} active`
}

export function promotionSummary(data: PromotionData | null): string {
  if (!data || data.error) return ''
  return data.stages.map(stage => `${stage.branch} ${stage.origin}`).join(' · ')
}

export function settingsBody(ui: Ui, data: SettingsData | null, problem: string, problems: string[], press: Press) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, problem || 'Reading the configuration…')
  const { groups, shown } = settingGroups(data.schema)
  return h(
    ui.Box,
    { flexDirection: 'column' },
    problem !== '' ? h(ui.Text, { color: 'red' }, problem) : null,
    problems.map(line => h(ui.Text, { color: 'yellow' }, `! ${line}`)),
    groups.map(group =>
      h(ui.Box, { flexDirection: 'column', marginBottom: 1 },
        h(ui.Text, { bold: true, dimColor: true }, group),
        shown.filter(spec => spec.group === group).map(spec => {
          const value = data.values[spec.key]
          const from = data.sources[spec.key]
          const tag = from && from !== 'default' ? ` (${from})` : ''
          if (spec.type === 'bool') {
            return h(ui.Button, { key: spec.key, onPress: () => void press(spec.key, value === true ? 'no' : 'yes') },
              value === true ? '[x] ' : '[ ] ', spec.label, tag)
          }
          return radio(ui, spec.key, `${spec.label}${tag}:`, (spec.options ?? []).map(option => ({ value: option, label: option })), String(value), press)
        })),
    ),
    h(ui.Text, { dimColor: true }, 'Changes apply to this session only; a new session starts from your saved defaults (/adyusuf:config saves them).'),
  )
}

export function agentsBody(ui: Ui, data: SettingsData | null, press: Press) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, 'Reading the configuration…')
  const mode = String(data.values.mode)
  const model = String(data.values.mode_model)
  return h(
    ui.Box,
    { flexDirection: 'column' },
    h(ui.Text, { dimColor: true }, `Opus agents run on ${model === 'keep' ? 'their defined model' : model} unless one is set below`),
    h(ui.Box, { flexDirection: 'column', marginTop: 1 },
      data.agents.map(agent =>
        h(ui.Box, { flexDirection: 'column', marginBottom: 1 },
          h(ui.Button, {
            key: `on-${agent.role}`,
            onPress: () => {
              if (mode === 'A') return
              press(`agents.${agent.role}.enabled`, enabledFor(!agent.active, agent.in_mode))
            },
          }, `${agent.active ? '[x] ' : '[ ] '}${agent.role}${!agent.in_mode && agent.active ? ' (added)' : ''}${agent.in_mode && !agent.active && mode !== 'A' ? ' (off)' : ''}`),
          agent.active
            ? radio(ui, `agents.${agent.role}.model`, `  model (defined ${agent.defined}):`,
              AGENT_MODELS.map(option => ({ value: option, label: option === 'default' ? `default (${agent.runs_on})` : option })),
              agent.model, press, true)
            : null)),
    ),
    h(ui.Text, { dimColor: true }, "A box ticked beyond the mode's set adds that agent; cleared, it removes one."),
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
