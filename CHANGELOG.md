# Changelog

## Unreleased

_Docs and other non-runtime edits collect here and fold into the next runtime release. Version numbers move only when the skills, scripts, or hooks change._

- `ctdd-in-depth.md` given the same rewrite, the largest of the three. The relentless em-dash cadence (over 300 of them) that made the argument exhausting to read is broken into sentences, and the most deeply-nested paragraphs are un-stacked. Every claim, hedge, number, citation, weakness, and *(Proposed — not yet built)* tag is preserved exactly, and verified mechanically after the pass — the density here is partly the argument pre-empting objections, so nothing was simplified away, only made readable. It stays the hostile-review rationale; it just no longer fights the reader to deliver it.
- `ctdd-in-practice.md` given the same rewrite: the em-dash-heavy cadence that read as machine-written is gone, a few passages that assumed the point were re-explained, and the structure and content are unchanged. It complements the new README and points at `ctdd-in-depth.md` for the full argument.
- README rewritten for a senior engineer meeting CTDD for the first time. It now opens with what using the plugin looks like before the philosophy, leads the three-doc split cleanly (README = operating manual, *in practice* = the ten-minute feel, *in depth* = the reasoning), and cuts the em-dash-heavy phrasing that made it read as machine-written. Same content and same six-deterministic-pieces honesty; about 1,000 tokens lighter.

- The status pin in `ctdd-in-depth.md` no longer lists what shipped — the changelog already says that. It keeps only the two things nothing else records: what the skills cost to run, and which mechanisms the document describes but hasn't built.

## 0.12.1 — 2026-07-21

### Changed
- **Colocated notes state the rule, not where it was found.** Write "ledger status 7 means settled; a capture in that state must not be re-submitted," not "the upstream service checks this in its settlement handler." A citation pins the comment to another team's file name, so it breaks silently when they refactor and nothing in this repo notices. The sharper test: a colocated note states something that stays true; anything true only as of today belongs in the plan or an ADR, which are point-in-time records and may name specifics freely. The plan carries the provenance, the code carries the rule.

## 0.12.0 — 2026-07-21

### Added
- **A place for facts the code depends on that live outside the repo.** Colocated notes previously admitted only universals and deliberate boundaries. They now also take the expensive external fact: a legacy system's semantics, a non-obvious key relationship, a storage format, a framework quirk. These are the things an agent rediscovers from scratch every session because no test, contract, or ADR can hold them. The entry test keeps it from becoming a spec document: **could the next reader derive this from the code, the tests, or the contract in this repo?** If yes, don't write it. If no, and rediscovering it means reading another system, one sentence where the code touches it. Not an ADR (that records a decision) and not a spec (a test covers behavior) — the external fact both of those assume.

## 0.11.3 — 2026-07-21

### Changed
- **Spelled out that "copy the plan verbatim" and "keep the summary short" are not in conflict.** The previous release could be misread as "paste the whole plan into the terminal," which would undo the change that made summaries readable in the first place. The plan file already opens with the thirty-second decision summary, so copying *that section* verbatim plus the file path gives the human the same brief read they would have got, in the same words the file holds. Brevity was never the problem; re-wording was.

## 0.11.2 — 2026-07-21

### Fixed
- **The plan shown in the terminal must be copied from the plan file, not summarized.** The rule already said the presentation is "that file's own content," but nothing forced a verbatim copy, so the agent wrote a fresh condensation instead: ~160 lines with evidence, assumptions, tests, and sequencing on disk, versus a short rewrite on screen that shared none of that structure. Two documents, immediately disagreeing, and no way for the reviewer to tell which one they approved. Now: read the file and paste it in. If it is too long, paste the decision summary section verbatim plus the file path and say the rest is in the file — a truthful excerpt, never a re-write.

## 0.11.1 — 2026-07-21

### Fixed
- **New facts learned during the plan gate now go into the plan file, not just the presentation.** The plan file is written before plan mode, but plan mode blocks repo writes, so anything the agent learns *while the gate is open* had nowhere to go and accumulated in the harness's throwaway file instead. The result: the document you review is stale on the newest thing the agent knows, and the presentation quietly becomes a second, competing plan. The agent must now say what it learned, say the plan needs it, and ask to leave plan mode long enough to write it, then re-present. It may never close the gate with the file and the presentation disagreeing.

## 0.11.0 — 2026-07-19

### Added
- **The agent has to actually run a check before saying it passed.** No more "tests pass" or "the build is clean" unless it ran that command in the same message and read the output. If it couldn't run something, it says so instead of glossing over it. This also covers work done by sub-agents: the diff is the evidence, not the agent's summary of itself.
- **It checks your working tree before implementing.** Uncommitted work it didn't make, or you sitting on `main`, and it stops and asks. A mixed tree makes the final diff impossible to review, which is the thing this method reviews.

