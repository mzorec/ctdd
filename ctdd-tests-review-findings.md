# `ctdd-tests` review — 47 findings, prioritised

**Scope:** `skills/ctdd-tests/SKILL.md` (121 lines) + `skills/ctdd-tests/references/rationale.md` (69 lines), plus the two scripts the skill invokes and the guards that cover it.
**Repo state:** clean working tree at `e7a639b` (V0.37.0). No diff — the whole current content was reviewed.
**Method:** 6 independent review angles + primary-source verification. Every ✅ item was reproduced by running code or by direct file comparison, not inferred.

> **This file is untracked and not part of the plugin.** Delete it when the findings are dispositioned. Do not commit it — repo rule 6 (this repo is public).

---

## Read this before acting

The reviewing session was told to ignore `CLAUDE.md` rule 3 and "The standing priority" so it could propose freely. **You have not been.** Before changing anything:

- **Rule 3 — skill prose changes need the human's approval. Stop and ask.** Nearly every item here touches `SKILL.md`. Say what each change displaces and what evidence demanded it, then wait.
- **Rule 1 — behavior changes ship with tests in the same commit.** The script-side items (U6, U7, H1, M19, L1, L2) need cases in `test_*.py`. `python -m pytest scripts/ hooks/ -q` must stay green. **Note: pytest was not installed on the review box**, so no claim is made about current suite state — check it first.
- **Rule 8 — a guard can pass without guarding.** U6 and M19 are two live instances *in the guards that cover this skill*. After fixing either, delete the rule it covers and confirm the guard fails.
- **Rule 4 — deterministic > prompted.** H1, L1 and L2 are the highest-value shape: they convert prose into a checker call, two of them with no new script.
- **Rule 10 — a repair pass is where the next defects come from.** H2 is a repair whose call-site enumeration missed this file (`backlog.md:221` lists where it landed; ctdd-tests is not on the list).
- **Windows:** `python3` is a dead stub here — it exits **49** with a Microsoft Store message. Use `python` or `py -3`.

**Suggested order:** the four URGENT prose contradictions around line 85–86 first (they can destroy user work or fabricate findings); then the two script/guard fixes (U6, U7), which need no rule-3 conversation; then HIGH as one approval conversation; then the rest.

**A structural note that shapes several fixes.** Three of the eight `Test review` items carry rules the *writing* lanes need (item 3 pinning power, item 4 no-weakening, item 8 artifact fit), but line 105 scopes the whole section to the review lane and `ctdd-review`. Items M5, M8, M9, H9 and U5 are all symptoms of that one boundary. Consider fixing it once rather than eight times.

---

## URGENT — 7 items
*Can destroy user work, fabricate evidence, or produce a false finding against correct code.*

### U1 ✅ Break-and-revert has no baseline and can destroy uncommitted work
`skills/ctdd-tests/SKILL.md:85`

> "Standalone, with no plan in flight, you may tell the two apart by **breaking the one production rule the test names**, re-running, and reverting… Verify the revert by re-running the same command and confirming a clean production diff."

The strings `git`, `baseline` and `diff-base` appear **nowhere** in this file, unlike `ctdd-change` step 0 which records staged/unstaged/untracked state before anything is written. With the user's own uncommitted work in the touched file, `git diff` is never clean — so the agent either declares it clean by recognising lines as not-its-own, or "reverts" with `git checkout -- <file>` and destroys the human's edits. **This row supplies the occasion for a destructive command in a skill that never establishes what to restore to.**

**Fix:** either delete the standalone branch and always hand back to `ctdd-change`, or require a recorded baseline + a named restore mechanism before the edit.

### U2 ✅ The same row authorizes a production edit guardrail line 28 forbids
`skills/ctdd-tests/SKILL.md:85` (vs `:28`, `:31`, `:48`)

