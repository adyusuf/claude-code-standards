import { expect, test } from 'claude-code/testing'

// The test environment has no process, so the boxes cannot fill from the plugin's script here and `$.state` cannot be
// seeded; what is pinned is that each box loads, draws on both surfaces and says what it waits for. The data paths are
// exercised by hand in a session: press a toggle in Settings, pick a mode, run git in the repository.
const PROPS = { title: 'x', isFocused: false } as never
const BOXES = [
  { id: 'adyusuf-settings', waits: /Reading the configuration/ },
  { id: 'adyusuf-agents', waits: /Reading the configuration/ },
  { id: 'adyusuf-promotion', waits: /Reading the branches/ },
] as const

for (const surface of ['terminal', 'desktop'] as const) {
  for (const box of BOXES) {
    test(`${box.id} draws its waiting state on ${surface}`, async $ => {
      const ui = await $.ui.mount({ plugin: 'adyusuf', surface, component: 'Pane', requestId: box.id, props: PROPS })
      expect(await ui.find({ type: 'Text', text: box.waits })).toBeDefined()
      await ui.unmount()
    })
  }
}
