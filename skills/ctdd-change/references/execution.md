# Execution reference

Loaded from `SKILL.md` at a step-7 breakpoint, at step 9 packet assembly, or for
a standalone ADR. The evidence-state and break-point tables are lookups:
`SKILL.md` names the states so the agent can recognize one; this file carries
the required action for each.

## Evidence states
| Observed state | Required action |
|---|---|
| Pin pass: a named pin passes before the change | Proceed; re-run after the change and require the same pass. |
| Intended red: a named new test fails on its planned assertion | Proceed to step 8. |
| Compile red: the test cannot compile because the planned production type or member is absent | Add the smallest compile-only stub that fails as not-implemented, re-run, and require intended red. Implement nothing else. |
| Compile red: the test cannot compile for its own reasons — a wrong `using`, a missing test-project reference, a typo | Fix the test support and re-run. Add no production code and no stub: the production API is not what is missing. |
| Wrong red: the failure comes from setup, environment, a typo, or an unrelated defect | Fix that cause, re-run, and require intended red. A wrong red never unlocks step 8. |
| Premature green: a named new test passes before implementation | Stop. Report whether the behavior already exists or the assertion fails to constrain it, and return to step 6. |
| Pin fail: a named pin fails before the change | Stop. The pin describes behavior the code never had; return to step 6. |
| Weakened green: green obtained by relaxing, deleting, skipping, or retargeting an assertion | Stop and reopen the gate under 8.6; never keep the relaxed assertion silently. |
## Break points
| Signal | Required action |
|---|---|
| A checker cannot run, cannot read its input, or exits `2` | Treat the claim it would have verified as unverified: plan-gated at step 3, blocked at steps 5 and 7, `NOT RUN — <reason>` in the packet. |
| Plan mode owns the write location | Leave plan mode, write the canonical plan to `docs/plans/`, and keep the harness copy non-authoritative. |
| A planned test is difficult to write or duplicates an existing test | Hand the case to `ctdd-tests`; add no production seam and delete no coverage to make it easy. |
| Verification surfaces failures unrelated to this change | Report them with the failing command, exclude them from the packet's pass claims, and do not fix them under this plan. |
| The required hold-out runner is unavailable | Record `result: NOT RUN — <reason>` and leave the packet unresolved. This is not a decline: only the human declines, and only then does the plan carry `declined by human` with the human-verified expected values. Never record `passed`. |
## Standalone ADR procedure
1. Read `references/adr-rules.md`.
2. Gather Context, Decision, and Consequences.
3. Find the next ADR number under `${CLAUDE_PROJECT_DIR}/docs/adr/`.
4. Render `references/adr-template.md`.
5. Write `${CLAUDE_PROJECT_DIR}/docs/adr/NNNN-<kebab-slug>.md`.

## Review packet assembly — SKILL.md step 9.3
1. Re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" <plan-path>` when a plan exists.
2. Re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <red-log> --tests-from <plan-path>` when the plan names new-behavior tests. When it names preservation pins, re-run both `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <pin-log> --tests-from <plan-path> --expect-pass` and `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <pin-after-log> --tests-from <plan-path> --expect-pass`.
   Record `n/a — plan declares none` for a lane the plan does not name; never run a lane with no names, which is a usage error rather than a pass.
3. Re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git <diff-base>` and compare its inventory with `Files likely to change`.
4. Emit the packet in the exact shape the output contract declares.

## Review packet shape — emitted to `stdout`
`Business requirement: <text>`; `Back-translation: <text or n/a — no test diff>`; `Plan: <repo-relative path or n/a — trivial>`; `Approval: <quoted approval or n/a — trivial>`; `Plan check: <final checker line or n/a>`; `Red state: <final verdict or n/a — plan declares none>`; `Pin state before: <final verdict or n/a — plan declares none>`; `Pin state after: <final verdict or n/a — plan declares none>`; `Spec surface: <Verdict line>`; `Verification: <command => result or NOT RUN — <reason>>; ...` for the contract validator, focused tests, broader suite, and build; `Hold-out: <passed, failed, declined by human, NOT RUN — <reason>, or not required>`; `Residual risk: <text or none>`.
