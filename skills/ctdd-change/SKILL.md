---
name: ctdd-change
description: >-
 Drive a backend API or microservice change the Contract- and Test-Driven
 Development (CTDD) way. Use whenever the user asks to implement, add, modify,
 extend, or fix behavior in a backend service — an endpoint, handler, message
 consumer, domain rule, or bug — even if they never say "CTDD" or mention
 tests. Reads the existing API contract and relevant tests before designing
 anything, produces a reviewable pre-coding implementation plan, gates coding
 on approval, and prompts for an Architecture Decision Record (ADR) on
 structural decisions. Also use for standalone ADR requests ("write an ADR",
 "record this decision"). Triggers include "implement this endpoint", "add
 this to the service", "change this API", "fix this bug in the service",
 "modify this handler", "plan this backend change", "migrate this flow", "refactor this
 service", "raise or change this limit or rule", "implement the review
 comments on my PR", "address the reviewer's feedback", "deprecate a field
 in an event schema", "stage a contract or event-schema rollout", "CTDD
 this". Not for
 visual/UX correctness (testable state logic qualifies wherever it lives),
 not for infrastructure/build/deploy config (Dockerfiles, pipelines, cluster
 manifests), not for test-only tasks (use ctdd-tests), and not for reviewing
 an existing diff or PR (use ctdd-review).
---

# CTDD: driving a backend change

**Use this skill when the unit of work is a change** — a feature, endpoint, handler, message consumer, or bug to build or modify. It owns the whole workflow and every non-test artifact: the design plan, the ADR (structural decisions), the API contract, the consumer contract, and the pre-coding implementation plan. When it is time to write or review tests, it hands off to the `ctdd-tests` skill for the test craft. If the task is *only* about tests — writing tests in isolation, or reviewing/fixing existing tests, with no feature being built — use `ctdd-tests` directly instead.

Follow Contract- and Test-Driven Development. The direction is the inverse of prose-spec-driven development: the API contract and tests come first and the technical prose spec is *derived from them*, not written up front. Tests are the executable spec for **preservation** ("don't break what exists"); the business requirement plus the plan are the spec for **creation** ("what to build").

One clarification the name invites: **"contract-first" means the boundary is specified before tests and implementation — not before understanding.** Always read what exists before designing what changes.

Scope: services behind an API — and the real line is *assertable correctness*, not the deployment tier. Don't apply it where correctness is visual or experiential; testable state logic (reducers, routing, client-side state machines) qualifies wherever it lives.

## Workflow

Work through these steps in order. Scale ceremony to the risk of the change — a one-line fix skips most of this; a change to a state machine or a service boundary does all of it. On non-trivial changes, **no work product is written to disk — no contract edit, no ADR, no test, no code — until the implementation plan (step 6) is approved**; steps 3–5 produce drafts that ride inside the plan. The plan file itself (step 6) is the one pre-approval write: it is the gate's artifact, written *before* approval so the human reviews it in an editor — deferring it until after approval defeats the point. **Scaling down is visible, never silent:** when you judge a change trivial and skip the gate, first output one line — `Risk: trivial — <reason>. Skipping the plan gate.` — so the human can veto the classification before you touch a file. Two changes are never trivial regardless of size: an edit to an existing test, and any contract-file edit — "just updating a test" is a spec change. Where a diff already exists, `scripts/check-spec-surface.py` is the deterministic counterweight to this call: if it reports touched test or contract surface, the change is not trivial.

1. **Confirm intent.** Restate the business requirement (what the customer/caller needs) in one or two sentences. This is the source of what to build. If it's ambiguous, ask before proceeding.

2. **Read what exists.** Retrieve the relevant slice of the API contract and tests — by route, message type, module, changed files, domain terms, or failing tests — not the whole suite. Summarize the current behavior so you and the developer share an accurate model of what exists. Present this summary as "here's my reading — correct me," never as ground truth. For a greenfield service there is nothing to read — say so and move on; the contract and the plan carry the spec, and everything written in steps 5–7 becomes its seed.

3. **Design plan (brief).** State the approach, the shape of the change, what's explicitly out of scope, and the riskiest part. If the developer already gave direction, capture theirs rather than inventing a competing one. Keep it short — it leads the plan's decision summary, not a maintained doc.

4. **ADR — only for a structural decision.** If the change touches a service boundary, a cross-service contract, a data-ownership line, or any architecture choice with real tradeoffs, draft an Architecture Decision Record. See "ADR rules" below. If it's an ordinary behavior change, skip this.

