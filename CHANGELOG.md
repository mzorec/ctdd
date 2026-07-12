# Changelog

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
