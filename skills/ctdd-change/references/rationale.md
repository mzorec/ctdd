# CTDD change rationale

This file preserves explanations removed from the always-loaded `SKILL.md`.
It is not part of the execution procedure.

## Source lines 29, 31, and 33

- The API contract and tests precede implementation because tests specify preservation while the business requirement and plan specify creation.
- Contract-first means specifying the boundary before tests and implementation, not before understanding the existing system.
- Assertable correctness is the scope boundary because visual and experiential correctness require a different evaluation method.

## Source line 37

- Guardrails appeared before the workflow because post-compaction loading retained the opening part of the skill.

## Source lines 41–50

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

## Source lines 54 and 72

- A regression test is the executable specification of a bug fix and preserves the edge case after the fix ships.
- A bug fix with a regression test changes the specification surface, so it belongs in the short-plan lane rather than the trivial lane.
- An existing test that intentionally asserts the reported behavior turns the task into a specification change rather than a bug fix.

## Source lines 76 and 80

- Existing asserted behavior changes through an amendment so “update the test to match” cannot silently redefine the requirement.
- Cross-artifact disagreement is a specification defect only when two artifacts make incompatible claims about the same observable constraint.
- Different artifacts can state compatible constraints at different layers.
- Quietly changing the easiest artifact until CI passes hides the unresolved specification decision.

## Source lines 84–96

- Line count does not determine risk because a one-line assertion edit changes the specification while a large code-only rename can preserve it.
- The plan file is the only pre-approval write because the reviewer needs a durable artifact to approve.
- Visible trivial classification lets the human veto skipped ceremony.
- The baseline distinguishes intentional review input from unrelated contamination.
- The intent statement remains the source of what to build.
- The current-behavior reading is provisional because retrieval can be incomplete.
- A greenfield service seeds its contract and tests through the planned workflow.
- The design brief belongs inside the plan instead of becoming a second maintained document.
- The contract delta precedes tests because services and consumers build against the boundary.

## Source line 98

- The plan gate catches wrong direction before implementation cost accumulates.
- The repository plan remains authoritative when a harness exposes its own plan file.
- Writing the repository plan before entering plan mode prevents the harness file from replacing the CTDD record.
- Verbatim presentation prevents a second plan from drifting away from the file.
- Updating the file before re-presenting keeps newly learned facts inside the artifact being approved.
- Approval authorizes execution of the plan file rather than a newly composed plan.
- A repository-relative PR/MR pointer remains portable across CI checkouts.
- Rooted filesystem paths prevent module-directory changes from writing plans and evidence to the wrong location.
- The plan stops being maintained after the change ships because it records the approved implementation decision rather than current behavior.

## Source lines 100–106

- Red-state evidence proves a new test detects the absence of requested behavior.
- A new test that passes before implementation either describes existing behavior or fails to assert the planned change.
- Pin-state evidence proves a preservation test describes the implementation before replacement.
- A compiling stub lets the test fail for the behavioral reason rather than a missing-symbol error.
- Reopening the gate prevents a late discovery from becoming an unreviewed specification edit.
- Back-translation lets the reviewer compare the business requirement with the requirement encoded by changed tests.
- Colocated prose is restricted because executable contracts and tests resist drift better than comments.

## Source lines 114–131

- `plan-format.md` is authoritative because `check-plan.py` validates that exact section structure.
- The decision summary leads because a reviewer needs the non-routine decision and risk before the supporting inventory.
- `BLOCKING` separates questions that prevent implementation from decisions the human can veto cheaply.
- The risk line exposes how much ceremony the change receives.
- Existing-behavior citations make thin retrieval visible.
- Separate new-behavior and preservation headings prevent a checker from applying the wrong pass/fail expectation.
- Old and new assertions expose changed requirements that a test name can hide.
- Explicit NFR and hold-out fields turn silence into a reviewable decision.
- An omitted mandatory section represents a skipped decision rather than an implicit “none.”

## Source lines 135–137

- ADRs remain append-only because they record a decision at a point in time rather than the current system state.
- Superseding a prior ADR preserves the historical decision while recording its replacement.
