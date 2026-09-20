# Commits, PRs and code review

## 1. Branches

```
<type>/<short-description>     feat/member-process-status
                               fix/order-total-rounding
                               chore/upgrade-efcore
                               docs/api-contract
```

- English, kebab-case, short. A person's name or a ticket number alone is not a branch name.
- A branch is cut **from the integration branch** (`dev`) and returns there. No branch is cut directly from `test`/`prod`.
- No long-lived branches — a branch older than two or three days is either split or frequently rebased/merged from `dev`.

## 2. Commits

```
<type>(<scope>): <summary, imperative mood, under 72 characters>

The body: why this change was needed, and which alternative was ruled out.
If it is breaking: BREAKING CHANGE: <explanation>
```

Types: `feat` `fix` `refactor` `perf` `test` `docs` `chore` `build` `ci` `revert`

- **Atomic commits:** a commit compiles and covers exactly one subject. "wip", "fix", "final" are forbidden.
- A formatting or rename commit is committed **separately** from a logical change (so the diff stays readable).
- Generated files, `node_modules` and build output are never committed.
- **Commit only your own diff.** Never use `git add -A` blindly; a parallel session may grab someone else's file.

## 3. PR size and contents

- Target: **under 400 changed lines**. If it is bigger, split it — review quality collapses on a large PR.
- **One PR = one subject.** A refactor, a feature and a reformat never share a PR.
- The PR description (`templates/pr-template.md`):
  - What / why
  - How it was tested (the command plus its result)
  - A screenshot (if the UI changed, before/after)
  - Backward-compatibility impact (**a required field**: "none" is a valid answer, but it is written down)
  - Whether there is a migration / an env change / a new secret
  - How to roll it back

## 4. The merge gate (automatic — no merge without passing it)

> **Scope (global rule #25):** the full gate below is for the **`dev → test` and
> `test → prod` promotions**. On a **`feature/* → dev` merge** only **build + fast
> unit tests** run; review, secret/SAST/CVE scanning, backward-compatibility
> scanning, e2e and the coverage threshold **do not run**. **The formatter/linter
> also runs once at the END of the task list**, not on every merge (global
> #25/#26). `dev` publishes nothing outward; the gate belongs at the promotion.

- [ ] Build (backend + web + mobile)
- [ ] Unit tests green
- [ ] **Line coverage ≥ 80% in every codebase** — with an honest denominator; an unmeasured codebase blocks (global #29, `10-test-strategy.md` §7)
- [ ] `tsc --noEmit`, ESLint, `dotnet format --verify-no-changes`
- [ ] Backward-compatibility scan (`08-backward-compatibility.md` §7)
- [ ] The secret scanner (gitleaks or similar) is clean
- [ ] The dependency security scan has no critical finding
- [ ] If there is a migration, its reversibility is stated

The gate is **never bypassed**. Loosening a test to get through it is forbidden.

## 5. Review checklist (for the reviewer)

**Correctness**
- [ ] Does it genuinely meet the acceptance criteria?
- [ ] Edge cases: empty, one, many, null, long text, negative, concurrent
- [ ] Are the error paths handled? Is any exception swallowed silently?

**Contract / compatibility**
- [ ] Was a field deleted, renamed or retyped?
- [ ] Is there a new required input field?
- [ ] Did enum ordering break? Did a global serializer setting change?
- [ ] Does the older mobile version still work with this change?

**Security**
- [ ] Is every endpoint authorized? Is resource ownership (IDOR) checked?
- [ ] Is input validated? Is raw SQL parameterized?
- [ ] Does a secret or PII leak into a log or a response?

**Data**
- [ ] Any N+1? Is there pagination? Is an index needed?
- [ ] Is the transaction boundary right? Is there an external call inside it?
- [ ] Is the migration reversible? Does it contain a `DROP`?

**Readability**
- [ ] Do the names convey intent? The 300-line rule?
- [ ] Any dead code, commented-out code, or an ownerless TODO?
- [ ] Any hard-coded URL/port/key?

**Tests & documentation**
- [ ] Is there a test for the behaviour change? Was a test loosened?
- [ ] Are Swagger/OpenAPI, CLAUDE.md and the related documents current?

## 6. Finding severity levels

| Level | Meaning | Consequence |
|---|---|---|
| **Blocking** | Data loss, a security hole, a breaking change, wrong business logic | Not merged |
| **Important** | A performance problem, a missing test, a missing error path, a contract risk | Fixed in this PR |
| **Suggestion** | Naming, structure, readability | The author's call |
| **Note** | Sharing information | No action |

When writing a comment: **what** is wrong + **why** it matters + **a suggestion**.
"This is bad" is not a review. A suggestion-level comment does not block the merge.

## 7. The author's responsibility

- **Read your own diff** before opening the PR. Do not make the reviewer find what you could see yourself.
- Answer every comment (fixed / not fixing, for this reason). No silent resolutions.
- If you made a large change after review, ask for review again.

## 8. Merge strategy

- Into `dev`: **squash merge** (a clean history) or rebase — one style within a project.
- `dev → test → prod`: a **promotion**, fast-forward/merge. Never a merge in the reverse direction.
- **No** direct commit or PR to `test` and `prod` — only from the previous stage, with the user's approval.
- Before merging, `git fetch` and update if you are behind — a gate running against stale code gives false confidence.
- A `--force` push happens only on your own feature branch and only with explicit approval.

## 9. Claude's role in review

- **If the target branch is `dev`, no review happens** (global rule #25): the diff is not read, no agent is invoked, no scan runs — if build + fast tests + lint are green, it is merged. If something catches the eye along the way, it is noted in one line without blocking the merge.
  - ⚠️ **One exception (`modes/role-selection.md` §3):** if the change weakens **backups, secret management or a security gate itself** (`continue-on-error`, disabling a gate, switching off gitleaks, breaking backup/restore) then `qa` runs in the `dev` direction too and the reason is recorded. #25 buys speed, not an irreversible loss.
- If the "merge" command **targets `test` or `prod`**: **the diff is reviewed first**; if there is a **blocking** finding, STOP and report it.
- The "review done" flag is never given to the merge gate without a review having happened.
- What automatic scanning cannot catch (a change of meaning, enum drift, tightened authorization) is checked **by hand**.
