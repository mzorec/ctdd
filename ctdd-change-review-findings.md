# `ctdd-change` review — 41 findings, prioritised

**Scope:** `skills/ctdd-change/` (SKILL.md + 7 references), plus the three scripts and one hook the skill invokes.
**Date:** 2026-08-20. **Repo state:** working tree at the time of review had uncommitted changes across skills/, scripts/, hooks/, docs/ (a step-renumbering + wording repair pass).
**Method:** 11 independent review angles + primary-source verification. Every item marked ✅ was reproduced by running code, not inferred from reading.

> **This file is untracked and not part of the plugin.** Delete it when the findings are dispositioned. Do not commit it — see repo rule 6 (this repo is public).

---

## Read this before acting

The reviewing session was explicitly told to ignore `CLAUDE.md` rules 3 and "The standing priority" so it could propose freely. **You have not been.** Before you change anything:

- **Rule 3 — skill prose changes need the human's approval. Stop and ask.** Most High items below touch `SKILL.md` or a reference. Say what each change displaces and what evidence demanded it, then wait. The bar is "a real-use finding demanded it".
- **Rule 1 — behavior changes ship with tests in the same commit.** Four of the High items are *script* fixes (`check-plan.py`, `check-spec-surface.py`, `check-redstate.py`, `hooks/spec-edit-guard.py`). Each needs cases in its `test_*.py`. Suite must stay green: `python -m pytest scripts/ hooks/ -q`.
- **Rule 8 — a guard can pass without guarding.** After writing any guard for these, delete the rule it covers and confirm the guard fails. H1 exists *because* an earlier guard didn't do this.
- **Rule 2 — one definition of spec surface.** H2 and H3 are both "two definitions disagreed". Fix them in the one place (`hooks/spec-edit-guard.py` holds the patterns; `check-spec-surface.py` imports them), never by forking a second copy.
- **Rule 10 — a repair pass is where the next defects come from.** H6, H7, H9, H10 were all *introduced or left* by the repair pass under review. Re-read after you repair.
- **Windows:** `python3` is a dead stub here. Use `python` or `py -3`.

**Suggested order:** the four script fixes first (H1–H3, H5) — they are mechanical, testable, and independent of rule 3. Then the prose contradictions (H4, H6–H15) as one approval conversation. Then Medium as a second.

---

## HIGH — 15 items
*Ships wrong behavior, blocks the workflow, or defeats a gate.*

### H1 ✅ `NO EVIDENCE LANE` guard bypassed by a `- none` bullet
`scripts/check-plan.py:232` (`_BULLET_NAME`, consumed by `_names_a_test`)

`_BULLET_NAME` reads a bullet reading `none` as a test identifier, so the guard passes the exact plan shape it exists to reject — and rejects the compliant form.

```
Preservation pins
- none — the touched area has no existing tests.
→ check-plan: all mandatory sections present for a small plan (10 of 19)   EXIT 0

Preservation pins: none — the touched area has no existing tests.     ← the form plan-format.md:11 rule 4 MANDATES
→ check-plan: NO EVIDENCE LANE                                            EXIT 1
```

The checker rewards the format violation and rejects the mandated form. The bullet-form plan passes 5.4, gets human approval at step 6, then dead-ends at step 7: either 7.4/7.8 skip both lanes so step 8's Enter can never be met, or `check-redstate.py` extracts `none` as a test name (`not found in the log (1): none`) and 7.7 routes to execution.md's "Pin fail — return to step 6" over a pin that does not exist. `check-plan.py:544-549`'s own comment says the guard exists for precisely this: *"step 8's Enter … can never be met, after a human has already approved."*

**Fix:** exclude a bare `none` bullet in `_names_a_test`. Add a case to `test_check_plan.py`. **Script-side; no prose change; no rule-3 approval needed.**

---

### H2 ✅ JSON Schema and `openapi/` directories are not contract surface
`hooks/spec-edit-guard.py:53-59` (`CONTRACT_DEFAULT`), surfaced at `skills/ctdd-change/SKILL.md:40`

`SKILL.md:40` names JSON Schema and OpenAPI as valid Contract change artifacts. The shared patterns anchor `openapi` to the **basename**, so a contract under an `openapi/` directory never qualifies.

```
classify("openapi/payments.yaml")        -> None      ← README.md:204's own CI recipe uses this layout
classify("schemas/payment.schema.json")  -> None
classify("events/PaymentCaptured.avsc")  -> None
classify("payments.openapi.yaml")        -> contract  (the only shape that works)
classify("contracts/payments.yaml")      -> contract
```

At step 3.3 a change whose only spec artifact is `openapi/payments.yaml` yields `Verdict: no test/contract/ADR surface touched.` EXIT 0 — the verbatim trivial-lane precondition — so **a real contract delta skips the plan gate entirely**. At 8.4/8.5 the packet's `Spec surface:` row records "no surface touched" on a change whose plan carries a Contract changes section. No ctdd-change file mentions the `CTDD_CONTRACT_PATTERNS` escape hatch.

