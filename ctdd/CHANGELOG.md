# Changelog

## Unreleased

_Docs and other non-runtime edits collect here and fold into the next runtime release. Version numbers move only when the skills, scripts, or hooks change._

- Backlog: an investigate-without-changing lane filed as two options — a diagnostic mode inside `ctdd-change` that runs steps 0–2 and stops (preferred: no new always-on description, no fourth routing surface), or a separate `ctdd-investigate` skill if the findings output needs a contract the step-2 reading cannot carry. Neither built: the trigger is the same request arriving a third time, or findings having to be re-derived when the change workflow runs afterwards. One occurrence is an idea, not a trigger.

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

## 0.37.0 — 2026-08-03

A full adversarial review of the plugin — 14 parallel agents, most script defects reproduced by running the code rather than inferred. **17 P0s, 9 P2s, 10 P4s and 12 workflow defects**, every fix reproduced before and mutation-tested after. Suite 243 → 289.

### Gate bypasses — the evidence checkers certified false states

- **A fully green run certified as "red state verified."** v0.29.0 disqualified a marker word only when the adjacent character was alphanumeric or `_`, so it fixed one spelling and left `/`, `-`, `.` and space voting: `tests/error/test_capture.py::test_x PASSED` supplied its own failure verdict from a path segment. Step 7.10 runs exactly this command and 7.11 stops on any state but intended red, so an agent that implemented first and captured green passed the gate.
- **A FAILING pin certified as a captured baseline — this lane failed *open*.** `looks_like_pass` had the identical treatment. The v0.29.0 entry closes *"`--expect-pass` failed closed on the same input, so only the safety-critical lane was wrong"* — **that repair opened the lane it called safe**, and a bogus baseline makes v0.35.0's `broken pin` state undetectable in any repository with a `success/` segment.
- **ANSI colour inverted the verdict.** An SGR escape terminates in `m`, so `\x1b[31mFAILED\x1b[0m` disqualified its own marker, the mention survived without a verdict and routed to *passing* — a red test reported as *"passed before implementation"*, with the remediation accusing a correct test of asserting nothing. Most CI runners emit colour by default.
- **`Risk: trivial` inside a fenced block skipped all nineteen checks**, and the format's own worked example is fenced, so quoting it was enough.
- **The categorical line was never required to exist.** Tier, triviality and the hold-out check all read it, and `categorical_line(text) or text` fell back to the whole document — so a breaking contract change with no categorical line derived `medium` from one prose sentence containing `contract: none`, dropping four sections from the gate. An em dash also silenced the hold-out check, and the hold-out block ran to EOF in a plan with no blank lines, letting `rollout options:` in the last line satisfy the actionability check.
- **The tier was inverted and the honest plan cost more.** `_names_a_test` inferred *a test exists* from the **absence** of `none`, so `New-behavior tests: none — pure refactor` derived `large` while empty headings with no test named derived `medium` and passed at 15 of 19. The v0.30.0 guard was defeated by deleting a word.
- **One required section could never be reported missing.** The duplicate scan excludes the categorical `Risk:` line; the missing scan did not, so that line satisfied `Risk level:` and deleting the section outright still exited 0.
- **The plan pointer allowed no markdown prefix**, and the miss is a NOTE — so the description was validated *as* the plan and a leftover `Risk: trivial` in it skipped every check while the real plan file was never opened.
- **`check-redstate` exited 2 while printing "red state verified"**, and `worked-change.md` copies that line into the packet verbatim.
- **A submodule bump read as "no surface touched"** — the exact string SKILL.md 3.3 opens the trivial lane on. Gitlinks now report as *unread surface* and block the lane.
- **The cwd fallback under-reported surface.** `git diff` emits root-relative paths and `git ls-files --others` cwd-relative ones, so running from a subdirectory made markers unread, ADRs unresolved and untracked files invisible. Now `git rev-parse --show-toplevel`.

### The evidence checker lost named tests

- A hyphenated name **truncated to its first stem and then matched everything** — `capture-fails-when-zero` captured as `capture`, which `_match_span` then accepted against every hyphenated name in the log. Two distinct tests collapsed into one and a single failing run certified both.
- A wrapped bullet closed the test section; a section label longer than 72 characters did not close it — and `plan-format.md`'s own conditional label is 76, so copying the skeleton verbatim extracted `n/a` coverage rows as test names.
- A bullet that yielded no name vanished with nothing reported: a fully-qualified `Ns.T::name` or a generic parameter produced an empty section, and the tier, the evidence lanes and the packet all agreed there were no tests.
- **Go and TAP could never verify a preservation pin.** `FAIL_MARKERS` carried `fail:` and `not ok`, so both could report red state, while the pass side had no `--- PASS:` and `ok ` self-disqualified against the TAP test number.

### Workflow defects — instructions that could not be followed

- **The new-behaviour handoff deadlocked.** `ctdd-change` 7.9 invokes `ctdd-tests`; `ctdd-tests` routes *changed expected behavior* back — and a new-behaviour test **is** changed intent, while `ctdd-change` forbids writing test files. Neither could produce the file and step 8's Enter was unsatisfiable. The carve-outs sat *after* the routing gate, so they were never reached.
- **Six stale step references** from the v0.35.0 renumbering: `Skip 7.10–7.12` in a step 7 that ends at 7.11, and a `Stop:` list naming the wrong substeps.
- **A plan with no evidence lane passed the gate and dead-ended** — 7.4 and 7.8 skip both lanes, so step 8's Enter can never be met, *after* a human approved.
- **Step 10 had no reachable execution point**: 9.4 ends *name the final diff and wait* while its Enter was satisfied at 9.3.
- **`defer` had no resolution** — it landed on `NOT RUN — deferred`, which skips rule 8's fallback, since only `declined by human` triggers it.
- **A bare "approve" over an unanswered BLOCKING passed**, and step 7 then began with the agent obliged to guess the one thing the section titled *"BLOCKING — I will not guess"* said it would not. New `--post-approval`.
- **No durable approval record**: four decision artifacts are stdout-only, so a resumed session could establish 6.4 only by inferring approval from artifacts. New `--approval`, with a revision digest so an 8.6 amendment reports **APPROVAL STALE**.
- **8.5 compared in one direction** — a plan naming a contract file whose edit never happened left the inventory a subset, no stop fired, and an approved change did not ship. New `--plan`, report-only.
- **`Business requirement` never reached the gate**, though step 9.2 back-translates against it.
- **The approval gate asked the agent to recommend its own plan**, against 6.4's exclusion list.
- **The negative control mutated production during step 7** — scoped now to the lane with no plan in flight. *(Introduced in v0.33.0 and not checked against `execution.md`.)*
- **The test verdicts collapsed into `test-quality`**, so `add-coverage` could never produce `needs-tests`, and `rename` — a naming preference — was carried into a skill that omits preferences.
- **The plan directory was hardcoded in eight places** while the checker honours `planDir` and rejects any pointer outside it: configurable and unusable. New `--plan-dir`.

### Guards that did not guard

