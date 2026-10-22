// Stands in for the engine's 'claude-code/testing' when the mod's engine-free logic is measured with Deno
// (scripts/coverage.sh): the same `test` and `expect(...).toBe/.toEqual/.toContain` the mod's tests use, nothing more.
import assert from 'node:assert/strict'

export const test = (name: string, body: () => void | Promise<void>) => Deno.test(name, body)

export const expect = (actual: unknown) => ({
  toBe: (wanted: unknown) => assert.strictEqual(actual, wanted),
  toEqual: (wanted: unknown) => assert.deepStrictEqual(actual, wanted),
  toContain: (part: string) => assert.ok(String(actual).includes(part), `${String(actual)} does not contain ${part}`),
})
