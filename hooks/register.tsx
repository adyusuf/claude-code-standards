import type { EngineInterface, Hook, Register } from 'claude-code'

import type { AgentRow, Promotion, Settings, Stage } from '../types'
import {
  agentsBody, agentsSummary, FOLDED_AT_START, isFolded, nextFold, promotionBody, promotionSummary, section, settingsBody, settingsSummary,
} from './boxes'
import type { FoldId, Scope, SectionId } from './boxes'
import {
  countOf, DISCOVER_PY, IS_FILE_PY, overrideNote, parseDiscovery, plannedStages, refSet, scriptDir, waivedLines, waivedRange,
} from './choose'
import { operationWarnings, warnings } from './notices'
import { parseStatus, statusBody, statusDir, statusStep, statusSummary } from './status'
import type { StatusProbe } from './status'

/** One pane, four bordered boxes in it (Status, Settings, Agents, Promotion), each folded by its header. */
const BOXES = 'adyusuf-boxes'
const TITLE = 'adyusuf'

// The pane's values live in `$.state`, declared in ../types; a value never written reads as undefined, so each read names its initial one.
const settings = { plugin: 'adyusuf', key: 'settings' } as const
const settingsError = { plugin: 'adyusuf', key: 'settingsError' } as const
const settingsProblems = { plugin: 'adyusuf', key: 'settingsProblems' } as const
const promotion = { plugin: 'adyusuf', key: 'promotion' } as const
const folded = { plugin: 'adyusuf', key: 'folded' } as const
const status = { plugin: 'adyusuf', key: 'status' } as const

/** How often the Status box looks at its file while nothing else wakes it (a background run writing its steps). */
const STATUS_POLL_MS = 2000

const PLUGIN = 'adyusuf'
const MARKETPLACE = 'adyusuf-marketplace'
const PLUGIN_ID = `${PLUGIN}@${MARKETPLACE}`

type Run = (argv: readonly string[]) => Promise<{ exitCode: number; stdout: string; stderr: string }>

/** The configuration script of the INSTALLED adyusuf plugin ('' when it has none yet); the choice is choose.ts's scriptDir. */
async function scriptPath(run: Run): Promise<string> {
  const found = await run(['python3', '-c', DISCOVER_PY, MARKETPLACE, PLUGIN])
  const { record, listing } = parseDiscovery(found.stdout)
  const dir = scriptDir(record, PLUGIN_ID, listing)
  if (!dir) return ''
  const script = `${dir}/scripts/adyusuf_config.py`
  const has = await run(['python3', '-c', IS_FILE_PY, script])
  return has.exitCode === 0 ? script : ''
}

/** This session's id ('' when the engine will not say): the boxes change THIS session's layer only, never the saved defaults. */
async function sessionId($: EngineInterface): Promise<string> {
  try {
    return (await $.session.id()) || ''
  } catch {
    return ''
  }
}

async function refreshSettings($: EngineInterface) {
  const run: Run = argv => $.process.run(argv)
  const script = await scriptPath(run)
  if (!script) {
    await $.state.set(settingsError, 'The adyusuf plugin with /adyusuf:config is not installed yet: /plugin update adyusuf')
    return
  }
  const id = await sessionId($)
  const scope = id ? ['--session', id] : []
  const shown = await run(['python3', script, 'show', '--json', ...scope])
  const agents = await run(['python3', script, 'agents', '--json', '--all', ...scope])
  const schema = await run(['python3', script, 'schema'])
  // The "Claude settings" block: the shipped defaults and the user's own file, with no project or session layer (user decision 28/10/2026).
  const savedRead = await run(['python3', script, 'show', '--json', '--user'])
  if (shown.exitCode !== 0 || agents.exitCode !== 0 || schema.exitCode !== 0 || savedRead.exitCode !== 0) {
    await $.state.set(settingsError, (shown.stderr || agents.stderr || schema.stderr || savedRead.stderr || 'adyusuf_config.py failed').slice(0, 300))
    return
  }
  try {
    const data = JSON.parse(shown.stdout) as { values: Settings['values']; sources: Settings['sources']; problems?: string[] }
    const saved = JSON.parse(savedRead.stdout) as { values: Settings['values']; sources: Settings['sources'] }
    const next: Settings = {
      schema: JSON.parse(schema.stdout),
      values: data.values,
      sources: data.sources,
      saved: { values: saved.values, sources: saved.sources },
      agents: JSON.parse(agents.stdout) as AgentRow[],
    }
    // Every change since the last read (a press in the boxes, /adyusuf:config, a hand edit) is a warning in the chat, with its rules.
    const { value: before = null } = await $.state.get(settings)
    await $.state.set(settings, next)
    for (const line of warnings(before, next)) $.ui.log(line)
    await $.state.set(settingsError, '')
    await $.state.set(settingsProblems, data.problems ?? [])
  } catch (error) {
    await $.state.set(settingsError, `Unreadable answer from adyusuf_config.py: ${String(error).slice(0, 200)}`)
  }
}

