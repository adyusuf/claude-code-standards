# Mobile standards (React Native / Expo)

## 1. Core principle: one API, two clients

- Mobile and web consume the **same** endpoints. No platform-specific API such as `/api/mobile/*` is created.
- Differences are resolved in the UI/UX layer: mobile may show fewer fields or order them differently; **the data contract is identical**.
- A mobile client can stay stuck on an old version in the store → **API backward compatibility is vital on mobile**. See `08-backward-compatibility.md`.
- Shared logic (date formatting, search normalization, authorization helpers, i18n keys) must have **the same behaviour** as on web; in a shared package where possible.

## 2. Structure and configuration

```
src/
  api/client.ts   → THE single source: BASE_URL, SIGNALR_URL, WEB_URL, timeout, interceptors
  screens/        → screens
  components/     → shared components
  navigation/     → navigator definitions
  hooks/ lib/ i18n/
```

- Hard-coded URL/IP/port is **forbidden** — it belongs in `api/client.ts`. Fallbacks are DEV-only and defined in one place.
- Environments are separated with `app.config.ts` + EAS profiles (`development` / `preview` / `production`).
- Secrets are never embedded in the bundle — a mobile bundle **can be opened**; there is no real secret on the client side.

## 3. Navigation

- Type-safe navigation (a typed param list). Route names are never written as free-form strings.
- A **deep link / universal link** is defined for every main screen and matches the web URL.
- The back gesture (and the Android hardware button) behaves as expected on every screen; in a modal it closes the modal.
- Prefer a tab + stack combination over a deep stack; the user must be able to reach the main screen in three taps.

## 4. Lists and performance

- A long list uses `FlatList`/`FlashList` — `map` inside a `ScrollView` is **forbidden**.
- `keyExtractor` uses a stable id; the row component is `memo`ised and pure.
- `getItemLayout` is provided where possible; `initialNumToRender` is tuned.
- Images are sized and cached (`expo-image`).
- Heavy work never blocks the JS thread; animations run on the UI thread through Reanimated.
- Start-up time is measured; no unnecessary synchronous work happens behind the splash screen.

## 5. Network and offline

- Every request has a timeout and can be cancelled.
- With no connectivity: a clear "you are offline" state plus a retry. An infinite spinner is forbidden.
- Cache-first with background refresh for critical lists.
- If writes are to be queued while offline, they are sent with an **idempotency key** (`07-api-design.md`).
- Token refresh lives in one place (an interceptor), and concurrent 401s trigger a single refresh (a mutex).

## 6. Storage

- Tokens and sensitive data → `expo-secure-store` (Keychain/Keystore). A token is never written to `AsyncStorage`.
- `AsyncStorage` is for non-sensitive preferences and cache only.
- On logout, all local data is cleared.

## 7. Permissions and platform differences

- A permission is requested **at the moment it is used**, with its reason explained (never all permissions at start-up).
- If a permission is denied the app keeps working (an explanatory state, not a broken screen).
- iOS/Android differences (`Platform.select`) are collected in one place, not scattered across screens.
- Safe areas are accounted for on every screen; no content sits under the notch or the gesture bar.
- When the keyboard opens the input stays visible (`KeyboardAvoidingView` / `keyboardVerticalOffset`).

## 8. Accessibility

- `accessibilityLabel` + `accessibilityRole` on every interactive element.
- A touch target is at least 44×44.
- The layout survives dynamic font sizing (the user's setting) — no fixed-height text boxes.

## 9. Versioning and release

- Versioning: `version` (what the user sees) + `buildNumber`/`versionCode` (incremented on every upload).
- The pre-release checklist:
  - [ ] Version/build number incremented
  - [ ] The changes work with the old API (users on the previous version are not broken)
  - [ ] Crash reporting enabled and tagged with the new version
  - [ ] Store copy and screenshots current
  - [ ] Permission description strings (`NSCameraUsageDescription` and friends) correct
  - [ ] Privacy/data-collection declarations (App Privacy / Data Safety) correct
  - [ ] The Maestro e2e smoke suite passed (`12-maestro.md`)
- Build format: **AAB** (Android) / **IPA** (iOS) for store upload; an APK for device installation is a separate request.
- Heavy builds run **sequentially** (parallel Gradle/Kotlin compilation risks OOM).
- OTA updates (EAS Update) are for JS-only changes; a native change requires a store release. The OTA channel is matched to the store version.

## 10. Forced-update strategy

- The API must be able to report the minimum supported client version (a header or a `/config` endpoint).
- On an unsupported version the app shows an "update required" screen — it never fails silently.
- This mechanism is **not a licence to make breaking changes**: additive evolution still applies.

## 11. Never-do list

- ❌ Creating a platform-specific API endpoint
- ❌ A long list built from `ScrollView` + `map`
- ❌ Keeping a token in `AsyncStorage` or in the bundle
- ❌ Laying out a screen in fixed pixels (device diversity)
- ❌ Requesting every permission at start-up
- ❌ Adding a native module without approval (leaving Expo managed requires an ADR)
