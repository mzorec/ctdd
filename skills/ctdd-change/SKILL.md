---
name: ctdd-change
description: >-
  Drive a backend API or microservice change the Contract- and Test-Driven
  Development (CTDD) way. Use whenever the user asks to implement, add, modify,
  extend, or fix behavior in a backend service — an endpoint, handler, message
  consumer, domain rule, or bug — even if they never say "CTDD" or mention
  tests. Reads the existing API contract and relevant tests before designing
  anything, produces a reviewable pre-coding implementation plan, gates coding
  on approval, and prompts for an Architecture Decision Record (ADR) on
  structural decisions. Also use for standalone ADR requests ("write an ADR",
  "record this decision"). Triggers include "implement this endpoint", "add
  this to the service", "change this API", "fix this bug in the service",
  "modify this handler", "plan this backend change", "migrate this flow", "refactor this
  service", "raise or change this limit or rule", "implement the review
  comments on my PR", "address the reviewer's feedback", "deprecate a field
  in an event schema", "stage a contract or event-schema rollout", "CTDD
  this". Not for
  visual/UX correctness (testable state logic qualifies wherever it lives),
  not for infrastructure/build/deploy config (Dockerfiles, pipelines, cluster
  manifests), not for test-only tasks (use ctdd-tests), and not for reviewing
  an existing diff or PR (use ctdd-review).
---

# CTDD: driving a backend change

**Use this skill when the unit of work is a change** — a feature, endpoint, handler, message consumer, or bug to build or modify. It owns the whole workflow and every non-test artifact: the design plan, the ADR (structural decisions), the API contract, the consumer contract, and the pre-coding implementation plan. When it is time to write or review tests, it hands off to the `ctdd-tests` skill for the test craft. If the task is *only* about tests — writing tests in isolation, or reviewing/fixing existing tests, with no feature being built — use `ctdd-tests` directly instead.

Follow Contract- and Test-Driven Development. The direction is the inverse of prose-spec-driven development: the API contract and tests come first and the technical prose spec is *derived from them*, not written up front. Tests are the executable spec for **preservation** ("don't break what exists"); the business requirement plus the plan are the spec for **creation** ("what to build").

One clarification the name invites: **"contract-first" means the boundary is specified before tests and implementation — not before understanding.** Always read what exists before designing what changes.

Scope: services behind an API — and the real line is *assertable correctness*, not the deployment tier. Don't apply it where correctness is visual or experiential; testable state logic (reducers, routing, client-side state machines) qualifies wherever it lives.

## Workflow

Work through these steps in order. Scale ceremony to the risk of the change — a one-line fix skips most of this; a change to a state machine or a service boundary does all of it. On non-trivial changes, **nothing is written to disk — no contract edit, no ADR, no test, no code — until the implementation plan (step 6) is approved**; steps 3–5 produce drafts that ride inside the plan. **Scaling down is visible, never silent:** when you judge a change trivial and skip the gate, first output one line — `Risk: trivial — <reason>. Skipping the plan gate.` — so the human can veto the classification before you touch a file. Two changes are never trivial regardless of size: an edit to an existing test, and any contract-file edit — "just updating a test" is a spec change. Where a diff already exists, `scripts/check-spec-surface.py` is the deterministic counterweight to this call: if it reports touched test or contract surface, the change is not trivial.

1. **Confirm intent.** Restate the business requirement (what the customer/caller needs) in one or two sentences. This is the source of what to build. If it's ambiguous, ask before proceeding.

2. **Read what exists.** Retrieve the relevant slice of the API contract and tests — by route, message type, module, changed files, domain terms, or failing tests — not the whole suite. Summarize the current behavior so you and the developer share an accurate model of what exists. Present this summary as "here's my reading — correct me," never as ground truth. For a greenfield service there is nothing to read — say so and move on; the contract and the plan carry the spec, and everything written in steps 5–7 becomes its seed.

3. **Design plan (brief).** State the approach, the shape of the change, what's explicitly out of scope, and the riskiest part. If the developer already gave direction, capture theirs rather than inventing a competing one. Keep it short — it lives in the PR description, not a maintained doc.

