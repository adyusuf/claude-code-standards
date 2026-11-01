// The drawing parts every box of the adyusuf pane shares: the element table, the radio and checkbox icons, one pressable
// option, one aligned line. Engine-free like boxes.ts, which they were split out of so no file passes 300 lines (rule #9).

export type Factory = (type: unknown, props: Record<string, unknown> | null, ...children: unknown[]) => unknown
/** `Svg` is in the element table only where the surface draws it (desktop, not the terminal). */
export type Ui = { h: Factory; Box: unknown; Text: unknown; Button: unknown; Svg?: unknown }

/** One indentation step, in cells: the width of a box header's `▾ `. */
export const INDENT = 2
/** A warning (a waived gate, an unreadable settings file): orange as hex, which the terminal and the desktop both draw. */
export const WARN = '#E07B00'
const ICON_ON = '#378ADD'
const ICON_OFF = '#888780'
// Exactly the shape's size: an empty margin inside the image read as a space after the icon (user decision 01/11/2026).
const svg = (body: string) => `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">${body}</svg>`
const ICONS = {
  radio: {
    on: svg(`<circle cx="6" cy="6" r="5" fill="none" stroke="${ICON_ON}" stroke-width="1.2"/><circle cx="6" cy="6" r="2.5" fill="${ICON_ON}"/>`),
    off: svg(`<circle cx="6" cy="6" r="5" fill="none" stroke="${ICON_OFF}" stroke-width="1.2"/>`),
  },
  check: {
    on: svg(`<rect x="1" y="1" width="10" height="10" rx="2" fill="none" stroke="${ICON_ON}" stroke-width="1.2"/><path d="M3.5 6.2l2 2 3.8-4.2" fill="none" stroke="${ICON_ON}" stroke-width="1.5"/>`),
    off: svg(`<rect x="1" y="1" width="10" height="10" rx="2" fill="none" stroke="${ICON_OFF}" stroke-width="1.2"/>`),
  },
}
type Kind = keyof typeof ICONS

/**
 * One line: its head (a label, a role) in a column of `width` cells, then one column of parts per layer, side by side.
 * Every column but the last is `columnWidth` cells at least, so the next one starts at the same place on every line.
 */
export function line(ui: Ui, head: unknown, columns: unknown[], width: number, columnWidth = 0) {
  const { h } = ui
  return h(ui.Box, { flexDirection: 'row', columnGap: 1 },
    h(ui.Box, { minWidth: width, flexShrink: 0 }, head),
    columns.map((parts, at) => h(ui.Box, {
      flexDirection: 'row', flexWrap: 'wrap', columnGap: 1, ...(at < columns.length - 1 ? { minWidth: columnWidth, flexShrink: 0 } : {}),
    }, parts)))
}

export const label = (ui: Ui, text: string) => (text === '' ? null : ui.h(ui.Text, { bold: true }, text))

/**
 * One pressable part. `chosen` fills its icon (desktop) or puts it in brackets (terminal) and draws it at full strength,
 * the rest dimmed. The icon sits beside the Button: a Button holds text only.
 */
export function option(ui: Ui, key: string, text: string, kind: Kind, chosen: boolean, onPress: () => void) {
  const { h } = ui
  const button = h(ui.Button, { key, plain: true, dimColor: !chosen, onPress }, ui.Svg || !chosen ? text : `[${text}]`)
  if (!ui.Svg) return button
  return h(ui.Box, { flexDirection: 'row', alignItems: 'center' },
    h(ui.Svg, { source: ICONS[kind][chosen ? 'on' : 'off'], alt: chosen ? `${text}, chosen` : text, width: 12, height: 12 }), button)
}

/** The cells one row's options take: each name with its brackets or icon, a gap between them. */
export const cells = (names: string[]) => names.reduce((sum, name) => sum + name.length + 2, 0) + Math.max(0, names.length - 1)

/** The hover group that ties a label to its card (the engine's `hover.scope`: 1 to 64 characters). */
const helpScope = (id: string) => `adyusuf-help-${id}`.slice(0, 64)

/** A label the pointer can rest on: while it does, the card of the same `id` shows (user decision 01/11/2026). */
export const hoverable = (ui: Ui, id: string, child: unknown) => ui.h(ui.Box, { hover: { scope: helpScope(id) } }, child)

/**
 * The card a label opens while the pointer rests on it: a hidden row drawn right after the label's line, so it opens in
 * place and pushes the rows below down. Nothing drawn later can cover it and no row needs counting, as a placed card
 * would. The card is in the label's hover group too, so the pointer may move onto it. The theme's text colour behind
 * the inverse text keeps it readable in either theme. No text, no card.
 */
export function helpCard(ui: Ui, id: string, text: string | undefined) {
  if (!text) return null
  return ui.h(ui.Box, { display: 'none', hover: { scope: helpScope(id), display: 'flex' }, paddingX: 1, backgroundColor: 'text' },
    ui.h(ui.Text, { color: 'inverseText' }, text))
}
