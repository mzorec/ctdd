# CTDD: a first-timer's guide

Contract- and Test-Driven Development for backend services, in about ten minutes.

This is the short version. The full argument (where the method breaks, how it compares to spec-driven development, and the reasoning behind it) lives in `ctdd-in-depth.md`. The operating manual (installation, CI recipes, and tuning) is the README. This guide stays at the concept level, so it stays true across releases.

## The problem it solves

You're building a backend service, and an AI coding agent is doing a lot of the implementation. The standard advice is to write a technical spec first, keep it as the source of truth, and implement against it.

Two things go wrong with that, and every team has lived both.

The first is **drift**. A spec document is a second codebase with no failure signal. The code changes, nothing forces the document to change with it, and you find out it's wrong only when someone trusts it and gets burned. A stale test fails in CI within one run. A stale spec paragraph fails silently, months later, and the blame lands on whoever believed it.

The second is **incompleteness**. Most of the interesting edge cases don't exist until you build the thing: the null in the middle of the batch, the retry after a partial write, two requests racing. A spec written before the code is structurally incomplete, not because anyone was lazy, but because the information wasn't there yet.

So the maintained technical spec is a document that starts incomplete and then rots. CTDD's move is to stop maintaining it.

## The idea in one paragraph

For a service behind an API, two artifacts already describe what it does, and they can't quietly lie, because they execute. The API contract (OpenAPI, protobuf, AsyncAPI) fixes the shape at the boundary. Behaviour-level tests fix the behaviour. CTDD treats those two as the spec. The agent reads them and builds against them, and when a human needs a prose summary, the agent generates one on demand. The spec becomes an output, not an input. The customer's business spec stays as the source of intent, and a short, disposable plan carries the "why" of each change before it's built.

One naming note, because it heads off a real confusion. Read it as **contract-and-test-driven**, driven by both artifacts together. It is not "contract-test-driven": contract testing (Pact and similar) verifies the shape of the boundary and is one ingredient here, but the behaviour tests carry the meaning, which no schema can generate.

In practice, you stop one thing, keep two, and start one:

- **Stop** writing and maintaining a technical implementation spec for the agent.
- **Keep** the customer's business spec, which is your source of intent, and your engineering artifacts, which were always worth having.
- **Start** treating a change to a test as a change to a requirement, and reviewing it that way.

## Why this helps the agent

An AI agent is at its weakest when the prompt gives it nothing but a goal:

> Implement partial capture.

From that, it has to infer everything else from code structure, naming, conventions, and maybe some stale docs. Inference is exactly where agents quietly go wrong.

CTDD gives it better inputs. The API contract tells it what the boundary has to look like. The relevant tests tell it what behaviour already exists and must not break. The business request and the plan tell it what to add or change. ADRs and invariant notes tell it which design choices are deliberate. Pact and property tests tell it what consumers and universal rules depend on.

So the agent stops reading code and guessing at intent. And the workflow makes it show its work: before it writes any code, it has to state what existing behaviour it found, what it thinks the change means, which tests or contracts will change, which of its assumptions might be wrong, and where coverage or consumer contracts are missing.

It offers that summary as "here's my reading, correct me," and the plan gate is where you do. This is the practical value of CTDD in one sentence: before the agent writes any code, it puts its understanding of the requirements in front of you, while a misunderstanding is still cheap to fix.

## What "the spec" is made of

| Artifact | Answers | Why it can't rot |
|---|---|---|
| Business spec | What does the customer need? | External, owned by the business; it is the intent |
| API contract | What shape is the boundary? | Validated at runtime and in CI; a violating payload fails |
| Behaviour tests | What does the service do now? | A wrong one fails the build |
| Plan, per change | Why this change, what shape? | Disposable; folds into the PR, never maintained |
| ADRs | Why is the structure this way? | Append-only records of decisions; never edited, so never stale |
| Property tests / Pact | What must always hold? What do consumers rely on? | Executable universals, verified on both sides in CI |

Terms explained:

- **ADR** is a short architecture decision note: why a boundary, a pattern, or a structural choice exists.
- **Pact** is a consumer contract test: one service states what it expects from another, and CI verifies the provider still delivers it.
- **Property test** is a test that checks a rule across many generated inputs rather than one hand-picked example.
- **Regression contract** is the current behaviour that mustn't break unless a human approves changing it.

