# CTDD change rationale

This file preserves explanations removed from the always-loaded `SKILL.md` and operational references.
It is not part of the execution procedure.
Sections are named after the rule they explain; they carry no line numbers, which rot on every edit of the body.

## Scope and contract-first

- The API contract and tests precede implementation because tests specify preservation while the business requirement and plan specify creation.
- Contract-first means specifying the boundary before tests and implementation, not before understanding the existing system.
- Assertable correctness is the scope boundary because visual and experiential correctness require a different evaluation method.

## Guardrail placement

- Guardrails appeared before the workflow because post-compaction loading retained the opening part of the skill.

## Evidence and current-turn runs

- A checker verdict matters because an unverified log proves only that a command ran.
- A preservation pin that fails before conversion describes behavior the current code never had.
- A pending hold-out creates the appearance of a guard without its result.
- The baseline is re-read because the working tree can change while a plan waits for approval.
- Current-turn runs prevent stale, partial, or delegated reports from masquerading as evidence.
- A subagent diff is evidence because its summary can omit or misstate the actual change.
- Tests written against the old implementation record behavior before replacement removes the evidence source.
- Characterization tests distinguish observed behavior from intended behavior through the `currently_*` marker.
- Distributed-system behavior receives stronger checks because examples alone cover too little of retries, ordering, eventual consistency, and partial failure.
- CTDD replaces a hand-written technical implementation specification, not the customer business requirement.

## Bug-fix lane

- A regression test is the executable specification of a bug fix and preserves the edge case after the fix ships.
- A bug fix with a regression test changes the specification surface, so it belongs in the short-plan lane rather than the trivial lane.
- An existing test that intentionally asserts the reported behavior turns the task into a specification change rather than a bug fix.

## Amendments and artifact conflict

- Existing asserted behavior changes through an amendment so “update the test to match” cannot silently redefine the requirement.
- Cross-artifact disagreement is a specification defect only when two artifacts make incompatible claims about the same observable constraint.
- Different artifacts can state compatible constraints at different layers.
- Quietly changing the easiest artifact until CI passes hides the unresolved specification decision.

## Baseline, classification, and design inputs

- Line count does not determine risk because a one-line assertion edit changes the specification while a large code-only rename can preserve it.
- The plan file is the only pre-approval write because the reviewer needs a durable artifact to approve.
- Visible trivial classification lets the human veto skipped ceremony.
- The baseline distinguishes intentional review input from unrelated contamination.
- The intent statement remains the source of what to build.
- The current-behavior reading is provisional because retrieval can be incomplete.
- A greenfield service seeds its contract and tests through the planned workflow.
- The design brief belongs inside the plan instead of becoming a second maintained document.
- The contract delta precedes tests because services and consumers build against the boundary.

## The plan gate

- The plan gate catches wrong direction before implementation cost accumulates.
- The repository plan remains authoritative when a harness exposes its own plan file.
- Writing the repository plan before entering plan mode prevents the harness file from replacing the CTDD record.
- Verbatim presentation prevents a second plan from drifting away from the file.
- Updating the file before re-presenting keeps newly learned facts inside the artifact being approved.
- Approval authorizes execution of the plan file rather than a newly composed plan.
- A repository-relative PR/MR pointer remains portable across CI checkouts.
- Rooted filesystem paths prevent module-directory changes from writing plans and evidence to the wrong location.
- The plan stops being maintained after the change ships because it records the approved implementation decision rather than current behavior.

## Red state, pin state, and colocated prose

- Red-state evidence proves a new test detects the absence of requested behavior.
- A new test that passes before implementation either describes existing behavior or fails to assert the planned change.
- Pin-state evidence proves a preservation test describes the implementation before replacement.
- A compiling stub lets the test fail for the behavioral reason rather than a missing-symbol error.
- Reopening the gate prevents a late discovery from becoming an unreviewed specification edit.
- Back-translation lets the reviewer compare the business requirement with the requirement encoded by changed tests.
- Colocated prose is restricted because executable contracts and tests resist drift better than comments.