- The v0.31.0 guard **passed with every rule it covered inverted** — a list of substring checks, rule 8's third named failure.
- **The survival probes were structurally unreachable, and the wrong constant had been moved.** Restoring the proxy showed the guard that originally fired was the 500-char reserve, which the file itself labels *EARLY WARNING, NOT PROTECTION* — and the response had raised the constant the probes slice on. The stated justification, *"measured 4.00"*, was `len(body)/(len(body)//4)`: 4.00 for any text. Probes now assert **offset**.
- The quoted-literal guard **skipped the block it was written for** and compared five words, so a truncation always passed. It found three live truncations.
- The reference-loader guard asserted the filename, not the loader; the enforcement-claim guard was case-sensitive and frontmatter-only, and found two live claims.
- **Nothing resolved an `N.M` step reference.** The new guard found the stale references above on its first run.
- Three hook guards passed with their rules deleted, using paths that matched nothing.
- **The suite was not green on Windows** — 27 call sites decoded with the console codepage, and a mangled `Risk level: trivial —` turned the newline-bypass *rejection into an acceptance*.

### Evaluation corpus

- The only eval guard was a **two-phrase whitelist over one of three files**, so 49 of 80 cases were read by no test — and a third phrasing of the defect its docstring cites was live and green.
- **Pressure cases could not fail on folding**: scored by `should_trigger` alone, a skill that holds the wall and one that folds score identically. All 13 now carry `must_not_fold`.
- Seven reject and positive clauses had no case at all.
- **The eval-CI backlog entry named the wrong blocker.** `claude plugin eval` discovers `evals/<case>/prompt.md` with `graders/<name>.md` and has **no `should_trigger` grader**; pointed at this directory it finds zero cases. Every item gated on "eval CI runs" is blocked behind converting all 80 cases, not behind wiring CI.

### Configuration, platform and reporting

- An override yielding no patterns silently emptied the spec surface; the advisory hook blocked on `PreToolUse`; `.ctdd.json` was discarded through a BOM or UTF-16; approval baselines were invisible in a dotted `.Tests` project — the dominant .NET Verify layout, where re-recording one makes an implementation pass **with no test file edited**.
- A letter-prefixed `ADR-NNNN-slug.md` resolved to nothing, reporting `BROKEN ADR markers` on a healthy repository; `--allow-empty` was forwarded to git and unreachable; marker reads were uncapped; a non-mapping operation was dropped without a warning; an unparseable contract produced a clean matrix over **zero operations at exit 0**.
- The Write guard discarded the replacement text, so a stub overwriting a 400-line suite got byte-identical advice to one that adds a case.
- The README pointed marketplace users at `.claude/hooks.json`, which Claude Code does not load.

### Reference and example repairs

`check-spec-surface` appeared **zero times** in the worked example, leaving 3.3 and 8.4 undemonstrated; `Pin state before` and `after` were byte-identical; the example demonstrated the gate in the wrong order; the canonical plan violated field rule 4 by marking `Side effects` *Always* with no case addressing it.

### Budgets

- **`BODY_LIMIT_CHARS = 15,500`, decoupled from the compaction proxy.** The limit was `proxy − margin`, two properties on one dial — which is how v0.31.0 went wrong. The proxy stays at 15,000; probes assert offset against `MAX_PROBE_OFFSET_CHARS`. At an outside tokenizer's 4.16–4.50 chars/token this is **69–75% of Anthropic's ~5,000-token guidance**.
- Route ratchet 41,000 → 42,700 across the review, every raise preceded by displacement.

## 0.36.0 — 2026-08-03

Parts C and D: references left behind by the last four releases' repairs, and spec rules that were mechanically checkable and unchecked.

### Fixed — enforcement
- **The decision summary is checked.** Deleting it from the format's own canonical example still exited 0 at 19 of 19, while 6.1 leads the gate presentation with it and 6.2 copies it verbatim into the plan-mode surface — the whole gate rested on text nothing could see. It is the plan's opening prose with no heading of its own, so it is checked against the known section headings rather than by a pattern of its own; a first attempt matched any opening line and passed a plan starting with `BLOCKING`.
- **Field rule 9 is enforced.** Wildcards, bare directories, `(+ tests)` and `TBD` in a path now fail the gate. These paths feed `check-redstate --tests-from`, so the gate was blessing paths no test file can be written to.
- **`check-plan.py` prints a plan revision digest.** *"An Approval record for the current plan revision"* named something defined nowhere and recorded nowhere: 8.6 edits the plan in place at the same path, so a pre-amendment approval was textually identical to a current one, and one pilot plan ran to 28 amendment rounds. The Approval record now carries `plan: <path>@<revision>`. Honest limit: self-reported. Where `docs/plans/` is tracked, the git blob id is the only fully mechanical form.
- **An indented continuation bullet is no longer extracted as a test name.** `  - note: the boundary is exclusive.` became the test `note`, which `check-redstate` then reported *not found in the log* at 7.11 — after approval and after the tests were written, with no diagnostic naming the cause.

### Fixed — references
- **`adr-rules.md` rule 2 carried the pre-v0.31 write freeze** — keyed on an Approval record existing at all, so an agent following it for ADR timing wrote the ADR while an amended plan sat unapproved. The reference was looser than the gate it serves.
- **The four-digit ADR rule collided with a three-digit series.** The reader is deliberately width-agnostic and strips leading zeros, so `001-` and `0001-` resolve to the same decision; a repo numbering `001`–`014` now continues at `015`, and `0001` is used only for an empty directory.
- **`Status: Accepted` was unreachable**, so rule 15's append-only freeze never fired and a shipped decision's Context and Decision stayed rewritable for life. Rule 7 now promotes on ship.
- **Rule 17 ordered the agent to edit test files**, which the guardrail forbids — it now asks `ctdd-tests` for the test markers and marks contracts itself.
- **`rationale.md` predated the tier system entirely** (zero occurrences of "tier") and stated that `check-plan.py` validates *that exact section structure*, when it validates `required_for(tier)` — a maintainer reading it would "fix" the tier sets and reopen the both-lanes hole. A tier section is added and the claim corrected.
- **`ctdd-review` is told where the evidence logs live.** It requires pre- and post-change pin passes and the paths appeared nowhere in that skill; where `docs/plans/` is git-ignored, neither plan nor logs reach the repository, so the packet must carry them.
- **The colocated note has a defined path.** Rule 2 required *the exact path named in the approved plan*, and no plan section names one — so the step either skipped a required output or wrote to an unapproved path after the diff went to review. It now writes to the governed path and reports the write as a post-approval spec-surface edit.

## 0.35.0 — 2026-08-03

Part A: seven fail-open paths where evidence certified nothing.

