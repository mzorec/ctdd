# Implementation plan format

Load this file only at `SKILL.md` step 6.1.

1. Write the sections below in the displayed order.
2. Replace every placeholder.
3. Use exact repository-relative paths.
4. Use exact test names.
5. Write `none — <reason>` for an empty mandatory section.
6. Omit only the sections marked conditional.

```markdown
<Decision summary: one to three sentences naming the proposed direction, the highest risk, and every unresolved decision.>
Risk: <normal | high-risk> · contract: <none | additive | breaking> · ADR: <none | NNNN required> · hold-out: <not required | required: 1–3 sealed tests from human>

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
- `<exact test name>` — path: `<path>`; <behavior>; expected pre-implementation failure: <assertion failure or behavioral mismatch>.

Preservation pins
- `<exact test name>` — path: `<path>`; <behavior that must pass before and after>.

Changed existing assertions (conditional: include only when an existing assertion changes)
- `<exact test name>` — path: `<path>`; old: `<assertion>`; new: `<assertion>`; business requirement: <reason>.

Contract changes
- `<path>` — <exact boundary delta>; compatibility: <backward-compatible | breaking>.

NFR budgets
- latency/throughput: <unchanged | budget and verification>
- authorization: <unchanged | changed surface and verification>
- tenant isolation: <unchanged | changed surface and verification>
- retention/audit: <unchanged | changed surface and verification>

Hold-out
- decision: <required | not required>
- reason: <reason>
- request: <1–3 sealed tests written and withheld by the human | n/a>
- storage: <location outside the agent-readable working tree | n/a>
- runner: <human or CI job that runs the sealed tests once after green | n/a>
- result: <pending | not required>
- human-verified expected values: <assertions and values | n/a> (include when the human declines a required hold-out)

ADR draft (conditional: include only when step 4.2 fires)
- Context: <situation, constraints, and options>
- Decision: <chosen structure>
- Consequences: <benefits, costs, and follow-up>

Files likely to change
- `<exact path>` — <planned change>
```

## Field rules

1. Use `normal` or `high-risk`; never write `trivial` in a plan.
2. Set `contract: breaking` when an existing route, response shape, request shape, event shape, or error code changes incompatibly.
3. Put every answer-dependent question under `BLOCKING` with a recommended answer.
4. Put every assumed decision under `Proceeding unless you object`.
5. Cite retrieved contracts and tests under `Existing behavior`.
6. Write both `New-behavior tests` and `Preservation pins` on every plan.
7. List happy, negative, boundary, and error-path tests required by the change.
8. Put each changed existing assertion in `Changed existing assertions` with its old and new forms.
9. Require a hold-out for money, authorization, state-machine, rounding, inclusivity, timezone, fee-treatment, or other load-bearing boundary semantics.
10. Ask the human to write 1–3 hold-out tests directly from the business requirement and keep their contents outside the agent-readable working tree.
11. Name the human or CI job that runs the hold-out once after the visible suite is green.
12. Record `result: pending` at plan time for a required hold-out.
13. Record `result: not required` when no hold-out is required.
14. When the human declines a required hold-out, list the load-bearing expected values the human must verify independently and do not label that fallback as a hold-out.
15. Use exact file paths; do not use wildcards, directories, `(+ tests)`, or unnamed future files.
16. Update the plan before approval when a resolved BLOCKING answer changes risk, contract compatibility, tests, or files.

## Complete example

Request: `Add partial capture to the payments service.`

```markdown
Allow one capture below the authorized amount while preserving over-capture rejection. The unresolved decision is the released remainder's hold lifetime. Money-path boundary semantics require a sealed hold-out.
Risk: normal · contract: additive · ADR: none · hold-out: required: 2 sealed tests from human

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
- `capture_succeeds_when_amount_is_below_authorized` — path: `tests/payments/CaptureTests.cs`; accepts `87.50` against `100.00`; expected pre-implementation failure: current equality rule rejects the request.
- `capture_succeeds_when_amount_is_one_cent` — path: `tests/payments/CaptureTests.cs`; accepts the smallest positive amount; expected pre-implementation failure: current equality rule rejects the request.
- `capture_succeeds_when_amount_is_one_cent_below_authorized` — path: `tests/payments/CaptureTests.cs`; accepts the upper interior boundary; expected pre-implementation failure: current equality rule rejects the request.
- `capture_fails_when_released_remainder_is_recaptured` — path: `tests/payments/CaptureTests.cs`; starts from a fixture with a released remainder and rejects another capture; expected pre-implementation failure: no released-remainder guard exists.

Preservation pins
- `capture_succeeds_when_amount_equals_authorized_amount` — path: `tests/payments/CaptureTests.cs`; full capture remains accepted before and after.
- `capture_fails_when_amount_is_zero` — path: `tests/payments/CaptureTests.cs`; zero remains rejected before and after.
- `capture_fails_when_amount_is_negative` — path: `tests/payments/CaptureTests.cs`; negative amounts remain rejected before and after.
- `capture_fails_when_amount_exceeds_authorized_amount` — path: `tests/payments/CaptureTests.cs`; over-capture remains rejected before and after.

Contract changes
- `payments/contract/openapi.yaml` — change the amount constraint to `0 < amount <= authorizedAmount`; compatibility: backward-compatible.

NFR budgets
- latency/throughput: unchanged — no new external call or loop.
- authorization: unchanged — existing capture policy remains on the route.
- tenant isolation: unchanged — payment lookup remains tenant-scoped.
- retention/audit: unchanged — the existing audit event already records authorized and captured amounts.

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
```