## Plan tiers

`check-plan.py` derives small, medium or large from the categorical line and the two evidence headings, and requires a different section set for each. The tier is derived rather than written because `trivial` was once claimed over an absent diff, and a self-declared size would leak the same way. Tiers shrink documentation, never evidence: both test headings, the risk line, the verification commands and the approval gate are required at every tier, and a plan naming no test in either lane derives large rather than the lightest tier — a plan with no evidence must not also be the one with the fewest sections.

## Plan format

- `plan-format.md` is authoritative because `check-plan.py` validates the section set its tier requires — `required_for(tier)`, a per-tier subset, not every section at every tier.
- The decision summary leads because a reviewer needs the non-routine decision and risk before the supporting inventory.
- `BLOCKING` separates questions that prevent implementation from decisions the human can veto cheaply.
- The risk line exposes how much ceremony the change receives.
- Existing-behavior citations make thin retrieval visible.
- Separate new-behavior and preservation headings prevent a checker from applying the wrong pass/fail expectation.
- Old and new assertions expose changed requirements that a test name can hide.
- Explicit NFR and hold-out fields turn silence into a reviewable decision.
- An omitted mandatory section represents a skipped decision rather than an implicit “none.”

## ADR lifecycle

- ADRs remain append-only because they record a decision at a point in time rather than the current system state.
- Superseding a prior ADR preserves the historical decision while recording its replacement.

## Rationale moved from `adr-rules.md`

- ADRs stay short so one record represents one decision.
- ADRs record structural choices and tradeoffs rather than behavior already represented by contracts and tests.
- Superseding instead of rewriting preserves the decision history.

## Rationale moved from `colocated-notes.md`

- Colocated prose is restricted because it has no executable drift detector.
- Stable identifiers survive upstream repository refactors better than mutable file paths.
- Time-bound provenance belongs in point-in-time artifacts; source comments carry only durable rules.

## Rationale moved from `plan-format.md`

- The decision summary leads so the approval gate exposes direction, risk, compatibility, ADR work, and human obligations before file detail.
- `BLOCKING` separates unanswered choices from assumptions the human can veto.
- Exact existing-behavior citations expose thin retrieval.
- Separate new-behavior and preservation sections keep red-state and pass-before-and-after evidence in distinct lanes.
- Old and new assertions expose requirement changes hidden by unchanged test names.
- Explicit NFR and hold-out fields turn silence into a reviewable decision.
- Independently written hold-outs break the shared-implementation path between production code and agent-authored tests.
- Human-verified expected values reduce shared-computation risk when a required hold-out is declined, but they do not replace independent tests.

## Trivial lane requires an existing diff

- Triviality is a property of a diff, so a change that has not been written yet has nothing to classify; the earlier wording let an unwritten change declare itself trivial and skip the gate.
- `check-spec-surface.py` exit `1` and exit `2` are treated alike because an unverified triviality claim and a contradicted one are equally unproven.
- The trivial lane exists for finishing work already on disk, not for choosing to skip planning.

## Approval

- Approval is defined by who sends it because every other candidate — a restatement, a green checker, a subagent verdict, silence, a harness accepting a plan-mode surface — can be produced by the agent itself.
- Self-approval and self-review would make the gate and the independent review circular.

## Evidence states

- A red run is not evidence by itself: a compile error, a broken fixture, and the planned assertion failure all print as failure, and only one of them proves the test detects the missing behavior.
- A premature green means the test describes existing behavior or fails to constrain the change, which is a specification finding rather than a test bug.
- A weakened assertion changes the requirement, so it reopens the gate instead of being applied silently.

## Empty plan sections

- An empty section is written on its heading line because a bullet reading `none` is extracted by `check-redstate.py` as a test name and produces a false unverified verdict.
- The section still has to appear, because an omitted section is a skipped decision rather than an implicit none.

## Worked example

- Models copy examples more reliably than prose, so the artifact shapes exist once, in full, including the two states that are easiest to accept wrongly: compile red and premature green.
