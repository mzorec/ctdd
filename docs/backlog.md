# CTDD backlog — a decision record

This is not a to-do list. It is a record of ideas that are **deliberately not built**, each with the specific evidence that would justify building it. The distinction matters: a to-do list invites you to pick the next item; this document invites you to check whether reality has yet asked for one.

Each entry opens with **the problem it solves** in plain language — read those first to understand the shape of what's missing. The fields below each (trigger, cost, why-not-now) are the decision mechanics: they tell you *when* the idea earns its build, not just what it is.

**The governing rule.** The runtime is frozen. Nothing here gets built from an armchair — every item names a *trigger*, an observation from real use that must occur first. Building an item before its trigger fires is the exact anti-pattern the method's own kill-criteria section warns against: mitigating a weakness you haven't felt, which is faith dressed as engineering. Most of these will never be built, and that is the intended outcome, not a failure of follow-through.

**How to use this after the pilot.** Run one real change through the loop with pre-registered criteria and a weekly annoyance journal (see the pilot protocol). When the pilot produces a *specific* pain, come here and check whether a filed item addresses exactly that pain. If yes, its trigger has fired — build it. If the pain matches nothing here, that is the more valuable finding: a weakness neither reviewer nor author predicted, which is worth more than anything on this list.

---

## Tier 1 — blocks the grade, gated on the pilot itself

These are the only items whose absence caps the project. All are cheap; none is buildable from inside a container.

### The instrumented pilot
**The problem.** Everything about CTDD is currently argued, not observed. The method has survived four rounds of hostile review, but no one has run a real change through it on a real service and measured what happened. Until someone does, "it works" is a belief — a well-defended one, but a belief. This is the single thing standing between a strong argument and a validated method, and it's the prerequisite for every other decision on this list.
**Why you'd want it.** It converts the whole project from "here's a thing I built" to "here's a thing that works, and here's what it cost" — the difference that makes the open-source repo, the conference talk, and any Aegis pitch land. It also protects you: if the method disappoints on real work, you find out after four weeks, not after building a platform on top of it.
**What:** ~10–15 real changes on one service (ideally a real service you own), four weeks, pre-registered criteria, weekly annoyance journal, retrospective churn analysis.
**Trigger:** none — this is the trigger for everything else.
**Moves:** overall grade B+ → A−.
**Risk if skipped:** the method stays, by its own standard, unfalsifiable in deployment — kill signals named but never instrumented.

### Gate telemetry
**The problem.** The plan gate's whole value is that it sometimes stops you — makes you reconsider, edit, or reject before code exists. But right now nothing records whether that's actually happening. A gate that rubber-stamps every plan looks identical, from the outside, to a gate that's doing its job. You can't tell a working gate from a decorative one without data.
**Why you'd want it.** The single most diagnostic number for the whole method is the gate's reject/edit rate: near zero means it's theater, a healthy band means it's alive. Telemetry is what makes that number exist. It's also what lets the method detect its *own* decay over time — the difference between believing it works and knowing when it has stopped.
**What:** capture plan-gate outcomes (approved / edited / rejected) and hold-out results as JSONL — a hook if the ExitPlanMode event cooperates, a manual log if it does not.
**Trigger:** the pilot — needed to compute that reject/edit rate.
**Why not now:** needs a live event probe on your Claude Code install; must inject nothing into normal (non-CTDD) sessions, so the always-paid-bootstrap cost is avoided.