### Removed
- Three explanations in `ctdd-change` that didn't change what the agent does.

## 0.10.4 — 2026-07-19

### Removed
- About 400 tokens of explanation from `ctdd-change` — no rules changed. Mostly passages explaining *why* a rule exists, which the agent doesn't need; the reasoning lives here instead.

## 0.10.3 — 2026-07-19

### Added
- **When a change both preserves old behaviour and adds new behaviour, do the preserving part first.** Tests that pin existing behaviour have to run against that behaviour — if you reshape things first, those tests still pass but no longer prove anything.

## 0.10.2 — 2026-07-19

### Changed
- **Evidence is now the checker's one-line verdict, not the log file.** A log only proves some tests ran; nobody reads it to check *which*. Running the check against the plan is what catches a test that got renamed or swapped between planning and implementation.
- `ctdd-review` asks for that verdict, and tells the reviewer to run the check themselves if only a log is offered.

## 0.10.1 — 2026-07-18

### Fixed
- **The plan file now gets written before the agent enters plan mode.** Plan mode only lets it write to a scratch file outside your repo — so the plan would vanish with the session and be invisible to review and CI. If the agent is already in plan mode with no plan file, it now says so and asks you to exit briefly rather than quietly using the scratch file.

## 0.10.0 — 2026-07-18

### Changed
- **The plan summary is now written like a person talking, not a form.** It leads with whatever surprised the agent or whatever it won't guess at; if nothing about the change is surprising, it says so in a sentence and stops. The previous version was a row of labelled fields — scannable but hollow, and it got skimmed.
- **The full plan now prints to the terminal as well as the file.** Summary first, detail below. The earlier rule showed only a pointer, which solved the wrong problem: dense detail in a terminal was never the issue, dense detail with no summary in front of it was.

## 0.9.9 — 2026-07-18

### Added
- A one-line summary strip at the top of every plan: risk level, whether the contract change is breaking, whether a hold-out is needed, whether an ADR is required. Those four decide whether you need to read further, and they used to be scattered through the detail.

## 0.9.8 — 2026-07-18

### Fixed
- **`check-redstate.py` could report success for tests that never ran.** Any prose line mentioning "characterization tests" made it silently skip every test name after it, then print "red state verified" and exit 0. Now a section label only counts if it *starts* the line, and the success message lists every test it actually checked.
- **UTF-8 on Windows.** `--help` crashed on a standard console, and piped logs decoded wrongly — a genuinely failing jest/vitest/TAP test would report as passing. (dotnet was unaffected.)
- `--expect-pass` was reading the wrong list of tests from the plan.
- A log line that mentions a test without saying pass or fail is now reported as an unreadable run, not as a broken test.

### Docs
- The README claimed six deterministic pieces and listed five; the missing one was `check-redstate.py` itself. Now listed, with an honest note that it isn't in the CI recipe because CI can't know which log belongs to which change.

## 0.9.7 — 2026-07-18

### Added
- **`--expect-pass`** — the mirror of the red-state check, for tests that pin existing behaviour. They have to be seen *passing* against the old code, saved to `<plan>.pinstate.log`, and still pass afterwards.
- **A rule for compiled languages:** a test naming a type that doesn't exist yet doesn't fail, it fails to compile — which proves nothing. Write the type as a stub first so the test compiles and fails for the right reason.

## 0.9.6 — 2026-07-18

### Added
- **`check-plan.py --from-description`** — CI now reads a `CTDD-Plan: docs/plans/<name>.md` line from the merge request and validates *that file*. Previously CI checked the merge request text instead, so it could reject a request that correctly pointed at a good plan, or approve a stale copy pasted into the description.
- The pointer is treated as untrusted input: no traversal, no absolute paths, nothing outside `docs/plans/`. If the file isn't there, the error says why (usually `docs/plans/` is git-ignored) and gives both fixes.

## 0.9.5 — 2026-07-18

### Fixed
- Pin tests are no longer fed to the red-state checker, which would flag them as failures. Plans now list new-behaviour tests and preservation pins under separate headings.
- A one-line bug fix that adds a regression test is now its own category. The skill used to say the plan "collapses to a sentence" while the checker demanded nine sections, and the rejection message wrongly said "an edit to an existing test" when the test was newly added.
- `check-plan.py` now checks for the two decision-summary headings the format has always called mandatory.
- Discovering mid-implementation that a planned test or contract clause is wrong now stops and re-opens the gate, instead of "change it and mention it at the end."

