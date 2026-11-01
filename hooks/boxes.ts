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
import { cells, helpCard, hoverable, INDENT, label, line, option, WARN } from './controls'
import { COLUMN_HELP, ROW_HELP, SECTION_HELP } from './help'
import type { Ui } from './controls'

export type { Factory, Ui } from './controls'

/** `session`: this session only; `saved`: the saved defaults every new session starts from (the user's file). */
export type Scope = 'session' | 'saved'
export type Press = (key: string, value: string, scope?: Scope) => void

type Spec = { key: string; type: 'bool' | 'enum'; label: string; group: string; options?: string[] }
type AgentRow = {
  role: string; defined: string; runs_on: string; default_model?: string; active: boolean; in_mode: boolean; enabled: string; model: string
  description?: string
}
type Layer = { values: Record<string, boolean | string>; sources: Record<string, string> }
type SettingsData = Layer & { schema: Spec[]; saved?: Layer; agents: AgentRow[] }
type Stage = { branch: string; origin: string; unpushed: number; waived: string[] }
type PromotionData = { stages: Stage[]; error?: string; outside?: boolean }

export const SECTIONS = ['status', 'settings', 'agents', 'promotion'] as const
export type SectionId = (typeof SECTIONS)[number]

/**
 * What the pane shows. Outside a git repository the session is taken as no-code work: only Status and Settings, and
 * Settings only Replies (user decision 01/11/2026; standards/13 §8a). Until the folder is read, and inside a repository,
 * everything shows; a git failure that is not "outside" leaves `outside` unset, so it hides nothing.
 */
export function paneFor(promotion: PromotionData | null): { sections: SectionId[]; codeWork: boolean } {
  const outside = promotion?.outside === true
  return { sections: outside ? ['status', 'settings'] : [...SECTIONS], codeWork: !outside }
}

/** Whether the session's folder is outside every git repository: the engine's `session.repo()` answers null. */
export const outsideRepository = (repo: unknown) => repo === null
/** The one setting a task with no code uses. */
const NO_CODE_ROWS = ['Replies']

/**
 * What starts folded, so the pane opens as a short card and not as one long list: two boxes, and the System column of
 * Settings (the saved defaults, opened when wanted; user decision 01/11/2026).
 */
export const FOLDED_AT_START: Record<string, boolean> = { agents: true, promotion: true, claude: true }
/** What can fold: a box, or the System column of Settings (fold id `claude`, its first name). */
export type FoldId = SectionId | 'claude'

/** Whether `id` is folded; a state saved before `id` could fold falls back to how it starts. */
export const isFolded = (fold: Record<string, boolean>, id: FoldId) => fold[id] ?? FOLDED_AT_START[id] ?? false
/** The fold state after a press on `id`'s header: what it reads as now, turned over. */
export const nextFold = (fold: Record<string, boolean>, id: FoldId) => ({ ...fold, [id]: !isFolded(fold, id) })
/** The System column's fold: whether it is folded, and what a press on its heading does. */
export type ColumnFold = { folded: boolean; toggle: () => void }

/** The radio group of an agent's model. */
const AGENT_MODELS = ['opus', 'sonnet', 'haiku', 'fable']
const TARGETS = ['dev', 'test', 'prod']
/** The names the Agents box shows; the role (agent file, settings key) keeps its own name. */
const ROLE_NAMES: Record<string, string> = {
  'product-manager': 'product', 'test-writer': 'tester', 'doc-writer': 'doc', 'coverage-auditor': 'coverage', 'e2e-writer': 'e2e',
}

type Item = { key: string; name: string }
type Row = { label: string; items: Item[] } | { label: string; key: string; names?: Record<string, string> }
const targets = (prefix: string, names = TARGETS): Item[] => names.map(name => ({ key: `${prefix}.${name}`, name }))

