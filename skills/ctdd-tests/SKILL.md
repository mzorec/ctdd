---
name: ctdd-tests
description: >-
  Write and review tests as the executable spec for backend APIs and
  microservices, following Contract- and Test-Driven Development (CTDD). Use
  whenever the task is about tests themselves: writing or naming tests,
  reviewing or judging test quality, fixing flaky or brittle tests, adding
  regression, characterization, or property-based tests, or improving coverage
  of a backend service — even if the user never says "CTDD". Enforces
  behavior-level (not implementation-coupled) naming, flags tests a
  behavior-preserving refactor would break, checks contract coverage, adds
  property tests for invariants (idempotency, ordering, validation,
  state-machine rules), and suggests mutation testing on the critical core.
  Triggers include "write tests for", "review these tests", "are these tests
  good", "name these tests", "add property tests", "add a regression test",
  "test this endpoint", "why is this test brittle", "pin the current
  behavior", "add characterization tests before we refactor", "assert this
  can never happen", "my refactor broke these tests". Not for visual/UX
  correctness (testable state logic qualifies wherever it lives) and not for
  authoring load/performance test scripts (k6, NBomber, JMeter); when a
  feature is being built end to end, ctdd-change drives the workflow and
  calls this skill.
---

# CTDD: tests as the spec

**Use this skill when tests are the unit of work** — writing tests in isolation, reviewing or critiquing existing tests, judging test quality, or adding property tests. It owns the *craft* of tests. If you are building or changing a feature end to end, use the `ctdd-change` skill instead; it drives the workflow and will invoke this skill when it is time to write tests.

Tests are the executable specification of how a backend service behaves — the artifact the agent and future engineers read to know what the service does. They only serve that purpose if they assert **observable behavior**, not implementation details. This skill writes and reviews tests to that standard.

## The one rule

Write and judge tests at the **behavior level** — what a caller or the outside world observes — not the implementation level. The test name is the spec line, so name tests as statements of intent.

A useful check: **if a correct refactor that preserves behavior breaks the test, the test is at the wrong altitude.** It's testing wiring, not the contract. Fix its altitude. Left unfixed it corrupts the spec: an agent reads the brittleness as intent and preserves it.

### Good behavior-level names

```
returns_404_when_payment_does_not_exist
rejects_capture_when_payment_is_not_authorized
publishes_payment_completed_event_after_successful_capture
is_idempotent_when_the_same_command_is_retried
```

### Implementation-coupled names to avoid

```
calls_repository_once
invokes_mapper
uses_payment_status_validator
handler_calls_private_method
```

## When writing tests

- Assert through the public interface and observable outputs (HTTP response, status, emitted events, persisted state visible via the API) — not private methods, internal call counts, or call order unless order *is* the contract.
- Cover the contract: happy path, boundaries, and error cases. Name each as intent.
- Avoid mocking so heavily that the test only verifies the mocks. Prefer real collaborators or realistic fakes at the service boundary.
- Make tests deterministic: control the clock, IDs, and randomness at the boundary rather than sleeping or retrying around them. A flaky spec reads as an unreliable spec — to the agent and to CI alike.
- For a bug fix, write the failing behavior-level regression test that reproduces it *first* — that test is the spec of the fix, and it stays forever. This is how the suite accumulates edge cases.
- New behavior has no tests yet — writing them is writing the spec. Make the names describe the requirement.

## When reviewing tests

For each test, ask and report:

1. **Altitude** — would a behavior-preserving refactor break it? If yes, flag it as implementation-coupled and suggest a behavior-level rewrite.
2. **Name** — does the name state observable intent? If it names a mechanism (repository, mapper, handler, private method), rename it.
3. **Coverage of the contract** — are happy path, boundaries, and error cases present? Note gaps as "uncovered cases," and be explicit that untested behavior reads as unconstrained to an agent.
4. **Mock weight** — is the test mostly asserting on mocks? Flag it.
5. **Determinism** — is it timing- or ordering-dependent in a way that will flake?
6. **Contract alignment** — for externally visible behavior, does the API contract (and consumer contract, if any) say the same thing the test asserts? A test and a contract that disagree are two specs in conflict; flag it — deciding which one is right is a spec decision for `ctdd-change` and the human, not a silent fix.

