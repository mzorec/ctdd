# The implementation plan — output contract

Read this before writing a plan (step 6). It is the authoritative format; the skill carries only
the field list. `check-plan.py` validates presence of these sections, so a plan written without
this file is caught mechanically rather than shipping malformed — but presence is not quality,
and the guidance below is what makes each field worth reading.

Produce this as a reviewable summary, then stop for approval on non-trivial changes:

**Lead with a decision summary the human can read in under a minute**, then put the supporting detail below it — the gate asks for a *ruling on decisions and risks*, not a reading of the whole file inventory. **The test of the summary is that a reader who agrees with it can approve without scrolling**; if they must go into the detail to find out what they are agreeing to, the summary has failed and the two-layer structure has bought nothing.

Write it the way you would tell a colleague what you found, standing at their desk with thirty seconds of their attention — **lead with what surprised you, or what you are not willing to guess at**. A summary that reads like a filled-in form has failed even when every field is correct: fields carry categories, and what a reviewer needs is the one thing about *this* change that is not routine. If nothing about it is surprising, say exactly that in a sentence and stop — a short honest summary is the goal, not a filled page.

Close it with a single categorical line, demoted because it is genuinely form-like: `Risk: normal · contract: additive · ADR 0005 required · hold-out: 2 sealed tests from you`. State `contract: breaking` explicitly whenever an existing response shape, route, or error code changes — a breaking change a reviewer meets in the file inventory rather than the summary is the failure this line exists to prevent — and name anything the human is on the hook for, because those are commitments, not information.

Then the two buckets:

- **BLOCKING — I will not guess.** The open questions whose answer changes the implementation and which you refuse to assume: each as a one-line question with your recommended answer. These are what approval actually turns on.
- **Proceeding unless you object.** Decisions you've made and will act on (schema choices, ordering, nullability, what the repository returns): one line each. Consequences you'll absorb belong here, not in BLOCKING — the point is to show them without asking permission for each.

A reader who agrees with every recommendation should be able to approve from the summary alone. The detail below is backup for when they don't.

The detail section, in full:

- **Risk level** — normal / high-risk, with one line on why (a trivial change produces no plan at all — see the workflow preamble — so a plan's risk line never reads `trivial`; and, if a high-risk unknown is carved out of an otherwise-normal change, name it here so the risk call is honest). This is the justification for the ceremony being scaled up or down; a reviewer who disagrees with the risk call should be able to object to that before anything else. **If a BLOCKING decision later resolves in a way that changes scope — a type-only option becoming a breaking rewire, say — restate the risk level and the contract-changes section to match the branch actually chosen.** A plan whose top-line risk reflects the option you didn't take reads as safer than the work is.
- **Existing behavior** found in the contract and relevant tests — cite the file paths and test names actually retrieved (evidence, not paraphrase), so thin retrieval is visible to the reviewer. State known gaps explicitly — "no Pact found for the checkout caller" converts silence into a reviewable absence.
- **Assumptions** you are making.
- **Uncovered or ambiguous cases** — behavior that matters but isn't pinned by a test, and anything the requirement doesn't specify.
- **Proposed new/changed tests** — named at the behavior level, and **split under two headings when both kinds are present**, because their evidence runs in opposite directions:
 - `New-behavior tests — must be observed failing` (red state applies; `check-redstate.py --tests-from` reads *only* these)
 - `Preservation pins — must pass before and after` (green-then-still-green is their evidence; verified with `check-redstate.py --expect-pass`, never the default red-state check — see step 7)

 **When a change both preserves and creates, do the preserving part first** — pins describe how the current code behaves, so a pin written before a change that reshapes what it observes still passes while proving nothing. Pin, convert, verify green, *then* build the new behavior on top. This ordering is a correctness property, not a preference: get it backwards and the suite stays green while the detector is silently gone.

 For each *changed existing* test, show the old and the new assertion, not just the name — the name is exactly where a wrong encoding hides.
- **Contract changes**, if any (and whether they're backward-compatible; flag breaking changes explicitly).
- **NFR budgets this change could touch** — latency/throughput, authz surface, tenant isolation, retention/audit. State "none" explicitly; an unstated budget is not a free one.
- **Hold-out** — required / not required, with why. Required when the change alters money, auth, state-machine, or boundary semantics (rounding, inclusivity, timezones, fee treatment). If required, ask the human to write 1–3 acceptance tests directly from the business spec and to withhold them from you; they run once, after green (sealing them is the team's CI job — see the README). Record the decision **and track its outcome**: write `result: pending` at plan time; step 9 updates it to `passed`, `failed`, or `declined by human`. The outcomes are not equivalent: `failed` **blocks approval at review** — `ctdd-review` treats a failed hold-out as a merge-blocking finding, and since nothing mechanical enforces it the reviewer is that gate; a failed hold-out is the method working, and merging past it is the one thing the hold-out exists to prevent. `declined by human` is an explicit **waiver**, reported at review as a deviation on a load-bearing change, never a neutral success. Never proceed as if this step happened when it didn't — and never leave it `pending` past review.

  **Where the hold-out is declined, fall back to human-verified expected values** on the load-bearing assertions — a distinct, cheaper guard, not a degraded hold-out. You write the test; the human checks the *number*, by doing the arithmetic rather than reading the code that produced it (capturing 87.50 of 100 leaves 12.50). Say which assertions you want checked and show the values plainly. This breaks the **shared-computation** path, where a test derives its expected value from the same production helper the implementation uses and both encode the same wrong rule. It cannot break a **shared misunderstanding**: if the human misreads the requirement the same way you did, the number looks right to both of you, and only a sealed test written from the business spec by someone who has not seen the implementation reaches that. Offer it as the fallback, never as the equivalent — a guard that quietly replaces the hold-out makes circularity worse while feeling like progress.
- **ADR draft**, if step 4 produced one.
- **Files likely to change.**

Treat a change to an existing test as a change to the spec — call it out for review. If this plugin's `"${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py"` is available (that variable resolves to the plugin's install directory, so the command works from any project; quote it, since the path can contain spaces), run the emitted plan through it — adding `--diff` with the current `{ git diff --name-status -M <baseline>; git ls-files --others --exclude-standard | sed 's/^/A\t/'; }` once edits exist (the second half so a new, still-untracked test file is counted, not silently missed), so a trivial claim is cross-checked against the actual surface — and fix any missing sections before presenting.

### Example (condensed)

Request: *"Add partial capture to the payments service — allow capturing less than the authorized amount."*

```
A backward-compatible relaxation of the capture amount rule — the one thing I
won't guess is what happens to the auth hold on the released remainder.
Risk: normal · contract: additive · no ADR · hold-out: 1–2 sealed tests from you

BLOCKING — I will not guess:
- What happens to the auth hold on the released remainder? (recommend: it
 expires with the original authorization)
Proceeding unless you object:
- Zero capture amount is rejected; the released remainder is not re-capturable

Risk level: normal — single-service, backward-compatible contract change;
money path, so amount edge cases must be pinned in tests

Existing behavior (payments/contract/openapi.yaml; tests/payments/CaptureTests.*):
- POST /payments/{id}/capture requires amount == authorized amount
- capture_fails_when_amount_exceeds_authorized_amount covers over-capture
Known gaps: no consumer contract (Pact) found for the checkout caller

Assumptions:
- Partial capture moves the payment to CAPTURED (no new PARTIALLY_CAPTURED state)
- The released remainder is not re-capturable

Uncovered / ambiguous:
- What happens to the auth hold on the released remainder? (needs confirmation)
- Is a zero capture amount valid? (assuming no)

Proposed tests:
- capture_succeeds_when_amount_is_below_authorized
- capture_releases_remainder_when_partially_captured
- capture_fails_when_amount_is_zero

Contract changes:
- Relax amount rule to 0 < amount <= authorized (backward-compatible)

NFR budgets touched: none — no new external calls; authz surface unchanged

Hold-out: required — money-path amount semantics; asked the human for
1–2 sealed acceptance tests from the business spec (run once, after green);
result: pending

Files likely to change:
- payments/contract/openapi.yaml
- payments/domain/capture.* (+ tests)
```

The human resolves the ambiguous points, approves, and only then are the contract edit, the tests, and the code written. Had this introduced a `PARTIALLY_CAPTURED` state shared across services, step 4 would have added an ADR draft to the plan.