### Changed
- Hold-out outcomes are no longer interchangeable: **failed** blocks approval, and **declined** is a recorded waiver, not a quiet success.
- Two artifacts only conflict if they claim different things about the *same* constraint. A schema describing payload shape and a test asserting a business rule aren't a contradiction.
- Four more trigger test cases, including ones that should *not* fire (CSS feedback, README wording, Dockerfile changes).

## 0.9.4 — 2026-07-18

### Fixed
- The skill said "nothing is written to disk before approval" while also requiring the plan file to be written. Now it says no *work product* before approval — the plan file is the thing you review, so it comes first.
- `ctdd-review` didn't know plans live in `docs/plans/`; it still looked only in pull request descriptions.

### Docs
- Status pin re-measured (it had been bumped for nine releases without its contents being updated), and `ctdd-in-practice` gained a sentence noting the plan is a file you read in your editor.

## 0.9.3 — 2026-07-18

### Fixed
- Two rules contradicted each other: one said new tests must be seen failing first, the other said pin tests must be seen passing first — for the same tests, with no exception stated. It now depends on what the test asserts: new behaviour must fail first, preserved behaviour must pass first and keep passing.

## 0.9.2 — 2026-07-18

### Changed
- **"The existing tests will catch it" now has to name which tests.** The old rule only fired when you *changed* behaviour, so a refactor that claimed to *preserve* behaviour slipped past — which is the more dangerous case, because it comes with false confidence. If you can't name the tests, write them against the old code first, watch them pass, then convert.

## 0.9.1 — 2026-07-17

### Fixed
- `check-redstate.py` didn't recognise JUnit/Maven failure output, so Java projects got a false "not found." Added Go and TAP test cases too, and documented the real limit: the test name and the failure marker have to be on the same line.

## 0.9.0 — 2026-07-17

### Added
- **`check-redstate.py`** — checks a saved test run and confirms the new tests were actually seen failing before implementation. It flags tests that passed before the code existed (either the behaviour was already there, or the test asserts nothing) and tests that never ran at all.
- `ctdd-change` now saves that run to `docs/plans/<plan>.redstate.log`, and `ctdd-review` treats a missing one as a finding.

### Changed
- If a blocking question gets answered in a way that changes the scope, the plan's risk level and contract section have to be restated to match.

## 0.8.3 — 2026-07-13

### Fixed
- **Plan mode could trap the agent in a loop.** It couldn't cleanly exit, and declining kept it re-presenting the same plan while "approve" and "decline" meant something ambiguous to you. Now the plan file is the authority, plan mode just shows a pointer, and approving means "start implementing."

### Changed
- Plan filenames are now `<TICKET>-<kebab-slug>.md` or `<date>-<kebab-slug>.md`, so the folder reads as a timeline instead of a pile of mashed-together names.

## 0.8.2 — 2026-07-13

### Fixed
- **The scripts silently did nothing on Windows** where `python` and `py` exist but `python3` doesn't. Added a portability note, inline Windows alternatives in the skills, and a `hooks.windows.json.example` using `py -3`. The scripts themselves were always cross-platform.

### Docs
- README gained a section on `docs/plans/`: what lands there, and whether to commit it or ignore it.

## 0.8.1 — 2026-07-13

### Changed
- **Plans are now always written to a file**, not only long ones. The plan is the decision record for a change and deserves to exist regardless of size. A trivial change still produces no plan, so no file.

### Docs
- Added `CLAUDE.md` for working on this repo, and rewrote `docs/backlog.md` so every entry opens with the problem it solves in plain language.

## 0.8.0 — 2026-07-13

### Changed
- **Plans are written to a file and lead with a decision summary** in two buckets — *blocking* questions and *proceeding unless you object* — so you can approve from the summary if you agree with it. A dense plan is right for a big change; a terminal is the wrong place to read one.
- Documentation-only edits no longer bump the version. They collect under **Unreleased**.

## 0.7.6 — 2026-07-13

### Docs
- Filed how `ctdd-review` relates to Claude Code's built-in `/code-review`: they answer different questions ("is this code correct?" versus "does this test still encode the right requirement?"), so run both.

## 0.7.5 — 2026-07-13

### Docs
- New `docs/backlog.md` — a record of ideas deliberately *not* built, each with the specific observation that would justify building it. Closes with the entry test: an idea that can't say what would prove it unnecessary doesn't belong there.

## 0.7.4 — 2026-07-13

### Added
- MIT license, marketplace entry, and install instructions — the plugin is now installable with `/plugin marketplace add` and `/plugin install`.
- `.gitattributes` pins line endings so the scripts don't break on Windows checkouts.

