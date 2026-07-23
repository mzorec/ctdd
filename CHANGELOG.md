# Changelog

## Unreleased

_Docs and other non-runtime edits collect here and fold into the next runtime release. Version numbers move only when the skills, scripts, or hooks change._

- `ctdd-in-depth.md` gains an honest limit on the deterministic tiers: moving a rule into a checker removes drift but not wrongness, and substitutes a quieter failure. Twenty defects of one shape — a checker reporting success over input it never read — came out of running this method's own tooling, several of them fixes for the previous one that reached a single caller. The two rules that follow are free and were not obvious in advance: test checkers against malformed, partial and empty input rather than well-formed input, and enumerate every caller before declaring a fail-silent path closed.
- Checked and found accurate, so unchanged: the status pin (version and all three measurements), the six deterministic pieces, hold-out vocabulary, and the absence of any withdrawn library recommendation. `ctdd-in-practice.md` and the README need nothing — the night's changes were runtime and packaging, which those documents deliberately stay clear of.

- Backlog: the truncation work is now measured and filed in priority order. Cutting step 6's rationale is the low-risk first move (184 characters of margin becomes ~1,400, nothing becomes load-dependent). Moving steps 7–10 into references is the only change that reaches the 5,000 guidance, and it is *strictly better* rather than a trade, because those steps are already truncated — a reference with a surviving loader is available on demand where truncation is simply gone. Its trigger can resolve either way: run one real change through a compacting session, and if nothing goes wrong the refactor should not be built at all. Splitting step 6's structure is demoted to last: it converts rules that currently survive into conditionally-loaded ones with no checker behind them.

- A second improvements audit of `ctdd-tests` converged independently on the same candidates and the same verdict: build none, every trigger unfired. Existing entries refined (report the marker-removal *event* rather than inferring promotion; altitude churn needs a human behaviour-preserving label as input) and one new candidate filed — a validated craft receipt that checks the disclosure's completeness without certifying its reason. Four rejections recorded with reproductions, including the counterexample showing a mutation score cannot detect altitude: an interaction-coupled and a behaviour-level test both kill the same mutant, and only a preserving refactor separates them. The rationale now states that distinction with the case that shows it.

- Coherence audit after the review run: no contradictions introduced, vocabulary consistent across the three skills, and the repeated softening of absolutes did not dilute the rules (hedge density 0.05–0.16%). One structural drift found and recorded: `ctdd-change` has grown past the point where moving a rule earlier can rescue it — a guarded rule now sits 184 characters inside the truncation boundary, and moving two others in pushed it out. The step-6 split's trigger has fired on that measurement.

- Backlog: four mechanisation candidates for `ctdd-tests` filed with fireable triggers and false-alarm costs — a promotion detector, an observation ledger, altitude-churn analysis, and a sleep-only determinism lint. **None built**: every trigger is unfired. Six proposals recorded as rejected with their measured false-positive rates, including a name linter at 43% and the full determinism clause at 50%, which is why the lint is filed narrowed to sleeps alone.

- Backlog: the step-6 split's trigger was "a rested session" — a schedule, not a failure condition, in the file whose purpose is holding work until evidence arrives. Replaced with a condition that can actually fire, and the rule is now stated once at the top: a trigger names an observable event, or it is an intention to build dressed as discipline. The two ready-to-build entries also gained the half they were missing — what would show each was a mistake.

- Step 7 no longer restates the evidence rule the standing guardrails already carry. The guardrail copy survives compaction and the step-7 copy did not, so the duplication cost attention without adding coverage; step 7 now points at it. 159 characters removed, no rule lost.
- Backlog: the machine-readable test block and the single evidence-verification command are filed as ready to build, with the design settled — a fenced block under the existing headings rather than YAML frontmatter, because a plan may live in plan-mode output or a PR description, and the block must be the human-readable list rather than a second copy of it.

- **README no longer overclaims, in two places where simplifying contradicted the method.** "The contract and the tests can't lie: they run" is false as written — tests can execute perfectly while encoding the wrong business rule, which is the method's own central weakness, and a contract not wired into validation constrains nothing. It now says what is actually true: they can still be wrong about intent, but once enforced they cannot *silently* disagree with the implementation they cover, which a prose spec can. And "that pause before coding is the whole point" contradicted the gate's demotion from main guard to *first* guard: it catches a wrong direction, not a wrong encoding, because at plan time the assertion bodies do not exist yet.
- **README keys hold-outs on load-bearing semantics rather than implementation risk**, matching the fix already made in `ctdd-review`. A payment amendment is routinely normal-risk and still load-bearing.
- **The CI recipe now fetches the scripts.** Installing the plugin puts them in Claude Code's plugin directory on a developer's machine, not in the application repository CI checks out — so the recipe silently ran nothing, or worse, whatever happened to sit at `scripts/` in the target project. It now clones the plugin at a pinned version into `.ctdd/` and calls the scripts from there.

