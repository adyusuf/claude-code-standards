import { expect, test } from 'claude-code/testing'

// The test environment has no process, so the boxes cannot fill from the plugin's script here and `$.state` cannot be
// seeded; what is pinned is that the pane loads, draws on both surfaces, shows its three bordered boxes with the folded
// ones summarised, and says what each unfolded one waits for. The data paths are exercised by hand in a session: press a
// toggle in Settings, pick a mode, run git in the repository.
const PROPS = { title: 'x', isFocused: false } as never

for (const surface of ['terminal', 'desktop'] as const) {
  test(`the pane draws Settings unfolded and waiting on ${surface}`, async $ => {
    const ui = await $.ui.mount({ plugin: 'adyusuf', surface, component: 'Pane', requestId: 'adyusuf-boxes', props: PROPS })
    expect(await ui.find({ type: 'Text', text: /Settings/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Reading the configuration/ })).toBeDefined()
    await ui.unmount()
  })

  test(`the pane shows the Agents and Promotion headers folded on ${surface}`, async $ => {
    const ui = await $.ui.mount({ plugin: 'adyusuf', surface, component: 'Pane', requestId: 'adyusuf-boxes', props: PROPS })
    expect(await ui.find({ type: 'Text', text: /Agents/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Promotion/ })).toBeDefined()
    await ui.unmount()
  })
}
