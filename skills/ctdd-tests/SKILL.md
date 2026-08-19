---
name: ctdd-tests
description: >-
  Use for "write tests for this endpoint", "add a regression test", "review
  these tests", "rename these tests", "fix this flaky test without changing
  behavior", "pin the current behavior before refactoring", "add
  characterization tests", "add property tests for this invariant", "find
  missing boundary or error cases", or "derive authorization test cases". Use
  when tests themselves are the deliverable or review subject. Reject
  "implement/fix/change/refactor this backend feature" and "update tests to
  match the new behavior"; route those to ctdd-change. Reject review of a PR,
  MR, branch, staged changes, or pasted diff, including "review just the tests
  in this PR"; route those to ctdd-review. Reject test-framework troubleshooting,
  test-project setup, UI-test authoring, load-test scripts, and infrastructure work.
---
# CTDD: write tests as the spec
Rationale, not procedure: `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-tests/references/rationale.md`.

## Routing
- Keep test-only creation, naming, isolated review, de-flaking, altitude repair, regression, characterization, preservation-pin, property, authorization-conformance, and coverage work here when **What the caller observes is unchanged**.
- Route changed expected behavior, deleted intent tests, characterization **promoted to intent**, or requests to sync tests with implementation to `ctdd-change`; send promotion **through the gate, not as a rename**.
- Route review of any PR, MR, branch, staged set, or pasted diff to `ctdd-review`, even when the requested scope is tests only.

## Guardrails
- Treat approved requirements and confirmed behavior as intent; assert through a public response, value, message, visible state, or contractual interaction.
- Never edit, delete, skip, loosen, replace, or reclassify a test to make implementation pass.
- Stop and hand off to `ctdd-change` before changing an expected outcome or production behavior.
- Derive project-specific test conventions from applicable `CLAUDE.md` and `.claude/rules/`, the target test project, and adjacent tests; stop and report any conflict.
- Do not introduce or default to a test framework, assertion library, fixture style, naming convention, path, or runner.
- Do not introduce production implementation during a test-only task.
- Do not report a run, pass, failure, red state, or checker result without running the command and reading its output in the current turn.

## Output contract
| Output | Exact location | Required shape |
|---|---|---|
| Visible test | Exact repo-relative path printed before editing; use the approved plan path when invoked by `ctdd-change` | Existing test project/module and directory; discovered framework, assertion form, fixture pattern, and naming convention |
| Test review | `stdout` | One verdict per test plus uncovered positive, negative, boundary, and error cases |
| Craft-edit disclosure | `stdout` | Staying here **does not change what the diff reports**; **say so in one line**: `Tests changed: <exact paths/names>. Observable behavior unchanged: <reason>.` |
| Authorization matrix | Exact repo-relative output path printed before generation | Generated from the named contract and checked against the same path |
| Hold-out test | No agent-produced file | A human writes 1–3 acceptance tests outside `${CLAUDE_PROJECT_DIR}`, keeps that location unreadable to the agent, runs them once after the visible suite is green, and reports only passed/failed/declined |

## Ordered test-writing workflow
Execute steps 1–8 in order when the task adds a test. Two lanes run reduced:
- **Craft edit to an existing test** (rename, de-flake, altitude repair): steps 1–2, then 5–8; skip 3–4; in step 6 the required result is an unchanged verdict; step 8 carries the craft-edit disclosure. Read `Test review` items 1, 2 and 6 first — they carry the operative criteria for altitude, naming and de-flaking, and retrying around a flake is never the fix.
- **Isolated review or gap-finding**, writing nothing: steps 1–2, then **Test review**, then step 8.

Do not start implementation from this skill.
1. **Route. Precondition:** the request and available repository context are known.
   - Keep the task here only when tests are the unit of work and caller-visible intent remains unchanged.
   - Stop at the named sibling when a routing rule above fires.
2. **Discover conventions. Precondition:** step 1 kept the task here.
   - Read every applicable `CLAUDE.md` and `.claude/rules/` file plus the nearest behavior-level tests, target test project configuration, contract, and runner configuration.
   - Confirm repository instructions against the target project and adjacent tests; stop and report any conflict.
   - Print the framework, assertion library, test project/module, test directory, exact target file path, class/file naming, test naming, fixture pattern, and exact focused test command.
   - Stop before writing when any required artifact location or convention remains unknown.
