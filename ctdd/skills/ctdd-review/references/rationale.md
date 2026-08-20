# CTDD review rationale

This file explains the choices behind `../SKILL.md`. It is not procedure and is not loaded during a review.

## Role separation
Review and authoring are separate jobs because silent fixes erase the review record and let the author validate their own interpretation. `ctdd-review` therefore emits evidence-bounded findings; `ctdd-change` implements accepted findings; `ctdd-tests` owns isolated test craft.

## Complete surface and comparison base
A branch or PR compared only with `git diff` can hide commits already on the branch. An untracked test or contract file can be the entire specification delta. Fixing the base, inventorying every change status, and reading the full surface prevent the reviewer from proving a defect against the wrong change. `check-spec-surface.py` provides a deterministic inventory cross-check; it does not judge intent.

## Tests and contracts as proposed intent
Tests externalize expected behavior and contracts define boundaries other parties build against. Modifying or deleting either proposes a requirement change, but agreement between changed tests and code does not prove that proposal is correct. New behavior without a behavior-level test remains unconstrained for the next change. A structural ADR records the decision and tradeoffs rather than merely describing the resulting behavior.

## Circularity
A test and implementation can agree on the same wrong boundary, fee rule, or state transition. Back-translating load-bearing tests into plain requirement sentences and comparing those sentences with independently approved intent breaks that circularity. Reading all changed files before judging a suspicious line also catches guards, migrations, or compensation implemented elsewhere in the same diff.

## Evidence direction and verification
A raw test log proves only that a run occurred; the red-state checker establishes whether the planned tests were present and failed in the required direction. New-behavior tests need pre-implementation failure evidence because an immediately green test can pass for the wrong reason. Preservation pins and characterization observations run in the opposite direction: they establish old behavior by passing before and after the refactor. Thin coverage and distributed behavior weaken the meaning of a green suite, so they require explicit pins or stronger contract/property evidence.

## Risk, budgets, and hold-outs
The implementation risk label and whether a change is load-bearing are separate axes: a small payment-rule change can be normal implementation risk and still carry severe semantic consequences. State-machine, authorization, money, external-boundary, tenant, retention, and audit changes therefore retain budget and hold-out checks even when the plan calls them normal risk. A missing or failed required hold-out result is different from unavailable verification and is reported accordingly.

## Mandatory review dimensions
Correctness precedes formatting because an attractive diff can still violate behavior. Negative, boundary, failure, cancellation, compatibility, concurrency, persistence, security, observability, test-quality, and migration checks are mandatory because defects cluster outside the representative happy path. A dimension can be `not relevant` only after inspected evidence establishes that result.

## Findings, severity, and correction
False positives consume implementation effort and can teach the next change the wrong contract. Reproduction is strongest when available; static proof is sufficient when a complete control/data path and governing invariant establish the failure; inference remains useful only when confidence and missing verification are explicit. Severity follows observable impact, not reviewer alarm, diff size, or implementation complexity. The finding cites the defective changed line and the smallest correction so the consumer can act without repeating the review or being pushed into a redesign. Review length follows the number and impact of qualifying findings rather than pressure to produce commentary.

## Changed specification artifacts
A correct, acknowledged test or contract amendment remains visible in review scope and verification, but it is not a defect finding. It becomes a finding only when it conflicts with approved intent, creates an unhandled compatibility risk, weakens required detection, or lacks required change evidence. This keeps visibility without converting every legitimate requirement change into implementation work.

## Verification limits and no-findings
Unavailable infrastructure, broken harnesses, and ambiguous intent reduce confidence but do not prove the change is defective. Recording those limits preserves honesty without manufacturing findings. An explicit no-findings result is necessary because silence is indistinguishable from an incomplete review.

## Hold-out independence
Record the approved hold-out decision and any externally supplied result, but do not inspect sealed hold-out tests or expose implementation analysis to their author. Independence is lost once the reviewer can adapt hidden acceptance tests to the implementation.