`:28` — "Stop and hand off to `ctdd-change` before changing an expected outcome **or production behavior**." Unhedged, in a register of absolutes. `:48` — "Do not start implementation from this skill." The Output contract (35–41) has **no row admitting a production write**. Yet `:85` says "you may". Nothing states which wins, so the outcome depends on which line the agent read last. Line 31 ("Do not introduce production implementation") is the weaker hit — *breaking* a rule is not *introducing* implementation; **line 28 is the clean contradiction**.

### U3 The break-and-revert inference is unsound whenever the rule is enforced twice
`skills/ctdd-tests/SKILL.md:85`

> "green against the broken rule means the test asserts nothing, red means the behavior genuinely exists"

Holds only if the broken rule is the *sole* enforcement point. A test asserting "rejects a negative amount with 400" may pass because request-model binding rejects the value before the handler guard runs. Break the handler guard → still green → the rule declares a **correct, genuinely-pinning test** vacuous, and it gets deleted or loosened. That is exactly the outcome `:27` exists to prevent, reached by following `:85`.

### U4 ✅ The exit-2 remediation cannot work, and following it fabricates a finding
`skills/ctdd-tests/SKILL.md:86`

> "`--expect-pass` with `--tests-from <plan-path>` over a plan naming no pin is a usage error. **Fix the invocation and re-run**; report if it still cannot run."

Observed over a plan whose pin heading reads `Preservation pins: none — …`: exit 2 and the script's own message says the **opposite** of the prose (`check-redstate.py:495-503`):

> "When there are genuinely no pins, declare it on the heading line … and **do not run this lane at all**: a plan that names no pin has nothing to verify, and this result is not a pass."

There is no fixed invocation — no flag makes a pin-less plan verifiable. An agent obeying "fix the invocation" drops `--expect-pass`, which flips extraction to the new-behavior section. Observed: exit 1, `RED STATE NOT VERIFIED / passed before implementation (1): … either the behavior already existed and the plan missed it, or the test asserts nothing.` **A fabricated finding against a correct test, produced by following the row literally.**

**Fix:** replace the remediation clause with the script's own. The "usage error" *label* is accurate (exit 2 matches the docstring); only the remedy is wrong.

### U5 ✅ The craft lane's only integrity condition has no before-run
`skills/ctdd-tests/SKILL.md:45`

The lane is "steps 1–2, then 5–8; skip 3–4; **in step 6 the required result is an unchanged verdict**". But step 5 performs the edit and step 6 is the only run — **nothing in the lane produces the first half of "unchanged"**, and guardrail `:32` forbids reporting a run the agent did not perform this turn. The condition is unverifiable by construction.

Concrete: an agent calls an assertion edit "altitude repair" (`rationale.md:23` supports that reading), drops a `body.error == "AMOUNT_ZERO"` clause as an internal detail, keeps the status assertion, reports green with a truthful-sounding disclosure. The error-contract half of the spec is gone. `:27`'s prohibition does not reach it — it is scoped "to make implementation pass", and no implementation is in flight.

### U6 ✅ The guard covering these files can never fire
`scripts/test_check_spec_surface.py:1625`

```python
if claim in line and "ctdd-tests" in line:
```

Requires the claim word **and** the literal token `ctdd-tests` on the *same line*. Verified: `grep -c "ctdd-tests" skills/ctdd-tests/references/rationale.md` → **0**. Structurally incapable of failing over one of its two primary targets. In `SKILL.md` the token appears only at line 2 (`name: ctdd-tests`) and line 17 (the rationale pointer path) — neither is prose that could carry an enforcement claim.

`CLAUDE.md` rule 8 names this shape **literally**: *"a loop over lines containing a term that no longer appeared anywhere."* The docstring is also false now — it asserts "`ctdd-tests` contains no script and invokes no checker" while `:69` and `:118` invoke two.

**Fix:** scan whole file text, not per-line co-occurrence — file identity is already known from the path. Correct the docstring. Then apply rule 8's recipe.

### U7 ✅ The prescribed `--check` runs where it cannot fail
`skills/ctdd-tests/SKILL.md:118`

