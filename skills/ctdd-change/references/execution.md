# Execution reference

Loaded from `SKILL.md` at a step-7 breakpoint, at step 9 packet assembly, or for
a standalone ADR.

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
| Broken pin: a named pin passed before the change and fails after it | Stop. The change broke preserved behavior. This is the finding, not a plan defect: do not amend the pin away and do not weaken it. Report it and return to 8.1 with the implementation, never to step 6 with the plan. |
| Weakened green: green obtained by relaxing, deleting, skipping, or retargeting an assertion | Stop and reopen the gate under 8.6; never keep the relaxed assertion silently. |
## Break points
| Signal | Required action |
|---|---|
| A checker cannot run, cannot read its input, or exits `2` | Treat the claim it would have verified as unverified: plan-gated at step 3, blocked at steps 5 and 7, `NOT RUN — <reason>` in the packet. |
| A target file changed outside the approved plan (7.2) | Stop. Name the files. Revert them, or amend under 8.6 and re-approve; 7.2 does not self-clear. |
| A run produced no per-test lines, only a summary | Unverified in both lanes: `not found in the log` is neither a pass nor a failure. Re-run with per-test reporting. |
| 7.12 stops and the approved line is not `red pause: skip` | Print `git diff <diff-base> --stat`, the full diff (to a file beside the plan when long), and the intended change as a two-column table — `File`, and `Intended change` as a full descriptive sentence naming what happens there — one row per existing production file, dependency-ordered from the planned paths in the repo's own structure, no architecture assumed, cleanup last. Under `phased`, split it into one such table per phase, each under a `## Phase N — <what changes, and what is true afterwards that was not before>` heading, and print no separate file list beside it. Never per-file blocks or label-prefixed records. Name any behavior-flow step no row serves; never call a phase a group. Append the intended-change table to the plan as `## Intended change`, under one line saying so and dating it after approval — a record of what will be built, never part of what was approved. Close with the few things most worth the human's eye. Ask to proceed as a Decision prompt. A requested change is an 8.6 amendment; proceed only on an affirmative human message. |
| 8.7 stops with `red pause: phased` and a phase's implementation is complete | Print the phase's diff and its evidence — build result, every pin green, the intended-red set changed only by tests the phase's own files serve — and ask to continue as a Decision prompt; recommend nothing. An in-scope correction re-enters at 8.1; out of scope reopens the gate under 8.6. The last phase's checkpoint may fold into 9.4. |
| Plan mode owns the write location | Leave plan mode, write the canonical plan to `docs/plans/`, and keep the harness copy non-authoritative. |
| A planned test is difficult to write or duplicates an existing test | Hand the case to `ctdd-tests`; add no production seam and delete no coverage to make it easy. |
| Verification surfaces failures unrelated to this change | Report them with the failing command, exclude them from the packet's pass claims, and do not fix them under this plan. |
| The required hold-out runner is unavailable | Record `result: NOT RUN — <reason>` and leave the packet unresolved. This is not a decline: only the human declines, and only then does the plan carry `declined by human` with the human-verified expected values. Never record `passed`. |
## Standalone ADR procedure
1. Read `references/adr-rules.md`.
2. Gather Context, Decision, and Consequences.
3. Resolve the ADR directory with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --adr-dir`; stop and ask when it reports ambiguity. Find the next number in it.
4. Render `references/adr-template.md`.
5. Write `<resolved directory>/NNNN-<kebab-slug>.md`.

## Review packet assembly — SKILL.md step 9.3
1. Re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" <plan-path>` when a plan exists.
2. Re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <red-log> --tests-from <plan-path>` when the plan names new-behavior tests. When it names preservation pins, re-run both `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <pin-log> --tests-from <plan-path> --expect-pass` and `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" <pin-after-log> --tests-from <plan-path> --expect-pass`.
   Record `n/a — plan declares none` for a lane the plan does not name; never run a lane with no names, which is a usage error rather than a pass.
3. Re-run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git <diff-base>` and derive the packet's `Deviations:` field: one entry per diff file absent from `Files likely to change`, per planned file untouched, per slice or 7.12 row landed through a different approach, and per 8.6 amendment (old → new in one clause), each `<subject> — <delta> — <reason>`; `none` only when all are clean. Disclosure is not authorization: out-of-plan scope reopens the gate under 8.6. Run `check-adr-drift.py` on the same base; an ADR that lost its last marker is re-marked, disclosed, or superseded.
4. Resolve `Red pause:` to the quoted releases of the 7.12 pause and each phase checkpoint, `skipped at gate`, or `n/a — trivial`.
5. Emit the packet in the exact shape the output contract declares.

## Review packet shape — emitted to `stdout`
`Business requirement: <text>`; `Back-translation: <text or n/a — no test diff>`; `Plan: <repo-relative path or n/a — trivial>`; `Approval: <quoted approval or n/a — trivial>`; `Review: <n/a or commissioned by the author — independence not established>`; `Plan check: <final checker line or n/a>`; `Red state: <final verdict or n/a — plan declares none>`; `Pin state before: <final verdict or n/a — plan declares none>`; `Pin state after: <final verdict or n/a — plan declares none>`; `Spec surface: <Verdict line>`; `Verification: <command => result or NOT RUN — <reason>>; ...` for the contract validator, focused tests, broader suite, and build; `Hold-out: <passed, failed, declined by human, NOT RUN — <reason>, or not required>`; `Red pause: <quoted release(s) | skipped at gate | n/a — trivial>`; `Deviations: <none | <subject> — <delta> — <reason>; …>`; `Residual risk: <text or none>`.