5. **Draft the contract change.** Design the API contract delta (OpenAPI/JSON Schema for REST, protobuf/gRPC IDL, AsyncAPI for events) before tests or implementation — the contract is the boundary spec the service and its consumers build against. State whether it's backward-compatible; flag breaking changes explicitly. For a change that affects another service, include the consumer-driven contract update (e.g. Pact) so both sides are pinned and a breaking change fails in CI, not in production.

6. **Implementation plan — STOP for review.** Assemble the plan (format below) and stop. For anything beyond a trivial change, wait for a human to review and approve it before touching a file. This is the cheapest place to catch a wrong **direction**, and that is all it catches: at plan time the test encodings don't exist, so a shared misunderstanding in an assertion body sails through. Step 9 and the hold-out handle that half. **Write the plan file before entering plan mode, and in that order** — plan mode restricts writes to its own scratch file, which is disposable, outside the repo, and invisible to `ctdd-review` and CI — an agent already inside it *cannot* create `docs/plans/<n>.md`. Write the plan to the repo, *then* suggest plan mode for high-risk changes if the session isn't already in it — it makes this gate mechanical, and the plan presented for approval already contains the proposed contract diff and test names. If you are already in plan mode with no repo plan file, say so and ask the human to exit it long enough for you to write the file, rather than quietly adopting the scratch file as the record. **When in plan mode: the repo plan file at `docs/plans/<n>.md` is the authority — never the harness's own plan file. Plan mode's exit presentation is that file's own content — **read the file and copy it in verbatim**, never write a fresh summary of it. Summarizing is the natural move when the box is labelled "plan" and it is the wrong one: the moment the presentation is composed rather than copied, you have two plan documents, they immediately disagree on detail, and the human cannot tell which one they approved. In practice that means the **decision summary section, pasted verbatim, plus the file path**, with the rest left in the file. Short and verbatim are not in tension: the file already opens with the thirty-second read, so copying it satisfies both — the human gets the same brief summary they would have got anyway, and it is the same text the file holds, so there is nothing to drift. What is forbidden is re-wording it. A truthful excerpt, never a re-write. Present it and immediately hand the exit decision to the human; do not sit re-presenting. **If you learn something material while the gate is open** — a corrected fact, a working-tree surprise, an answer that changes the design — you cannot carry it in the presentation instead: a delta that exists only in what you show is the second plan document arriving by another route, and the file the human reviews is then stale on the newest thing you know. Say what you learned, say the plan file needs it, and ask to leave plan mode long enough to write it, then re-present. Never close the gate with the file and the presentation disagreeing. Approving the plan-mode gate means "implement from the plan file," so treat it as the go-signal, not a request to re-plan.** Whenever a plan is produced, write it to `docs/plans/<name>.md` (create the directory if absent), where `<name>` is `<TICKET>-<kebab-slug>` when a ticket exists, else `<YYYY-MM-DD>-<kebab-slug>`. Use kebab-case for the slug (`capture-partial-payment`, not `capturepartialpayment` or `CapturePartialPayment`). Print the plan **in full, to the terminal as well as the file** — summary first, detail below it — and say where the file was written. Compose it once: the file is authoritative, and the terminal shows that same content, never a separately-written variant. The one exception is a trivial change: it produces no plan (just the `Risk: trivial — <reason>` line), so it produces no file — put that same `Risk: trivial — <reason>` line in the PR/MR description so CI can validate the claim, since there is no plan to point at. Otherwise put one pointer line in the PR/MR description — `CTDD-Plan: docs/plans/<name>.md` — so the reviewer and CI validate the same artifact you wrote rather than a pasted copy that can drift; when `docs/plans/` is tracked, commit the plan (and any `.redstate.log`/`.pinstate.log`) so the pointer resolves for the reviewer and CI, and when it is git-ignored, paste the plan into the description instead. The plan is not *maintained* after the change ships.

