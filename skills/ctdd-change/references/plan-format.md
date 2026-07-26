# Implementation plan format

Load this file only at `SKILL.md` step 5.1.

1. Write the sections below in the displayed order.
2. Replace every placeholder.
3. Use exact repository-relative paths.
4. Use exact test names.
5. Write an empty mandatory section as `<Section name>: none — <reason>` on the heading line itself, with no bullet under it. A bullet reading `none` is extracted by `check-redstate.py` as a test name and fails the run.
6. Omit only the sections marked conditional.

```markdown
<Decision summary: one to three sentences naming the proposed direction, the highest risk, and every unresolved decision.>
Risk: <normal | high-risk> · contract: <none | additive | breaking> · ADR: <none | NNNN required> · hold-out: <not required | required: 1–3 sealed tests from human>
Business requirement: <the requested behavior in the requester's terms>
Intended behavior: <what the caller observes after this change>

BLOCKING — I will not guess
- <one-line question> Recommended answer: <answer>.

Proceeding unless you object
- <decision and consequence>

Risk level: <normal | high-risk> — <one-line reason>

Existing behavior
- `<path>` — `<contract clause or exact test name>`: <observed behavior>.
Known gaps
- <missing artifact or coverage>

Assumptions
- <assumption>

Uncovered or ambiguous
- <case and required resolution>

New-behavior tests
- `<exact test name>` — path: `<path>`; case: <positive | negative | lower boundary | upper boundary | interior boundary | invalid input | authorization | not-found | conflict | cancellation | duplicate delivery | persistence | serialization | error code | side effect | no side effect>; <behavior>; expected pre-implementation failure: <assertion failure or behavioral mismatch>.

Case coverage not reached
- <case category> — n/a — <reason>

Preservation pins
- `<exact test name>` — path: `<path>`; case: <category>; <behavior that must pass before and after>.

Changed existing assertions (conditional: include only when an existing assertion changes)
- `<exact test name>` — path: `<path>`; old: `<assertion>`; new: `<assertion>`; business requirement: <reason>.

Contract changes
- `<path>` — <exact boundary delta>; compatibility: <backward-compatible | breaking>; consumers: <named consumers | none — <reason>>; rollout: <single deploy | ordered steps>.

NFR budgets
- latency/throughput: <unchanged | budget and verification>
- authorization: <unchanged | changed surface and verification>
- tenant isolation: <unchanged | changed surface and verification>
- retention/audit: <unchanged | changed surface and verification>
- observability: <unchanged | added or changed signal and where it is asserted>

Implementation slices
- `<exact production path>` — <change>; turns green: `<exact test name>`.

Verification
- `<exact command>` — expected: <exact outcome>.

Hold-out
- decision: <required | not required>
- reason: <reason>
- request: <1–3 sealed tests written and withheld by the human | n/a>
- storage: <location outside the agent-readable working tree | n/a>
- runner: <human or CI job that runs the sealed tests once after green | n/a>
- result: <pending | not required>
- human-verified expected values: <assertions and values | n/a> (include when the human declines a required hold-out)

ADR draft (conditional: include only when `SKILL.md` step 4.3 fires)
- Context: <situation, constraints, and options>
- Decision: <chosen structure>
- Consequences: <benefits, costs, and follow-up>

Files likely to change
- `<exact path>` — <planned change>

Residual risk
- <what stays unproven after the planned verification>
```

## Field rules

