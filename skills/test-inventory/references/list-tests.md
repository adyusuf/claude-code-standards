# Listing tests per stack

Commands that print test names (and so counts) without running anything. Run them from
the repository root. zsh does not expand `--include=*.cs` unquoted — always quote the glob.

## Vitest / Jest / Playwright (TS)

```bash
grep -nE "^\s*(describe|it|test)(\.each\([^)]*\))?(\.(skip|only))?\(" <file> \
  | sed -E 's/^([0-9]+):\s*/\1: /' | cut -c1-160
```

`it.each` / `test.each` rows are one block here; the runner's own count
(`vitest run <file>` → "Tests N passed") is the authoritative number.

## xUnit / NUnit (C#)

```bash
awk '/\[(Fact|Theory|Test|TestCase)/{f=1;next}
     f && /\(/{match($0,/[A-Za-z0-9_]+\(/); n=substr($0,RSTART,RLENGTH-1);
     if(n!="InlineData" && n!="MemberData") print n; f=0}' <file>
```

Find the test files that exercise an endpoint:

```bash
grep -rlE '"/api/<route>"|<route>/\{' <tests-dir> --include='*.cs'
```

## JUnit / Robolectric (Kotlin)

```bash
grep -A1 "@Test" <file> | grep -oE 'fun `[^`]+`|fun [A-Za-z0-9_]+\(' | sed 's/fun //'
```

## XCTest (Swift)

```bash
grep -oE "func test[A-Za-z0-9_]+" <file> | sed 's/func //'
```

## Maestro (YAML flows)

Each flow file is one test; its purpose is in the leading comment block:

```bash
for f in <flows-dir>/*.yaml; do printf '%s  ' "$(basename "$f")"; grep -m1 '^#' "$f"; done
```

## Coverage per file (Vitest, v8)

```bash
npx vitest run --coverage --coverage.reporter=json-summary --coverage.reporter=json \
  --coverage.reportsDirectory="$SCRATCH/cov" > "$SCRATCH/cov.log" 2>&1
```

Read `coverage-summary.json` for per-file line percentages and `coverage-final.json`
(`statementMap` + `s` with count 0) for the uncovered line ranges. A narrowed
`--coverage.include` can make the global threshold fail with exit 1 while every test
passed — read the test summary line, not only the exit code.

## Finding a fake that hides failure paths

```bash
grep -rn "Success: true\|return true\|Result.success" <tests-dir>/**/Fake*
```

A shared fake that only ever succeeds means the failure branch of every caller is
untested — report it once, at the fake, and reference it from each screen.
