import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { AgentRow, Promotion, Settings, Stage } from '../types'
import { countOf, enabledFor, overrideNote, plannedStages, refSet, scriptDir, settingGroups, waivedLines, waivedRange } from './choose'

const SETTINGS = 'adyusuf-settings'
const AGENTS = 'adyusuf-agents'
const PROMOTION = 'adyusuf-promotion'

const settings = atom({ plugin: 'adyusuf', key: 'settings' } as const, null)
const settingsError = atom({ plugin: 'adyusuf', key: 'settingsError' } as const, '')
const settingsProblems = atom({ plugin: 'adyusuf', key: 'settingsProblems' } as const, [])
const promotion = atom({ plugin: 'adyusuf', key: 'promotion' } as const, null)

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

const AGENT_MODELS = ['default', 'opus', 'sonnet', 'haiku', 'fable']

// Clicks run one after another: two settings changed quickly must not race each other's read-modify-write.
let queue: Promise<void> = Promise.resolve()
function click($: EngineInterface, key: string, value: string) {
  queue = queue.then(() => setSetting($, key, value)).catch(() => undefined)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'adyusuf:panels', description: 'Open the adyusuf settings, agents and promotion boxes' })
    void $.ui.open({ id: SETTINGS, title: 'Settings' })
    void $.ui.open({ id: AGENTS, title: 'Agents' })
    void $.ui.open({ id: PROMOTION, title: 'Promotion' })
    await safely($, refreshSettings($))
    await safely($, refreshPromotion($))
    return next(e)
  })

  on('command.run', { command: 'adyusuf:panels' }, async $ => {
    await $.ui.open({ id: SETTINGS, title: 'Settings' })
    await $.ui.open({ id: AGENTS, title: 'Agents' })
    await $.ui.open({ id: PROMOTION, title: 'Promotion' })
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

  on('ui.render', { component: 'Pane', requestId: SETTINGS }, async ($, e) => {
    const { Box, Text, Button, Select } = $.ui.resolve(e)
    const data = await read($, settings)
    const problem = await read($, settingsError)
    const problems = await read($, settingsProblems)
    if (!data) return <Text dimColor>{problem || 'Reading the configuration…'}</Text>
    const { groups, shown: shownSchema } = settingGroups(data.schema)
    const set = (key: string, value: string) => click($, key, value)
    return (
      <Box flexDirection="column">
        {problem !== '' && <Text color="red">{problem}</Text>}
        {problems.map(line => <Text color="yellow">! {line}</Text>)}
        {groups.map(group => (
          <Box flexDirection="column" marginBottom={1}>
            <Text bold dimColor>{group}</Text>
            {shownSchema.filter(spec => spec.group === group).map(spec => {
              const value = data.values[spec.key]
              const from = data.sources[spec.key]
              if (spec.type === 'bool') {
                return (
                  <Button key={spec.key} onPress={() => void set(spec.key, value === true ? 'no' : 'yes')}>
                    {value === true ? '[x] ' : '[ ] '}{spec.label}{from && from !== 'default' ? ` (${from})` : ''}
                  </Button>
                )
              }
              return (
                <Select
                  key={spec.key}
                  label={`${spec.label}${from && from !== 'default' ? ` (${from})` : ''}:`}
                  value={String(value)}
                  options={(spec.options ?? []).map(option => ({ value: option, label: option }))}
                  onSelect={picked => void set(spec.key, picked)}
                />
              )
            })}
          </Box>
        ))}
        <Text dimColor>Changes apply to this session only; a new session starts from your saved defaults (/adyusuf:config saves them).</Text>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: AGENTS }, async ($, e) => {
    const { Box, Text, Button, Select } = $.ui.resolve(e)
    const data = await read($, settings)
    if (!data) return <Text dimColor>Reading the configuration…</Text>
    const mode = String(data.values.mode)
    const model = String(data.values.mode_model)
    const active = data.agents.filter(agent => agent.active).length
    return (
      <Box flexDirection="column">
        <Text bold>
          Mode {mode}: {mode === 'A' ? 'no agents, the session works alone' : `${active} of ${data.agents.length} agents active`}
        </Text>
        <Text dimColor>Opus agents run on {model === 'keep' ? 'their defined model' : model} unless one is set below</Text>
        <Box flexDirection="column" marginTop={1}>
          {data.agents.map(agent => (
            <Box flexDirection="column" marginBottom={1}>
              <Button
                key={`on-${agent.role}`}
                onPress={() => {
                  if (mode === 'A') return
                  click($, `agents.${agent.role}.enabled`, enabledFor(!agent.active, agent.in_mode))
                }}
              >
                {agent.active ? '[x] ' : '[ ] '}{agent.role}{!agent.in_mode && agent.active ? ' (added)' : ''}{agent.in_mode && !agent.active && mode !== 'A' ? ' (off)' : ''}
              </Button>
              {agent.active && (
                <Select
                  key={`model-${agent.role}`}
                  label={`  model (defined ${agent.defined}):`}
                  value={agent.model}
                  options={AGENT_MODELS.map(option => ({ value: option, label: option === 'default' ? `default (${agent.runs_on})` : option }))}
                  onSelect={picked => click($, `agents.${agent.role}.model`, picked)}
                />
              )}
            </Box>
          ))}
        </Box>
        <Text dimColor>A box ticked beyond the mode's set adds that agent; cleared, it removes one.</Text>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PROMOTION }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const data = await read($, promotion)
    if (!data) return <Text dimColor>Reading the branches…</Text>
    if (data.error) return <Text dimColor>{data.error}</Text>
    return (
      <Box flexDirection="column">
        {data.stages.map(stage => (
          <Box flexDirection="column" marginBottom={1}>
            <Text bold>
              {stage.branch.padEnd(5)} origin {stage.origin}
              {stage.unpushed > 0 ? `  ${stage.unpushed} not pushed` : '  pushed'}
            </Text>
            {stage.waived.length === 0 ? (
              <Text dimColor>no waived gate on the way in</Text>
            ) : (
              stage.waived.map(line => <Text color="yellow">waived {line}</Text>)
            )}
          </Box>
        ))}
        {data.stages.length === 0 && <Text dimColor>No dev, test or prod branch here.</Text>}
      </Box>
    )
  })
}