The move that makes this practical: humans don't read the whole test suite. The agent retrieves the relevant slice and mediates. Tests plus contract are the regression contract ("don't break what exists"), the business spec plus the plan supply creation ("what to build"), and ADRs supply the "why it's shaped this way."

## How a change actually runs

Say you ask:

> Add partial capture to the payments service, allow capturing less than the authorized amount.

**First, the agent reads before it designs.** It retrieves the contract and the tests around capture, and it cites what it read, so if it only looked at half of what mattered, you can see that. Nothing gets drafted against a boundary nobody has looked at.

**Then it stops with a plan, before touching a file.** This is the first safety pause, where you review intent while it's still cheap to correct. The plan is written to a file under `docs/plans/` so you read it in your editor rather than scrolling through chat; what lands in chat is a pointer plus a short summary. The plan looks something like this:

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

That's condensed; the real format has a few more required lines.

**You answer the ambiguities and approve.** The gate catches a wrong direction before there's any code to anchor the argument. Two minutes here beats two hours untangling a green-but-wrong implementation later.

**Only then: contract, tests, code.** The contract is applied, the tests are written, and the code is implemented until everything's green. Those new tests *are* the new part of the spec being created; writing them is the act of specifying.

**Review reads the tests and contract as the spec.** It doesn't only ask "is the code clean?" It asks "do the changed tests and contract encode the right behaviour?" A changed test is a changed requirement, and it gets flagged as one. For money and auth paths, the plan asks a human to write one or two independent hold-out tests straight from the business spec, kept somewhere the agent can't read them, run after the visible suite is green. That's the one guard that still works when the visible tests and the code share the same misunderstanding.

## Two common variants

### Bug fix

A bug fix runs the same loop, compressed:

1. write the failing behaviour-level regression test that reproduces the bug,
2. fix the code,
3. keep the test forever.

That test is the spec of the fix, and this is how the suite slowly accumulates every edge case the team has actually hit.

### Amendment: changing existing behaviour

An amendment is the everyday case on a mature service: the change modifies behaviour that an existing test already asserts.

Suppose the business now allows 10% over-capture for shipping adjustments. The test `capture_fails_when_amount_exceeds_authorized_amount` is both the old rule being broken and the place the new rule gets written.

CTDD's answer is that the business requirement overrides the old test, but only through a reviewed diff that shows the old assertion and the new one side by side.

The reflex to unlearn is:

> just update the test to match

That's a requirements change wearing the costume of housekeeping.

## What compounds

A prose spec decays as a byproduct of doing the work. Every change can make it slightly less true, and nothing forces anyone to notice.

CTDD's artifacts are meant to move the other way. Every bug fix leaves a permanent regression test behind, so the suite accumulates the edge cases the team has actually hit. Every well-run change adds retrievable spec, so the next change starts from a better-described system than the one before it. The contract stays honest wherever validation is wired, because a violating payload fails. The plan is disposable, but what survives it is meant to land in durable artifacts: tests, contracts, and ADRs where the structure changed.

That's the long-run bet: **the executable spec gets richer as a byproduct of doing the work, instead of rotting as a byproduct of doing the work.**

There's an important catch in that, and it's why the discipline in the next section matters. A suite of behaviour-level tests compounds into an increasingly precise specification of observable behaviour. A suite of brittle, implementation-coupled tests compounds into an increasingly precise description of the code as it happens to be written today, which then blocks the very refactor it should have protected. Accumulation is a multiplier on whichever discipline you actually have. It doesn't supply the discipline.

And one honest caution about how to read the compounding claim: it's a claim about mechanism, not a promise about outcomes. CTDD doesn't make code cleaner by itself; that's still design skill, refactoring judgment, and code review. What it claims is narrower and checkable: when you follow the method on assertable behaviour, the durable spec gets richer over time, while a prose side-spec tends to decay.

## The one rule that makes it work

Write tests at the behaviour level, describing what a caller observes, and name them as statements of intent, because the name is the spec line.

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

Here's the test for whether a test is at the right altitude: if a correct refactor that preserves behaviour breaks it, it's at the wrong altitude. It's asserting wiring, not the contract.

Be wary of mock-heavy tests for the same reason. A test that mostly verifies which collaborators got called is describing implementation wiring, even when its name sounds behavioural. This discipline is the foundation the whole method stands on, and it's where CTDD fails quietly: an agent reading brittle tests as the spec will faithfully preserve the brittleness.

## Where it applies, and the honest floor

The real scope line is **assertable correctness**: use CTDD wherever "correct" can be captured in an executable assertion.