- `ctdd-in-depth.md` given the same rewrite, the largest of the three. The relentless em-dash cadence (over 300 of them) that made the argument exhausting to read is broken into sentences, and the most deeply-nested paragraphs are un-stacked. Every claim, hedge, number, citation, weakness, and *(Proposed — not yet built)* tag is preserved exactly, and verified mechanically after the pass — the density here is partly the argument pre-empting objections, so nothing was simplified away, only made readable. It stays the hostile-review rationale; it just no longer fights the reader to deliver it.
- `ctdd-in-practice.md` given the same rewrite: the em-dash-heavy cadence that read as machine-written is gone, a few passages that assumed the point were re-explained, and the structure and content are unchanged. It complements the new README and points at `ctdd-in-depth.md` for the full argument.
- README rewritten for a senior engineer meeting CTDD for the first time. It now opens with what using the plugin looks like before the philosophy, leads the three-doc split cleanly (README = operating manual, *in practice* = the ten-minute feel, *in depth* = the reasoning), and cuts the em-dash-heavy phrasing that made it read as machine-written. Same content and same six-deterministic-pieces honesty; about 1,000 tokens lighter.

- The status pin in `ctdd-in-depth.md` no longer lists what shipped — the changelog already says that. It keeps only the two things nothing else records: what the skills cost to run, and which mechanisms the document describes but hasn't built.

## 0.20.1 — 2026-07-21

The non-blocking half of the `ctdd-tests` audit: the delete list and the sharpening list.

### Removed
- Eight further clauses of exhortation and repetition — "left unfixed it corrupts the spec", "untested behavior reads as unconstrained", "a flaky perf gate … worse than an honest absence", "this asymmetry is the point", and the sentence in the opening that described what the skill does, which the always-loaded description already says.

### Changed
- **A green property run is sampled evidence, not proof.** The runner exercises a finite configured number of generated cases looking for a counterexample and shrinks one when it finds it; saying so keeps the guarantee honest.
- **Idempotency is stated so it can be asserted**: under the same key, the observable result is identical *and* there is no duplicate side effect. "Twice equals once" is the slogan, not the assertion.
- **"The ecosystem's standard tools" is now "an established, project-approved tool."** Standard is not a property a tool has.
- **An SLO check must name five things** — metric, percentile, workload, environment, threshold. Fewer than five is an aspiration wearing a check's name.

### Kept, against the review
- The delete list marked "tests are the spec for preservation; they do not tell you what new thing to build" as a fourth restatement. It is the routing boundary that sends creation to the business requirement and the plan, and it is the only place this skill says where new behavior comes from. Kept; the genuinely decorative sentence beside it was cut instead.

## 0.20.0 — 2026-07-21

A rule-by-rule audit of `ctdd-tests`, which had never been read clause by clause.

### Fixed
- **The always-loaded description claimed to *enforce* rules the skill only prompts.** `ctdd-tests` ships one file and invokes no checker; it now says it applies criteria and reviews coverage rather than enforcing them.
- **A marked characterization observation had no stated place in a plan.** The distinction added in 0.17.1 landed in one skill and not its consumers. Both artifacts now share the `Preservation pins` heading, because that heading names the direction the evidence runs — green before, still green after — not the artifact's intent. `ctdd-review` accepts either.
- **Two review checks could not produce reproducible findings.** "Mostly asserting on mocks?" and "will it flake?" are now stated as criteria: flag a test whose verdict comes only from collaborator interactions when an observable outcome was available, and name the uncontrolled input rather than predicting flakiness.
- **The authorization-matrix instruction named no mechanism**, despite the skill triggering on it. It now gives the exact generate and check commands, and it has moved out of property-based testing — the generator derives a finite exhaustive table, which is contract conformance, not sampling.
- A surviving mutant no longer implies a weak test: equivalent mutants cannot be killed by any test, and chasing one produces an implementation-detail assertion. A regression test now stays *while the behavior is required*, which stops it contradicting the amendment lane. A flaky marked test has a tiebreak. The name examples now include a behavior-sounding name that is still implementation-coupled.
- "Visual/UX correctness, which tests can't assert" is now a scope statement rather than a false absolute — visual regression and accessibility tooling exist; they are simply out of scope here.

