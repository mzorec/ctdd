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
- Write the tests when `ctdd-change` invokes you under an approved plan: that is the gate having already run, and it is the only route by which a new-behavior test can be written at all.
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
| Test review | `stdout` | One verdict per test plus the uncovered cases, by the names step 5 uses |
| Craft-edit disclosure | `stdout` | Staying here **does not change what the diff reports**; **say so in one line**: `Tests changed: <exact paths/names>. Observable behavior unchanged: <reason>.` |
| Authorization matrix | Exact repo-relative output path printed before generation | Generated from the named contract and checked against the same path |

## Ordered test-writing workflow
Execute steps 1–8 in order when the task adds a test. Two lanes run reduced:
- **Craft edit to an existing test** (rename, de-flake, altitude repair): steps 1–2, then 5–8; skip 3–4; run the test once before editing and record its verdict — step 6 requires it unchanged; step 8 carries the craft-edit disclosure. Read `Test review` items 1, 2, 4 and 6 first — they carry the criteria for altitude, naming, weakening and de-flaking; retrying around a flake is never the fix.
- **Isolated review or gap-finding**, writing nothing: steps 1–2, then **Test review**, then step 8 — verdicts only: this lane runs no test.

Do not start implementation from this skill.
1. **Route. Precondition:** the request and available repository context are known.
   - Keep the task here only when tests are the unit of work and caller-visible intent remains unchanged.
   - Stop at the named sibling when a routing rule above fires.
2. **Discover conventions. Precondition:** step 1 kept the task here.
   - Read every applicable `CLAUDE.md` and `.claude/rules/` file plus the nearest behavior-level tests, target test project configuration, contract, runner, and — under a plan — the plan path and its evidence-log paths configuration.
   - Confirm repository instructions against the target project and adjacent tests; stop and report any conflict.
   - Print the framework, assertion library, test project/module, test directory, exact target file path, class/file naming, test naming, fixture pattern, and exact focused test command.
   - Stop before writing when any required artifact location or convention remains unknown.
3. **Derive the case set. Precondition:** step 2 produced every exact convention and path.
   - State the observable rule and independently sourced expected values; list at least one positive case, every material boundary, each invalid or forbidden case, and each contractual error path.
   - For every case, state setup, action, observable result, and forbidden side effects.
   - Keep separate tests for distinct rules. Merge cases only when setup, action, observable rule, and side-effect assertions are identical; retain named boundary and error inputs as data rows.
4. **Choose evidence direction. Precondition:** step 3 has no unresolved intent conflict.
   - Mark new behavior and bug regressions `must fail before implementation`.
   - Read each failure's text, not just its verdict: a missing fixture, a typo or an unrelated defect is not the reason the test names. A bug-fix regression test is the spec of the fix and stays as long as that behavior is required; deleting it later removes the spec.
   - Mark confirmed preservation pins and `currently_*` characterization observations `must pass before refactor`.
5. **Write tests only. Precondition:** step 4 assigned every test one evidence direction, or the craft lane entered with the pre-edit verdict recorded.
   - Write each test at the public boundary in the discovered framework and exact target path.
   - Name each test as an observable requirement; prefix only unconfirmed observations with `currently_`.
