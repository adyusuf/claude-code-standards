import { expect, test } from 'claude-code/testing'

import { changesBetween, operationWarnings, RULES, rulesFor, warning, warnings } from './notices'
import type { View } from './notices'

const SCHEMA = [
  { key: 'push.prod', label: 'Push prod' },
  { key: 'pod.connect', label: 'Connect to pod' },
  { key: 'mode', label: 'Working mode' },
]
const view = (values: Record<string, boolean | string>, saved?: Record<string, boolean | string>): View =>
  ({ schema: SCHEMA, values, saved: saved ? { values: saved } : undefined })

test('a setting names the rules it steers, and a setting no rule reads names none', () => {
  expect(rulesFor('mode')).toEqual(['#27', '#28'])
  expect(rulesFor('agents.qa.model')).toEqual(['#27', '#28'])
  expect(rulesFor('write.unit_tests')).toEqual(['#8', '#32', '#29'])
  expect(rulesFor('write.e2e')).toEqual(['#33', '#31'])
  expect(rulesFor('merge.test')).toEqual(['#34', '#26'])
  expect(rulesFor('push.prod')).toEqual(['#34', '#26'])
  expect(rulesFor('gates_before_push.dev')).toEqual(['#34', '#25', '#29'])
  expect(rulesFor('coverage_before_push.test')).toEqual(['#34', '#29'])
  expect(rulesFor('ci_after_push.prod')).toEqual(['#34', '#19'])
  expect(rulesFor('e2e_before_deploy.test')).toEqual(['#33', '#34', '#31'])
  expect(rulesFor('mode_model')).toEqual(['#27'])
  expect(rulesFor('pod.connect')).toEqual([])
  expect(rulesFor('something.new')).toEqual([])
})

test('every rule a setting points at has its few words', () => {
  for (const key of ['mode', 'mode_model', 'agents.x.model', 'write.unit_tests', 'write.e2e', 'merge.dev', 'push.dev', 'gates_before_push.dev', 'coverage_before_push.dev', 'ci_after_push.dev', 'e2e_before_deploy.test']) {
    for (const rule of rulesFor(key)) expect(RULES[rule] === undefined).toBe(false)
  }
})

test('changes are the keys whose value differs, and there are none without an earlier read', () => {
  expect(changesBetween(null, view({ mode: 'C' }))).toEqual([])
  expect(changesBetween(undefined, view({ mode: 'C' }))).toEqual([])
  expect(changesBetween(view({ mode: 'B', 'push.prod': true }), view({ mode: 'C', 'push.prod': true }))).toEqual([{ key: 'mode', from: 'B', to: 'C' }])
  expect(changesBetween(view({}), view({ mode: 'C' }))).toEqual([{ key: 'mode', from: undefined, to: 'C' }])
})

test('a warning says the scope, the setting, old and new value, and the rules in play', () => {
  expect(warning({ key: 'push.prod', from: false, to: true }, 'this session', SCHEMA)).toBe(
    '⚠ adyusuf setting changed (this session): Push prod (push.prod) no → yes. Rules in play: #34 merges, pushes and gates follow the configuration, not questions; #26 work off dev, one commit per task, merged through a gate.')
  expect(warning({ key: 'pod.connect', from: true, to: false }, 'saved defaults', SCHEMA)).toBe(
    '⚠ adyusuf setting changed (saved defaults): Connect to pod (pod.connect) yes → no. No rule reads this setting.')
  expect(warning({ key: 'unknown.key', from: undefined, to: 'x' }, 'this session', SCHEMA)).toBe(
    '⚠ adyusuf setting changed (this session): unknown.key (unknown.key) unset → x. No rule reads this setting.')
})

test('nothing is said on the first read or when nothing changed', () => {
  expect(warnings(null, view({ mode: 'C' }))).toEqual([])
  expect(warnings(view({ mode: 'C' }, { mode: 'C' }), view({ mode: 'C' }, { mode: 'C' }))).toEqual([])
})

