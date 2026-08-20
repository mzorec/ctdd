# ADR rules

Load this file only when `SKILL.md` step 4.3 fires or the Standalone ADR procedure starts.

1. Record one structural decision per ADR.
2. During the change workflow, draft the template fields inside the implementation plan and write no ADR file until an Approval record exists for the current plan revision — an amendment voids the previous one — and write it at step 7.3.
3. During the standalone ADR procedure, write the ADR after gathering its fields.
4. Resolve the ADR directory once with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --adr-dir` and write the approved or standalone ADR to `<that directory>/NNNN-<kebab-slug>.md`. Never assume a path: writing into a directory the repository does not use restarts the numbering beside an existing series.
5. Find the next number by incrementing the highest existing ADR number in that same directory, matching its width: a repository numbering `001`–`014` continues at `015`, not `0001`, because the reader strips leading zeros and `001-` and `0001-` would resolve to the same decision. Start at `0001` only when the directory is empty.
6. Render `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/adr-template.md`.
7. Set `Status` to `Proposed` unless the user explicitly supplies another valid status, and to `Accepted` once the change carrying it has shipped. Nothing else promotes an ADR, so one left `Proposed` for life never reaches rule 15's append-only freeze and its Context and Decision stay rewritable.
8. Set `Date` to the current date.
9. Name the known deciders; write `Not recorded` when none are supplied.
10. Write `Context` in two to five sentences describing the situation, constraints, and considered options.
11. Write `Decision` in one or two sentences stating the chosen structure.
12. Write `Consequences` with benefits, costs, closed options, and follow-up work.
13. Keep the rendered ADR to one page or less.
14. Do not use an ADR to describe current behavior.
15. Do not rewrite the Context, Decision, or Consequences of an accepted or superseded ADR.
16. To reverse a decision, create a new ADR and change only the old ADR's `Status` to `Superseded by NNNN`.
17. Ask `ctdd-tests` to mark the tests the decision governs, and mark the contracts yourself, with a comment naming it — `ADR-NNNN` and one line of what it decides — in each repository's own comment syntax. The marker moves with the file and is the only pointer between a decision and the code it constrains that cannot rot independently of what it points at. It reports relevance, not enforcement: a marked test usually exercises the area rather than asserting the decision.
