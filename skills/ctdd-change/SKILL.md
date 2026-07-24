---
name: ctdd-change
description: >-
  Use for "implement this endpoint", "add this to the service", "fix this backend bug", "change this API", "modify this handler", "migrate this flow", "refactor this service",
  "implement the review comments", "deprecate this event field", "write an ADR", or "CTDD this". Use for backend APIs, handlers, consumers, domain rules, contract rollouts,
  and structural decisions. Reject "review this PR", "review these tests", "fix this pipeline", "change this Dockerfile", and "fix this CSS layout"; route them to
  ctdd-review, ctdd-tests, infrastructure tooling, or UI work.
---
# CTDD: drive a backend change
Rationale, not procedure: `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/rationale.md`.
## Routing
- Route a test-only task to `ctdd-tests`.
- Route review of an existing diff, branch, PR, or MR to `ctdd-review`.
- Treat testable state logic as backend-style behavior regardless of deployment tier.
- For a standalone ADR request, skip the change workflow and execute **Standalone ADR procedure**.
## Unordered guardrails
Do not infer an order among these condition-triggered rules.
- Do not claim a test, build, gate, checker, or subagent result without a run completed and read in the current turn.
- Inspect a subagent diff before accepting its result.
- Treat the business requirement as the source of intent.
- Do not change uncovered behavior silently.
- Name the tests that detect every behavior you claim to preserve.
- Invoke `ctdd-tests` before creating, changing, renaming, or deleting a test.
- Require property tests, boundary contract tests, and human review for retries, ordering, eventual consistency, async messaging, or partial failure.
- Stop on incompatible claims about the same observable constraint.
- Resolve an artifact conflict against the business requirement through an approved amendment.
- Read `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/colocated-notes.md` before writing a colocated invariant or external-fact note.
## Output contract
| Output name | Exact path | Required shape |
|---|---|---|
| Pre-plan statements | `stdout` | Baseline statement: `Baseline: branch=<name>; target=<name>; diff-base=<commit>; staged=<summary>; unstaged=<summary>; untracked=<summary>.` Intent statement: `Business requirement: <one or two sentences>.` Current-behavior reading: `Current behavior:` plus exact path/test bullets or one greenfield bullet, ending `Correct this reading before I plan.` |
| Trivial-risk declaration | `stdout` and PR/MR description | `Risk: trivial — <reason>. Skipping the plan gate.` |
| Implementation plan | `${CLAUDE_PROJECT_DIR}/docs/plans/<name>.md`, `stdout`, and PR/MR description when `docs/plans/` is ignored | Decision summary; `BLOCKING`; `Proceeding unless you object`; Risk level; Existing behavior; Assumptions; Uncovered or ambiguous; New-behavior tests; Preservation pins; Contract changes; NFR budgets; Hold-out with `result:`; conditional ADR draft; Files likely to change. Name `<name>` as `<TICKET>-<kebab-slug>` or `<YYYY-MM-DD>-<kebab-slug>` without a ticket. Use `references/plan-format.md` for field rules. Print the full plan plus path outside plan mode; print the verbatim decision summary plus path inside a plan-mode approval surface. |
| Plan pointer | PR/MR description when `docs/plans/` is tracked | `CTDD-Plan: docs/plans/<name>.md` |
| ADR | `${CLAUDE_PROJECT_DIR}/docs/adr/NNNN-<kebab-slug>.md` | Render `references/adr-template.md` with Context, Decision, and Consequences. |
| Contract change | Exact repo-relative contract path listed in the plan | Valid OpenAPI, JSON Schema, protobuf, AsyncAPI, Pact, or repository-native contract syntax. |
| Test change | Exact repo-relative test path listed in the plan | Behavior-level test names and assertions produced under `ctdd-tests`. |
| Test evidence logs | Red state: `${CLAUDE_PROJECT_DIR}/docs/plans/<name>.redstate.log`; pin state: `${CLAUDE_PROJECT_DIR}/docs/plans/<name>.pinstate.log` | Complete raw output from the named new-behavior or preservation-pin run. |
| Review packet | `stdout` | `Business requirement: <text>`; `Back-translation: <text or n/a>`; `Plan: <repo-relative path or n/a>`; `Plan check: <final checker line or n/a>`; `Red state: <final verdict or n/a>`; `Pin state: <final verdict or n/a>`; `Spec surface: <Verdict line>`; `Verification: <command => result or NOT RUN>; ...`; `Hold-out: <passed, failed, declined by human, or not required>`. |
| Colocated note | Exact repo-relative source or contract path listed in the plan | One sentence stating one universal rule, deliberate gap, or durable external fact. |
## Ordered change workflow
Execute steps 0–10 in order.
Before step 6 approval, write only the step 6 plan file.
0. **Establish the baseline.**
   1. Record the current branch, target branch, and staged, unstaged, and untracked files.
   2. Set `diff-base` to `HEAD` for uncommitted work and to the target-branch merge-base for branch, PR, or MR work.
   3. Treat an intentional review diff as input.
   4. Stop and report unrelated target-file edits as contamination.
   5. Print the Baseline statement.
1. **Confirm intent.**
   1. Print the Intent statement.
   2. Stop for an answer when the business requirement is ambiguous.
2. **Read the existing slice.**
   1. Read the relevant contract, tests, changed files, routes, messages, and domain terms.
   2. Print the Current-behavior reading when existing artifacts were found.
   3. Print the Current-behavior reading with one bullet, `greenfield; no existing contract or tests found`, when nothing exists.