### Removed
- Eleven clauses classified as exhortation or repetition, including two superlatives that offered no decision procedure.

### Added
- Four guards: no skill may claim enforcement it lacks, the authz instruction must name its mechanism, the review criteria must state what a violation looks like, and both evidence artifacts must share the stated plan lane. Suite 140 → 144.

## 0.19.1 — 2026-07-21

### Fixed
- **Step 6 stated a configuration-dependent behaviour as an absolute.** It justified writing the plan before entering plan mode by claiming plan mode's own file is necessarily outside the repository and that an agent inside plan mode cannot create the canonical plan. `plansDirectory` is configurable, so that is a policy about which artifact is authoritative, not a limit of the tool. Rewritten as policy — and the configurable case strengthens the rule rather than weakening it, since pointing it into the repo puts two plans in one directory with only one of them reviewed.

### Added
- The golden test now asserts the authoritative example carries **both** mandated test headings, so it cannot drift from the format again. Suite 139 → 140.

## 0.19.0 — 2026-07-21

Six blockers in the deterministic scripts, all reproduced before fixing.

### Fixed
- **An optional-authentication endpoint was generated as requiring authentication.** Under OpenAPI, an empty security requirement (`- {}`) means auth is optional; the generator denied anonymous callers whenever it appeared beside an alternative, so the matrix asserted the opposite of the contract and the scaffolded tests would have enforced it.
- **The authorization generator published matrices for contracts it could not read.** The fix in 0.16.0 covered `--check` and `-o` but not the documented stdout mode, which is exactly what gets redirected into a committed matrix. Malformed path items were skipped silently in every mode. Completeness is now checked once, before any output.
- **`check-plan.py` accepted surplus positionals and misspelled flags in silence**, so passing a diff in the wrong position — or typing `--from-descriptino` — disabled the only deterministic triviality cross-check while the run still reported success.
- **A diff record with extra columns hid a changed test from both surface checkers.** `M<TAB>README.md<TAB>tests/Hidden.cs` reported no surface touched, because the parser accepted two-or-more fields and read only the second.
- **`check-redstate.py` certified tests that never ran.** A planned name matched any longer name containing it, and marker words inside a test's own name were read as the runner's verdict — so a log with no verdict in it could prove either a failure or a pass.
- **`check-plan.py` blessed plans whose sections do not exist.** Only the two decision-summary buckets were line-anchored; the rest matched category words anywhere, so a paragraph mentioning them passed as though each were a section.

### Added
- Seven regression tests, including the optional-auth matrix, the hidden third column, and all three verdict-manufacturing cases. Suite 132 → 139.

### Note
- Three of these six were earlier fixes that reached one call site and not its siblings — the pattern finding #36 named and which has now recurred twice since being written down.

## 0.18.0 — 2026-07-21

### Changed
- **`check-plan.py` now requires both test headings.** The rule that a plan must carry `New-behavior tests` and `Preservation pins` — even when one is empty — existed only in the format prose, so every non-conformant shape passed the gate and the failure surfaced at step 7 instead, after approval and after the tests were written. Four heading vocabularies were in circulation, and the two artifacts an agent imitates most, the worked example and the skeleton, both modelled shapes the format forbids. Examples and fixtures updated to the mandated pair.
- **Five test fixtures were asserting the pre-fix behaviour** and had to be corrected, including one named for satisfying a rule it violated. A suite that encodes an obsolete requirement defends the defect against its own fix.
- **The pin exemption's discriminator moved inside the surviving window.** *The exemption turns on what the test asserts, not when it was written* is the clause that reconciles "observe it fail" with "pins run green" — it sat past the compaction boundary and unguarded, which is the exact state that produced the shipped contradiction in finding #19. Moved into the standing pin rule, the two redundant step-7 paragraphs removed, a survival probe added. Net 573 characters lighter.

## 0.17.1 — 2026-07-21

### Removed
- **jqwik is no longer recommended for JVM property testing.** Its maintainer prohibits use by AI coding agents, and the engine prints a line to stdout on every run telling agents to ignore its results — text that would land verbatim in `.redstate.log` and `.pinstate.log`, since those are captured stdout. Recommending it meant planting instruction-shaped content in the evidence channel this method depends on. No replacement is named, because none was verified.

