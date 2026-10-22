import { expect, test } from 'claude-code/testing'

import { enabledFor, installPathOf, isWanted, overrideNote, waivedLines } from './choose'

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