Run back to back exactly as written:
```
gen-authz-matrix: wrote authz-matrix.json (2 operations x 4 identities = 8 rows).   exit 0
gen-authz-matrix: authz-matrix.json is current (2 operations x 4 identities).       exit 0
```
It **cannot** fail one command after the generator wrote the file — both sides re-serialize with identical `json.dumps(..., sort_keys=True)` (`gen-authz-matrix.py:286, 315`). The flag's documented purpose is drift over time (`gen-authz-matrix.py:35`: "the --check mode makes that a CI failure"). Observed with one operation appended and the matrix un-regenerated: exit 1, `DRIFT — authz-matrix.json is stale … 4 row(s) added`.

**The agent is told to run the version that proves nothing and told nothing about the version that proves something.** Fix: keep the generate step; replace the immediate re-run with an instruction to wire `--check` into CI against the committed matrix.

---

## HIGH — 17 items
*Ships wrong behavior, blocks the workflow, or defeats a gate.*

### H1 ✅ Evidence capture is gated behind a plan the standalone lanes never have
`skills/ctdd-tests/SKILL.md:69` — the conditional "Under an approved `ctdd-change` plan" governs **both** the saved log and the checker call. The frontmatter triggers on "add a regression test", "pin the current behavior before refactoring", "add characterization tests" — all plan-free, so no checker is ever invoked and step 7 accepts the result on self-report. But `check-redstate.py`'s **first documented usage** (docstring line 5) is plan-free: `run.log --test Name1 --test Name2`, parsed at `:458`, with `expect_pass` computed independently at `:451`. Verified standalone: `--test CurrentlyReturnsEmptyList --expect-pass` → exit 0, "preservation baseline captured". `grep -rn -- "--test\b" skills/` returns **nothing** — no skill uses it. **Fix: one bullet in step 6, no new script.**

### H2 ✅ Hold-out row omits `NOT RUN` from the resolution set
`skills/ctdd-tests/SKILL.md:41` says "reports only passed/failed/declined" (3). `ctdd-change/SKILL.md:104` declares 4, `plan-format.md:71` says "unavailability is never a decline", `execution.md:27` says "This is not a decline: only the human declines." An unavailable runner has no slot here, so the agent records `declined` — which `plan-format` rule 7 calls a **waiver**, and `ctdd-review` reports one the human never made. `backlog.md:221` enumerates where the four-state repair landed ("`SKILL.md` step 9.1, `plan-format.md` rule 12, and `references/execution.md`") — **ctdd-tests is not on that list**. The row also fixes the human as the runner, where `plan-format.md:172` has a `runner:` field naming a CI job.

### H3 ✅ Worked table has no case for the smallest accepted amount
`skills/ctdd-tests/SKILL.md:98` — rows are 40, 100, 0, −1, 101. The upper edge is covered on both sides; the lower edge only on the **rejected** side. An implementation with a minimum-capture floor, `amount >= 1` on a sub-unit currency, or integer truncation of 0.01 passes all five rendered tests. The sibling's example for the **same contract** names exactly this test: `plan-format.md:131` `capture_succeeds_when_amount_is_one_cent` — "accepts the smallest positive amount" (and `:132` the upper interior boundary, also absent here).

### H4 ✅ "Lower boundary" labels a rejected input, hiding H3
`skills/ctdd-tests/SKILL.md:98` — an agent auditing its own derivation against step 3's "every material boundary" sees rows named 'Upper boundary' and 'Lower boundary' and concludes both edges are done. **The label is what makes the missing case invisible.** Compounding: lines 96 and 97 satisfy every one of line 60's merge conditions, and line 102 asks only that they stay "identifiable", so the sole accepted-boundary assertion may legitimately collapse into a data row.

### H5 ✅ Craft lane cannot legally enter step 5
`skills/ctdd-tests/SKILL.md:64` — step 5's Precondition is "step 4 assigned every test one evidence direction", but line 45 skips step 4 and lines 44–46 grant no waiver. It chains into `:69`'s "with the matching evidence direction". Observed over a renamed test that passes before and after: default mode → exit 1 with a false finding; `--expect-pass` → exit 0 recording a craft edit as a preservation baseline it is not. **Neither answer is "unchanged verdict".**