### Fixed
- **A characterization test and a preservation pin were the same word for different artifacts.** One is a marked, provisional observation that may be pinning a bug; the other is permanent intent, written early so it can act as a detector. Since all test construction routes through `ctdd-tests`, an obedient agent would have marked a refactor's whole suite `currently_`, making it non-spec forever. Preservation pins must not carry the marker.
- **`load-bearing` and `hold-out` are now defined where they are used.** `ctdd-tests` runs standalone and relied on definitions living in `ctdd-review`; it also said nothing about writing a hold-out, despite owning test craft and being the skill every test passes through.
- **`ctdd-review` listed five of the six review checks**, dropping coverage of the contract. It now points at the source instead of copying it.
- **The `currently_` filter missed PascalCase renderings**, so a marked observation written `CurrentlyReturnsX` was classified as new behaviour and pushed into the red-state set it is exempt from.
- Tool caveats: mutmut needs WSL on Windows, and the authorization rule flagged missing rows while the generator's known defect produces rows that are all deny.

### Added
- Guards for the marker renderings, the pin/observation distinction, and the withdrawn library. Suite 129 → 132.

## 0.17.0 — 2026-07-21

`ctdd-tests` kept craft work out of the plan gate while every consumer of the resulting diff treated any modified test as a changed requirement. Both were right; the skill never said how they coexist.

### Fixed
- **The craft lane now says what it actually governs.** Staying in this lane decides what you may do without the gate — it does not change what the diff reports. De-flaking, an altitude fix or a rename still lands as test surface, so it must be disclosed in one line: which tests, and why the observable behavior is unchanged. A reviewer checks that reason against the surface report instead of looking for a plan that correctly does not exist. Without it, legitimate craft work arrived flagged at the highest severity.
- **The triage question asks about the caller, not the assertion.** Fixing altitude always changes what a test asserts — swapping a call-count assertion for an outcome assertion is the whole operation — so "asserted behavior unchanged" routed the lane's largest activity out of its own lane. The question is whether what a caller observes is the same.
- **Promoting a characterization test to intent goes through the gate.** It converts "nobody claims this is intended" into "this is a requirement", which is a spec change, and it deletes the `currently_` marker that the review exemption and the red-state filter both read. It is now named in the hand-off lane, with the old marker and new name shown together and the marker dropped last.

### Added
- Three tests asserting the cross-skill agreement holds, so this contradiction cannot return quietly. Suite 126 → 129.

## 0.16.2 — 2026-07-21

### Fixed
- **`--test` combined with a `--tests-from` that yielded nothing reported success anyway.** The plan cross-check — the thing that catches a test swapped between plan and implementation — stopped operating silently. It now reports the plan's contribution and refuses.
- **The decision-summary bucket check matched prose anywhere in the document.** "Nothing here is blocking and I am proceeding unless something breaks" satisfied both buckets with neither heading present, while the changelog claimed they were enforced. Patterns are now anchored to the start of a line.
- **The `<n>` / `<name>` plan placeholder split returned** after being fixed in v0.9.4; a bulk path edit reintroduced it.
- **`ctdd-tests`' description had four characters of headroom** against the description cap, with its routing exclusions at the tail — so the next addition would have truncated the part that stops it overlapping the other skills. Trimmed to 1,452 characters, exclusions verified, and a guard now fails below 46 characters of headroom.
- **Hook enablement assumed a clone.** For a marketplace install the plugin lives in a per-version cache directory that is reclaimed after upgrades, so copying a file there is both awkward and temporary. The README now says so and gives the durable alternative.
- **The CI recipe pinned a literal version** that goes stale every release; it now carries a placeholder.

### Added
- Guards for each, including one asserting every skill description keeps headroom below the cap. Suite 122 → 126.

## 0.16.1 — 2026-07-21

### Fixed
- **The evidence rules with the worst drift history were the ones most likely to be truncated.** Red-state discipline, the verdict-not-the-log rule, and hold-out execution all lived inside steps 7 and 9 — which fire latest in a session, which is exactly when compaction has already happened. They are now standing guidance, stated as conditions rather than step outputs, and the survival test guards them.
- **The bug-fix lane's worked example failed both checkers.** It showed a compressed plan as three inline one-liners; a plan in that shape is rejected by `check-plan.py` for eight missing sections and gives `check-redstate.py` nothing to read. Since bug fixes are the modal case, the least-supported path was the most-used one. The example is now a complete short plan with the regression test as a bullet, bound to both checkers by a golden test.
- **The CI recipe made every surface inventory noisy.** It cloned the plugin into the checkout without ignoring it, so the plugin's own tests reported as your changed spec surface. Over-reporting teaches a reader to ignore the verdict just as reliably as under-reporting does.