/** The lines of a settings block, in order. A setting the schema has and no row names is still drawn (see `block`). */
export const ROWS: Row[] = [
  { label: 'Mode', key: 'mode' },
  // The star ties it to the Agents rows it acts on: the roles whose file says opus carry the same star.
  { label: 'Model*', key: 'mode_model', names: { keep: 'opus' } },
  { label: 'Replies', key: 'reply.length' },
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

/** The labels of the Settings rows, in order; every one has a hover card text in help.ts. */
export const ROW_LABELS = ROWS.map(row => row.label)

/** The width of the label column of a settings block, in cells: the longest label and a gap. */
const LABEL_WIDTH = Math.max(...ROWS.map(row => row.label.length)) + 2

/** The name an Agents row shows: the short name and a star for an opus role (Model* replaces exactly those roles). */
const agentName = (agent: AgentRow) => `${ROLE_NAMES[agent.role] ?? agent.role}${agent.defined === 'opus' ? '*' : ''}`

/** Whether a role was added to the mode or taken out of it; drawn at the end of its row, so it never widens the names. */
function agentMark(agent: AgentRow, mode: string) {
  if (!agent.in_mode && agent.active) return '(added)'
  return agent.in_mode && !agent.active && mode !== 'A' ? '(off)' : ''
}

/**
 * The head column of Settings and Agents, one width for both, so their options start at the same place (user decision
 * 01/11/2026): the longest label, or the longest name of a role that is on (its checkbox and a gap counted). A role
 * that is off has no radios after it, so its name does not widen the column.
 */
export function headWidth(data: SettingsData) {
  return Math.max(LABEL_WIDTH, ...data.agents.filter(agent => agent.active).map(agent => agentName(agent).length + 3))
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

/**
 * One bordered box with a header that folds it. The header is the arrow and the title alone, nothing beside it (user
 * decision 01/11/2026: a summary there made the pane cluttered). The title is a bold Text and only the arrow is pressable:
 * inside a Button the desktop drops the bold.
 */
export function section(ui: Ui, id: SectionId, title: string, folded: boolean, toggle: () => void, body: unknown) {
  const { h } = ui
  return h(
    ui.Box,
    { flexDirection: 'column', borderStyle: 'round', paddingX: 1, marginBottom: 1 },
    h(ui.Box, { flexDirection: 'row', columnGap: 1 },
      h(ui.Button, { key: `fold-${id}`, plain: true, onPress: toggle }, folded ? '▸' : '▾'),
      hoverable(ui, `section-${id}`, h(ui.Text, { bold: true }, title))),
    helpCard(ui, `section-${id}`, SECTION_HELP[id]),
    folded ? null : h(ui.Box, { flexDirection: 'column', marginLeft: INDENT }, body),
  )
}

/**
 * The settings as one table (user decision 01/11/2026): a label, this session's options (a press changes this session
 * only), then the saved defaults' options (a press changes `~/.claude/adyusuf.json`, which new sessions start from). The
 * System heading folds that column; folded, only the heading is left, right beside Session and pointing right (`System ▸`),
 * and open it sits over its column pointing back (`System ◂`) (user decisions 01/11/2026). The heading is a bold Text with
 * only the arrow pressable: the desktop draws a Button as a native button, which drops the bold and pads the text out of
 * line with the column. The fold keeps its first id, `claude`, so a saved fold state still applies.
 */
function table(ui: Ui, data: SettingsData, press: Press, claude: ColumnFold, codeWork: boolean) {
  const { h } = ui
  const lines = settingLines(ui, data.schema, press).filter(one => codeWork || NO_CODE_ROWS.includes(one.label))
  const width = Math.max(0, ...lines.map(one => cells(one.names))) + 2
  const head = headWidth(data)
  const saved = data.saved && !claude.folded ? [['saved', data.saved] as [Scope, Layer]] : []
  const layers: [Scope, Layer][] = [['session', data], ...saved]
  const heads = [
    hoverable(ui, 'column-Session', h(ui.Text, { bold: true }, 'Session')),
    data.saved
      // The desktop's native button pads the arrow already, so a gap there would leave it far from the name.
      ? h(ui.Box, { flexDirection: 'row', columnGap: ui.Svg ? 0 : 1 }, hoverable(ui, 'column-System', h(ui.Text, { bold: true }, 'System')),
        h(ui.Button, { key: 'fold-claude', plain: true, onPress: claude.toggle }, claude.folded ? '▸' : '◂'))
      : null,
  ].filter(head => head !== null)
  // Each card is a hidden row right after its label's line.
  return h(ui.Box, { flexDirection: 'column' },
    line(ui, null, heads, head, claude.folded ? 0 : width),
    helpCard(ui, 'column-Session', COLUMN_HELP.Session),
    data.saved ? helpCard(ui, 'column-System', COLUMN_HELP.System) : null,
    lines.flatMap(one => [
      line(ui, hoverable(ui, `row-${one.label}`, label(ui, one.label)), layers.map(([scope, layer]) => one.draw(scope, layer)), head, width),
      helpCard(ui, `row-${one.label}`, ROW_HELP[one.label])]))
}

const OPEN: ColumnFold = { folded: false, toggle: () => undefined }

export function settingsBody(ui: Ui, data: SettingsData | null, problem: string, problems: string[], press: Press, claude = OPEN,
  codeWork = true) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, problem || 'Reading the configuration…')
  return h(
    ui.Box,
    { flexDirection: 'column' },
    problem !== '' ? h(ui.Text, { color: 'red' }, problem) : null,
    problems.map(line => h(ui.Text, { color: WARN }, `! ${line}`)),
    codeWork ? null : h(ui.Text, { dimColor: true }, 'No repository here: only Replies shows. Change the rest with /adyusuf:config.'),
    table(ui, data, press, claude, codeWork),
  )
}

