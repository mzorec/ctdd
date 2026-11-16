# Proposals after 0.57.0: further lighter lanes

*(Proposed — not yet built.)* That holds for every item below with no **Status** line. Each of those is here for a yes or a no.

Seven items were chosen by the owner the same day and are built in 0.57.0: g, h, i, k, l, n and the diff stat of finding 16. Building h and i also covered c, as far as its rule went. A ninth, m, was built in 0.58.0 the next day, on the owner's word. Each of the nine carries a **Status** line saying what was built and where its shape differs from the proposal. The other ten are still proposals.

They come from the same session as 0.57.0: one real change that went through ten gate presentations and nine amendments, labelled A1 to A9 below in the order they happened. Evidence marked "eval" is from `evals/workflow/RESULTS-2026-11-14.md`.

One limit holds for every lane proposed here. A lane never applies when a test expectation, a contract shape or observable behaviour changes, and it never lets the agent approve anything on the human's behalf. Where a lane says "no gate", the approval already given stands for everything it covered, and the change is still recorded under `Amendments` and shown at the next stop.

## The nine candidates

### a. A rewording made only for the checker

- **Evidence.** A5 reworded two phase bullets so the altitude check could find an owner. It changed the revision and cost gate 6. 0.57.0 removed that cause: the owner is now the first token that resolves to a layer, and a test that cannot be placed is listed, not skipped.
- **Rule.** Compute the plan revision over the parts an approval is about: the summary and the `Risk:` line, the gate-visible sections, both test lanes, `Changed existing assertions`, `Contract changes`, the paths in `Files likely to change`, and each slice's `turns green:` claim. Wording outside those leaves the revision as it was, so there is no new gate.
- **How the checker decides.** It already splits a plan into those parts for the delta block. The revision would hash them instead of the whole text.
- **Risk.** The excluded wording becomes a place where meaning can change unapproved: a slice's sentence says what will be built. `Residual risk` and `Existing behavior` would have to stay inside, which leaves little outside.
- **Recommendation: no, for now.** The one specimen no longer needs a plan edit. Wait for a second.

### b. Correcting a pin's name or path

- **Evidence.** A2 fixed a pin whose name belonged to another class and whose path did not exist, and cost gate 3. 0.57.0 catches that at step 5.4, before the first gate, so the lane matters only for a pin corrected after approval.
- **Rule.** No gate when the amendment changes only a preservation pin's name or path, its `covers:` line is unchanged, and the corrected pin is observed passing against the unchanged implementation. A notice in place of the gate.
- **How the checker decides.** The delta shows changes in the preservation lane only, with `covers:` unchanged. The old name is found nowhere in the repository's tests, so this is a correction and not a substitution. `check-redstate.py --expect-pass` verifies the new name in a pin log captured before any production file changed.
- **Risk.** A different test under a similar name pins something else, and the human approved a preservation claim about one behaviour. The "old name exists nowhere" condition is what keeps it a typo fix.
- **Recommendation: yes, with those three conditions.**

### c. Moving or renaming a type or a file

- **Evidence.** A7 and A8 moved two types after a layering guard failed: two gates and a full verification run. 0.57.0 already gives this case the covering approval, the delta block and the lighter lane, because the tests are unchanged.
- **Rule.** What is left to add: name the verification for a move. Run the build, the invariant suite (item i) and the tests whose files use the moved names.
- **How the checker decides.** The lighter lane's condition, plus `Contract changes` unchanged, plus a file list whose basenames are the same set under different directories.
- **Risk.** A move can change behaviour where names are load-bearing: registration by convention, a namespace inside a serialised type name, reflection. The invariant suite is the check for that, which is why this depends on item i.
- **Recommendation: yes, together with i.**
- **Status: covered by i, in 0.57.0, without a lane of its own.** The lighter lane's run, as the checker prints it under a delta block, is now the build, the plan's invariant suite and the tests the amendment touches. The move-specific condition in "How the checker decides" was not built: a move takes the lighter lane on that lane's existing condition.

### d. Wording-only changes to descriptions and doc comments