### Corrected
- **Findings #31 and #33 recorded a false runtime fact.** They claimed `${CLAUDE_SKILL_DIR}` does not exist, and #33 generalised that into a standing caution about reviewers repeating claims. The variable exists — it is the directory containing a skill's `SKILL.md`, added in v2.1.64 — and the verification behind both rejections consulted the plugins reference rather than the skills substitutions table. `${CLAUDE_PLUGIN_ROOT}` is still the right choice here, because it also resolves in frontmatter where the other has open bugs, but that is a reason on the merits. Both findings are amended in place with the original text preserved.

## 0.16.0 — 2026-07-21

Five critical fail-silent defects, all reproduced before fixing.

### Fixed
- **A modified test file with a non-ASCII name passed CI as trivial.** Git quotes such paths by default (`"tests/Ra\304\215unTests.cs"`), and the leading quote defeated every path pattern, so the file classified as no spec surface at all — defeating the one rule the deterministic layer exists to enforce, in exactly the codebases most likely to have accented filenames. Paths are now unquoted in the parser.
- **The step-9 pipeline reported a clean pass when git failed.** A bad baseline left stdout empty and the checker concluded "no surface touched", exit 0, with a modified test in the tree. Step 9 and the plan format now use the returncode-checked `--git <baseline>` invocation that `ctdd-review` already used, and empty input refuses a verdict unless `--allow-empty` is given.
- **Three more ways test names were silently dropped.** An explanatory sentence inside a test list truncated the section; bold, italic and colon-separated bullets were skipped; a bullet beginning with a section phrase inverted the classification. Emphasis is now stripped, `:` accepted as a separator, and a section changes only on a label-shaped line.
- **The pin lane was unreachable for a pure-preservation refactor** — a false blocker in one lane and a usage error in the other. Both test headings are now written every time, and the pin lane names the missing section rather than failing generically.
- **The authorization gate passed over a contract it could not read.** A `$ref`-composed OpenAPI spec yielded zero rows, which `--check` then called current. It now refuses when any path item was skipped or the check would cover zero operations.

### Added
- Regression tests for each, including the quoted-path case. Suite 116 → 121.

### Note
- The durable fix for name extraction is still the machine-readable test list filed in the backlog. Ten instances of one shape is a verdict on parsing identifiers out of free-form markdown; this release narrows the surface, it does not close it.

## 0.15.1 — 2026-07-21

### Fixed
- **Instructions to read the references were themselves being truncated.** The previous release justified dropping the plan skeleton and ADR rules after compaction because a reference backs them — but the lines telling the agent to *load* those references sat even later in the file. The result would have been worse than the original problem: the format gone and the instruction to fetch it gone too. Loaders now sit where the action starts — ADR rules at step 4, the plan format at step 6, colocated notes in the standing guidance.
- **The working-tree re-check moved into standing guidance.** It sat at the far edge of the surviving window, and a tree moving mid-session is precisely a long-session concern, which is when compaction has already happened.
- Step 8 referred to the Amendments rule "below" after the reorder moved it above; it now names the rule without a direction. The plan skeleton offered a `trivial` risk level that the authoritative format forbids, since a trivial change produces no plan at all.

### Changed
- **The compaction test no longer claims more than it proves.** It measured characters while being named for tokens. It is now named as a conservative proxy, uses a pessimistic 3 characters per token instead of 4, and exists to assert *margin* rather than to simulate a tokenizer. Under the tighter bound the furthest load-bearing rule sits around 4,100 tokens.
- **"Loaded somewhere" is now "loaded before it is needed."** That test only checked a filename appeared in the skill; it now asserts the loader precedes the inline section it backs.

### Added
- Guards for the reference loaders surviving truncation, and for the plan skeleton never offering a trivial risk level. Suite 114 → 116.

## 0.15.0 — 2026-07-21

The post-compaction truncation limit was verified against the documentation rather than taken on trust, and measuring it changed what needed fixing.

### Changed
- **Rules that apply throughout now come before the steps that apply once.** After auto-compaction, Claude Code keeps only the first 5,000 tokens of a skill — so at ~5.9k the tail was being dropped from long sessions, which is exactly when the discipline matters most. The section that was disappearing was Guardrails: *no status claim without a run*, the preservation-detector rule, and the distributed-systems escalation. Every step-6 rule already survived, so the split everyone assumed was the fix was not the problem.
- Three more blocks moved up with them, because they were never steps: **amendments** (fires whenever a change touches an existing test), **artifact conflicts** (a stop condition), and the **bug-fix lane** (a classification rule). What is truncated now — standalone-ADR routing, the plan skeleton, the ADR rules — each has a reference the skill loads, and the plan format also has a checker that fails loudly when it is ignored.