**Fix:** add a directory-anchored OpenAPI/AsyncAPI pattern and `*.schema.json` to `CONTRACT_DEFAULT` (the single definition, rule 2). Consider `.avsc`. Tests in `test_check_spec_surface.py` + `test_spec_edit_guard.py`. **Script-side.**

---

### H3 ✅ The ADR you were told to write is not ADR surface
`skills/ctdd-change/references/adr-rules.md:8`; mechanism at `scripts/check-spec-surface.py:61` vs `:180-195`

Rule 4 resolves the ADR directory with `check-spec-surface.py --adr-dir`, which **honours** `CTDD_ADR_DIR` / `.ctdd.json adrDir`. The same script's `classify()` **hardcodes** `adr/`|`adrs/`.

```
CTDD_ADR_DIR=docs/decisions python scripts/check-spec-surface.py --adr-dir
→ docs/decisions                                                        EXIT 0

printf 'A\tdocs/decisions/0016-new-decision.md\nM\tsrc/S.cs\n' | ... check-spec-surface.py -
→ Other files touched: 2
→ Verdict: no test/contract/ADR surface touched.                        EXIT 0
```

One script, two disagreeing definitions of where ADRs live (rule 2). On an override repo, a change whose only spec artifact is the approved ADR satisfies step 3.3's trivial-lane precondition verbatim; at 8.5 the inventory omits the ADR the plan named.

**Fix:** have `classify()` consult the resolved ADR directory rather than a hardcoded pattern. **Script-side.**

*Verified NOT a defect:* variable-width filenames classify fine (`docs/adr/015-x.md -> adr`, `docs/adr/0015-x.md -> adr`), so `adr-rules.md:5`'s new width guidance is safe. See L1 for the prose-only residue.

---

### H4 ✅ small-tier rule omits the named-test requirement
`skills/ctdd-change/references/plan-format.md:57`

The stated recipe lists four conditions for `small`. `check-plan.py:550` additionally requires that *some* lane name a test, and rejects before `plan_tier()` ever runs.

```
Risk: normal · contract: none · ADR: none · hold-out: not required
New-behavior tests: none — behavior is unchanged.
+ one named pin                       → small plan (10 of 19)   EXIT 0
Preservation pins: none — nothing to pin, the area is untested.
                                      → NO EVIDENCE LANE        EXIT 1
```

The second plan satisfies **every one** of line 57's four stated conditions. The trigger is ordinary: a behavior-preserving refactor in an untested area is plan-gated by 3.5, has nothing to pin, and adds no new behavior — exactly the plan line 57 describes. `SKILL.md:76` then says *"fix every reported failure, and re-run until it exits 0"* against a failure that names no section, so **the loop cannot converge**.

**Aggravating:** the correct statement was added *in this diff* to `references/rationale.md:79` — the one file `SKILL.md:12` says **"Never load … during a change"** — while the wrong copy was left in the file step 5.1 actually loads.

**Fix:** correct `plan-format.md:57` to state the named-test requirement, or (better, rule 4) delete the prose derivation and point at the checker, which names its tier on every run. Note `rationale.md:79`'s "derives large" is technically true of `plan_tier()` but never observable — `main()` rejects first.

---

### H5 ✅ `check-redstate` accepts fixture ERRORs as intended red
`skills/ctdd-change/SKILL.md:94` (step 7.10); mechanism at `scripts/check-redstate.py:101` (`FAIL_MARKERS`), `:156` (`looks_like_failure`)

A plan naming two new tests + a pytest log in which both tests only **ERRORed in fixture setup** (`ERROR tests/test_capture.py::test_… - KeyError: 'DATABASE_URL'`):

```
→ check-redstate: all 2 new test(s) observed failing — red state verified.   EXIT 0
```

No assertion ever executed. `execution.md:15` states *"Wrong red: the failure comes from setup, environment, a typo, or an unrelated defect … A wrong red never unlocks step 8"*, and `SKILL.md:95` says *"Stop on any state other than intended red"* — but the agent holds the exit-0 verdict 7.10 asked for and proceeds. The script's docstring admits this ceiling; `SKILL.md:94`'s "Verify red state with" does not, and the packet reports the verdict line as evidence.

**Fix — two options.** Cheapest: prose at 7.10 stating the checker proves *a named test appeared with a failure marker*, not that the failure was the planned one. Stronger: teach `check-redstate.py` to bucket setup/collection errors separately (mirrors the pin lane, which already has the extra bucket — see H11).

---

### H6 ✅ "re-run `check-plan.py` to exit 0" produces exit 1
`skills/ctdd-change/references/worked-change.md:65`

The worked run tells the agent to move the answered BLOCKING question into `Decisions confirmed in session`, remove the question, and re-run "to exit 0". Applied literally to the canonical example:

```
→ check-plan: MISSING sections for a large plan — decision summary: BLOCKING
→ A plan that omits a section hasn't decided it; it has skipped it.          EXIT 1
```

`decision summary: BLOCKING` is REQUIRED at every tier (`check-plan.py:60`). Step 5.4's "re-run until it exits 0" loops against an instruction the worked example promised would clear it. The missing half — write `BLOCKING — I will not guess: none — <reason>` on the heading line — lives only in `plan-format.md` rule 4 and in `--post-approval`'s error text, not in the run the agent is told to copy.

**Compounding:** the bare re-run this line names cannot detect whether the move happened at all. `--post-approval` is the only check (`UNANSWERED BLOCKING AT APPROVAL`, `check-plan.py:565-577`) and appears in no skill file — see M1.

**Fix:** correct the instruction to the heading-line form, and render the post-answer state somewhere (see L8).

---

### H7 ✅ Worked transcript drops the plan-revision digest line
`skills/ctdd-change/references/worked-change.md:44` (propagates to `:62`, `:123`)

The step-5 transcript shows one output line. The script prints two:

```
check-plan: plan revision 76f952277e26 — carry it in the Approval record and the packet as `plan: <path>@76f952277e26`.
check-plan: all mandatory sections present for a large plan (19 of 19; …)      ← only this one is quoted
```

The omitted line is **the only place in the entire skill** that tells the workflow to carry the digest. Step 4.1 says "copy its artifact shapes" from this file, so the digest never reaches the two places `SKILL.md:38` now requires it: the Approval record at `:62` (`plan: docs/plans/PAY-123-partial-capture.md.` — no digest) and the packet's `Plan:` field at `:123`.

Verified downstream: `check-plan.py <plan> --approval <record>` on `:62`'s exact text →
`the approval record names no plan revision. Expected \`plan: <path>@453959650ce8\`.` EXIT 1.

So the `APPROVAL STALE` guard (`check-plan.py:601-607`) — shipped because 8.6 amends the plan in place at the same path — **can never fire**: a pre-amendment approval stays textually identical to a current one.

**Fix:** quote both lines at `:44`; add `@<digest>` at `:62` and `:123`; add the digest slot to `execution.md:43`'s packet shape.

---

### H8 Step 8's Enter is met vacuously; the red lane is skipped entirely
`skills/ctdd-change/SKILL.md:96`

Step 4.5 says *"Route a changed existing assertion as an amendment carrying its old and new form"*, and `plan-format.md` rule 3 gives it its own section — so a 400→422 status change goes there rather than under `New-behavior tests`.

```
Risk: normal · contract: none · ADR: none · hold-out: not required
New-behavior tests: none — the change is expressed by retargeting the existing assertion below
Changed existing assertions   (old: 400 / new: 422)
Preservation pins             (one named)
→ all mandatory sections present for a small plan (10 of 19)   EXIT 0
```

Step 7: 7.4 doesn't fire (a pin exists), 7.8 fires, 7.9–7.11 skipped. Step 8's Enter clause *"intended red for every new-behavior test the plan names"* is **vacuously true**, and *"at least one lane named a test"* is met by the pin. The contractual status code changes with **no run ever observing it red**.

Two compounding facts: `Changed existing assertions` is in **no** REQUIRED pattern in `check-plan.py`, so nothing verifies it; and 7.5/7.9 are the only `ctdd-tests` invocation points and both are lane-gated, so the approved section **has no producing step**. `plan-format.md:59` states the invariant this breaks: *"Tiers shrink documentation, never evidence."*

**Fix:** step 8's Enter must require intended red for any plan carrying `Changed existing assertions`, or `Changed existing assertions` must route into the new-behavior lane. See also M4.

---

### H9 Colocated note: "path listed in the plan" vs "no plan section names one"
`skills/ctdd-change/SKILL.md:44` ⟷ `references/colocated-notes.md:9`

The Output contract fixes the path to one *"listed in the plan"*. `colocated-notes.md` rule 2 — **rewritten in this diff** — says no plan section names one. `colocated-notes.md` is factually right: `plan-format.md:14-43`'s section list has no colocated-note section. SKILL.md is always loaded; the reference loads at 10.2, so the agent holds both.

Its remedy is also unreachable: *"report the write in the packet"* — but 9.3 already assembled and printed the packet, `execution.md:43`'s field list has no colocated-note slot, and `SKILL.md:43` binds the packet to *"the exact field list in references/execution.md"*, so adding one breaks the contract. The `Spec surface:` row was captured before the note existed, and the note's path is by construction absent from `Files likely to change`.

Net: a post-approval edit to a source or contract file lands **after every check that would have surfaced it** and reaches `ctdd-review` as an unexplained comment.