Backend APIs and microservices are the home case, request in, response out; given some state, an operation produces new state. Don't stretch CTDD over visual or UX correctness, where a test structurally can't assert "this looks right." A frontend's testable state layer (reducers, routing logic, client-side state machines) can qualify, but the visual layer usually can't.

And the floor, stated plainly because it's the single most decision-useful sentence here: **CTDD assumes an existing testing culture; it does not create one.**

Every safeguard in the method is built out of behaviour-level-testing discipline, so none of them can stand in for it. A team that can't yet write behaviour-level tests should build that muscle on ordinary TDD first.

On cost, the method follows its own ceremony rule:

- a trivial change costs one declared line,
- a normal change costs a few minutes of plan review before any code exists,
- a load-bearing change adds a human-written hold-out.

The weight tracks the cost of being wrong, not the size of the diff.

## Where it's honestly weak

The method's credibility rests on naming its own breaks. The full treatment (eight weaknesses, their mitigations, and the signals that tell you it's failing) is Part 2 of the rationale. For a first-timer, these are the ones to keep in mind.

**Tests are a sample, not a universal.** The agent can't tell behaviour that's guaranteed from behaviour that's only accidentally true right now. The mitigation is property-based tests for the real invariants, and treating the agent's summary as a claim to check rather than ground truth.

**A suite can't say "undefined on purpose."** Silence looks like an oversight. The mitigation is one sentence next to the boundary where it's deliberate, and only there.

**Circularity.** The agent can write a wrong test and wrong code that agree with each other; the suite goes green and everyone's happy. The mitigations are layered: the plan gate catches a wrong direction, humans review the tests as the spec to catch a wrong encoding, and hold-outs cover the load-bearing paths.

**Untested behaviour reads as permission.** The safety net has exactly the holes your coverage has. The mitigation is characterization tests, marked as observations rather than intent, written before a risky refactor, plus Pact at service boundaries.

**Performance, security, and audit requirements have no natural executable home.** The mitigation is to give them explicit homes: executable where you can, honest prose where you can't. In a role-based service, a contract-derived authorization matrix is often the highest-value test artifact per hour you'll write.

The two weaknesses you'll hit most in day-to-day work are **changed tests**, because they may be changed requirements, and **thin coverage**, because untested behaviour looks unconstrained to the agent.

## Four questions first-timers ask

**Isn't this just TDD with extra steps?**

It's TDD taken seriously, plus three things classic TDD usually lacked: the API contract as a machine-readable boundary spec, an agent as the designated reader of the relevant suite, and ADRs so structure doesn't get accidentally "improved" away. The fairest description is the floor promoted to a method, assembled from parts with twenty years of evidence behind them, which is more than most 2026 spec-driven tooling can claim.

**If tests are the spec, where does a new feature's spec come from?**

From the business requirement, the plan, and the contract you design first. Tests specify preservation. For creation, writing the tests *is* writing the spec, which is exactly why the plan gate matters most on new work: a wrong new test is a wrong spec.

**What stops the AI from gaming its own tests?**

Nothing automatic; that's the circularity weakness, named in the open. The guards are layered: a human approves intent before code exists, reviews the tests as requirements afterwards, and for money and auth writes hold-outs the agent never sees. Independence can't be faked with "a second agent" running the same model on the same context.

**Do we stop writing documentation?**

No. The business spec stays. ADRs record why the architecture is shaped the way it is. One-line invariant notes mark deliberate boundaries. The one thing that dies is the maintained technical prose spec, the document that starts incomplete and rots. When someone needs prose, the agent derives it from the artifacts that can't lie.

## Try it first

Try CTDD on one real backend change. The README covers installation and quick start.

Ask for the change in plain language and watch for the plan gate:

> Add partial capture to the payments service.

The agent should read the relevant contract and tests, summarize the existing behaviour, list its assumptions and the gaps, propose tests, and stop before touching any files.

## Rule of thumb for daily use

Default to CTDD for services behind an API, on a team that already has behaviour-level testing discipline. Make the contract the boundary spec. Add Pact the moment services start depending on each other. Layer in property tests where the invariants are real. And match the ceremony to the cost of being wrong.

## Read deeper later

When you want the full argument (the eight weaknesses, the comparison against Spec Kit, Kiro, and Tessl, and what evidence would show the method is failing) read `ctdd-in-depth.md`. It's long because it defends the method under hostile review. This guide is short so you can try it on one real change.