### H6 Compile-red row routes only one of the sibling's two arms
`skills/ctdd-tests/SKILL.md:83` keys on "a public type or member is absent" and always prescribes a stub. `execution.md:14` has a second arm with the **opposite** action: "the test cannot compile for its own reasons — a wrong `using`, a missing test-project reference, a typo | Fix the test support and re-run. **Add no production code and no stub.**" ctdd-tests has no row for it (line 84 names harness/fixture/clock/random/ordering/environment, not the test's own source) — **and ctdd-tests, having authored the test, is the party most likely to produce that arm.** Result: `ctdd-change` writes production code for a defect that needs none, and step 8.5 flags it as exceeding the plan.

### H7 Post-stub resume violates step 6's precondition
`skills/ctdd-tests/SKILL.md:83` — "resume only after the test executes" re-enters step 6, whose Precondition is "only the declared test artifacts changed" — false once a production stub lands. The agent halts mid-plan or overrides a stated gate. `docs/pilot-findings.md:510` records the same literalism next door ("The compile-only stub read as a ceiling on implementation"), patched in `ctdd-change` step 8 but **not** in this skill's step 6.

### H8 A throwing stub manufactures uniform red
`skills/ctdd-tests/SKILL.md:83` — the stub the row prescribes (`throw new NotImplementedException()` — the compiler requires a return) makes **every** test in the file fail before reaching a single assertion. The run distinguishes nothing about the assertions, which is precisely what `rationale.md:39` says compile failure cannot do. `check-redstate` certifies it. **The fix for the row's own named defect reintroduces that defect one layer down.**

### H9 A failure for an unplanned reason maps to no blocked row
`skills/ctdd-tests/SKILL.md:73` — step 7 preserves only "fails for the planned observable reason" and routes everything else to `When blocked`, whose only run-result rows are 83 (compile), 84 (harness/environment), 85 (unexpected pass), 86 (checker). A test failing with a 500 from an unwired collaborator instead of the planned 400 matches **none**, while `check-redstate` exits 0. Agent records intended RED and hands off.

### H10 Nothing anywhere tells the agent to read the failure text
`skills/ctdd-tests/SKILL.md:71` — "fails for the planned observable reason" is the lane's only integrity condition, and no step directs comparing the failure output against the expected values stated at step 3. Tests asserting `response.Should().NotBeNull()` satisfy it, go green the moment any code path exists, and `check-redstate` reports "red state verified". The one item that would catch it — Test review item 3, "Pinning power" — is scoped by `:105` to the review lane and is **unreachable from steps 1–8**.

### H11 Demotion to `currently_` is completely ungated
`skills/ctdd-tests/SKILL.md:121` — every rule governs *removing* the marker. `:121` constrains only "Promote or remove"; `:22` routes only "promoted to intent"; `:66`'s criterion ("unconfirmed") is self-attested; `:27` is scoped "to make implementation pass", which no rename does. So a confirmed intent test is renamed to `currently_*` through the craft lane, unchanged verdict, truthful disclosure, no gate. Load-bearing downstream in three places: `check-redstate` filters `currently_` out of the red set, `ctdd-review` accepts a marked observation for thin coverage, and `rationale.md:61-62` makes the marker mean nobody claims the behavior is desired.

### H12 A new test written as `currently_*` bypasses the gate entirely
`skills/ctdd-tests/SKILL.md:66` — the mirror of H11. A new test marked `currently_` is a "characterization observation", gets `must pass before refactor` (which never requires red), and is thereby specified **outside** the gate line 21 calls the only route.

### H13 Review handoff supplies one of three required fields
`skills/ctdd-tests/SKILL.md:114` — `ctdd-review/SKILL.md:56` requires `[severity][category][evidence-class] file:start-end — title`; its `:30` requires an evidence class from a five-value set; its `:31` bar lists nine elements. Line 114 supplies **category only** and glosses the nine-element bar as two. Entering from `ctdd-review`'s "apply the complete ctdd-tests review section", the agent emits a malformed Findings section or invents a severity — inflating a craft note into a merge-blocking finding that `ctdd-review` explicitly forbids.

### H14 The evidence-log path is unresolvable from inside this skill
`skills/ctdd-tests/SKILL.md:34` — `:69` says "save per-test output to **its exact** `.redstate.log` or `.pinstate.log` path", but the Output contract has no row for evidence logs, and this skill never names `${CLAUDE_PROJECT_DIR}`, `<plan-dir>` or `<name>`, nor resolves the plan dir. The sibling has exactly such a row (`ctdd-change/SKILL.md:42`). An agent invoked at 7.5/7.9 writes to a guessed path; `ctdd-change`'s 7.6/7.10 then runs the checker against a **different file**. (Verified *correct*: `.pinstate-after.log`'s absence — `ctdd-change` 8.3 owns that run.)