6. **Run before implementation or refactor. Precondition:** only the declared test artifacts changed.
   - Run the exact focused command from step 2 and read the complete output.
   - Under an approved `ctdd-change` plan, save per-test output to its exact `.redstate.log` or `.pinstate.log` path and run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <log> --tests-from <plan-path>` with the matching evidence direction, adding `--expect-pass` for pins. `python3` on PATH is a dead stub on many Windows installs; fall back to `py -3` or the full `python.exe` path.
   - Standalone: save the run to a file anyway and verify each named test with `--test <name>`. Evidence you did not capture is evidence you cannot show.
7. **Resolve the result. Precondition:** step 6 produced executable test output.
   - Preserve a new-behavior test that fails for the planned observable reason.
   - Preserve a preservation pin or characterization observation that passes, and a craft edit whose verdict is unchanged: those are the required results of their lanes, not blocked states.
   - Hand a new-behavior test failing for an unplanned reason to `ctdd-change` as `wrong red`.
   - Apply the `When blocked` action for every other result; stop when a preservation pin or characterization observation fails before refactor.
8. **Report. Precondition:** every written test has valid current-turn evidence or an explicit stop result.
   - Print exact paths, test names, the covered cases by the same names step 5 uses, command, result, any hand-off, and the craft-edit disclosure when required.

## When blocked
| Signal | Required action |
|---|---|
| Expected behavior or public API is unclear | Stop; do not invent an API, result, or error contract. Report the unresolved decision to `ctdd-change`. |
| A public-boundary test is hard, nearly every dependency needs a mock, or setup obscures the rule — and not a pure transformation (next row) | Use an existing higher public boundary and test helpers. If blocked, report coupling/design pressure to `ctdd-change`; do not expose internals, substitute call counts, or change production design here. |
| The assertion is about a pure transformation — a lexical form, encoding, ordering, or null shape — and the boundary reached needs a database, network, or broker | Cover the matrix exhaustively at the smallest boundary that has a contract of its own. Keep one representative case at the outer boundary, plus anything only reachable there: it proves the wiring. Two exhaustive tiers is one tier of waste. |
| The test cannot compile because a public type or member is absent | Do not count compilation failure as RED. If the member is planned, request a compile-only stub from `ctdd-change` returning a default, never throwing: a throwing stub reddens every test alike. If it is not planned, stop — the plan is incomplete. Resume at 6 once the test executes, the stub counting as a declared artifact. |
| The harness, fixture, clock, random source, ordering, or environment fails | Fix test support without changing the expectation or the seeded inputs the assertion reads, then rerun. Changing those pins a different scenario. |
| A `must fail before implementation` test passes | Stop; report whether the behavior already exists or the assertion fails to constrain it, and return the finding to `ctdd-change`, which owns the production tree and records a baseline before touching it. Never edit production here to tell the two apart. |
| A checker cannot run, cannot read its input, or exits `2` | Its claim is unverified, never a pass. Exit `2` also reports a plan-content defect, such as a `currently_` name in the new-behavior set — read the message. When the plan's pin heading declares `none`, do not run the pin lane at all: there is nothing to verify, and `--expect-pass --tests-from <plan-path>` over such a plan exits `2` telling you to write a heading that is already there. Otherwise fix the invocation and re-run; report if it still cannot run. |
| Manual testing, coverage, code inspection, a test written after implementation, simplicity, existing untested code, time already spent, or retained exploration replaces assigned evidence | Reject it. Only preservation pins and characterization observations use `must pass before refactor`; discard exploration, then hand implementation to `ctdd-change` after executable RED. |

## Worked case derivation
Use an adjacent behavior-level test from the target test project as the syntax specimen. Do not copy framework syntax, attributes, assertion APIs, fixture style, naming, or paths from this skill.

Contract: capture accepts `0 < amount <= authorizedAmount`, returns `200`, and emits one `PaymentCaptured`; invalid amounts return `400` and emit none.

| Case | Input | Required observable result | Required side effect | Forbidden side effect |
|---|---|---|---|---|
| Representative positive | amount `40`, remaining `100` | `200` | Exactly one `PaymentCaptured` | More than one `PaymentCaptured` |
| Upper boundary | amount `100`, remaining `100` | `200` | Exactly one `PaymentCaptured` | More than one `PaymentCaptured` |
| Lower boundary | amount `0.01`, remaining `100` | `200` | Exactly one `PaymentCaptured` | More than one `PaymentCaptured` |
| Below lower boundary | amount `0`, remaining `100` | `400`, `amount_out_of_range` | None | Any `PaymentCaptured` |
| Authorization | amount `40`, caller lacks `payments:capture` | `403`, `forbidden` | None | Any `PaymentCaptured` |
| Above upper boundary | amount `101`, remaining `100` | `400`, `amount_out_of_range` | None | Any `PaymentCaptured` |

Render with step 2 conventions and path; carry an exact code and body into the plan, and write `n/a — <reason>` for any column a case cannot have. Keep positive and upper-boundary rules identifiable; combine `0` and `-1` only when output names both. Infer no syntax or path here.

## Test review
Entered from the review lane above, or from `ctdd-review` for the test portion of a diff. For each test, report:
1. **Altitude:** rewrite when a behavior-preserving refactor breaks it.
2. **Name:** rename mechanisms into observable intent.
3. **Pinning power:** identify missing positive, negative, boundary, error, and forbidden-side-effect assertions, and cases asserted exhaustively at two boundaries at once.
4. **No weakening:** flag any relaxed, deleted, skipped, or reclassified expectation as a spec amendment. An assertion moved to a smaller boundary is not weakened — but only when the destination test is named and observed passing; "I moved it" without a named destination is a deletion.
5. **Interaction coupling:** replace internal interaction verdicts with observable outcomes; retain interactions that are themselves contractual; state **what determines the verdict**.
6. **Determinism:** a flaky spec reads as an unreliable spec, to the agent and the human, so retrying around it is never the fix. State how many consecutive passes settle it and show them; one run cannot tell a fixed flake from a lucky pass. **Name the uncontrolled input**: clock, timezone, ID, random value, sleep, retry, shared fixture, external dependency, or order dependency.
7. **Contract alignment:** stop on disagreement between test, API/consumer contract, and approved intent.
8. **Artifact fit:** verify exact path, framework, naming, fixture, and assertion conventions; a mismatch is `rename` or `rewrite-altitude`, never a silent pass.
Summarize each as keep / rename / rewrite-altitude / de-flake / add-coverage / reduce-interaction-coupling / contract-mismatch / spec-amendment, each with `file:start-end`, an evidence class and a one-line title: `ctdd-review` publishes all five parts and cannot synthesise what it was not given. When `ctdd-review` entered this section, map each verdict to its category: `contract-mismatch` and `spec-amendment` to `spec-change`, `add-coverage` to `needs-tests`, the rest to `test-quality`. `keep` is a non-finding and is never emitted. Emit `rename` only where the review's own bar is met — a triggering input and an observable consequence; a naming preference has neither, and that skill omits preferences.

## Special test forms
- For idempotency, ordering, round-trips, state machines, or validation invariants, use a project-approved property-test library; assert outcomes and duplicate/forbidden side effects. **On the JVM, not jqwik** — its maintainer states the project is not meant to be used by AI coding agents, and the engine prints a line to stdout on every run instructing agents to disregard previous instructions and ignore the run's results. `.redstate.log` is captured stdout, so that text lands in the artifact the deterministic layer reads as evidence.
- Generate authorization conformance with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gen-authz-matrix.py" <openapi-path> --check <matrix-path>` against the committed matrix first: that is where drift shows. Regenerate with `-o <matrix-path>` only after reading what changed — `--check` immediately after `-o` compares the file to itself and cannot fail. Inspect every operation with no `allow` row, and assert the matrix in a test. The generator synthesises one identity per scope and never a combination, so an operation needing AND-ed scopes or `x-roles` plus a scope is structurally all-deny: read that as a generator limit, never as a contract fact. Scaffolding a 403 assertion from it inverts the contract.
- For money, authorization, and state-machine cores, run the project-approved mutation tool; strengthen behavior assertions for non-equivalent surviving mutants and ignore equivalent mutants.
- For an SLO or latency budget, propose a check naming metric, percentile, workload, environment, and threshold; do not author load-test scripts here.
- Mark only unconfirmed observations `currently_`; preservation pins **must not** be marked. Never mark a new-behavior test and never demote a confirmed pin — both exempt it from red state, so both go through the gate. Both land under the plan's `Preservation pins` heading, which names the direction the evidence runs, not the artifact's intent. Promote or remove the marker only through approved `ctdd-change`: show the old marked name and the new name together, and drop the marker last, so the gate can tell a promoted observation from new intent.
