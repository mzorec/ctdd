---
name: ctdd-change
description: >-
  Use when the deliverable is changed backend behavior: "implement this endpoint", "add this to the service", "fix this backend bug", "change this API", "modify this handler",
  "migrate this flow", "refactor this service", "implement the review comments", "deprecate this event field", "write an ADR", or "CTDD this". Covers backend APIs, handlers,
  consumers, domain rules, contract rollouts, and structural decisions, with the tests, contracts, and ADRs that ship with them. Route here whenever production code or a
  contract changes, even when the request names only tests. Reject test-only work that leaves observable behavior unchanged — "write tests for this", "pin current behavior
  before refactoring", "de-flake this test" — and route it to ctdd-tests. Reject judging an existing PR, MR, diff, branch, commit, or staged set and route it to ctdd-review.
  Reject pipeline, Dockerfile, deployment, build-tooling, and visual-only work.
---
# CTDD: drive a backend change
`python3` on PATH is a dead stub on many Windows installs; fall back to `py -3` or the full `python.exe` path. Load a reference only where a step below names it. Never load `references/rationale.md` during a change.
## Routing
- Route a task whose deliverable is only tests, with observable behavior unchanged, to `ctdd-tests`.
- Route judging an existing diff, branch, commit, PR, or MR to `ctdd-review`. Implementing its feedback stays here.
- Treat testable state logic as backend-style behavior regardless of deployment tier.
- For a standalone ADR request, skip the change workflow, read `references/execution.md`, and execute its **Standalone ADR procedure**.
## Unordered guardrails
Do not infer an order among these condition-triggered rules.
- Do not claim a test, build, gate, checker, or subagent result without a run completed and read in the current turn; inspect a subagent diff before accepting its result.
- Treat the business requirement as the source of intent.
- Do not change uncovered behavior silently.
- Name the tests that detect every behavior you claim to preserve.
- Invoke `ctdd-tests` before creating, changing, renaming, or deleting any test file; never write a test file from this skill.
- Require property tests, boundary contract tests, and human review for retries, ordering, eventual consistency, async messaging, or partial failure.
- Stop on incompatible claims about the same observable constraint.
- Resolve an artifact conflict against the business requirement through an approved amendment.
- Do not approve your own plan, and do not issue the `ctdd-review` verdict on your own diff — loading its procedure here is still you.
## Output contract
| Output name | Exact path | Required shape |
|---|---|---|
| Pre-plan statements | `stdout` | Baseline: `Baseline: branch=<name>; target=<name>; diff-base=<commit>; staged=<summary>; unstaged=<summary>; untracked=<summary>.` Intent: `Business requirement: <one or two sentences>.` Current-behavior reading: `Current behavior:` plus exact path/test bullets, or the one bullet `greenfield; no existing contract or tests found`, ending `Correct this reading before I plan.` |
| Trivial-risk declaration | `stdout` and PR/MR description | `Risk: trivial — <reason>. Skipping the plan gate.` Emit only through step 3.6. |
| Implementation plan | `${CLAUDE_PROJECT_DIR}/docs/plans/<name>.md`, and PR/MR description when `docs/plans/` is ignored | Every section and field rule of `references/plan-format.md`, in the order that file displays. |
| Plan pointer | PR/MR description when `docs/plans/` is tracked | `CTDD-Plan: docs/plans/<name>.md` |
| Decision prompt | interactive question when offered, else `stdout` | 2–4 exclusive options, one recommended with a one-line reason, free text always accepted. A selection is a message from the human and counts as an answer; a harness accepting a plan is not. |
| Gate presentation | `stdout` | `Plan: <path> (<tier>)`, the decision summary verbatim, the categorical `Risk:` line, then the `Hold-out` block in full. The summary names every other decision the human may refuse, one line each; offer those sections and print them on request. Then anything the human must act on. |
| Approval record | `stdout` | `Approved by: <human message quoted>; plan: docs/plans/<name>.md.` |
| ADR | `<resolved ADR directory>/NNNN-<kebab-slug>.md` | `references/adr-template.md` rendered with Context, Decision, and Consequences. |
| Contract change | Exact repo-relative contract path listed in the plan | Valid OpenAPI, JSON Schema, protobuf, AsyncAPI, Pact, or repository-native contract syntax. |
| Test change | Exact repo-relative test path listed in the plan | Behavior-level test names and assertions produced under `ctdd-tests`. |
| Test evidence logs | Red state: `${CLAUDE_PROJECT_DIR}/docs/plans/<name>.redstate.log`; pin state before: `${CLAUDE_PROJECT_DIR}/docs/plans/<name>.pinstate.log`; pin state after: `${CLAUDE_PROJECT_DIR}/docs/plans/<name>.pinstate-after.log` | Complete raw output from the named run. |
| Review packet | `stdout` | The exact field list in `references/execution.md`, assembled at step 9. |
| Colocated note | Exact repo-relative source or contract path listed in the plan | One sentence stating one universal rule, deliberate gap, or durable external fact. |
## Ordered change workflow
Execute steps 0–10 in ascending order. Until the step 6 Approval record exists, the only file you write is the step 5 plan file. An amendment re-enters at the lowest invalidated step.
0. **Establish the baseline.** Enter: a change request exists. Emit: Baseline statement. Stop: unresolvable base, contamination.
   1. Record the current branch, target branch, and staged, unstaged, and untracked files. Report it when the current branch is the target branch: the change is landing where it would be reviewed from.
   2. Set `diff-base` to `HEAD` for uncommitted work and to the target-branch merge-base for branch, PR, or MR work.
   3. Stop and ask which base to use when the target branch is absent, disputed, or has no merge-base.
   4. Treat an intentional review diff as input, and stop and report unrelated target-file edits as contamination.
