# Maestro — mobile e2e standards

## 1. Scope

Mobile e2e is **even more expensive** than web (an emulator, a build, device
differences). Only:

- Launch + login + the main flow (smoke): does the app open, does login work, does the main list load
- Critical business flows (placing an order, submitting a form, opening a notification)
- The core scenarios checked before a store release

Target: **5-15 flows**, a total run under 10 minutes. Do not e2e-test every screen.

## 2. Flow structure

```
.maestro/
  config.yaml
  flows/
    00-launch.yaml        → the app opens, the splash clears, nothing crashes
    01-login.yaml         → login
    02-members-list.yaml  → the list loads, the empty state, the error state
    03-create-order.yaml  → a critical flow
  subflows/
    login.yaml            → the pieces reused through runFlow
```

- Repeated steps are extracted into a subflow with `runFlow` (login, logout, seeding).
- Every flow starts **independently** (`launchApp: clearState: true`) — never rely on the state a previous flow left behind.
- A flow's name says what it tests; the numbering conveys reading order, not run order.

## 3. Selector policy

1. `id: "member-list-item"` → `testID` in React Native (**preferred**)
2. `text: "Save"` → breaks when i18n changes, so use it carefully
3. Coordinates / index → **a last resort**, fragile

The rules:
- Every interactive element gets a **stable `testID`**; on iOS together with `accessibilityLabel`.
- A `testID` is fixed, not generated (`member-row-${id}` is fine, `row-3` is not).
- Deleting a `testID` breaks e2e → when one changes, the flows are updated with it.

## 4. Waiting

- `assertVisible` already waits in Maestro — a manual `sleep` is **never used**.
- For long-running operations, wait **conditionally** with `waitForAnimationToEnd` or `extendedWaitUntil`.
- Every fixed `sleep` you see is a flaky test in waiting.

## 5. Data and environment

- Connect to the test environment; **never to production**. The base URL comes from the build profile (`preview`/`development`).
- Setup data is seeded through the API (with Maestro's `runScript`, or in a separate step beforehand).
- Use a unique user rather than a fixed test user, so parallel runs do not collide.
- Credentials are passed through `env`, never written into a flow file.

## 6. Device matrix

- Minimum: one Android (the lowest supported API level) + one iOS (the lowest supported version).
- Additionally: a small screen and a large screen (that is where layouts break most).
- Device differences are solved in the code, not in the test — do not scatter `if android` branches through a flow.

## 7. CI

- It does not run on every push — it needs a build. Triggers: a release candidate, a nightly run, or the `dev → test` promotion.
- Maestro Cloud or a self-hosted emulator; whichever it is, the **artifacts** (video + logs) are kept.
- Before a store release the smoke flows **must pass** (`06-mobile.md` §9 checklist).

## 8. Things to watch while writing

- Permission dialogs (location, notifications, camera) are handled explicitly in the flow — otherwise it hangs.
- Element visibility changes once the keyboard opens; `hideKeyboard` may be needed.
- The Android back button (`back`) differs from an iOS swipe — the flow must work on both.
- If the network is slow, the answer is a real wait condition, not a longer timeout.

## 9. Never-do list

- ❌ Waiting with `sleep`
- ❌ Tapping by coordinates (outside a genuine last resort)
- ❌ Running against production
- ❌ A username/password embedded in a flow
- ❌ Writing e2e for every screen (that belongs to unit/component tests)
- ❌ Changing a `testID` without telling anyone