export function agentsBody(ui: Ui, data: SettingsData | null, press: Press) {
  const { h } = ui
  if (!data) return h(ui.Text, { dimColor: true }, 'Reading the configuration…')
  const mode = String(data.values.mode)
  const width = headWidth(data)
  // User decisions 01/11/2026: a row is the role's checkbox with its name (pressing the name toggles it, as in Settings),
  // then the model as one radio group; the `default` checkbox that sat between them is gone. The radio of the model the
  // role runs on is chosen; choosing the model `default` gives writes `default`, any other pins that model.
  // A role that runs is named in bold (user decision 02/11/2026). Bold cannot sit inside a Button on the desktop, so the
  // name is a Text and only the checkbox before it, a glyph Button, toggles the role.
  const role = (agent: AgentRow) => h(ui.Box, { flexDirection: 'row', columnGap: 1 },
    h(ui.Button, { key: `on-${agent.role}`, plain: true, dimColor: !agent.active, onPress: () => {
      if (mode === 'A') return
      press(`agents.${agent.role}.enabled`, enabledFor(!agent.active, agent.in_mode))
    } }, agent.active ? '☑' : '☐'),
    h(ui.Text, agent.active ? { bold: true } : { dimColor: true }, agentName(agent)))
  const key = (agent: AgentRow) => `agents.${agent.role}.model`
  // The model `default` gives; from an older script without `default_model`, known only while the role is on `default`.
  const givenByDefault = (agent: AgentRow) => agent.default_model ?? (agent.model === 'default' ? agent.runs_on : undefined)
  const mark = (agent: AgentRow) => (agentMark(agent, mode) === '' ? null : h(ui.Text, { dimColor: true }, agentMark(agent, mode)))
  const models = (agent: AgentRow) => AGENT_MODELS.map(model => option(ui, `${key(agent)}=${model}`, model, 'radio', model === agent.runs_on,
    () => press(key(agent), model === givenByDefault(agent) ? 'default' : model)))
  return h(
    ui.Box,
    { flexDirection: 'column' },
    // The header says nothing beside its title, so mode A, where no press takes effect, says so here.
    mode === 'A' ? h(ui.Text, { dimColor: true }, 'mode A runs no agents') : null,
    // A role's card is its agent file's description, a hidden row right after its line.
    data.agents.flatMap(agent => [
      line(ui, hoverable(ui, `agent-${agent.role}`, role(agent)), [[...(agent.active ? models(agent) : []), mark(agent)]], width),
      helpCard(ui, `agent-${agent.role}`, agent.description)]),
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