7. **Write the tests and apply the contract.** First check the working tree: uncommitted work you did not make, or implementing straight onto `main`, contaminates the diff this method reviews. Report what you found and let the human choose — commit, stash, branch — rather than building on a mixed tree. Then, after approval: apply the contract change, write any ADR the plan drafted to its numbered file (`docs/adr/NNNN-*.md`, per the ADR rules), then write behavior-level tests for the new behavior — new behavior has no tests yet, so this is where its spec is created. Write them at the behavior level (defer to the `ctdd-tests` skill for the discipline). Reach for property-based tests where an invariant applies (idempotency, ordering, validation, terminal-state rules). Then run the new tests **before implementing** and observe them fail — a test that has never failed is unvalidated as a detector. A new test that passes before the implementation exists is a finding — either the behavior already exists and the plan missed it, or the test asserts nothing. **Capture that failing run to a file** — `docs/plans/<name>.redstate.log` beside the plan — and verify it: `python3 scripts/check-redstate.py docs/plans/<name>.redstate.log --tests-from docs/plans/<name>.md` (or `--test <Name>` per test; `python`/`py` on Windows). **The evidence is that verdict line, not the log file** — carry it into the review. Verifying `--tests-from` the plan is what catches a test silently renamed or swapped between plan and implementation; an unverified log is not evidence. If capturing is impossible in this environment, say so explicitly at review — never state or imply red state was verified when no run was captured. **One exemption, and it turns on what the test *asserts*, not when it was written:** a **pin** (characterization) test asserts behavior that *already exists* — so it must be observed **passing** against the current implementation, and must still pass after the change. Green-then-still-green is its evidence; feeding it to `check-redstate.py` would report a false finding. A behavior-preserving refactor normally has both kinds. **Capture pin evidence the same way**: run the pins green against the *current* implementation before converting, save that run to `docs/plans/<name>.pinstate.log`, and verify it with `check-redstate.py docs/plans/<name>.pinstate.log --expect-pass --test <Name>`; after converting, the same tests must still pass. A pin that *fails* before the change is a finding in itself — the pin does not describe what the code actually does, so fix the pin, or you will "preserve" behavior that was never there.

 In a compiled language, a test naming a type that does not exist yet does not *fail* — it does not *compile*, and an uncompiled test is not evidence of anything. Write the new type as a stub (throwing or returning a default) so the test compiles and fails for the right reason, then implement. If you skip the stub, say so rather than reporting red state you never observed.

8. **Implement until the contract validates and the tests are green.** Do not weaken a test to make it pass. **If implementation reveals that a planned test, contract clause, or behavior assumption is wrong, stop and re-open the gate** — this is an amendment (see "Amendments" above), not an implementation detail: amend the plan in place with the old and new assertion or contract delta, re-run `check-plan.py`, and get approval for the amendment before changing the spec artifact. Discovering the error late does not downgrade it; "changed the test and mentioned it at the end" is the silent-spec-change path the gate exists to close.

