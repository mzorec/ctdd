# ctdd friction findings — session fad73bc1 (PUT /documents/{documentNumber}/processing-status)

Source: one unverified analysis pass over a real ctdd-change session in the `edavki.documentintegration` repository, 2026-11-11 to 2026-11-12. Confirm each finding against the script or skill text before acting on it.

Transcript: `C:\Users\markoz\.claude\projects\C---GitA1EDavki-edavki-documentintegration\fad73bc1-fd4e-4a6e-bf65-7851710512fe.jsonl`

`L<n>` = JSONL line number in the transcript (timestamps UTC). Confidence: **verified** = seen in both the transcript and the skill/script text; **inferred** = the cause or the benefit of the fix is the analyst's reading.

The session had 10 gate presentations:

| Gate | Line | Revision | Amendment | Outcome |
|---|---|---|---|---|
| 1 | L507 | 36733a91e81e | initial plan | "1a, 2b, decline, approve" (L612), not recordable |
| 2 | L830 | 3a2ac318f99c | A1: blocking answers, parallel-route refusal, hold-out decline, ADR reword | approved L838 |
| 3 | L918 | 7c4c3120bcef | A2: wrong OpenAPI pin name and path | approved L920 |
| 4 | L1448 | 760b97baa4df | A3: routes injected into the handler | not approved, more design questions |
| 5 | L1661 | 2eb67ceecc0b | A4: write on `IDocumentRepository`, feature under Documents | user asked about the altitude table |
| 6 | L1720 | 317f3dffa965 | A5: `.ctdd.json` + phases reworded for the checker | user disputed layer order and test altitude |
| 7 | L1807 | 1f835dbdc8c2 | A6: handler tests moved to unit tests | approved L1809 |
| 8 | L2754 | f5e7dc8e87b3 | A7: two types moved beside the port (architecture guard) | "wait what?" (L2756) |
| 9 | L2794 | 363c5eef1469 | A8: the same two types moved to Domain | approved L2802 |
| 10 | L3167 | decedff7b462 | A9: `backendMessage` → `statusMessage` | approved L3175 |

## Previously known findings (from the session itself)

