import { expect, test } from 'claude-code/testing'

import {
  countOf, enabledFor, installPathOf, isWanted, newestLiveDir, overrideNote, plannedStages, refSet, scriptDir, settingGroups,
  waivedLines, waivedRange,
} from './choose'

const ID = 'adyusuf@adyusuf-marketplace'

test('the install folder is the one the plugin manager records, not a newer replaced one', () => {
  const record = JSON.stringify({
    version: 2,
    plugins: { [ID]: [{ scope: 'user', installPath: '/c/adyusuf/3a60fbd765af/', version: '3a60fbd765af' }] },
  })
  expect(installPathOf(record, ID)).toBe('/c/adyusuf/3a60fbd765af')
})

test('a single object entry and several entries are both read, the first with a path wins', () => {
  expect(installPathOf(JSON.stringify({ plugins: { [ID]: { installPath: '/one' } } }), ID)).toBe('/one')
  expect(installPathOf(JSON.stringify({ plugins: { [ID]: [{ scope: 'x' }, { installPath: '/two' }, { installPath: '/three' }] } }), ID)).toBe('/two')
})

test('no record, no entry, no path or unreadable text name nothing', () => {
  for (const text of ['', 'not json', '{}', JSON.stringify({ plugins: {} }), JSON.stringify({ plugins: { [ID]: [] } }),
    JSON.stringify({ plugins: { [ID]: [{ installPath: 7 }] } })]) {
    expect(installPathOf(text, ID)).toBe('')
  }
  expect(installPathOf(JSON.stringify({ plugins: { other: [{ installPath: '/x' }] } }), ID)).toBe('')
})

test('ticking an agent that the mode lacks adds it, clearing one it has removes it, anything else is auto', () => {
  expect(enabledFor(true, false)).toBe('on')
  expect(enabledFor(false, true)).toBe('off')
  expect(enabledFor(true, true)).toBe('auto')
  expect(enabledFor(false, false)).toBe('auto')
})

test('yes/no settings compare as booleans and the others as text', () => {
  expect(isWanted(true, 'yes')).toBe(true)
  expect(isWanted(true, 'no')).toBe(false)
  expect(isWanted(false, 'no')).toBe(true)
  expect(isWanted('B', 'B')).toBe(true)
  expect(isWanted('B', 'C')).toBe(false)
})

test('a click that a higher layer overrides says which layer wins', () => {
  expect(overrideNote('mode', 'C', 'C', 'user')).toBe('')
  expect(overrideNote('mode', 'C', 'B', 'project')).toBe("mode stays B: the project layer sets it, and it wins over the user's file")
  expect(overrideNote('push.prod', 'no', true, undefined)).toContain('another layer')
  expect(overrideNote('push.prod', 'no', true, 'default')).toContain('another layer')
})

test('every Gate-Waived line is listed with the commit it came from', () => {
  const log = '@@abc1234\nmerge\n\nGate-Waived: unit, e2e (neden: configuration)\n@@def5678\nplain commit\n@@0a0a0a0\nGate-Waived: unit (neden: x)\n'
  expect(waivedLines(log)).toEqual(['abc1234 unit, e2e (neden: configuration)', '0a0a0a0 unit (neden: x)'])
  expect(waivedLines('')).toEqual([])
})

test('the script folder is the recorded one, else the newest copy that is not marked as replaced', () => {
  const record = JSON.stringify({ plugins: { [ID]: [{ installPath: '/c/3a60' }] } })
  const cache = 'orphaned /c/49eb/\nlive /c/3a60/\nlive /c/0000/\n'
  expect(scriptDir(record, ID, cache)).toBe('/c/3a60')
  expect(scriptDir('', ID, cache)).toBe('/c/3a60')
  expect(scriptDir('not json', ID, 'orphaned /c/49eb/\n')).toBe('')
  expect(newestLiveDir('live /c/with space/\n')).toBe('/c/with space')
  expect(newestLiveDir('')).toBe('')
  expect(newestLiveDir('garbage\nlive\n')).toBe('')
})

test('the Settings box shows the groups in schema order and leaves the agents to their own box', () => {
  const schema = [
    { key: 'mode', group: 'Session' },
    { key: 'agents.qa.model', group: 'Agents' },
    { key: 'pod.connect', group: 'Pod' },
    { key: 'mode_model', group: 'Session' },
  ]
  const { groups, shown } = settingGroups(schema)
  expect(groups).toEqual(['Session', 'Pod'])
  expect(shown.map(spec => spec.key)).toEqual(['mode', 'pod.connect', 'mode_model'])
})

test('a promotion stage exists when its origin branch does, and reads the range from the stage before it', () => {
  const have = refSet('dev\norigin/dev\norigin/test\ntest\norigin/prod\n')
  const stages = plannedStages(have)
  expect(stages).toEqual([
    { branch: 'dev', previous: '', local: true },
    { branch: 'test', previous: 'dev', local: true },
    { branch: 'prod', previous: 'test', local: false },
  ])
  expect(waivedRange(stages[0])).toBe('')
  expect(waivedRange(stages[2])).toBe('origin/prod..origin/test')
  expect(plannedStages(refSet('origin/prod\norigin/dev\n'))).toEqual([
    { branch: 'dev', previous: '', local: false },
    { branch: 'prod', previous: '', local: false },
  ])
  expect(plannedStages(refSet('main\n'))).toEqual([])
})

test('git output is read as counts and ref sets', () => {
  expect(countOf('3\n')).toBe(3)
  expect(countOf('')).toBe(0)
  expect(countOf('x')).toBe(0)
  expect(refSet(' a \n\nb\n').size).toBe(2)
})
