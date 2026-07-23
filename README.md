# CTDD, Contract- and Test-Driven Development

A Claude Code plugin for backend work. It keeps an AI coding agent honest about *what a service is supposed to do* by treating your API contract and your behaviour tests as the specification: the thing the agent reads before it writes code, and the thing you review after.

The idea in one line: stop maintaining a separate technical spec that quietly goes out of date, and let the contract and the tests carry the technical spec instead. They can still be wrong about intent — that is the method's central weakness and it is discussed at length in the rationale — but once they are enforced they cannot *silently* disagree with the implementation they cover. A prose spec can.

If you want the reasoning behind that before you trust it, read [`docs/ctdd-in-depth.md`](docs/ctdd-in-depth.md). If you just want to feel what a change looks like, read [`docs/ctdd-in-practice.md`](docs/ctdd-in-practice.md). This file is the operating manual: what the plugin does, how to install it, and how to wire it into CI.

## What using it actually looks like

You ask for a change in plain language:

> "Add partial capture to the payments service, allow capturing less than the authorized amount."

Instead of writing code straight away, the agent stops and hands you a plan. The plan leads with the one thing that isn't routine about this change (what surprised it, or what it refuses to guess at) and then lists what it found: the existing behaviour (cited to real files and test names), the tests it intends to write, the contract change with backward-compatibility flagged, and any questions only you can answer. You read it, resolve the questions, and approve.

Only then does it write the tests, apply the contract change, and implement until both are green. It finishes by showing you the tests and the contract diff and asking you to review *those* as the spec for the change, because under CTDD, that is the spec.

That pause before coding is the **first** guard, not the only one: it catches a wrong *direction* while the misunderstanding is still a sentence in a plan rather than something already in the code. It cannot catch a wrong *encoding* — a plan whose test names are right while the assertion bodies underneath encode the wrong rule — because at plan time those bodies do not exist yet. Reviewing the tests as the spec, and the hold-out, are what cover that half.

Reviewing someone else's change works the same way from the other side:

> "Review this PR before I merge it."

The reviewer skill reads the diff spec-first: a changed test is a changed requirement, a contract diff is a boundary change, new behaviour needs a test, and so on. It returns findings with an overall verdict.

## Install

The plugin installs from any marketplace that lists it: a marketplace is just a git repo with a `.claude-plugin/marketplace.json` at its root.

From the published repo:

```
/plugin marketplace add mzorec/ctdd
/plugin install ctdd
/reload-plugins
```

From a local clone, point the marketplace at the checkout directory instead:

```
/plugin marketplace add /path/to/ctdd
/plugin install ctdd
```

