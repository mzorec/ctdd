# ADR rules

Load this file only when `SKILL.md` step 4.3 fires or the Standalone ADR procedure starts.

1. Record one structural decision per ADR.
2. During the change workflow, draft the template fields inside the implementation plan and write no ADR file before the step 6 Approval record exists; write it at step 7.3.
3. During the standalone ADR procedure, write the ADR after gathering its fields.
4. Write the approved or standalone ADR to `docs/adr/NNNN-<kebab-slug>.md`.
5. Find `NNNN` by incrementing the highest existing four-digit ADR number.
6. Render `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/adr-template.md`.
7. Set `Status` to `Proposed` unless the user explicitly supplies another valid status.
8. Set `Date` to the current date.
9. Name the known deciders; write `Not recorded` when none are supplied.
10. Write `Context` in two to five sentences describing the situation, constraints, and considered options.
11. Write `Decision` in one or two sentences stating the chosen structure.
12. Write `Consequences` with benefits, costs, closed options, and follow-up work.
13. Keep the rendered ADR to one page or less.
14. Do not use an ADR to describe current behavior.
15. Do not rewrite the Context, Decision, or Consequences of an accepted or superseded ADR.
16. To reverse a decision, create a new ADR and change only the old ADR's `Status` to `Superseded by NNNN`.
17. Mark the tests and contracts the decision governs with a comment naming it — `ADR-NNNN` and one line of what it decides — in each repository's own comment syntax. The marker moves with the file and is the only pointer between a decision and the code it constrains that cannot rot independently of what it points at. It reports relevance, not enforcement: a marked test usually exercises the area rather than asserting the decision.