async function refreshPromotion($: EngineInterface) {
  const git = (args: string[]) => $.process.run(['git', ...args])
  const refs = await git(['for-each-ref', '--format=%(refname:short)', 'refs/heads', 'refs/remotes/origin'])
  if (refs.exitCode !== 0) {
    await $.state.set(promotion, ({ stages: [], error: 'Not inside a git repository' }) as Promotion)
    return
  }
  const stages: Stage[] = []
  for (const stage of plannedStages(refSet(refs.stdout))) {
    const tip = await git(['rev-parse', '--short', `origin/${stage.branch}`])
    const ahead = stage.local ? await git(['rev-list', '--count', `origin/${stage.branch}..${stage.branch}`]) : null
    const range = waivedRange(stage)
    const log = range ? await git(['log', '--format=@@%h%n%B', range]) : null
    stages.push({
      branch: stage.branch,
      origin: tip.stdout.trim(),
      unpushed: ahead ? countOf(ahead.stdout) : 0,
      waived: log && log.exitCode === 0 ? waivedLines(log.stdout) : [],
    })
  }
  await $.state.set(promotion, ({ stages }) as Promotion)
}


/** `session` writes this session's layer; `saved` writes the user's file, the defaults every new session starts from. */
async function setSetting($: EngineInterface, key: string, value: string, scope: Scope) {
  const run: Run = argv => $.process.run(argv)
  const script = await scriptPath(run)
  if (!script) {
    await $.ui.toast('The adyusuf plugin is not installed yet: /plugin install adyusuf@adyusuf-marketplace')
    return
  }
  const id = scope === 'session' ? await sessionId($) : ''
  if (scope === 'session' && !id) {
    await $.ui.toast('Could not tell which session this is, so nothing was changed (the saved defaults stay as they are)')
    return
  }
  const done = await run(['python3', script, 'set', ...(id ? ['--session', id] : []), key, value])
  if (done.exitCode !== 0) await $.ui.toast(done.stderr.trim().slice(0, 200) || 'The change was refused')
  await refreshSettings($)
  const { value: now = null } = await $.state.get(settings)
  const layer = scope === 'saved' ? now?.saved : now
  if (done.exitCode === 0 && layer) {
    const note = overrideNote(key, value, layer.values[key], layer.sources[key])
    if (note) await $.ui.toast(note)
  }
}

/** This session's status file ('' when the engine will not say which session this is, or no folder is usable). */
async function statusPath($: EngineInterface): Promise<string> {
  const id = await sessionId($)
  const dir = statusDir(await $.env.get('ADYUSUF_STATUS_DIR'), await $.env.get('USERPROFILE'), await $.env.get('HOME'))
  return id && dir ? `${dir}/${id}.json` : ''
}

// The file's modification time at the last read; status.ts's statusStep decides from it whether to read, clear or keep.
let statusStamp = -1
let statusWarned = false
/** One refresh: look at the file, then read, clear or keep as statusStep says. A read error keeps the last table. */
async function readStatus($: EngineInterface) {
  const path = await statusPath($)
  if (!path) return
  let probe: StatusProbe
  try {
    probe = (await $.fs.exists(path)) ? { kind: 'file', mtimeMs: (await $.fs.stat(path)).mtimeMs } : { kind: 'missing' }
  } catch {
    probe = { kind: 'error' }
  }
  let step = statusStep(statusStamp, probe)
  if (step.action === 'read') {
    try {
      await $.state.set(status, parseStatus(await $.fs.read(path)))
    } catch {
      step = statusStep(step.stamp, { kind: 'error' })
    }
  } else if (step.action === 'clear') {
    await $.state.set(status, null)
  }
  statusStamp = step.stamp
  if (step.stamp === -1 && !statusWarned) {
    statusWarned = true
    $.ui.log(`adyusuf: the Status box cannot read ${path}; it keeps its last table and tries again`)
  }
}

// Refreshes run one after another (trigger, poll and turn end may overlap): an older read must not land after a newer one.
let statusQueue: Promise<void> = Promise.resolve()
function refreshStatus($: EngineInterface): Promise<void> {
  statusQueue = statusQueue.then(() => readStatus($)).catch(() => undefined)
  return statusQueue
}
// The one poll of this process: a second session.start (a resume, a reload) replaces it instead of stacking another.
let statusPoll: { cancel: () => void } | undefined

