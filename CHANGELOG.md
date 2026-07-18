# Changelog

## Unreleased

_Documentation and non-runtime changes land here and fold into the next runtime release. Version numbers move only on runtime changes (skills, scripts, hooks); every doc edit is already dated by the rationale's status pin._

- `ctdd-in-depth.md` status pin trimmed to what only it can say. The **"Shipped:" inventory is cut** — it restated the changelog cumulatively, the README already describes the layout, and unbuilt mechanisms are tagged inline as *(Proposed — not yet built.)*, so an untagged one is shipped by convention: three sources for one fact, and demonstrably the part that rots (it drifted across nine releases while the version number kept being bumped). **Kept:** the token-cost measurements (not "what changed" but "what this costs to run", backing the doc's attention-budget argument) and **"described in this document but not yet shipped"** — a claim about the *document's own prose* outrunning the runtime, which a changelog structurally cannot make, and the pin's real justification in a document about doc↔code drift.

- `ctdd-in-depth.md` synced after nine runtime releases (0.8.0–0.9.7), which had moved the runtime without touching the rationale. Four changes, all factual: **status pin re-measured** per its own rule (bodies ≈6.3k/2.6k/2.1k; `check-redstate.py` now 19 cases and carries `--expect-pass`; `check-plan.py` carries `--from-description`) — the version had been bumped while the contents went stale; **weakness #4's mitigations** gain the preservation-detector rule and the pin-then-convert procedure the pilot produced; the **mitigations table** row for #4 matches; and a one-line **pilot pointer in the status pin** — a pilot has run and its findings live in `docs/pilot-findings.md`. (A fuller pilot-results paragraph was drafted and cut: the rationale document argues the method, and a results summary is current-status content that belongs in the journal — keeping it in both places would mean maintaining the same claims twice, which is the drift this document is about. The status pin is where current-status content already lives, with its own "trust the repo if stale" disclaimer.) `ctdd-in-practice.md` deliberately untouched: it walks one change at concept level, and the new material is runtime detail it exists to stay clear of.

## 0.9.8 — 2026-07-18

Fixes a fail-silent defect in `check-redstate.py` that inverted its purpose (external code review, finding #22). Reproduced before fixing; both defects predate v0.9.7.

- **🔴 `--tests-from` silently dropped test names and still reported success.** The pin-section regex was `search()`ed against every line, so any prose mentioning "characterization tests" flipped the parser into skip mode and dropped every following bullet — while printing "all N new test(s) observed failing — red state verified" and exiting **0** for the subset it read. Two named tests that never ran, green CI. The fix: a section label must **start** the line's content (leading markdown stripped, matched at position 0), never merely appear in it — which preserves the skill's documented bullet-style pin marker that a headings-only fix would have broken. The success message now **names every test it checked**, so exit 0 can never again be silent about what it skipped.
- **🟠 UTF-8 on Windows.** `--help` crashed with `UnicodeEncodeError` on a cp1252 console (the docstring carries jest's `✕`), and piped logs were read in the locale encoding, so mojibake stripped the failure marker and a genuinely failing jest/vitest/mocha/TAP test reported as "passed before implementation" — the opposite verdict from the same log passed as a file. stdin/stdout/stderr are now reconfigured to UTF-8 with `errors="replace"`. Direction matters: this cried wolf rather than letting wolves through, and dotnet was unaffected (`Failed` is ASCII). Second Windows-only defect in the deterministic layer after v0.8.2's launcher issue.
- **`--expect-pass --tests-from` now extracts the pin section** rather than the new-behavior section, which is the only set it can meaningfully verify.
- **A mention without a verdict marker** is reported as an unreadable run, not as "the pin is wrong, not the code."
- **Doc↔code drift, same review:** README claimed six deterministic pieces and listed five — the missing one was `check-redstate.py`, added in v0.9.0 by bumping the count without extending the enumeration. Now listed, with an honest note that it is *not* in the CI recipe: a red-state log is a per-change artifact CI cannot generically locate, so red state is deterministic when run and reviewed at the gate, not pipeline-enforced like the surface checks. CLAUDE.md's stale "72 tests" corrected to 92 with a re-count reminder.
- **Filed not built:** `gen-authz-matrix.py` conjunctive-requirement gap (AND-ed scopes produce all-deny rows while `--check` reports the endpoint covered). Suite 87 → 92.

## 0.9.7 — 2026-07-18

Pin evidence becomes an artifact (pilot finding #21 — the filed `--expect-pass` trigger fired on the first behavior-preserving refactor after it was written).

- **`check-redstate.py --expect-pass`** verifies the mirror of red state: named **pin/characterization** tests observed *passing* in a captured run against the current implementation. Diagnostics are pin-specific — a pin that *fails* before the change means the pin is wrong, not the code ("or you will 'preserve' behavior that was never there"), and an unrun pin proves nothing about preservation. Aggregate summary lines are ignored, as in the red-state path.
- **Step 7 now requires `docs/plans/<name>.pinstate.log`** beside `.redstate.log`. Observed: a real refactor ran the pin-then-convert discipline *correctly* — pins green against the old implementation, converted, same assertions still green — but wrote no evidence file, so the preservation proof lived only in terminal scrollback, even though the plan had demanded capture twice. The discipline held; the evidence evaporated. Between the two logs a change now carries its own proof.
- **New-type red state in compiled languages.** A test naming a type that does not exist yet does not fail — it does not compile, and an uncompiled test is evidence of nothing. Step 7 now says to write the type as a stub so the test compiles and fails for the right reason, and to say so explicitly if the stub is skipped rather than reporting unobserved red state. v0.9.0 had assumed a dynamic-language failure mode.
- Backlog: the `--expect-pass` entry is removed — built, on its stated trigger. Suite 83 → 87.

## 0.9.6 — 2026-07-18

The authority chain is now consistent end to end: the skill writes the canonical plan, the MR points at it, `ctdd-review` reads it, and CI validates *that file* — not a pasted copy.

- **`check-plan.py --from-description`** resolves a `CTDD-Plan: docs/plans/<name>.md` pointer out of an MR description and validates the file it names. Fixes a real inconsistency: the CI recipe linted `$CI_MERGE_REQUEST_DESCRIPTION` while the runtime had made `docs/plans/<name>.md` authoritative — so CI could reject an MR that correctly pointed at a valid plan, bless a stale copy pasted into the description, or lint the brief design plan instead of the implementation plan, recreating exactly the two-plan drift v0.8.3 removed from the runtime.
- Pointer handling is **hardened and honest about its limits**: the path is untrusted CI input, so traversal, absolute paths and anything outside `docs/plans/*.md` are refused; a pointer to a file CI cannot see fails with the actual cause named — `docs/plans/` is probably git-ignored — and both remedies spelled out. With no pointer at all it falls back to validating the description (backward compatible) with a nudge toward the pointer. 6 regression tests; suite 77 → 83.
- **README recipe updated** to the pointer form, plus a note making the commit-vs-ignore trade concrete: committing `docs/plans/` is what lets CI validate the canonical plan; git-ignoring it means pasting the plan into the description and accepting that the copy can drift from what the reviewer reads.
- **Skill step 6** now emits the pointer line — and pays for the addition by dropping the commit-vs-ignore rationale that duplicated the README (the trim the v0.9.4 audit identified). Net shorter.

## 0.9.5 — 2026-07-18

External review of v0.9.3, verified claim-by-claim against the tree (finding #20). Six reconciliations, two backlog filings, one rejection.

- **Pin tests no longer fed to the red-state checker** (the review's best find; missed by the 0.9.4 audit). `check-redstate.py --tests-from` extracted every underscore-shaped bullet with no concept of a pin section — so step 7 recommended a command that contradicted the exemption stated two sentences later. Extraction now skips bullets under a preservation-pin heading and any `currently_`-prefixed name anywhere, and the plan format splits proposed tests under two headings (`New-behavior tests — must be observed failing` / `Preservation pins — must pass before and after`). 2 regression tests.
- **The compressed bug-fix lane is now distinct from the trivial lane.** The skill said the bug-fix gate "collapses to a sentence" while `check-plan.py` required nine sections, and its rejection message said "an edit to an existing test" even when the diff only *added* one. The skill now says a bug fix collapses to a *short plan* (sections present, most as one-liners); the script reports an added-test diff with its own message pointing at that lane. 2 test cases, including the ordinary add-a-regression-test case the suite never had.
- **`check-plan.py` now enforces the two decision-summary buckets** (`BLOCKING` / `Proceeding unless you object`) — the format called them mandatory, the checker never verified them.
- **Step 8 re-opens the gate.** "If a test is wrong, fix it as a spec change and say so" under-signalled against the amendment route: discovering a planned test/contract/assumption is wrong now *stops*, amends the plan, re-runs the checker, and gets approval before the spec artifact changes.
- **Hold-out outcomes are no longer equivalent:** `failed` blocks approval; `declined by human` is an explicit waiver reported as a deviation on a load-bearing change, never a neutral success.
- **Artifact-conflict rule qualified:** artifacts conflict only when they make incompatible claims about the *same observable constraint* — a schema owning payload shape while a test owns a state-dependent rule is not a contradiction, and a Pact narrowing a broader space is specialization.
- **Evals 24 → 28** on `ctdd-change`: negative fixtures for the over-broad review-comment trigger (CSS, README, Dockerfile) plus the backend-positive control. Suite 72 → 77.
- **Filed, not built:** exact-contract-delta-in-plan (trigger: an approved prose description diverging from the applied delta — not yet observed) and the hold-out waiver schema (trigger: the first real decline — zero so far).
- **Rejected:** the review's description/trigger prose edits. Description tightening is a recorded backlog item gated on eval-CI showing a specific trigger error; the review proposed doing it blind without engaging that recorded reason.

## 0.9.4 — 2026-07-18

Coherence audit (pilot finding #20) — first end-to-end read of all three skills since 0.8.0; reconcile-or-remove only, nothing added.

- **`ctdd-review` dimension 8 reconciled with the 0.9.3 pin exemption** — it still demanded a captured failing run "for every new test in the diff," which would flag legitimate pin/characterization tests as findings (#19's sibling, live on the reviewer's side). Now scoped to tests asserting *new* behavior, with the pin exemption stated: their evidence is green-then-still-green, and they are not fed to `check-redstate.py`.
- **`ctdd-change` step 7 reordered** — the 0.9.3 exemption had been inserted between the red-state rule and its capture instruction, leaving "capture that failing run" dangling after a paragraph about tests that pass. Order is now rule → capture → exemption.
- **Step 6 sentence fusion repaired** — the 0.8.3 filename-convention insertion had fused two sentences ("…orders the folder into a timeline and present a short pointer…"). Split.
- **Placeholder unified** — step 7's `<plan-name>` (3×) now matches step 6's defined `<name>`.
- **Condensed example reconciled to its own format** — it predated 0.8.0 and never gained the mandated decision-summary buckets; a reader copying it would omit the summary. BLOCKING / Proceeding lines added, drawn from the example's own assumptions and ambiguities.
- **Stale facts corrected:** README's redstate suite count 11 → 13; CLAUDE.md's test total 59 → **72** (10 check-plan + 13 check-redstate + 11 check-spec-surface + 12 gen-authz + 26 hook), "five" scripts → four, and `check-redstate.py` added to its layout list.
- **Status pin re-measured** — it had been re-versioned three times without re-measuring, violating its own rule. Now (≈4 chars/token): descriptions ≈1.0k tokens always-in-context (unchanged in practice — the frozen descriptions held); bodies ≈5.2k / 2.2k / 1.7k on trigger (previously pinned 3.9k / 2.2k / 1.6k — the earned fixes cost ≈1.6k tokens of trigger-time budget on `ctdd-change`, the honest price of 0.8.0–0.9.3); plan example ≈389 tokens; `check-redstate.py` added to the Shipped list.
- Reviewed and deliberately kept: the 0.9.2 guardrail / 0.9.3 exemption overlap (procedure-at-plan-time vs evidence-at-test-time — different jobs, both load-bearing). Reviewed and deferred, needs a pilot occurrence: the bug-fix section's regression test has no capture wording. `ctdd-tests` needed nothing.

## 0.9.4 — 2026-07-18

Coherence audit — first end-to-end read of the three skills as one instruction set since the pilot began (motivated by finding #19, a contradiction shipped between piecemeal releases). Mandate: reconcile or remove only, never add. Two runtime reconciliations, two doc syncs; everything else reported, not changed.

- **`ctdd-change`: the nothing-on-disk rule now names its own exception.** It read "nothing is written to disk until the plan is approved" while step 6 requires writing the plan file — and the ambiguity had an observed consequence: the Mapperly session deferred persisting the plan until after approval, exactly what the file-backed design exists to prevent. The rule now says *no work product* pre-approval, and the plan file is the gate's artifact, written before approval so the human reviews it in an editor.
- **`ctdd-review`: the gather step now names `docs/plans/` as the canonical plan location** — it predated the 0.8.x file convention and only mentioned PR descriptions, so a reviewer had no pointer to where plans actually live.
- **Status pin re-measured** per its own rule: bodies ≈5.5k / 2.6k / 2.0k (`ctdd-change`/`ctdd-tests`/`ctdd-review`; up ~34% total since the 0.6.1 measurement), descriptions ≈1.1k always-in-context. Manifest aligned with the pin (both 0.9.4).
- **`ctdd-in-practice` §2 synced** (the edit deferred since 0.8.1, due at the next substantive touch): one sentence noting the plan is a file reviewed in an editor, with a pointer + decision summary in chat.
- **Audit findings reported, deliberately not fixed:** (1) `gen-authz-matrix.py` is referenced by no skill — an orphaned deterministic tool, adjacent to finding #10's twice-observed authz-asserted-not-checked pattern; wiring it into the plan format would be an *addition*, offered as the next earned fix rather than smuggled into an audit. (2) A terminology seam: step 7 and review dimension 8 say "pin (characterization)" while `ctdd-tests` defines characterization narrowly as `currently_*`-marked possibly-wrong observations; plain preservation pins are intent tests written green-first and need no marker — the Mapperly agent navigated this correctly unprompted, so it is a watch item, not a defect. (3) Step 6 is the heaviest single block (~450 words); its commit-vs-ignore guidance duplicates the README — candidate trim, kept because the adjacent "plans are not maintained after ship" clause is load-bearing agent behavior. Verified consistent: red-state ↔ pin exemption across step 7 and dimension 8, the trivial-never rules, the hold-out lifecycle, both sides of back-translation, the Windows launcher notes, and the single-home characterization definition.

## 0.9.3 — 2026-07-18

- **Resolved a contradiction v0.9.2 introduced** (pilot finding #19, self-inflicted). v0.9.0 requires new tests to be observed *failing* before implementation; v0.9.2 requires pin tests to be written against the old implementation and observed *passing*. For the same tests, with no exemption stated — an agent hit the collision mid-change and resolved it by judgment. Step 7 now names the rule, and it turns on **what the test asserts**: a test asserting *new* behavior must be observed failing (red state, `check-redstate.py`); a **pin/characterization** test asserting *preserved* behavior must be observed passing against the current implementation and must still pass after the change — green-then-still-green is its evidence, and running it through `check-redstate.py` would report a false finding. A behavior-preserving refactor normally has both kinds.
- Backlog (Tier 2): filed `check-redstate.py --expect-pass`, the symmetric captured artifact for pin evidence — **not built**, gated on the pin discipline actually drifting. Red state earned enforcement by drifting four times; pin discipline has drifted zero.

## 0.9.2 — 2026-07-18

- **Thin-coverage guardrail now covers preservation claims** (pilot finding #18, predicted then confirmed). It previously fired only when a change proposed *altering* behavior in a thinly-covered area — so a behavior-*preserving* refactor slipped past, which is the more dangerous case because it comes with false confidence. Confirmed on a real plan: a mapping refactor asserted "the existing tests are the preservation guard" while naming no test that asserts the mapping, and deleted the hand-written implementation in the same change. The guardrail now: covers preservation claims explicitly; requires naming *which* tests assert the behavior being preserved ("if you cannot name them, the guard does not exist"); and gives the cheap procedure — write the new tests against the **old** implementation first, watch them pass, then convert, and the same tests must still pass. Same tests, other order, no extra cost. A widening of the existing bullet, not a new instruction.

## 0.9.1 — 2026-07-17

- `check-redstate.py`: added the `FAILURE` marker so **JUnit/Maven Surefire** output (`testName(Class)  Time elapsed: 0.01 sec  <<< FAILURE!`) is recognised — it was the one common runner the marker list missed. Added Go (`--- FAIL:`) and TAP (`not ok`) cases to the suite (13 cases; 72 total). Documented the actual coverage and the real limit in the tool: it is framework-agnostic, but the test name and the failure marker must appear on the **same line** — runners that split them across lines (RSpec) read as not-found, and the honest response there is explicit evidence or an explicit "couldn't capture," never a silent miss.

## 0.9.0 — 2026-07-17

Red-state moves from prompted to deterministic — the pilot's most-repeated finding, fixed.

- **New `scripts/check-redstate.py` (+ 11-case suite; 70 tests total).** Verifies that named new tests were *observed failing* in a captured run: it scans a test-run log and reports any named test that passed before implementation (a finding — either the behavior already existed and the plan missed it, or the test asserts nothing) or is absent (never run). Recognises the common runner markers (dotnet/xunit, pytest, jest, generic FAIL/ERROR), ignores aggregate summary lines, and reads names from `--test` or `--tests-from <plan>`. Honest ceiling documented in the tool: it proves *a* failing run mentioning the test, not that the failure was for the right reason — the assertion message is still the reviewer's read.
- **`ctdd-change` step 7 now captures the red run as an artifact** — `docs/plans/<plan>.redstate.log` beside the plan — and verifies it with the script. Rationale (pilot findings #12, four occurrences across three changes): "run the tests and watch them fail first" is prompted discipline, and prompted discipline drifted every single time under real work — twice disclosed, once silently. An artifact a reviewer can check replaces a promise nobody can audit. If capture is impossible, the skill requires saying so explicitly rather than implying verification happened.
- **`ctdd-review` gains dimension 8, red-state evidence**: a new test with no captured failing run is unvalidated as a detector; absent evidence is a finding, an explicit "could not capture, here's why" is acceptable, silent omission is not.
- **Plan re-tiering on scope change**: when a BLOCKING decision resolves into a different branch (type-only becoming a breaking rewire), the risk level and contract-changes sections must be restated to match the branch actually chosen — a plan whose top-line risk reflects the option you didn't take reads as safer than the work is.

- `pilot-findings.md`: Change 2 findings. **#14** — back-translation (shipped v0.6.0) caught a real spec *imprecision* on first use: the spec's "filtered to deposited status" was actually Subsequent-only, surfaced by reading the tests back as prose. **#15** — Option A (the seam fix) proved its own diagnosis: the two pre-existing 404 tests pass unchanged; one contract-observable consequence (NSwag folds the response description into ApiException.Message) to carry into Change 3. **#12 escalated to PRIORITY** — red-state violated a third time (Change 2 repeated implementation-before-tests); prompted-not-enforced has now drifted on every substantive change, making it the clearest candidate for moving a discipline from prompted to deterministic (a 'tests observed failing' artifact gate; needs hook/CI, not skill prose).

## 0.8.3 — 2026-07-13

Two plan-output fixes, both earned by the pilot — the confirmed plan-mode failure (#7) and the filename convention.

- **Plan-mode modal trap (finding #7, reproduced on v0.8.2).** v0.8.0/0.8.1 fixed plan *duplication* (the agent writes a pointer, not a second plan) but the modal trap remained: plan mode is a second surface the agent couldn't cleanly exit, and repeated declines kept it idle in a regeneration loop while the approve/decline meaning was ambiguous to the human. Fix: the skill now states the plan file is the authority, plan mode's exit presentation is a pointer + summary (never a regenerated plan), and the agent presents then immediately hands the exit decision over — approving = "implement from the plan file," the go-signal. README gains the human-side half: approving the plan-mode gate means implement; declining means the content is wrong; declining to mean "not yet" just keeps the agent idle.
- **Plan filename convention.** Plans now write to `docs/plans/<TICKET>-<kebab-slug>.md` (ticket when present) or `<YYYY-MM-DD>-<kebab-slug>.md` (else) — kebab-case, date/ticket-prefixed, so the folder sorts into a readable timeline. Replaces the bare `<ticket-or-slug>` that produced unreadable mashed-together names (`getdocumentattachmentlist.md`).

- Backlog (Tier 1): filed **`ctdd-retro`**, a structured end-of-change capture tool — the *witness-not-critic* version of "a diagnostic skill that finds CTDD improvements." Records factual trace + human journal answers into `docs/pilot-findings.md`; explicitly forbidden from proposing skill edits (an AI-judges-its-own-skills diagnostic is the circularity weakness pointed at the frozen prose). Gated on ~3–4 changes so its structure is derived from the journal's recurring questions, not guessed.

## 0.8.2 — 2026-07-13

Pilot finding #2 — the deterministic layer silently no-ops on Windows.

- **Windows Python portability.** On a real pilot run, `check-plan.py` reported `Python was not found` and the skill correctly fell back to manual — but that means the plugin's entire *deterministic* layer (the scripts, the one part that's more than prompting) doesn't run on a machine with only `python`/`py`, not `python3`. Fixes: a portability note in the README next to the enforcement section (if a `ctdd-*` script silently does nothing, check that `python3` resolves; scripts degrade safe but only *run* when a Py3 launcher is on PATH); the two skill invocations now show the `python`/`py` Windows alternative inline; and a new `hooks/hooks.windows.json.example` with the `py -3` launcher. The scripts are unchanged and cross-platform — only the launcher token differs. (A deeper fix — a launcher shim, or the skills detecting the interpreter — is filed for the pilot to justify if the note proves insufficient.)

- README: added a **`docs/plans/`** subsection under Quick start — what lands there, the commit-vs-git-ignore choice with each option's real tradeoff, the by-design fact that plans are unmaintained after ship, and a deliberately restrained note that post-merge value (reviewer context, decision archaeology) is a bonus of committing and an open pilot question, not a promise. Also fixed a duplicate `## Install` heading (the publishing edit had created a second one; retitled to *Install from this repo*).

## 0.8.1 — 2026-07-13

- **`ctdd-change` now always writes the plan to `docs/plans/<ticket>.md`** (not only when it's long). Rationale (maintainer's): the plan is the decision record for a change and deserves to exist as a file regardless of size; a chat window is a poor viewer either way, and always-file gives one predictable location. The trivial-change exception is explicit — a trivial skip produces no plan, so no file. The skill now also surfaces the source-control choice to the user rather than deciding it: `docs/plans/` committed = a PR-linked audit trail; git-ignored = scratch; the plan is unmaintained after ship either way. Supersedes v0.8.0's longer-than-a-screen threshold.

### Folded in from Unreleased (docs, no version of their own)
- Added `CLAUDE.md` for meta-work on the plugin repo itself (layout, the non-negotiable rules — tests-with-behavior, one spec-surface definition, frozen skill prose, grep-before-edit — versioning/release steps, and the pilot-first standing priority). Guidance for agents editing the plugin; not a runtime artifact.
- Rewrote `docs/backlog.md` for human readability: every entry now opens with **The problem** and **Why you'd want it** in plain language before the decision mechanics (trigger, cost, why-not-now). Same items and triggers; a reader can now see *why each idea would be good to have*, not only *when it may be built*.

## 0.8.0 — 2026-07-13

First runtime change driven by real use rather than review — the pilot's first finding.

- **`ctdd-change` plan output is now two-layer and file-backed.** Pilot finding #1: on a real load-bearing change (a document-attachment list endpoint authoring SQL views and drawing a schema-ownership line), the plan gate produced exactly the right content but was too dense to review in a terminal. Fixes: (1) step 6 writes any longer-than-a-screen plan to `docs/plans/<ticket>.md` for review in an editor, presenting a pointer + summary in chat instead of pasting the whole plan; (2) the plan format now leads with a **decision summary** in two buckets — *BLOCKING (I will not guess)* and *Proceeding unless you object* — so a reviewer who agrees with the recommendations can approve from the summary alone, with full detail as backup below. The dense plan wasn't the problem; the terminal was the wrong viewer. This also lays the canonical plan path that weakness #8 archiving and the deferred plan-frontmatter idea were both waiting on.
- Versioning policy change: documentation-only edits no longer bump the version — they collect under **Unreleased** and fold into the next runtime release. The status pin already dates every doc change.

## 0.7.6 — 2026-07-13

Docs only — backlog gains the `/code-review` composition question.

- `docs/backlog.md` Tier 4: filed the relationship between Claude Code's `/code-review` (multi-agent correctness reviewer) and `ctdd-review` (spec reviewer). They check different things — "is the code correct?" vs "do the changed tests/contract encode the right requirement?" — so the plan is to run both and narrow `ctdd-review` to its unique lane if the pilot shows redundant overlap, or keep it broad if it catches a changed-requirement `/code-review` waves through. Trigger: one diff seen by both reviewers. Notes the GitHub-only / Team-plan / ~$15–25-per-PR limits that make the managed product unavailable on self-hosted GitLab, and the independent-pass argument (LLM-as-Judge ~45% error detection; "fresh eyes is just another agent with the same blind spots").
- No runtime changes; skill prose remains frozen.

## 0.7.5 — 2026-07-13

Docs only — the deferred-ideas backlog, structured to resist premature building.

- New `docs/backlog.md` — a **decision record, not a to-do list**: every deferred idea filed with the specific real-use observation (its *trigger*) that would justify building it, plus honest costs and risks. Tiers: pilot-gated evidence work (Tier 1), the four proposed mechanisms already tagged in the rationale with their triggers (Tier 2), coherent-but-unproven integrations including the SDD-requirements-upstream idea with its hard disposability boundary (Tier 3), tool-absorption items gated on the eval harness (Tier 4), and the recorded rejections table with the condition that would reopen each. Closes with the entry test: an idea that can't name its own disconfirming evidence doesn't belong in the backlog.
- Rationale governs the backlog's Tier 2/3 by reference (the proposed markers and rejection reasons already live in `ctdd-in-depth.md` and the changelog history); the backlog collects them with triggers so nothing gets lost *and* nothing gets built from an armchair.
- Linked from the README doc map. No runtime changes; skill prose remains frozen.

## 0.7.4 — 2026-07-13

Publishing metadata — the plugin becomes installable.

- **MIT license** (`LICENSE`, © 2026 Marko Zorec) and `license` / `homepage` / `repository` fields in the manifest, pointing at `github.com/mzorec/ctdd`. Rationale: a license protects expression, not the method — anyone can reimplement CTDD from the rationale — so restricting it would cost adoption while protecting nothing that matters. The remaining risk in this project is "nobody has run it," and MIT is the license people install without reading.
- **`.claude-plugin/marketplace.json`** — makes the repo installable: `/plugin marketplace add mzorec/ctdd` then `/plugin install ctdd`.
- README gains an **Install** section, including the local-clone path and the standalone-skills fallback (copy `skills/*` into `.claude/skills/`), plus the Windows note (`python` / `py` where the docs say `python3`).
- `.gitattributes` pins LF line endings (Windows checkouts would otherwise CRLF the scripts) and `.gitignore` excludes `__pycache__` / `.pytest_cache`.
- No runtime changes; skill prose remains frozen.

## 0.7.3 — 2026-07-13

Docs only — the compounding claim, stated as mechanism and fenced against its own abuse.

- `ctdd-in-practice`: new **"What compounds"** section (before the one-rule section, which is its counterweight): bug fixes leave permanent regression tests, well-run changes add retrievable spec, contracts stay honest *where validation is wired*, and what survives a disposable plan lands in tests, contracts, and ADRs. The bet, stated narrowly: the **executable spec becomes richer** as a byproduct of the work instead of rotting as one — with the bidirectional counterweight attached (brittle tests compound into an increasingly precise description of yesterday's code, blocking the refactor they should protect; accumulation multiplies whatever discipline you have, it does not supply it) and an explicit disclaimer that CTDD does not make code cleaner by itself — that stays design skill, refactoring judgment, and review.
- `ctdd-in-depth`: the same claim filed in Part 2 **inside the failure-signals section, not the benefits** — a prediction, not an observation; checkable against the signals already listed (suite growth per incident, retrieval difficulty on mature services, covered-behavior regression rate — the last already tracked by churn-on-refactor, so an instrumented pilot tests the claim for free); and explicitly barred from ever answering a bad result, since "you didn't follow it enough" is the No True Scotsman move that excused every failed methodology in software.
- Maintainer's qualifiers adopted throughout ("improves" → "becomes richer"; "every change" → "every well-run change"; contract honesty conditioned on wired validation; ADRs restored alongside tests and contracts).
- No runtime changes; skill prose remains frozen.

## 0.7.2 — 2026-07-13

Docs only — the agent's-side framing added where first-timers actually need it (maintainer-directed placement).

- `ctdd-in-practice`: new **"Why this helps the agent"** section between the idea and the spec table — goal-only prompts force inference (the agent's weakest mode); the artifact set is better inputs; the workflow makes the agent show its work before code exists. Honors the displace-as-much-as-you-add rule: "here's my reading — correct me" relocated into the new section as its closer, and the key-move paragraph slimmed to its unique artifact-role mapping.
- `ctdd-in-depth`: one paragraph after the retrieval-evidence discussion — CTDD read from the agent's side is a requirements-context protocol, not extra process. Deliberately one paragraph; the doc already argues this formally.
- README deliberately untouched, per maintainer direction.
- No runtime changes; skill prose remains frozen.

## 0.7.1 — 2026-07-13

Docs only — the maintainer's editorial pass on `ctdd-in-practice.md` adopted as canonical, with two fixes.

- Adopted: a plain-English glossary (ADR, Pact, property test, regression contract); a **"Try it first"** section that turns the ending into a verifiable first experience — ask for a change in plain language and watch for the plan gate; a "two weaknesses you'll hit most often" prioritization (changed tests, thin coverage); the amendment promoted to its own section with the "just update the test to match" reflex called out as a quote; the daily rule of thumb synced with the in-depth wording; scannable subsection structure throughout (~2.0k → ~2.3k words — growth noted against the doc's stay-short defense; next edit should displace as much as it adds).
- Fixed in adoption: a duplicated floor sentence removed; the intro promise corrected from "the evidence behind it" to "the **reasoning** behind it" — by the in-depth doc's own grading, method-level evidence is still unattempted, and the on-ramp doesn't get to oversell it.
- No runtime changes; skill prose remains frozen.

## 0.7.0 — 2026-07-13

The boundary release — one argued freeze exception, then the runtime is frozen pending pilot data.

- **Red-state check** (the freeze exception, recorded in the design-decisions appendix): `ctdd-change` step 7 now requires running new tests *before* implementing and observing them fail — a test that has never failed is unvalidated as a detector, and a vacuously-passing wrong test is weakness #3 wearing a green checkmark. A new test that passes pre-implementation is a finding: the behavior already exists and the plan missed it, or the test asserts nothing. Credit where due: the underrated half of Superpowers' TDD "Iron Law."
- **Pressure-scenario eval cases** (+2 per skill → 24 / 24 / 21): urgency ("production is down, just update the test"), sunk cost ("I already wrote the fix"), borrowed authority ("the senior dev said sync the expected values"), and skip-review pressure must still trigger the protective skill. Methodology adopted from Superpowers' skill-testing-under-pressure. Honest scope: these are trigger-level cases; whether a skill *holds the wall* after firing needs the eval harness run — still backlog, still on the adopter's machine.
- **README: co-installing with Superpowers** — same bet, different altitude; the workflow-entry collision named (session-start bootstrap wins by first-mover; task-list plans specify execution for a subagent, CTDD plans specify intent for a human — `check-plan.py` correctly fails the former); a `CLAUDE.md` adjudication note gives `ctdd-change` the plan gate for backend changes, places brainstorming upstream and execution skills inside the implementation step.
- Pin re-measured per its own rule (the `ctdd-change` body grew by the two red-state sentences) and re-pinned at 0.7.0 with eval counts 24 / 24 / 21. **Runtime prose is now frozen**: the next skill change must be justified by pilot data, not review.

## 0.6.1 — 2026-07-13

Docs only — the cost/size findings filed where each can't rot.

- `ctdd-in-depth`: new **"What it costs to operate"** passage (Part 1, end of the second-payoff section) carrying the three durable claims: CTDD's overhead rides on retrieval any competent agentic workflow already pays; cost scales with the risk tier by design; and the honest operating risk is frequency, not per-change cost — gate decay under volume, with the reject/edit rate and annoyance journal named as the instruments. The design-decisions appendix gains the **skill-prose-freeze** rule (the budget is attention across rules, not word count; new guidance displaces, never accumulates).
- Status pin: **measured sizes at this version** (descriptions ≈1.0k tokens always in context; bodies ≈3.8k / 2.2k / 1.6k on trigger; plan ≈325; hook ≈28 per spec-surface edit) — version-bound numbers live only in the pin and are re-measured at every re-pin.
- `ctdd-in-practice`: one cost-shape sentence in the floor section, deliberately number-free per that doc's drift-slow discipline.
- No runtime changes; deliberately excluded: external-guidance comparisons, environment-dependent percentages, and any felt-cost verdict — that's the pilot's question.

## 0.6.0 — 2026-07-12

Weakness-closing release: the pre-pilot pair, plus the remaining proposals filed honestly.

- **New `scripts/gen-authz-matrix.py`** — derives the authorization matrix from the OpenAPI contract: every identity (anonymous / authenticated / one per scope and `x-roles` role) × every operation, expected `allow` / `deny-401` / `deny-403`, with the *why* per cell. Honors operation-over-global security, `security: []` as explicitly public, OR across requirement objects, AND within one, and scope subsets (partial-scope callers get their 403 rows). Deterministic output so the JSON diffs cleanly — a new endpoint appears in review as new rows — and `--check` turns "a new endpoint without a matrix row is uncovered authz" into a CI failure. `--csharp-scaffold` prints the one-time xUnit adapter (the JSON is the generated artifact; the adapter is copied once, so nothing exists in two places to drift). Honest ceiling stated in the tool and the rationale: it covers the authorization surface the contract *declares* — object-level rules stay with hand-written behavior tests. 12-case test suite; total 59 green.
- **Back-translation** for load-bearing diffs (`ctdd-change` step 9, `ctdd-review` circularity guardrail): the agent states, from the tests alone, the requirement they encode, and the human compares prose to prose — the wrong-encoding half of weakness #3 gains a second guard beside hold-outs. Survives the same-prior objection that killed second-opinion review: it reads *artifact → prose*, not *intent → artifact*.
- Rationale (Part 2) updated: back-translation marked as shipped; the generator news lives in the promoted authorization-matrix section under "Covering the gap" (the weakness-#7 bullet stays a pointer — one home per fact); four further mechanisms filed as **proposed — not yet built** (claim-provenance summaries for #1, machine-readable `CTDD-UNDEFINED` markers for #2, a Roslyn expected-value independence analyzer for #3, a coverage-report *reader* for #4 — explicitly distinguished from the coverage-quantifier killed earlier); Microsoft Coyote named as the concrete #6 escalation rung (production-proven in Azure; MSR "as-is" support model noted). Traceability rows #3/#7 and the status pin re-pinned.
- README: generator in the deterministic-pieces list (now five), repo layout, and a `--check` drift line in the CI recipe.

## 0.5.2 — 2026-07-12

- Docs only: new `docs/ctdd-in-practice.md` — a ten-minute first-timers' introduction (the concept, a worked change, the one rule, the honest floor and limits, four FAQ). Deliberately concept-level so it drifts slowly; runtime specifics stay in the README, the argument stays in the rationale — which is renamed `docs/ctdd-in-depth.md` in the same release, making the doc pair *in practice / in depth* (the prose keeps "rationale" as the genre word). Chosen over "primer" partly because *primer* means "example" in Slovenian — misleading for half the audience. Cross-linked from both. No runtime changes.

## 0.5.1 — 2026-07-12

Third review round, applied selectively — four accepted items, three recorded rejections.

- `check-plan.py --diff`: a declared trivial skip is now **mechanically contradicted** when the supplied `git diff --name-status -M` touches test or contract surface (classifier shared with `check-spec-surface.py` and the hook — one definition of spec surface, env overrides included). Bypass #3 (triviality gaming) goes from "review might notice" to "the linter says no." The linter finally has its own test suite (10 cases; total 47 green).
- Hold-out record gains an outcome: `result: pending` at plan time, updated at step 9 to `passed` / `failed` / `declined by human`; `ctdd-review` treats a `pending` result at review time as a finding. Closes "required" being a promise with no completion state.
- Existing-behavior section now states **known gaps** explicitly ("no Pact found for the checkout caller") — silence becomes a reviewable absence.
- README gains a **GitLab CI recipe**: surface inventory always printed (attention, not error), plan lint with `--diff` as the failing gate on the MR description, hold-outs executed from a separate repo/branch only after green — converting both scripts from "when run" to "always run."
- Recorded rejections, with reasons: Bash command-string scanning (re-proposed; still false-fires on every test *run* — documented in the hook section); in-repo `tests/HoldOut/` convention (a well-known path makes hold-outs *more* discoverable while labeling them sealed — the trait is CI's selector only); plan YAML frontmatter (plans live in PR descriptions; revisit when weakness #8 archiving gives them a canonical file path).

## 0.5.0 — 2026-07-12

Lane-ownership fix and the first deterministic diff-level check, from the second runtime review.

- **`ctdd-tests` routing rule** — the review's sharpest finding, applied with a triage framing instead of its proposed eval flip: the skill still *fires* on the ambiguous ask ("my refactor broke these tests", "fix this flaky test") because the alternative is no discipline in context at all — but it now triages before touching anything. Asserted behavior unchanged → stay (de-flaking, altitude, naming, mock weight, coverage). Expected outcome changes, an intent test is deleted, or the ask is "update tests to match" → stop and hand off to `ctdd-change` for the full amendment gate. Description narrowed to "de-flaking or improving brittle tests *without changing what they assert*"; the refactor eval case deliberately **stays positive**.
- **New `scripts/check-spec-surface.py`** — deterministic inventory of the spec surface a diff touches, classifying changed/deleted/renamed tests, contracts (Pact called out — cross-team blast radius), and ADRs from `git diff --name-status -M`. Imports the hook's pattern lists and honors the same `CTDD_TEST_PATTERNS`/`CTDD_CONTRACT_PATTERNS` overrides, so there is exactly one definition of "spec surface". Closes the hook's structural blind spots (Bash-lane edits, renames, deletions) at review time; a rename out of test surface is reported as "treat as a deletion until shown otherwise". Exit 1 = surface touched (attention, not error). Own 11-case test suite; total suites now 37 green.
- Wired in: `ctdd-review` runs the inventory as its mandatory first step; `ctdd-change` runs it before presenting the final diff (undeclared or "trivial"-declared surface ⇒ stop and reclassify) and names it as the deterministic counterweight to triviality calls; step 9 now also states when a recorded hold-out actually executes (after green, result part of the review).
- Trigger surface tuned from the review's misses: review-feedback and event-schema-rollout phrasings (`ctdd-change`); authorization-matrix and SLO-proposal phrasings (`ctdd-tests`); pre-PR sanity checks and partial diff review — "review just the changed tests and contract" (`ctdd-review`, with the tests-in-isolation exclusion clarified to *outside any diff*). Evals extended to 22/22/19 accordingly.

## 0.4.1 — 2026-07-12

- **Hook regression fixed:** the ambiguous-extension guard (added in 0.4.0 to stop `spec/payments.yaml` being mislabeled a test edit) was suppressing globally — fixture and golden data files under `tests?`/`__tests__` went silent, exactly the weakness-#3 "fixture setup" surface where a wrong encoding hides. Suppression is now scoped to outside test directories; `tests/fixtures/*.json` and friends fire again (Edit and Write-overwrite both). Both behaviors are now pinned: 4 new cases, suite at 26. Lesson owned: the 0.4.0 behavior change shipped unasserted — in a plugin about executable specs.
- `check-plan.py`: trivial-skip reason must sit on the risk line (`[^\n]{3,}`) — a bare `Risk: trivial —` followed by a newline no longer lets the next section masquerade as the reason.
- Naming: expansion respelled **"Contract- and Test-Driven Development"** (suspended hyphen — driven by contracts *and* tests, not by contract-tests); acronym unchanged. Rationale gains a Specmatic/CDD prior-art entry fencing the name-adjacent neighbor, plus a one-line disambiguation at first use.
- README: version note for the PreToolUse `additionalContext` dependency (older Claude Code builds may drop it).
- Packaging: `__pycache__`/`.pytest_cache` excluded from the distribution.

## 0.4.0 — 2026-07-12

Runtime hardening from the CTDD runtime review — closing the rationale↔runtime gaps it confirmed.

- `ctdd-change`: plan gate honestly scoped (catches wrong *direction* only; wrong encoding routes to the step-9 review and hold-outs); triviality skips are visible and vetoable, and an edit to an existing test or any contract file is never trivial; new **Amendments** (the everyday case) and **When artifacts disagree** subsections; mandatory plan lines for NFR budgets, the hold-out decision (required / requested / declined), old-vs-new assertions on changed tests, and evidence-cited retrieval; suggests plan mode on high-risk changes; new triggers for refactor/migration and rule/limit phrasings, new negative for infra/build config.
- `ctdd-tests`: contract-derived **authorization-matrix** property tests (a new endpoint without a matrix row is uncovered authz); SLO-check proposals scoped to existence and shape (load-test authoring is out of lane); "my refactor broke these tests" trigger.
- `ctdd-review`: dimension 8 — an implicated-but-unstated NFR budget is a finding, and a missing hold-out record on a high-risk diff is a finding; new `risk-misclassified` tag (including high-risk diffs with no plan at all); cross-artifact conflicts fold into `spec-change`; "look it over" trigger, negative for one-off migrations.
- Scope corrected across all three skills to **assertable correctness** — testable state logic qualifies wherever it lives.
- Hook: PreToolUse companion catches Write **overwrites** of existing test files (existence-checked; new files stay silent); honest docstring for the uncovered Bash lane; own test suite in `hooks/test_spec_edit_guard.py`; doc-file false positive (`LoadTest.md`) fixed via extension-limited pattern.
- New `scripts/check-plan.py`: an omission detector for the plan (presence, not quality); `ctdd-change` runs it when available.
- Trigger evals extended (21/19/17 cases): refactor- and ops-phrased positives, agent-output review, handoff ownership asserted on both sides, one Slovenian case per skill, and the Dockerfile / k6 / data-migration wrong-fire negatives.
- README: enforcement-honesty section (prompted vs deterministic vs blocking — plan mode is the only blocking gate, and the host provides it), hold-out "sealing is CI's job" section, hook limits stated plainly, hook added to the adoption ladder.

## 0.3.0 — 2026-07-10

- Spec-edit hook now ships **off by default** (`hooks/hooks.json.example`), so a company-wide install never interrupts anyone who hasn't opted in. Copy it to `hooks/hooks.json` and `/reload-plugins` to enable.

- New skill `ctdd-review`: the reviewer's side of the workflow — runs the PR checklist against a finished diff, treating changed tests as changed requirements and contract diffs as boundary changes.
- New spec-edit hook (`PostToolUse`): modifying an existing test file or any contract file injects a CTDD reminder mechanically — enforcement that doesn't depend on a skill staying in context. Patterns tunable via `CTDD_TEST_PATTERNS` / `CTDD_CONTRACT_PATTERNS`.
- `ctdd-tests`: characterization tests as a first-class concept — `currently_*`-marked observations, distinct from asserted intent, with an explicit promotion path.
- Trigger eval sets shipped in `evals/` for reproducible description tuning.
- README: requirements, adoption ladder, hook documentation.

## 0.2.0 — 2026-07-10

- `ctdd-change`: workflow reordered (read what exists before designing the contract change; nothing written to disk before plan approval), restored the closing human review of tests + contract as the spec, added bug-fix (regression-test-first) and standalone-ADR modes, embedded example plan, risk-level output, ADR template in `references/`.
- `ctdd-tests`: determinism and regression-test guidance, contract-alignment review check, property/mutation tooling pointers.
- Rationale moved into the plugin at `docs/rationale.md` with a table of contents, an appendix replacing the in-essay tooling section, and a weakness→enforcement traceability table.
- README rewritten as the operating manual (install, quick start, ownership table).

## 0.1.0

- Initial release: `ctdd-change`, `ctdd-tests`.
