# ADR rules

Load this file only when `SKILL.md` step 4.3 fires or the Standalone ADR procedure starts.

1. Record one structural decision per ADR. One change may require several; list every number on the categorical line.
2. During the change workflow, draft the template fields inside the implementation plan and write no ADR file until an Approval record exists for the current plan revision — an amendment voids the previous one — and write it at step 7.3.
3. During the standalone ADR procedure, write the ADR after gathering its fields.
4. Resolve the ADR directory once with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --adr-dir` and write the approved or standalone ADR to `<that directory>/NNNN-<kebab-slug>.md`. Never assume a path: writing into a directory the repository does not use restarts the numbering beside an existing series.
5. Find the next number by incrementing the highest existing ADR number in that same directory, matching its width: a repository numbering `001`–`014` continues at `015`, not `0001`, because the reader strips leading zeros and `001-` and `0001-` would resolve to the same decision. Start at `0001` only when the directory is empty.
6. Render `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/adr-template.md`.
7. Set `Status` to `Accepted` when writing it at 7.3 — the human approved the draft at the gate, and that is the acceptance. Use `Proposed` only for a standalone ADR written outside an approved plan; nothing later promotes one, so a `Proposed` ADR never reaches rule 15's freeze.
8. Set `Date` to the current date.
9. Name the known deciders; write `Not recorded` when none are supplied.
10. Write `Context` in two to five sentences describing the situation and constraints. Write `Options` as the losing alternatives, one line each with why it lost; a forced choice names its constraint and revisit condition.
11. Write `Decision` in one or two sentences stating the chosen structure.
12. Write `Consequences` with benefits, costs, closed options, and follow-up work.
13. Keep the rendered ADR to one page or less.
14. Do not use an ADR to describe current behavior.
15. Do not rewrite the Context, Decision, or Consequences of an accepted or superseded ADR.
16. To reverse or alter what an accepted ADR decided — in part or in full — create a new ADR and change only the old ADR's `Status` to `Superseded by NNNN`, optionally with a one-line cause — `Superseded by NNNN — decided on a misread credential` — so a wrong decision reads as wrong, not merely old. The new ADR's title ends with `(supersedes NNNN)`, making the lineage visible in a directory listing; numbers stay flat and chronological — never sub-numbered. Flip that `Status` in the same change that writes the new ADR, at step 7.3 — a new record superseding one that still reads `Accepted` is an unfinished change, not a later chore. There is no amended status: rules that survive are restated in the new record, and the new Context reconciles the old option list with what is now chosen.
18. A change that removes the last `ADR-NNNN` marker for a decision confirms the decision still holds and re-marks it, or supersedes it under rule 16 — an accepted ADR nothing in the tree names is a decision no later reader will be pointed at. `scripts/check-adr-drift.py` reports it mechanically at packet assembly, from marker removal in the diff rather than a whole-repo audit, which would report never-marked ADRs on every run.
17. Ask `ctdd-tests` to mark the tests the decision governs, and mark the contracts yourself, with a bare `ADR-NNNN` reference in each repository's own comment syntax, placed where that syntax carries ancillary notes rather than the member's own description — `<remarks>`, not `<summary>`; `@see`, not the leading sentence. Carry the identifier alone: never restate what the ADR decides or why, because a restatement is a second copy that drifts from the record it points at, and the reader follows the reference to read the decision in full. The marker moves with the file and is the only pointer between a decision and the code it constrains that cannot rot independently of what it points at. It reports relevance, not enforcement: a marked test usually exercises the area rather than asserting the decision.