### Fixed
- **A markdown heading bypassed the both-lanes-none guard.** `_LANE_NONE` omitted the heading prefix every REQUIRED pattern allows, so `## New-behavior tests: none` derived `small` while the same plan with bare headings derived `large` — a cosmetic choice deciding whether a plan declaring zero tests passed the gate, reopening v0.30.0's hole through that fix's own regex. **That fix had shipped with no tests at all**; both heading-style cases are now covered.
- **A pin that passes before and fails after had no state.** The seven-state vocabulary had `pin fail: a named pin fails *before* the change`, whose action is *"the pin describes behavior the code never had; return to step 6"* — so the single most important signal this method produces routed to a row telling the agent to amend the pin away, with only a guardrail between it and that. A **broken pin** state is added: *this is the finding, not a plan defect; do not amend the pin away and do not weaken it; return to 8.1 with the implementation, never to step 6 with the plan.*
- **The trivial lane stopped running anything.** 8.5's `treat 8.3 and 8.6 as n/a` cancelled all five of 8.3's obligations, only one of which is plan-dependent — so the lane admitted on *named* existing tests never ran them, and a rename that does not compile could ship. Now only the pin re-run and 8.6 are `n/a`; the validator, tests, suite and build still run.
- **7.7 wrote the pin-state-after log before implementation.** v0.31.0 deleted its unevaluable trigger but kept the obligation, making the after-run unconditional inside step 7 — so `.pinstate-after.log` was always created from a pre-change run and only later overwritten at 8.3, which may never run. `check-redstate` cannot tell the two apart. 8.3 owns the after-run; the step-7 duplicate is gone.
- **Step 8's Enter was satisfiable by the empty set.** v0.30.0's repair was tier-only, so a `large` plan writing all 19 sections with both lanes `none` still skipped both lanes and emitted a conformant packet reading `Red state: n/a` beside a genuine human approval. The Enter now requires at least one lane to name a test.
- **`check-redstate` exited 0 while certifying a subset.** A `currently_`-prefixed name under the new-behaviour heading is reclassified and dropped — correctly, since it marks an observation — but `plan-format` puts those under `Preservation pins`, so one there is a plan defect, and step 7.12 and step 8's Enter both key on this exit code. It now exits 2: the reclassification is reported *and* uncertified, rather than reported and blessed.
- **`trivial claim stands` reported more than it inspected.** The lane has two conditions; the cross-check reads paths, so it cannot see 3.4's behavior-preserving requirement — a changed validation limit in one production file produced the same verdict as a mechanical rename. Message only: *survives the surface check… NOT checked: 3.4's behavior-preserving requirement. This reads paths, not hunks.* No heuristic was built; three attempts at that class were killed at 43–50% false positives.

### Changed
- Route ratchet 41,500 → 41,800, net of deleting 7.7's pre-implementation after-run.

## 0.34.0 — 2026-08-03

Four guards that did not guard, all reproduced by mutation before and after. Until these worked, nothing protected the repairs of the last three releases — including the ones they were written for.

### Fixed
- **The v0.31.0 guard passed with every rule it covered inverted.** It was a list of substring checks, so rewriting the write freeze to *"Once an Approval record exists … write whatever you like; the only file you write is the step 5 plan file is not a rule"* left it green. Rule 8's third named failure verbatim. It now asserts whole sentences; all four of the reviewer's inversions fail.
- **The survival probes were structurally unreachable, and the wrong constant had been moved.** Setting the proxy back to `5000 * 3` produces exactly one failure: the **500-char reserve**, which this file itself labels *EARLY WARNING, NOT PROTECTION*. v0.31.0 responded to that early warning by raising the constant `_surviving_head()` slices on, by 2,500 — which rule 9 says to check first. And the stated justification, *"measured 4.00"*, was `len(body)/(len(body)//4)`: 4.00 for any text at all, a tautology rather than a measurement. The proxy is restored to 15,000, the reserve lowered to 300, and a new `MAX_PROBE_OFFSET_CHARS = 13,500` asserts **where** each must-survive rule sits rather than merely that it is present — the presence form goes vacuous the moment the body is smaller than the proxy, because then the head slice is the whole body. Moving a probe to the end of the body now fails, naming the rule and its offset.
- **The quoted-literal guard skipped the block it was written for.** It only inspected lines *starting* with a checker prefix, so the whole review-packet block — `Plan check: `, `Red state: ` — was skipped and a fabricated `BANANA PANCAKE VERDICT` passed there; and it compared five words, so a truncation is a prefix of the real literal and always passed. Now token-wise, end-anchored, holes and digits wildcarded. It immediately found **three** live truncations, not the one reported.
- **The reference-loader guard asserted the filename, not the loader.** Every reference is also named in the Output contract table, so replacing step 5.1's `Read references/plan-format.md.` with prose left it green while the fallback it protects had stopped existing.

### Fixed — references
- `worked-change.md`'s packet quotes regenerated: the plan-check verdict was missing the tier and N-of-M count, and both pin-state lines dropped the re-run sentence.

## 0.33.0 — 2026-08-03

Seven `ctdd-tests` repairs plus the negative control. All eight are instructions that could not be followed, or a discipline the pilot used and never wrote down.

### Fixed
- **The authorization-matrix command exited 2 as written.** No OpenAPI argument was named, `-o` was never mentioned though the instruction says to write to the contract path, and `--check` needs the spec too. Both forms are now shown with their arguments and verified to run. **The all-deny caveat is restored with them**, and it is the dangerous half: the generator synthesises one identity per scope and never a combination, so an AND-ed-scope operation is structurally all-deny — read as a contract fact, that scaffolds a 403 assertion for the legitimately authorised caller and inverts the contract in the authorization domain.
- **Step 7 accepts a passing pin.** It preserved a *failing* new-behaviour test and routed every other result to the blocked table, so the mandatory outcome of `must pass before refactor` — and the craft lane's unchanged verdict — had no accepting branch, and the nearest table row was a word-level match for the wrong lane. The sibling had this defect and it was fixed there; the repair was never made here.
- **The craft lane reads the criteria that govern craft.** Its three jobs each have their operative rule inside `Test review`, which is scoped to the review lane — so the lane doing the work never entered it. De-flaking by adding a retry is what item 6 exists to forbid.
- **The promotion rule has all three parts again.** v0.17.0 fixed this with *named in the hand-off lane, old marker and new name shown together, marker dropped last*; two thirds were compressed away with no changelog entry, and the guard passed over the remnant. `currently_` is the discriminator both `ctdd-review`'s pin exemption and `check-redstate`'s classifier read.
- **A blocked row for a checker that cannot run or exits `2`, and `checker` in the guardrail.** `ctdd-tests` is the only skill that runs the checkers and carried neither. The rule existed twice — in the two skills that do not run the command.
- **The jqwik warning describes the hazard instead of reproducing it.** The quote was truncated past its scoping clause, leaving an unscoped *Disregard previous instructions* in the always-loaded surface on every invocation, including Python and Go work that will never touch a JVM — the same injection one trust level above the evidence channel it warns about. The maintainer attribution is restored.
- **The per-test verdict vocabulary maps into `ctdd-review`'s findings.** `ctdd-review` mandates applying this section to every changed test, but its own categories are disjoint and `keep` is a non-finding it forbids emitting three ways. `reduce-interaction-coupling` is also back, having been swapped out while the dimension that produces it survived.