1. The gate presentation after an amendment does not show what changed.
2. The gate's hold-out block shows empty result fields and still recommends `write` after the human declined.
3. No lighter lane for small amendments such as a field rename.
4. `check-spec-surface --plan` lists planned files as untouched (see finding 8 below for the real cause; the session's "misses staged/untracked files" diagnosis was wrong).
5. `check-plan` "UNRESOLVED PATHS" misfires on backticked code and bare directory names.
6. Altitude check layer order needed a manual `.ctdd.json`.
7. Architecture guards were hit only at Phase 3 verification.
8. Step 9.1 hand-check prompt repeated many times while the user asked other questions.
9. Endpoint tests went green a phase early because step-7 stubs already mapped the route.

## Ranked findings

### 1. NEW — Structure is never shown before tests and stubs are written, so design review happened at the red pause
- **What happened:** the user first saw type names, ports, folders and test projects at the 7.12 pause (L1379), after 29 tests and all stubs existed. They then questioned each in turn:
  - L1381 "Why all ProcessingStatuses are in enums why not only the ones that they can set"
  - L1387 "why do we have routes … Routes { get; init; }"
  - L1399 "Isnt it ussualy that this is handler job and it should be injected into handler?"
  - L1456 "ProcessingStatusRepository looks wrong to me"
  - L1553 "endpoint and feature is also ProcessingStatus which is well.. not a feature or endpoint?"
  - L1739 "if it can be covered with persistance test it should be written in persistance not other way around"
- **Cost:** amendments A3–A6, gates 4–7 (about 4,200 words), a second `ctdd-tests` run to move or rewrite all four test files and every stub (L1840–L2075), and a second red-state capture.
- **Responsible text:** `plan-format.md` "Gate-visible sections": "The summary, the `Hold-out` block, `Behavior flow`, `Known gaps`, `Assumptions` and `Uncovered or ambiguous` go to `stdout` in full at step 6.1." `Implementation slices` and `Files likely to change` are not gate-visible, and the 7.12 intended-change table is built only after step 7.
- **Proposed change:** add a gate-visible `Structure` block for medium and large plans: new or changed public types and where they live, ports touched, configuration bindings, test project per test group. Simplest route is to build the 7.12 table at step 5 and print it in `--gate`.
- **Confidence:** verified; the saving is inferred.

### 2. NEW — "approve" typed together with the change never counts; 4 of 10 gates re-approved what the human had just dictated
- **What happened:** L612 "1a, 2b, decline, approve"; L1694 "add .ctdd.json and reword the phases, approve"; L1757 "yes, approve"; L2785 "Domain, approve". Each time the full gate was printed again, e.g. L1720: "You approved before these two changes existed, and the skill requires approval of the exact revision".
- **Responsible text:** `SKILL.md` 6.3 "Offer: approve, approve with changes, reject. Amend the plan, re-run the checker and re-offer on changes"; preamble "an amendment voids the previous one". The label "approve with changes" reads as an approval and never is one.
- **Proposed change:** rename the option to "change, then re-present", or add a conditional approval: when the message states the change and approves, amend, print only the delta, and record `Approved by: "<their message>" (covers the amendment they dictated)`. Stop again only if the amendment went beyond what they dictated.
- **Confidence:** verified.

### 3. Extra evidence for known #1 — six of nine re-presentations were byte-identical to the previous gate block
- **What happened:** gates 3, 4, 5, 8, 9 and 10 printed a checker block identical to the gate before. Gate 6 differed only in the altitude table and gate 7 in seven altitude rows; only gate 2 changed substantive text. About 11,100 words were presented across the ten gates.
- The assistant hand-built a block diff three times to be able to say so (L1444, L2714, L2789).
- **Root cause beyond "no delta":** amendments landed in sections that are not gate-visible, and `plan-format.md` defines no amendment section. The session invented three ("Decided at the gate", "Amended at Phase 3 verification", "Amended at the review packet"); A3–A6 were edited in place with no old/new record.
- **Proposed change:** define one `Amendments` section; on a re-presentation `--gate` prints its newest entry first and "gate-visible sections unchanged since <revision>".
- **Confidence:** verified.

### 4. NEW — Preservation pins are not checked against the repository; a wrong name and path cost gate 3
- **What happened:** the pin run passed (L883), yet the plan named `OpenApiDocument_CarriesNoEmptySummaryOrDescription`, which exists in another class and covers the internal listener's document, at a path that does not exist. The assistant found it by grep (L887–L897).
- **Responsible script:** `check-redstate.py --expect-pass --tests-from` matches bare names and ignores the plan's `path:`; `check-plan.py` never checks that a pin path exists.
- **Proposed change:** at 5.4 fail when a pin's `path:` is missing or does not contain the name; in `check-redstate` require the passing occurrence to come from that file and warn on names that occur in more than one class.
- **Confidence:** verified.

### 5. NEW — The altitude check passed the altitude problem the human cared about, and a plan was reworded only so the checker could find an owner
- **False negative:** seven handler tests were planned in `Application.IntegrationTests`. Layer comes from a path token, so integration and unit projects are both "Application" and matched. The user caught it (L1739); the assistant agreed it was "the wrong altitude" (L1755).
- **Rewording:** the owner is the first backticked token of a slice bullet (`owner = ticks[0]`). Phase 1 began with a `.sql` path and Phase 3 with a route name, so 20 of 29 tests had owner `?`, which silently skips the comparison. The assistant reworded both phases (L1708), which changed the revision and produced gate 6.
- **Responsible text:** `check-plan.py` `layer_of`, `slice_claims`, altitude loop; `ctdd-tests` step 5 "Write each test at the public boundary", with no "cheapest harness that observes it" rule inside a layer.
- **Proposed change:** let `.ctdd.json` declare a harness kind per test project and print it; take the owner from every backticked path in the bullet that resolves to a layer; warn when an owner is `?` while layers are configured; add to `ctdd-tests` step 3 "state the lowest harness that can observe each case".
- **Confidence:** verified.

### 6. NEW — BLOCKING questions reach the gate as one-liners without options, and a non-recommended answer voids the plan just presented
- **What happened:** the user asked L606 "what are blocking things?"; the options appeared only then (L610). The answer "2b" was not the recommendation, so the approval in the same message was lost and gate 2 followed.
- **Responsible text:** the gate-visible list omits `BLOCKING — I will not guess`; the Gate presentation row asks only for "the one-line refusable decisions"; the guardrail "Ask every question as a Decision prompt" is not applied here.
- **Related gap:** `check-plan.py --post-approval` (field rule 11) is named only in `worked-change.md` line 65, not in any `SKILL.md` step, and was never run. After compaction the assistant dropped the BLOCKING heading; the checker reported it as "MISSING sections … decision summary: BLOCKING" (L806), an internal label that does not match the heading.
- **Proposed change:** ask BLOCKING questions as Decision prompts before step 5 ends; print any that remain in `--gate` in full with options; add the `--post-approval` run to `SKILL.md`; rename the label.
- **Confidence:** verified.

### 7. NEW — Step 8.6 says amend and re-gate; with more than one possible fix the agent picked one and was redirected
- **What happened:** after the guard failure the assistant moved two types beside the port and opened gate 8 inside a 1,262-word message. User: L2756 "wait what?", then L2773 "doesnt this belongs to domain?". A8 and gate 9 followed.
- **Responsible text:** `SKILL.md` 8.6 "amend the plan file with the old and new form, re-run `check-plan.py` … return to step 6".
- **Proposed change:** prepend "State the finding and offer the candidate fixes as a Decision prompt before editing the plan"; the gate message after an 8.6 stop leads with the finding.
- **Confidence:** verified.

### 8. NEW — `check-spec-surface --plan` has three more defects, and the session's diagnosis of known #4 was wrong
- **Root cause of "Planned but untouched":** not staging. `--git` runs `git diff --name-status -M <base>` plus `git ls-files --others`, so staged and untracked files are read. The printed list (lines 598–602) compares against `seen`, which holds only classified test/contract/ADR surface, so every planned production file is always listed. Line 577 already has the corrected set but uses it only for the verdict. `IDocumentRepository.cs` appeared in both "Planned but untouched" and "Production files with no `## Intended change` row" in one run (L2848). The assistant told the user "It only sees committed history" (L3384).
- **"Planned" is any backticked path anywhere in the plan** (`plan_paths_from`). The list included a legacy-repo citation `PersonalPortal/Pages/Documents/View.aspx.cs` (L3379), amendment "Old:" paths, and pin files.
- **Contract surface false negative:** `docs/api/document-integration-openapi-v1.json` matches none of `CONTRACT_DEFAULT` in `hooks/spec-edit-guard.py`. No run in the session printed a "Contract surface" section.
- **False "no Intended change row":** `.ctdd.json` and `Api/appsettings.json` (already dirty in the step-0 baseline) were reported (L2860).
- **Proposed change:** print from `_seen`; read planned paths only from `Files likely to change`; match `openapi|swagger|asyncapi` anywhere in the basename; exclude `.ctdd.json` and baseline-dirty files.
- **Confidence:** verified.

### 9. Extra evidence for known #7 — the guard violation existed from the step-7 stubs
- **What happened:** the port returned a feature-folder type from the first stub (L1116, 11-11 21:18) and was found at L2644 (11-12 06:02), three approved revisions later. Assistant: "It would have failed the same way under every earlier revision" (L2771).
- **Responsible text:** 7.10 runs only the named tests; `execution.md` 8.7 evidence is "build result, every pin green, the intended-red set".
- **Proposed change:** name a fast invariant suite in `Verification` and run it at 7.10 and every 8.7 checkpoint; add to 2.1 "read the repository's architecture tests for rules on where new types may live".
- **Confidence:** verified.

### 10. NEW — The two skills contradict each other on compile-only stubs, and the plan engineered a wrong stub to get red
- **Text:** `execution.md`: "Add the smallest compile-only stub that fails as not-implemented"; `worked-change.md`: "throws not-implemented"; `ctdd-tests`: "returning a default, never throwing: a throwing stub reddens every test alike".
- **What happened:** the session followed `ctdd-tests`, with the endpoint mapped and registered. To keep one test red the plan specified a 132-line enum "carrying every `DocumentStatus` name". That was the user's first question at the pause (L1381), and the same wired stubs caused known #9.
- **Proposed change:** one rule in both files: stubs return defaults and may not be shaped to make a test fail; when an honest stub makes a named test pass, record `red: compile red only — constrained by <slice>`. Mark each stub "throwaway, replaced in Phase N" in the 7.12 table.
- **Confidence:** verified; the link to #9 is inferred.

### 11. Extra evidence for known #2 and #8 — after a decline, the hand check has no defined moment or close
- **What happened:** the five values were in the plan from A1 (L763) and listed under gate 2 (L830), which the user approved. The checker block printed `human-verified expected values:` blank at all ten gates, because `gate_presentation` reads `approved_region`, which blanks that field. Step 9.1 then asked for the same values eight times (L2882, L2984, L3002, L3014, L3024, L3057, L3077, L3384). The red-pause prompt was repeated at L1385 and L1391.
- **Responsible text:** `plan-format.md` rule 8 gives no timing; `SKILL.md` 9.1.
- **Proposed change:** on a decline at the gate, print the values in the gate block and let the approval carry the confirmation; 9.1 stops only if values changed. State a pending stop once, then a one-line status.
- **Confidence:** verified.

### 12. NEW — `HOLDOUT_BLOCK` takes the first line starting with "hold-out" anywhere in the plan
- **What happened:** a bullet "- Hold-out: declined by human." matched before the real section; the checker reported "HOLD-OUT NOT ACTIONABLE — missing options:, recommended:" though both were present (L782). The assistant read the checker source and reworded the bullet.
- **Responsible script:** `check-plan.py` line 191 and `HOLDOUT_BLOCK.search(text)`; the same match feeds `approved_region` and the gate block.
- **Proposed change:** locate the block through `_section_bounds`, or require an unindented heading followed by `- decision:`.
- **Confidence:** verified.

### 13. NEW — `.approval.log` is not a log
- **What happened:** appending a second approval gave "APPROVAL STALE — the record approves revision 3a2ac318f99c" (L923), because the checker reads the first `@<rev>`. The file was overwritten, so the history of five approvals is gone. The first record was also rejected for the bare label `"approve"` (L843).
- **Proposed change:** read the last record and keep earlier lines as history; put `(typed at the gate)` in the output-contract template.
- **Confidence:** verified.

### 14. NEW — The plan only grows, three file lists are hand-synced, and the size warning prints on every run
- **What happened:** 33,575 chars (~14 min) at gate 1, 51,161 (~23 min) at gate 10, 54,569 at the end. 8.6 requires "the old and new form". `Files likely to change`, `Implementation slices` and `## Intended change` list the same files; the assistant repaired the last by script twice (L2063, L2859).
- **Proposed change:** make `## Intended change` the single file list after approval; allow a consolidation the checker recognises as such; print the size line only under `--gate`.
- **Confidence:** verified; remedy inferred.

### 15. NEW — Field rule 9 forces invented names for generated files
- **What happened:** the plan named `20261111120000_ProcessingStatus.cs`; the generator stamped `20261112054253`. The assistant renamed two files, the attribute, a folder and a hash line to match the plan (L2196–L2200).
- **Proposed change:** allow a declared `<generated>` path, resolved to the real name in `## Intended change`.
- **Confidence:** verified.

### 16. NEW — `git diff <diff-base> --stat` omits untracked files, which pushed the agent to modify the index
- **What happened:** to show new files in the 7.12 stat the assistant ran `git add -N`, then `git reset -q` to undo it (L1348–L1364), in a repo where the user stages from the IDE during sessions.
- **Responsible text:** `execution.md` 7.12 "Print `git diff <diff-base> --stat`, the full diff".
- **Proposed change:** give a non-mutating recipe (throwaway `GIT_INDEX_FILE`, or a `--stat` mode in `check-spec-surface.py`) and state "never touch the index".
- **Confidence:** verified.

### 17. NEW — `ctdd-tests` has no lane for naming tests for a plan
- **What happened:** `ctdd-change` requires invoking it "before drafting a test path", but `ctdd-tests` writes tests only "under an approved plan". The assistant improvised "Draft-only … write NO test file now" (L403); the step 2 and 3 printouts were not shown, and the altitude choice in finding 5 was made there. The skill was invoked four times (L403, L941, L1840, L3195).
- **Proposed change:** add a "Plan drafting" lane: steps 1–4, write nothing, return names, paths, evidence direction and harness level.
- **Confidence:** verified; the altitude link is inferred.

### 18. Extra evidence for known #6
- Gates 1–5 each carried 25–29 rows of `? | ?`. User: "what is this what layers does skill have this?" (L1663).
- The user disputed the order twice (L1722, L2411). The assistant first defended dependency order, then reversed: "the checker uses it for test reach" (L2421). In the script the order matters only for multi-owner tests and the words "above/below".
- **Proposed change:** print one line when unconfigured; document what the order means; propose a `.ctdd.json` at step 2.
- **Confidence:** verified.

### 19. Extra evidence for known #3 and #5
- **#3:** the full 8.3 run was repeated three times (L2603, L2828, L3339), the last two for a two-file move and a field rename.
- **#5:** two exit-1 runs, L2732 (folder names in amendment prose) and L3148 (a method signature containing `...`). The first fix replaced exact folder names with vaguer prose.

### 20. Minor, NEW
- **`--plan-dir` does not say tracked or ignored.** The assistant told the user at gates 1 and 2 that `docs/plans` is tracked; it is ignored (`.gitignore:401`, L849). Verified.
- **`turns green:` exactness is undocumented.** First plan check failed with "VAGUE OWNERSHIP" (L472); `plan-format.md` shows the rule only by example. Verified.
- **`check-redstate` gives no failure reasons.** The assistant wrote an ad-hoc log parser three times (L1332, L1335, L2057). Need verified; benefit inferred.

## Counts
- **Gate presentations:** 10.
- **Amendments:** 9 (1 blocking answer, 1 wrong pin, 4 structural or altitude corrections at the red pause, 1 checker-only rewording, 2 for one guard failure, 1 rename).
- **Approvals:** 5 recorded; the human typed an approval 9 times, and 4 were lost because the message also carried a change.
- **Checker runs that failed for non-substantive reasons:** 6 — hold-out regex misfire (L782), BLOCKING heading label (L806), bare approval label (L843), two-line approval log (L923), UNRESOLVED PATHS twice (L2732, L3148; known #5). One more, VAGUE OWNERSHIP (L472), was by design but undocumented.
- **Misleading output without failure:** 3 `check-spec-surface --plan` runs (L2848, L3379, L3403); 5 gate blocks with an all-`?` altitude table.
- **Repeated blocking prompts:** hand check 8 times, red pause 2 times.
- **Other:** 4 `ctdd-tests` invocations, 3 full verification runs, 3 compactions (L521, L1489, L2896).