### H15 ✅ No `python3` dead-stub warning in the skill that writes the evidence
`skills/ctdd-tests/SKILL.md:17` — body line 2 carries only a rationale pointer, where `ctdd-change/SKILL.md:12` carries the hazard at the identical position. ctdd-tests spells `python3` at `:69` and `:118`. Reproduced: `python3 --version` → WindowsApps Store alias, "Python was not found…", **exit 49** — matching nothing the `When blocked` table enumerates. In standalone lanes `ctdd-change`'s SKILL.md is never loaded. `backlog.md:160-162` records this trigger as **already fired twice**. `ctdd-review` omits it too — the honest fix is one shared line in all three.

### H16 ✅ The two worked artifacts model the same endpoint incompatibly
`skills/ctdd-tests/SKILL.md:92` — `0 < amount <= remaining` implies a **decreasing running bound** (repeat partial captures). `plan-format.md:105` bounds the same `POST /payments/{id}/capture` by `authorizedAmount` and "rejects any later capture", with `:133` a 409 test for re-capture. One allows repeat captures, the other forbids them.

### H17 "Fix test support" lets a pin's scenario drift while its assertion is preserved
`skills/ctdd-tests/SKILL.md:84` — "Fix test support without changing the expectation" holds only the assertion text fixed, while `:59` makes seeded setup part of the case. Re-seeding a fixture from `Pending` to `Authorized` moves which scenario the pin exercises; the pin ends green, `--expect-pass` certifies "preservation baseline captured", and `ctdd-change` 8.3 re-runs it green after the refactor — **preserving nothing**. `:73`'s stop never engages because the repair happens before the run that reaches step 7. In the craft lane step 3 is skipped, so the setup was never written down to diverge from.

---

## MEDIUM — 19 items

### M1 `:86` mislabels the cause of a second exit-2 condition
The row attributes every exit 2 to the invocation, but `check-redstate.py:488-494` also returns 2 for a **plan-content** condition — a `currently_`-prefixed name found under the New-behavior heading — whose stated remedy is a plan edit that `:121` forbids without approved `ctdd-change`. Verified: identical re-run reproduces exit 2. The agent reports "the checker cannot run" with a diagnosis pointing at the command, not the plan line.

### M2 Worked table has no authorization case
`:94` — all five rows are 200/400 validation outcomes on a secured money endpoint. `:118` supplies `gen-authz-matrix.py` for exactly this and the frontmatter triggers on "derive authorization test cases", yet the one worked example never reaches it, and marks nothing n/a.

### M3 Worked table teaches a taxonomy the plan format cannot express
`:94` — no error path in `plan-format`'s sense ("Exact contractual code and body"), and no n/a discipline, so a derivation rendered into a plan cannot satisfy `plan-format` rule 4. Step 3's "each invalid or forbidden case" has no counterpart in the plan's `case: <positive | negative | boundary | error path | authorization | side effect | legacy behavior>` enum.