### Added
- **A test that asserts the load-bearing rules survive truncation**, not merely that they exist somewhere in the file. Nine named rules must fall inside the first 5,000 tokens; verified by pushing one past the boundary, where it fails. Suite 113 → 114.

## 0.14.6 — 2026-07-21

### Added
- **Guards for the step-6 split, written before the split.** The one remaining structural refactor is also the one most likely to repeat the v0.14.0 defect, where four workflow sections silently moved into a file that almost never loads. Three tests now make that failure loud: eight gate transitions — each traceable to a pilot finding — must stay in the always-loaded skill; a `plan-mode.md` reference, once it exists, must contain none of them; and every reference that exists must be one the skill actually tells the agent to read. Verified against a deliberately bad split, where they fail as intended. Suite 111 → 113 (+1 skipped until the split happens).

## 0.14.5 — 2026-07-21

### Fixed
- **A malformed diff still passed through `check-plan.py`.** The previous release taught the standalone surface checker to refuse a verdict over input it could not parse, but `check-plan.py` imports that same parser and never looked at the result — so it printed "trivial claim stands" and exited 0 over discarded input. Both callers now fail closed.
- **Malformed lines are returned rather than kept in module-level state.** Two callers shared one list, nothing reset it between runs, and a second call could inherit the first's leftovers. `parse_name_status` now returns `(entries, malformed)`.
- **`ctdd-review` asks the hold-out question about load-bearing changes, not high-risk ones.** The method's own example is `Risk: normal` with a hold-out required for money semantics, so keying the review on risk level let a normal-risk payment amendment pass with the question never asked. Risk is implementation complexity; load-bearing is the consequence of getting the semantics wrong.

### Added
- Regression tests for the composed path and for parser state leaking between calls, both verified failing against 0.14.4 first. Suite 109 → 111.

## 0.14.4 — 2026-07-21

### Fixed
- **The plan pointer in the MR description is repository-relative again.** Rooting every plan path at the project directory in 0.14.3 also rewrote the `CTDD-Plan:` line, which after substitution becomes an absolute path — and CI rejects absolute pointers from a description on purpose, because that text is untrusted input. Every plan-carrying change would have failed the gate. Filesystem writes stay rooted; repository metadata stays portable.
- **Unparseable input no longer produces a clean verdict.** `check-spec-surface.py` skipped lines it could not read and then reported "no surface touched" — a conclusion it had not reached, over input it had thrown away. It now names the first bad line and exits 2 without giving a verdict.
- **`check-plan.py` no longer passes when its triviality cross-check cannot run.** CI could ask for a deterministic check, not receive one, and still go green. A trivial claim that was never verified is not a passing claim.
- **`ctdd-review`'s example matches its own instructions.** The prose described rooted, baseline-aware surface collection while the example still showed the old bare command — and an example is what gets copied.

### Added
- Regression tests for all of the above, each verified failing against the previous code first. Suite 107 → 109.

## 0.14.3 — 2026-07-21

### Added
- **Regression tests for the two defects fixed in 0.14.2**, which shipped without them. Both were verified the right way round: they fail against the previous code and pass against the current, so they are detectors rather than decoration. One covers a staged test change (a bare `git diff` reports it as no surface); the other runs the checker from a nested directory with the new test in a sibling, which the old cwd-relative listing missed. Suite 105 → 107.

### Fixed
- **Plan and evidence paths are rooted at `${CLAUDE_PROJECT_DIR}`.** After a `cd` into a module directory, a bare `docs/plans/<name>.md` resolves under *that* directory, so the plan gets written somewhere the reviewer and CI never look — the same defect as the untracked-file listing, in a different place. `ctdd-review` reads from the same rooted location.

## 0.14.2 — 2026-07-21

### Fixed
- **A staged test change reported no spec surface at all.** `check-spec-surface.py --git` ran a bare `git diff`, which compares the working tree against the index — so a test that was modified and then staged returned "no surface touched", exit 0. It now defaults to `HEAD`, covering staged and unstaged together. The previous release note overclaimed: that mode had closed only the untracked half of the blind spot.
- **Untracked files were discovered relative to the current directory.** After a `cd` into a subdirectory, a new test elsewhere in the repo disappeared from the inventory. Both the script and the skill's pipeline now anchor to `${CLAUDE_PROJECT_DIR}`, and a failing file listing reports an error instead of quietly returning nothing.
- **`ctdd-review` now uses the same baseline rules as `ctdd-change`** — merge-base for a branch or PR, untracked files included, commands anchored to the project root. The authoring skill understood baselines while the reviewing skill still ran a bare `git diff`.
- **Two regression tests were being skipped by their own file's documented command.** Both sat after the `if __name__ == "__main__"` block, so running the file directly ran everything except them. Every such block now sits at the end of its file; direct execution went 11 → 15 and 29 → 32 tests.
- Step 8 pointed at an "Amendments" section "above" that the previous release had restored below it.