1. Use `normal` or `high-risk`; never write `trivial` in a plan.
2. Set `contract: breaking` when an existing route, response shape, request shape, event shape, or error code changes incompatibly.
3. Put every answer-dependent question under `BLOCKING` with a recommended answer.
4. Put every assumed decision under `Proceeding unless you object`.
5. Cite retrieved contracts and tests under `Existing behavior`.
6. Write both `New-behavior tests` and `Preservation pins` on every plan.
7. Cover every applicable row of **Required case coverage** below.
8. Put each changed existing assertion in `Changed existing assertions` with its old and new forms.
9. Require a hold-out for money, authorization, state-machine, rounding, inclusivity, timezone, fee-treatment, or other load-bearing boundary semantics.
10. Ask the human to write 1–3 hold-out tests directly from the business requirement and keep their contents outside the agent-readable working tree.
11. Name the human or CI job that runs the hold-out once after the visible suite is green.
12. Record `result: pending` at plan time for a required hold-out; resolve it to exactly one of `passed`, `failed`, `declined by human`, or `NOT RUN — <reason>`, and never let an unavailable runner become a decline.
13. Record `result: not required` when no hold-out is required.
14. When the human declines a required hold-out, list the load-bearing expected values the human must verify independently and do not label that fallback as a hold-out.
15. Use exact file paths; do not use wildcards, directories, `(+ tests)`, `TBD`, or unnamed future files.
16. Write every resolved BLOCKING answer into the plan before approval, replacing the question with the decision. Re-run the plan checker and return to the gate when the answer also changes risk, contract compatibility, tests, or files.
17. Give every `Implementation slices` entry exactly one named test that turns green; a slice with no test is an unspecified change.
18. Give every `Verification` command an expected outcome; a command with no expected outcome proves nothing when it is run.
19. Write one behavior per test entry; split an entry that names two observable rules.
20. Name each test after the observable rule, never after its setup.
21. Assert the observable result and the required and forbidden side effects; do not name an internal call, mock interaction, or snapshot of unreviewed output as the expected outcome.
22. List every **Required case coverage** row the change does not reach under `Case coverage not reached` as `<case> — n/a — <reason>`; never leave a row unaddressed.
23. Name every `New-behavior tests` entry as the test that turns some `Implementation slices` entry green; a test no slice turns green is behavior nobody implements.

## Required case coverage

Name the tests here; `ctdd-tests` owns how each one is written.

**Section follows the evidence direction, not the case.** A case this change adds or alters goes under `New-behavior tests`; the same case goes under `Preservation pins` when the change must leave it exactly as it is. The column below names the usual direction — write the other one when this change inverts it, and do not record a case as not reached when it is covered in the other direction.

| Case | Required trigger | Assertion form | Usual section | Plan must name it |
|---|---|---|---|---|
| Positive | The change adds or alters an accepted input | Observable success result | New-behavior | Always |
| Negative | An input the rule must reject | Observable rejection, no state change | New-behavior | Always |
| Lower boundary | The rule has a minimum | Result at the minimum and one step below | New-behavior | When a minimum exists |
| Upper boundary | The rule has a maximum | Result at the maximum and one step above | New-behavior | When a maximum exists |
| Interior boundary | The rule splits a range | Result on each side of the split | New-behavior | When a split exists |
| Invalid input | Malformed, missing, or wrong-typed input | Contractual error code and message shape | New-behavior | When the boundary accepts input |
| Authorization | The operation is secured | Denied identity observes the contractual denial code | New-behavior | When the route or handler is secured |
| Not-found | The operation addresses a resource | Contractual not-found result, no side effect | New-behavior | When an identifier is accepted |
| Conflict | The operation has a forbidden state transition | Contractual conflict result, state unchanged | New-behavior | When a state machine is touched |
| Cancellation | The operation is cancellable or long-running | Cancellation observed, no partial commit | New-behavior | When cancellation is observable |
| Duplicate delivery | The operation consumes a message or accepts a retry key | Second delivery observes the first result and emits nothing new | New-behavior | When messaging or retry is touched |
| Persistence | The operation writes | Committed state on success, no state after failure | New-behavior | When a transaction boundary is touched |
| Serialization | The wire shape changes | Old payload still deserializes; new payload round-trips | New-behavior | When a contract or event shape changes |
| Legacy behavior | Existing behavior must survive | Same observable result before and after | Preservation | Always |
| Error codes | An error path is observable | Exact code and error body | New-behavior | When an error path changes |
| Side effects | The operation emits, publishes, or writes | Exactly the required effects and none of the forbidden ones | Both | Always |

## Complete example

Request: `Add partial capture to the payments service.`