- **Evidence.** A9 added a description to a contract field in the same amendment as the rename.
- **Rule.** Delta approval; re-run only the contract and document tests and regenerate the contract.
- **How the checker decides.** The plan cannot show that a contract's shape is unchanged. A script can: compare the old and new contract after dropping `description`, `summary`, `title` and `example` keys. That is a new mode for `check-spec-surface.py`, for OpenAPI in JSON or YAML.
- **Risk.** Descriptions are published. Consumers read them and generated clients carry them. And wording inside an error message is an expected value, so the lane has to be limited to those four keys and to code comments.
- **Recommendation: yes only if the shape comparison is built; otherwise no.**

### e. A file already written, inside approved scope, missing from the plan

- **Evidence.** A8 also added a projection file to the file list: it had been written in phase 1 without being listed.
- **Rule.** A `Deviations` entry in the packet, not an amendment, when the file serves an approved slice and adds no behaviour of its own.
- **How the checker decides.** `check-spec-surface.py --plan` already lists production files with no `## Intended change` row. The lane would apply to a file that is new, is not test, contract or ADR surface, and sits in a directory that already holds a planned file. Whether it carries behaviour is not something a script can decide.
- **Risk.** Helper files are where unplanned behaviour hides, and location is a weak proxy for scope. The human still sees the file in the checkpoint's table and in the packet.
- **Recommendation: yes, as described, and say in the packet that location was the test.**

### f. Red state again only for the tests that changed

- **Evidence.** After A3 to A6 the red run was captured again for all twenty-nine tests. In the eval, the stand-in under pressure did this on its own for the one changed test and saved it to a second log.
- **Rule.** After an amendment, capture red state for the tests the delta block names as added or changed. The others keep the evidence they have.
- **How the checker decides.** The delta block already names the changed tests. `check-redstate.py` would accept a second log and, for each test, read the newest log that mentions it.
- **Risk.** A test the plan left alone can still change in code, by a moved fixture or a shared helper, and nothing re-observes it. The craft-edit lane's rule that a verdict stays unchanged is the cover for that.
- **Recommendation: yes.**

### g. Every pending stop asked once

- **Evidence.** The red-pause prompt was printed twice while the human asked about something else, and the hand check eight times. 0.57.0 applies ask-once to the hand check only. In the eval the baseline repeated the whole prompt and the changed text gave one status line.
- **Rule.** Move the sentence from step 9.1 to the Decision prompt row: a stop is asked once, and while it is unanswered each later reply ends with one line naming it.
- **How the checker decides.** It does not; this is conversation.
- **Risk.** A prompt that has scrolled away is forgotten, so the status line has to say what is pending and how to answer it. Budget: the sentence would leave 9.1, where the measured compaction boundary cuts it on one model, and sit near character 4,300, which pushes the hold-out stop about 90 characters later.
- **Recommendation: yes.**
- **Status: built in 0.57.0.** The sentence moved unchanged, to the guardrail that makes every question a Decision prompt and not to the Decision prompt row: the cost in front of step 9.1 is the same in either place, and the guardrail is where asking is ruled. It sits at character 1,202. Measured in `g-pending-stop-once`: 2 of 4 on the baseline, which was mild, and 4 of 4 after. The hand-check scenario was run again on the moved text and held.

### h. Scoped verification at each phase checkpoint

- **Evidence.** Step 8.3 lists the contract validator, the focused tests, the broader suite and the build, and reads as owed at every phase. The session ran the full list three times.
- **Rule.** At a checkpoint: the build, the phase's own tests and the pins. The whole suite, the release build and any migration check run once, after the last phase.
- **How the checker decides.** Nothing to decide. `Verification` could mark which commands are final-only.
- **Risk.** A regression outside the phase's tests surfaces at the end. The eval shows exactly this: a scoped run did not see a layering test that the whole suite did.
- **Recommendation: yes, and only together with i.**
- **Status: built in 0.57.0, with i.** Step 8.3 opens "When no phase remains", and the checkpoint row of `execution.md` names what a phase owes: the build, the plan's new-behavior tests, its pins and its invariant suite, and a sentence in the reply that the rest still runs. `Verification` does not mark which commands are final-only; nothing needed it. Measured in `h-checkpoint-scope`: 2 of 5, then 5 of 5.