### Added
- **A structure test that fails when load-bearing routing leaves the always-loaded skill.** It asserts the four workflow sections stay in `SKILL.md`, that the notes reference holds only note craft, and that every bundled path the skill names actually exists. This is the defect that shipped in 0.14.0, and the previous changelog admitted nothing checked for it. Suite 102 → 105.

## 0.14.1 — 2026-07-21

### Fixed
- **Four workflow rules were accidentally moved into a reference that almost never loads.** The v0.14.0 split carried **Bug fixes**, **Amendments**, **When artifacts disagree**, and **Standalone ADR requests** into `references/colocated-notes.md`, which is read only when a colocated note is being written. An ordinary bug fix or test amendment would have run without them, and step 8 referred to an "Amendments" section that was no longer in the loaded skill. The three workflow rules are back in the skill; standalone-ADR routing stays in the skill with its procedure in `adr-rules.md`; the notes reference is note craft only again.
- **`check-spec-surface.py --git` missed untracked files.** The script's own convenience mode ran a bare `git diff`, so a change whose only spec artifact was a new test file reported no surface — reopening, through the simpler documented invocation, the blind spot the skill's pipeline had just closed. Now lists untracked files alongside the diff, with a regression test. Suite 101 → 102.

### Note
- Restoring those rules puts `ctdd-change` at ~5.6k tokens, above the ~5k guidance it met in 0.14.0. Part of that earlier figure was the bug: rules had gone missing rather than moved. The remaining honest reduction is splitting step 6's presentation and storage detail into its own reference, which is also a coherence fix, and the two belong in one deliberate pass rather than another quick one.

## 0.14.0 — 2026-07-21

`ctdd-change` was ~8.2k tokens, well past the ~5k guidance for a skill body. Three blocks accounted for most of it, and all three are needed only at one point in the workflow. They now live in `references/` and load on demand. **No rule was removed.**

### Changed
- **The plan format moved to `references/plan-format.md`** (2569 tokens, 30% of the old body). The skill keeps the field list and a load instruction at step 6. This is the safest block to externalise because it is the one with a checker behind it: a plan written without it is caught by `check-plan.py` rather than shipping malformed.
- **The colocated-note craft moved to `references/colocated-notes.md`** (1328 tokens). Step 10 keeps the trigger — universal rule, deliberate gap, or an external fact — so the agent still knows *when*; the reference carries the entry tests and the durable-fact rule.
- **The ADR rules moved to `references/adr-rules.md`** (238 tokens), beside the template they already pointed at. The skill keeps what an ADR is and when one is needed.
- The design principle throughout: **the trigger stays in the skill, the craft moves to the reference.** A reference that fails to load then degrades quality rather than skipping an action.

### Fixed
- The golden test caught this restructure moving the plan example out of `SKILL.md` and now follows it into the references, so the example and the parsers stay bound wherever the example lives.

Result: skill body ~8.2k → ~5.0k tokens, with ~4461 tokens of references paid only when the relevant step fires.

## 0.13.3 — 2026-07-21

### Added
- **A step 0 that establishes the baseline before anything is read.** The working-tree check used to run at step 7, after the plan was already approved — but what is in the tree decides which tests get retrieved, what the agent thinks current behaviour is, and what contract delta it proposes. All of that is settled before step 7 and frozen by approval. Three real changes were planned against a tree nobody had looked at; one of them proposed a design that collided with work the human had already started.
- Step 0 also separates two situations the old rule ran together: work already under review (PR comments, a feature branch) is **input** and must never be stashed away, while unrelated local edits or someone else's half-finished work on your target files are **contamination**. It fixes the baseline that every later diff check measures from.

### Fixed
- **The surface check now measures from that baseline instead of always `HEAD`.** For a branch or PR, `HEAD` misses everything already committed on it, so a PR-shaped change could report no spec surface at all.
- Step 7 keeps a shorter re-check, since a tree can move while a plan sits under review.

## 0.13.2 — 2026-07-21