### M4 "A second event" names no assertable effect
`:96` — the accepted rows' Forbidden column is untyped while the rejected rows name a type. Rendered literally it forbids *any* second event and breaks when an audit event joins the flow; rendered as intended it duplicates the adjacent "Exactly one `PaymentCaptured`". Either way it teaches that `:59`'s "forbidden side effects" is satisfied by restating the required effect.

### M5 Craft lane's required reading omits the one rule that would stop it
`:45` sends the agent to Test review items **1, 2 and 6** — Altitude, Name, Determinism — omitting item 4 ("No weakening"), the only rule that calls a relaxed expectation a spec amendment. See U5.

### M6 De-flake verdict is undecidable from the lane's own evidence
`:45` — step 6 prescribes exactly **one** run, which cannot distinguish a fixed flake from a lucky pass. "Fix this flaky test" is an advertised trigger (`:5`). Item 6, which line 45 routes to, requires only that the agent **name** the uncontrolled input — never demonstrate control.

### M7 Blocked rows 81 and 82 fire together with opposite actions
Testing response ordering behind a database matches **both** signals verbatim. Row 81 sends the agent up a tier (hand-off, no green); row 82 sends it down (self-serve, ends green). No precedence rule, and `:73` applies "the action" in the singular. The row that ends green is the self-declared one.

### M8 `:82` instructs the move without the condition that legitimises it
Row 82 positively instructs moving exhaustive assertions to a smaller boundary. `:109`'s qualifier — "not weakened — **but only when the destination test is named and observed passing**" — lives in Test review, scoped by `:105` to the review lane, never the writing lane. So eleven cases can be "moved" to a test never run to green while the outer test passes, indistinguishable in the diff from the weakening `:27` forbids.

### M9 `:109`'s "observed passing" is unreachable in the lane that judges it
The review lane (`:46`) runs nothing, and `:32` forbids reporting an unobserved run. The sentence supplies no verdict for named-but-unobserved — its only fallback covers an *unnamed* destination — so the agent fabricates the observation or flags a correct craft repair as a spec amendment, which `:114` maps to `spec-change` and blocks the change on a false positive.

### M10 Review lane must print a command and result it never ran
`:75` requires "command, result"; `:46` declares the lane writes nothing and never enters step 6. Step 8's Precondition is vacuously satisfied over an empty set, so the step **is** enterable — the failure is in its body. Note the asymmetry: `:45` amends steps 6 and 8 for the craft lane; `:46` amends nothing.

### M11 `keep` is an approval barred by a defect bar
`:114`'s last clause permits `keep` "only where the review's own bar is met — a triggering input and an observable consequence", which a sound test has neither of by construction — yet `:105` and `:38` both require one verdict per test. Ten tests, eight sound → ten verdicts owed, two lawfully producible.

### M12 Item 8 "Artifact fit" has no verdict
`:113` — the eight verdicts map onto items 1–7 plus `keep`; the 8/8 count coincidence hides a 7-to-7 mapping. A test in the wrong project or using the wrong assertion library trips item 8 and cannot be summarized. Under `ctdd-review` entry it also gets no category, because `:114` maps verdicts, not items.

### M13 Three case lists disagree across the skill
Item 3 (`:108`) checks "positive, negative, boundary, error, forbidden-side-effect"; step 3 (`:58`) lists "positive, every material boundary, each invalid or forbidden case, each contractual error path"; the Output contract (`:38`) names only four. None mentions authorization, and none mentions a *required* side effect — so a capture test set that never asserts `PaymentCaptured` is emitted at all passes "Pinning power".

### M14 Step 2's discovery list omits the plan path and the evidence-log path
`:55` names nine conventions, none of them the two locations `:69` obliges the skill to use. `:56` then fires ("Stop before writing when any required artifact location remains unknown") and blocks a fully approved change — or the agent invents a path. See H14.