9. **Present the spec for human review.** When green, present the diff with the tests and the contract framed as the spec, not just the code: changed tests are changed requirements, contract diffs are boundary changes. If `scripts/check-spec-surface.py` is available, run the diff through it (`{ git diff --name-status -M HEAD; git ls-files --others --exclude-standard | sed 's/^/A\t/'; } | python3 scripts/check-spec-surface.py -`, or `python`/`py` on Windows — listing untracked files alongside the diff catches a newly-created test file, the blind spot where a bare `git diff` reports no surface and a new regression test slips through) and include its output: any test or contract surface it reports that the plan didn't declare — or declared trivial — means stop and reclassify before review. For a load-bearing diff, also produce a **back-translation** before handing over: state, from the tests in this diff alone, the requirement they encode — one or two plain sentences — and put it next to the business requirement so the human compares prose to prose. If the plan recorded a hold-out as required, this is when it runs: ask the human to execute the sealed tests now, after green, treat their result as part of this review, and update the plan's hold-out `result:` line accordingly (the outcomes, and what each one blocks, live in the plan format's Hold-out field). The `ctdd-review` skill drives the reviewer's side of this gate.

10. **Invariant note — only where needed.** If a rule is universal or a boundary is intentionally undefined and can't be made executable, add one colocated sentence (docstring/contract comment), e.g. "Must hold for all N > 0; behavior for N ≤ 0 is intentionally undefined." Do not write prose for anything a test or contract already covers. Same sentence-sized budget for **a fact this code depends on that lives outside this repo** and cost real time to establish: an upstream system's semantics (status `7` in the ledger feed means *settled*, not *pending*), a non-obvious key relationship (a capture's id is its authorization's id, not one of its own), a storage format (this column is compressed in production and raw in test), a framework quirk that constrains the shape. The entry test is one question: **could the next reader derive this from the code, the tests, or the contract in this repo?** If yes, do not write it. If no, and rediscovering it means reading another system, write the one sentence where the code touches it. **State the rule, never the citation.** Write what is true ("ledger status 7 means settled; a capture in that state must not be re-submitted"), not where you found it ("the upstream service checks this in its settlement handler"). A citation pins your comment to another team's file name, so it breaks silently when they refactor and nothing here will ever notice. The test is durability: **a colocated note states something that stays true; anything true only as of today belongs in the plan or an ADR**, which are point-in-time records and may name specifics freely. So the plan carries the provenance and the code carries the rule. This is not an ADR (that records a decision you made) and not a spec (a test covers behavior) — it is the external fact both of those assume.

### Bug fixes

A bug fix runs the same loop, compressed. Confirm the *expected* behavior (step 1), read the slice (step 2), then write a failing behavior-level regression test that reproduces the bug — that test *is* the spec of the fix — and implement until it's green. The test stays forever; that is how the suite accumulates edge cases. (The regression-test rule itself lives in `ctdd-tests`; this section owns only the workflow around it.) The plan gate collapses to a *short* plan — the sections still appear, most as one-liners ("Existing behavior: test X asserts Y; Proposed tests: the regression test; Contract changes: none") — not to a trivial one-line skip. Adding a regression test is adding spec, so a bug fix is not the trivial lane; `check-plan.py` reports an added-test diff distinctly for exactly this reason. The trivial lane is for code-only changes that touch no test or contract surface at all. One caution: if an existing test asserts the buggy behavior *on purpose*, this is not a bug fix but a spec change — stop and run the full gate (step 6), calling out the test change explicitly.

### Amendments — the everyday case

Most real changes modify behavior an existing test asserts — neither pure preservation nor pure creation. Route these as spec changes, not code changes: the business requirement overrides the old test, and only through a reviewed diff. The plan must show each affected test's old and new assertion (see the plan format); the gate and the step-9 review do most of their real work here. The reflex to resist by name: "update the test to match" turns a spec change into a silent one.

### When artifacts disagree

A contract that allows what a test rejects, an example test contradicting a property test, a Pact expecting a shape the contract dropped — a cross-artifact conflict is a **detected spec bug**, not a tiebreak. First check that it *is* one: artifacts conflict only when they make incompatible claims about the **same observable constraint**. Different artifacts legitimately own different layers — a schema stating a payload's shape while a test asserts a state-dependent business rule is not a contradiction, and a Pact or example narrowing a broader permitted space is specialization, not conflict. Stop, decide which artifact is wrong against the business intent, and fix it as a reviewed spec change. The one forbidden move is quietly adjusting whichever artifact is easiest to change until CI goes green.

### Standalone ADR requests

When the ask is only to record a decision ("write an ADR for choosing RabbitMQ over Kafka"), skip the workflow and apply the ADR rules directly: interview for context, decision, and consequences where they aren't given; find the next number in the ADR directory; write the file from the template.

## The implementation plan (output before coding)

Produce this as a reviewable summary, then stop for approval on non-trivial changes:

**Lead with a decision summary the human can read in under a minute**, then put the supporting detail below it — the gate asks for a *ruling on decisions and risks*, not a reading of the whole file inventory. **The test of the summary is that a reader who agrees with it can approve without scrolling**; if they must go into the detail to find out what they are agreeing to, the summary has failed and the two-layer structure has bought nothing.

Write it the way you would tell a colleague what you found, standing at their desk with thirty seconds of their attention — **lead with what surprised you, or what you are not willing to guess at**. A summary that reads like a filled-in form has failed even when every field is correct: fields carry categories, and what a reviewer needs is the one thing about *this* change that is not routine. If nothing about it is surprising, say exactly that in a sentence and stop — a short honest summary is the goal, not a filled page.

Close it with a single categorical line, demoted because it is genuinely form-like: `Risk: normal · contract: additive · ADR 0005 required · hold-out: 2 sealed tests from you`. State `contract: breaking` explicitly whenever an existing response shape, route, or error code changes — a breaking change a reviewer meets in the file inventory rather than the summary is the failure this line exists to prevent — and name anything the human is on the hook for, because those are commitments, not information.

Then the two buckets:

- **BLOCKING — I will not guess.** The open questions whose answer changes the implementation and which you refuse to assume: each as a one-line question with your recommended answer. These are what approval actually turns on.
- **Proceeding unless you object.** Decisions you've made and will act on (schema choices, ordering, nullability, what the repository returns): one line each. Consequences you'll absorb belong here, not in BLOCKING — the point is to show them without asking permission for each.

A reader who agrees with every recommendation should be able to approve from the summary alone. The detail below is backup for when they don't.

The detail section, in full:

- **Risk level** — normal / high-risk, with one line on why (a trivial change produces no plan at all — see the workflow preamble — so a plan's risk line never reads `trivial`; and, if a high-risk unknown is carved out of an otherwise-normal change, name it here so the risk call is honest). This is the justification for the ceremony being scaled up or down; a reviewer who disagrees with the risk call should be able to object to that before anything else. **If a BLOCKING decision later resolves in a way that changes scope — a type-only option becoming a breaking rewire, say — restate the risk level and the contract-changes section to match the branch actually chosen.** A plan whose top-line risk reflects the option you didn't take reads as safer than the work is.
- **Existing behavior** found in the contract and relevant tests — cite the file paths and test names actually retrieved (evidence, not paraphrase), so thin retrieval is visible to the reviewer. State known gaps explicitly — "no Pact found for the checkout caller" converts silence into a reviewable absence.
- **Assumptions** you are making.
- **Uncovered or ambiguous cases** — behavior that matters but isn't pinned by a test, and anything the requirement doesn't specify.
- **Proposed new/changed tests** — named at the behavior level, and **split under two headings when both kinds are present**, because their evidence runs in opposite directions:
 - `New-behavior tests — must be observed failing` (red state applies; `check-redstate.py --tests-from` reads *only* these)
 - `Preservation pins — must pass before and after` (green-then-still-green is their evidence; verified with `check-redstate.py --expect-pass`, never the default red-state check — see step 7)

 **When a change both preserves and creates, do the preserving part first** — pins describe how the current code behaves, so a pin written before a change that reshapes what it observes still passes while proving nothing. Pin, convert, verify green, *then* build the new behavior on top. This ordering is a correctness property, not a preference: get it backwards and the suite stays green while the detector is silently gone.

 For each *changed existing* test, show the old and the new assertion, not just the name — the name is exactly where a wrong encoding hides.
- **Contract changes**, if any (and whether they're backward-compatible; flag breaking changes explicitly).
- **NFR budgets this change could touch** — latency/throughput, authz surface, tenant isolation, retention/audit. State "none" explicitly; an unstated budget is not a free one.
- **Hold-out** — required / not required, with why. Required when the change alters money, auth, state-machine, or boundary semantics (rounding, inclusivity, timezones, fee treatment). If required, ask the human to write 1–3 acceptance tests directly from the business spec and to withhold them from you; they run once, after green (sealing them is the team's CI job — see the README). Record the decision **and track its outcome**: write `result: pending` at plan time; step 9 updates it to `passed`, `failed`, or `declined by human`. The outcomes are not equivalent: `failed` **blocks approval at review** — `ctdd-review` treats a failed hold-out as a merge-blocking finding, and since nothing mechanical enforces it the reviewer is that gate; a failed hold-out is the method working, and merging past it is the one thing the hold-out exists to prevent. `declined by human` is an explicit **waiver**, reported at review as a deviation on a load-bearing change, never a neutral success. Never proceed as if this step happened when it didn't — and never leave it `pending` past review.

  **Where the hold-out is declined, fall back to human-verified expected values** on the load-bearing assertions — a distinct, cheaper guard, not a degraded hold-out. You write the test; the human checks the *number*, by doing the arithmetic rather than reading the code that produced it (capturing 87.50 of 100 leaves 12.50). Say which assertions you want checked and show the values plainly. This breaks the **shared-computation** path, where a test derives its expected value from the same production helper the implementation uses and both encode the same wrong rule. It cannot break a **shared misunderstanding**: if the human misreads the requirement the same way you did, the number looks right to both of you, and only a sealed test written from the business spec by someone who has not seen the implementation reaches that. Offer it as the fallback, never as the equivalent — a guard that quietly replaces the hold-out makes circularity worse while feeling like progress.
- **ADR draft**, if step 4 produced one.
- **Files likely to change.**

Treat a change to an existing test as a change to the spec — call it out for review. If this plugin's `scripts/check-plan.py` is available on disk, run the emitted plan through it — adding `--diff` with the current `{ git diff --name-status -M HEAD; git ls-files --others --exclude-standard | sed 's/^/A\t/'; }` once edits exist (the second half so a new, still-untracked test file is counted, not silently missed), so a trivial claim is cross-checked against the actual surface — and fix any missing sections before presenting.

### Example (condensed)

Request: *"Add partial capture to the payments service — allow capturing less than the authorized amount."*

```
A backward-compatible relaxation of the capture amount rule — the one thing I
won't guess is what happens to the auth hold on the released remainder.
Risk: normal · contract: additive · no ADR · hold-out: 1–2 sealed tests from you

BLOCKING — I will not guess:
- What happens to the auth hold on the released remainder? (recommend: it
 expires with the original authorization)
Proceeding unless you object:
- Zero capture amount is rejected; the released remainder is not re-capturable

Risk level: normal — single-service, backward-compatible contract change;
money path, so amount edge cases must be pinned in tests

Existing behavior (payments/contract/openapi.yaml; tests/payments/CaptureTests.*):
- POST /payments/{id}/capture requires amount == authorized amount
- capture_fails_when_amount_exceeds_authorized_amount covers over-capture
Known gaps: no consumer contract (Pact) found for the checkout caller

Assumptions:
- Partial capture moves the payment to CAPTURED (no new PARTIALLY_CAPTURED state)
- The released remainder is not re-capturable

Uncovered / ambiguous:
- What happens to the auth hold on the released remainder? (needs confirmation)
- Is a zero capture amount valid? (assuming no)

Proposed tests:
- capture_succeeds_when_amount_is_below_authorized
- capture_releases_remainder_when_partially_captured
- capture_fails_when_amount_is_zero

Contract changes:
- Relax amount rule to 0 < amount <= authorized (backward-compatible)

NFR budgets touched: none — no new external calls; authz surface unchanged

Hold-out: required — money-path amount semantics; asked the human for
1–2 sealed acceptance tests from the business spec (run once, after green);
result: pending

Files likely to change:
- payments/contract/openapi.yaml
- payments/domain/capture.* (+ tests)
```

The human resolves the ambiguous points, approves, and only then are the contract edit, the tests, and the code written. Had this introduced a `PARTIALLY_CAPTURED` state shared across services, step 4 would have added an ADR draft to the plan.

## ADR rules

An ADR is a short record (a page or less) of one significant decision, in three parts: **context** (the situation and forces), **decision** (what was chosen), **consequences** (what was accepted, good and bad). Scaffold new ADRs from `references/adr-template.md` in this skill's folder.

- Store as a numbered, append-only file, e.g. `docs/adr/0007-payments-in-domain-layer.md`.
- **Append-only:** never edit a past ADR to reflect a new decision. If a decision is reversed, write a new ADR that supersedes the old one and mark the old one "Superseded by NNNN". The record is what was believed *at the time*.
- Capture the decision and its tradeoffs, not a description of current behavior. The moment it narrates what the code does, it has drifted into spec territory — stop.

## Guardrails

- **No status claim without a run in this turn.** Don't say tests pass, the build is clean, a gate is green, or a subagent's work is done unless you ran it in *this* message and read the output. A previous run, a partial check, and an agent's own report of success are not evidence — for a subagent, the diff is the evidence, not its summary. If you couldn't run it, name what you did not verify rather than wording around it.
- Untested behavior is not permission to change it — and **a claim to *preserve* behavior needs a detector just as much as a change does**. In a thinly-covered area, flag it for human attention rather than trusting a green suite. For a behavior-preserving refactor, "the existing tests are the guard" is an assertion, not a fact, until you name *which* tests assert the behavior being preserved; if you cannot name them, the guard does not exist. Cheapest fix when a refactor replaces an existing implementation (a hand-written mapper swapped for a generated one, a helper for a library): write the new tests against the **old** implementation first and watch them pass, then convert — the same tests must still pass. Same tests, written in the other order; it costs nothing and turns the claim into evidence. Where the old implementation is being deleted, this is the only thing that records what it did. (The `ctdd-tests` skill defines the characterization discipline: `currently_*`-marked observations, distinct from intent.)
- For distributed-systems logic (async messaging, eventual consistency, retries, ordering, partial failure), treat it as the dangerous core and escalate rigor: property tests, contract tests at the messaging boundary, and human review. Don't rely on example tests alone here.
- Keep the customer's business spec as the source of intent — this workflow replaces the hand-written technical implementation spec, not the business requirement.