### i. An invariant suite, named in the plan and run early

- **Evidence.** The layering violation existed from the step-7 stubs and was found at the last phase's verification, three approved revisions later. The eval fixture reproduces it: the layering test already fails at the phase 2 checkpoint.
- **Rule.** `Verification` names one fast invariant command, such as the architecture tests. It runs at step 7.10 and at every checkpoint, and step 2.1 reads the repository's rules about where new types may live.
- **How the checker decides.** `check-plan.py` requires a `Verification` bullet marked `invariants:`, or `invariants: none — <reason>`, above the small tier.
- **Risk.** It adds a step and a required line, and `none` is the easy answer. It also assumes the suite is fast.
- **Recommendation: yes.** It is the counterweight to the lighter lane and to h.
- **Status: built in 0.57.0.** `check-plan.py` requires the line above the small tier and fails without it as `NO INVARIANT SUITE`, except for a plan that already has an approval record. `check-redstate.py` says to run the suite once red state is verified at 7.10, the checkpoint row counts its result, and the lighter lane's run includes it. Step 2.1 was not changed: the checker's failure message says to read what the rules say about where new types may live, which is where an agent drafting a plan meets it. Measured in `i-invariants-early`: 1 of 4, then 4 of 4.

## The four asked for by name

### Plan consolidation and one file list (finding 14)

- **Evidence.** The plan grew from 33,575 to 54,569 characters. Three sections list the same files and were re-synced by a script twice.
- **Proposal.** `check-plan.py` prints the `## Intended change` table's rows from `Files likely to change`, so that table is generated and never hand-synced. A consolidation, which rewrites the plan to its current form and keeps `Amendments` as the history, needs no gate when the checker finds the gate-visible parts, the tests, the contract section and the file paths all unchanged.
- **Risk.** A consolidation rewrites approved text, so the comparison has to be exact or it is a gate.
- **Recommendation: yes to the generated table; yes to consolidation only with the exact comparison.**

### Declared names for generated files (finding 15)

- **Evidence.** The plan invented a migration's timestamp, the generator chose another, and two files, an attribute, a folder and a hash line were renamed to match the plan.
- **Proposal.** A planned path may carry one `<generated>` segment where a tool names the file. `check-plan.py` accepts it, `check-spec-surface.py --plan` matches it to exactly one touched file and prints the real name, and `## Intended change` records that name.
- **Risk.** It reopens a wildcard in a rule written to forbid them. Limits: one token per path, a literal suffix after it, and a report when it matches no file or two.
- **Recommendation: yes.**

### A diff stat that does not touch the index (finding 16)

- **Evidence.** To show new files in the pause's stat, the agent ran `git add -N` and then `git reset`, in a repository whose owner stages from the IDE during a session.
- **Proposal.** `check-spec-surface.py --git <base> --stat` prints the changed and the untracked files with line counts. `execution.md` names it at 7.12 and says never to touch the index.
- **Risk.** Small: one more mode and its tests.
- **Recommendation: yes.**
- **Status: built in 0.57.0, and one flag wider.** `--stat` prints the stat and `--patch <file>` writes the full diff, both from a copy of the index with the untracked files marked in it. With `--plan` the plan's own untracked files stay out, and the file `--patch` writes is never part of the next one. Step 9.4 uses `--stat`; the 7.12 row uses both and says nothing touches the index.

### A plan-drafting lane in ctdd-tests (finding 17)

- **Evidence.** `ctdd-change` requires `ctdd-tests` before a test path is drafted, and `ctdd-tests` writes only under an approved plan. The session improvised a "write nothing" pass, and the placement that later cost four amendments was chosen there.
- **Proposal.** A third reduced lane: steps 1 to 4, nothing written, returning names, paths, evidence direction and the lowest harness that can observe each case.
- **Risk.** Budget first: `ctdd-tests` has 3 characters of room, so this needs a displacement or a recorded raise of about 250. A lane that returns without writing is also easy to skip.
- **Recommendation: yes, with the budget decision made explicitly.**

