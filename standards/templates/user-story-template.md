# US-<000>: <Short title>

## Story

As a **<role>**, I want **<capability>**, so that **<benefit>**.

## Context

<Why now? Which real situation does it solve? The current pain point, if any.>

## Scope

**In:**
- <...>

**NOT in this release:** (a list left unwritten turns into scope creep later)
- <...>

## Acceptance criteria

### 1. Happy path
```
Given  <initial state>
When   <user action>
Then   <observable result>
And    <additional result>
```

### 2. Empty state
```
Given  there are no records
When   the user opens the page
Then   a "No <thing> yet" message and an "<Add>" button are shown
```

### 3. Error state
```
Given  the API returns 500
When   the user loads the list
Then   an error message and a "Try again" button are shown, and the page does not crash
```

### 4. Authorization
```
Given  the user does not have the <permission> permission
When   <action> is attempted
Then   403 is returned AND the action is not offered in the UI (both)
```

### 5. Edge cases
- Very long text / 1000+ records / special characters / concurrent edits
- Search with accented characters (case- and accent-insensitive)

## Technical notes

- **API:** <new/changed endpoint — is it additive?>
- **DB:** <new field — is it nullable?>
- **Web/mobile parity:** <the same, or if they differ, why>
- **i18n:** <new keys>

## Definition of Done

- [ ] Every acceptance criterion is met
- [ ] Unit tests written, plus e2e where needed
- [ ] The API is backward compatible and Swagger is current
- [ ] Accessibility checked
- [ ] i18n keys added (the default locale is mandatory)
- [ ] Logging/metrics added (if this is a critical flow)
- [ ] Documentation and CLAUDE.md updated
