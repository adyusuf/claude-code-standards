# UI / UX Design Standards

## 1. Design tokens — one source

Colour, typography, spacing, radius, shadow, z-index and breakpoints are defined in
**one file** (CSS variables / a theme object). A component never contains a raw
`#3b82f6`, `13px` or `margin: 7px`.

- Spacing scale: 4px-based (4, 8, 12, 16, 24, 32, 48, 64). Intermediate values are not
  invented.
- Typography scale: at most 6 steps. Every step has a defined line height.
- Colours are named by **role** (`--color-danger`), not by shade (`--color-red-500`
  exists only in the palette layer).
- z-index values are only chosen from the defined layers (base / dropdown / sticky /
  modal / toast).

## 2. Component discipline

- A component does **one job**. A component over 300 lines gets split (modal, row
  renderer, form, filter bar).
- Presentational and data (container) responsibilities are separated: a component that
  fetches data does not also manage the JSX tree.
- If the prop count exceeds 7, either group them into an object or split the component.
- A shared component (`Button`, `Input`, `Modal`, `Table`, `EmptyState`) is written
  **once**; it is never reinvented inside a page.
- Variants come from props (`variant="danger"`), not from a copy-pasted component.

## 3. Every screen designs 5 states

| State | Requirement |
|---|---|
| **Loading** | A skeleton or spinner; no layout jump (the placeholder has the same dimensions) |
| **Empty** | Explanatory text + the primary action ("No records yet — add the first one") |
| **Error** | What happened in human language + what to do + a retry button. No stack traces |
| **Partial/long** | Very long text, too many records, a very long name → overflow handling, `text-overflow` |
| **Success** | Feedback (toast/inline). No silent success |

A missing state design is a missing feature.

## 4. Form rules

- The label is always visible (a `placeholder` is not a label).
- Validation runs **on blur or on submit**, not on every keystroke; it clears
  immediately as the error is corrected.
- The error message sits **directly below the field** and says what to do ("Phone must
  be 10 digits", not "Invalid").
- During submit the button is disabled with a loading indicator → double submission is
  prevented.
- A warning on leaving the page with unsaved changes.
- The required-field marker is consistent; optional fields may be marked explicitly too.
- The form must be completable end to end with the keyboard (a sensible tab order).

## 5. Navigation and URLs

- Application state **lives in the URL**: tab, filter, page number and search term go in
  query params. They survive a reload.
- The back button behaves as expected. Opening a modal does not pollute history (or it
  does so deliberately and the back button closes the modal).
- Deep linking must be possible to every screen (on mobile too — `06-mobile.md`).
- Entering an unauthorized page shows a 403 screen; not a blank page or an endless
  spinner.

## 6. Responsive

- Written mobile-first. Few breakpoints (sm/md/lg/xl), taken from tokens.
- Touch targets at least 44×44px. Nothing depends on hover alone (there is no hover on
  mobile).
- On a narrow screen a table either scrolls horizontally (inside its own container) or
  turns into a card list. **The page body never scrolls horizontally.**
- Images use `max-width: 100%`; no fixed pixel widths.

## 7. Accessibility (WCAG 2.1 AA — the minimum)

- [ ] Semantic HTML: a `button` is clickable, not a `div onClick`. The heading hierarchy
      is not skipped (h1→h2→h3).
- [ ] Every form field has a `label` (a matching `htmlFor`/`id`).
- [ ] Contrast: 4.5:1 for normal text, 3:1 for large text, 3:1 for icons and borders.
- [ ] Every function is reachable by keyboard; the focus indicator is visible
      (`outline: none` on its own is forbidden).
- [ ] When a modal opens, focus is trapped inside and returns to the trigger on close;
      `Esc` closes it.
- [ ] Information is never conveyed by colour alone (an error = red + icon + text).
- [ ] Meaningful `alt` on images; `alt=""` if decorative.
- [ ] Dynamic content changes are announced with `aria-live` (toasts, the result count).
- [ ] `prefers-reduced-motion` is respected.

## 8. Text and i18n

- No user-facing string is embedded in code → an i18n key. The primary locale is the
  default, with a secondary one alongside it.
- Keys are named by area: `members.list.emptyTitle`.
- Plurals, dates, numbers and currency formatting are left to the library — never
  concatenated by hand.
- Tone: short, direct, not accusatory. Instead of "An error occurred", use "Could not
  save — check your connection and try again".
- Dates are displayed as **`dd/mm/yyyy`** (a global rule). Time uses the 24-hour format.

## 9. Motion

- Duration 150–300ms; entry slightly slower than exit.
- Animate only `transform` and `opacity` (never a property that triggers layout).
- Animation carries information (where it came from, where it went); it is not added for
  decoration.

## 10. Dark mode

- Colours come through tokens; `@media (prefers-color-scheme)` plus a user-preference
  override.
- Fixed white/black values are never embedded. Images and shadows are checked separately
  in dark mode.

## 11. The design review question

When a screen is finished, ask: *"Would someone seeing this screen for the first time
understand what to do within 5 seconds?"*
If not, revisit the hierarchy (one clear primary action), the spacing and the text.