## Others found while building 0.57.0

### j. Open BLOCKING questions printed at the gate, with their options

- **Evidence.** The human asked "what are blocking things?" at the first gate and saw the options only then (finding 6).
- **Proposal.** Print the `BLOCKING` section in the gate block whenever it is not `none`.
- **Risk.** A longer first gate, bounded by the number of open questions.
- **Recommendation: yes.**

### k. `--approval` also checks what `--post-approval` checks

- **Evidence.** `--post-approval` is named in one reference line and in no step, and was never run in the session.
- **Proposal.** Verifying an approval refuses a plan that still asks a BLOCKING question.
- **Risk.** A plan approved while still asking fails once and has to be fixed.
- **Recommendation: yes.**
- **Status: built in 0.57.0.** The check runs only once the record is known to be for the current revision, so a plan amended after approval is still reported as stale and not as asking.

### l. Step 8.4 passes the baseline

- **Evidence.** 0.57.0 added `--baseline` to `check-spec-surface.py`, and the skill does not pass it, so files dirty before the change are still reported as missing rows.
- **Proposal.** Step 8.4 passes the step-0 line. About 40 characters in the body.
- **Recommendation: yes.**
- **Status: built in 0.57.0, in a different shape.** No step passes anything. `check-plan.py --gate` records what git reports dirty while the plan has no approval, in `<name>.gate-dirty.txt` beside the plan, and `check-spec-surface.py --plan` reads that file and names what it excused. The proposed shape was dropped because the step-0 line is one an agent can print again after the change exists, and one session did, with the change's own files in it. Passing that line would have silenced the report. It costs the body nothing. `--baseline` stays as the manual form.

### m. A harness kind per test project

- **Evidence.** Seven tests sat in an integration project where unit tests would do, and the layer check matched them, because both projects name the same layer (finding 5). The new `Tests by file` lines put the project in front of the human at the first gate, which is half of this.
- **Proposal.** `.ctdd.json` names a harness kind per test project, and the altitude table prints it.
- **Risk.** New configuration that each repository has to fill in.
- **Recommendation: wait and see whether `Tests by file` is enough.**
- **Status: built in 0.58.0, and one rule wider.** The owner asked for it the next day, without waiting. `.ctdd.json` takes `harnesses`, the kinds lightest first, where the proposal had a kind per project, and the altitude table prints the kind beside the layer. The wider part: a new-behavior test in a heavier harness must carry a `- needs:` line wherever a lighter project of the same layer sits on disk beside its own, and `check-plan.py` refuses the plan without one. A layer with one test project is not asked, and neither is a test that sits where an approved plan had it. Measured with `m-heavier-harness`: 2 of 5 assertions before, 5 of 5 after (`evals/workflow/RESULTS-2026-11-15.md`).

### n. Step 5.5 displaced by what `--plan-dir` prints

- **Evidence.** 0.57.0's wording put the hold-out stop at character 14,053 of the body. One model's measured compaction boundary is near 14,200, so on that model the stop's opening survives and the rest of step 9.1 does not. `--plan-dir` now says what to do about the pointer and the commit, which is what step 5.5 says.
- **Proposal.** Step 5.5 points at that output. About 100 characters come back before step 9.1.
- **Risk.** One more instruction that lives in a script's output instead of the skill.
- **Recommendation: yes, or accept the position knowingly.**
- **Status: built in 0.57.0.** Step 5.5 reads "Do what `--plan-dir` printed about the plan's commit and its pointer", and both of that command's answers now name the step and carry the whole instruction. 92 characters came back. Items g and h spent them and 29 more, so the hold-out stop starts at 14,082, not earlier than before: what changed is that the ask-once rule is no longer behind it, and step 9.1 ends 69 characters sooner.

### o. `turns green:` exactness said in the format

- **Evidence.** The first plan check of the session failed on a wildcard after `turns green:`, a rule the format shows only by example (finding 20).
- **Proposal.** One clause in field rule 9.
- **Recommendation: yes; it is the cheapest item here.**