### Added
- **The negative control** (backlog C1): break the one production rule the test names, re-run, revert — green against the broken rule means the test asserts nothing. The pilot invented this twice under pressure (finding #12) and never wrote it down; it is the tool-free form of the mutation testing the skill already recommends, and the backlog rejects mutation testing *as a gate*, which this is not. The revert must be verified by re-running the same command and confirming a clean production diff, because it licenses a production edit inside a lane whose guardrail forbids one.

### Fixed — docs
- **Finding #58's conclusion corrected.** It claimed `ctdd-tests` and `ctdd-review` prose lost nothing, directly above its own block restoring two clauses into `ctdd-tests` — a file rewritten prose-to-contract in the same pass. The control-group claim holds only for `ctdd-review`. This is the mechanism the finding itself names: an auditor reads *lost nothing*, scopes their pass elsewhere, and the defects survive another round.

## 0.32.0 — 2026-08-03

Five findings from a `ctdd-tests` review, all script-, eval- or reference-side. Two of its three framing facts were already stale — the body limit is 17,000, not 14,500, and the suite is green — but `ctdd-tests` was byte-identical to what it read, so the findings stand.

### Fixed
- **The jqwik guard passed with its rule deleted.** `for line in t.split("\n"): if "jqwik" in line ...` — with no jqwik lines the loop body never runs. That is CLAUDE.md rule 8's first named example verbatim, and blind to exactly the regression 0.21.2 shipped. It now asserts the warning **exists** and checks a stable marker instead of requiring the injection string verbatim, which had turned a hazard into a required invariant. Mutation-tested both ways.
- **The enforcement-claim guard was case-sensitive and frontmatter-only.** `assertNotIn("Enforces", desc)` let *"it enforces behaviour-level naming"* through — and that sentence had already shipped, in **two** places the widened guard immediately found: `docs/ctdd-in-depth.md` and `README.md`. `ctdd-tests` invokes no checker, so both now say *derives*. Rejection claims are ruled out too: a skill can never reject, only route.
- **Approval and snapshot baselines are test surface.** `.verified.*`, `.approved.*`, `.snap` and `__snapshots__/` were in no pattern, so re-recording a baseline (`verify --accept`, `jest -u`) made an implementation pass with **no test file edited** — evading the guardrail's verb list entirely and landing as `other` in every deterministic consumer. A spec amendment with no artifact.
- **The equivalent-mutant claim was false as written.** *"cannot be killed without coupling tests to implementation"* implies a white-box test could; an equivalent mutant is semantically identical and no test kills it. Restored to the changelog's own corrected wording — *by any test* — because the reading it licensed was to write the implementation-coupled assertion the guardrail forbids, on money and authorization cores.
- **Two eval cases asserted `should_trigger: true` for phrasings the description rejects** — *"update them to match the new code"* and *"just sync them with what the code returns now"* — while `ctdd-change-triggers.json` marks the same shape true, so both sets claimed the same request. Flipped, with the routing reason recorded on each case.

### Added
- Guards for the approval-baseline patterns and for eval/description agreement. The evals have never been executed, so nothing else would have caught the repeat of a defect the changelog already records fixing once.

## 0.31.0 — 2026-08-03

Six workflow transitions that could not be executed as written. None is new guidance; one is a deletion.

### Fixed
- **6.4 excludes harness acceptance again.** The v0.21.x prose-to-contract rewrite left four exclusions where the changelog records five; the harness clause survived only in the Output contract's `Decision prompt` row. It is least redundant exactly where it was dropped, because 6.2 still writes the summary into the plan-mode surface — the one case where a plan-mode approval genuinely responds to the CTDD summary.
- **The trivial lane can be unwound.** 3.7 said *return to 3.1 as plan-gated*, but step 4's Enter was *step 3 did not fire 3.6* — permanently false once it had. The only executable path was to continue down a lane the agent had just been told it did not qualify for, with a trivial declaration already in the PR description. 3.7 now retracts the declaration, and step 4 admits a retraction.
- **`approve with changes` and `reject` are consumed.** 6.3 mandated a three-option prompt; 6.4 defined satisfaction only as an affirmative message, so *"approve, but use 409 not 422"* satisfied the gate and 6.5 authorised executing a plan file that still said 422. Changes now amend, re-check and re-present; reject stops.
- **The pre-approval write freeze re-arms.** It was keyed on *the step 6 Approval record exists* — existence, not currency — so it discharged permanently at the first approval and imposed nothing while an 8.6 amendment waited for re-approval. Now keyed on the current plan revision, which an amendment voids.
- **Step 8 admits the trivial lane without assuming a plan.** Its body re-runs pins *named in the plan* and compares against `Files likely to change`, neither of which exists in that lane — leaving 8.5 to compare the diff against itself. 8.5 now compares against the declared diff there, and 8.3 and 8.6 are `n/a`.
- **7.7's unevaluable trigger removed.** `preservation-only conversion` occurred once in the entire skills tree — in the clause requiring it — and `plan-format.md` declares no section by that or any equivalent name, so nothing in a plan could signal one. The pin re-run it was bundled with is kept.

### Changed
- **The compaction proxy uses a measured ratio: 5,000 × 3 → 5,000 × 3.5.** The token budget never changed; the characters-per-token used to express it was a worst case of 3, while these bodies measure **4.00**. So the limit sat at 72% of Anthropic's ~5,000-token guidance while presenting itself as the ceiling, and blocked correctness work on that basis. Still below measured density, so the survival probes keep a margin. This does not validate the 5,000 itself — compaction behaviour here has never been measured, and one long session run to a compaction is the experiment that would settle it.
- Route ratchet 41,000 → 41,500 for the six repairs above.

## 0.30.0 — 2026-08-03

Four defects from a second adversarial review, both measurable ones reproduced first. Six further findings need skill-body edits and are held for approval per rule 3.

### Fixed
- **A plan naming no test in either lane could be `small`.** The tier was derived from `New-behavior tests: none` alone, so declaring `none` in *both* lanes passed at 8 of 19 — no red-state log, no pin log, no `ctdd-tests` invocation, and step 8's *satisfied every applicable evidence lane* met vacuously. Weaker than the trivial lane the tier system was built to close, which at least demands named existing tests. Both lanes declaring `none` now derives `large`. Read from the heading line, because scanning the block below matched the shell commands under `Verification`.
- **A `currently_`-prefixed name under the new-behaviour heading is now reported.** Extraction drops it — correctly, since the prefix marks a characterization observation that must not be demanded to fail (findings #29, #36) — but silently, so a plan naming four tests produced *"all 3 new test(s) observed failing — red state verified"* with nothing to show one had left the red set. The reclassification is printed and the rest still verifies; exit code unchanged.
- **`plan-format.md` rule 6 no longer licenses the agent to supply the expected value.** It said each hold-out assertion names *an observable input and the expected output*, while rule 8 requires the human to recompute every value by hand — so followed literally, the sealed test encoded the agent's own arithmetic and could not contradict an implementation from the same reading. Now: *which* output to assert, never the value.
- **`worked-change.md` regenerated against the current skill.** It still described printing the complete plan verbatim, quoted a `check-plan` string the script has not emitted since tiers landed, and told the agent to replace a BLOCKING question in place rather than move the answer to `Decisions confirmed in session`.

### Added
- A guard comparing every `check-plan:` / `check-redstate:` / `check-spec-surface:` line quoted in a reference against the scripts' actual literals, with numbers normalised so counts may differ. The example taught a verdict string for four releases after the script stopped printing it, and nothing compared them.

## 0.29.1 — 2026-08-03

### Changed
- **Skill prose is no longer frozen; it needs the human's approval.** Rule 3 asked for a freeze that was never quite true — prose changed anyway, and the freeze framing meant the argument happened after the edit rather than before it. It now asks for the same evidence and the same displacement, but as a **stop-and-ask**: name what it displaces, what it costs against the body and route budgets, and what evidence demanded it, then wait. The `real-use finding, not a review suggestion` bar is unchanged.
- The rule also states what this session got wrong twice: **a budget guard firing is not permission to drop the cheapest item and call it a displacement.** Where the only honest resolution is a human decision, say so rather than resolving it quietly.
- `CLAUDE.md`'s runtime note and `docs/backlog.md`'s governing rule and Tier 4 heading no longer say *frozen*; they say the change waits for a trigger **and** an approval.

## 0.29.0 — 2026-08-03

Fourteen defects from an external adversarial review, every one reproduced before fixing. Nine were in code changed during the preceding sessions.

### Fixed — critical
- **A fully green run certified as red state.** `_verdict_text` stripped the matched test name but left the rest of the line, so `tests/test_error_paths.py::t PASSED` put `error` at index 12 against `passed` at 30 and first-marker-wins read a PASSED line as a failure. Step 7.11 runs exactly that command and 7.12 treats exit 0 as intended red, so an agent that implemented first and captured green passed the gate — the vacuous-test case the script exists to catch. Markers must now match as whole words. `--expect-pass` failed closed on the same input, so only the safety-critical lane was wrong.

### Fixed — the gate could be skipped
- **The word `trivial` anywhere skipped every check.** `TRIVIAL` was the one required pattern left unanchored, so `Residual risk: trivial — …` in a mandatory section, or prose describing the lane, exempted the plan from every section, duplicate, tier and hold-out check. Line-anchored like the rest.
- **Tier, triviality and hold-out now read the categorical line alone.** All three searched the whole document: a stray `contract: none` in prose downgraded a contract-bearing plan to `medium`, and a superseded `hold-out: not required` in an amendment beat the real declaration, skipping the actionability check entirely.
- **The categorical line is matched without assuming field order.** Requiring `contract:` before `hold-out:` made a reordered line count as a second `risk level` section — a `DUPLICATED` error naming a section that does not exist, which step 5.4's *re-run until it exits 0* cannot converge on. Also fixes an off-by-one that dropped the last character of a match on a final line with no trailing newline.
- **`--diff` includes ADR surface and refuses empty input.** CI blessed as trivial the same ADR-touching diff the runtime gate calls SPEC SURFACE TOUCHED; and a zero-byte diff — from a wrong base ref, a shallow clone, or staged work against an unstaged diff — verified a triviality claim over nothing inspected.
- **`business requirement` and `intended behavior` are required at every tier.** Every bug fix lands at `medium` by construction, since 5.3 requires the regression test be named, so the small tier is unreachable — and the modal case was gated on a plan that never said what it was for, with step 9.2 back-translating against a section that need not exist.

### Fixed — configuration and platform
- **An override that yields no patterns is a configuration error.** `CTDD_TEST_PATTERNS=";"` is truthy, discarded the defaults and split to zero segments with no `re.error`, so the trivial lane, the CI cross-check and the hook all went silent at once while the report still said *env overrides honored*.
- **The advisory hook no longer blocks.** Exit 2 from `PreToolUse` is the block signal, so one typo in a regex blocked every Write in the session. `PostToolUse` keeps exit 2, where there is nothing left to block.
- **`.ctdd.json` is decoded through BOM and UTF-16.** PowerShell's `>` writes UTF-16LE and `Set-Content -Encoding UTF8` writes UTF-8+BOM; both raised `ValueError`, were swallowed, and every setting silently reverted to defaults on the platform this repo documents interpreter fallbacks for.
- **ADR lookups anchor to `CLAUDE_PROJECT_DIR`.** From a subdirectory they returned a confident wrong directory rather than the ambiguity the escape hatch exists for — writing `0001` beside an existing series.
- **`check-spec-surface` reconfigures stdout to UTF-8.** A non-ASCII path raised `UnicodeEncodeError` on a legacy codepage, truncating the inventory and exiting 1 — the same code that means SPEC SURFACE TOUCHED, so a crash read as a finding.

### Fixed — a guard that was not guarding
- **The format-drift guard checks `required_for(tier)`, not just `REQUIRED`.** It asserted every mandatory heading had a pattern, never that the pattern survived into the tier sets — so deleting a name from `MEDIUM_SECTIONS` left it green while the drift was live. Rule 8's own test: delete the rule the guard covers and confirm it fails. It did not. The nine sections a tier omits are now marked conditional in `plan-format.md`, and the guard derives that set from the format rather than a hardcoded list.

## 0.28.1 — 2026-08-03

### Fixed
- **"Changed test expectations are changed requirements", not "changed tests".** A rename, de-flake or altitude repair is a changed test and not a changed requirement — `ctdd-tests` keeps those in its own lane on exactly that basis, and `expectation` is already the term of art in its dimension 4. The absolute form coexisted with the craft lane in v0.20.1 too, so this is a precision fix rather than a defect repair.
- **Rule 8 compressed to its two imperatives.** Recompute each value by hand from the business requirement, never by reading the code that produced it; offer it as the fallback, never as the equivalent. The explanation of why reading the implementation inherits the misunderstanding belongs in the findings log, not in a file loaded on every plan-gated change. Both imperatives kept — the 0.21.x mistake was compressing away the semantic condition, not compressing.
- **The changelog no longer claims a `consumer pin` field exists.** It is demonstrated in the worked example only; no field rule requires it and `check-plan.py` does not check it. The example teaches, but the entry described a contract that was never written — the example-versus-contract ambiguity this project keeps trying to eliminate.

### Changed
- **A section repeating what another already carries is a fault.** The two-reader block licensed unbounded detail below the summary without saying anything against repetition, which is what 28 amendment rounds actually produced. The permission stays; the constraint is new.

## 0.28.0 — 2026-08-03

### Restored
- **"A flaky spec reads as an unreliable spec, to the agent and the human, so retrying around it is never the fix."** The determinism dimension names the uncontrolled input; it never said why. The argument decides cases the dimension does not enumerate.
- **"A bug-fix regression test is the spec of the fix and stays as long as that behavior is required; deleting it later removes the spec."** Dimension 4 covers deleting it as a spec amendment, but not why it persists.
- **Step 0 reports when the current branch is the target branch** — the change is landing where it would be reviewed from. Step 0 recorded `branch=<n>` and never remarked on it; the 2026-08-03 baseline read `branch=main` in silence. Phrased against the declared target rather than a hardcoded `main`, so it holds for any trunk name.

### Changed
- **Route ratchet 40,400 → 41,000.** ~10,250 tokens, 5th of Anthropic's 62 shipped skills by loaded prose. Two of the three restorations landed in `ctdd-tests`, which needed no increase at all; only the branch check touched the constrained budgets. The headroom is deliberate — a ceiling with 48 characters spare is what caused a requested addition to be dropped and reported as a displacement.

### Audit closed
- Every rule-shaped and prose line that has existed in `skills/` since v0.11.3 — **267 in total** — has now been read individually rather than matched. Fourteen losses, all purpose sentences attached to surviving structures. Five restored, four covered by successors, three marginal, two were the hold-out clauses restored in 0.26.2. `ctdd-review` prose lost nothing. **This entry originally said `ctdd-tests` lost nothing too, directly above its own `Restored` block restoring two clauses into that file** — and `ctdd-tests` was rewritten prose-to-contract in the same pass as `ctdd-change`. The v0.32.0 review then found seven further losses there, exactly the way finding #58 predicts: an auditor reads *lost nothing*, scopes their pass elsewhere, and the defects survive another round.

## 0.27.2 — 2026-08-03

### Restored
- **"Changed tests are changed requirements and contract diffs are boundary changes: the packet presents them as the spec, not as code."** Step 9 had been left saying *assemble its exact packet* — a shape with no reason. This is the method's thesis and the reason `check-spec-surface` exists.
- **The back-translation is derived from the changed tests alone, and placed beside the business requirement so the human compares prose to prose.** Without the first clause it is a summary of the diff rather than independent evidence; without the second there is nothing to compare it against. It is the cheapest wrong-encoding detector in the method and the only one that runs on every change.

### Added
- A guard on both, and finding #58: all 102 rules from v0.20.1 read one at a time, twelve losses, every one a purpose sentence attached to a surviving structure. Two automated passes missed all twelve because a purpose sentence is built from the same words as the structure it explains.

## 0.27.1 — 2026-08-03

### Added
- **`consumer pin` shown in the worked contract-changes entry.** `consumers: <names>` is a list; a pin is a test that fails in CI when compatibility breaks. It is demonstrated in the example only — no field rule requires it and `check-plan.py` does not check it — because there is still no observed instance of an unpinned consumer breaking downstream. This project's evidence is that the example is the operative instruction, so it teaches; but it is not a contract, and 0.27.0's own judgement that it lacked an observed instance was correct. Promote it to a field rule with a guard when that instance arrives.

### Changed
- **Both budget guards now state what they are and what they are not.** The compaction reserve is early warning: the survival probes slice at the proxy itself, so the reserve guards them by nothing — and at 14,500 the body limit is already stricter than Anthropic's ~5,000-token guidance (~3,600 tokens, 72%). The route ratchet is a ratchet, not a budget: no published guidance bounds per-change reference load, the number was set to wherever the content happened to be, and its only job is to make growth a decision.
- **`CLAUDE.md` rule 9 gains its missing half.** It said *displace or decide, never shave*. It now also says check what the number is before treating it as a constraint, and never resolve a budget conflict alone — the guard once caused an addition the human had asked for to be dropped silently, which is the failure to avoid.

### Noted, not fixed
- `plan-format.md` (14,591 ch) is larger than the skill it serves (14,032). 42% of it is the complete example, which this project's own evidence says is the operative instruction — so the proportion is defensible, but it is the one place a reference outweighs its skill.

## 0.27.0 — 2026-08-03

### Changed
- **The plan is stated as having two readers, and the gate follows from it.** The summary is for the human: a few minutes, and a reader who agrees with every recommendation approves from it alone. Everything below is for the agent implementing it and for the reader who disagrees — exact names, values and paths, with **no ceiling on how much of that a change needs**. Length below the summary was never the fault; a summary that does not stand alone is.
- **The gate prints the summary and the `Hold-out` block in full**, not eight sections. Printing all eight made the gate scale with the plan and stop being a few-minute read. The summary now names every other refusable decision — `Assumptions`, `Uncovered or ambiguous`, `Known gaps`, `NFR budgets`, `Residual risk`, `ADR draft` — one line each, with the sections offered and printed on request. The hold-out keeps its exemption: it is the one item asking the human to leave the terminal and do something.
- **The categorical `Risk:` line closes the summary** rather than opening it. It is form-like and it is what `check-plan.py` parses to derive the tier — the other reader's input, at the summary's foot.

### Restored
- **Length below the summary is not a fault; a summary that does not stand alone is.** Folded into the two-reader sentence rather than added as its own line — the conclusion of the reframing, and it had been trimmed for 80 characters.
- **Capture the human's stated direction, not a competing one; a decision handed back unresolved returns to `BLOCKING` with their version as the default.** Lost at v0.21.0. Observed three times: the agent correcting the human wrongly on a load-bearing claim, re-raising settled decisions, and resolving the `≥50` semantics itself after the human bounced the question back. Worded to the shape that actually failed rather than the v0.11.3 original.
- **The current-behavior reading is offered for correction, never as ground truth.** The `Correct this reading` line survived; the prohibition behind it did not.
- **Not restored: the consumer-driven contract pin.** Added, then dropped when the route ratchet fired — it is the one item with no observed instance and a dependency on a consumer publishing a contract. Dropping an unevidenced addition is the right displacement; shaving evidenced prose to fund it is not.

- The success test from v0.20.1, lost when `plan-format.md` became a field list in v0.21.0: *a reader who agrees with every recommendation approves from the summary alone.* Nineteen sections said what must be **present**; nothing said what **good** meant, so 6,735 words read as thoroughness. Not restored: *"under a minute"* and *"thirty seconds of their attention"* — `check-plan.py` already reports reading time, and a stopwatch is the wrong target for the agent's half of the file.

## 0.26.2 — 2026-08-03

### Fixed
- **The hold-out decline path gets back what made it independent.** The human recomputes each value by hand from the business requirement rather than reading the code that produced it — verifying by opening the implementation and agreeing inherits the misunderstanding the hold-out exists to break. Lost in `1d84b78`, a commit with no changelog entry.
- **The fallback is offered as the fallback, never as the equivalent.** A guard that quietly replaces the hold-out makes circularity worse while feeling like progress. Seven declines, zero hold-outs.
- **`declined by human` is a waiver, not a neutral outcome,** and `ctdd-review` reports a declined or `NOT RUN` hold-out as a finding on a high-risk or contract-touching change. It had become one of four enum values, indistinguishable in the packet from a decline on a rename.

### Added
- A guard covering each restored clause individually, all three confirmed to fail when their clause is deleted. None had ever been on the `must_survive` list, which is why a compression pass removed them while its changelog claimed every rule intact (finding #57).

## 0.26.1 — 2026-08-03

### Fixed
- **The outer tier is scoped, and relocation is not deletion.** Downward pressure alone was a ratchet: step 3 demands *every* boundary and *each* error path, dimension 3 hunts for *missing* assertions, and dimension 4 makes deleting one a spec amendment — so the matrix would be added below while the expensive tier stayed exhaustive forever. The outer boundary now keeps one representative case plus what is only reachable there; dimension 3 also flags a case asserted exhaustively at two boundaries at once; and dimension 4 exempts an assertion moved to a smaller boundary — **only** when the destination test is named and observed passing, since *"I moved it"* without a destination is a deletion.
- **Altitude pressure now runs in both directions.** The escalation rule only pointed up — a hard test moved to *"an existing higher public boundary"* — and the altitude criterion, *rewrite when a behavior-preserving refactor breaks it*, only detects a test that is too **low**. A test asserting a lexical form through SQL passes that check perfectly: it survives every refactor, costs a database wipe, and can afford three values where thirty are cheap. `ctdd-tests` carried no notion that one correct boundary can cost more than another — no mention of slow, expensive, or database anywhere in it. A new breakpoint row moves pure-transformation assertions down to the smallest boundary with a contract of its own, and explicitly keeps the outer test, which is the one that survives the work moving between components.

## 0.26.0 — 2026-08-03

### Fixed
- **`check-plan.py` rejects a plan with a section written twice.** It asked whether each heading was present at least once, so a plan rewritten 28 times with 16 silent-failing `sed` calls passed 19/19 with a spliced duplicate section in it. The categorical `Risk: … · contract: …` line is excluded from the count, since the `risk level` pattern matches it by design.
- **`check-plan.py` rejects a required hold-out that names no work.** A plan wrote `request: 2 sealed tests written and withheld by the human` — the unbounded phrasing plan-format rule 6 exists to replace — with no `options:` and no `recommended:`, and the human had to ask *"what is my task"*. Seven declines and one deferral, and the work had never once been named.

### Added
- **ADR markers are read by the workflow.** Step 2.1 reads every ADR named by an `ADR-NNNN` marker in the contracts and tests it already reads; step 2.3 scans the repository's ADR titles when the change adds contract surface, because new surface carries no markers.
- **ADR numbers of any width are seen.** The marker pattern required exactly four digits, so `ADR-001` and `ADR-12` matched nothing at all — no marker, no broken-marker warning, no output, and silence reads as *no decision applies*. Markers are now echoed exactly as written and matched by value, so `ADR-17` finds `0017-x.md` and `ADR-0017` finds `017-x.md`.
- **`planDir` makes the plan location a default instead of a rejection.** `check-plan.py` refused any `CTDD-Plan:` pointer not under `docs/plans/`, so a repository keeping plans elsewhere could not use the pointer at all. The configured value is validated as strictly as the pointer it gates — absolute paths, traversal and drive letters fall back to the default — because this runs in CI over untrusted MR descriptions.
- **`.ctdd.json` at the repository root stores settings that should outlive a shell** — `adrDir`, `testPatterns`, `contractPatterns`. An environment variable lives in one shell and is absent on a fresh clone, a teammate's machine and in CI, so a decision made once had to be remade every session. Environment still wins for a single deliberate run; a malformed or missing file is ignored rather than fatal, because it is read on every hook invocation.
- **One ADR directory, decided once and used everywhere.** `check-spec-surface.py --adr-dir` is the single resolution for reading *and* writing: `CTDD_ADR_DIR` when the human has set it, otherwise the one existing ADR directory, otherwise `docs/adr` for a repository that has none — and it stops rather than picking when several exist. Read and write previously disagreed: the writer scanned an empty `docs/adr/`, wrote `0001` beside an `adr/` already holding `0001`–`0014`, and the reader then found two ADRs numbered the same. A guard rejects any hardcoded ADR path in a skill or reference.
- **ADR directories are discovered, not assumed.** `docs/adr/` is where this plugin *writes* a new ADR; it is not where every repository *keeps* them. `adr/`, `doc/adr/` and `architecture/adrs/` all resolve now, `CTDD_ADR_DIR` covers layouts the `adr`/`adrs` convention misses, and a repository with no ADR directory is reported as unresolvable rather than as a broken marker — a fixed path list turns a correctly-marked test in a differently-organised repo into a false alarm. Plan-format rule 10 pins the tests that already assert a matched ADR's decision — a decision no test protects is one the change can reverse silently.
- **`check-plan.py` reports gate-reading cost** for plans over 1,500 words. Plans have run 5,432, 17,801, 31,448 and 57,321 characters; the last is ~31 minutes before a human can approve, and it accrued over 28 amendment rounds rather than being chosen. Reported, not enforced.

### Changed
- **Compaction reserve 1,000 → 500 characters.** This buffer is early warning, not protection: the survival probes slice the body at the 15,000-char proxy itself, so lowering it does not weaken them by one character. It shortens the runway before a probe would fail — and that failure is loud and names the rule that fell out. Measured: the last probe sits at 10,585, with 4,415 chars of slack to the proxy. Body headroom 60 → 560.
- **Route ratchet 38,200 → 40,000, and it now bounds one thing.** It had moved four times in two sessions because it was doing two jobs; it bounds **attention cost** — loaded once per change, then cached, never truncated. The body's compaction guard owns truncation and is unchanged, because the window it stands for has never been measured. 40,000 chars is ~10,000 tokens, 5th of Anthropic's 62 shipped skills by loaded prose.

### Validated
- The 0.25.0 review-dispatch fix held in real use: *"Per step 9.4 I'm not dispatching ctdd-review: a review this session commissions isn't independent."* The 0.24.1 stack-trace fix held too — no log filtering, and all three evidence lanes re-verified against the session's own artifacts.

## 0.25.0 — 2026-07-30

### Added
- **ADR markers: a comment naming a decision, in the code it governs.** `check-spec-surface.py` reports the ADRs the changed files name and flags any marker resolving to no ADR file; `spec-edit-guard.py` reminds on edit. The hook is the only component that fires when no skill triggered, which is where a decision was most likely to be contradicted unseen.
- The ADR verdict reports relevance only — *no marker does not prove no decision applies*. Marker matching sees only decisions someone annotated, and a guard holds that wording.

## 0.24.1 — 2026-07-30

### Fixed
- **`check-redstate.py` compares only the occurrences that carry a verdict.** It required every mention to agree, so a .NET stack trace repeating the test name broke red state on a genuinely failing test — a 0.24.0 regression, hit twice in one session.
- **Step 9.4 stops and hands the `ctdd-review` verdict to the human; the agent never loads it here and never dispatches it unasked.** It said "invoke", which two sessions read two ways — one loaded the skill in-context and reviewed its own diff. A subagent the writing session commissions and frames is not independent either.
- **The guardrails carry a `py -3` / full-path interpreter fallback.** `python3` on PATH is a dead stub on many Windows installs.

## 0.24.0 — 2026-07-27

### Added
- **Plan tiers: `small` 8 sections, `medium` 13, `large` 19.** Derived from the categorical line and the new-behavior heading, never declared, so `small` cannot be claimed over a contract delta. Real plans ran ~14 minutes to read at the gate against a 3-minute example.
- **A `Gate presentation` artifact puts eight plan sections on `stdout` in full.** Step 6.1 said "print the complete plan verbatim", unfollowable at 31,448 characters, so agents compressed and the hold-out was the first thing lost.
- **A `Decision prompt` artifact — 2–4 options, one recommended, free text accepted — required at steps 1.1, 6.3 and 9.1.** A selection is a message from the human; a harness accepting a plan is not.
- **A required hold-out names its 1–3 assertions and offers `write` / `decline` with a recommendation.** The ask was "write 1–3 sealed tests", declined six times.
- Guards for tier derivation, the restored discriminators, the re-enterable verification step, and every tier keeping its evidence sections.

### Fixed
- **A test name must agree across every occurrence before the checker verifies it.** It returned on the first line matching the direction asked, so a name failing in one project and passing in another satisfied either lane.
- **The compile-red row splits by cause:** production API absent → stub; the test does not compile for its own reasons → fix the test. One remedy covered both.
- **`Decisions confirmed in session` is a defined conditional section.** The rule said to record resolved BLOCKING answers without saying where, so plans invented a heading.
- **Five discriminators moved from `ctdd-review`'s do-not-load rationale into its body** — proportionality, ADR tradeoffs, test-and-code agreement, silent fixes, additive-versus-breaking.
- **`ctdd-review` step 5 is re-enterable.** It ran verification before steps 6 and 7 produce the candidates it verifies.
- P0–P3 and the three verdicts documented in `ctdd-in-depth.md`.

### Changed
- **Compaction reserve 1,500 → 1,000 characters.** The proxy assumes 3 chars/token, measured is 4.00, so the reserve was binding while the guidance had 1,600 tokens spare.
- **The hold-out is described as a declared intention with a working decline path,** not weakness #3's primary mitigation. Zero executions across six changes.
- **Route ratchet 37,500 → 38,200.** Raised for tiers, lowered when the lane-variants table came out, raised again for the gate presentation.

### Validated
- Clause 6.4 refused a harness plan approval. The self-review prohibition left the verdict outstanding. The full evidence cycle ran including `pinstate-after.log`. `worked-change.md` transferred near-verbatim into a different repository.

## 0.23.0 — 2026-07-26

### Added
- **Evidence states: seven, each with a required action.** Compile red, wrong red, premature green and weakened green had no rule at all.
- **Break points: five** — checker exit `2`, plan mode owning the write location, a difficult or duplicate planned test, unrelated verification failures, an unavailable hold-out runner.
- **Approval defined by exclusion.** Your own restatement, silence, a subagent verdict, a passing checker and harness acceptance of a plan-mode surface are not approval.
- **`references/worked-change.md`** — one complete change, steps 0–9, with verbatim checker output.
- **`references/execution.md`** — evidence-state and break-point lookups, packet assembly, standalone-ADR procedure.
- **A route-cost ratchet** over the body plus the three unconditionally loaded references.

### Changed
- **Triviality requires a diff that already exists.** "No diff exists" satisfied the checker condition, so any unwritten change could skip the plan.
- **Amendment order: stop → amend → re-check → return to step 6 → resume at the lowest invalidated step.** The old order re-checked against a plan the human had not seen.
- **Skip conditions key on content.** `Preservation pins: none` is a literal no compliant plan contains, so the skip never fired and correct pin-free changes failed the pin lane.
- **Required case coverage follows the evidence direction, not the case.** A preservation-only refactor could not satisfy a categorical `New-behavior` column.
- **Field rules 23 → 10, coverage table 16 rows → 7, skeleton 3,097 → 1,043 characters.** None of the 23 was mechanically enforced and three restated `ctdd-tests`' job; the example teaches the rest.
- **Steps 8 and 9 run the validator, tests and build once.** They ran twice.

### Fixed
- **Step 8 admits every applicable evidence lane.** Preservation-only refactors satisfied neither entry condition and had no route into implementation.
- **Step 8 replaces the compile-only stub.** It read as a ceiling on production code, forbidding the implementation it was meant to precede.
- **`check-plan.py` covers all 19 mandatory sections,** with a guard against drift. Seven became mandatory while `REQUIRED` stayed at twelve, so a plan omitting all seven exited `0`.
- **Every script reference is anchored to `${CLAUDE_PLUGIN_ROOT}` and displays its arguments.** Nine bare invocations across three skills; step 9's commands exited 1 and 2 exactly as shown.
- **The standalone-ADR lane loads `execution.md` directly.** Its procedure sat behind a step-7 loader that lane skips by definition.
- **`worked-change.md` is tracked, and relative reference paths are checked.** It shipped untracked and both existence guards passed vacuously after path normalization.
- **Hold-out outcomes are `passed`, `failed`, `declined by human`, or `NOT RUN — <reason>`.** An unavailable runner was recorded as a human decline.
- **`<name>.pinstate-after.log` declared.** The post-change pin run had no artifact, so only the baseline could be rechecked.
- **Resolved BLOCKING answers reach the plan, and a later edit re-runs the checker.** An approved plan could still be asking its question against a stale check.
- **`ctdd-review` runs only existing reproducers and shows `--expect-pass` with its names.** It was told to run a reproducer its own guardrail forbade authoring; the bare flag is a usage error.
- **The canonical example matches its own rules** — side-effect assertion present, no false `n/a`, every new-behavior test in a slice, no untested production file, no category the table does not define.
- Stale release metadata corrected; `.claude/settings.local.json` ignored without hiding `.claude/rules/`.

### Budget
- Body **11,124 → 14,891 → 12,914**; the margin guard reserves space instead of testing a boundary. Steps 7–9 stayed in the body — they now sit inside the surviving head, so moving them would trade guaranteed-present for conditionally-loaded. `adr-rules.md` and `colocated-notes.md` load only when their trigger fires.

### Not changed
- **Premature green still returns to step 6 in every case.** Splitting it installs a self-classification escape at the moment the agent has just been told to stop.
- **`worked-change.md` still loads unconditionally.** The proposed trigger asks the agent to assess its own confusion.

## 0.22.0 — 2026-07-25

### Fixed
- **The golden-example extractor matches language-tagged fences and keys on a test name.** 0.21.3 shipped red: the references rewrite changed `plan-format.md`'s fenced example and four tests raised. Both commits carried the same version number.
- **Seven passing guards restored,** including the 0.21.1 regression tests for fully-qualified .NET names and trailing-dot prefix rejection — the only two defects then found by running a real change. The fixes were untouched, so a live fix had lost its detector.
- **`ctdd-tests`' eval fixture matches its own description.** It asserted `should_trigger: true` for a phrase the description names as a reject; nothing runs the evals, so nothing caught it.
- **The ordered workflow names the lanes that write no test.** `Execute steps 1–8 in order` was unconditional while the description triggers on renaming, de-flaking and isolated review — tasks that reach step 3 with no case set to derive.
- **The pin-lane gloss no longer renders as a plan heading.** Both checkers still read it, so this was a wrong instruction rather than a broken gate: the guard asserted the phrase was present, not that it still played its role.
- **The jqwik warning is restored** on the bullet where the library is chosen. Finding #45 recorded removal *plus* the reason stated where a reader meets it; 0.21.2 kept the removal and dropped the reason.
- **`check-spec-surface.py` stops instead of falling back to a weaker pattern set** when `hooks/spec-edit-guard.py` is absent, and **`check-plan.py`'s triviality cross-check no longer runs against a degraded classifier.**
- **`check-redstate.py` and `gen-authz-matrix.py` exit non-zero on a missing argument,** and **`spec-edit-guard.py` fails closed on an unparsable pattern override** instead of crashing.

### Changed
- **`ctdd-tests` gives an executable action at each discipline breakpoint** instead of stopping on unclear intent, and treats invalid substitutes as evidence-direction aware — manual checks, coverage, inspection, tests-after, sunk effort, retained exploration.
- **The worked section teaches case derivation through a framework-neutral table.** Finding #53: a single xUnit sample had made it the effective default while the prose claimed neutrality. Syntax stays repository-owned; no per-framework references were added.

### Added
- **The compaction guard measures every skill.** Its probe list bound to `ctdd-change` alone, which is how `ctdd-tests` overflowed the same proxy by 1,085 characters unnoticed.
- Guards for the hardening pass, the workflow lanes, the preservation-pin role, repository-owned convention discovery, and rejection of xUnit-specific tokens.
- Suite **142 passing / 4 failing at HEAD → 161 passing**, with one existing skip.

## 0.21.1 — 2026-07-24

Two defects found by running a real change, not by review.

### Fixed
- **Fully-qualified test names matched nothing.** The identifier-boundary rule added in 0.19.0 treated a leading `.` as part of the name, so `Namespace.Class.Method` — exactly what `dotnet test --logger "console;verbosity=detailed"` prints — was never found. A dot before a name is a namespace separator; a dot after still rejects a prefix match.
- **Nothing said how to produce a log the checker can read.** Default `dotnet test` output names no individual test, so an evidence capture could contain only a summary and verify nothing. Step 7 now requires per-test output and names the flag for the common runners, and the checker diagnoses a summary-only log instead of merely reporting every name as missing.

### Added
- Regression tests for both boundary directions. Suite 140 → 142.

### Note
- The machine-readable test block in the backlog moved from filed to ready: on this change the agent had to amend its own approved plan so `--tests-from` could parse it. The plan was correct and readable; the parser was the limitation.

## 0.21.0 — 2026-07-21

`ctdd-change` rewritten as procedure. **6,537 → 2,757 tokens**, under the post-compaction limit for the first time since v0.14.0, with every rule intact.

### Changed
- **The skill is now a numbered procedure with an explicit output contract**, and the reasoning lives in `references/rationale.md`. A table names every artifact's exact path and required shape — plan, pointer, ADR, evidence logs, review packet, colocated note — which is checkable in a way prose was not. Guardrails are declared unordered rather than leaving order to be inferred.
- **Two rules became structural instead of stated.** Preserve-before-create is encoded in the step order rather than asserted, and `trivial` is a separate declared output rather than a risk level inside a plan, which is the distinction that previously needed a paragraph.
- The always-loaded description drops from 1,329 to 566 characters.
- **The worked bug-fix example is removed.** It was added because the bug-fix lane is the modal case, but duplicated examples had produced four competing heading vocabularies; one canonical example, guarded and still passing both checkers, has no drift surface. The rule that replaces it is more precise: a short **complete** plan whose `New-behavior tests` section names the regression test.

### Fixed
- **The structure guards were pinned to exact sentences and failed on a correct rewrite.** A check that fires on good work is worse than no check — it argues against improvement and teaches people to ignore verdicts. They now match the rules in their current wording.

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