## 0.7.3 — 2026-07-13

### Docs
- Added the claim that the executable spec gets richer as a byproduct of doing the work — stated narrowly, with its counterweight (brittle tests accumulate into a precise description of yesterday's code) and an explicit bar on ever using it to explain away a bad result.

## 0.7.2 — 2026-07-13

### Docs
- New section on why this helps the agent: a goal-only prompt forces it to guess, and the contract plus tests are simply better inputs.

## 0.7.1 — 2026-07-13

### Docs
- Editorial pass on `ctdd-in-practice`: plain-English glossary, a "try it first" section, and the two weaknesses you'll hit soonest. Corrected a promise of "the evidence behind it" to "the reasoning behind it" — at that point there was no evidence.

## 0.7.0 — 2026-07-13

### Added
- **New tests must be run and seen failing before the code is written.** A test that has never failed hasn't been shown to detect anything.
- Trigger tests for pressure situations: urgency, sunk cost, borrowed authority, and "skip the review just this once" all have to still fire the protective skill.
- README section on installing this alongside Superpowers, and which one owns the workflow entry point.

### Changed
- Skill prose is now frozen: the next change to it has to be justified by something that happened in real use, not by a review.

## 0.6.1 — 2026-07-13

### Docs
- New passage on what this costs to run: the overhead rides on retrieval any competent agent workflow already pays, cost scales with risk by design, and the real risk is frequency — the gate decaying under volume.

## 0.6.0 — 2026-07-12

### Added
- **`gen-authz-matrix.py`** — derives an authorization matrix from the OpenAPI contract: every identity against every operation, with the expected allow/401/403 and the reason. `--check` fails CI when a new endpoint ships with no rows. Honest limit: it covers what the contract *declares*, so per-object rules still need hand-written tests.
- **Back-translation**: on load-bearing changes the agent states, from the tests alone, what requirement they encode — and you compare that prose to your original. It reads artifact-to-prose, which is why it doesn't share the blind spot of asking a second agent to re-derive the same answer.

## 0.5.2 — 2026-07-12

### Docs
- New `docs/ctdd-in-practice.md`, a ten-minute introduction, and the rationale renamed `docs/ctdd-in-depth.md` — making the pair *in practice* and *in depth*.

## 0.5.1 — 2026-07-12

### Added
- `check-plan.py --diff` now contradicts a "trivial" claim when the diff actually touches tests or contracts.
- Hold-outs get an outcome (`pending` / `passed` / `failed` / `declined`), and review treats a still-`pending` result as a finding.
- Plans state known gaps explicitly, so silence becomes something you can review.
- README gained a GitLab CI recipe, turning the scripts from "when run" into "always run."

## 0.5.0 — 2026-07-12

### Added
- **`check-spec-surface.py`** — lists exactly which tests, contracts, and ADRs a diff touches, including renames and deletions that the hook can't see.

### Changed
- `ctdd-tests` now triages before acting: fixing a flaky test is its job, but changing what a test asserts hands off to the full change workflow.

## 0.4.1 — 2026-07-12

### Fixed
- A guard added in 0.4.0 to stop `spec/payments.yaml` being mistaken for a test file was silencing fixture files under `tests/` as well — exactly where a wrong test setup hides. Both behaviours are now pinned by tests. Owned lesson: that change shipped without a test, in a plugin about executable specs.

## 0.4.0 — 2026-07-12

### Changed
- `ctdd-change`: the plan gate is honestly scoped (it catches the wrong *direction*, not a wrong encoding); a "trivial" skip is now visible and vetoable; editing an existing test or any contract file is never trivial. Added sections for amendments and for what to do when artifacts disagree.
- `ctdd-tests`: authorization-matrix property tests, so a new endpoint without a row is visible as uncovered.
- `ctdd-review`: an unstated NFR budget or a missing hold-out record on a risky diff is now a finding.

### Added
- `check-plan.py`, which flags missing sections in a plan.
- The spec-edit hook now also catches overwrites of existing test files, and has its own test suite.

## 0.3.0 — 2026-07-10

### Added
- **`ctdd-review`** — the reviewer's side: runs the checklist over a finished diff, treating changed tests as changed requirements.
- A hook that reminds you when you edit a test or contract file, so the discipline doesn't depend on a skill staying in context. Ships off by default.
- Characterization tests as a first-class idea: `currently_*` marks an observation rather than an intention.

## 0.2.0 — 2026-07-10

### Changed
- `ctdd-change` reordered: read what exists before designing the contract change, and write nothing to disk before the plan is approved. Added bug-fix and standalone-ADR modes.

## 0.1.0

- First release: `ctdd-change` and `ctdd-tests`.