### M15 The "only route" claim hard-codes sibling step numbers
`:21` — "invokes you at 7.5 or 7.9 … the only route by which a new-behavior test can be written at all." Those numbers live in another file that no checker cross-references, and `ctdd-change`'s own internal copies have already drifted three times. The completeness claim is also unbacked: `ctdd-change`'s `Changed existing assertions` section has **no producing step** (7.5/7.9 are the only invocation points, both lane-gated), so a retargeted assertion is written by nobody or outside this route.

### M16 The Authorization matrix row obligates a print no step orders
`:40` requires the output path "printed before generation", but no step in 1–8 generates a matrix or prints that path — the only generation site is a Special test forms bullet outside the workflow. An agent asked to "derive authorization test cases" executes steps 1–8 and never reaches `:118`.

### M17 The Hold-out row is unreachable from this skill's own workflow
`:41` appears nowhere else in the file; it is `ctdd-change`'s artifact (its Gate presentation row and step 9.1). Two Output-contract rows are thus unreachable from steps 1–8 (with M16).

### M18 ✅ All seven `(source lines N–M)` citations are stale; three misland
`skills/ctdd-tests/references/rationale.md:14, 20, 27, 35, 45, 50, 59`

| cites | actual | lands on |
|---|---|---|
| Guardrails 25–31 | 25–32 | omits `:32`, the current-turn evidence rule — which has **no rationale bullet at all** |
| Routing and outputs 19–40 | 19–23 + 34–41 | omits `:41` (Hold-out); spans a gap |
| Ordered workflow 42–69 | 43–75 | 42 is blank; stops inside step 6, excluding steps 7–8 |
| Blocked-state 71–79 | 77–87 | **workflow steps 7–8** |
| Test review 96–106 | 104–114 | **the Worked case derivation table** |
| Special test forms 108–112 | 116–121 | **Test review items 3–7** |
| Characterization 113 | 121 | **Test review item 8** |

`grep -rn "source line" skills/ --include=*.md` returns only this file. The sibling states the policy at `ctdd-change/references/rationale.md:5`: *"they carry no line numbers, **which rot on every edit of the body**."* Cheapest fix is the sibling's — delete the ranges, keep the section names.

### M19 ✅ The worked-table guard does not pin boundary completeness
`scripts/test_check_spec_surface.py:1693` asserts presence of `"Representative positive"`, `"Upper boundary"`, `"Below lower boundary"`, `"Forbidden side effect"` and absence of xUnit tokens. It does **not** pin `"Lower boundary"`, the row count, or any status code — so H3/H4 exist under a passing guard, and adding a row or relabelling `:98` breaks nothing. Rule 8.

---

## LOW — 4 items
*Features, and defects outside the skill proper.*

### L1 Feature: `check-redstate.py --compare <before.log> <after.log>`
The craft lane's "unchanged verdict" (U5) is the most machine-checkable property in the skill and nothing checks it. Exit 1 when any test name's verdict differs between captures, 0 when identical, 2 when a name appears in one log only. **Reuses the existing `looks_like_pass` / `FAIL_MARKERS` per-line logic — no new parser.** Wire into step 6's craft bullet (capture before, capture after, compare) and have step 8 print the verdict beside the disclosure. Distinct from backlog items: *altitude churn* is retrospective git co-change analysis; *validated craft receipt* checks disclosure completeness. Neither checks verdict equality.

### L2 Feature: a conventions artifact for step 2
`:55` prints nine discovered conventions to stdout; steps 5, 6 and 8 all consume them, and nothing durable records them. After a compaction, a resume, or the 7.5/7.9 hand-off the block is gone, and guardrail `:30` is unfalsifiable after the fact. Proposal: step 2 writes `<plan-dir>/<name>.conventions.json` (or `.ctdd-conventions.json` outside a plan), plus `check-spec-surface.py --conventions <path> --git <base>` asserting every added/modified test path lies under the declared directory and matches the declared naming pattern. **Not a re-proposal of the rejected name linter** (43% FP) — that judged names against a plugin-wide vocabulary; this checks paths against the repository's own step-2-declared values, so it has no cross-repo false-positive surface.

