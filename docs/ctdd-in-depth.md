# Contract- and Test-Driven Development (CTDD)

*The spec is derived from the tests and API contracts, not written up front — for backend APIs and microservices*

A practical alternative to spec-driven development for backend/microservice work, plus an honest account of where it breaks and how to handle it. Throughout, the approach is referred to as **CTDD** — read it as contract-*and*-test-driven, not contract-test-driven; contract tests are one tier of the stack, not the driver. The API contract fixes the boundary, behavior-level tests fix the behavior, and together they form the executable spec an AI agent (or a new engineer) reads and builds against.

**How to read this.** First time here? `docs/ctdd-in-practice.md` is the ten-minute version — start there and come back for the argument. Part 1 is the approach. Part 2 is where it breaks and how to hold it together. Part 3 is how it compares to the alternatives and when to reach for each. (Noticed irony: a method whose pitch is "don't maintain a big prose document" ships with one — but this is rationale, not spec; it records *why*, like a long-form ADR, and only the version-pinned appendix claims what exists.)

**Contents**

- **Part 1 — The approach:** [Scope: why backend, not frontend](#scope-why-backend-not-frontend) · [The idea in one line](#the-idea-in-one-line) · [What each artifact is for](#what-each-artifact-is-for) · [Example: payment capture](#example-payment-capture) · [The workflow, start to finish](#the-workflow-start-to-finish) · [What the agent must output before coding](#what-the-agent-must-output-before-coding) · [The one rule that makes it work](#the-one-rule-that-makes-it-work) · [The second payoff](#the-second-payoff-good-engineering-at-low-marginal-cost) · [Covering the gap](#covering-the-gap-property-tests-contracts-and-a-minimal-invariants-file) · [ADRs](#architecture-decisions-adrs-the-durable-why-of-the-structure)
- **Part 2 — Where it breaks:** [Weaknesses, and how to tackle them](#weaknesses-and-how-to-tackle-them) · [When it's failing: observable signals](#when-its-failing-observable-signals) · [PR checklist](#pr-checklist)
- **Part 3 — Comparisons and use:** [Why not full SDD](#why-not-full-spec-driven-development) · [The honest scorecard](#the-honest-scorecard-vs-prose-specs) · [How it compares](#how-it-compares-to-the-alternatives) · [When to choose which](#when-to-choose-which) · [Prior art](#prior-art-where-this-sits-in-the-landscape) · [Bottom line](#bottom-line)
- **Annex:** [CTDD in audited environments](#annex-ctdd-in-audited-environments) — weakness #8's governance machinery (proposed)
- **Appendix:** [Running CTDD as skills](#appendix-running-ctdd-as-skills) — the plugin, and where each Part-2 weakness is enforced
- **Appendix:** [Design decisions and rejected alternatives](#design-decisions-and-rejected-alternatives) — why the method and plugin are shaped this way, and the paths not taken

---

**PART 1 — THE APPROACH**

---

## Scope: why backend, not frontend

This approach is scoped deliberately to **backend APIs and microservices**, because that domain is close to its ideal case — and frontend is where it's weakest.

Backend correctness is **objective and expressible**: a request goes in, a response comes out; given state, an operation produces new state. That is exactly what behavior-level tests capture cleanly. There's no "does it *look* right," no subjective UX layer that tests structurally can't assert. On the frontend, much of "correct" is visual and experiential — spacing, responsiveness, feel — and the tooling for that (visual/snapshot regression) is brittle and drifts, which is the one thing this whole approach exists to avoid. The frontend also fails the sampling problem far harder: near-infinite interaction and layout states, much of it not reducible to an assertion.

Backend also hands you an artifact frontend lacks: **the API is already an agent- and machine-readable contract** (OpenAPI/JSON Schema for REST, protobuf/gRPC IDL, AsyncAPI for events). That's a genuine source of truth at the service boundary, not prose — and a mature ecosystem (schema-first design, consumer-driven contract testing) already treats it that way.

The precise line is not the deployment tier, though — it's **assertable correctness**: use CTDD where what "correct" means can be captured in an executable assertion. Backend-vs-frontend is a good heuristic for that line, not the line itself, and it leaks in both directions. A backend whose output is a rendered document (an invoice PDF, a generated tax form) has correctness that is partly visual: tests can assert extractable structure and field presence, but "the document is right" needs human or visual review — treat that layer like frontend. Conversely, a frontend with a fully testable state layer (reducers, routing logic, client-side state machines) is exactly "given state, an operation produces new state" — that layer can run under CTDD even though the rendering above it can't.

So: use this for services behind an API — with assertability, not the tier, as the actual test — and don't stretch it over a UI.

## The idea in one line

Keep the **business specification** from the customer as the source of *intent*. Instead of writing a second, detailed technical spec for an AI coding agent to implement against, let the agent (e.g. Claude Code) read the **API contract plus the relevant tests** as the agent-readable spec of how the service currently behaves — and summarize that for developers. A short **disposable plan** captures the *why* before each change.

This is **not** a replacement for the customer's business spec. It replaces the technical implementation spec you'd otherwise hand-write for the agent.

The direction is the inverse of *prose*-spec-driven development. SDD goes prose spec → tests → code: you author and maintain a technical document first and derive everything from it. CTDD reverses that: the executable artifacts — the API contract and the tests — are the maintained sources. Existing behavior is *derived from them*, read out on demand rather than authored up front; new behavior is *reviewed into them*. The prose spec is an output, not an input. (The contract is still designed first — but it's an executable boundary spec, not a prose document; the distinction is what Tier 2 below turns on.)

What's saved, precisely: not the specification work itself — the API shape still gets designed, behavioral clauses still get written (as test names and bodies), edge cases still get enumerated (in the plan and the property tests). The claim is not less work; it's the same work redirected into artifacts that execute and are enforced, so they can't rot. What's eliminated is the separate prose document and its maintenance.

## What each artifact is for

| Artifact | Owns | Audience | Maintained? |
|----------|------|----------|-------------|
| Business spec | What the customer needs (intent) | Humans | Yes — external, stays |
| Plan | Why *this change*, what shape | Human + agent | Disposable — folds into the PR |
| ADRs (Architecture Decision Records) | Why the *structure* is this way (service boundaries) | Human + agent | Durable — append-only, superseded not edited |
| API contract (OpenAPI / protobuf / AsyncAPI) | The interface shape at the boundary | Agent + other services | Durable — schema-first, validated |
| Tests | How the service behaves now | Agent reads → summarizes for humans | Yes — enforced automatically |
| Consumer-driven contracts (Pact) | The agreement *between* services | Agent + consuming teams | Durable — verified in CI both sides |
| Invariants / property tests | Universal rules & intentional boundaries | Human + agent | Durable — executable where possible |

The key move: humans don't read the whole test suite. The agent reads the contract and the relevant tests, holds them in context, and produces a summary. Tests plus the API contract become the **regression contract** — "don't break what exists" — while the business spec plus the plan supply "what to build," and ADRs supply "why it's shaped this way."

### Working with large suites

In a real system the agent can't (and shouldn't) ingest every test. It should retrieve the relevant slice — by module, changed files, domain terms, failing tests, API route, message type, and coverage links. The goal isn't "all tests in context"; it's "the relevant behavioral contract in context." Treat suite retrieval as a first-class step, not an afterthought.

There's early empirical support for retrieval being the active ingredient rather than a nicety: a 2026 study ("TDAD: Test-Driven Agentic Development" — a different system from the TDAD paper under prior art) gave a coding agent an AST-derived code↔test impact map and cut agent-introduced regressions by roughly 70% (test-level regression rate 6.08% → 1.82%) — while an ablation that added TDD *procedural* instructions without targeted test context made regressions *worse* than baseline. The mechanism, not the ritual, is what helps. (Small open models on SWE-bench; transfer to frontier models unproven.)

Stated from the agent's side, this is the method's practical core rather than extra process: a goal-only prompt ("implement partial capture") forces the agent to reconstruct requirements from code structure and naming — inference, its weakest mode. The artifact set is a grounding move — contract for the boundary, tests for existing behavior, plan for the delta, ADRs for intent — and the plan gate then forces the resulting understanding into the open while a misunderstanding is still cheap. Seen this way, CTDD is a requirements-context protocol for agents that happens to also be good engineering.

## Example: payment capture

A small end-to-end illustration of how the artifacts fit together.

**Business spec (intent).** A payment may be captured only after authorization. A captured payment may not be captured again.

**API contract.** `POST /payments/{id}/capture` accepts a capture amount and returns the updated payment state. (Defined in OpenAPI; request/response validated in CI.)

**Behavior tests (the executable spec of behavior).**

```
capture_succeeds_when_payment_is_authorized
capture_fails_when_payment_is_pending
capture_fails_when_payment_is_already_captured
capture_fails_when_amount_exceeds_authorized_amount
```

**Property / invariant.** For every terminal payment state, capture is rejected. (A property test generates states rather than enumerating them.)

**Consumer contract (Pact).** The checkout service expects a failed capture to return a stable error code, not just any `400`. Verified against the provider in CI, so a change that drops the code fails before it reaches checkout.

**Authorization matrix.** Only the merchant service role may capture; the generated matrix asserts every other role receives `403` on `POST /payments/{id}/capture` — derived from the contract's security scheme, so a new endpoint can't ship without a row.

**ADR.** Payment state transitions are enforced in the domain layer rather than in controllers, because captures can be triggered from the API, retry jobs, and message consumers — one enforcement point, not three.

Read together, these are what the agent implements against: the contract fixes the shape, the tests fix the behavior, the property covers the whole state space, the Pact protects the consumer, and the ADR tells the agent not to "helpfully" move the state machine into the controller.

## The workflow, start to finish

There are **two plans**, and it's worth keeping them distinct. The *design plan* (step 2) is the human's — why this approach, the shape. The *implementation plan* (step 6) is the agent's — how it intends to build it. The first frames the problem; the second is a reviewable gate before code is written.

1. **Intent** — start from the customer's business spec. That's the source of what to build.
2. **Design plan (human)** — write a short, disposable plan: why this approach, the shape, what's out of scope, the risky part. Lives in the PR description, then discarded.
3. **ADR (only for a structural decision)** — if the change touches a service boundary or a real architecture choice, record context → decision → consequences. Append-only; supersede, don't edit.
4. **Agent reads contract + relevant tests** — the agent retrieves the relevant slice and summarizes current behavior, so devs and the agent share a model of what exists. Understanding precedes design: nothing gets drafted against a boundary nobody has read.
5. **Contract first — drafted before tests and code** — design or update the API contract (OpenAPI/protobuf/AsyncAPI) as a *proposed* change, reviewed inside the implementation plan (step 6) and applied to disk only after approval. This is the boundary spec the agent and consuming services build against; for cross-service changes, update the consumer-driven contract (Pact) so both sides are pinned. "Contract-first" means before implementation — not before reading what exists.
6. **Implementation plan (agent) — reviewed before coding** — the agent proposes *how* it will implement: the approach, the new/changed tests, contract changes, files it will touch, assumptions, and uncovered or ambiguous cases (the full list is under "What the agent must output before coding"). For anything beyond a trivial change, a human reviews and approves this plan before a line of code is written — this is the cheapest place to catch a wrong direction, and it's the first guard against the circularity problem (weakness #3 details what the gate can and can't catch, and what must come after it). Scale the gate to the change: a one-line fix doesn't need it; a change to a state machine does — and don't let the agent be the sole judge of triviality: "just updating a test" is a spec change.
7. **Test** — write behavior-level tests for the new behavior (it has no tests yet — this is where its spec gets created). Reach for property tests where an invariant applies (idempotency, ordering, validation).
8. **Build** — implement until the contract validates and the tests are green.
9. **Review** — a human reviews the *tests and the contract* as the spec, not just the code (see weakness #3).
10. **Invariant note** — add a colocated sentence only where a universal rule or an intentional gap can't be made executable (see weakness #2).

### New features and greenfield services

A common question: if the spec *is* the tests, what happens when a new feature has no tests yet?

Tests are the spec for **preservation** — and a new feature has nothing to preserve yet, so there's no existing suite to read for it. That's expected, not a gap. For new work the source of *what to build* is the business requirement plus the short plan plus the **API contract you design first** (step 5). You then *write* the behavior-level tests as part of building the feature (step 7), and that act is what **creates** the spec. Afterwards, those tests are the durable spec the next change reads.

Because the tests are being *invented* rather than read, the review gate (step 6) matters most here: a wrong new test is a wrong spec, so a human should confirm the proposed tests actually encode the requirement before code is written. For a fully greenfield service with no tests at all, the "read existing tests" step is simply empty — you lean entirely on contract-first and the plan, and everything you write becomes the seed of the spec. The method degrades gracefully; it just has less to read.

### Amendment: the modal case

Preservation and creation are the clean poles; most real changes to a mature service are neither — they **modify behavior an existing test asserts**. Allowing a 10% over-capture for shipping adjustments means `capture_fails_when_amount_exceeds_authorized_amount` is simultaneously the preservation artifact being violated and the place where the new spec gets written. The preservation/creation split survives this, but as a rule of *authority*, not a taxonomy of changes: the business spec overrides the old test — and only through a reviewed diff. A changed test is a changed requirement, reviewed at the gate like any other spec change. Amendment deserves its own name because it's the everyday case, and it's where circularity (weakness #3) most easily slips through: the reflex "update the test to match" turns a spec change into a silent one. The gate, the changed-test review, and the optional spec-edit hook do most of their real work here — not on greenfield.

## What the agent must output before coding

This is the **implementation plan** from step 6 of the workflow — the reviewable gate. Before writing any implementation, require the agent to produce:

- relevant existing behaviors found in tests and contracts;
- assumptions it is making;
- uncovered or ambiguous cases;
- proposed new or changed tests;
- contract changes, if any;
- files likely to change.

The agent should not implement until this summary is reviewed for risky or ambiguous changes. This is the first guard against the circularity problem (weakness #3): the human checks the *intended* behavior before the agent has a chance to make the tests and the code agree on the wrong thing. (Weakness #3 covers what a plan structurally can't catch.)

## The one rule that makes it work

Write tests at the **behavior level** — what the caller or user observes — not the implementation level. Name them as statements of intent; the name is the spec line. If a correct refactor breaks a test, the test was coupled to implementation — fix its altitude. This is the hardest discipline in testing and the prerequisite the whole approach leans on, so it's worth protecting deliberately. And state the floor plainly: **CTDD assumes an existing testing culture; it does not create one.** Every safeguard in Part 2 is made of that discipline, so none of them can substitute for it. A team that can't yet write behavior-level tests should build that muscle on ordinary TDD first. The subtler gap is calibration: a team can have a testing culture without a shared standard for what requirement-level means — implementation snapshots read as behavioral at a glance — and the churn-on-refactor signal in "When it's failing" is the detector; watch it hardest in the first months.

**Good behavior-level names:**

```
returns_404_when_payment_does_not_exist
rejects_capture_when_payment_is_not_authorized
publishes_payment_completed_event_after_successful_capture
is_idempotent_when_the_same_command_is_retried
```

**Implementation-coupled names (avoid):**

```
calls_repository_once
invokes_mapper
uses_payment_status_validator
handler_calls_private_method
```

The first set survives any refactor that preserves behavior; the second set breaks the moment you rename a method or swap a collaborator, which means it's testing the wiring, not the contract.

Beware mock-heavy tests for the same reason: a test that mostly verifies collaborator calls is describing implementation wiring even when its name sounds behavioral. Prefer asserting through the public service boundary, with realistic fakes where needed. This discipline is where CTDD fails *quietly*: when tests look behavioral but are actually implementation snapshots, the agent reads the brittleness as intent — and faithfully preserves it.

## The second payoff: good engineering at low marginal cost

The reason to review behavior-level tests as the spec isn't only to feed the agent — the same practice produces what you'd want from any well-built service:

- **Maintainability / safe refactoring.** Behavior-level tests pin *what* the service does, not *how*, so you can restructure internals freely and the suite flags only real behavior breaks. That's what keeps a codebase safe to change months later.
- **Stability.** Every fixed bug becomes a regression test, so failures don't silently return; a change that breaks existing behavior fails loudly in CI instead of quietly in production.
- **Robustness.** The property-test and contract layer forces edge cases and invariants — idempotency, ordering, validation — to be handled explicitly rather than discovered by a customer.
- **Shared understanding.** Tests reviewed as requirements are living, executable documentation. Intent stops living in one engineer's head, which is what actually speeds onboarding and hand-offs.
- **Better boundaries.** Code that's painful to test at the behavior level usually has muddy module boundaries; the testability pressure nudges the design toward cleaner seams.

**And crucially, none of this is overhead the way a technical spec is.** ADRs, the API contract, behavior tests, and property tests are durable engineering assets a well-run service should have regardless of whether an agent ever reads them. If a team already treats them as first-class artifacts, CTDD adds little ceremony on top; if it doesn't, the upfront cost is real — but it goes into artifacts that stay useful. A hand-written technical spec, by contrast, is closer to pure overhead: it's written once to brief the implementer, and although it's usually kept (in a wiki or the repo), it typically stops being *maintained* the moment the code exists, so it goes stale and its value decays. (Regulated environments that keep specs under formal document control are the exception — and exactly the case Part 3 routes to SDD.) Being retained but unmaintained is arguably worse than deleted — it still looks authoritative while quietly lying. The real contrast isn't kept-vs-discarded; it's *maintained-and-verified* versus *kept-but-rotting*: this approach spends comparable effort, but on artifacts that stay honest because they execute and are enforced, so they keep paying off instead of rotting. That's what makes it low-ceremony rather than just cheap.

Two caveats: these are the classic payoffs of disciplined testing, inherited here rather than invented — and they depend on the same discipline the approach leans on. Implementation-coupled or unreviewed tests deliver the opposite: brittleness plus false confidence. And "robustness" in particular comes from the property/contract tier, not example tests alone. So the AI framing adds a *reader* for these artifacts; the engineering benefit was always the reason to write them.

**What it costs to operate.** Three facts about overhead, stated here because a method that hides its costs is hiding part of its spec. First, the dominant cost of any agent-driven change is retrieval — reading the contract and the relevant tests — and CTDD does not add that cost: it mandates what a competent agentic workflow pays anyway, and the method's own marginal overhead (skill guidance, the plan, the review prose) is small against that baseline. Second, cost scales with the risk tier by design: a trivial change costs one declared line; a normal change costs minutes of human attention at the plan gate, spent at the moment attention is cheapest — before code exists to anchor anyone; a load-bearing change adds a human-written hold-out, priced against a wrong money-path change reaching production. Third — the honest one — the operating risk is not per-change cost but frequency: at high plan volume the gate degrades into a stamp, and a stamped gate is worse than none because it still looks like coverage. Whether a team sits below or above that threshold is not derivable from this document; the gate reject/edit rate and the adopter's own annoyance journal (the failure signals in Part 2) are the instruments that answer it.

## Covering the gap: property tests, contracts, and a minimal invariants file

Tests are a sample of behavior and can't state a universal or mark a region as "undefined on purpose." To cover that, don't reach for prose first — most of it can stay executable, which means it can't drift silently either. Rank by drift-resistance and only fall to plain text for the residue.

**Tier 1 — make the universal executable (best).** A **property-based test** asserts a rule across a generated *range* of inputs instead of a few hand-picked points (`for all lists, reverse(reverse(x)) == x`). This expresses the "for all" *and* runs, closing most of the gap that felt structural.

**Tier 2 — encode the constraint in the code and the contract.** Preconditions, postconditions, invariant assertions (design-by-contract), and the type system. A type that makes `N ≤ 0` unrepresentable, or a runtime `assert N > 0`, states the boundary and enforces it. On the backend this tier is stronger than elsewhere, because the **API contract becomes executable Tier 2 once validation is wired in**: an OpenAPI/JSON Schema or protobuf definition states the shape of every request and response, and request/response validation, schema linting, and generated tests enforce it at runtime and in CI. A schema file nobody validates against is just prose in YAML — the enforcement is part of the contract. Design the contract first (schema-first / API-first) and it becomes the boundary spec the agent implements against, not prose. The agent reads it as a hard constraint, because a violating payload fails validation. The tier's weight rests on the API contract (shared across services, statically readable, runtime-enforced); in-code contracts — types, preconditions, asserts — are useful local hardening, a component rather than a pillar.

**The authorization matrix — the cheapest high-value member of this family.** For any service with roles and endpoints, generate the full matrix from the contract — every role × every endpoint, expected allow or deny — and assert it as tests. It's mechanical to produce (the contract's security schemes and route list define the axes), behavior-level by construction (it asserts exactly what a caller observes: 200-family vs 401/403), and regenerated when the contract changes, so it can't drift from the boundary. It converts authorization — normally the classic untested load-bearing behavior (weakness #4) and the security half of weakness #7 — into an executable universal: not "these three endpoints check roles" but "every endpoint's answer to every role is asserted." For SSO, selfcare, payment, and e-signing services, this is often the highest-value test artifact per hour spent in the entire stack. Since v0.6.0 the plugin ships the generator: `scripts/gen-authz-matrix.py` derives the matrix from the OpenAPI document — every identity (anonymous / authenticated / one per scope and `x-roles` role) × every operation, expected `allow` / `deny-401` / `deny-403` with the *why* per cell — deterministically, so the JSON diffs cleanly and a new endpoint shows up in review as new rows; its `--check` mode turns "an endpoint without matrix rows" into a CI failure, and `--csharp-scaffold` prints the one-time xUnit adapter (the JSON is the generated artifact; the adapter is copied once, so nothing exists in two places to drift). One honest ceiling: the matrix covers the authorization surface the contract *declares* — object-level rules ("only the owning merchant may capture *this* payment") are invisible to any schema and stay with hand-written behavior tests.

**Tier 3 — colocated prose, only for what can't be executed.** Rationale, intent, "undefined on purpose," scope decisions. Put these in a **docstring/contract comment next to the code** — colocation keeps them honest, because they're in the diff whenever the code changes and the agent reads them inline. Promote to a standalone `INVARIANTS.md` only for a cross-cutting rule no single location owns, and keep that file to a curated list of universals and deliberately-undefined regions.

**When the artifacts disagree.** With this many artifact types, conflicts happen: a contract allows what a test rejects, an example test contradicts a property, Pact expects a shape the contract dropped. No artifact outranks another automatically — a cross-artifact conflict is a *detected spec bug*, and it takes the amendment path: stop, decide which artifact is wrong against business intent, fix it as a reviewed spec change. The conflict type is itself diagnostic: a Pact failure is the highest-blast-radius signal (a consumer's reality disagrees); contract-vs-test usually means validation isn't wired (Tier 2 exists only when enforced); example-vs-property means the generator found the lie in the example. The one forbidden move is the quiet fix — adjusting whichever artifact is easiest to change until CI goes green.

**Strict entry rule:** the moment an invariant note describes behavior a test already covers, it's becoming the spec doc you were trying to avoid. Something goes in Tier 3 only if it's (a) a universal or a boundary, and (b) not already executable as a property or a contract. Everything that *can* drop to Tier 1 or 2 should.

**Mutation testing — the guardrail for load-bearing logic.** Coverage alone is not enough: a test can execute a line without actually protecting the rule on it. Mutation testing checks this by making small changes to the code (e.g. `>` to `>=`) and confirming a test fails. If the suite stays green after a mutation, the test is weak — and the agent will treat a weak test as a strong contract. Run mutation testing on the critical core (money, auth, state machines), not everywhere; it's slow, so target it where a false sense of safety is dangerous.

## Architecture decisions (ADRs): the durable "why" of the structure

**What an ADR is.** An **Architecture Decision Record** is a short document — often a page or less — that captures one significant technical decision in three parts: the *context* you were in, the *decision* you made, and the *consequences* you accepted. Teams keep them as a numbered, append-only log in the repo (e.g. `docs/adr/0007-payments-in-domain-layer.md`). If you haven't used them: think of a dated changelog for architecture choices, with the reasoning attached — not a design doc you keep editing, but a record of what was decided and why, at the time.

The disposable plan throws away design rationale — six months later nobody remembers why a boundary is where it is. ADRs are the durable home for that, and they don't drag you back into spec-driven development because of one property: **an ADR records a decision at a point in time, not the current state of the system.** It's append-only. You don't edit an ADR when code changes; if a decision is reversed you write a new one that supersedes it and leave the original as a record of what you believed and why. That immutability is what keeps it from drifting — it never claims to describe what the system does *now* (tests do that), only why a choice was made.

For the agent this fills a gap tests structurally can't. Tests show *behavior*; they say nothing about why the system is *shaped* the way it is. Without that, an agent sees two services that could be merged, finds no test forbidding it, and "helpfully" merges them — destroying a separation that existed for blast radius, deploy independence, team ownership, or a compliance boundary. The ADR is where that "why" lives, so the agent and new devs treat the structure as intentional, not incidental.

Keep the same scope discipline as the invariants file: an ADR captures *a decision and its tradeoffs* (context → decision → consequences), not a description of behavior. The moment it narrates what the code does, it's drifting into spec territory.

---

**PART 2 — WHERE IT BREAKS, AND HOW TO HOLD IT TOGETHER**

---

## Weaknesses, and how to tackle them

This approach is a reasonable *default*, not a universal win. Be honest about where it's thin.

### 1. Tests are a sample, not a universal — and the agent generalizes from the sample
A test asserts "for these inputs, this holds." A spec says "for all inputs." When the agent reads the suite and reports "the system does X," it can't cleanly separate behavior that's *guaranteed*, behavior that *happens to be true but was never asserted*, and behavior *nobody considered*. It tends to smooth all three into one confident narrative.

Caveat in fairness: prose specs share this gap, and an AI reading prose is at least as prone to confidently interpolate. So this is a weakness of *summarizing an incomplete spec*, not a weakness unique to tests.

**How to tackle it:**
- Treat the agent's summary as "here's my reading — tell me where I'm wrong," never as ground truth.
- Track behavioral coverage of the things you actually care about; the suite is the agent's entire theory of the system, so gaps in coverage are gaps in its understanding.
- Use property-based tests for logic with real invariants — they assert over ranges of inputs instead of hand-picked points, shrinking the sampling gap.
- *(Proposed — not yet built.)* **Claim provenance** in derived summaries: every sentence the agent reads out of the suite carries its evidence — `[asserted by: test X / contract]` or `[INFERRED]` — so the three things it currently smooths together (guaranteed, accidentally true, never considered) stay visibly distinct, and the INFERRED bucket is the sampling gap made per-claim visible.

### 2. A test suite can't say "this is undefined on purpose"
Tests express what *is* checked. They can't state a universal in one line, and they can't mark a region as intentionally unconstrained. The suite's silence about a case is indistinguishable from an oversight — which is exactly the ambiguity that bites the agent when it implements: it reads "untested" as "free to change."

**How to tackle it:**
- This is the one place a line of prose genuinely earns its keep. Where a rule is universal or a boundary is deliberate, write one sentence: *"Must hold for all N > 0; behavior for N ≤ 0 is intentionally undefined."* Not a spec document — a sentence, next to the code or in the contract, that resolves the on-purpose-vs-accident ambiguity tests can't.
- Reserve this for real invariants and boundaries. Everywhere else, let the tests carry it.
- *(Proposed — not yet built.)* A **machine-readable marker convention** for those sentences — e.g. `// CTDD-UNDEFINED: N<=0 — <why>` — so declared gaps become greppable: an inventory report is deterministic, and a diff touching a marked region can be flagged mechanically instead of hoping the agent reads the docstring.

### 3. Circularity — the agent can satisfy the tests without being right
"Make the tests pass" is a spec the agent can meet by writing a test that encodes a shallow understanding and code that matches it — both wrong in the same direction, suite green, everyone happy. Especially when the agent writes both.

The problem has two distinct attack surfaces, and they need different guards:

- **Wrong direction** — the proposed behavior itself misreads the requirement. The plan gate catches this: a human reviews intent before either artifact exists, at the cheapest point.
- **Wrong encoding** — the plan is right at the level of test *names*, and the misunderstanding lives below them: in assertion bodies, fixture setup, or a fake shared between test and implementation. The gate structurally cannot see this, because at gate time the encodings don't exist. The silent-failure condition, concretely: `capture_fails_when_amount_exceeds_authorized_amount` is approved at the gate; the test derives "authorized amount" from the same fixture helper the implementation uses; both encode fee-inclusive semantics where the business meant fee-exclusive; the suite is green, and the reviewer signed off on a true *name* attached to a wrong *encoding*. Expect it in exactly the load-bearing semantics: rounding, bound inclusivity, timezones, fee inclusion.

**How to tackle it:**
- Wrong direction: require the agent to propose the new/changed tests *before* implementation (see "What the agent must output before coding") and review intent there.
- Wrong encoding: a human reviews the **tests** as the actual spec — that's the one artifact where a wrong understanding hides. You haven't escaped reading; you've relocated it from "read the whole system" to "review the proposed tests," which is far smaller — though roughly comparable to reviewing a spec section under SDD; the advantage over SDD here is drift, not review economics.
- For anything load-bearing, independence: tests written or reviewed by someone other than whoever wrote the implementation — with the caveat that "another agent" running the same model on the same context is cosmetic independence, the same prior twice. So for load-bearing changes, use the strong form — a **hold-out acceptance test**: a human writes one to three tests straight from the business spec before the agent starts; the agent never sees them; they run only once implementation is green. Treat this as part of the method there, not an optional extra. It's the only guard that works when the visible tests and the code share a single misunderstanding. (Precedent: TDAD's hidden-test split, where the held-out pass rate — not the visible one — is treated as the real measure of compliance.) One limit: this guard doesn't escape the method's central fragility — sealed behavior-level tests from the business spec demand exactly the scarce discipline the whole approach leans on — it *concentrates* it: one to three tests, written well, once, at the highest-leverage point, instead of suite-wide vigilance. That's the right shape for a scarce resource, and it is no rescue for a team that can't write behavior-level tests at all.
- **Back-translation** (in the runtime since v0.6.0): for load-bearing diffs, the agent states — from the tests alone — the requirement they encode, in one or two sentences, and the human compares that prose to the business intent. This survives the same-model objection that killed second-opinion review: the misunderstanding lives in the *intent → artifact* direction, but back-translation reads the *artifact → prose* direction — the bytes concretely encode fee-inclusive semantics whatever the model once believed, and the human stays the judge.
- *(Proposed — not yet built.)* An **expected-value independence analyzer** (Roslyn, advisory, scoped to money/boundary asserts): flag tests whose expected values are *computed by production code* — the shared `FeeCalculator`, the common fixture builder — rather than literal or test-owned. This would be the first mechanical guard the wrong-encoding surface has ever had; heuristic, so it catches the gross shared-computation cases and leaves independent-but-identically-wrong literals to the reviews above.
- Mutation testing helps catch tests that pass without protecting the rule — note it checks test *strength*, not altitude or intent, so it complements the reviews rather than replacing them.

### 4. Untested load-bearing behavior gets treated as permission
Real systems are full of behavior that matters but was never tested. To the agent, untested = unconstrained, so it will refactor or alter that behavior and every test stays green. The safety net has exactly the holes your coverage has. Across service boundaries this is worse: a change that passes one service's own suite can still break a *consumer* that relied on the old response shape.

**How to tackle it:**
- Backfill characterization tests before large refactors — capture current behavior first so the agent has boundaries. Mark them as observations, not requirements (e.g. a `currently_*` prefix): a characterization test may pin a bug, so changing one is a human decision about whether the old behavior was intent or accident — unlike an intent test, which *is* the spec.
- Use **consumer-driven contract testing (Pact)** at service boundaries: consumers declare what they expect, the provider verifies against it in CI, and a breaking change fails *before* it reaches the other team. This is the cross-service protection single-repo tests can't give you.
- When the agent proposes a change in an area with thin coverage, flag it for extra human attention rather than trusting the green suite.
- *(Proposed — not yet built.)* A **coverage-report reader**: the diff-surface script annotates changed files with their coverage percentage *read from the report CI already produces* (cobertura/lcov). Distinct from the coverage-quantifier idea killed earlier — that died over per-ecosystem tooling maintenance; reading a standard report format is not that. "Thinly covered" becomes a number where the number already exists, and stays a judgment where it doesn't.

### 5. Tests describe preservation, not creation
For genuinely new behavior there are no tests yet, so tests-as-spec is purely a regression contract. The "what to build" still comes entirely from the business spec and the plan.

**How to tackle it:**
- Be precise about the division: tests are the spec for *preservation*; the business spec plus the plan are the spec for *creation*. Don't expect tests to tell the agent what the new thing should do.
- Require the agent to propose the new tests before implementation.
- Review changed tests as changed requirements — a diff to a test is a diff to the spec.

### 6. Distributed-systems behavior is where the sampling gap bites hardest
Async messaging, eventual consistency, idempotency, retries, ordering, partial failure — the microservice failure modes are timing- and interleaving-dependent, so the cases you didn't imagine are exactly the ones that page you at 3am. Plain unit and even service-level tests are weak here; this is the "dangerous core" of a microservice system.

**How to tackle it:**
- Treat the coordination/consistency logic as the critical core and escalate the rigor there: property-based tests (excellent for idempotency, ordering, and invariants over generated interleavings); systematic concurrency testing for the .NET core — **Microsoft Coyote** explores task interleavings deterministically against unmodified code via binary rewriting, with reproducible traces, production-proven in Azure and sitting exactly on the rung between property tests and formal methods (note it's MSR "as-is" open source, no formal support); contract tests for the messaging boundary; and — for a truly critical protocol — formal methods. Keep the CRUD-ish request/response surface in the default tests-as-spec lane.

### 7. Non-functional and security requirements have no executable home
The stack specifies functional behavior at the boundary: shape (contract), behavior (tests), cross-service expectations (Pact), universals (properties), rationale (ADRs). A whole class of spec content fits none of them: latency and throughput budgets, resource ceilings, authorization-matrix completeness, tenant isolation, data retention and deletion semantics, audit-log completeness, backpressure and shutdown behavior. An agent reading contract + tests has no theory of the p99, and will happily introduce an N+1 query or a synchronous external call with every test green — the violation is invisible to the entire spec. For the regulated domains this method targets, these requirements are frequently the contract the customer actually signed. Prose SDD templates (Kiro's design doc, a classic SRS) do carry quality-attribute sections — but a latency budget in prose drifts exactly like every other prose clause, and a stale budget is false confidence, which the kept-but-rotting argument above says is arguably worse than honest silence. The prose camp's real edge is only day-one visibility, front-loaded and decaying like the rest of its spec. So this weakness is not NFR-envy of SDD: NFRs are hard for every methodology, and this one owes them the same discipline it applies to functional behavior — push what's expressible into executable form, and keep the residue honest.

**How to tackle it** *(proposed — unlike the mitigations for #1–#6, none of these have been validated in practice yet)*:
- Make what can be checked executable — **executable NFR checks**, a parallel track to the correctness tiers rather than a rung on them: SLO/latency assertions and load-test thresholds in CI (sampled and environment-sensitive — and note that perf gates are flaky, flaky gates get disabled, and a disabled check that still *looks* covered is worse than an honest absence: fixed baselines, generous margins, trend-alerts rather than hard gates in noisy environments, and if you turn a check off, delete it visibly); **authorization-matrix tests generated from the contract** (promoted to its own section under "Covering the gap," because for role-based services it's the highest-value mechanism in this document); scheduled retention/deletion verification jobs.
- Give the residue the homes prose already has: a colocated Tier-3 budget note for local constraints; a curated NFR section in `INVARIANTS.md` for cross-cutting budgets; an ADR where the boundary is structural (an isolation or compliance boundary *is* a service-boundary decision).
- Feed it to the agent explicitly: the implementation plan (step 6) should require the agent to state which NFR budgets its change could touch. "No test covers latency" must not read as "latency is free."
- And the residue: some of this (isolation under adversarial load, true p99) is only verifiable by observation in staging or production. That's *monitored*, not *specified* — say so rather than pretending the suite covers it.
- Do **not** import a standalone prose quality-attribute document as the fix — that reintroduces the maintained-side-document drift this whole doc argues against. The prose residue goes to the same colocated notes, `INVARIANTS.md` section, and ADRs as everything else.

### 8. The executable spec has no versioned record-of-intent for audit
In a regulated domain, "prove what this service was contractually required to do on date X, and who signed it off" is a real deliverable. A test suite and contract mutated in place — even with full git history — is not that: git proves what the artifacts *were*, not what the system was *required to be, as approved*. The chain a document-controlled SRS provides — requirement clause → approved change → sign-off authority — has no single home here. The plan, the one artifact that carried "what was required and why," folds into a PR description: raw material for an audit trail, but scattered across a platform, not a document-controlled record with sign-off authority attached; and a test diff shows who committed a change, not that the business owner approved the requirement it encodes. This is the one place where the regulated market's attachment to prose specs is rational rather than legacy inertia. It pairs with #7 as the second class of spec content the executable stack structurally can't express: #7 is constraints without assertions; #8 is intent-as-signed-off without documents.

**How to tackle it:** the mitigations — archived append-only plans, and a derived requirement→test manifest emitted at release — are governance machinery rather than method epistemics, so they live in their own annex, "CTDD in audited environments," along with the boundary where full SDD remains the right call. All of it is proposed, not yet validated in practice.

## When it's failing: observable signals

A method that can't fail can't be evaluated — only believed. And "the team was messy" must not become a universal alibi: if the signals below fire on a team that is genuinely following the method, the method — not the team — is failing there. Watch for:

- **Plan-gate reject rate ≈ 0.** A working gate rejects or amends sometimes; weeks of instant approvals mean it has decayed into a rubber stamp and the wrong-direction guard is off. Instrument it — log approved / edited / rejected and dwell time; the trend is the health check.
- **Test churn on behavior-preserving refactors trending up.** If refactors keep breaking tests, the suite is drifting from behavior level toward implementation snapshots — the one discipline everything leans on is failing quietly, exactly as Part 1 warns.
- **Mutation scores high, escaped defects flat.** Tests strong against mutants but wrong about intent is circularity in the wild: the suite and the code agree, reality disagrees.
- **Incident rate in well-covered areas not improving.** If behavior the "spec" covers still breaks in production at the old rate, the executable spec isn't binding reality — check whether the tests assert the right things at the right altitude before writing more of them.
- **Review cost up, defects flat.** If review latency and gate load rise materially without a matching drop in escaped defects on asserted behavior, the method is charging its price without paying its return. Stop calling it an efficiency win; downshift the ceremony deliberately or exit — don't let the suite keep growing as a substitute for asking the question.

The first two are cheap to instrument and worth wiring up from day one; they are the difference between believing the method works and knowing when it has stopped.

**The compounding claim, and why it isn't a defense.** The method predicts a flywheel: regression tests accumulate per bug fix, retrievable spec accumulates per change, and later changes begin from richer context than earlier ones. The executable spec becomes richer as a byproduct of the work rather than decaying as one. This is CTDD's strongest long-run argument, and it is also the easiest place to smuggle in an unfalsifiable one. So state it precisely: it is a prediction, not an observation — nothing here has measured it yet — and it is checkable. A team can look at whether its regression suite grows with incidents, whether retrieval on mature services is getting easier or harder, and whether covered behavior breaks less often over time — the last of which is the same quantity the churn-on-refactor and regression-rate signals above already track, so an instrumented pilot tests the compounding claim for free rather than taking it on faith.

It compounds in both directions. The same accumulation that turns behavior-level tests into an increasingly precise specification turns implementation-coupled tests into an increasingly precise description of yesterday's code. And it may never be used as a reply to a bad result. "It would have worked if you had followed it more" is the No True Scotsman move that has excused every failed methodology in software; CTDD's answer to a bad result is the failure signals above, not a demand for more faith.

## PR checklist

A menu, not a mandate — scale it to the risk of the change. A one-line config tweak doesn't need all of this; a change to the payment state machine needs all of it and then some.

- Does every new behavior have a behavior-level test?
- Are changed tests reviewed as changed requirements?
- Are API contract changes reviewed as boundary changes?
- Did the agent list assumptions and uncovered cases before coding?
- Are tests coupled to observable behavior rather than implementation details?
- Are intentional gaps documented as invariant notes?
- Does any service-boundary or architecture decision need an ADR?
- Are characterization tests added before risky refactors?
- Are cross-service expectations protected by consumer-driven contracts?
- Are critical invariants covered by property tests, contracts, types, or formal methods (and spot-checked with mutation testing)?
- Could this change move a latency/throughput budget or a security boundary (authz, tenant isolation, retention/audit)? If so, is the budget executable — or at least explicitly stated somewhere the agent read it?
- In an audited repo: is the approved plan archived, and the requirement→test manifest updated for this change?

---

**PART 3 — HOW IT COMPARES, AND WHEN TO USE IT**

---

## Why not full spec-driven development

Two independent arguments, often conflated. Both hold.

**1. Drift.** A prose spec is a second codebase. It drifts from reality the moment code changes, because nothing pulls it back into sync — you find out it's wrong when someone gets burned. For covered behavior, tests remove the *silent* version of this problem: either the implementation still matches the executable expectation, or the test fails. The remaining risk is narrower — that the expectation itself becomes obsolete when intended behavior changes and nobody updates the test — but that's a visible, reviewable event, not silent rot.

**2. Completeness — you can't write the perfect spec in the first place.** This is upstream of drift and arguably more fundamental. Capturing every edge case and technical detail up front is genuinely hard, because *many edge cases don't exist until you build the thing*: the null in the middle of the batch, the retry-after-partial-write, the two-requests-racing case — you discover these while implementing, not while speccing. The act of writing code surfaces questions the spec author never thought to ask, so a spec written before the code is structurally incomplete — not from laziness, but because the information didn't exist yet. To enumerate every edge you'd have to mentally execute the whole system, which is just writing the code in your head, badly.

There's a cost asymmetry that makes it worse, for algorithmic and stateful logic especially, specifying down to "every edge case" approaches implementation cost, because you're writing the same logic in prose, a medium with no compiler to catch contradictions and no test runner to flag a missing case. You pay almost-implementation cost for an artifact that's *less* rigorous than the implementation, because nothing checks it. (For policy-type edges the asymmetry is weaker — "a capture after the refund window closes is rejected" is one sentence to state and days to implement. The argument is about the logic-dense middle, which is also where prose specs actually go wrong.)

Tests turn this weakness into a strength: you don't enumerate edge cases up front, you **accumulate** them. Every bug becomes a regression test, so each edge is captured the moment it's discovered, in executable form, permanently. The spec grows to match reality incrementally instead of trying to predict it perfectly on day one. A prose spec must be complete to be trustworthy; a test suite is allowed to be incomplete and still honest about what it covers — its silence means "not yet," not "definitely handled."

**The caveat — the dangerous core is the exception.** One class of edge case you *do* want to pin down before coding: the ones where discovering them in production is catastrophic — money, auth, data loss, the distributed-coordination core. There, "find the edge when it bites" is unacceptable, so escalate to property-based tests (which *generate* edges you didn't think of) and formal methods (which prove the space is covered). And accumulating edges reactively has its own failure mode — you only capture what actually bit someone, so the rare-but-severe case may never become a test (the sampling problem, weakness #1, in a different outfit); property testing is the main mitigation. So the rule is: don't spec every edge up front by default, with a deliberate exception for the small core where a miss is catastrophic.

## The honest scorecard vs. prose specs

- **Drift:** tests win decisively — drift on covered behavior is caught by a failing test, not left silent; prose drifts silently everywhere.
- **Raw incompleteness:** roughly a wash — both omit the case nobody imagined; prose arguably worse because a finished-looking paragraph stops people looking.
- **Expressing universals & marking intentional gaps:** raw prose is *not* the answer — property tests and contracts win because they're executable. Prose only wins on the small residue: rationale, intent, and "undefined on purpose," which belongs colocated with code (Tier 3) or in an ADR at structural scale.

## How it compares to the alternatives

These are trade-off characterizations, not scores — the point is the *shape* of each option, not a ranking. "Cost" and "discipline needed" describe the burden (lower is easier); the rest are strengths (higher is better). Two axes need defining: **rigor** is expressive power — what the approach can state (universals, cross-cutting intent, quality attributes) — not enforcement strength, which is the drift column. **AI fit** is how well the approach's artifacts steer and constrain an agent — which is why vibe coding, the most AI-*native* mode, scores lowest: it hands the agent nothing to be constrained by.

| Approach | Drift resistance | Rigor | AI fit | Cost | Discipline needed | Best fit |
|---|---|---|---|---|---|---|
| **CTDD** (tests + API contract + ADRs) | High | Moderate | High | Low marginal (moderate–high upfront) | High | Backend services behind an API; weak on frontend |
| Full spec-driven development | Low–Medium (as side-document) | High | Moderate | High | High | Mandated written contracts; regulated/audited domains |
| Test-driven development (classic) | High | Moderate | Moderate | Low marginal (moderate upfront) | High | The low-drift core this builds on |
| Behavior-driven development (Gherkin/Cucumber) | High | Moderate | High | High (glue-code tax) | High | Stakeholders co-authoring acceptance criteria |
| Design by contract | High | Moderate | High | Moderate | Moderate | A component (Tier 2), not a whole method |
| Formal methods / verification (TLA+, Coq) | Low–Medium (model-only) → High (refined/extracted) | Very high | Moderate | Very high | Very high | Critical cores — consensus, concurrency, safety |
| Ad-hoc / "vibe coding" (no spec) | None | None | Low | Low now / high later | None | Throwaway prototypes only |

A note on the CTDD row's cost cell, because it's split deliberately: for a team already running behavior tests, contracts, and ADRs, the marginal cost is genuinely low; for a team without them, the upfront cost is real — it buys durable assets, but it isn't free. And "discipline needed: high" is itself a recurring cost — sustained review attention — counted here rather than waved away.

**CTDD** — strongest for backend APIs/microservices specifically: correctness is objective, the API contract is a real agent-readable spec at the boundary, and consumer-driven contract testing covers cross-service drift. It's essentially *TDD upgraded* with agent-reads-the-suite, ADRs, and API contracts. Used on a frontend it loses its main advantage, because the visual/UX layer is exactly where tests can't assert correctness. Its standing trade-offs: the sampling problem, and the fact that every safeguard is review-dependent — sustained discipline is the method's own single point of failure, not merely a team attribute (see "When it's failing: observable signals" for how to tell it's slipping).

**Full SDD** — real rigor (experts catch wrong requirements before code; states universals). Drift is the fatal trade-off when the spec is a side document — the agent implements against a spec that no longer matches reality. (That's also what the table's "AI fit: moderate" means: a spec is maximally agent-readable on day one and decays as it drifts — the fit is front-loaded.) Regeneration-style SDD (Tessl) escapes some of that by making the spec the actively maintained source artifact, but that shifts the cost and review burden onto the spec itself. Worth it only where a written contract is mandatory.

**Classic TDD** — the low-drift core this builds on, minus the rationale layer and the explicit AI role; test-first is the first discipline abandoned under pressure.

**BDD** — executable, business-readable, agent-friendly, but the glue-code maintenance tax is the trade-off. Pays off only where non-technical stakeholders truly co-author scenarios.

**Design by contract** — a *component*, not a methodology (it's Tier 2 above); strong drift resistance, agent treats contracts as hard constraints.

**Formal methods** — the highest rigor that exists, traded against cost and specialist skill that rule it out as a default. One drift caveat the table now carries: a TLA+ model verifies the *design*, not the code — unless the implementation is refinement-checked or extracted from the proof, the model is a side artifact that drifts from the implementation exactly like prose. Right for concurrency protocols, consensus, safety-critical cores; overkill for a CRUD app.

**Vibe coding** — fast and fine for throwaway prototypes; the trade-off is total — nothing anchors intent and the AI's output has no safety net, so it collapses as a way to build anything you'll maintain.

## When to choose which

- **CTDD** — backend services behind an API, reasonably understood requirements, a team that can hold behavior-level-testing discipline (the floor from Part 1 applies: the method assumes that culture exists; it does not create it). The default for most day-to-day service work. This is the sweet spot: objective correctness plus a real agent-readable API contract.
- **Add consumer-driven contract testing (Pact)** — as soon as more than one service depends on another. It's the cross-service drift protection single-repo tests can't provide, and it belongs in the default stack for any real microservice system. At organization scale, though, Pact is an operational program — broker hygiene, provider states, pending-pact management, cross-team ownership — not a checkbox line in a stack diagram.
- **Add design by contract / property tests on top** — the same code but with real invariants: money, quotas, state machines, idempotency, ordering — anything with a "must always hold" rule. Layers *within* CTDD, not a switch away from it.
- **Add formal methods for the critical core only** — the coordination/consistency logic: distributed consensus, transaction protocols, cryptographic or safety-critical logic where a subtle bug is catastrophic. Verify the small dangerous kernel; use CTDD for everything around it.
- **Reach for full SDD** — hard external contracts: public APIs and SDKs other teams build against, protocol/wire-format definitions, and audited domains where a prose spec under document control is the *mandated deliverable format* — not merely because a domain is regulated. Where the mandate is "an auditable record of requirements" rather than a prescribed format, the derived record in the audited-environments annex may satisfy it — verify with the regime first. Even then, keep it scoped to the contract boundary and let tests own behavior behind it.
- **Don't use this for frontend/UI** — where correctness is visual and experiential, tests can't assert it and the method's core advantage evaporates. Use design mocks, visual regression, and manual/UX review there instead.
- **Vibe coding is acceptable** — throwaway prototypes, spikes, and one-off scripts you will not maintain. The moment it's going to live, graduate it to CTDD.
- **When requirements are fuzzy or unstable** — none of the spec-first approaches fit; explore with lightweight prototypes first to *discover* the requirement, then lock it down with the contract and tests once it stabilizes. Don't write a spec for something you don't understand yet.

Rule of thumb: **for backend services, where the Part 1 floor holds, default to CTDD; make the API contract the boundary spec; add Pact the moment services depend on each other; layer property tests/contracts where invariants are real; escalate to formal methods only for the dangerous coordination core; and reserve prose SDD for genuine external contracts.** Match the ceremony to the cost of being wrong.

## Prior art: where this sits in the landscape

This isn't fringe — it's one side of a debate that became mainstream across the industry in 2025–2026 under the banner **spec-driven development (SDD)**. SDD emerged as a direct reaction to the same failure mode this doc opens with: "vibe coding" agents that produce plausible code which drifts from intent and decays as projects scale. By 2026, several major tools and ecosystems had shipped some flavor of the idea — GitHub Spec Kit, AWS Kiro, and Tessl most cleanly; Cursor, OpenSpec, BMAD, and Google Antigravity get grouped under the banner too, though for some of them "SDD" stretches the term (BMAD is agent-role orchestration; Antigravity's artifacts are agent work-products, not maintained specs). The motivation is settled; the disagreement is over *which artifact is the source of truth* — and that's the exact fault line this doc takes a side on. (Dates matter in this section: the landscape reorganizes quarterly, so the claims below are pinned to when they were verified — mid-2026 — rather than asserted as timeless.)

The most useful map of the prose camp is Böckeler's taxonomy (in the Fowler-site analysis cited below): **spec-first** — write a spec per change, then build; **spec-anchored** — keep the spec alive alongside the code; **spec-as-source** — the spec is the maintained artifact and code is regenerated from it. Part 3's drift critique lands squarely on the middle rung, the maintained side-document. It does *not* land on spec-as-source, whose entire design is that the spec can't silently diverge because it's the mechanism of change (that model's costs are different: review burden, regeneration non-determinism, waterfall creep). And it barely lands on spec-first, because a per-change spec is disposable — nothing is maintained, so nothing drifts; it just goes stale inside its PR, exactly like this doc's own plan.

**The prose-spec-first camp (mainstream).** Keeps a written spec as the driving artifact.

- **GitHub Spec Kit** — Spec → Plan → Tasks → Implement. Mind the say/do gap: GitHub's rhetoric makes the spec "the shared source of truth," but the tool creates a branch per spec — still the default as of early 2026, per its own issue tracker, where users keep asking for a way to turn it off — in practice a living artifact for the lifetime of a change request, not of the feature. That's spec-first, not spec-anchored: functionally, Spec Kit's spec is this doc's disposable plan with more ceremony. Which sharpens the real disagreement — if the mainstream's flagship tool already half-concedes that the prose spec is per-change, the remaining question is *what carries durable behavioral truth after the change lands*. Spec Kit's implicit answer is the code; this doc's answer is the tests plus the contract, and as an agent-readable spec those beat raw code. That is a stronger argument for CTDD than drift alone.
- **AWS Kiro** — a specs workflow around `requirements.md`, `design.md`, and `tasks.md` before any code (its Design phase mirrors the plan + ADR layer here).
- **Tessl** — the radical end *as stated*: the spec is the *primary maintained artifact* and code is regenerated from it. This is the strongest form of the position this doc argues against — though note it's Tessl's thesis more than its shipped emphasis: the company's own January 2026 launch put a skills registry and package manager front and center, its mid-2026 self-description is "agent enablement platform," and the regeneration Framework remained short of general availability per third-party reviews. Note also that the standard objections to spec-as-source are review burden, regeneration non-determinism, and waterfall creep — *not* drift, which is the disease that model is designed to cure by making the spec the mechanism of change. (Martin Fowler's write-up notes that some SDD workflows generate more Markdown than anyone can review, giving a false sense of control — the review-burden objection, and the same concern this doc is built around.)

- **Specmatic ("Contract-Driven Development")** — the name-adjacent neighbor, one search away from this doc's name, and the spec-as-source camp's executable wing: it turns the API specification itself (OpenAPI/AsyncAPI/proto/WSDL) into generated contract tests and service virtualization, so implementations can't drift from the spec's *shape*. Two fences, both worth stating plainly. First, CTDD is not contract testing: contract tests verify boundary shape and are one tier of this stack — Specmatic is in fact a perfectly good way to wire Tier 2's "validation must be enforced" requirement — while the behavior tests carry the *semantics* as independent assertions no specification can generate (`capture_releases_remainder_when_partially_captured` is not derivable from a schema). Second, the direction differs: Specmatic derives its tests *from* the spec, one source of truth; CTDD keeps two sources deliberately — the contract for shape, the behavior suite for meaning — because a generated test can only ever restate its generator.

**The test-centric camp (this doc's side).** Treats executable tests as the source of truth the agent implements against. Now an active research area called **agentic TDD**:

- **TDAD (Test-Driven AI Agent Definition)** — a methodology for building *tool-using LLM agents*, not backend services: a human writes a behavioral specification, one agent compiles it into executable tests, a second agent refines the *prompt* until they pass, and mutation testing plus hidden held-out tests validate the tests themselves. Two qualifications. Architecturally, TDAD is spec-first-with-executable-compilation — the maintained source is the human-written spec and the tests are generated *from* it — so it is not evidence for "tests as the maintained source of truth"; what it does support is the narrower, load-bearing claim that executable verification beats prose verification, and that the tests themselves need validating. Its division of labor — the human owns "specification authorship and test review," the AI owns implementation — is this doc's circularity guard (weakness #3) in another domain, and its hidden-test split (real compliance measured on tests the implementing agent never saw) is the strongest known guard for the wrong-encoding half of that weakness. Beware a naming collision: a separate 2026 paper, "TDAD: Test-Driven Agentic Development," is a different system — the code↔test impact-analysis work cited under "Working with large suites."
- **TDFlow** and standard unit-to-acceptance agentic TDD workflows — same principle, different packaging.

**The bridge — EARS** (Easy Approach to Requirements Syntax): a constrained way of writing acceptance criteria that maps roughly 1:1 onto test cases. It's the industry's other answer to "how do we make prose executable" — a different tool aimed at the same seam this doc fills with property tests and contracts.

**Where this doc sits.** It's the test-centric counter-position: the mainstream bet on prose-spec-as-source-of-truth (in rhetoric more than in practice — see the Spec Kit note above); this doc takes the test-as-source-of-truth side. The critique it's built on (maintained prose specs drift) is the standard objection to the mainstream. The mainstream's counter-critique — tests catch unit behavior but miss architectural, contract-level, and quality-attribute violations — is patched here with ADRs, contracts, and weakness #7's executable-NFR treatment; the quality-attribute part is the least covered of the three, and it's named as a weakness rather than claimed solved. The one deliberate concession to prose-as-record is weakness #8's audit trail — addressed (so far only as a proposal) with derived, append-only records rather than a maintained spec, the doc's own move applied to its hardest case. So this approach is a deliberate attempt to get the test-centric camp's low drift *and* cover the system-level blind spot the prose camp keeps pointing at.

## Bottom line

For backend APIs and microservices — on a team that already holds behavior-level testing — use the API contract plus tests as the verified, low-drift spec the agent reads and implements against. Keep the customer's business spec as intent. Design the contract first, add consumer-driven contract tests the moment services depend on each other, and push universals down to executable forms — property tests and schema validation — wherever you can. Let prose carry only rationale and intentional gaps: colocated notes for local decisions, ADRs for service-boundary ones. Give non-functional and security budgets an explicit home — executable where possible — because the agent cannot respect a constraint no artifact states. In audited domains, see the annex: the record of intent should be derived and append-only, never a maintained prose spec. Escalate rigor for the distributed-coordination core, and don't stretch the method over a frontend. Remember the agent's summary is a convenience to interrogate, not a truth to trust.


---

## Annex: CTDD in audited environments

Weakness #8 is a different kind of concern from #1–#7: those are about the method's epistemics; this is governance. It gets an annex as a conscious choice — the method's core story shouldn't grow compliance machinery inline — and everything here is **proposed, not yet validated in practice**; treat it as an unreviewed design.

**Archive the plans.** In regulated repos, promote the plan from disposable to archived: approved implementation plans, with their gate approvals, become a numbered, append-only record alongside the ADRs. Append-only is what makes this safe — like an ADR, an archived plan records what was required *at a point in time*, never what the system does now, so it can't drift. This half needs no annotation discipline and is the low-risk part of the answer.

**Derive the record, don't maintain it.** At each release, tag the suite and contract and emit a signed manifest mapping requirement IDs to the tests and contract versions that encode them. Concretely: the requirement IDs come from the ticket or contract-clause system; tests carry them as attributes/traits (e.g. `[Trait("req", "PAY-123")]`); a generator walks the suite at release and emits the mapping. This is a **derived requirements-traceability matrix** — better than a maintained one, because the artifact side regenerates, but the annotations themselves are maintained metadata with known drift modes: a requirement reworded under a stable ID silently changes what the link means; untagged tests leave holes the matrix can't see; and nothing but review stops a copy-pasted wrong tag. Partial enforcement is possible (the plan gate requires new tests to declare their requirement ID; the generator flags untagged tests in audited modules) — but this is the least proven idea in this document. If the annotation cost isn't acceptable, fall back to the archived plans alone.

**Know where the boundary sits.** Whether a derived record satisfies a given auditor is a question for the specific regime and contract. Some mandate a prose SRS under document control as the *format* — that mandated-format case is the genuine SDD carve-out in Part 3: reach for SDD where the deliverable format is prescribed, not merely because a domain is "regulated." Verify with the regime before betting the compliance story on the manifest.

---

**APPENDIX — THE PLUGIN**

---

## Appendix: running CTDD as skills

CTDD is packaged as a small **plugin** — three skills, one hook, and a plan linter — so the discipline runs itself instead of living only in this doc.

> **Status pin — update on every release.** This appendix describes plugin **v0.7.4** (2026-07-13). Measured at this version: the three skill descriptions total ≈1.0k tokens (always in the agent's context); the skill bodies are ≈3.9k / 2.2k / 1.6k tokens (`ctdd-change` / `ctdd-tests` / `ctdd-review`, loaded only on trigger, one at a time); a full plan is ≈325 tokens; the hook reminder is ≈28 tokens per spec-surface edit; script output only costs when a script is run. These numbers are re-measured at every re-pin — quoted anywhere else they would be stale within two releases. **Shipped:** skills `ctdd-change` (with `references/adr-template.md`), `ctdd-tests`, `ctdd-review`; the spec-edit hook — `PostToolUse` plus a `PreToolUse` companion that catches Write *overwrites* of existing test files — off by default as `hooks.json.example`, with its own 26-case test suite (fixture/golden files under test directories are asserted to fire; spec-dir data files are asserted silent); `scripts/check-plan.py`, an omission detector for the implementation plan (with a trivial-vs-diff cross-check); `scripts/gen-authz-matrix.py`, deriving the identity × operation authorization matrix from the OpenAPI contract, with a `--check` drift gate; `scripts/check-spec-surface.py`, a deterministic diff-surface inventory (tests, contracts, ADRs — renames and deletions included, patterns shared with the hook) that `ctdd-review` runs first and triviality calls answer to; trigger eval sets in `evals/` (24 / 24 / 21 cases, not yet run in CI). The hold-out ships as a mandatory plan decision plus record — *sealing* it is CI's job by design, not a missing feature. **Described in this document but not yet shipped:** gate telemetry and churn-on-refactor instrumentation (the "When it's failing" signals are not yet observable from the plugin); weakness #8's plan archiving and release-manifest generator; the `mitigates:` frontmatter + generated version of the table below. If this line is stale, trust the repo, not this appendix — a runtime description that overstates its runtime would be doc↔code drift in a document about doc↔code drift.

The division of labor across documents is deliberate, so each fact has one home: this document is the *rationale*; the skills are the *runtime*; the plugin **README is the operating manual** — installation, the quick-start walkthrough, the artifact-ownership table, and the plan-mode and trigger-tuning notes live there, not here.

- **`ctdd-change`** — drives a backend change end to end: read the existing contract and the relevant slice of tests → draft the contract change → produce a pre-coding implementation plan (risk call, NFR budgets, hold-out decision, changed tests shown old-vs-new — trivial skips are declared visibly) for review → write behavior-level tests → implement to green → present the tests and contract for human review as the spec. Prompts for an ADR on structural decisions, handles standalone ADR requests, and runs bug fixes as regression-test-first.
- **`ctdd-tests`** — writes and reviews tests as the spec: enforces behavior-level naming, flags brittle/implementation-coupled and mock-heavy tests, checks test↔contract alignment, distinguishes characterization observations (`currently_*`) from asserted intent, and adds property tests for invariants — including the contract-derived authorization matrix (every role × every endpoint, expected allow/deny).
- **`ctdd-review`** — the reviewer's side: runs the PR checklist against a finished diff, reading the tests and contract as the spec under review — changed tests as changed requirements, contract diffs as boundary changes, new behavior without a behavior-level test as uncovered — and an implicated-but-unstated NFR budget, or a missing hold-out record on a high-risk diff, as a finding rather than a pass.

An optional `PostToolUse` **hook** (shipped off by default, opt-in per team) adds the one enforcement that doesn't depend on a skill staying in context: once enabled, modifying an existing test file (Edit, or a Write overwrite caught by a PreToolUse existence check) or touching any contract file mechanically injects a reminder that a spec artifact just changed and what CTDD attaches to that. It's off by default because it fires on every relevant edit, in every session — valuable for a team bought into CTDD, needless interruption for one that isn't.

The one-line rule for choosing: use `ctdd-change` when the unit of work is *a change* (a feature, endpoint, handler, bug); use `ctdd-tests` when the unit of work is *tests themselves*; use `ctdd-review` when the unit of work is *judging a finished change*. `ctdd-change` calls `ctdd-tests` for you when it's time to write tests. A condensed example of the pre-coding implementation plan is embedded in the `ctdd-change` skill and in the README's quick start.

### Where each weakness is enforced

Part 2 names eight weaknesses; the skills are where their mitigations actually run (#7's prompts shipped in v0.4.0; #8 remains named-but-unenforced — the table says so). This table is itself a maintained mapping, accepted as the one deliberate exception and pinned to the status line above; generating it from skill frontmatter is an open item. The mapping, so a reviewer can check the runtime against the rationale:

| Weakness (Part 2) | Enforcement point in the skills |
|---|---|
| #1 Tests are a sample | `ctdd-change` step 2 presents its reading as "correct me," never ground truth; `ctdd-tests` pushes invariants into property tests |
| #2 Can't say "undefined on purpose" | Invariant-note step in `ctdd-change`; `ctdd-tests` boundary rule (one colocated sentence, nothing more) |
| #3 Circularity | The pre-coding plan gate (wrong *direction*) plus the closing step-9 human review of tests + contract in `ctdd-change` (wrong *encoding*); the plan's mandatory hold-out line — required / requested / declined — with `ctdd-review` treating a missing record on a high-risk diff as a finding (sealing the hold-out is CI's job by design); `ctdd-review` checks a test/code pair against the business intent, not against each other; the spec-edit hook, where enabled, flags Edit and Write-overwrite modifications of existing tests (Bash-mediated edits are outside hook reach); mutation testing on the critical core in `ctdd-tests`; back-translation of load-bearing diffs (tests read back out as a requirement sentence) in `ctdd-change` step 9 and the `ctdd-review` circularity guardrail |
| #4 Untested load-bearing behavior | `ctdd-change` guardrail: thin coverage is flagged, characterization tests first (marked `currently_*` as observations, not intent); `ctdd-review` escalates diffs in thin-coverage areas; Pact at service boundaries |
| #5 Preservation vs. creation | Proposed tests reviewed in the plan before code exists; changed tests called out as spec changes by `ctdd-change`, the hook (where enabled), and `ctdd-review` |
| #6 Distributed-systems core | `ctdd-change` guardrail: escalate to property tests, messaging contract tests, and human review |
| #7 NFRs & security requirements | Prompted in the runtime since v0.4.0: the plan carries a mandatory NFR-budgets line ("none" must be stated, never implied); `ctdd-tests` proposes contract-derived authorization-matrix tests and SLO checks (existence and shape only); `ctdd-review` dimension 8 treats an implicated-but-unstated budget as a finding, not a pass. Since v0.6.0 the authz matrix has a deterministic generator (`gen-authz-matrix.py`, with a `--check` drift gate for CI); SLO/retention checks remain repo/CI work the skills demand but don't run |
| #8 No record-of-intent for audit | Not yet enforced in the skills — open items: a regulated-repo mode in `ctdd-change` that archives approved plans append-only instead of discarding them; a release-manifest generator mapping requirement IDs → tests and contract versions |

## Design decisions and rejected alternatives

The record of *why* the method and the plugin are shaped this way — including the paths not taken. It exists so a reviewer can attack a decision on its merits instead of guessing at intent, and so the reasoning survives the sessions it was made in. Each entry is a decision, its alternative, and the reason the alternative lost.

**Why CTDD at all, rather than adopting an existing SDD framework.** This started as a survey of the landscape — Spec Kit, Superpowers, OpenSpec, BMAD — and a working recommendation to tier by change size: TDD-first as the floor for production-path work, a persisted spec (Superpowers or plan mode) at ~4-file features, and a Spec Kit + Superpowers "hybrid" only for cross-team or externally-audited work. CTDD is what fell out of taking the floor seriously: if TDD-first already gives a runnable contract and an audit trail at near-zero overhead, and the heavier frameworks mostly add a *prose* spec that then drifts, the question becomes why maintain the prose artifact at all on the backend. The frameworks weren't wrong; they were aimed at a problem (human-readable up-front specification) that executable artifacts solve better where the domain is testable. CTDD is the floor promoted to a method, not a new framework competing with them.

**Why the name changed from "hybrid."** The approach was originally called "the hybrid" (Spec Kit for spec/plan/tasks + Superpowers for the implementation loop). That name described a *composition of two other tools*, which stopped being accurate once the method dropped the maintained prose spec entirely. "Contract- and test-driven" names what the method actually asserts — the contract and tests are the source — rather than which tools it was assembled from. Residual "hybrid" wording in earlier drafts was a naming-drift bug, not a second concept.

**Why the workflow reads before it designs the contract.** An earlier draft ordered the steps "contract first, then read the existing tests." That inverted understanding and design: it had the agent proposing a boundary change before reading the boundary that exists. The fix was to make "read what exists" precede "draft the contract change," and to define "contract-first" as *before tests and implementation*, not *before understanding*. The rejected order optimized for a tidy slogan over the actual dependency.

**Why a pre-coding plan gate instead of trusting the tests.** The method's own weakness #3 is circularity: tests and code can agree on the wrong thing. The alternative — write tests, write code, review the result — catches this too late, once both artifacts already encode the same mistake. The gate moves the review to the cheapest point, before either exists, where a human corrects intent rather than untangling agreement. This is why the gate is load-bearing and not ceremony, and why plan mode is called out as the ideal host for it.

**Why a separate `ctdd-review` skill rather than folding review into `ctdd-change`.** Review and authoring are different jobs with a deliberate separation the method relies on — the author shouldn't be the sole judge of whether their tests are the right spec. Two drivers (change, review) delegating to one craft skill (tests) keeps that separation in the runtime, not just the prose. The rejected single-skill design would have quietly merged the two roles the plan gate and the closing review are meant to keep apart.

**Why the spec-edit hook ships off by default.** The hook is the only enforcement that survives context rot — it fires mechanically when a spec artifact is edited, regardless of whether the skill is still salient. But it fires on *every* relevant edit in *every* session, and this plugin is meant for company-wide and possibly external use. An always-on reminder is valuable to a team bought into CTDD and pure interruption to one that isn't. Shipping it as `hooks.json.example` (opt-in per team) rather than active-by-default trades a little discoverability for not annoying colleagues who never asked for it — the right default when the annoyance is unsolicited and the benefit is opt-in. Contract-only narrowing is documented for teams that want the signal without the test-edit noise.

**Why characterization tests are marked, not just written.** "Add characterization tests first" is easy to say and ambiguous in practice: a pinned observation of current behavior can encode a bug, and an agent reading the suite as spec would faithfully preserve it as if it were intent. Marking them (`currently_*`) makes the observation-vs-intent distinction machine-readable, so a failing characterization test raises a human question ("was that intent or accident?") instead of triggering a silent update in either direction. The unmarked alternative loses exactly the information that keeps weakness #4 from silently becoming weakness #3.

**Why the rationale, README, and skills are kept as separate homes.** An earlier version carried the full tooling manual inside this essay, which duplicated content the README and skills already owned and created the same drift surface the method argues against. The split — rationale is the *why*, README is the *operating manual*, skills are the *runtime* — gives each fact one home. The traceability table above is the deliberate exception: it's rationale-native (it maps argument to enforcement) so it stays here.

**Why skill prose is frozen (v0.5+).** The skills' real budget is the agent's *attention across rules*, not the word count: instruction-following degrades before size limits are reached, and a rule that isn't followed is a disabled check that still looks like coverage — this document's own named anti-pattern. So new guidance must displace old rather than accumulate, and mechanisms that can live elsewhere do: scripts and CI carry the deterministic checks, this document carries the proposed-not-built list. Three consecutive releases grew the skill bodies; the freeze is the correction, and any exception has to argue for its tokens against everything already there. The first granted exception (v0.7.0) is the red-state check in the change workflow — run new tests before implementing and observe them fail — two sentences judged worth their tokens because weakness #3's cheapest failure mode is a test that never failed; it displaced nothing.

**Scope held, not expanded.** Frontend/UI was considered and deliberately excluded, repeatedly, because the method's foundational claim — tests assert correctness — is false where correctness is visual. Extending CTDD to the frontend would require a different verification substrate (visual regression, interaction contracts) the method doesn't provide, so the honest move is a hard scope line rather than a weak generalization. This is a limit, not an oversight.

**Still open.** License selection (internal-use note vs. an OSS license) and whether the plugin manifest should carry a team/org identity rather than an individual author — both are distribution decisions deferred to the maintainer, not method questions.

---

## References

- Understanding Spec-Driven Development: Kiro, spec-kit, and Tessl — Martin Fowler site, Birgitta Böckeler (the load-bearing source for the Prior Art taxonomy): https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- Spec-Driven Development (SDD): The Definitive 2026 Guide — BCMS (vendor listicle; background color only, not load-bearing): https://thebcms.com/blog/spec-driven-development
- Spec-driven development with AI: open source toolkit — GitHub Blog: https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- GitHub Spec Kit Documentation: https://github.github.com/spec-kit/
- Contract Driven Development — Specmatic documentation: https://docs.specmatic.io/contract_driven_development.html
- Test-Driven Development with AI Agents: A Practical Guide (2026) — Fundesk: https://www.fundesk.io/test-driven-development-ai-agents-guide
- Test-Driven AI Agent Definition (TDAD) — arXiv: https://arxiv.org/abs/2603.08806
- TDAD: Test-Driven Agentic Development (code↔test impact analysis; a different system from the TDAD above, despite the acronym) — arXiv: https://arxiv.org/abs/2603.17973
- TDFlow: Agentic Workflows for Test Driven Development — arXiv: https://arxiv.org/pdf/2510.23761
- My TDD Workflow with Agents — From Unit to Acceptance Tests — Medium: https://abhinavmanc.medium.com/my-tdd-workflow-with-agents-556af6574a22