### `ctdd-retro` — structured end-of-change capture (NOT an AI-judges-the-skills diagnostic)
**The problem.** The pilot's findings have to come from somewhere, and the tempting-but-wrong source is an in-session AI reviewer asked "what should we improve about the CTDD skills?" That's the circularity weakness wearing a helpful face: the same model, running the same skills, with the same blind spots, asked to critique what it just did — it will manufacture plausible "improvements" every session because that's what models do when asked to find improvements, feeding the frozen skill prose exactly the accretion the freeze exists to stop. Worse, it's blind to the findings that actually mattered: plan-too-dense-to-read needed a human's eyes on a terminal (#1), scripts-don't-run needed a real Windows box (#2), the low-effort-drift needed a human who knew what the instruction meant (#4). None of those are visible from inside the transcript that already looks fine to the model that produced it.
**Why you'd want it (the version that isn't a trap).** Split *observing* from *judging*. The agent is a good **witness** and a bad **critic**, so have it report facts, not opinions: which workflow steps did it skip or compress, did `check-plan` actually run or fall back, how many human/advisor corrections changed direction and on what, did the existing-behavior section end up matching what was actually found, how long did exploration take. Then *you* supply judgment, prompted by structure — what annoyed you, did the gate catch anything manual review would have missed, did any prior finding recur. The tool appends a structured entry to `docs/pilot-findings.md`. It generates **observations, never skill changes** — a finding earns a runtime edit only when it recurs and you decide it does, exactly as the first four findings did.
**What:** a lightweight `ctdd-retro` skill (or slash command) run at the end of a real change: (1) agent reports the factual trace, (2) asks the human the two or three journal questions that need a person, (3) appends a structured finding entry. Explicitly forbidden from proposing skill edits — the retro feeds the journal, the journal feeds *your* decisions, no skill edits itself.
**Trigger:** after ~3–4 real changes, when the journal's *recurring* questions are known — so the retro's structure is derived from what the pilot actually keeps asking, not guessed up front (the same derive-don't-design discipline that governs the `.ctdd.yml` schema and the CLAUDE.md).
**Why not now:** you have one change's worth of data. Building a capture tool for a process you've run once means guessing its structure. Tonight's manual journal entry took ten minutes and produced four real findings; automating that prematurely optimizes the wrong thing. And the always-present risk: if built carelessly as "AI reviews the skills," it becomes a confabulation engine pointed straight at the frozen prose — so the observation-only constraint is load-bearing, not a nicety.
**Cost:** one small skill/command + a structured-entry format. The discipline (witness-not-critic, observations-not-edits) is the hard part, not the code.

### Eval CI run
**The problem.** The skills only work if they *trigger* on the right requests and hold under pressure. There are 69 eval cases written (including scenarios designed to tempt the skill into skipping process under deadline urgency), but they've never actually been run against the skill harness. So "the skills trigger correctly" is, right now, an assertion — the tests exist but nobody has watched them pass.
**Why you'd want it.** It turns guidance quality from a claim into a measurement, and it catches the failure that matters most: a skill that's *supposed* to refuse "just update the test to match, production is down" but doesn't. Without the run, you'd only discover that on a real Tuesday.
**What:** execute the 24/24/21 trigger sets against the skill harness at release time.
**Trigger:** available now — needs the skill-creator harness verified to run headless on your machine.
**Why not now:** the harness lives on your machine, not here.
**Moves:** guidance A− → A.

---

## Tier 2 — proposed mechanisms, filed in the rationale, gated on a specific pain

Each is already written into `ctdd-in-depth.md` tagged *(Proposed — not yet built.)*, against the weakness it addresses. **Do not build more than one without a matching pilot finding** — the pilot should *reprioritize* this list, and the standing bet is that the item the pilot calls for is not the one you'd guess today.

### Claim-provenance summaries (weakness #1: a sample smoothed into a story)
**The problem.** When the agent reads the test suite and reports "here's what this service does," it blends three very different things into one confident paragraph: behavior that's genuinely guaranteed by a test, behavior that happens to be true but nothing pins, and behavior nobody ever considered. The reader can't tell which is which — and acting on the second kind (accidentally-true behavior) as if it were the first is exactly how a change built on a false assumption slips through.
**Why you'd want it.** It makes the agent show its evidence per claim, so an inference the agent is *guessing at* is visibly flagged rather than dressed in the same confident prose as a fact. The reader's trust gets calibrated to what's actually asserted.
**What:** every sentence in a derived summary tagged `[asserted by: test X / contract]` or `[INFERRED]`; lintable.
**Trigger:** the pilot shows a summary being over-trusted — a change proceeded on an agent claim that turned out to be accidentally-true, not guaranteed.
**Why not now:** it's skill prose, and the instruction budget is at its edge — it costs attention *every* session to guard against a gap that may be rare in practice.
**Cost:** skill text + small linter, ~2h.

### `CTDD-UNDEFINED` marker convention (weakness #2: the suite can't say "undefined on purpose")
**The problem.** Tests say what the system *does*. They have no way to say "we deliberately decided not to define this." So a boundary that was left open on purpose looks identical to one that was simply forgotten — and the next person (or agent) either "fixes" a non-bug or trusts a gap that was never meant to be relied on. Silence is ambiguous.
**Why you'd want it.** A tiny, greppable marker turns "we meant to leave this open" into a durable, discoverable fact instead of tribal knowledge — and lets a diff touching that region flag itself, so deliberate gaps stop reading as oversights.
**What:** a `// CTDD-UNDEFINED: N<=0 — <why>` convention, a greppable inventory report, and `check-spec-surface` flagging diffs that touch marked regions.
**Trigger:** the pilot hits a real case where deliberate silence read as an oversight (or a forgotten gap read as intentional) and caused a wrong change.
**Why not now:** a convention nobody follows is a disabled check that looks like coverage — the method's own named anti-pattern. Building it is trivial; getting it *adopted* is the real cost, and adoption can't be validated without a team actually using it.
**Cost:** ~1h to build; unbounded to get followed.

### Expected-value independence analyzer (weakness #3: the wrong-encoding trap)
**The problem.** The most dangerous failure in the whole method: the agent writes a test *and* the code, and both share the same misunderstanding — so the test passes, the suite is green, and everyone's happy, but the encoded behavior is wrong. The classic case is a money test whose expected value is computed by the same production helper it's supposed to be checking (fee-inclusive where the business meant fee-exclusive). The test isn't verifying the rule; it's echoing the code's version of it.
**Why you'd want it.** It's the *first mechanical guard* this failure mode has ever had. Every other defense against wrong-encoding is human (the plan gate, spec-review, hold-outs); an analyzer that flags "this expected value is computed by production code, not stated independently" catches the gross cases automatically, before a human even looks.
**What:** a Roslyn analyzer — advisory, scoped to money/boundary asserts — flagging tests whose expected values are *computed by production code* rather than literal or test-owned.
**Trigger:** the pilot produces an actual wrong-encoding escape, or back-translation (shipped v0.6.0, the cheap human version of this guard) proves insufficient on a load-bearing change.
**Why not now:** the most expensive item here — days of work, a separate toolchain, real false-positive tuning. Back-translation is the cheap first line; prove *it* insufficient before paying for the analyzer. High value if the trigger fires, pure waste if it doesn't.
**Cost:** days; separate repo.

### Coverage-report reader (weakness #4: untested behavior reads as permission)
**The problem.** When the agent changes code in an area with thin test coverage, nothing warns it. The green suite looks like a safety net, but it has holes exactly where no tests exist — and to the agent, "no test forbids this" is indistinguishable from "this is fine." Changes proceed on false confidence precisely where confidence is least warranted.
**Why you'd want it.** Your CI already produces a coverage report; this just *reads* it and annotates the changed files with their real coverage number. "This area is thinly covered — extra human attention" becomes a fact the agent surfaces, not a judgment a reviewer has to remember to make.
**What:** `check-spec-surface --coverage cobertura.xml` annotates changed files with existing coverage %.
**Trigger:** the pilot repos actually emit cobertura/lcov, *and* a thin-coverage area caused a change to proceed on false confidence.
**Why not now:** it reopens a shape of idea already killed once (the coverage *quantifier*, which died over per-ecosystem tooling maintenance). This is a *reader* of an existing report, which is genuinely different — but it still only earns its place if the report exists and the gap actually bit.
**Cost:** ~2h.

---

## Tier 3 — integration ideas, coherent but unproven

### SDD-style requirements decomposition, upstream of the plan gate (weakness: creation vs. preservation)
**The problem.** CTDD is strongest at *preservation* — tests brilliantly pin "don't break what exists." It's weakest at *creation*: for a genuinely new, genuinely fuzzy feature, the spec has to come from somewhere before any test can encode it, and "writing the tests is writing the spec" quietly assumes you already know what the tests should assert. On a vague requirement, a wrong new test is a wrong spec with nothing upstream to catch it. Spec-driven development's structured requirements phase is a real answer to exactly this gap.
**Why you'd want it.** For the fuzzy-greenfield case — where the plan gate's "uncovered / ambiguous" list is too thin to pin down what "correct" even means — a short, structured acceptance-criteria decomposition gives the plan something solid to build tests from. It borrows SDD's genuine strength for the one case CTDD admits it's weak.
**The hard boundary that keeps it coherent:** the requirement doc is **consumed by the first test that encodes it, then it's history** — same lifecycle as the plan, never a parallel maintained source of truth. Break that rule and you've resurrected the drift-prone prose side-spec CTDD exists to abolish, now running *beside* the thing that replaced it. (SDD and CTDD aren't two methods to blend — they're the same "where does the spec live" question, and a naive blend maintains prose *and* tests, which is the original disease next to its cure.)
**What:** an optional `ctdd-specify` skill, triggering *only* on greenfield / genuinely-ambiguous work (never amendments or bug fixes), producing a disposable acceptance-criteria breakdown that feeds the existing plan gate.
**Trigger:** the pilot includes a genuinely fuzzy new feature where the plan gate's ambiguity list proved too thin to decompose the requirement, and a wrong new test resulted.
**Why not now:** the doc already lists creation as a known weakness with a stated mitigation ("the plan gate matters most on new work"). Shipping *more* mitigation before evidence the existing one is insufficient is faith. Small — one conditional skill, load-bearing on nothing — but small and unjustified is still unjustified.
**Cost:** one conditional skill, upstream of the plan.

### Weakness #8 machinery — audit-record archiving
**The problem.** In a regulated shop, "we followed a disciplined process" often has to be *provable to an auditor*, not just true. CTDD produces the raw material — plans, ADRs, reviewed test diffs — but scatters it (plans ride into PR descriptions and vanish; nothing archives the decision trail in a form an auditor would accept). For regulated-domain work this could be the difference between the method being adoptable and being a compliance liability.
**Why you'd want it.** It turns the method's own byproducts into an audit trail — the plan-as-filed, the decision archived, the hold-out result recorded — so "show me you reviewed this change as a spec change" has an answer that isn't "trust us."
**What:** canonical file paths for plans, plan/decision archiving, and the derived-record-for-auditors design.
**Trigger:** a *regulated adopter* who must satisfy an auditor forces the design — the real question ("will this auditor accept a derived record?") is answered by an auditor, not by a feature.
**Why not now:** the doc's own least-proven idea. Building an archiving system before an adopter needs it is designing a filing cabinet for documents nobody is filing.
**Downstream:** this is also the trigger for revisiting **plan YAML frontmatter** (rejected three times) — frontmatter becomes natural once plans have a canonical archived file path, and pointless before. *(Note: v0.8.0's file-backed plan output, `docs/plans/<ticket>.md`, was the first step toward this canonical path — driven by a real readability finding, not by this item. If the pilot keeps producing plans as files, this trigger is closer than it looks.)*
**Cost:** unknown until the adopter's constraints are known.

---

## Tier 4 — absorbed from other tools, gated on the freeze

### Full Superpowers eval-under-pressure methodology
**The problem.** A skill can trigger correctly and still *fold* the moment a request comes wrapped in urgency, sunk cost, or borrowed authority ("the senior dev said just sync the expected values"). Trigger-accuracy tests don't catch that — they check whether the skill fires, not whether it *holds* once fired. The pressure cases landed in v0.7.0, but the broader technique (systematically hardening skill prose against rationalization) is a repeatable process, not a one-time addition.
**Why you'd want it.** It hardens the skills against the exact conditions under which discipline actually breaks in real life — deadline pressure — rather than the calm conditions under which prose is easy to follow.
**What:** the repeatable pressure-testing process, applied whenever skill prose changes.
**Trigger:** eval CI runs (Tier 1) and a pressure case *fails* — a skill that should hold the wall doesn't.
**Why not now:** cases without a running harness are untested assertions; the technique needs the harness first.

### Require an exact contract delta in the plan, not a prose description
**The problem.** The plan gate is called contract-first, but the plan format asks only for "Contract changes, if any" — and the worked example supplies prose ("relax amount rule to `0 < amount <= authorized`"), not a diff. So the human approves *an idea about the boundary*, and the actual OpenAPI/protobuf edit happens after approval. "Amount becomes optional" and `nullable: true` are not the same change; approving the first does not approve the second. This is the contract twin of the wrong-encoding problem the method already understands for tests — approving a test *name* while the wrong assertion hides in the body.
**Why you'd want it.** It closes the gate's remaining blind spot on the boundary half. Requiring either a fenced delta (`- required: [amount]` / `+ required: []`) or an explicit "None — externally observable boundary unchanged" makes the approved artifact the same artifact that ships. For code-first/runtime-generated contracts (this fleet's case: OpenAPI generated at startup), the equivalent is the exact annotation/signature delta that generates it.
**Trigger:** an approved prose contract description diverging from the delta actually applied — the pilot's plans so far *did* carry exact DTO records and endpoint declarations, so the failure this prevents has not yet been observed. Also worth watching: a reviewer objecting that they could not tell, from the plan, what the boundary would become.
**Why not now:** proposed by review, not by use — and the plan format is already the heaviest block in the skill. Adding a mandatory section to close an unobserved gap is the accretion the freeze exists to prevent. If the trigger fires, the fix is one bullet in the format plus a `check-plan.py` presence check.
**Cost:** one plan-format bullet, one script pattern, two test cases.

### Hold-out waiver schema (approver + reason)
**The problem.** `declined by human` is a terminal outcome with no recorded owner. v0.9.5 fixed the dangerous half — `failed` now blocks approval and `declined` is named an explicit waiver reported as a deviation — but a waiver still has no *approver* or *reason* field, so "required, unless someone declined it" can quietly become "optional with bookkeeping."
**Why you'd want it.** A waiver that names who accepted the risk and why is auditable; an anonymous one is a hole with a label on it. In a regulated shop this is the difference between a recorded risk acceptance and an unexplained gap.
**Trigger:** the first real `declined by human` on a load-bearing change. Zero have occurred — every pilot hold-out has been `required` or `not required`, and the one outstanding is `pending`.
**Why not now:** designing a waiver form before anyone has waived anything is guessing at the fields. The consequence-clause shipped in v0.9.5 is the part that was actually dangerous.
**Cost:** two optional fields in the hold-out line, one review check.

### `gen-authz-matrix.py`: conjunctive requirements produce no allow-row, yet `--check` calls the endpoint covered
**The problem.** When one requirement object demands *two* things at once — two scopes, or a scope plus `x-roles` — no single identity on the generated axis holds the combination, so every row for that operation comes out `deny`. Each row is individually correct (a caller with only `payments:write` really should get 403 when `payments:admin` is also required), and the C# scaffold won't fail against a correct implementation. The defect is subtler: **the authorized-caller path is never asserted at all**, and because `--check` compares only row *presence*, the endpoint reports as covered with zero positive-path coverage. Same presence-isn't-quality gap the project already names for `check-plan.py`, but here it hides behind a green check.
**Why you'd want it fixed.** An authz matrix whose whole point is "who can reach this" that silently omits "and here is who *can*" is a comfortable lie on exactly the endpoints with the strictest requirements — the ones where AND-ed scopes appear. In a regulated domain that is the wrong place to be quietly uncovered.
**What:** synthesize a composite identity per conjunctive requirement (the union of what that requirement demands) so at least one allow-row exists, and have `--check` fail an operation whose rows are entirely `deny`.
**Trigger:** available now — an external review found it by reading the code, and the fixtures only ever use a single scope, which is why 12 green tests miss it. Build it when an OpenAPI document in the pilot actually uses conjunctive security, or when the authz matrix is first wired into a real CI (finding #10's still-unactioned authz thread).
**Why not now:** it needs a design call on what a synthesized composite identity is *named* in the matrix, and naming it wrong makes the drift check noisy for everyone. Filed with its repro rather than guessed at 1am.
**Cost:** ~2h plus fixtures with conjunctive security.

### Description tightening
**The problem.** The three skill *descriptions* sit in the agent's context every single session (~1k tokens total, always paid). They're near the point where adding words stops sharpening the trigger and starts blurring it — but "near the point" is a guess, because the eval harness that would *measure* trigger accuracy hasn't run. Tightening them blind is as likely to make triggering worse as better.
**Why you'd want it.** Sharper descriptions mean the skills fire when they should and stay quiet when they shouldn't — less wasted context, fewer false triggers. But only if the tightening is guided by measurement.
**What:** trim/sharpen the always-in-context descriptions, guided by eval data.
**Trigger:** eval CI shows a *specific* trigger error — a false fire or a miss traceable to description wording.
**Why not now:** the right next skill change, but doing it blind is guesswork. Sequence: eval CI → measure → *subtract* words → re-measure.

### Compose with Claude Code `/code-review`; narrow `ctdd-review` to the spec lane
**The problem.** Claude Code's built-in `/code-review` is a strong *correctness* reviewer (four agents hunting bugs, boundary conditions, auth flaws, with a verification pass). `ctdd-review` does something different: it asks whether the changed tests and contract encode the *right requirement* — a changed test that flips `capture_fails...` into `capture_succeeds...` is not a bug (code correct, tests green, all correctness agents pass), it's a silently changed requirement. The risk is running them as if they're the same tool: either drowning in redundant overlap, or dropping `ctdd-review` and losing the spec-level check `/code-review` structurally cannot make.
**Why you'd want it.** Clarity on the division of labor: `/code-review` for "is this code correct," `ctdd-review` for "did the requirement quietly change," the scripts for the mechanical layer. Run all three; narrow `ctdd-review` away from generic quality nits (which `/code-review` does better) toward its unique spec lane — a *subtraction*, the rare change the freeze permits.
**What:** a README note on running both, plus a scoped narrowing of `ctdd-review` if the pilot shows redundancy.
**Trigger:** the pilot runs one change through both and shows either redundant noise (narrow it) *or* `ctdd-review` catching a changed-requirement `/code-review` waved through (keep it broad — its justification, proven on live code).
**Why not now:** which way the evidence points is a one-diff-seen-by-both question; guessing narrows away a check that might be earning its place. The independent-pass argument stands regardless: when agents write code, a second correctness agent shares the author's blind spot — LLM-as-Judge alone catches ~45% of errors (IBM, AAAI 2026) — so an independent spec-level pass is worth keeping beside the correctness one.
**Constraint for your world:** the *managed* Code Review product is GitHub-only, Team/Enterprise-plan-only, ~$15–25/PR — unavailable on self-hosted GitLab. The *local* `/code-review` command runs on any plan but is correctness-only and reads `CLAUDE.md`/`REVIEW.md`, not your skills. So on your stack: local `/code-review` for correctness + `ctdd-review` skill for spec + the deterministic scripts in CI.
**Cost:** documentation, not code.

---

### The deterministic layer needs a real interpreter and silently no-ops without one — make the absence loud
**The problem.** Twice now a change has reached the verification step, tried to run `check-redstate.py`, and hit `Python was not found` — the machine has the tool but no `python`/`py`/`python3` that actually executes (the Windows Store alias resolves the command and then refuses to run). Each time the agent fell back to verifying the log *by hand* — correctly, and it got the right answer — but a hand-verified gate is precisely the thing the deterministic layer exists to replace. v0.8.2 documented the launcher token; it did not make a *missing* interpreter fail loudly, so the failure mode is a checker that quietly isn't there and a human trusting a manual grep.
**Why you'd want it.** The whole argument for scripts over prose is that they don't depend on anyone's diligence. A checker that silently degrades to "the agent eyeballed it" has the reliability of prose while looking like enforcement — the worst of both. The fix is not more prose; it is (a) a one-command environment check the README/skill can run once (`py -3 -c "print(1)"` or equivalent) that turns "no interpreter" into a setup error at install time rather than a surprise at the gate, and possibly (b) a tiny pure-shell fallback that at least counts declared-vs-failing test names when no Python exists, so the manual grep becomes a script rather than a human habit.
**Trigger:** already fired twice (two separate changes hit `Python was not found` mid-verification). This is the most-repeated *environment* failure in the pilot.
**Why not now (barely):** the manual fallback worked both times and the change shipped correctly, so it is not urgent — but it is the clearest "mechanism exists and silently isn't invoked" case, and it should be built before a third occurrence, not after. Needs a small decision on whether the shell fallback is worth maintaining as a second implementation of the same check (the thing the project otherwise refuses).
**Cost:** ~1h for the install-time check; ~2h more if the shell fallback is built and tested.

### The generated-client / OpenAPI-404 hazard is a recurring, cross-change trap worth a named check
**The problem.** On at least two changes, regenerating the API client rewrote *every* endpoint's 404 handling from the shared error type to a synthetic per-operation type, breaking existing typed-client tests on endpoints the change never touched. Root cause is stable and external to any one change: the API's OpenAPI document doesn't `$ref` the shared error schema for 404s, so the generator inlines a fresh type per operation. Each change rediscovers this the hard way, reverts the regeneration, and ships without a typed-client method.
**Why you'd want it.** This is a contract-integrity problem CTDD is well-placed to catch but currently doesn't: the OpenAPI document *is* a contract artifact, and "the shared error type is no longer shared" is exactly a silent contract regression. A small check — assert every error response of a given status `$ref`s the shared schema rather than an inline type — would turn a repeated multi-hour surprise into a red gate, and it generalizes (any shared response type that silently de-shares).
**Trigger:** fired on the paged-list change and again on the content-download change — same root cause both times.
**Why not now:** it is arguably a lint for *the API repo*, not the CTDD plugin, so it may belong in that project's CI rather than here; and it needs the shared-schema convention stated before it can be checked. File until it's clear which repo should own it — but it is a real, repeating, contract-shaped defect, not a one-off.

### Stop mid-implementation when the change outgrows its risk call (not just when the plan is wrong)
**The problem.** Step 8 already stops and re-opens the gate when implementation reveals that *a planned test, contract clause, or behaviour assumption is wrong*. What it doesn't clearly cover is the plan being **incomplete rather than incorrect**: the change turns out to touch far more than the plan listed, or to be materially riskier than the risk line claimed. A "normal" change quietly becoming a high-risk one is a real failure mode, because the ceremony that would have applied (hold-out, ADR, closer review) was decided at the gate on a smaller picture, and nothing re-asks the question.
**Why you'd want it.** The risk call drives everything downstream. If it's wrong and never revisited, a money-path change can ship with the review depth of a rename.
**Why not now.** In practice agents already stop for discoveries well beyond the current rule's letter: on a dirty tree, on someone else's in-flight refactor, on a client regeneration that broke untouched endpoints, on a pre-existing view leak found while implementing. The behaviour is emergent and reliable so far, so a new rule would be prose for something already happening. There is also a real cost to over-stopping: a gate that fires on every discovery becomes noise, the human stops reading it, and that is the "nobody reads the plan" failure arriving from the opposite direction.
**Trigger:** an actual instance where implementation grew materially past the plan's risk call and shipped without the gate re-opening, or where a reviewer found the ceremony was chosen on a picture that had since changed. Build it then, scoped tightly to the risk line rather than to "any discovery."
**Cost:** ~1–2 sentences in step 8, and a matching `ctdd-review` check that the shipped diff still matches the plan's declared risk tier.

### Move minority-case blocks out of `ctdd-change` into `references/` (progressive disclosure, not a skill split)
**The problem.** `ctdd-change` is ~6.9k tokens, the largest of the three skills and near the top of the ~64 skills measured on disk. Step 6 (the plan gate) is 646 words and step 7 is 389 — about 40% of the workflow between them. Several blocks are needed on only a minority of changes but load every time: the ADR rules, the standalone-ADR-request lane, and the when-artifacts-disagree procedure.
**The idea.** Move those into `references/` files loaded on demand, the way `references/adr-template.md` already works. Same rules, less always-loaded weight, no new triggering surface.
**Why NOT split it into more skills** (the rejected alternative, recorded so it isn't re-proposed): skills load one at a time on trigger, so a plan skill plus an implement skill would either both end up loaded — same tokens, an extra always-on description, and a new routing failure mode — or load sequentially, leaving the plan's rules out of context exactly when implementation needs them. The coupling data rules it out anyway: "the plan" appears 25 times in the skill and "the gate" 8, because step 7 depends on the plan's declared tests, step 8's amendment rule depends on the gate, and step 9 checks the diff against what the plan said. It is one causal chain; cutting it duplicates the cross-references (drift) or drops them.
**Trigger:** evidence that size is actually degrading rule-following — most directly, the pressure eval cases showing worse compliance at current size than at a reduced one. Absent that, this is restructuring on a hunch, and the skill measures the same as the largest skill in the most-referenced peer plugin, so "it feels big" is not evidence.
**Cost:** ~2h, plus a re-run of the trigger evals to confirm the on-demand blocks still get pulled when they should.

### Stop parsing test names out of prose: have the plan emit a machine-readable list
**The problem.** `--tests-from` extraction has now had **three separate fail-silent defects**, all in the same function, all found by outside readers rather than by use: a prose line mentioning characterization tests swallowed every name after it; names without an underscore (plain PascalCase, the dotnet default) were skipped entirely; and identifier-shaped bullets were pulled from *every* non-pin section, so the plan format's own mandated "existing behavior" citations were treated as new tests. Each fix was correct. The pattern is the finding: a regex reading identifiers out of hand-written markdown has an unbounded surface, because the prose it reads is free-form by design, and every failure mode is silent by default — the checker verifies the subset it managed to parse and reports success for it.
**Why you'd want it fixed properly.** This is the gate that answers the pilot's own most-repeated weakness (prompted discipline drifts). A gate whose parser can silently under-read is a gate you have to hand-verify, which is what it exists to replace.
**What:** have the plan carry the test names in a form that cannot be mis-parsed — a fenced block with one name per line under a fixed marker, or a small JSON/YAML frontmatter block the skill writes and the script reads. Prose stays for humans; the machine reads the machine block. The script then fails loudly when the block is missing rather than guessing from bullets.
**Trigger:** available now — three defects is a pattern, not a coincidence. The reason to file rather than build tonight is that it changes the plan *format*, which touches `ctdd-change`, `check-plan.py`, `check-redstate.py`, and every example, and a format change made at the end of a long session is how you get a fourth defect.
**Watch for:** the honest counter-argument is that a machine block is a second place test names live, so plan prose and the block can disagree. Mitigation is that the block is the only thing the script reads, and review reads both.
**Cost:** ~3h across the skill, both scripts, and the examples.

### Redesign the hold-out so it actually gets written (0% execution rate over the whole pilot)
**The problem.** Finding #30: the hold-out was declared required on four to five load-bearing changes and executed zero times, by the method's author, after repeated prompts. It is the primary mitigation for the central weakness, so a 0% rate makes that weakness effectively unmitigated in practice.
**The likely mechanism.** It is requested at plan time and collected after green. Plan time is peak engagement; post-green is the trough. The design asks when attention is highest and collects when it is lowest.
**Options, none chosen:**
- **Shrink the ask.** "One assertion and one expected number, from the business spec" instead of "one to three acceptance tests." Most of the guard's value is in one independent expected value on the load-bearing path.
- **Move it forward.** Collect the sealed assertion *during* the plan review, while the human is already reading and deciding, and hold it until after green. The independence property survives; only the timing changes.
- **Stop claiming it.** Downgrade weakness #3's coverage honestly and rely on the plan gate, the tests-as-spec review, back-translation, and the v0.12.2 middle guard, saying plainly that the strong form is aspirational.
**Trigger:** available now — this is a reproduced failure with n=5 and the strongest possible subject. The reason not to build tonight is that all three options are real, they trade differently, and choosing between them is a product decision that deserves a rested read plus one actual attempt at writing a hold-out to see what it really costs.
**Cost:** ~1h for the shrink or the move; the honest downgrade is a doc edit and a paragraph in the rationale.

## Recorded rejections — do not re-propose without engaging the reason

These were proposed (several more than once, by different reviewers) and rejected with cause. They're here so a future round argues with the reasoning instead of re-litigating the conclusion.

| Rejected | Reason | Would reopen if |
|---|---|---|
| Bash command-string scanning | False-fires on every test *run* (`dotnet test tests/X.cs` matches the same path pattern as an edit). Half-right determinism gets disabled; a disabled check that looks like coverage is the named anti-pattern. | A scanner could distinguish a test *run* from a test *edit* with near-zero false positives — non-trivial. |
| In-repo `tests/HoldOut/<ticket>/` convention | A well-known path in the working repo makes hold-outs *more* discoverable to the agent while labeling them sealed — sealing theater, worse than nothing. The trait is CI's selector from a *separate* location only. | Never, while the agent has repo read access. Structural, not tunable. |
| Plan YAML frontmatter | Plans live in PR descriptions and plan-mode output, often never as files; frontmatter there is ceremony parseable by nobody. The stable-headings contract already exists in `check-plan.py`. | Weakness #8 archiving gives plans a canonical file path (see Tier 3) — and v0.8.0's `docs/plans/` output is the first move in that direction. |
| Second-opinion review by a second agent | Same model, same prior, same blind spot — two green artifacts agreeing proves nothing. Back-translation replaced it by reading *artifact → prose* instead of re-deriving *intent → artifact*. | A genuinely independent checker exists (different model family, or a human) — at which point it's just "the human reviews," already in the method. |
| Coverage *quantifier* (vs. reader) | Per-ecosystem coverage-tooling maintenance is a rabbit hole. | Superseded by the coverage-report *reader* (Tier 2), which reads an existing report instead of computing coverage. |

---

## The one-line test for anything added here later

Before filing a new idea, it must answer: **what observation from real use would tell me this is needed, and what would tell me it isn't?** An idea that can't name its own disconfirming evidence doesn't belong in this document — it belongs in the rationale's list of things the method deliberately doesn't do.