4. **ADR — only for a structural decision.** If the change touches a service boundary, a cross-service contract, a data-ownership line, or any architecture choice with real tradeoffs, draft an Architecture Decision Record. See "ADR rules" below. If it's an ordinary behavior change, skip this.

5. **Draft the contract change.** Design the API contract delta (OpenAPI/JSON Schema for REST, protobuf/gRPC IDL, AsyncAPI for events) before tests or implementation — the contract is the boundary spec the service and its consumers build against. State whether it's backward-compatible; flag breaking changes explicitly. For a change that affects another service, include the consumer-driven contract update (e.g. Pact) so both sides are pinned and a breaking change fails in CI, not in production.

6. **Implementation plan — STOP for review.** Assemble the plan (format below) and stop. For anything beyond a trivial change, wait for a human to review and approve it before touching a file. This is the cheapest place to catch a wrong **direction** — and that is all it catches: at plan time the test encodings don't exist, so a shared misunderstanding in assertion bodies or fixtures sails through this gate. That half is handled at step 9's review of the tests as the spec and, for load-bearing changes, by the hold-out line in the plan format below. For high-risk changes, suggest the human switch to plan mode if the session isn't already in it — it makes this gate mechanical, and the plan presented for approval already contains the proposed contract diff and test names.

7. **Write the tests and apply the contract.** After approval: apply the contract change, then write behavior-level tests for the new behavior — new behavior has no tests yet, so this is where its spec is created. Write them at the behavior level (defer to the `ctdd-tests` skill for the discipline). Reach for property-based tests where an invariant applies (idempotency, ordering, validation, terminal-state rules).

8. **Implement until the contract validates and the tests are green.** Do not weaken a test to make it pass; if a test is wrong, fix the test as a spec change and say so.

9. **Present the spec for human review.** When green, present the diff with the tests and the contract framed as the spec, not just the code: changed tests are changed requirements, contract diffs are boundary changes, and both deserve explicit attention in review. If `scripts/check-spec-surface.py` is available, run the diff through it (`git diff --name-status -M | python3 scripts/check-spec-surface.py -`) and include its output: any test or contract surface it reports that the plan didn't declare — or declared trivial — means stop and reclassify before review. If the plan recorded a hold-out as required, this is when it runs: ask the human to execute the sealed tests now, after green, treat their result as part of this review, and update the plan's hold-out line to `passed`, `failed`, or `declined by human` — a result left `pending` at merge is a review finding. The `ctdd-review` skill drives the reviewer's side of this gate.

10. **Invariant note — only where needed.** If a rule is universal or a boundary is intentionally undefined and can't be made executable, add one colocated sentence (docstring/contract comment), e.g. "Must hold for all N > 0; behavior for N ≤ 0 is intentionally undefined." Do not write prose for anything a test or contract already covers.

### Bug fixes

A bug fix runs the same loop, compressed. Confirm the *expected* behavior (step 1), read the slice (step 2), then write a failing behavior-level regression test that reproduces the bug — that test *is* the spec of the fix — and implement until it's green. The test stays forever; that is how the suite accumulates edge cases. (The regression-test rule itself lives in `ctdd-tests`; this section owns only the workflow around it.) The plan gate usually collapses to a sentence ("failing test X reproduces it; fixing Y"). One caution: if an existing test asserts the buggy behavior *on purpose*, this is not a bug fix but a spec change — stop and run the full gate (step 6), calling out the test change explicitly.

### Amendments — the everyday case

Most real changes modify behavior an existing test asserts — neither pure preservation nor pure creation. Route these as spec changes, not code changes: the business requirement overrides the old test, and only through a reviewed diff. The plan must show each affected test's old and new assertion (see the plan format); the gate and the step-9 review do most of their real work here. The reflex to resist by name: "update the test to match" turns a spec change into a silent one.

### When artifacts disagree

A contract that allows what a test rejects, an example test contradicting a property test, a Pact expecting a shape the contract dropped — a cross-artifact conflict is a **detected spec bug**, not a tiebreak. Stop, decide which artifact is wrong against the business intent, and fix it as a reviewed spec change. Rough diagnostics: a Pact failure has the highest blast radius (a consumer is involved); contract-vs-test usually means validation isn't wired; example-vs-property means the generator found the example's lie. The one forbidden move is quietly adjusting whichever artifact is easiest to change until CI goes green.