### L3 The status pin is stale and the CHANGELOG claims it was verified
`docs/ctdd-in-depth.md:463` still reads "describes plugin **v0.24.0**" against a `plugin.json` at **0.37.0**, thirteen runtime releases later — and measures the ctdd-tests body at ~2.8k tokens when it is 14,389 chars (~3,597 tok at the pin's own 4 chars/token; ~3,197 even at 4.5). Sharper than staleness: CHANGELOG's Unreleased section claims *"Checked and found accurate, so unchanged: the status pin (version and all three measurements), the six deterministic pieces, hold-out vocabulary"* — **false on its first item, and false on hold-out vocabulary too** (H2). Rule 7: honesty tags are load-bearing.

### L4 ✅ A committed duplicate of the plugin tree lives at `ctdd/`
`git ls-files ctdd` returns **39 tracked files** — a second copy of the plugin inside the repo. Byte-identical to `skills/` for both files under review today, so it changes nothing here. But a second copy of every skill in a public repo is exactly the two-copy drift rule 2 exists to prevent, and **nothing guards the two trees against diverging.** Either delete it or add a guard asserting they match.

---

## Verification appendix — checked and cleared

Recorded so nobody re-runs them:

- **jqwik (`:117`) is properly sourced** — `docs/pilot-findings.md:323` ("Verified against the vendor's own user guide and independent reporting"), `CHANGELOG.md:540`, and a guard at `test_check_spec_surface.py:606-626` that permits it *only* as a warning. It is the best-evidenced line in the skill. Not a finding, and **do not adjudicate the upstream claim** from inside this repo.
- **`:118`'s generator-limit warning is true** — an operation with AND-ed scopes `oauth: [a, b]` and one with `x-roles: [admin]` plus a scope both returned all-deny across every identity, exactly as the prose warns.
- **Flags are real and correctly ordered** — `-o` (`gen-authz-matrix.py:270`) and `--check` (`:272`) exist; spec-first positional order is required and the prose gets it right (`-o m2.json openapi.yaml` → exit 2). `--expect-pass` is stripped positionally (`check-redstate.py:451-452`) so "adding" it anywhere works.
- **"Usage error" at `:86` is an accurate label** — exit 2 matches the docstring's "Exit 2 = usage or input error". Only the remedy is wrong (U4).
- **`7.5` / `7.9` resolve today** — `ctdd-change/SKILL.md:89` and `:93`. (The fragility is M15, not a current break.)
- **`.pinstate-after.log`'s absence is correct** — `ctdd-change` step 8.3 owns the after-run and never delegates it.
- **`currently_` names extract cleanly** under `Preservation pins` with `--expect-pass` (exit 0, "all 3 pin test(s) observed PASSING"); `check-redstate.py:377` handles them deliberately.
- **Internal pointers resolve** — Test review items 1/2/6 = Altitude, Name, Determinism; `Test review` (`:104`) and `When blocked` (`:77`) exist verbatim; `Preservation pins` matches `plan-format.md:32/138` and the script's `PIN_HEADING_RX`.
- **Evidence-direction vocabulary matches both regexes** — `— must fail before implementation` / `— must pass before refactor`, exit 0 both lanes.
- **`ctdd-review`'s categories exist** — `spec-change`, `needs-tests`, `test-quality` are all at `ctdd-review/SKILL.md:33`. The gap is the missing severity and evidence class (H13), not the category names.
- **Rule 6 is not violated** — the payments worked example is fabricated illustration (the pilot's real work is described elsewhere as list/paged/content-download endpoints), and `:117`'s library naming is a documented negative recommendation, explicitly permitted by its guard.
- **`--csharp-scaffold` being unused is deliberate** — guardrail `:30` forbids introducing a framework.
- **pytest was NOT installed on the review box** — no claim is made about current suite state or the passing count. Verify before and after any fix.