**Fix needs three touches:** the Output contract row, a `Colocated note:` field in `execution.md:43`, and a step 10.3 re-running `check-spec-surface.py --git <diff-base> --plan <plan-path>` (reuses M2's flag — the note lands under `Unplanned surface` by construction, which is exactly the deterministic report rule 2 asks for in prose).

---

### H10 Stale skip range `7.5–7.8` swallows the other lane's skip
`skills/ctdd-change/SKILL.md:88`

7.4 reads *"Skip 7.5–7.8 when the plan's `Preservation pins` names no test"*; 7.8 reads *"Skip 7.9–7.11 when the plan's `New-behavior tests` names no test."* With no pins the agent skips 7.5–7.8 and lands on 7.9 — **the decision that would have governed that lane was inside the skipped range.** The range should read **7.5–7.7**.

The diff shows two of three copies corrected and this one not:
`Stop: 7.2, 7.8, 7.12` → `Stop: 7.2, 7.7, 7.11` ✓ · `Skip 7.10–7.12` → `Skip 7.9–7.11` ✓ · line 88 untouched ✗

Presently masked only by the `NO EVIDENCE LANE` rejection guaranteeing one lane names a test — **and that mask is defeated by H1**, at which point this becomes a live post-approval dead end. (Rule 10.)

---

### H11 ✅ No evidence row for an unreadable new-test run
`skills/ctdd-change/references/execution.md:16`

One summary-only log, two lanes, two different diagnoses:

```
red lane: RED STATE NOT VERIFIED. / passed before implementation (2): …
          "A new test that passes before the implementation exists is a finding."      EXIT 1
pin lane: PIN BASELINE NOT VERIFIED. / mentioned without a pass/fail marker (2): …
          "this is an unreadable run, not a failing pin. Check the runner's output
           format rather than the test."  + names --logger "console;verbosity=detailed" / -v   EXIT 1
```

`observed_failing()` (`check-redstate.py:264-270`) returns seen-but-not-failed when no line carries a verdict, so the red lane has three buckets where the pin lane has four. A default-verbosity `dotnet test` capture therefore makes the agent classify **premature green**, follow `execution.md:16` ("Stop … return to step 6"), and **re-plan an already-approved change** — when the actual fix is a runner verbosity flag the same script already prints in the other lane. `SKILL.md:113` asserts the file *"carries the required action for every state and break point"*; this state has no row.

**Fix:** give the red lane the fourth bucket (script), and add the row (prose).

---

### H12 7.2 is a Stop with no resumption; 8.6 leaves artifacts under a voided approval
`skills/ctdd-change/SKILL.md:84`

The step 7 header declares `Stop: 7.2, 7.7, 7.11`, but only 7.7 and 7.11 have rows in `execution.md`. Its Evidence-states table has eight rows, all about test runs; its Break-points table has four, none about 7.2.

Reachable path: a large plan is approved; 7.3 writes the contract delta and an ADR; both logs captured. At 8.6 the approved spec turns out wrong (`worked-change.md:114-116` documents exactly this run). 8.6 amends and returns to step 6. `SKILL.md:46` now applies again — *"Until an Approval record exists for the current plan revision, the only file you write is the step 5 plan file; an amendment voids the previous one."* The contract and ADR are on disk under a **voided** approval. Nothing un-writes them; 8.6 lists no revert; and the freeze forbids the *corrective* write rather than the original one.

On resume, 7.1 re-checks the tree and 7.2 fires if the amendment dropped the ADR — with no action anywhere. If the amended plan still lists the path, 8.5 passes and the stale artifact **ships silently**: the packet reports `Approval:` for the current revision with no field recording that an artifact was produced under a superseded one.

---

### H13 Hold-out `NOT RUN` is a de facto defer the agent picks unilaterally
`skills/ctdd-change/SKILL.md:104` (step 9.1)

This diff removed `defer` from the offered options (`write / decline / defer` → `write / decline`) but left `NOT RUN — <reason>` as a resolution the agent reaches by its own judgement of runner availability, that no rule requires it to ask before choosing, that only `failed` blocks against, and that no script reads (`check-plan.py` never inspects the hold-out `result:` field).

The canonical example **establishes in-session unavailability by construction**: `plan-format.md:171-172` reads `storage: separate repository, unavailable to this session` and `runner: CI hold-out job, once the visible suite is green`. So NOT RUN is the default shape of every hold-out written from it — and it is the path taken *instead of asking*, since asking is what costs the turn.

Ships: a money-path change whose packet reads `Hold-out: NOT RUN — sealed suite runs in CI post-merge`, `check-plan.py` exit 0, **no `declined by human` waiver** for review to report (`plan-format.md:71` calls that a waiver "and expect the review to report it"), no human-verified expected-values fallback under rule 8, and a human never asked for the two assertions rule 6 calls a five-minute task.

**Fix:** dropping the label did not remove the mechanism. Either make NOT RUN require the write/decline prompt to have been asked first, or have `check-plan.py` read the `result:` field.

---

### H14 An 8.6 amendment can be re-approved by the original message
`skills/ctdd-change/references/worked-change.md:65` (second clause)

*"The same message approves because no other presented decision changed; otherwise re-present the amended plan."*

An amendment that changes a **test expectation** touches no section that `plan-format.md:53`'s closed enumeration requires the summary to name — `Changed existing assertions` is not on that list. So the decision summary, the categorical `Risk:` line and the `Hold-out` block are byte-identical to what the human already read, and this sentence completes step 6 again **with no new human message at all**.

Confirmed: `Changed existing assertions` is absent from `check-plan.py`'s REQUIRED list, so the re-run exits 0. And `execution.md:37`'s packet re-run of `check-redstate <red-log> --tests-from <plan-path>` still exits 0, because the pre-amendment log names the same test — **the checker actively re-certifies stale evidence against the amended plan.**

The boundary between "the spec was wrong" (8.6) and "the test was inconvenient" (8.2's prohibition) is decided entirely by the agent's narration, and `execution.md:19` routes `Weakened green` into this same 8.6 procedure.

---

### H15 Trivial lane's coverage claim leaves no artifact
`skills/ctdd-change/SKILL.md:63` (step 3.5)

3.5 — *"Require named existing tests that already cover every touched behavior, and no colocated note."* — is a precondition for skipping the human gate entirely, yet the only artifact 3.6 requires is `Risk: trivial — <reason>. Skipping the plan gate.`, which **carries no test names**. `check-plan.py`'s own trivial-lane output says: *"NOT checked: 3.4's behavior-preserving requirement. This reads paths, not hunks, so a changed limit or validation rule inside one production file looks identical to a mechanical rename."*

Worked example: a "mechanical extraction" moves an inline amount check into a shared validator whose boundary is `>=` where the inline check was `>`. 3.3 exits 0, 3.5 is satisfied by tests the agent named **only to itself**, 3.6 skips the gate. 8.3's suite passes because those tests never covered the edge, so 3.7 never fires. An off-by-one at a validation boundary merges with no plan, no approval, no pin, no red state, and **no named tests in any record**.

Aggravating: 3.2 requires only *"a diff that already exists"* and never says who authored it — an agent that explored and patched in an earlier turn arrives at step 3 having **manufactured its own precondition** (step 0.4 calls only *unrelated* target-file edits contamination).

**Fix:** require the trivial declaration to name the covering tests, so 3.5's claim leaves an auditable trace.

---

## MEDIUM — 18 items
*Enforcement gaps, unwired capability, and contradictions that mislead without directly shipping wrong behavior.*

### M1 Approval record is stdout-only; `--approval` / `--post-approval` are dead code
`skills/ctdd-change/SKILL.md:38`

Verified by grep: both flags appear **nowhere** in `skills/`, `README.md`, or `docs/`. Every invocation the workflow specifies is bare (`SKILL.md:76`, `SKILL.md:102`, `execution.md:36`).

- A session dying between step 6 and step 8 has **no durable artifact** that 6.4 was satisfied — and 6.4 rules out by name every substitute the agent has.
- `--post-approval` is the only enforcement of `plan-format.md` field rule 11. On the canonical example (BLOCKING open): bare run EXIT 0; `--post-approval` → `UNANSWERED BLOCKING AT APPROVAL` EXIT 1. So "Approved." over an open BLOCKING question passes today.

**Proposed:** add `${CLAUDE_PROJECT_DIR}/docs/plans/<name>.approval.md` to the Output contract beside the existing evidence-log paths; wire `--post-approval` at 6.3 and `--approval` at 7.1 and after 8.6 re-approval. Zero new script, both flags already unit-tested.

### M2 8.5 compares by hand; `--plan` does it and covers the deficit direction
`skills/ctdd-change/SKILL.md:101` (and `execution.md:39`)

8.6 stops only *"when 8.5 exceeds the plan"*, so the **deficit** direction is unhandled: a plan naming a contract file whose contract is never edited leaves the inventory a strict subset, no stop fires, and an approved contract change **simply does not ship**. `check-spec-surface.py:458-475`'s own comment spells out this scenario and prints *"An approved change that never reaches its file does not ship."*

Verified: `--git HEAD` alone printed only the changed test; `--git HEAD --plan <plan>` printed `Planned but untouched:` listing both missing paths. Report-only, so no exit-code semantics move. **Rule 4, zero new script.**

### M3 A declared ADR is verified by nothing
`skills/ctdd-change/references/plan-format.md:16`

`check-plan.py:645` validates only `for field in ("contract", "hold-out")`, so `ADR: NNNN required` on the mandatory categorical line is **parsed by nothing**, and no step verifies the declared ADR was written into the resolved directory. Step 4.3 fires, the human approves partly *because* the decision will be recorded, and 7.3 is simply not executed — or the file restarts a numbering series (which `adr-rules.md:8` warns about but nothing checks).

**Proposed:** extend `check-plan.py`'s existing `--diff` path (already calls `_load_surface()` / `classify()`), failing when the categorical line matches `ADR:\s*(\d+)\s*required` and no diff entry classifies as `adr`; add `ADR` to the categorical-field loop in the same change.

### M4 No check that a rewritten assertion reaches the plan
`skills/ctdd-change/references/plan-format.md:67` (field rule 3)

`Changed existing assertions` is not in REQUIRED, and no script reads diff **hunks** — so an assertion silently rewritten inside an existing test file is invisible to every mechanism. This is the exact defect `ctdd-review` exists to catch, and the change workflow cannot detect it. `SKILL.md:99` step 8.2 ("Do not weaken, delete, skip, or retarget an assertion to obtain green") is pure prose. Feeds H8 and H14.

**Proposed:** `check-spec-surface.py --git <diff-base> --hunks` running `git diff -U0`, reporting non-whitespace non-comment **deleted** lines inside test-classified paths; `check-plan.py <plan> --hunks <file>` failing when such deletions exist and the plan has no `Changed existing assertions`. Deleted lines are the discriminator — adding a test produces only `+` lines, which is why a `--name-status` check would false-positive on nearly every change. Ship report-only, as `--plan` already is.

### M5 The Verification lane has no artifact while the other two do
`skills/ctdd-change/SKILL.md:99` (step 8.3)

Red state and pins have `.redstate.log` / `.pinstate.log` / `.pinstate-after.log` in the Output contract, each verified by `check-redstate.py`. The `Verification:` packet row — contract validator, focused tests, broader suite, build — has **no declared output path**, so *"never reuse an earlier turn's output"* is pure recollection. An agent that ran `dotnet build` twenty turns and one amendment ago writes `Verification: dotnet build => exit 0` and nothing can distinguish that from a current-turn run. The plan's own `Verification` section already names the exact commands, so claim and evidence are fully machine-comparable and simply never compared.

**Proposed:** `<name>.verify.log` in the Output contract + `check-redstate.py <verify-log> --commands-from <plan-path>` (sibling of `--tests-from`, reuses the same "scan a log for named strings" machinery). Optional `--require-newer <path>` for the ordering claim.

### M6 3.7's retraction is unexecutable, and its trigger is nearly unreachable
`skills/ctdd-change/SKILL.md:65`

*"Retract the declaration from stdout and the PR/MR description"* — stdout cannot be unprinted, so the retraction is additive; the original `Risk: trivial` line stays verbatim in the transcript any reviewer scrolls. No procedure for a PR already open, approved, or merged; no instruction to notify anyone who acted on it. And *"return to 3.1 as plan-gated"* produces a plan and a gate presentation for code already on the target branch.

The trigger names only 3.4 and 3.5, omitting 3.2 and 3.3, and 8.6 is `n/a` in this lane. Its one determinate in-lane instantiation — a step 10 note contradicting 3.5's "no colocated note" — arrives **after 9.4 already handed over the diff**. Note also that 3.5 asks step 3 to predict step 10's outcome.

### M7 9.4 permits the review it calls non-independent
`skills/ctdd-change/SKILL.md:107`

*"Never load `ctdd-review` here, and never dispatch it yourself unless asked — a review this session commissions and frames is not independent, whichever context runs it."* One sentence forbids and permits the same act: "unless asked" is operative, the independence clause is rationale. An opening "CTDD this and review it when you're done" reads as being asked. The packet shape has no field for a review verdict and no provenance marker, so a self-commissioned verdict lands in the PR unqualified.

### M8 Trivial lane: 9.1 stops for a hold-out with no plan to supply inputs
`skills/ctdd-change/references/execution.md:38` (and `SKILL.md:104`)

Step 9 declares `Stop: 9.1` unconditionally. In the trivial lane there is no plan, hence no categorical `hold-out:` field, no `Hold-out` block, no `runner:` line — the inputs 9.1 names do not exist, and nothing waives it (contrast 8.5, which explicitly says "take 8.3's pin re-run and 8.6 as `n/a`"). Worse, `Red state:`, `Pin state before:` and `Pin state after:` offer exactly one alternative each — `n/a — plan declares none` — and no plan exists to declare anything, so **the packet's only conformant rendering is a false statement**.

### M9 The trivial declaration and the pasted plan share one channel
`skills/ctdd-change/SKILL.md:77` (step 5.5)

Where `docs/plans/` is git-ignored, 3.6 writes `Risk: trivial` to the PR/MR description and 5.5 later pastes the complete plan into the same field, with no step reconciling them and no verification of 3.7's retraction. If the trivial line survives, CI's own recipe (`README.md:210`) hits `check-plan.py:464`'s `if TRIVIAL.search(text)` **before** the pointer NOTE, the NO EVIDENCE LANE guard, tier derivation, the duplicate scan and every section check. Reproduced: a description holding a stale trivial line **plus** a complete plan → `trivial-skip declaration found … no further sections required.` EXIT 0. CI reports a validated trivial change; the artifact it validated is a full plan.

### M10 ✅ "Set Status to Accepted once shipped" is unreachable
`skills/ctdd-change/references/adr-rules.md:11`

Added in this diff. `Accepted` appears **only** here and in the template's enum — no step anywhere promotes an ADR. The ADR is written at 7.3; "once the change carrying it has shipped" is after 9.4 hands over, i.e. after the workflow ends. The rule's own sentence names the failure it creates: *"one left `Proposed` for life never reaches rule 15's append-only freeze and its Context and Decision stay rewritable."*

### M11 Example `Verification` omits the mandatory broader suite
`skills/ctdd-change/references/plan-format.md:161`

Names three commands; `SKILL.md:99` (8.3) requires four — contract validator, focused tests, **broader suite**, build. `worked-change.md:130` reports four in the packet. An agent copying the plan shape plans three, then must run an unplanned command or silently skip the suite. `plan-format.md:63` makes the example operative, and `Verification` is a section no tier can drop.

### M12 The canonical example contradicts itself on consumer contracts
`skills/ctdd-change/references/plan-format.md:120` vs `:145`

`Known gaps: - No consumer contract exists for the checkout caller.` vs `Contract changes: … consumers: checkout-web, settlement-batch; consumer pin: \`pacts/checkout-web-payments.json\` runs in CI`. checkout-web *is* the checkout caller and a Pact file *is* a consumer contract. `SKILL.md:26` guardrail says *"Stop on incompatible claims about the same observable constraint"* — the example the agent copies demonstrates carrying two through the gate unresolved.

### M13 A preservation pin drops the side effect it should pin
`skills/ctdd-change/references/plan-format.md:139`

The full-capture pin says only "full capture remains accepted", dropping the `PaymentCaptured` emission that `worked-change.md:27` records as this test's current behavior. The Required-case-coverage table puts Side effects in `Usual section: Both` / `Plan must name it: Always`, but the example names one only on the New-behavior side and records only `authorization` under `Case coverage not reached` — so the preservation half is neither covered nor recorded, which field rule 4 says never to do. Nothing pins that full capture still emits exactly one event.

### M14 The hold-out asks for an output the plan never exposes
`skills/ctdd-change/references/plan-format.md:168`

*"assert the remaining authorized amount you compute yourself"* — "remaining authorized amount" appears in no other section; `Intended behavior` exposes only the `CAPTURED` transition, and what it should hold is precisely what the still-open BLOCKING question has not decided. The human writes a sealed test against a field that may not exist, and it fails at the runner for a reason the packet reads as `failed`, which **blocks**. Item (2) is input-for-input the preservation pin at `:139`, so half the sealed set duplicates the agent's own suite — contradicting `:170`'s own rationale.

### M15 The canonical summary names none of the gate-visible items
`skills/ctdd-change/references/plan-format.md:102`

`:53` was changed in this diff to require the summary name seven decisions including `Business requirement`. The example's summary names direction, the unresolved decision, and the hold-out — none of the seven — though the example carries six of those sections below it. Only the summary reaches stdout at 6.1, so an agent copying the operative example prints a gate the business requirement never reaches.

### M16 "every decision" vs "every other decision", and the list is wrong either way
`skills/ctdd-change/references/plan-format.md:53` vs `SKILL.md:37`

SKILL.md says the summary names *"every **other** decision"* (other than the Hold-out printed immediately before). plan-format.md now says *"every decision"* — and then omits `Hold-out`, the one decision both files single out for full printing. It also adds `Business requirement`, which `plan-format.md:17` already puts **inside** the summary block, so the line tells the agent to "offer on request" something the gate already printed.

### M17 Worked example runs a command the workflow never prescribes
`skills/ctdd-change/references/worked-change.md:98`

`check-spec-surface.py < surface.txt` — but `SKILL.md:100` (8.4) prescribes `--git <diff-base>`, and `surface.txt` is created nowhere in the workflow. It exists only in `README.md:199`'s CI recipe (a different lane, and passed positionally there, not on stdin). `worked-change.md:3` says "Copy these shapes", so an agent copying it runs a redirect from a nonexistent file; on an empty stream the script returns exit 2 (`empty input — nothing was inspected`), which `execution.md:23` makes an unverified claim — while the transcript below shows a full successful inventory.

### M18 `gen-authz-matrix.py` is unreachable from `ctdd-change`
`skills/ctdd-change/references/plan-format.md:91` (and the `authorization` NFR row at `:149`)

The generator is named in `ctdd-tests/SKILL.md:118`, README and the rationale, but **nowhere in ctdd-change** — so the plan's `authorization` case-coverage row and `authorization` NFR budget row are both filled in by assertion at step 4.4, before `ctdd-tests` is ever invoked. A new route ships with `authorization — n/a — same policy as siblings` and zero authz rows, where `--check` against the committed matrix would have failed deterministically from the same contract file the plan is already editing.

**Note before building:** `docs/pilot-findings.md:77` already journals this exact candidate with a two-instance trigger, and `backlog.md:137` refers to the unactioned authz thread. **Confirm the trigger fired with the human** rather than treating it as new. Carry the caveat that an all-`deny` operation is a known generator limit, never a contract fact.

---

## LOW — 8 items
*Drift and self-violations with no failing behavior behind them.*

### L1 ADR `NNNN` width drift (prose only)
`adr-rules.md:9` now requires matching the repository's existing width, while `adr-rules.md:8`, `SKILL.md:39`, `execution.md:33` and `adr-template.md:1` all still spell `NNNN`. **The code is width-tolerant** — verified: `docs/adr/015-x.md -> adr`, `ADR_MARKER = \d{1,4}`, resolver `0*(\d{1,4})` — so nothing breaks; the copies just disagree.

### L2 Packet pin-state lines carry undeclared prefixes
`worked-change.md:127-128` gained `7.6 ·` / `8.3 ·` + log-path prefixes in this diff. `execution.md:43` declares a bare verdict, and the adjacent `Red state:` line one row above does **not** use the prefix — so the example contradicts both the authority and itself. Either declare the prefix in the packet shape for all three lanes or drop it.

### L3 `plan-format.md` restates what it says it doesn't
`:77` — *"`ctdd-tests` owns test naming, altitude, **assertion form** … Do not restate them here"* — sits eleven lines above a table column headed **"Assertion form"** with seven filled rows (`:85-93`).

### L4 "Gate-visible sections" omits the line that goes first
`plan-format.md:49` says *"The summary and the `Hold-out` block go to stdout in full at step 6.1"* — no mention of `Plan: <path> (<tier>)`, which `SKILL.md:37` requires **first**. Incomplete rather than contradictory, but it is the section an agent reads at 5.1.

### L5 `python3` is spelled in every command after the warning against it
`SKILL.md:12` warns it is a dead stub on Windows, then all 16 command occurrences across SKILL.md and its references spell `python3`. `docs/backlog.md` carries a variant of this ("make the absence loud"), but the backlog entry's fix is *install-time* and does not stop the agent's first invocation failing mid-workflow. A single-resolution mechanism (resolve the launcher once at step 0, carry it as a token; guard test asserting no file spells a bare `python3`) is the cheaper shape.

### L6 "Scan this repository's ADR titles" names no mechanism
`SKILL.md:57` (step 2.3) leaves the scan entirely to judgement though `--adr-dir` already resolves the directory deterministically.

### L7 Field rules restate what the example demonstrates
`plan-format.md:63` claims *"anything it demonstrates is not restated here"*; several of the eleven field rules restate what the complete example already shows. Worth an audit pass against the attention budget, not a line-by-line fix.

### L8 The post-answer plan state has no shape anywhere
Neither example ever renders `Decisions confirmed in session`, which field rule 11 mandates. Feeds H6 — the agent is told to produce a section it has never seen. Adding it to the worked example fixes both.

---

## Verification appendix — what was checked and cleared

These were investigated and are **not** defects; recorded so nobody re-runs them:

- **Variable-width ADR filenames classify correctly.** `docs/adr/015-x.md` and `docs/adr/0015-x.md` both → `adr`. Classification is directory-based, not numbering-based.
- **No forked spec-surface patterns** anywhere in `skills/ctdd-change/`. The prose only invokes `check-spec-surface.py`, which imports from `hooks/spec-edit-guard.py`. Rule 2 holds.
- **Evidence-state names agree** between `SKILL.md:113` (eight), `execution.md:11-19` (nine rows only because Compile red is split by required action) and `ctdd-tests/SKILL.md:83`.
- **Test-file write ownership agrees** across `SKILL.md:24`, `adr-rules.md:21`, `colocated-notes.md:9`, `ctdd-tests/SKILL.md:21`.
- **Exit-code semantics are conformant.** Clean tree → EXIT 2; code-only → EXIT 0; test edit → EXIT 1; bad base ref → EXIT 2. `SKILL.md:61`'s quoted verdict string is an exact prefix of the script's literal. Treating 1 and 2 alike is correct as written.
- **The canonical example passes its own checker** at `19 of 19` for a `large` plan, and `--tests-from` extracts exactly the 4 new and 4 pin names the worked example claims.
- **`check-plan.py --diff` not being used at step 3 is not a defect** — 3.3's "require exit 0" is strictly stricter than `--diff`'s added-tests-only carve-out.
- **Packet field order** in `worked-change.md:121-132` matches `execution.md:43` field-for-field (the only deviation is L2's prefixes).
- **Versioning is current:** `.claude-plugin/plugin.json` bumped in the working tree and every runtime item in the diff has a CHANGELOG entry.
- **The payments example does not violate rule 6** — `CaptureTests.cs`, `checkout-web`, `PAY-123` are fabricated illustration, and the rule forbids *real* identifiers from client work.
