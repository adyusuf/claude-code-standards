import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { AgentRow, Promotion, Settings, Stage } from '../types'
import {
  agentsBody, agentsSummary, FOLDED_AT_START, promotionBody, promotionSummary, section, settingsBody, settingsSummary,
} from './boxes'
import type { SectionId } from './boxes'
import { countOf, overrideNote, plannedStages, refSet, scriptDir, waivedLines, waivedRange } from './choose'

/** One pane, three bordered boxes in it (Settings, Agents, Promotion), each folded by its header. */
const BOXES = 'adyusuf-boxes'
const TITLE = 'adyusuf'

const settings = atom({ plugin: 'adyusuf', key: 'settings' } as const, null)
const settingsError = atom({ plugin: 'adyusuf', key: 'settingsError' } as const, '')
const settingsProblems = atom({ plugin: 'adyusuf', key: 'settingsProblems' } as const, [])
const promotion = atom({ plugin: 'adyusuf', key: 'promotion' } as const, null)
const folded = atom({ plugin: 'adyusuf', key: 'folded' } as const, FOLDED_AT_START)

const PLUGIN_ID = 'adyusuf@adyusuf-marketplace'
const CACHE = '$HOME/.claude/plugins/cache/adyusuf-marketplace/adyusuf'

type Run = (argv: readonly string[]) => Promise<{ exitCode: number; stdout: string; stderr: string }>

/** The configuration script of the INSTALLED adyusuf plugin ('' when it has none yet); the choice is choose.ts's scriptDir. */
async function scriptPath(run: Run): Promise<string> {
  const record = await run(['sh', '-c', 'cat "$HOME/.claude/plugins/installed_plugins.json" 2>/dev/null'])
  const cache = await run(['sh', '-c', `for d in $(ls -dt ${CACHE}/*/ 2>/dev/null); do if [ -e "$d.orphaned_at" ]; then echo "orphaned $d"; else echo "live $d"; fi; done`])
  const dir = scriptDir(record.stdout, PLUGIN_ID, cache.stdout)
  if (!dir) return ''
  const has = await run(['test', '-f', `${dir}/scripts/adyusuf_config.py`])
  return has.exitCode === 0 ? `${dir}/scripts/adyusuf_config.py` : ''
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
    await update($, settingsError, () => 'The adyusuf plugin with /adyusuf:config is not installed yet: /plugin update adyusuf')
    return
  }
  const id = await sessionId($)
  const scope = id ? ['--session', id] : []
  const shown = await run(['python3', script, 'show', '--json', ...scope])
  const agents = await run(['python3', script, 'agents', '--json', '--all', ...scope])
  const schema = await run(['python3', script, 'schema'])
  if (shown.exitCode !== 0 || agents.exitCode !== 0 || schema.exitCode !== 0) {
    await update($, settingsError, () => (shown.stderr || agents.stderr || schema.stderr || 'adyusuf_config.py failed').slice(0, 300))
    return
  }
  try {
    const data = JSON.parse(shown.stdout) as { values: Settings['values']; sources: Settings['sources']; problems?: string[] }
    const next: Settings = {
      schema: JSON.parse(schema.stdout),
      values: data.values,
      sources: data.sources,
      agents: JSON.parse(agents.stdout) as AgentRow[],
    }
    await update($, settings, () => next)
    await update($, settingsError, () => '')
    await update($, settingsProblems, () => data.problems ?? [])
  } catch (error) {
    await update($, settingsError, () => `Unreadable answer from adyusuf_config.py: ${String(error).slice(0, 200)}`)
  }
}

async function refreshPromotion($: EngineInterface) {
  const git = (args: string[]) => $.process.run(['git', ...args])
  const refs = await git(['for-each-ref', '--format=%(refname:short)', 'refs/heads', 'refs/remotes/origin'])
  if (refs.exitCode !== 0) {
    await update($, promotion, () => ({ stages: [], error: 'Not inside a git repository' }) as Promotion)
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
  await update($, promotion, () => ({ stages }) as Promotion)
}


async function setSetting($: EngineInterface, key: string, value: string) {
  const run: Run = argv => $.process.run(argv)
  const script = await scriptPath(run)
  if (!script) {
    await $.ui.toast('The adyusuf plugin is not installed yet: /plugin install adyusuf@adyusuf-marketplace')
    return
  }
  const id = await sessionId($)
  if (!id) {
    await $.ui.toast('Could not tell which session this is, so nothing was changed (the saved defaults stay as they are)')
    return
  }
  const done = await run(['python3', script, 'set', '--session', id, key, value])
  if (done.exitCode !== 0) await $.ui.toast(done.stderr.trim().slice(0, 200) || 'The change was refused')
  await refreshSettings($)
  const now = await read($, settings)
  if (done.exitCode === 0 && now) {
    const note = overrideNote(key, value, now.values[key], now.sources[key])
    if (note) await $.ui.toast(note)
  }
}

/** A failing read must never stop the session from starting; the Settings box says what failed instead of waiting forever. */
async function safely($: EngineInterface, work: Promise<void>) {
  try {
    await work
  } catch (error) {
    await update($, settingsError, () => `Could not read: ${String(error).slice(0, 200)}`)
  }
}

// Clicks run one after another: two settings changed quickly must not race each other's read-modify-write.
let queue: Promise<void> = Promise.resolve()
function click($: EngineInterface, key: string, value: string) {
  queue = queue.then(() => setSetting($, key, value)).catch(() => undefined)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'adyusuf:panels', description: 'Open the adyusuf settings, agents and promotion boxes' })
    void $.ui.open({ id: BOXES, title: TITLE })
    await safely($, refreshSettings($))
    await safely($, refreshPromotion($))
    return next(e)
  })

  on('command.run', { command: 'adyusuf:panels' }, async $ => {
    await $.ui.open({ id: BOXES, title: TITLE })
    await safely($, refreshSettings($))
    await safely($, refreshPromotion($))
    return { text: 'adyusuf boxes opened.' }
  })

  // The boxes follow the work: a turn may have merged, pushed or changed a setting through /adyusuf:config.
  on('turn.complete', async ($, e, next) => {
    await safely($, refreshSettings($))
    await safely($, refreshPromotion($))
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: BOXES }, async ($, e) => {
    const ui = { ...$.ui.resolve(e), h }
    const { Box } = ui
    const data = await read($, settings)
    const problem = await read($, settingsError)
    const problems = await read($, settingsProblems)
    const stages = await read($, promotion)
    const fold = await read($, folded)
    const press = (key: string, value: string) => click($, key, value)
    const toggle = (id: SectionId) => () => void update($, folded, now => ({ ...now, [id]: !now[id] }))
    return (
      <Box flexDirection="column">
        {section(ui, 'settings', 'Settings', settingsSummary(data), fold.settings === true, toggle('settings'),
          settingsBody(ui, data, problem, problems, press))}
        {section(ui, 'agents', 'Agents', agentsSummary(data), fold.agents === true, toggle('agents'),
          agentsBody(ui, data, press))}
        {section(ui, 'promotion', 'Promotion', promotionSummary(stages), fold.promotion === true, toggle('promotion'),
          promotionBody(ui, stages))}
      </Box>
    )
  })
}