Summarize findings as: keep / rename / rewrite / add-coverage / contract-mismatch, with the specific reason for each.

## Property-based tests for invariants

Example tests sample specific inputs; property tests assert a rule across a generated range and so express a universal. Reach for them whenever a "must always hold" rule exists:

- **Idempotency** — applying the same command twice equals applying it once.
- **Ordering / commutativity** — where the spec requires (or forbids) order sensitivity.
- **Round-trips** — encode/decode, serialize/deserialize return the original.
- **State-machine invariants** — e.g. "for every terminal state, this operation is rejected."
- **Validation** — no accepted input ever violates the schema/contract.
- **Authorization matrix** — for any service with roles, generate every-role × every-endpoint expected allow/deny from the contract's security schemes and assert it. Mechanical to produce, behavior-level by construction (it asserts exactly what a caller observes: 2xx vs 401/403), and regenerated when the contract changes so it can't drift — usually the highest-value test artifact per hour in a role-based service. A new endpoint without a matrix row is uncovered authz: flag it.

Prefer generating the input space over hand-enumerating cases, and reach for the ecosystem's standard tools rather than hand-rolling generators — e.g. FsCheck or CsCheck plus Stryker.NET on .NET, Hypothesis plus mutmut on Python, fast-check plus StrykerJS on JS/TS, jqwik plus PIT on the JVM.

For the critical core (money, auth, state machines), also suggest **mutation testing**: coverage alone doesn't prove a test protects a rule — if flipping `>` to `>=` leaves the suite green, the test is weak and should be strengthened.

Where the contract or an ADR states an SLO or latency budget, propose the executable check for it — existence and shape only; authoring the load-test scripts themselves is outside this skill's lane. Shape guidance: fixed baseline, generous margin, trend-alert over hard gate in noisy environments. A flaky perf gate gets disabled and then still *looks* covered, which is worse than an honest absence.

## Characterization tests: observations, not requirements

Before refactoring a thinly-covered area — or whenever untested load-bearing behavior must be touched — pin the current behavior first with **characterization tests**: run the real code at its public boundary, observe what it does, and assert exactly that, including behavior that looks wrong. Their job is to make change visible, not to judge correctness.

Mark them so a reader — human or agent — can tell them apart from asserted intent: prefix the name with `currently_` (or use the ecosystem's category/trait mechanism), e.g. `currently_returns_200_with_empty_body_for_unknown_id`.

The two kinds carry asymmetric obligations, and this asymmetry is the point:

- An **intent test** is the spec. Changing it is changing requirements — the full spec-change treatment applies.
- A **characterization test** is a pinned observation. It may encode a bug. When one fails after a change, the question is "was the old behavior intent or accident?" — and that is a human decision. Never silently update a characterization test to match new behavior, and never silently "fix" code to preserve a pinned behavior nobody has confirmed as intended.

Once a human confirms a pinned behavior *is* intended, promote it: rename it to a behavior-level intent name and drop the marker. Observations graduate into spec; they don't stay observations forever.

## Boundaries this skill respects

- Tests are the spec for **preservation**; they do not tell you *what new thing to build* — that comes from the business requirement and the plan (see the `ctdd-change` skill).
- When a whole change (a PR or diff) is under review, `ctdd-review` drives and calls this skill for the test portion.
- This is for assertable correctness. It does not cover visual/UX correctness, which tests can't assert; testable state logic (reducers, client-side state machines) qualifies wherever it lives.
- If a universal or an intentionally-undefined boundary genuinely can't be made executable, capture it as a one-line colocated invariant note rather than a broader test or prose spec.
