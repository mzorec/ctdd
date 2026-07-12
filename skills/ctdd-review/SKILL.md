---
name: ctdd-review
description: >-
  Review a code change — a PR, merge request, branch diff, staged changes, or
  pasted diff — for a backend API or microservice the Contract- and Test-Driven
  Development (CTDD) way. Use whenever the user asks to review, check, or
  judge a change before merge, even if they never say "CTDD". Reads the tests
  and the API contract as the spec, not just the code: changed tests are
  changed requirements, contract diffs are boundary changes, new behavior
  needs a behavior-level test, structural decisions need an ADR. Triggers
  include "review this PR", "review this MR", "review this diff", "review my
  changes", "check this before I merge", "CTDD review", "look it over", "check what
  the agent did", "sanity-check this diff before I open the PR", "review just
  the changed tests and contract in this PR". Not for reviewing tests in
  isolation outside any diff (use ctdd-tests — the test or contract portion
  of a diff belongs here), not for implementing changes or
  responding to review comments (use ctdd-change), not for one-off scripts or
  data migrations with no test or contract surface, and not for visual/UX-only
  changes (testable state logic qualifies wherever it lives).
---

# CTDD: reviewing a change

**Use this skill when the unit of work is a review** — a finished diff, produced by a human or an agent, to be judged before merge. It is the reviewer's side of the workflow: `ctdd-change` drives the author, `ctdd-tests` owns the test craft, and this skill checks that a change actually treats the tests and the contract as the spec. For reviewing tests in isolation, use `ctdd-tests`; this skill calls it for the test portion of a change.

The core stance: **read the spec artifacts first and the implementation second.** A diff to a test is a diff to the requirements. A diff to the contract is a change to a boundary other parties build against. Most review failures aren't bugs in code — they're spec changes nobody noticed were spec changes.

## Gather the change

Get the full diff before judging anything: `git diff` for staged or branch changes, the PR/MR diff via whatever tooling is available, or the pasted patch. If `scripts/check-spec-surface.py` is available, run the diff's name-status through it first (`git diff --name-status -M | python3 scripts/check-spec-surface.py -`) and report its output before anything else: renamed or deleted tests still count as spec changes until shown otherwise, and its inventory is the deterministic cross-check on the plan's risk call. Retrieve just enough surrounding context to judge it — the contract files it touches, the existing tests around the changed behavior, and the ADR index if structure moved. If an implementation plan exists (PR description, plan output), read it first: the review's first job is checking the change against its own stated intent and risk call.

## Review dimensions

Work through these in order — spec first, code second. Scale depth to the risk of the change, and challenge the author's risk call if the diff doesn't match it (a "trivial" diff that touches a state machine is misclassified, and that is itself a finding).

1. **Spec changes — modified or deleted tests.** Every one is a changed requirement. For each: is it acknowledged as a spec change, and is the new expectation right against the business intent? A test relaxed so that failing code passes is the highest-severity finding this skill can raise. A deleted test is a silently dropped requirement unless the deletion is justified.
2. **Boundary changes — contract diffs.** For OpenAPI/protobuf/AsyncAPI/Pact diffs: is compatibility stated, and stated correctly? Additive changes (new endpoints, new optional fields) are compatible; removals, type changes, and semantic changes to existing fields are breaking and need the consumer contract updated plus a migration story.
3. **Coverage of new behavior.** Every new observable behavior in the diff needs a behavior-level test naming it. List new behaviors without one as uncovered — untested behavior reads as unconstrained to the next agent that touches this code.
4. **Test quality.** Apply the `ctdd-tests` review checks (altitude, naming, mock weight, determinism, contract alignment) to the new and changed tests in the diff.
5. **Structure.** Does the diff touch a service boundary, data ownership, or cross-service semantics? Then an ADR should be present — or explicitly declined with a reason. Check the ADR records a decision and its tradeoffs, not a description of behavior.
6. **Risk areas.** Changes in thinly-covered code without characterization tests pinned first; distributed-systems logic (messaging, retries, ordering, partial failure) changed without property or messaging-contract tests. Both escalate severity — a green suite is weak evidence exactly here.
7. **Invariant notes.** If the change introduces a universal rule or an intentional gap that can't be executable, is the one-line colocated note present?
8. **Budgets and hold-outs.** If the diff plausibly touches a latency/throughput budget, the authz surface, tenant isolation, or retention/audit behavior — and no artifact states the budget — that is a finding, not a pass. For a high-risk change (money, auth, state machines, boundary semantics): was a hold-out recorded in the plan (required / requested / declined), and did it run? An absent record — or a result still `pending` at review time — is a finding.

## Report format

Order findings by severity, each tagged with a verdict:

- **spec-change** — a test or contract change that alters requirements (call it out even when it's correct; visibility is the point). Cross-artifact conflicts land here too: two spec artifacts disagreeing is a detected spec bug
- **needs-tests** — new behavior without a behavior-level test
- **needs-adr** — a structural decision without a record
- **boundary-risk** — a breaking or ambiguously-compatible contract change
- **test-quality** — findings delegated from `ctdd-tests`
- **risk-misclassified** — the diff doesn't match the plan's risk call; a "trivial" diff that touches a state machine is misclassified, and that is itself a finding. A high-risk diff with no plan at all lands here too
- **nit** — anything that doesn't gate the merge

Close with an overall verdict — **approve** / **approve-with-nits** / **needs-work** — plus the one or two things that most deserve the author's attention. Keep proportion: a three-line fix gets a three-line review.

## Guardrails

- Review the change that exists, not the change you would have written. Style preferences are nits, not findings.
- When a test change and a code change agree with each other, remember they can agree on the wrong thing — check the pair against the stated business intent, not against each other. This is the circularity failure mode, and review is the last gate that can catch it.
- Don't fix anything during the review. Findings go back to the author (`ctdd-change` is the fixing lane); silent fixes destroy the review record and merge the author and reviewer roles the method deliberately separates.
