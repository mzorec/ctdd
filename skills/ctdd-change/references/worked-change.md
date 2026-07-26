# Worked change

Load this file only at `SKILL.md` step 4.1. Copy these shapes; the plan body itself is in `plan-format.md`.

Request: `Add partial capture to the payments service.` Repository: dirty only with the requester's own unrelated edit to `README.md`; branch `feature/partial-capture` off `main`.

## Step 0 — baseline

```
Baseline: branch=feature/partial-capture; target=main; diff-base=a1b2c3d; staged=none; unstaged=README.md; untracked=none.
```

`README.md` is not a target file of this change, so it is reported and left alone rather than treated as contamination of the change surface.

## Step 1 — intent

```
Business requirement: The merchant is allowed one capture below the authorized amount, and the released remainder is never capturable.
```

## Step 2 — current behavior

```
Current behavior:
- `payments/contract/openapi.yaml` — `POST /payments/{id}/capture`: requires capture amount equal to the authorized amount.
- `tests/payments/CaptureTests.cs::capture_fails_when_amount_exceeds_authorized_amount`: over-capture returns 400.
- `tests/payments/CaptureTests.cs::capture_succeeds_when_amount_equals_authorized_amount`: full capture returns 200 and emits `PaymentCaptured`.
Correct this reading before I plan.
```

The contract and the tests state the rule. `CaptureService.cs` is read only for the remainder handling that neither states.

## Step 3 — classification

```
$ python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git a1b2c3d
check-spec-surface: empty input — nothing was inspected, so no verdict is given. If the diff really is empty, pass --allow-empty.
```

No diff exists yet, so 3.2 fails and the change is plan-gated. No trivial declaration is emitted.

## Steps 4–5 — plan

The plan is written to `docs/plans/PAY-123-partial-capture.md` using `plan-format.md`, whose complete example is this change.

```
$ python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" "${CLAUDE_PROJECT_DIR}/docs/plans/PAY-123-partial-capture.md"
check-plan: all mandatory sections present (presence, not quality — the review still owns quality).
```

`docs/plans/` is tracked here, so the plan file is committed and the MR description carries one line:

```
CTDD-Plan: docs/plans/PAY-123-partial-capture.md
```

## Step 6 — gate

The complete plan is printed verbatim, followed by its path. Nothing else is written. The BLOCKING question is answered by the human in the same turn as the approval:

```
Human: release the remainder when the authorization expires. Approved.
```

```
Approved by: "release the remainder when the authorization expires. Approved."; plan: docs/plans/PAY-123-partial-capture.md.
```

The answer is written into the plan in place of the BLOCKING question before the record is printed, because approval authorizes the plan file and an approved file must not still ask a question. It changed no risk, contract, test, or file entry, so the checker did not have to run again; an answer that changed any of them would return the plan through 5.4 and 6.1.

## Step 7 — artifacts and evidence

Contract first, then pins, then new-behavior tests.

```
$ python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" \
    "${CLAUDE_PROJECT_DIR}/docs/plans/PAY-123-partial-capture.pinstate.log" \
    --tests-from "${CLAUDE_PROJECT_DIR}/docs/plans/PAY-123-partial-capture.md" --expect-pass
check-redstate: all 4 pin test(s) observed PASSING against the current implementation — preservation baseline captured. Re-run the same tests after the change; they must still pass.
```

The four pins pass against the unmodified service: that is what makes them pins. They are re-run unchanged after implementation.

```
$ python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" \
    "${CLAUDE_PROJECT_DIR}/docs/plans/PAY-123-partial-capture.redstate.log" \
    --tests-from "${CLAUDE_PROJECT_DIR}/docs/plans/PAY-123-partial-capture.md"
check-redstate: all 4 new test(s) observed failing — red state verified. (That they failed for the *right* reason is still the reviewer's read.)
```

Two of the four did not reach that verdict on the first run, and each was resolved by its **Evidence states** row before step 8 began:

- `capture_fails_when_released_remainder_is_recaptured` did not compile: `CaptureService.ReleasedRemainder` did not exist. A compile-only member that throws not-implemented was added, the test re-run, and the failure became the planned assertion failure. Nothing else was implemented.
- `capture_succeeds_when_amount_is_one_cent` passed on the first run. Premature green: the fixture authorized one cent, so the old equality rule already accepted it and the test did not constrain the change. The corrected fixture went back through step 6 as an amendment before it was accepted as evidence.

## Step 8 — implement and verify

Implementation follows the `Implementation slices` order, one slice per named test.

```
$ dotnet test --filter CaptureTests   => 10 passed, 0 failed
$ dotnet test                         => 412 passed, 0 failed
$ dotnet build                        => exit 0
$ spectral lint payments/contract/openapi.yaml => no errors
$ python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git a1b2c3d
Verdict: SPEC SURFACE TOUCHED — changed tests are changed requirements, contract diffs are boundary changes, and this change is not trivial whatever the plan's risk line says. (exit 1 = attention, not error)
```

The inventory lists `payments/contract/openapi.yaml` and `tests/payments/CaptureTests.cs`, both in `Files likely to change`, so nothing is reopened.

### When the specification turns out to be wrong

Implementing the released-remainder guard showed that `CAPTURED` is terminal in the state machine, so the approved `Intended behavior` was unreachable. Step 8.6 fired: implementation stopped, the plan file was amended with the old and new form of the transition, `check-plan.py` was re-run, the amended plan was re-presented at step 6, and a second Approval record was printed. Work resumed at step 7 because the amendment changed a planned test. The amendment is never applied by editing the test to match the code.

## Step 9 — review packet

```
Business requirement: The merchant is allowed one capture below the authorized amount, and the released remainder is never capturable.
Back-translation: Capture accepts any amount from one cent to the authorized amount, emits exactly one event carrying that amount, and rejects a second capture with 409.
Plan: docs/plans/PAY-123-partial-capture.md
Approval: "release the remainder when the authorization expires. Approved."
Plan check: check-plan: all mandatory sections present
Red state: check-redstate: all 4 new test(s) observed failing — red state verified. (That they failed for the *right* reason is still the reviewer's read.)
Pin state: check-redstate: all 4 pin test(s) observed PASSING against the current implementation — preservation baseline captured.
Spec surface: Verdict: SPEC SURFACE TOUCHED — ... (exit 1 = attention, not error)
Verification: dotnet test --filter CaptureTests => 10 passed; dotnet test => 412 passed; dotnet build => exit 0; spectral lint payments/contract/openapi.yaml => no errors
Hold-out: passed
Residual risk: The released remainder's expiry path is exercised only by the sealed hold-out.
```

`ctdd-review` is then invoked on the final diff. Its verdict is not written here.

## Lane variants

| Lane | What differs |
|---|---|
| Bug fix | Same sections, kept to one line each. The regression test is a new-behavior test and must be observed red; the behavior it protects gets a pin. Never the trivial lane. |
| Trivial | Only through 3.2–3.5: an existing diff, checker exit `0`, code-only, covered by named tests. Emit the declaration, go to step 8, and produce the packet with `Plan: n/a — trivial`. |
| Structural decision | Step 4.3 fires: the ADR fields are drafted inside the plan and the ADR file is written at step 7.3, never before approval. |
| Contract or event-schema change | `Contract changes` names compatibility, consumers, and rollout; the plan names a serialization case; the contract file is written at step 7.3 before the tests are run. |
| Preservation-only refactor | `New-behavior tests: none — behavior is unchanged` on the heading line. Steps 7.10–7.12 are skipped, `Red state: n/a — plan declares none` in the packet, and the pins carry the whole proof. |
| Review-feedback implementation | Enters at step 0 with the review as input. Feedback inside approved scope is implemented under the existing plan; feedback outside it fires 8.6. |
| Standalone ADR | The change workflow does not run. `SKILL.md` **Standalone ADR procedure** only. |