test('a session change is said as a session change, a saved change as a saved change', () => {
  const lines = warnings(view({ mode: 'C', 'push.prod': true }, { mode: 'C' }), view({ mode: 'B', 'push.prod': true }, { mode: 'C' }))
  expect(lines.length).toBe(1)
  expect(lines[0].startsWith('⚠ adyusuf setting changed (this session): Working mode (mode) C → B.')).toBe(true)
  const saved = warnings(view({ mode: 'B' }, { mode: 'C' }), view({ mode: 'B' }, { mode: 'A' }))
  expect(saved.length).toBe(1)
  expect(saved[0].startsWith('⚠ adyusuf setting changed (saved defaults): Working mode (mode) C → A.')).toBe(true)
})

test('a saved default that moved the session value too is said once, as the saved change', () => {
  const lines = warnings(view({ mode: 'C' }, { mode: 'C' }), view({ mode: 'A' }, { mode: 'A' }))
  expect(lines.length).toBe(1)
  expect(lines[0].includes('(saved defaults)')).toBe(true)
})

test('before the saved defaults are read only the session is compared', () => {
  const lines = warnings(view({ mode: 'C' }), view({ mode: 'B' }))
  expect(lines.length).toBe(1)
  expect(lines[0].includes('(this session)')).toBe(true)
})

test('a git push names its stage, a forced one says so, and the rules in play follow', () => {
  const lines = operationWarnings('git -C /repo push --force origin dev:prod')
  expect(lines.length).toBe(1)
  expect(lines[0]).toBe('⚠ adyusuf operation: git push (FORCED, prod). Rules in play: #34 merges, pushes and gates follow the configuration, not questions; #26 work off dev, one commit per task, merged through a gate. A force push is on the never-do list.')
  expect(operationWarnings('git push origin test')[0].includes('(test)')).toBe(true)
})

test('a git merge is a merge, and merge-base or status are not operations', () => {
  const lines = operationWarnings('git fetch && git merge --no-ff origin/dev')
  expect(lines.length).toBe(1)
  expect(lines[0].startsWith('⚠ adyusuf operation: git merge (dev). Rules in play: #26')).toBe(true)
  expect(operationWarnings('git merge-base HEAD dev')).toEqual([])
  expect(operationWarnings('git status; git log --oneline')).toEqual([])
  expect(operationWarnings('git -c core.x=1 -C repo status')).toEqual([])
  expect(operationWarnings('')).toEqual([])
})

test('a gate or scan script run names the gate rules, once however often it appears', () => {
  const lines = operationWarnings('bash scripts/gate-core.sh dev && bash scripts/coverage.sh; gitleaks detect')
  expect(lines.length).toBe(1)
  expect(lines[0].startsWith('⚠ adyusuf operation: gate / scan run. Rules in play: #25')).toBe(true)
  expect(lines[0].includes('#29')).toBe(true)
  expect(operationWarnings('cat scripts/coverage.sh')).toEqual([])
  expect(operationWarnings('grep -n x scripts/gate-core.sh; ls scripts/merge-gate.sh')).toEqual([])
  expect(operationWarnings('GATE_RUN_E2E=1 bash -x scripts/merge-gate.sh test').length).toBe(1)
  expect(operationWarnings('./scripts/gate-core.sh dev --list').length).toBe(1)
  for (const wrapped of ['timeout 600 bash scripts/merge-gate.sh dev', 'env X=1 bash scripts/coverage.sh', 'nohup gitleaks detect', 'time bash scripts/gate-core.sh dev']) {
    expect(operationWarnings(wrapped).length).toBe(1)
  }
})

test('a merge and a push in one command are two warnings, in the order they appear', () => {
  const lines = operationWarnings('git merge dev | cat; git push -f origin prod')
  expect(lines.length).toBe(2)
  expect(lines[0].startsWith('⚠ adyusuf operation: git merge (dev). Rules in play: #26')).toBe(true)
  expect(lines[1].startsWith('⚠ adyusuf operation: git push (FORCED, prod). Rules in play: #34')).toBe(true)
})