### Fixed
- **Triviality is now judged by artifact, not by size, where the judgement is first made.** The workflow opened with "a one-line fix skips most of this" while the bug-fix rule further down correctly said a regression test is spec. Classification happens at the top, so the top is where the right rule has to be: trivial means code-only, behavior-preserving, and touching no test or contract surface, whatever the line count.
- **The hand-off to `ctdd-tests` is now caused rather than described.** "Defer to the ctdd-tests skill" did not guarantee it was loaded; the step now says to invoke it before creating or changing any test.
- **Provenance for external facts was overcorrected.** "Never the citation" also ruled out stable references. A file path does pin your comment to another team's layout, but a contract version or ticket key survives their refactors and tells the next reader where to check. Order of preference is now stated: executable consumer contract, versioned schema identifier, stable ticket or ADR reference, bare sentence last.

### Added
- **A golden test binding the skill's embedded example to the parsers it illustrates.** The example must carry the mandated categorical line, pass `check-plan.py`, and have every one of its proposed test names extracted by `--tests-from`. Until now these agreed only because someone checked by hand; agents imitate the example, so a drifted example produces plans the gate rejects. Suite 98 → 101.

## 0.13.1 — 2026-07-21

### Fixed
- **The bundled scripts could not be found by anyone who installed the plugin.** Every invocation used a project-relative path (`scripts/check-plan.py`), but for an installed plugin the working directory is your project while the scripts live in the plugin's own directory — so the deterministic checks silently were not there, and a project with its own `scripts/check-plan.py` would have run that instead. All script and reference paths now use `${CLAUDE_PLUGIN_ROOT}`, which resolves to the plugin's install directory, quoted because that path can contain spaces. This went unnoticed for the whole pilot because the author works from a local clone, where the agent found the scripts anyway.

## 0.13.0 — 2026-07-21

Fourteen defects from an outside review, reproduced before adopting.

### Fixed
- **`--tests-from` silently skipped test names without an underscore.** A plain PascalCase name (the dotnet default) was dropped by the extraction regex, and the checker then reported success for the subset it could read. Three planned tests, one in the log, exit 0 and "red state verified." Any identifier now matches.
- **Extraction pulled names from the wrong sections.** It read identifier-shaped bullets from every non-pin section, including the "existing behavior" citations the plan format requires, so a fully compliant plan produced false blockers. It now collects only inside the section it is asked for.
- **Pin verification could never run.** In `--expect-pass` mode the script filtered out `currently_*` names, which is exactly the prefix pins are supposed to carry, so it found nothing and exited on a usage error. That filter now applies outside pin mode only.
- **A log in an unexpected encoding crashed instead of returning a verdict.** UTF-16 (PowerShell) or a stray cp1252 byte produced a stack trace, in a workflow whose rule is "the evidence is the verdict line." Both file reads now sniff the BOM and replace bad bytes, so a bad log fails closed with a verdict.
- **The plan linter rejected the skill's own heading.** A behaviour-preserving refactor listing only preservation pins failed the proposed-tests check.
- **The trivial lane could not pass its own CI recipe** — the risk line was specified as terminal output while CI reads the description. It now goes in the description, and "trivial" is gone from the plan's risk-level options, since a trivial change produces no plan.
- **The local surface check was blind to new files.** `git diff` shows nothing for an untracked file, so a bug fix whose only spec artifact is a new regression test read as touching no surface. Fixed with a read-only listing of untracked files beside the diff, rather than staging intent-to-add entries — a verification step must not alter the index.
- **A drafted ADR was never written to disk.** Step 4 drafted it into the plan and no later step wrote the file, so a structural change could ship without one.
- **The plan pointer could resolve to nothing** where `docs/plans/` is git-ignored, which the README explicitly allows — a guaranteed red gate. The disposition is now stated conditionally.
- Cross-skill contradictions: pins were told both to avoid and to use the red-state checker (it is the same script, `--expect-pass` mode); hold-out vocabulary differed between the author and reviewer skills; the design brief had two conflicting homes and no slot in the plan format; and the condensed example omitted the lead summary and categorical line the format mandates.
- The "failed hold-out blocks approval" wording implied mechanical enforcement that nothing performs; it now says plainly that it is a review gate.

### Added
- Six regression tests, including the PascalCase case. Suite 92 → 98.

## 0.12.2 — 2026-07-21

### Added
- **A cheaper middle guard for when a hold-out is declined: human-verified expected values.** The agent writes the test, a human checks the *number* by doing the arithmetic instead of reading the code that produced it. This breaks the shared-computation path, where the test takes its expected value from the same production helper the implementation uses and both encode the same wrong rule. It is explicitly **not** a substitute for a hold-out: it cannot catch a misunderstanding the human shares, which is the whole reason a sealed test is written from the business spec by someone who has not seen the implementation. Named as its own tier so it does not quietly become the reason the hold-out never gets written.

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