1. **Confirm intent.** Enter: step 0 printed the Baseline statement. Emit: Intent statement. Stop: ambiguity.
   1. Stop for an answer as a Decision prompt when the business requirement is ambiguous, and never proceed on an assumed answer.
2. **Read the existing slice.** Enter: step 1 has an unambiguous requirement. Emit: Current-behavior reading. Continue: always.
   1. Read the relevant contract, tests, changed files, routes, messages, and domain terms, plus every ADR named by an `ADR-NNNN` marker in them.
   2. Derive current behavior from the contract and tests; use the implementation only for behavior neither states. Offer the reading for correction, never as ground truth.
   3. Use the greenfield bullet when nothing exists. Scan this repository's ADR titles when the change adds contract surface: new surface carries no markers.
3. **Classify the change.** Enter: step 2 printed the reading. Emit: Trivial-risk declaration, or nothing. Continue: to step 4 unless 3.6 fires.
   1. Treat the change as plan-gated unless every condition in 3.2–3.5 holds.
   2. Require a diff that already exists against `diff-base` and that contains the complete requested change; anything still to be written is plan-gated.
   3. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git <diff-base>` and require exit `0` with `Verdict: no test/contract/ADR surface touched.`; treat exit `1` and exit `2` alike as plan-gated.
   4. Require a code-only, behavior-preserving diff: rename, comment, formatting, or mechanical extraction only. A changed limit, validation rule, generated file, or file of unknown type is plan-gated.
   5. Require named existing tests that already cover every touched behavior, and no colocated note.
   6. Print the Trivial-risk declaration, add it to the PR/MR description, and go to step 8.
   7. Return to 3.1 as plan-gated when any later step contradicts 3.4 or 3.5.
4. **Draft the decision inputs.** Enter: step 3 did not fire 3.6. Emit: draft content held for step 5. Continue: after 4.5.
   1. Read `references/worked-change.md` and copy its artifact shapes.
   2. Draft the approach, scope boundary, and highest risk inside the future plan.
   3. When the change decides a service boundary, data ownership, cross-service protocol, or persistence structure, read `references/adr-rules.md` and draft the structural ADR inside the future plan.
   4. Draft the contract delta inside the future plan, state backward compatibility for every delta, and name every affected consumer or write `consumers: none — <reason>`.
   5. Draft the test strategy: new-behavior tests and preservation pins. Route a changed existing assertion as an amendment carrying its old and new form.
5. **Write and validate the plan.** Enter: step 4 produced every draft. Emit: Implementation plan, Plan pointer. Stop: checker failure.
   1. Read `references/plan-format.md`.
   2. Leave plan mode before writing or updating the canonical plan. Treat every harness plan file as non-authoritative.
   3. Write the Implementation plan to its exact path. Its tier is derived from what it declares, not chosen. For a bug fix, require a short complete plan whose `New-behavior tests` section names the regression test.
   4. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" "${CLAUDE_PROJECT_DIR}/docs/plans/<name>.md"`, fix every reported failure, and re-run until it exits `0`.
   5. Add the Plan pointer and commit the plan file when `docs/plans/` is tracked; paste the complete plan into the PR/MR description when `docs/plans/` is ignored and one exists.