```markdown
Allow one capture below the authorized amount while preserving over-capture rejection. The unresolved decision is the released remainder's hold lifetime. Money-path boundary semantics require a sealed hold-out.
Risk: normal · contract: additive · ADR: none · hold-out: required: 2 sealed tests from human
Business requirement: The merchant is allowed one capture below the authorized amount.
Intended behavior: `POST /payments/{id}/capture` accepts `0 < amount <= authorizedAmount`, moves the payment to `CAPTURED`, and rejects any later capture.

BLOCKING — I will not guess
- What happens to the released authorization remainder? Recommended answer: release it when the original authorization expires.

Proceeding unless you object
- Reject zero and negative capture amounts.
- Prevent a second capture of the released remainder.

Risk level: normal — one service and one additive rule change on a money path.

Existing behavior
- `payments/contract/openapi.yaml` — `POST /payments/{id}/capture`: requires capture amount equal to the authorized amount.
- `tests/payments/CaptureTests.cs::capture_fails_when_amount_exceeds_authorized_amount`: rejects over-capture.
Known gaps
- No consumer contract exists for the checkout caller.

Assumptions
- A successful partial capture moves the payment to `CAPTURED`.
- The released remainder is not re-capturable.

Uncovered or ambiguous
- The released remainder's hold lifetime requires the BLOCKING answer.

New-behavior tests
- `capture_succeeds_when_amount_is_below_authorized` — path: `tests/payments/CaptureTests.cs`; case: positive; accepts `87.50` against `100.00`, returns `200`, and publishes exactly one `PaymentCaptured`; expected pre-implementation failure: current equality rule rejects the request.
- `capture_succeeds_when_amount_is_one_cent` — path: `tests/payments/CaptureTests.cs`; case: lower boundary; accepts the smallest positive amount; expected pre-implementation failure: current equality rule rejects the request.
- `capture_succeeds_when_amount_is_one_cent_below_authorized` — path: `tests/payments/CaptureTests.cs`; case: interior boundary; accepts the upper interior boundary; expected pre-implementation failure: current equality rule rejects the request.
- `capture_fails_when_released_remainder_is_recaptured` — path: `tests/payments/CaptureTests.cs`; case: conflict; starts from a fixture with a released remainder and returns `409` with no second `PaymentCaptured`; expected pre-implementation failure: no released-remainder guard exists.

Case coverage not reached
- authorization — n/a — the capture policy on the route is unchanged.
- not-found — n/a — the existing identifier lookup is unchanged.
- cancellation — n/a — capture is synchronous and not cancellable.
- duplicate delivery — n/a — no message consumer is touched.
- persistence — n/a — the existing transaction boundary is unchanged.
- serialization — n/a — no field is added or removed.
- invalid input — n/a — the request schema and its rejection codes are unchanged by this delta.

Preservation pins
- `capture_succeeds_when_amount_equals_authorized_amount` — path: `tests/payments/CaptureTests.cs`; case: legacy behavior; full capture remains accepted before and after.
- `capture_fails_when_amount_is_zero` — path: `tests/payments/CaptureTests.cs`; case: lower boundary; zero remains rejected before and after.
- `capture_fails_when_amount_is_negative` — path: `tests/payments/CaptureTests.cs`; case: negative; negative amounts remain rejected before and after.
- `capture_fails_when_amount_exceeds_authorized_amount` — path: `tests/payments/CaptureTests.cs`; case: upper boundary; over-capture remains rejected before and after.

Contract changes
- `payments/contract/openapi.yaml` — change the amount constraint to `0 < amount <= authorizedAmount`; compatibility: backward-compatible; consumers: checkout-web, settlement-batch; rollout: single deploy.

NFR budgets
- latency/throughput: unchanged — no new external call or loop.
- authorization: unchanged — existing capture policy remains on the route.
- tenant isolation: unchanged — payment lookup remains tenant-scoped.
- retention/audit: unchanged — the existing audit event already records authorized and captured amounts.
- observability: unchanged — the existing capture log line already carries both amounts.

Implementation slices
- `payments/domain/CaptureService.cs` — accept an amount below the authorized amount; turns green: `capture_succeeds_when_amount_is_below_authorized`.
- `payments/domain/CaptureService.cs` — accept the smallest positive amount; turns green: `capture_succeeds_when_amount_is_one_cent`.
- `payments/domain/CaptureService.cs` — accept the upper interior boundary; turns green: `capture_succeeds_when_amount_is_one_cent_below_authorized`.
- `payments/domain/CaptureService.cs` — reject a capture of the released remainder; turns green: `capture_fails_when_released_remainder_is_recaptured`.

Verification
- `dotnet test --filter CaptureTests` — expected: all listed new-behavior and pin tests pass.
- `dotnet build` — expected: exit 0.
- `spectral lint payments/contract/openapi.yaml` — expected: no errors.

Hold-out
- decision: required
- reason: money-path amount and boundary semantics
- request: 2 sealed tests written and withheld by the human
- storage: separate hold-out repository unavailable to the agent session
- runner: CI hold-out job, once after the visible suite is green
- result: pending
- human-verified expected values: n/a

Files likely to change
- `payments/contract/openapi.yaml` — relax the capture amount constraint.
- `payments/domain/CaptureService.cs` — implement partial capture and released-remainder handling.
- `tests/payments/CaptureTests.cs` — add new-behavior tests and preserve over-capture rejection.

Residual risk
- The released remainder's expiry path is exercised only by the sealed hold-out.
```
