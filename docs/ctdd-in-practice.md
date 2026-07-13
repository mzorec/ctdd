# CTDD — a first-timer's guide

Contract- and Test-Driven Development for backend services, in about ten minutes.

This is the short version. The full argument — where the method breaks, how it compares to spec-driven development, and the reasoning behind it — lives in `ctdd-in-depth.md` (the rationale, in the plugin's doc-homes split). The operating manual — installation, CI recipes, and tuning — is the README. This guide stays concept-level so it remains true across releases.

## The problem it solves

You're building a backend service, and an AI coding agent (or a new colleague) is doing much of the implementation. The standard answer is: write a technical spec first, keep it as the source of truth, and implement against it.

Two things go wrong with that, and every team has lived both.

First, **drift**: the spec is a second codebase with no failure signal. Code changes; nothing forces the document to change with it; you discover it's wrong only when someone relies on it. A stale test fails in CI within one run. A stale spec paragraph fails silently, months later, and the blame lands on whoever trusted it.

Second, **incompleteness**: many edge cases don't exist until you build the thing — the null in the middle of the batch, the retry after a partial write, two requests racing. A spec written before the code is structurally incomplete, not from laziness, but because the information wasn't there yet.

So the maintained technical prose spec is an artifact that starts incomplete and then rots. CTDD's move is to stop maintaining it.

## The idea in one paragraph

For a service behind an API, two artifacts already say what it does — and they can't silently lie, because they execute. The API contract (OpenAPI, protobuf, AsyncAPI) fixes the shape at the boundary; behavior-level tests fix the behavior. CTDD treats those as the spec. The agent reads them and builds against them; when a human needs a prose summary, the agent derives one on demand — the spec becomes an output, not an input. The customer's business spec stays as the source of intent, and a short disposable plan carries the "why" of each change before it's built.

One naming note, because it prevents a real confusion: read it as **contract-and-test-driven** — driven by both artifacts. It is not "contract-test-driven": contract testing (Pact, Specmatic-style) verifies the boundary's shape and is one ingredient here; behavior tests carry the semantics, which no schema can generate.

In practice you stop, keep, and start:

- **Stop** writing and maintaining a technical implementation spec for the agent.
- **Keep** the customer's business spec (intent), and your engineering artifacts — they were always worth having.
- **Start** treating a test diff as a requirements diff, and reviewing it that way.

## Why this helps the agent

An AI agent is weakest when the prompt gives it only a goal:

> Implement partial capture.

From that, it has to infer everything else from code structure, naming, conventions, and maybe stale docs — and inference is where agents quietly go wrong.

CTDD gives the agent better inputs:

- the **API contract** tells it what the boundary must look like;
- the **relevant tests** tell it what behavior already exists and must not break;
- the **business request and plan** tell it what should be added or changed;
- **ADRs and invariant notes** tell it which design choices are intentional;
- **Pact and property tests** tell it what consumers and universal rules rely on.

So the agent is no longer reading code and guessing intent. And the workflow makes it show its work — before writing code it must say:

- what existing behavior it found;
- what it thinks the change means;
- which tests or contracts will change;
- which assumptions may be wrong;
- where coverage or consumer contracts are missing.

That summary is offered as "here's my reading — correct me," and the plan gate is where you do. This is the practical value of CTDD: before the agent writes any code, it exposes its understanding of the requirements — while a misunderstanding is still cheap to fix.

## What "the spec" is made of

| Artifact | Answers | Why it can't rot |
|---|---|---|
| Business spec | What does the customer need? | External, owned by the business — it is intent |
| API contract | What shape is the boundary? | Validated at runtime and in CI — a violating payload fails |
| Behavior tests | What does the service do now? | A wrong one fails the build |
| Plan, per change | Why this change, what shape? | Disposable — folds into the PR, never maintained |
| ADRs | Why is the structure this way? | Append-only records of decisions — never edited, so never stale |
| Property tests / Pact | What must always hold? What do consumers rely on? | Executable universals; verified on both sides in CI |

A few terms, in plain English:

- **ADR**: a short architecture decision note — why a boundary, pattern, or structural choice exists.
- **Pact**: a consumer contract test — one service states what it expects from another, and CI verifies the provider still satisfies it.
- **Property test**: a test that checks a rule across many generated inputs, not just one example.
- **Regression contract**: the current behavior that must not break unless a human approves changing it.

The key move: humans don't read the whole test suite — the agent retrieves the relevant slice and mediates. Tests plus contract are the regression contract ("don't break what exists"); business spec plus plan supply creation ("what to build"); ADRs supply "why it's shaped this way."

## How a change actually runs

Say you ask:

> Add partial capture to the payments service — allow capturing less than the authorized amount.

### 1. The agent reads before it designs

It retrieves the contract and the tests around capture — and cites what it read, so thin retrieval is visible. Nothing is drafted against a boundary nobody has looked at.

### 2. It stops with a plan before touching any file

This is the first safety pause: you review intent while it is still cheap to correct. You get something like:

```text
Risk level: normal — single-service, backward-compatible; money path

Existing behavior (openapi.yaml; CaptureTests.*):
- POST /payments/{id}/capture requires amount == authorized
- capture_fails_when_amount_exceeds_authorized_amount covers over-capture

Known gaps:
- no consumer contract found for the checkout caller

Assumptions:
- Partial capture still moves the payment to CAPTURED

Uncovered / ambiguous:
- What happens to the auth hold on the released remainder?
- Is a zero capture amount valid? (assuming no)

Proposed tests:
- capture_succeeds_when_amount_is_below_authorized
- capture_releases_remainder_when_partially_captured
- capture_fails_when_amount_is_zero

Contract change:
- relax rule to 0 < amount <= authorized (compatible)

Hold-out:
- required — money-path amount semantics
- result: pending
```

This is condensed. The plugin's full format has a few more mandatory lines.

### 3. You answer the ambiguities and approve

The plan gate catches the wrong direction before code exists to anchor the discussion. Two minutes here beat two hours of untangling a green-but-wrong implementation.

### 4. Only then: contract, tests, code

The contract is applied, tests are written, and code is implemented until green. The new tests are the new spec being created — writing them is the specification act.

### 5. Review reads tests and contract as the spec

Review does not only ask, "Is the code clean?" It asks, "Do the changed tests and contract encode the right behavior?"

A changed test is a changed requirement and gets called out as one. For money and auth paths, the plan asks a human to write one or two independent hold-out tests straight from the business spec, kept where the agent can't read them. They run after the visible suite is green — the one guard that works when the visible tests and the code share the same misunderstanding.

## Two common variants

### Bug fix

A bug fix runs the loop compressed:

1. write the failing behavior-level regression test that reproduces the bug,
2. fix the code,
3. keep the test forever.

That test is the spec of the fix. This is how the suite accumulates edge cases.

### Amendment: changing existing behavior

An amendment is the everyday case on a mature service: the change modifies behavior an existing test already asserts.

Suppose the business now allows 10% over-capture for shipping adjustments. The test `capture_fails_when_amount_exceeds_authorized_amount` is simultaneously the old rule being violated and the place the new rule gets written.

CTDD's answer: the business requirement overrides the old test, but only through a reviewed diff showing the old and new assertion.

The reflex to unlearn is:

> just update the test to match

That is a requirements change dressed as housekeeping.

## What compounds

A prose spec decays as a byproduct of doing the work: every change can make it slightly less true, and nothing forces anyone to notice.

CTDD's artifacts are meant to move in the other direction. Every bug fix leaves a permanent regression test behind, so the suite accumulates edge cases the team has actually hit. Every well-run change adds retrievable spec, so the next change starts from a better-described system than the last one did. The contract stays honest where validation is wired, because a violating payload fails. The plan is disposable, but what survives it is supposed to land in durable artifacts: tests, contracts, and ADRs where structure changed.

That is the long-run bet: **the executable spec becomes richer as a byproduct of doing the work, instead of rotting as a byproduct of doing the work.**

The same accumulation is exactly why the next section matters. A suite of behavior-level tests compounds into an increasingly precise specification of observable behavior. A suite of brittle, implementation-coupled tests compounds into an increasingly precise description of the code as it happens to be written — which then blocks the refactor it should have protected. Accumulation is a multiplier on whichever discipline you actually have; it does not supply the discipline.

One caution about how to read this: this is a claim about mechanism, not a promise about outcomes. CTDD does not make code cleaner by itself. That remains design skill, refactoring judgment, and code review. What CTDD claims is narrower and checkable: when the method is followed on assertable behavior, the durable specification becomes richer over time, while a prose side-spec tends to decay.

## The one rule that makes it work

Write tests at the behavior level — what a caller observes — and name them as statements of intent, because the name is the spec line.

Good:

```text
returns_404_when_payment_does_not_exist
rejects_capture_when_payment_is_not_authorized
publishes_payment_completed_event_after_successful_capture
is_idempotent_when_the_same_command_is_retried
```

Not this:

```text
calls_repository_once
invokes_mapper
uses_payment_status_validator
```

The test for the test: if a correct refactor that preserves behavior breaks it, the test is at the wrong altitude. It is asserting wiring, not the contract.

Beware mock-heavy tests for the same reason. A test that mostly verifies collaborator calls is describing implementation wiring even when its name sounds behavioral. This discipline is the whole method's foundation, and it is where CTDD fails quietly: an agent reading brittle tests as spec will faithfully preserve the brittleness.

## Where it applies — and the honest floor

The real scope line is **assertable correctness**: use CTDD wherever "correct" can be captured in an executable assertion.

Backend APIs and microservices are the home case: request in, response out; given state, an operation produces new state. Don't stretch CTDD over visual or UX correctness, where tests structurally can't assert "looks right." A frontend's testable state layer — reducers, routing logic, client-side state machines — can qualify, but the visual layer usually does not.

And the floor, stated plainly because it's the most decision-useful sentence here: **CTDD assumes an existing testing culture; it does not create one.**

Every safeguard in it is made of behavior-level-testing discipline, so none of them can substitute for it. A team that can't yet write behavior-level tests should build that muscle on ordinary TDD first.

Cost-wise the method follows its own ceremony rule:

- a trivial change costs one declared line,
- a normal change costs a few minutes of plan review before code exists,
- a load-bearing change adds a human-written hold-out.

The weight tracks the cost of being wrong, not the size of the diff.

## Where it's honestly weak

The method's credibility rests on naming its own breaks. The full treatment — eight weaknesses, mitigations, and observable "it's failing" signals — is Part 2 of the rationale. For first-timers, these are the ones to remember.

**Tests are a sample, not a universal.** The agent can't tell guaranteed behavior from accidentally-true behavior. Mitigation: property-based tests for real invariants; treat the agent's summary as a claim to correct, never ground truth.

**A suite can't say "undefined on purpose."** Silence looks like an oversight. Mitigation: one colocated sentence where a boundary is deliberate — and only there.

**Circularity.** The agent can write a wrong test and wrong code that agree — suite green, everyone happy. Mitigation: the plan gate catches wrong direction, humans review tests as the spec to catch wrong encoding, and hold-outs cover load-bearing paths.

**Untested behavior reads as permission.** The safety net has exactly your coverage's holes. Mitigation: characterization tests, marked as observations rather than intent, before risky refactors; Pact at service boundaries.

**Performance, security, and audit requirements have no natural executable home.** Mitigation: give them explicit homes — executable where possible, honest prose residue where not. A contract-derived authorization matrix is often the highest-value test artifact per hour in a role-based service.

The two weaknesses you will hit most often in day-to-day work are:

1. **changed tests**, because they may be changed requirements;
2. **thin coverage**, because untested behavior looks unconstrained to the agent.

## Four questions first-timers ask

### Isn't this just TDD with extra steps?

It is TDD taken seriously plus three things classic TDD usually lacked:

1. the API contract as a machine-readable boundary spec,
2. an agent as the designated reader of the relevant suite,
3. ADRs so structure isn't accidentally "improved" away.

Fairest description: the floor promoted to a method — assembled from parts with twenty years of evidence, which is more than most 2026 spec-driven tooling can claim.

### If tests are the spec, where does a new feature's spec come from?

From the business requirement, the plan, and the contract you design first.

Tests specify preservation. For creation, writing the tests is writing the spec — which is exactly why the plan gate matters most on new work: a wrong new test is a wrong spec.

### What stops the AI from gaming its own tests?

Nothing automatic — that's the circularity weakness, named openly.

The guards are layered: a human approves intent before code exists, reviews the tests as requirements after, and for money/auth writes hold-outs the agent never sees. Independence cannot be faked with "a second agent" using the same model and same context.

### Do we stop writing documentation?

No.

The business spec stays. ADRs record why the architecture is shaped as it is. One-line invariant notes mark deliberate boundaries. What dies is specifically the maintained technical prose spec — the document that starts incomplete and rots.

When someone needs prose, the agent derives it from the artifacts that can't lie.

## Try it first

Try CTDD on one real backend change. The plugin README covers installation and quick start.

Ask for the change in plain language and look for the plan gate:

> Add partial capture to the payments service.

The agent should read the relevant contract and tests, summarize existing behavior, list assumptions and gaps, propose tests, and stop before touching files.

## Rule of thumb for daily use

Default to CTDD for services behind an API, where the team already has behavior-level testing discipline.

Make the contract the boundary spec. Add Pact the moment services depend on each other. Layer property tests where invariants are real. Match the ceremony to the cost of being wrong.

## Read deeper later

When you want the full argument — the eight weaknesses, the comparison against Spec Kit, Kiro, and Tessl, and what evidence would prove the method is failing — read `ctdd-in-depth.md`.

The in-depth rationale is long because it defends the method under hostile review. This guide is short so you can try it on one real change.
