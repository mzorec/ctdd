Goal: fix defects in this plugin's checker scripts that a real ctdd-change session exposed, then apply seven workflow changes I have already decided, each measured before and after with skill-creator, and propose further lighter lanes for my decision.

Evidence
- Findings report from that session: docs/session-findings-2026-11-12-processing-status.md
  It ranks 20 findings, each with transcript line numbers, the responsible script or skill line, and a proposed change. It also lists nine earlier findings it refers to as "known #1–#9".
- The session transcript it cites, if you need to check a quote:
  C:\Users\markoz\.claude\projects\C---GitA1EDavki-edavki-documentintegration\fad73bc1-fd4e-4a6e-bf65-7851710512fe.jsonl
  It is large; search it, do not load it whole.
- The plan those checkers ran against, usable as a real test input (read only, it belongs to another repo):
  C:\_GitA1EDavki\edavki.documentintegration\docs\plans\2026-11-11-backend-processing-status.md and its .approval.log, .redstate.log, .pinstate.log, .pinstate-after.log beside it.

The report is one unverified analysis pass. Before fixing anything, confirm each finding by reading the script or skill text and reproducing the behaviour. If a finding is wrong or only partly right, say so and skip or adjust it; one diagnosis from that session was already wrong.

Part 1: script fixes (do these)
From the report, findings 4, 8, 12, 13, the script side of 5, the UNRESOLVED PATHS misfire, and the minor items in 20:
1. check-spec-surface.py --plan: the "Planned but untouched" list compares against classified surface only, so every planned production file is listed; planned paths are taken from any backticked path in the plan instead of the file list; docs/api/*openapi*.json is not recognised as contract surface (patterns in hooks/spec-edit-guard.py); .ctdd.json and files already dirty at the baseline are flagged as lacking an Intended change row.
2. check-plan.py: the hold-out block is located by the first line starting with "hold-out" anywhere in the plan; a pin's path is never checked to exist or to contain the named test; UNRESOLVED PATHS fires on backticked code (a method signature) and on directory names in prose; the altitude owner is only the first backticked token of a slice bullet, and an owner of "?" silently skips the comparison while layers are configured; the plan-size line prints on every run; the "decision summary: BLOCKING" label does not match the heading it reports missing.
3. check-plan.py --approval: reads the first record in the approval log, so an appended approval reports stale and the file has to be overwritten. Read the last record and keep earlier lines as history.
4. check-redstate.py: --tests-from matches bare test names and ignores the plan's path, so a same-named test in another class satisfies a pin; it prints no failure reasons.
5. check-plan.py --plan-dir: say whether the directory is tracked or ignored.

For each fix: reproduce it first, add or extend a test in this repo's existing test setup (find it; do not introduce a new framework), fix, and show the test passing. Keep existing exit-code meanings.

Part 2: decided workflow changes (apply these, measured with skill-creator)
Load the skill-creator skill and follow its process. First read the repo's evals/ folder and reuse its format and runner if it has one. These are my decisions; implement them as stated, in the skill text and in the checkers where the checker must enforce them:
D1. Approval together with a dictated change counts. When my message states a change and approves (e.g. "Domain, approve"), amend the plan, print only the delta, and record the approval as covering that amendment. It covers only what I dictated: if the amendment goes beyond my words in any respect, stop and present it again. (Findings 2, 6.)
D2. After an amendment the gate shows only the delta plus a line that the gate-visible sections are otherwise unchanged since the previous revision. Define one Amendments section in the plan format, with old and new form, and have --gate print its newest entry. The first gate is still the full block. (Finding 3, known #1.)
D3. The first gate also shows structure: new or changed public types and where they live, ports touched, configuration bindings, and the test project per test group. (Finding 1.)
D4. After a late failure that needs an amendment (step 8.6), state the finding and offer the candidate fixes as a Decision prompt before editing the plan. (Finding 7.)
D5. The hand check after a declined hold-out stays a separate stop at step 9.1, not folded into the gate approval. Ask it once; while it is pending, later replies carry a one-line status, not the full prompt again. Fix the gate block printing the hold-out result and expected values blank after a decline. (Finding 11, known #2 and #8.)
D6. Compile-only stubs return defaults and never throw, in both skills and the worked example. A stub may not be shaped to make a test fail; when an honest stub lets a named test pass, the plan records it as constrained by a later slice. (Finding 10, known #9.)
D7. A lighter lane for small amendments such as a rename, allowed only when test names, inputs and expected values are unchanged: delta approval per D1/D2, the craft-edit lane for the tests, and verification scoped to what the amendment touches. A full verification run still happens once before the review packet. (Known #3.)

For each decision: write an eval scenario from the session moment the finding cites (my actual message and the state at that point) with an observable pass condition, run it against the CURRENT text as the baseline, apply the change, rerun, and report before and after side by side. A scenario that already passes on the current text does not demonstrate the finding; report that and tell me before changing the text.
D1, D2 and D7 loosen the "approve the exact revision" rule. For each of them also write one pressure scenario with superpowers:writing-skills that tempts the agent to stretch the rule (treating its own extra edits as covered by my approval; calling a behaviour change a rename), and show it holds. Where possible make the checker, not the agent, decide whether a lighter lane applies: for example by comparing the test names, inputs and expected values or the gate-visible sections between revisions.

Part 3: further lighter lanes (propose; do not apply)
Hard limit for every lighter lane: it never applies when a test expectation, a contract shape, or observable behaviour changes, and it never lets the agent approve anything on my behalf.
Evaluate these candidates from the session and add any others you find. For each give the evidence, the proposed rule, how the checker would decide eligibility, and what it risks:
a. Checker-only rewording of the plan (session amendment A5: phases reworded so the altitude check finds an owner). If the gate-visible sections and the test set are unchanged, no new gate: compute the approved revision over the approved region only.
b. Correcting a pin's name or path (A2). No full gate when the corrected pin is observed passing against the unchanged implementation; a delta notice instead.
c. Moving or renaming a type or file with no behaviour, contract or test-expectation change (A7/A8, after I pick the fix under D4). Delta approval; rerun the build, the invariant/architecture suite and the affected tests, not the whole suite.
d. Wording-only changes to descriptions and doc comments. Delta approval; rerun only the contract and document tests and regenerate the contract.
e. Adding to the plan a file that was already written and is inside approved scope (the projection file). A Deviations entry, not an amendment.
f. Re-capturing red state after an amendment only for the tests that changed, not the whole set.
g. Repeated pending stops in general (red pause, checkpoints): state once, then a one-line status, as in D5.
h. Scoped verification per phase checkpoint: the focused tests and pins at each checkpoint, with the whole suite, the Release build and the migration check once at the end.
i. An invariant suite named in the plan's Verification and run at step 7.10 and each checkpoint, so placement rules fail early instead of at final verification. (Finding 9; this adds a step, but removes a late amendment.)
Also propose, without applying: plan consolidation and a single file list (finding 14), declared generated file names (15), a non-mutating diff stat recipe with "never touch the index" (16), and a plan-drafting lane in ctdd-tests (17).

Constraints
- This is Windows. `python` and `python3` on PATH are dead stubs; use %LOCALAPPDATA%\Programs\Python\Python312\python.exe.
- Do not touch the edavki.documentintegration repository.
- Commit only when I ask. No Co-Authored-By trailer.
- Do not convert line endings in files you edit.
- Evals spawn subagents and cost tokens: run each scenario once for the baseline and once after, not in bulk repeats, unless I ask.
- Update CHANGELOG.md for what you change, in the file's existing style.

Finish with: a table of the Part 1 findings (confirmed / not reproduced / fixed / deferred) with the tests added and the full test run output; for each of D1–D7 the scenario, baseline and after results and the diff applied; and the Part 3 proposals as a list I can answer yes or no to.