3. **Classify the change.**
   1. Classify as trivial only when the diff is code-only, behavior-preserving, covered by named existing tests, contains no test or contract change, and produces no colocated note.
   2. Classify every added, changed, deleted, or renamed test or contract as non-trivial.
   3. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git <baseline>` when a diff exists.
   4. Print the Trivial-risk declaration when the classification is trivial and either no diff exists or the checker reports no test or contract surface.
   5. Add the same declaration to the PR/MR description when the condition in step 3.4 holds.
   6. Skip to step 8 when the condition in step 3.4 holds.
4. **Draft the decision inputs.**
   1. Draft the approach, scope boundary, and highest risk inside the future plan.
   2. Read `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/adr-rules.md` when the change contains a structural decision.
   3. Draft the structural ADR inside the future plan when step 4.2 fires.
   4. Draft the contract delta inside the future plan.
   5. State backward compatibility for every contract delta.
   6. Include the consumer contract delta for a cross-service change.
5. **Handle special lanes.**
   1. For a bug fix, require a short complete plan whose `New-behavior tests` section names the regression test.
   2. Route a changed existing assertion as an amendment that shows its old and new assertion.
6. **Write and gate the implementation plan.**
   1. Read `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/plan-format.md`.
   2. Leave plan mode before writing or updating the canonical plan.
   3. Treat every harness plan file as non-authoritative.
   4. Write the Implementation plan to its exact path.
   5. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" "${CLAUDE_PROJECT_DIR}/docs/plans/<name>.md"`.
   6. Fix every checker failure.
   7. Print the complete plan verbatim followed by its path outside a plan-mode approval surface.
   8. Copy the canonical decision summary verbatim and append its path inside a plan-mode approval surface.
   9. Add the Plan pointer when `docs/plans/` is tracked.
   10. Commit the plan file when `docs/plans/` is tracked.
   11. Paste the complete plan into the PR/MR description when `docs/plans/` is ignored.
   12. Stop for explicit approval.
   13. Treat approval as authorization to execute the plan file.
7. **Apply approved artifacts and create test evidence.**
   1. Re-check the working tree against step 0.
   2. Stop when a target file changed outside the approved plan.
   3. Write each approved contract or ADR artifact to its exact planned path.
   4. Invoke `ctdd-tests`.
   5. Skip steps 7.6–7.11 when the plan says `Preservation pins: none`.
   6. Write preservation pins against the current implementation.
   7. Run the pins before replacing preserved behavior.
   8. Save the complete run to the Pin-state evidence path, using a runner setting that prints one line per test (a summary-only log names no test, so the checker can verify nothing — e.g. `dotnet test --logger "console;verbosity=detailed"`, `pytest -v`, `go test -v`).
   9. Verify pins with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <pin-log> --tests-from <plan-path> --expect-pass`.
   10. Apply the preservation-only conversion.
   11. Re-run the same pins.
   12. Skip steps 7.13–7.17 when the plan says `New-behavior tests: none`.
   13. Write the new-behavior tests.
   14. Run the new-behavior tests before implementing new behavior.
   15. Save the complete run to the Red-state evidence path, with per-test output as in 7.8.
   16. Verify red state with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <red-log> --tests-from <plan-path>`.
   17. Stop when a new-behavior test passes before implementation.
8. **Implement remaining behavior and verify.**
   1. Implement only the approved behavior.
   2. Do not weaken an assertion to obtain green.
   3. Run the contract validator.
   4. Run the relevant tests.
   5. Run the build.
   6. Re-run every preservation pin listed in the plan when a plan exists.
   7. Amend the plan with the old and new assertion or contract delta when an approved assumption, clause, or assertion is wrong.
   8. Re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" "${CLAUDE_PROJECT_DIR}/docs/plans/<name>.md"` when step 8.7 fires.
   9. Obtain approval before changing the affected artifact when step 8.7 fires.
9. **Produce the review packet.**
   1. Stop for the human's sealed hold-out result when the plan says `required`.
   2. Set Hold-out to `not required`, `passed`, `failed` (blocks approval), or `declined by human` (waiver) from the plan and human result.
   3. Run the contract validator.
   4. Set its Verification result to `NOT RUN — no validator found` when none exists.
   5. Run the relevant tests.
   6. Run the build.
   7. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" "${CLAUDE_PROJECT_DIR}/docs/plans/<name>.md"` when a plan exists.
   8. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <red-log> --tests-from <plan-path>` when new-behavior tests exist.
   9. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <pin-log> --tests-from <plan-path> --expect-pass` when preservation pins exist.
   10. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git <baseline>`.
   11. Stop and reclassify when its inventory exceeds the approved plan.
   12. Set Back-translation to one sentence from the changed tests or to `n/a — no test diff`.
   13. Print the Review packet in its exact shape.
   14. Invoke `ctdd-review` for the reviewer-side evaluation.
10. **Write a colocated note only when triggered.**
   1. Write no note for behavior already expressed by a test or contract.
   2. Write one Colocated note for one universal rule, deliberate gap, or durable external fact.
## Standalone ADR procedure
1. Read `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/adr-rules.md`.
2. Gather Context, Decision, and Consequences.
3. Find the next ADR number under `${CLAUDE_PROJECT_DIR}/docs/adr/`.
4. Render `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/adr-template.md`.
5. Write `${CLAUDE_PROJECT_DIR}/docs/adr/NNNN-<kebab-slug>.md`.