### Standalone ADR requests

When the ask is only to record a decision ("write an ADR for choosing RabbitMQ over Kafka"), skip the workflow and apply the ADR rules directly: interview for context, decision, and consequences where they aren't given; find the next number in the ADR directory; write the file from the template.

## The implementation plan (output before coding)

Produce this as a reviewable summary, then stop for approval on non-trivial changes:

- **Risk level** — trivial / normal / high-risk, with one line on why. This is the justification for the ceremony being scaled up or down; a reviewer who disagrees with the risk call should be able to object to that before anything else.
- **Existing behavior** found in the contract and relevant tests — cite the file paths and test names actually retrieved (evidence, not paraphrase), so thin retrieval is visible to the reviewer. State known gaps explicitly — "no Pact found for the checkout caller" converts silence into a reviewable absence.
- **Assumptions** you are making.
- **Uncovered or ambiguous cases** — behavior that matters but isn't pinned by a test, and anything the requirement doesn't specify.
- **Proposed new/changed tests** — named at the behavior level. For each *changed existing* test, show the old and the new assertion, not just the name — the name is exactly where a wrong encoding hides.
- **Contract changes**, if any (and whether they're backward-compatible; flag breaking changes explicitly).
- **NFR budgets this change could touch** — latency/throughput, authz surface, tenant isolation, retention/audit. State "none" explicitly; an unstated budget is not a free one.
- **Hold-out** — required / not required, with why. Required when the change alters money, auth, state-machine, or boundary semantics (rounding, inclusivity, timezones, fee treatment). If required, ask the human to write 1–3 acceptance tests directly from the business spec and to withhold them from you; they run once, after green (sealing them is the team's CI job — see the README). Record the decision **and track its outcome**: write `result: pending` at plan time; step 9 updates it to `passed`, `failed`, or `declined by human`. Never proceed as if this step happened when it didn't — and never leave it `pending` past review.
- **ADR draft**, if step 4 produced one.
- **Files likely to change.**

Treat a change to an existing test as a change to the spec — call it out for review. If this plugin's `scripts/check-plan.py` is available on disk, run the emitted plan through it — adding `--diff` with the current `git diff --name-status -M` once edits exist, so a trivial claim is cross-checked against the actual surface — and fix any missing sections before presenting.

### Example (condensed)

Request: *"Add partial capture to the payments service — allow capturing less than the authorized amount."*

```
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
- payments/domain/capture.*  (+ tests)
```

The human resolves the ambiguous points, approves, and only then are the contract edit, the tests, and the code written. Had this introduced a `PARTIALLY_CAPTURED` state shared across services, step 4 would have added an ADR draft to the plan.

## ADR rules

An ADR is a short record (a page or less) of one significant decision, in three parts: **context** (the situation and forces), **decision** (what was chosen), **consequences** (what was accepted, good and bad). Scaffold new ADRs from `references/adr-template.md` in this skill's folder.

- Store as a numbered, append-only file, e.g. `docs/adr/0007-payments-in-domain-layer.md`.
- **Append-only:** never edit a past ADR to reflect a new decision. If a decision is reversed, write a new ADR that supersedes the old one and mark the old one "Superseded by NNNN". The record is what was believed *at the time*.
- Capture the decision and its tradeoffs, not a description of current behavior. The moment it narrates what the code does, it has drifted into spec territory — stop.

## Guardrails

- Untested behavior is not permission to change it. If you propose altering behavior in a thinly-covered area, flag it for extra human attention rather than trusting a green suite. Consider adding characterization tests first (the `ctdd-tests` skill defines the discipline: `currently_*`-marked observations, distinct from intent).
- For distributed-systems logic (async messaging, eventual consistency, retries, ordering, partial failure), treat it as the dangerous core and escalate rigor: property tests, contract tests at the messaging boundary, and human review. Don't rely on example tests alone here.
- Keep the customer's business spec as the source of intent — this workflow replaces the hand-written technical implementation spec, not the business requirement.