The three skills load automatically and need nothing beyond Claude Code. The optional hook and the CI scripts need Python 3 (see [Requirements](#requirements)).

You can also skip the plugin entirely and copy `skills/*` into a project's `.claude/skills/`, or into `~/.claude/skills/` to have them everywhere.

### Requirements

- Claude Code with plugin support.
- The three skills need nothing else.
- The optional spec-edit hook and the CI scripts need a Python 3 launcher on your `PATH`. On Linux that's `python3`; on Windows it's usually `python` or `py`, and you'll need to adjust the commands accordingly. The only third-party dependency is PyYAML, and only for the authz-matrix script.

A word of warning on that last point: if a CTDD script ever seems to do nothing, check that `python3` actually resolves to a working interpreter. On Windows, `python3` sometimes resolves to a Store shortcut that prints a message and exits without running anything, which looks like success and isn't. The skills fall back to following the plan by hand when Python is missing, but the *deterministic* checks only run when a real Python 3 is on the path.

## The three skills

The plugin is three skills that trigger on natural phrasing. You don't invoke them by name; you describe what you want and the right one fires.

**`ctdd-change`** drives a backend change. You say "implement this endpoint" or "add this field," and it reads the existing contract and the relevant tests, then produces the pre-coding plan described above and waits for your approval before writing anything. It scales its ceremony to the risk: a genuinely trivial change gets a one-line declaration you can veto, while a change touching money or auth gets a hold-out decision and an architecture-decision record. Crucially, if a change would alter what an existing test asserts, that's routed to you as a reviewed spec change, never a silent test edit.

**`ctdd-tests`** writes and reviews tests as the spec. It enforces behaviour-level naming (so tests read as requirements, not as descriptions of the current implementation), flags brittle tests that will break on a harmless refactor, and adds property-based tests for the invariants that matter, idempotency, ordering, validation, state-machine rules. It never changes a requirement on its own; anything that would touch an asserted expectation goes back through `ctdd-change`.

**`ctdd-review`** is the reviewer's side. Given a finished diff, it runs a checklist spec-first: changed or deleted tests are changed requirements, contract diffs are boundary changes, thin coverage on a risky change escalates the severity, and a missing hold-out record on a **load-bearing** diff is a finding rather than a pass — load-bearing meaning money, authorization, state machines, or externally consumed boundary semantics, which is a different axis from implementation risk. A payment amendment is routinely normal-risk and still load-bearing.

They hand off to each other (`ctdd-change` calls `ctdd-tests` for the test-writing, `ctdd-review` calls it for the test portion of a diff) and `ctdd-tests` also stands alone when you just need to write or review tests.

If a skill doesn't fire when you expect, or fires too eagerly, edit the `description` at the top of its `SKILL.md`; nothing about the workflow depends on the wording. The `evals/` folder has trigger test cases per skill so you can tune a description against examples rather than by feel.

### Who owns which artifact

| Artifact / activity | `ctdd-change` | `ctdd-tests` | `ctdd-review` |
|---|---|---|---|
| Design plan (brief why) | writes | | |
| ADR (structural decisions, standalone requests) | writes | | checks it exists |
| API contract (OpenAPI / protobuf / AsyncAPI) | writes | | checks compatibility |
| Consumer contract (Pact) | writes | | checks it exists |
| Implementation plan (pre-coding gate) | writes | | checks diff against it |
| Hold-out decision & record | requires + records | | missing record is a finding |
| Behaviour-level tests | delegates | owns the craft | |
| Characterization tests (`currently_*`) | delegates | owns | flags when missing |
| Property tests / mutation testing | delegates | owns | |
| NFR budgets & authz matrix | plan states them | proposes the checks | absence is a finding |
| Reviewing existing tests | | owns | delegates |
| Pre-merge review of a whole change | | | owns |

## Where plans go

When `ctdd-change` produces a plan, it writes it to `docs/plans/<name>.md` and gives you a pointer plus a short summary in chat. It writes to a file on purpose: a chat window is a bad place to read and annotate a plan, and an editor with folding and syntax highlighting is a good one. Filenames are `<TICKET>-<slug>` when you have a ticket and `<date>-<slug>` otherwise, kebab-case, so the folder reads as a timeline.

**Whether you commit `docs/plans/` is your call**, and the two choices give you different things. Committed, each plan becomes part of the change's history, PR-linked context for reviewers, and a record of *why* a change was made that outlives the diff. In a regulated shop that's the raw material an audit trail draws on. Git-ignored, the plan is scratch: useful for this one review, then gone.

Either way, one thing holds by design: **a plan is never maintained after its change ships.** It's a decision record for a single change, not a living document, and nothing updates it when the code later moves on. That's deliberate: the executable artifacts are the spec, and the plan is disposable input to them. It must never become a second source of truth competing with the tests and the contract.

### A note on plan mode

On a high-risk change you'll often be in Claude Code's plan mode, which makes the gate mechanical: nothing touches a file until you approve. The plan still lives in `docs/plans/<name>.md`; plan mode's own prompt is a pointer to that file plus the summary, not a second copy.

The two responses mean different things, and it's worth being clear about them. **Approving** means "the plan is right, implement it": it's the go signal. **Declining** means "the plan's content is wrong, revise it." If the plan is right but you're simply not ready to start, that's still an approve-then-review flow; declining repeatedly to mean "not yet" just leaves the session stuck and the agent idle.

One catch worth knowing: the plan file has to be written *before* the agent enters plan mode, because plan mode restricts writes to its own scratch file. The skill handles this, but if you ever see a plan land somewhere outside your repo, that's the cause.

## Honest about what's enforced

This matters, so it gets said plainly: almost everything in this plugin is *prompted*, not enforced. A skill is prose a model chooses to follow. It is not a gate, and a model under pressure can drift from it.

Six pieces are actually deterministic:

- **the spec-edit hook**, when a team enables it, and even then it's advisory, not blocking;
- **`check-plan.py`**, checks a plan for missing sections, and given a diff, mechanically contradicts a "trivial" claim when the diff actually touched tests or contracts;
- **`check-spec-surface.py`**, lists exactly which tests, contracts, and ADRs a diff touches, including the renames and deletions the hook can't see;
- **`gen-authz-matrix.py`**, derives an authorization matrix from the OpenAPI contract, and with `--check`, fails CI when a new endpoint ships without its rows;
- **`check-redstate.py`**, verifies from a captured test run that new tests were seen failing before implementation (or with `--expect-pass`, that preservation tests were seen passing);
- **the test suites** that pin all of the above.

The only genuinely *blocking* gate in the whole workflow is Claude Code's plan mode, and that's provided by the host, not this plugin.

There's one honest gap in that list. `check-plan.py` and `check-spec-surface.py` run in CI (see the recipe below), but `check-redstate.py` doesn't: a red-state log belongs to one specific change, and CI can't generically know which log goes with the diff in front of it. So red state is deterministic *when you run it* and reviewed at the gate, but it isn't enforced by the pipeline the way the surface checks are. Closing that properly would need the plan to name its own evidence files, which isn't built yet.

## The hook (optional, off by default)

The plugin ships a hook (`hooks/spec-edit-guard.py`) that is **not active when you install**. The skills are the product; the hook is an opt-in backstop for teams that want a mechanical reminder that doesn't depend on a skill staying in the model's attention over a long session. It stays dormant until you turn it on, so a company-wide install never interrupts a colleague who didn't ask for it.

When enabled, it does two things. When an existing test file is modified, it injects a reminder that a changed test is a changed spec, say which requirement changed and why, because a test weakened to make failing code pass is a spec regression. When a contract file is touched, it injects a boundary-change reminder to state backward compatibility. Creating a *new* test file stays silent; only modifying an existing one fires.

To enable it for your team:

```
cp hooks/hooks.json.example hooks/hooks.json
/reload-plugins
```

That works from a clone. **For a marketplace install it does not**, and the reason is worth knowing: the plugin lives under `~/.claude/plugins/cache/<version>/`, a fresh directory per version whose predecessor is reclaimed some days after an update — so a file you copy there is both awkward to find and temporary. Either keep a clone for the teams that want the hook, or copy `hooks.json.example` into your own project's `.claude/` and point it at the plugin's script with `${CLAUDE_PLUGIN_ROOT}`, which survives upgrades because it resolves at run time.

Because it fires on every matching edit, consider narrowing it first, contract files only is a good default, since they're higher-stakes and edited far less often than tests. You tune detection with semicolon-separated regexes, matched case-insensitively against the path:

```
CTDD_TEST_PATTERNS="(^|/)quality/;\.robot$"
CTDD_CONTRACT_PATTERNS="(^|/)api-specs/"
```

An override *replaces* the defaults, so include the originals if you want both. SOAP shops will want `CTDD_CONTRACT_PATTERNS="\.wsdl$;\.xsd$"`.

Two limits worth knowing. Edits made through Bash (`sed -i`, heredocs, `patch`, `git apply`) never reach the hook: it covers the Edit/Write lane only, deliberately, because scanning Bash command strings would false-fire on every test *run*. And a plugin update may replace the plugin directory, so re-check that your copied `hooks.json` survived after an upgrade.

To turn it back off, delete `hooks/hooks.json` (the `.example` stays) and `/reload-plugins`.

## Hold-out acceptance tests

For load-bearing changes, money, auth, state machines, boundary semantics, the plan carries a mandatory **hold-out** decision, and `ctdd-review` treats a missing record as a finding regardless of whether the change's implementation risk is normal or high.

Be clear about the division of labour here, because it's easy to get wrong. The skill can *require the decision and record it*. It **cannot seal anything**: an instruction can't guarantee the agent never sees a file sitting in its own workspace. Sealing is CI's job: keep the one to three human-written acceptance tests in a branch or repo the agent's session never reads, and run them once, after the visible suite is green. A hold-out the agent could read is just another visible test, and proves nothing about independence.

Use a trait or category, `[Trait("ctdd", "hold-out")]`, `[Category("HoldOut")]`, but *only* as the selector CI uses to pick the sealed set from its separate location. Don't turn it into an in-repo path like `tests/HoldOut/<ticket>/`: a well-known folder in the working repo makes hold-outs *more* discoverable to the agent while labelling them sealed, which is worse than not pretending.

## CI recipe (GitLab)

The scripts only bind when something runs them; CI is where "when run" becomes "always." A minimal merge-request pipeline:

Installing the plugin puts the scripts in Claude Code's plugin directory on a developer's machine, **not** in your application repository — so CI has to fetch them, pinned to a version, and must never run whatever happens to sit at `scripts/` in the project being checked:

```yaml
variables:
  CTDD_VERSION: "<latest-release-tag>"   # e.g. v0.16.1 — a literal here goes stale every release     # pin it; an unpinned checker is a moving gate

.ctdd-tools: &ctdd-tools
  - git clone --depth 1 --branch "$CTDD_VERSION" https://github.com/mzorec/ctdd.git .ctdd
  # keep the clone out of the surface inventory: without this the plugin's own
  # tests report as your changed spec surface, and a verdict that over-reports
  # trains the reader to ignore it, which is the same outcome as under-reporting
  - grep -qxF '.ctdd/' .gitignore 2>/dev/null || echo '.ctdd/' >> .gitignore

ctdd:spec-surface:
  stage: test
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - *ctdd-tools
    - git fetch origin $CI_MERGE_REQUEST_TARGET_BRANCH_NAME
    - git diff --name-status -M "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME...HEAD" > surface.txt
    # Inventory is attention, not error — print it loudly, never fail on it:
    - python3 .ctdd/scripts/check-spec-surface.py surface.txt || echo "SPEC SURFACE TOUCHED — review changed tests as changed requirements"
    # If you adopted the generated authz matrix: fail when the contract
    # gained an endpoint with no matrix rows (regenerate + review as a spec change):
    - python3 .ctdd/scripts/gen-authz-matrix.py openapi/payments.yaml --check tests/authz-matrix.json
    # The gate: the MR description carries one pointer line —
    #   CTDD-Plan: docs/plans/PAY-123-partial-capture.md
    # — and CI resolves and validates THAT file, so CI, the reviewer, and the
    # skill all read the same plan. A 'trivial' claim is declared visibly in the
    # description and mechanically contradicted if the diff moved spec surface.
    - echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 .ctdd/scripts/check-plan.py - --from-description --diff surface.txt

ctdd:hold-out:
  stage: hold-out            # a stage AFTER the normal test stage is green
  rules:
    - if: $CI_MERGE_REQUEST_LABELS =~ /load-bearing/
  script:
    # Sealed tests live where the agent's session cannot read them — a
    # separate repo or branch, cloned only here. The trait is CI's selector:
    - git clone --depth 1 "$CTDD_HOLDOUT_REPO_URL" holdout
    - dotnet test holdout --filter "ctdd=hold-out"   # adjust to your runner
```

Adapt the filter syntax and stage names to your stack. The shape is what matters: the surface inventory is always printed, the plan lint is the failing gate, and hold-outs run from outside the working tree only after the visible suite is green.

The `--from-description` mode resolves the `CTDD-Plan:` pointer and validates the plan file, which CI can only do if `docs/plans/` is committed. If your team git-ignores plans instead, drop the pointer and paste the plan into the MR description, CI then validates that copy, at the cost of the copy being able to drift from what the reviewer reads. Committing the plans is what keeps one artifact authoritative from the skill that writes it, through the MR that points at it, to the review and CI that read it.

## Co-installing with Superpowers

Superpowers and CTDD make the same bet, discipline as plain text, at different altitudes. Superpowers governs the *loop* (brainstorming, task plans, red/green, subagent dispatch); CTDD governs the *spec* (what tests mean, who may change them, where the contract and hold-outs sit). They compose well, with one collision: both want to own the plan for "build something," and Superpowers' session-start bootstrap tends to win by going first, so you'd get its execution-focused task-list plan instead of the CTDD intent-for-a-human plan, and `check-plan.py` will correctly reject the former as the wrong format.

The fix is one adjudication note in the project's `CLAUDE.md`:

```markdown
## CTDD owns backend-change planning
For any change to a backend service's behaviour, contract, or tests, the
ctdd-change skill owns the plan gate and its plan format. Superpowers'
brainstorming applies upstream, when intent is genuinely fuzzy (greenfield
ideation feeding the business spec). Its execution-level skills (worktrees,
systematic-debugging, subagent dispatch) apply inside ctdd-change's
implementation step. Never substitute a task-list plan for the CTDD plan.
```

Everything else in Superpowers coexists freely, worktrees, debugging discipline, and fresh-context subagents all serve the implementation step well.

## Adopting CTDD from zero

The method is cheap only if the artifacts already exist. If they don't, adopt in this order, each rung pays for itself before the next:

1. **Behaviour-level test naming.** Costs nothing but discipline, and it's what makes the suite readable as a spec at all.
2. **Contract validation in CI.** Validate requests and responses against the OpenAPI or protobuf definition, so the contract stops being prose in a YAML file.
3. **The spec-edit hook, contract-only at minimum.** The one mechanical reminder; enable it and, if test-edit reminders feel noisy, turn `CTDD_TEST_PATTERNS` down and keep the contract branch.
4. **Consumer-driven contracts (Pact).** The moment a second service depends on the first, cross-service drift protection nothing else gives you.
5. **Property-based tests.** Where the real invariants live: money, quotas, idempotency, ordering, state machines.
6. **Mutation testing.** Critical core only, to prove the tests actually protect the rules they cover.

Stop climbing when the next rung costs more than the failures it would prevent. A CRUD service with one consumer may never need rung 6.

## Repository layout

```
ctdd/
├──.claude-plugin/plugin.json
├── README.md                          ← you are here
├── CHANGELOG.md
├── docs/
│   ├── ctdd-in-practice.md            ← the ten-minute introduction
│   ├── ctdd-in-depth.md               ← the full argument: reasoning, weaknesses, prior art
│   └── backlog.md                     ← deferred ideas and the triggers that would justify building them
├── hooks/
│   ├── hooks.json.example             ← copy to hooks.json to enable (off by default)
│   ├── spec-edit-guard.py             ← the spec-edit reminder
│   └── test_spec_edit_guard.py        ← its test suite
├── scripts/
│   ├── check-plan.py                  ← lints a plan; --diff cross-checks trivial claims
│   ├── check-spec-surface.py          ← lists which tests/contracts/ADRs a diff touches
│   ├── gen-authz-matrix.py            ← authz matrix from OpenAPI (--check is a CI drift gate)
│   ├── check-redstate.py              ← verifies new tests were seen failing before implementation
│   └── test_*.py                      ← each script's own test suite
├── evals/                             ← trigger test cases, one file per skill
└── skills/
    ├── ctdd-change/
    │   ├── SKILL.md                   ← the change workflow
    │   └── references/adr-template.md ← ADR scaffold
    ├── ctdd-tests/SKILL.md            ← the test craft
    └── ctdd-review/SKILL.md           ← the pre-merge review
```

## What's deliberately not here

Two things are missing on purpose. The customer's **business spec** is external (it's the source of intent this plugin consumes, not something it produces. And there's no long-lived **technical prose spec**, because replacing it with contracts, tests, ADRs, and short disposable plans is the entire idea. (The design plan isn't missing) it's a step inside `ctdd-change`, just too lightweight to be its own skill.)
