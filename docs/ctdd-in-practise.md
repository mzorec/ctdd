# CTDD — a first-timer's guide

*Contract- and Test-Driven Development for backend services, in about ten minutes.*

This is the short version. The full argument — where the method breaks, how it compares to spec-driven development, the evidence — lives in `rationale.md`. The plugin's operating manual (installation, CI recipes, tuning) is the README. This primer is deliberately concept-level, so it stays true across releases.

## The problem it solves

You're building a backend service, and an AI coding agent (or a new colleague) is doing much of the implementation. The standard answer is: write a technical spec first, keep it as the source of truth, implement against it.

Two things go wrong with that, and every team has lived both. First, **drift**: the spec is a second codebase with no failure signal. Code changes; nothing forces the document to change with it; you discover it's wrong only when someone relies on it. A stale test fails in CI within one run. A stale spec paragraph fails silently, months later, and the blame lands on whoever trusted it. Second, **incompleteness**: many edge cases don't exist until you build the thing — the null in the middle of the batch, the retry after a partial write, two requests racing. A spec written before the code is structurally incomplete, not from laziness, but because the information wasn't there yet.

So the maintained technical prose spec is an artifact that starts incomplete and then rots. CTDD's move is to stop maintaining it.

## The idea in one paragraph

For a service behind an API, two artifacts already say what it does — and they can't silently lie, because they execute. The **API contract** (OpenAPI, protobuf, AsyncAPI) fixes the shape at the boundary; **behavior-level tests** fix the behavior. CTDD treats those as *the* spec. The agent reads them and builds against them; when a human needs a prose summary, the agent derives one on demand — the spec becomes an **output**, not an input. The customer's **business spec stays** as the source of intent, and a short **disposable plan** carries the "why" of each change before it's built.

One naming note, because it prevents a real confusion: read it as contract-*and*-test-driven — driven by both artifacts. It is **not** "contract-test-driven": contract testing (Pact, Specmatic-style) verifies the boundary's *shape* and is one ingredient here; the behavior tests carry the *semantics*, which no schema can generate.

In practice you stop, keep, and start:

- **Stop** writing and maintaining a technical implementation spec for the agent.
- **Keep** the customer's business spec (intent), and your engineering artifacts — they were always worth having.
- **Start** treating a test diff as a requirements diff, and reviewing it that way.

## What "the spec" is made of

| Artifact | Answers | Why it can't rot |
|---|---|---|
| Business spec | What does the customer need? | External, owned by the business — it *is* intent |
| API contract | What shape is the boundary? | Validated at runtime and in CI — a violating payload fails |
| Behavior tests | What does the service do now? | A wrong one fails the build |
| Plan (per change) | Why this change, what shape? | Disposable — folds into the PR, never maintained |
| ADRs | Why is the structure this way? | Append-only records of decisions — never edited, so never stale |
| Property tests / Pact | What must *always* hold? What do consumers rely on? | Executable universals; verified on both sides in CI |

The key move: **humans don't read the whole test suite.** The agent retrieves the relevant slice, holds it in context, and summarizes — "here's my reading, correct me." Tests plus contract are the regression contract ("don't break what exists"); business spec plus plan supply creation ("what to build"); ADRs supply "why it's shaped this way."

## How a change actually runs

Say you ask: *"Add partial capture to the payments service — allow capturing less than the authorized amount."*

**1. The agent reads before it designs.** It retrieves the contract and the tests around capture — and cites what it read, so thin retrieval is visible. Nothing is drafted against a boundary nobody has looked at.

**2. It stops with a plan — before touching any file.** This is the heart of the workflow. You get something like:

```
Risk level: normal — single-service, backward-compatible; money path
Existing behavior (openapi.yaml; CaptureTests.*):
- POST /payments/{id}/capture requires amount == authorized
- capture_fails_when_amount_exceeds_authorized_amount covers over-capture
Known gaps: no consumer contract found for the checkout caller
Assumptions:
- Partial capture still moves the payment to CAPTURED
Uncovered / ambiguous:
- What happens to the auth hold on the released remainder?
- Is a zero capture amount valid? (assuming no)
Proposed tests:
- capture_succeeds_when_amount_is_below_authorized
- capture_releases_remainder_when_partially_captured
- capture_fails_when_amount_is_zero
Contract change: relax rule to 0 < amount <= authorized (compatible)
Hold-out: required — money-path amount semantics; result: pending
```

