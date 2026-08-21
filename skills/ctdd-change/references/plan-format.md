# Implementation plan format

**This plan has two readers.** The summary is for the human at the gate: a few minutes, and a reader who agrees with every recommendation approves from it alone — so it names every decision they might refuse, including the hold-out and anything they must act on. Everything below is for the agent implementing it and for the reader who disagrees: exact names, exact values, exact paths, and no ceiling on how much of that a change needs. Length below the summary is not a fault; a summary that does not stand alone is, and so is a section repeating what another already carries. 
Close the summary with the categorical `Risk:` line: it is form-like, and it is what `check-plan.py` parses to derive the tier.

Load this file only at `SKILL.md` step 5.1.

1. Write the sections below in the displayed order.
2. Replace every placeholder.
3. Use exact repository-relative paths and exact test names.
4. Write an empty mandatory section as `<Section name>: none — <reason>` on the heading line itself, with no bullet under it. A bullet reading `none` is extracted by `check-redstate.py` as a test name and fails the run.
5. Omit only the sections marked conditional.

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
Known gaps (conditional: omitted at the small or medium tier)
Assumptions (conditional: omitted at the small tier)
Uncovered or ambiguous (conditional: omitted at the small tier)

New-behavior tests
- `<exact test name>` - path: `<path>`; case: <positive | negative | boundary | error path | authorization | side effect | legacy behavior>; <behavior>; expected pre-implementation failure: <what fails>.
Case coverage not reached (conditional: omitted at the small or medium tier)
Preservation pins
Changed existing assertions (conditional: include only when an existing assertion changes)
Colocated notes (conditional: include only when step 10.2 will write one)