/** A failing read must never stop the session from starting; the Settings box says what failed instead of waiting forever. */
async function safely($: EngineInterface, work: Promise<void>) {
  try {
    await work
  } catch (error) {
    await $.state.set(settingsError, `Could not read: ${String(error).slice(0, 200)}`)
  }
}

/** Folds or unfolds one box of the pane, or the System column; called from a press, never while drawing. */
async function flip($: EngineInterface, id: FoldId) {
  const { value: now = FOLDED_AT_START } = await $.state.get(folded)
  await $.state.set(folded, nextFold(now, id))
}

// Clicks run one after another: two settings changed quickly must not race each other's read-modify-write.
let queue: Promise<void> = Promise.resolve()
function click($: EngineInterface, key: string, value: string, scope: Scope) {
  queue = queue.then(() => setSetting($, key, value, scope)).catch(() => undefined)
}

const onStart: Hook<'session.start'> = async ($, e, next) => {
  await $.command.register({ name: 'adyusuf:panels', description: 'Open the adyusuf status, settings, agents and promotion boxes' })
  void $.ui.open({ id: BOXES, title: TITLE })
  await safely($, refreshSettings($))
  await safely($, refreshPromotion($))
  await refreshStatus($)
  // Polling covers what changes while no tool runs (a background gate writing its steps); it reads only on a new mtime.
  statusPoll?.cancel()
  statusPoll = $.clock.every(STATUS_POLL_MS, () => void refreshStatus($))
  return next(e)
}

const onPanels: Hook<'command.run'> = async $ => {
  await $.ui.open({ id: BOXES, title: TITLE })
  await safely($, refreshSettings($))
  await safely($, refreshPromotion($))
  statusStamp = -1
  await refreshStatus($)
  return { text: 'adyusuf boxes opened.' }
}

// The boxes follow the work: a turn may have merged, pushed or changed a setting through /adyusuf:config.
const onTurnComplete: Hook<'turn.complete'> = async ($, e, next) => {
  await safely($, refreshSettings($))
  await safely($, refreshPromotion($))
  await refreshStatus($)
  return next(e)
}

// The trigger: when a tool call returns (Claude's own status update is one), the Status box is current at once.
const onAnyTool: Hook<'tool.call'> = async ($, e, next) => {
  const result = await next(e)
  // `next(e)` resolves with the tool's own result (ToolCallResult), so this runs after the tool. Not awaited: the refresh
  // must never delay or fail the tool call it follows; refreshStatus never rejects.
  void refreshStatus($)
  return result
}

// A merge, a push or a gate run in a shell command is a warning in the chat before it runs, with the rules it falls under.
const onShell: Hook<'tool.call'> = async ($, e, next) => {
  const command = 'command' in e ? String(e.command) : ''
  for (const line of operationWarnings(command)) $.ui.log(line)
  return next(e)
}

const onRender: Hook<'ui.render'> = async ($, e) => {
  const ui = { ...$.ui.resolve(e), h }
  const { Box } = ui
  const { value: data = null } = await $.state.get(settings)
  const { value: problem = '' } = await $.state.get(settingsError)
  const { value: problems = [] } = await $.state.get(settingsProblems)
  const { value: stages = null } = await $.state.get(promotion)
  const { value: fold = FOLDED_AT_START } = await $.state.get(folded)
  const { value: now = null } = await $.state.get(status)
  const press = (key: string, value: string, scope: Scope = 'session') => click($, key, value, scope)
  const toggle = (id: FoldId) => () => void flip($, id)
  const shut = (id: SectionId) => isFolded(fold, id)
  const claude = { folded: isFolded(fold, 'claude'), toggle: toggle('claude') }
  return (
    <Box flexDirection="column">
      {section(ui, 'status', 'Status', statusSummary(now), shut('status'), toggle('status'), statusBody(ui, now))}
      {section(ui, 'settings', 'Settings', settingsSummary(data), shut('settings'), toggle('settings'),
        settingsBody(ui, data, problem, problems, press, claude))}
      {section(ui, 'agents', 'Agents', agentsSummary(data), shut('agents'), toggle('agents'),
        agentsBody(ui, data, press))}
      {section(ui, 'promotion', 'Promotion', promotionSummary(stages), shut('promotion'), toggle('promotion'),
        promotionBody(ui, stages))}
    </Box>
  )
}

export const register: Register = on => {
  on('session.start', onStart)
  on('command.run', { command: 'adyusuf:panels' }, onPanels)
  on('turn.complete', onTurnComplete)
  on('tool.call', { tool: 'Bash' }, onShell)
  on('tool.call', { tool: 'PowerShell' }, onShell)
  on('tool.call', onAnyTool)
  on('ui.render', { component: 'Pane', requestId: BOXES }, onRender)
}
