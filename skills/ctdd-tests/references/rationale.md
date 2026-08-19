# CTDD tests rationale

This file preserves explanations removed from the always-loaded `SKILL.md`.
It is not part of the execution procedure.


## Repository-owned test conventions

- Test framework, assertion library, fixture style, naming, paths, and runner are repository facts rather than CTDD-method rules.
- Applicable `CLAUDE.md` and `.claude/rules/` files carry persistent project instructions; target project configuration and adjacent tests verify that those instructions match the executable repository.
- A framework-specific specimen in the always-loaded skill can dominate a framework-neutral instruction and leak its syntax into another stack.
- The skill therefore teaches case derivation and takes syntax only from the target repository. Add a framework reference only for a CTDD-specific mechanism that nearby tests cannot reveal, such as a required marker, filter, lifecycle constraint, or evidence-capture command.

## Guardrails (source lines 25–31)

- Tests function as an executable specification only when they constrain behavior visible outside the implementation.
- The test skill owns test craft while the change and review siblings own end-to-end implementation and diff review.
- Human-authored hold-outs reduce shared-reasoning and shared-computation errors when visible tests and implementation come from the same agent.

## Routing and outputs (source lines 19–40)

- Caller-visible behavior, rather than whether assertion text changes, separates a craft repair from a specification amendment.
- Altitude repair changes assertions while preserving behavior, so routing on assertion edits sends valid craft work to the wrong lane.
- A craft-edit disclosure lets review distinguish an altitude or determinism repair from an undisclosed requirement change.
- A failed characterization observation requires a human decision when caller-visible behavior actually moved because the old observation can represent either intent or accident.

## Ordered workflow (source lines 42–69)

- Behavior-level names act as readable specification lines only when the assertions cross the same observable boundary.
- A behavior-sounding name paired only with mock verification remains implementation-coupled.
- Deterministic control of clocks, IDs, and randomness keeps the executable specification reproducible.
- A regression test must fail before the fix so the run demonstrates that the test detects the reported defect.


## Blocked-state discipline (source lines 71–79)

- An unclear API or expected outcome is an unresolved intent decision, not permission for the test writer to invent the contract.
- A hard public-boundary test, pervasive mocks, or setup larger than the rule is design pressure. The test skill reports that pressure; production redesign belongs to `ctdd-change`.
- Compilation failure cannot demonstrate that an executable assertion detects the intended defect, so a compile-only stub precedes RED evidence.
- Manual testing, coverage, code inspection, and tests written after implementation can provide useful information, but they do not replace witnessed RED for a case assigned `must fail before implementation`.
- Preservation pins and characterization observations run in the opposite direction: they establish current behavior by passing before refactor. Applying the new-behavior RED rule to them would reject valid evidence.
- Exploratory code can answer feasibility questions, but retaining it as the implementation biases the later test toward code that already exists. Treat exploration as disposable before the approved test-first implementation.
- Simplicity, existing untested code, time already spent, and schedule pressure do not change the evidence direction already assigned from the kind of work being performed.

## Test review (source lines 96–106)

- Reviewing altitude, names, contract coverage, interaction coupling, determinism, and contract alignment catches different ways a test can encode the wrong specification.
- A test-contract disagreement requires an intent decision because silently editing either artifact hides a specification change.

## Special test forms (source lines 108–112)

- Property runs sample generated inputs and search for counterexamples; they do not prove a universal mathematically.
- Authorization-matrix generation is finite conformance enumeration rather than property testing.
- An operation with no allow row can look exhaustively covered while omitting every authorized path.
- Mutation survivors expose assertions that do not protect required behavior, while equivalent mutants cannot be killed by any test, and chasing one produces an implementation-detail assertion.
- An executable SLO check needs metric, percentile, workload, environment, and threshold to define a reproducible constraint.
- Project-approved tools avoid introducing an unvetted generator, runner, or platform dependency.

## Characterization and preservation (source line 113)

- Characterization tests make existing behavior visible before refactor without claiming that the behavior is desired.
- The `currently_` marker distinguishes provisional observation from confirmed intent for humans, review rules, and evidence tooling.
- Preservation pins remain ordinary intent tests because the behavior is already confirmed and must remain specified after refactor.
- Promotion changes an observation into a requirement, so it requires the same gate as any other specification amendment.

## Scope boundary

- Tests preserve and constrain behavior; the approved business requirement supplies new intent.
- Visual, experiential, and load-test correctness require different tools even when state logic remains assertable.