*(Condensed — the plugin's full format has a few more mandatory lines.)*

**3. You answer the ambiguities and approve.** This gate is the cheapest place to catch a wrong *direction* — you're reviewing intent before any code exists to anchor you. Two minutes here beat two hours of untangling a green-but-wrong implementation.

**4. Only then: contract applied, tests written, code implemented until green.** The new tests *are* the new spec being created — writing them is the specification act.

**5. Review reads the tests and contract as the spec**, not just the code. A changed test is a changed requirement and gets called out as one. For money and auth paths, the plan asked a human to write one or two **hold-out tests** straight from the business spec, kept where the agent can't read them; they run now, after green — the one guard that works when the visible tests and the code share the same misunderstanding.

Two more flavors, briefly. A **bug fix** runs the loop compressed: write the failing behavior-level regression test that reproduces the bug — that test *is* the spec of the fix — then fix, and the test stays forever; that's how the suite accumulates edge cases. An **amendment** — the everyday case on a mature service — changes behavior an existing test asserts. Suppose the business now allows 10% over-capture for shipping adjustments: `capture_fails_when_amount_exceeds_authorized_amount` is simultaneously the rule being violated and the place the new rule gets written. CTDD's answer: the business requirement overrides the old test, **but only through a reviewed diff** showing the old and new assertion. The reflex to unlearn is "just update the test to match" — that's a requirements change dressed as housekeeping.

## The one rule that makes it work

Write tests at the **behavior level** — what a caller observes — and name them as statements of intent, because *the name is the spec line*:

```
returns_404_when_payment_does_not_exist
rejects_capture_when_payment_is_not_authorized
publishes_payment_completed_event_after_successful_capture
is_idempotent_when_the_same_command_is_retried
```

Not the implementation level:

```
calls_repository_once
invokes_mapper
uses_payment_status_validator
```

The test for the test: **if a correct refactor that preserves behavior breaks it, it's at the wrong altitude** — it's asserting wiring, not the contract. And beware mock-heavy tests: a test that mostly verifies collaborator calls is describing wiring even when its name sounds behavioral. This discipline is the whole method's foundation, and it's where CTDD fails *quietly* — an agent reading brittle tests as spec will faithfully preserve the brittleness.

## Where it applies — and the honest floor

The real scope line is **assertable correctness**: use CTDD wherever "correct" can be captured in an executable assertion. Backend APIs and microservices are the home case — request in, response out; given state, an operation produces new state. Don't stretch it over visual/UX correctness, where tests structurally can't assert "looks right" (though a frontend's testable state layer — reducers, client-side state machines — qualifies fine).

And the floor, stated plainly because it's the most decision-useful sentence here: **CTDD assumes an existing testing culture; it does not create one.** It takes a team from roughly the 70th percentile to the 90th, not from the 30th to the 70th. Every safeguard in it is made of behavior-level-testing discipline, so none of them can substitute for it. A team that can't yet write behavior-level tests should build that muscle on ordinary TDD first.

## Where it's honestly weak

The method's credibility rests on naming its own breaks. The short list (the full treatment — eight weaknesses, mitigations, and the observable "it's failing" signals — is Part 2 of the rationale):

- **Tests are a sample, not a universal.** The agent can't tell guaranteed behavior from accidentally-true behavior. Mitigation: property-based tests for real invariants; treat the agent's summary as a claim to correct, never ground truth.
- **A suite can't say "undefined on purpose."** Silence looks like an oversight. Mitigation: one colocated sentence where a boundary is deliberate — and only there.
- **Circularity.** The agent can write a wrong test and wrong code that agree — suite green, everyone happy. Mitigation: the plan gate (wrong direction), humans reviewing *tests* as the spec (wrong encoding), and hold-outs for the load-bearing paths.
- **Untested behavior reads as permission.** The safety net has exactly your coverage's holes. Mitigation: characterization tests (marked as observations, not intent) before risky refactors; Pact at service boundaries.
- **Performance, security, and audit requirements have no natural executable home.** Mitigation: give them explicit homes — executable where possible (a contract-derived authorization matrix is often the highest-value test artifact per hour in a role-based service), honest prose residue where not.

## Four questions first-timers ask

**Isn't this just TDD with extra steps?** It's TDD taken seriously plus three things it lacked: the API contract as a machine-readable boundary spec, an agent as the designated *reader* of the suite, and ADRs so structure isn't accidentally "improved" away. Fairest description: the floor promoted to a method — assembled from parts with twenty years of evidence, which is more than most 2026 spec-driven tooling can claim.

**If tests are the spec, where does a *new* feature's spec come from?** From the business requirement, the plan, and the contract you design first. Tests specify *preservation*; for creation, writing the tests *is* writing the spec — which is exactly why the plan gate matters most on new work: a wrong new test is a wrong spec.

**What stops the AI from gaming its own tests?** Nothing automatic — that's the circularity weakness, named openly. The guards are layered: a human approves intent before code exists, reviews the tests as requirements after, and for money/auth writes hold-outs the agent never sees. Independence you can't fake with "a second agent" — same model, same blind spot.

**Do we stop writing documentation?** No. The business spec stays. ADRs record why the architecture is shaped as it is. One-line invariant notes mark deliberate boundaries. What dies is specifically the *maintained technical prose spec* — the document that starts incomplete and rots. When someone needs prose, the agent derives it from the artifacts that can't lie.

## Where to go next

Try it on one real change: the plugin's README covers installation and a quick start — ask for a backend change in plain language and see the plan gate appear. The rule of thumb for daily use: *default to CTDD for services behind an API; make the contract the boundary spec; add Pact the moment services depend on each other; layer property tests where invariants are real; and match the ceremony to the cost of being wrong.* When you want the full argument — the eight weaknesses, the comparison against Spec Kit, Kiro, and Tessl, and what evidence would prove the method is failing — read `rationale.md`. It's long because it was built to survive hostile review; this primer is short because you weren't the hostile reviewer.