Contract changes (conditional: omitted at the small or medium tier)
NFR budgets (conditional: omitted at the small or medium tier)
ADR draft (conditional: include only when `SKILL.md` step 4.3 fires)
Implementation slices (conditional: omitted at the small tier)
Verification
Hold-out (conditional: omitted at the small tier)
Files likely to change
Residual risk (conditional: omitted at the small tier)
```

Name the plan file `<TICKET>-<kebab-slug>.md`, or `<YYYY-MM-DD>-<kebab-slug>.md` without a ticket.

## Gate-visible sections

The plan file is the complete artifact; the terminal is where the human decides. The summary and the `Hold-out` block go to `stdout` in full at step 6.1.

The hold-out is printed in full because it is the one item asking the human to leave the terminal and do something.

The summary names — one line each, not the sections — every decision the human may refuse other than the `Hold-out`, printed in full above: `Business requirement`, `Assumptions`, `Uncovered or ambiguous`, `Known gaps`, `NFR budgets`, `Residual risk`, and an `ADR draft` when one exists. Offer those sections; print them when asked.

## Plan tiers

`check-plan.py` requires a different section set per tier and names the tier it applied on every run. The tier is **derived, never written**: `small` needs `contract: none`, `risk: normal`, `hold-out: not required`, `New-behavior tests: none`, and at least one named test in the other lane; any contract delta, `high-risk`, a required hold-out, or **no named test in either lane** is `large`; everything else is `medium`. So `small` cannot be claimed over a contract delta the way `trivial` was once claimed over an absent diff.

Tiers shrink **documentation**, never **evidence**. Both test headings, the risk line, the verification commands, and the approval gate are required at every tier — a tier that could drop one would rebuild the triviality hole under a friendlier name.

## Field rules

The complete example below is the operative instruction: anything it demonstrates is not restated here. These are the rules an example cannot carry — prohibitions, decisions with more than one branch, and transitions that leave no trace in a finished plan.

1. Use `normal` or `high-risk`; never write `trivial` in a plan.
2. Set `contract: breaking` when an existing route, response shape, request shape, event shape, or error code changes incompatibly.
3. Put each changed existing assertion in `Changed existing assertions` with its old and new forms.
4. Cover every applicable row of **Required case coverage** below, and record every row the change does not reach under `Case coverage not reached` as `<case> — n/a — <reason>`; never leave a row unaddressed.
5. Require a hold-out for money, authorization, state-machine, rounding, inclusivity, timezone, fee-treatment, or other load-bearing boundary semantics.
6. Present a required hold-out as a decision, not a notice: name the 1–3 assertions to write, each an observable input and *which* output to assert — never the value, which the human computes (rule 8); give `write` and `decline` with their consequences; recommend one with a reason. "Write some sealed tests" has been declined six times; a named assertion with a number to compute is a five-minute task. Contents stay outside the agent-readable tree.
7. Use `result: pending` until the required hold-out runs. Before the packet, replace it with `passed`, `failed`, `declined by human`, or `NOT RUN — <reason>`; `declined by human` is a waiver, not a neutral outcome — record it as one and expect the review to report it; unavailability is never a decline.
8. When the human declines a required hold-out, list the load-bearing expected values and ask them to recompute each one by hand from the business requirement, never by reading the code that produced it. Offer it as the fallback, never as the equivalent, and do not label it a hold-out result.
9. Use exact file paths; never write wildcards, directories, `(+ tests)`, `TBD`, or unnamed future files.
10. Pin the tests that already assert a decision recorded by any ADR this change touches; a decision no test protects is a decision this change can silently reverse.
11. Capture the human's stated direction, not a competing one; a decision handed back unresolved returns to `BLOCKING` with their version as the default. Record every resolved BLOCKING answer under `Decisions confirmed in session` and replace the question with `none — answered before approval`; the section is required, so removing it fails the re-run, and the answer must be findable without the chat. Re-run the checker after every plan edit; re-present when the answer changes any other presented decision.

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
One capture below the authorized amount; over-capture still rejected. BLOCKING: the remainder's hold lifetime. Assumed: it releases at once. Gap: `settlement-batch` unpinned. Not reached: authorization. NFR: none. Residual: the expiry path rides on the hold-out. No ADR.
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
- `settlement-batch` has no consumer contract; only `checkout-web` is pinned.

Assumptions
- A successful partial capture moves the payment to `CAPTURED`.
- The released remainder is not re-capturable.

Uncovered or ambiguous
- The released remainder's hold lifetime requires the BLOCKING answer.

New-behavior tests
- `capture_succeeds_when_amount_is_below_authorized` — path: `tests/payments/CaptureTests.cs`; case: positive, side effect; accepts `87.50` against `100.00`, returns `200`, and publishes exactly one `PaymentCaptured`; expected pre-implementation failure: current equality rule rejects the request.
- `capture_succeeds_when_amount_is_one_cent` — path: `tests/payments/CaptureTests.cs`; case: boundary; accepts the smallest positive amount; expected pre-implementation failure: current equality rule rejects the request.
- `capture_succeeds_when_amount_is_one_cent_below_authorized` — path: `tests/payments/CaptureTests.cs`; case: boundary; accepts the upper interior boundary; expected pre-implementation failure: current equality rule rejects the request.
- `capture_fails_when_released_remainder_is_recaptured` — path: `tests/payments/CaptureTests.cs`; case: error path; starts from a fixture with a released remainder and returns `409` with no second `PaymentCaptured`; expected pre-implementation failure: no released-remainder guard exists.

Case coverage not reached
- authorization — n/a — the capture policy on the route is unchanged.

Preservation pins
- `capture_succeeds_when_amount_equals_authorized_amount` — path: `tests/payments/CaptureTests.cs`; case: legacy behavior, side effect; full capture remains accepted before and after.
- `capture_fails_when_amount_is_zero` — path: `tests/payments/CaptureTests.cs`; case: boundary; zero remains rejected before and after.
- `capture_fails_when_amount_is_negative` — path: `tests/payments/CaptureTests.cs`; case: negative; negative amounts remain rejected before and after.
- `capture_fails_when_amount_exceeds_authorized_amount` — path: `tests/payments/CaptureTests.cs`; case: boundary; over-capture remains rejected before and after.

Contract changes
- `payments/contract/openapi.yaml` — change the amount constraint to `0 < amount <= authorizedAmount`; compatibility: backward-compatible; consumers: checkout-web, settlement-batch; consumer pin: `pacts/checkout-web-payments.json` runs in CI — a break fails the build, not production; rollout: single deploy.

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
- `dotnet test` — expected: broader suite green.
- `dotnet build` — expected: exit 0.
- `spectral lint payments/contract/openapi.yaml` — expected: no errors.

Hold-out
- decision: required
- reason: money-path amount and boundary semantics
- request: 2 sealed tests. (1) capture 33.33 against an authorization of 100.00, assert the response status and resulting payment state, computed by you from the requirement. (2) capture the exact authorized amount, assert the resulting state. Your own words, not the names above.
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
