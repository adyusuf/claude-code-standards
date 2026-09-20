## What / Why

<One paragraph: which problem, and why this solution. Link to the ticket/issue.>

## Changes

- <file/module> — <what changed>
- ...

## How it was tested

```bash
# the commands that were run, and their results
dotnet test        # 142 passed
npm run test       # 87 passed
npm run e2e        # 18 passed
```

- [ ] Happy path exercised
- [ ] Error path exercised (<which one>)
- [ ] Unauthorized access exercised

## Screenshot (if the UI changed)

| Before | After |
|---|---|
| | |

## Backward-compatibility impact — **a required field**

- [ ] No field/endpoint was **deleted**, and no name or type **changed**
- [ ] Any new input field is **optional**
- [ ] Any new database column is **nullable**
- [ ] Validation was **not tightened** (no new `Required`/`UNIQUE`/narrowed `MaxLength`)
- [ ] Enum numeric ordering preserved
- [ ] The global serializer / routes / hub payload did not change
- [ ] **The older mobile version still works with this change**

If there is an impact, explain it: <...>

## Database / migration

- [ ] No migration
- [ ] There is a migration → is it reversible: <yes/no, how>
- [ ] Does it contain a `DROP`: <no / yes → a backup was taken and it was rehearsed in the test environment>

## Configuration / secrets

- [ ] No new env variable
- [ ] There is one → `.env.example` **and** the `SETUP.md` secret inventory were updated

## Security

- [ ] Any new endpoint is authorized (including resource ownership)
- [ ] Input is validated
- [ ] No PII/tokens leak into the logs

## Rollback

<If this change causes a problem, how is it rolled back? Is there a feature flag?>

## Documentation

- [ ] Swagger/OpenAPI is current
- [ ] `CLAUDE.md` / `docs/` are current
- [ ] Any new permanent rule was written into the relevant markdown file
