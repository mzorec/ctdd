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
Risk: <normal | high-risk> · contract: <none | additive | breaking> · ADR: <none | NNNN required> · hold-out: <not required | required: 1-3 sealed tests from human>
Business requirement:
Intended behavior:

BLOCKING - I will not guess
Proceeding unless you object
Decisions confirmed in session (conditional: include only when a BLOCKING question was answered before approval)
Risk level: <normal | high-risk> - <one-line reason>
Existing behavior
Known gaps
Assumptions
Uncovered or ambiguous

New-behavior tests
- `<exact test name>` - path: `<path>`; case: <positive | negative | boundary | error path | authorization | side effect | legacy behavior>; <behavior>; expected pre-implementation failure: <what fails>.
Case coverage not reached
Preservation pins
Changed existing assertions (conditional: include only when an existing assertion changes)

Contract changes
NFR budgets
ADR draft (conditional: include only when `SKILL.md` step 4.3 fires)
Implementation slices
Verification
Hold-out
Files likely to change
Residual risk
```

Name the plan file `<TICKET>-<kebab-slug>.md`, or `<YYYY-MM-DD>-<kebab-slug>.md` without a ticket.

## Gate-visible sections

The plan file is the complete artifact; the terminal is where the human decides. These go to `stdout` in full at step 6.1 whatever the plan's length — each carries a judgement the human may disagree with, and a long plan loses them first:

`Business requirement` · `Assumptions` · `Uncovered or ambiguous` · `Known gaps` · `NFR budgets` · `Residual risk` · `Hold-out` · `ADR draft` when one exists.

## Plan tiers

`check-plan.py` requires a different section set depending on what the plan declares, and names the tier and count it applied on every run. The tier is **derived, never written**: `small` needs `contract: none`, `risk: normal`, `hold-out: not required`, and `New-behavior tests: none`; any contract delta, `high-risk`, or a required hold-out is `large`; everything else is `medium`. So `small` cannot be claimed over a contract delta the way `trivial` was once claimed over an absent diff.

Tiers shrink **documentation**, never **evidence**. Both test headings, the risk line, the verification commands, and the approval gate are required at every tier — a tier that could drop one would rebuild the triviality hole under a friendlier name.

## Field rules

The complete example below is the operative instruction: anything it demonstrates is not restated here. These are the rules an example cannot carry — prohibitions, decisions with more than one branch, and transitions that leave no trace in a finished plan.

1. Use `normal` or `high-risk`; never write `trivial` in a plan.
2. Set `contract: breaking` when an existing route, response shape, request shape, event shape, or error code changes incompatibly.
3. Put each changed existing assertion in `Changed existing assertions` with its old and new forms.
4. Cover every applicable row of **Required case coverage** below, and record every row the change does not reach under `Case coverage not reached` as `<case> — n/a — <reason>`; never leave a row unaddressed.
5. Require a hold-out for money, authorization, state-machine, rounding, inclusivity, timezone, fee-treatment, or other load-bearing boundary semantics.
6. Present a required hold-out as a decision, not a notice: name the 1–3 assertions to write, each an observable input and the expected output; give `write` and `decline` with their consequences; recommend one with a reason. "Write some sealed tests" has been declined six times; a named assertion with a number to compute is a five-minute task. Contents stay outside the agent-readable tree.
7. Use `result: pending` until the required hold-out runs. Before the packet, replace it with `passed`, `failed`, `declined by human`, or `NOT RUN — <reason>`; unavailability is never a decline.
8. When the human declines a required hold-out, list the load-bearing expected values the human must verify independently, and do not label that fallback a hold-out result.
9. Use exact file paths; never write wildcards, directories, `(+ tests)`, `TBD`, or unnamed future files.
10. Pin the tests that already assert a decision recorded by any ADR this change touches; a decision no test protects is a decision this change can silently reverse.
11. Record every resolved BLOCKING answer under `Decisions confirmed in session` and remove the question it answered before approval; an approved plan must not still be asking, and the answer must be findable without the chat. Re-run the checker after every plan edit; re-present when the answer changes any other presented decision.

`ctdd-tests` owns test naming, altitude, assertion form, and what may not be asserted. Do not restate them here: two copies of a test rule drift, and the one in this file is the copy nobody checks.

## Required case coverage

Name the tests here; `ctdd-tests` owns how each one is written.

**Section follows the evidence direction, not the case.** A case this change adds or alters goes under `New-behavior tests`; the same case goes under `Preservation pins` when the change must leave it exactly as it is. The column below names the usual direction — write the other one when this change inverts it, and do not record a case as not reached when it is covered in the other direction.

| Case | Required trigger | Assertion form | Usual section | Plan must name it |
|---|---|---|---|---|
| Positive | The change adds or alters an accepted input | Observable success result | New-behavior | Always |
| Negative | An input the rule must reject | Observable rejection, no state change | New-behavior | Always |
| Boundary | The rule has a minimum, a maximum, or a split | Result at the edge and one step past it, on each edge that exists | New-behavior | When an edge exists |
| Error path | An observable failure, not-found, conflict, or malformed input | Exact contractual code and body, state unchanged | New-behavior | When an error path changes |
| Authorization | The operation is secured | Denied identity observes the contractual denial code | New-behavior | When the route or handler authorizes |
| Side effects | The operation emits, publishes, or writes | Exactly the required effects and none of the forbidden ones | Both | Always |
| Legacy behavior | Existing behavior must survive | Same observable result before and after | Preservation | Always |

Add a row of your own for concurrency, idempotency, duplicate delivery, persistence, serialization, or cancellation when the change touches one; the seven above are the ones that recur, not the whole world.

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
- `capture_succeeds_when_amount_is_one_cent` — path: `tests/payments/CaptureTests.cs`; case: boundary; accepts the smallest positive amount; expected pre-implementation failure: current equality rule rejects the request.
- `capture_succeeds_when_amount_is_one_cent_below_authorized` — path: `tests/payments/CaptureTests.cs`; case: boundary; accepts the upper interior boundary; expected pre-implementation failure: current equality rule rejects the request.
- `capture_fails_when_released_remainder_is_recaptured` — path: `tests/payments/CaptureTests.cs`; case: error path; starts from a fixture with a released remainder and returns `409` with no second `PaymentCaptured`; expected pre-implementation failure: no released-remainder guard exists.

Case coverage not reached
- authorization — n/a — the capture policy on the route is unchanged.

Preservation pins
- `capture_succeeds_when_amount_equals_authorized_amount` — path: `tests/payments/CaptureTests.cs`; case: legacy behavior; full capture remains accepted before and after.
- `capture_fails_when_amount_is_zero` — path: `tests/payments/CaptureTests.cs`; case: boundary; zero remains rejected before and after.
- `capture_fails_when_amount_is_negative` — path: `tests/payments/CaptureTests.cs`; case: negative; negative amounts remain rejected before and after.
- `capture_fails_when_amount_exceeds_authorized_amount` — path: `tests/payments/CaptureTests.cs`; case: boundary; over-capture remains rejected before and after.

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
- request: 2 sealed tests. (1) capture 33.33 against an authorization of 100.00, assert the remaining authorized amount you compute yourself. (2) capture the exact authorized amount, assert the resulting status. Your own words, not the names above.
- options: `write` — 2 assertions, ~5 minutes; `decline` — recorded as `declined by human`, and this plan then lists the values you must verify independently.
- recommended: `write` — the edge was derived from the same document the implementation reads, so nothing in the agent's suite is independent evidence it is right.
- storage: separate repository, unavailable to this session
- runner: CI hold-out job, once the visible suite is green
- result: pending
- human-verified expected values: n/a

Files likely to change
- `payments/contract/openapi.yaml` — relax the capture amount constraint.
- `payments/domain/CaptureService.cs` — implement partial capture and released-remainder handling.
- `tests/payments/CaptureTests.cs` — add new-behavior tests and preserve over-capture rejection.

Residual risk
- The released remainder's expiry path is exercised only by the sealed hold-out.
```