6. **Gate.** Enter: step 5 exited `0`. Emit: Gate presentation, Approval record. Stop: mandatory, until 6.4 is satisfied.
   1. Print the Gate presentation outside a plan-mode approval surface. The plan file stays the complete artifact.
   2. Copy the canonical decision summary verbatim into any plan-mode surface, with its path.
   3. Stop for explicit approval. Ask it as a Decision prompt: approve, approve with changes, reject. Write no contract, test, ADR, or production file, and execute no later step, until 6.4 is satisfied.
   4. Require an affirmative message from the human approving this plan. Your own restatement, silence, a subagent verdict, and a passing checker are not approval.
   5. Treat approval as authorization to execute the plan file.
7. **Apply approved artifacts and create test evidence.** Enter: step 6 printed the Approval record. Emit: contract, ADR, tests, pin-state logs, red-state log. Stop: 7.2, 7.8, 7.12.
   1. Re-check the working tree against step 0.
   2. Stop when a target file changed outside the approved plan.
   3. Write each approved contract or ADR artifact to its exact planned path.
   4. Skip 7.5–7.8 when the plan's `Preservation pins` names no test.
   5. Invoke `ctdd-tests` to write the preservation pins against the current implementation.
   6. Run the pins before replacing preserved behavior, save the complete run to the pin-state path. Verify pins with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <pin-log> --tests-from <plan-path> --expect-pass`.
   7. Apply the preservation-only conversion when the plan contains one; re-run the same pins to the pin-state-after path and verify them the same way.
   8. Stop on any state other than pin pass; read `references/execution.md`.
   9. Skip 7.10–7.12 when the plan's `New-behavior tests` names no test.
   10. Invoke `ctdd-tests` to write the new-behavior tests.
   11. Run them before implementing new behavior, save the complete run to the red-state path. Verify red state with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <red-log> --tests-from <plan-path>`.
   12. Stop on any state other than intended red; read `references/execution.md`.
8. **Implement and verify.** Enter: step 7 satisfied every applicable evidence lane — pin pass for every preservation pin the plan names, intended red for every new-behavior test the plan names — or step 3.6 fired. Emit: verification results. Stop: 8.6.
   1. Implement only the behavior approved at step 6, or nothing beyond the declared diff in the trivial lane. Replace any compile-only stub from step 7 with that implementation, and add no other production code.
   2. Do not weaken, delete, skip, or retarget an assertion to obtain green.
   3. Run the contract validator, the focused tests, the broader suite, and the build in the current turn; re-run every preservation pin named in the plan to the pin-state-after path; record `NOT RUN — <reason>` for anything absent, and never reuse an earlier turn's output.
   4. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git <diff-base>`.
   5. Compare its inventory with `Files likely to change`.
   6. Stop and reopen the gate when the approved specification is wrong, when 8.5 exceeds the plan, or when requested review feedback falls outside approved scope (feedback inside scope re-enters at the lowest invalidated step, no new plan): amend the plan file with the old and new form, re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" <plan-path>`, return to step 6, and resume at the lowest invalidated step after re-approval.
9. **Produce the review packet.** Enter: step 8 produced current-turn results. Emit: Review packet. Stop: 9.1. Changed tests are changed requirements and contract diffs are boundary changes: the packet presents them as the spec, not as code.
   1. Stop for the required sealed hold-out result from the named runner, asking write / decline / defer as a Decision prompt. Resolve it to `passed`, `failed`, `declined by human`, or `NOT RUN — <reason>`; only the human declines, an unavailable runner is `NOT RUN`, and `failed` blocks.
   2. Set Back-translation to one sentence derived from the changed tests alone, beside the business requirement so the human compares prose to prose, or to `n/a — no test diff`.
   3. Read `references/execution.md` now even if read earlier; re-run its checkers and assemble its exact packet.
   4. Stop and hand the `ctdd-review` verdict to the human: name the final diff and wait. Never load `ctdd-review` here, and never dispatch it yourself unless asked — a review this session commissions and frames is not independent, whichever context runs it.

10. **Write a colocated note only when triggered.** Enter: step 9 printed the packet. Emit: Colocated note, or nothing.
   1. Write no note for behavior already expressed by a test or contract.
   2. When the change leaves one universal rule, deliberate gap, or durable external fact not expressed by a test or contract, read `references/colocated-notes.md` and write one Colocated note.
## Evidence and break points
Before implementing, classify the run as **pin pass**, **intended red**, **compile red**, **wrong red**, **premature green**, **pin fail**, or **weakened green**. Only pin pass and intended red authorize step 8. A checker that cannot run, cannot read its input, or exits `2` leaves its claim unverified. `references/execution.md` carries the required action for every state and break point, the packet assembly, and the standalone-ADR procedure.