3. **Derive the case set. Precondition:** step 2 produced every exact convention and path.
   - State the observable rule and independently sourced expected values; list at least one positive case, every material boundary, each invalid or forbidden case, and each contractual error path.
   - For every case, state setup, action, observable result, and forbidden side effects.
   - Keep separate tests for distinct rules. Merge cases only when setup, action, observable rule, and side-effect assertions are identical; retain named boundary and error inputs as data rows.
4. **Choose evidence direction. Precondition:** step 3 has no unresolved intent conflict.
   - Mark new behavior and bug regressions `must fail before implementation`. A bug-fix regression test is the spec of the fix and stays as long as that behavior is required; deleting it later removes the spec.
   - Mark confirmed preservation pins and `currently_*` characterization observations `must pass before refactor`.
5. **Write tests only. Precondition:** step 4 assigned every test one evidence direction.
   - Write each test at the public boundary in the discovered framework and exact target path.
   - Name each test as an observable requirement; prefix only unconfirmed observations with `currently_`.
6. **Run before implementation or refactor. Precondition:** only the declared test artifacts changed.
   - Run the exact focused command from step 2 and read the complete output.
   - Under an approved `ctdd-change` plan, save per-test output to its exact `.redstate.log` or `.pinstate.log` path and run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <log> --tests-from <plan-path>` with the matching evidence direction, adding `--expect-pass` for pins.
7. **Resolve the result. Precondition:** step 6 produced executable test output.
   - Preserve a new-behavior test that fails for the planned observable reason.
   - Preserve a preservation pin or characterization observation that passes, and a craft edit whose verdict is unchanged: those are the required results of their lanes, not blocked states.
   - Apply the `When blocked` action for every other result; stop when a preservation pin or characterization observation fails before refactor.
8. **Report. Precondition:** every written test has valid current-turn evidence or an explicit stop result.
   - Print exact paths, test names, covered positive/negative/boundary/error cases, command, result, any hand-off, and the craft-edit disclosure when required.

## When blocked
| Signal | Required action |
|---|---|
| Expected behavior or public API is unclear | Stop; do not invent an API, result, or error contract. Report the unresolved decision to `ctdd-change`. |
| A public-boundary test is hard, nearly every dependency needs a mock, or setup obscures the rule | Use an existing higher public boundary and test helpers. If blocked, report coupling/design pressure to `ctdd-change`; do not expose internals, substitute call counts, or change production design here. |
| The assertion is about a pure transformation — a lexical form, encoding, ordering, or null shape — and the boundary reached needs a database, network, or broker | Cover the matrix exhaustively at the smallest boundary that has a contract of its own. Keep one representative case at the outer boundary, plus anything only reachable there; it proves the wiring and survives a refactor moving the work. Two exhaustive tiers is one tier of waste. |
| The test cannot compile because a public type or member is absent | Do not count compilation failure as RED. Request a compile-only stub from `ctdd-change`; resume only after the test executes. |
| The harness, fixture, clock, random source, ordering, or environment fails | Fix test support without changing the expectation, then rerun. |
| A `must fail before implementation` test passes | Stop; verify whether behavior already exists or the assertion fails to constrain it — break the one production rule the test names, re-run, and revert. Green against the broken rule means the test asserts nothing; red means the behavior genuinely exists. Verify the revert by re-running the same command and confirming a clean production diff. |
| A checker cannot run, cannot read its input, or exits `2` | Its claim is unverified, never a pass. `--expect-pass` with `--tests-from <plan-path>` over a plan naming no pin is a usage error. Fix the invocation and re-run; report if it still cannot run. |
| Manual testing, coverage, code inspection, a test written after implementation, simplicity, existing untested code, time already spent, or retained exploration replaces assigned evidence | Reject it. Only preservation pins and characterization observations use `must pass before refactor`; discard exploration, then hand implementation to `ctdd-change` after executable RED. |

## Worked case derivation
Use an adjacent behavior-level test from the target test project as the syntax specimen. Do not copy framework syntax, attributes, assertion APIs, fixture style, naming, or paths from this skill.

Contract: capture accepts `0 < amount <= remaining`, returns `200`, and emits one `PaymentCaptured`; invalid amounts return `400` and emit none.

| Case | Input | Required observable result | Required side effect | Forbidden side effect |
|---|---|---|---|---|
| Representative positive | amount `40`, remaining `100` | `200` | Exactly one `PaymentCaptured` | A second event |
| Upper boundary | amount `100`, remaining `100` | `200` | Exactly one `PaymentCaptured` | A second event |
| Lower boundary | amount `0`, remaining `100` | `400` | None | Any `PaymentCaptured` |
| Below lower boundary | amount `-1`, remaining `100` | `400` | None | Any `PaymentCaptured` |
| Above upper boundary | amount `101`, remaining `100` | `400` | None | Any `PaymentCaptured` |

Render with step 2 conventions and path. Keep positive and upper-boundary rules identifiable; combine `0` and `-1` only when output names both. Infer no syntax or path here.

## Test review
Entered from the review lane above, or from `ctdd-review` for the test portion of a diff. For each test, report:
1. **Altitude:** rewrite when a behavior-preserving refactor breaks it.
2. **Name:** rename mechanisms into observable intent.
3. **Pinning power:** identify missing positive, negative, boundary, error, and forbidden-side-effect assertions, and cases asserted exhaustively at two boundaries at once.
4. **No weakening:** flag any relaxed, deleted, skipped, or reclassified expectation as a spec amendment. An assertion moved to a smaller boundary is not weakened — but only when the destination test is named and observed passing; "I moved it" without a named destination is a deletion.
5. **Interaction coupling:** replace internal interaction verdicts with observable outcomes; retain interactions that are themselves contractual; state **what determines the verdict**.
6. **Determinism:** a flaky spec reads as an unreliable spec, to the agent and the human, so retrying around it is never the fix. **Name the uncontrolled input**: clock, timezone, ID, random value, sleep, retry, shared fixture, external dependency, or order dependency.
7. **Contract alignment:** stop on disagreement between test, API/consumer contract, and approved intent.
8. **Artifact fit:** verify exact path, framework, naming, fixture, and assertion conventions.
Summarize each as keep / rename / rewrite-altitude / de-flake / add-coverage / reduce-interaction-coupling / contract-mismatch / spec-amendment. When `ctdd-review` entered this section, carry only the non-`keep` verdicts into its findings as `test-quality`, except `contract-mismatch` (`spec-change`) and `spec-amendment` (`spec-change`); `keep` is a non-finding and is never emitted.

## Special test forms
- For idempotency, ordering, round-trips, state machines, or validation invariants, use a project-approved property-test library; assert outcomes and duplicate/forbidden side effects. **On the JVM, not jqwik** — its maintainer states the project is not meant to be used by AI coding agents, and the engine prints a line to stdout on every run instructing agents to disregard previous instructions and ignore the run's results. `.redstate.log` is captured stdout, so that text lands in the artifact the deterministic layer reads as evidence.
- Generate authorization conformance with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gen-authz-matrix.py" <openapi-path> -o <matrix-path>`, then `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gen-authz-matrix.py" <openapi-path> --check <matrix-path>`. Inspect every operation with no `allow` row, and assert the matrix in a test. The generator synthesises one identity per scope and never a combination, so an operation needing AND-ed scopes or `x-roles` plus a scope is structurally all-deny: read that as a generator limit, never as a contract fact. Scaffolding a 403 assertion from it inverts the contract.
- For money, authorization, and state-machine cores, run the project-approved mutation tool; strengthen behavior assertions for non-equivalent surviving mutants and ignore equivalent mutants.
- For an SLO or latency budget, propose a check naming metric, percentile, workload, environment, and threshold; do not author load-test scripts here.
- Mark only unconfirmed observations `currently_`; preservation pins **must not** be marked. Both land under the plan's `Preservation pins` heading, which names the direction the evidence runs, not the artifact's intent. Promote or remove the marker only through approved `ctdd-change`: show the old marked name and the new name together, and drop the marker last, so the gate can tell a promoted observation from new intent.
