# CTDD — Contract- and Test-Driven Development

A Claude Code plugin for backend API and microservice work. It encodes **Contract- and Test-Driven Development**: the API contract and behavior-level tests come first and *are* the executable spec the agent reads and builds against — the technical prose spec is derived from them, not written up front. Tests own preservation ("don't break what exists"); the business requirement plus a short plan own creation ("what to build").

**Scope:** backend services behind an API — more precisely, anywhere correctness can be captured in an executable assertion. Not for visual/UX correctness; testable state logic (reducers, client-side state machines) qualifies wherever it lives.

New to the method? [`docs/ctdd-in-practice.md`](docs/ctdd-in-practice.md) is the ten-minute introduction — the concept and what a change feels like in practice. The full argument — where it breaks, how it compares to spec-driven development, and where it sits in the 2025–2026 SDD landscape — lives in [`docs/ctdd-in-depth.md`](docs/ctdd-in-depth.md). This README is the operating manual; *CTDD in practice* is the on-ramp; *CTDD in depth* is the rationale — the why.

## Requirements

- Claude Code with plugin support.
- The three skills need nothing beyond Claude Code. The optional spec-edit hook (off by default — see below) needs `python3` on `PATH`; on native Windows outside WSL, change `python3` to `python` in your copied `hooks/hooks.json`.

## Install

The plugin installs from any marketplace that lists it — a marketplace is just a git repo carrying a `.claude-plugin/marketplace.json`. If this plugin lives in your repo, add a minimal one at the repo root:

```json
{
  "name": "my-plugins",
  "owner": { "name": "Your Team" },
  "plugins": [
    { "name": "ctdd", "source": "./ctdd", "description": "Contract- and Test-Driven Development" }
  ]
}
```

Then in Claude Code:

```
/plugin marketplace add <owner>/<repo>      (or a git URL, or a local path)
/plugin install ctdd@my-plugins
/reload-plugins
```

The three skills load automatically. The spec-edit hook is shipped **off by default** — see "The hook" below to opt in.

## Quick start

Ask for a backend change in plain language:

> "Add partial capture to the payments service — allow capturing less than the authorized amount."

`ctdd-change` triggers and, **before writing any code**, returns an implementation plan: a risk call, the existing behavior it found (cited to files and test names), its assumptions, the uncovered/ambiguous cases it needs you to resolve, the proposed behavior-level tests (changed existing tests shown old-vs-new assertion), the contract delta (with backward-compatibility flagged), the NFR budgets it could touch, a hold-out decision for load-bearing semantics, and the files it expects to touch. You resolve the ambiguities, approve, and only then does it apply the contract change, write the tests, and implement until both are green — closing by presenting the tests and contract diff as the spec for your review. Works especially well in plan mode (`Shift+Tab` or `/plan`), where the pre-coding gate is enforced by the tool itself.

Bug fixes run the same loop compressed: a failing behavior-level regression test reproduces the bug first, then the fix, and the test stays forever.

On the other side of the merge:

> "Review this PR before I merge it."

`ctdd-review` runs the checklist against the diff — spec first, code second — and returns findings tagged spec-change / needs-tests / needs-adr / boundary-risk / test-quality / risk-misclassified / nit, with an overall verdict.

## The three skills

**`ctdd-change`** — drives a backend change the CTDD way. Reads the existing contract and the relevant slice of tests, drafts the contract change, produces a reviewable pre-coding implementation plan (risk call, NFR budgets, hold-out decision for load-bearing semantics, changed tests shown old-vs-new assertion), gates coding on approval — a trivial skip is itself declared in one visible line you can veto — and closes with a human review of the tests and contract as the spec. Amendments to behavior an existing test asserts are routed as reviewed spec changes, never silent test updates. Prompts for an append-only ADR when a structural decision is involved, and also handles standalone ADR requests ("write an ADR for choosing RabbitMQ"). Ceremony scales to the risk of the change.

**`ctdd-tests`** — writes and reviews tests as the spec. Enforces behavior-level (not implementation-coupled) naming, flags brittle tests that break on refactor, checks contract coverage and test↔contract alignment, distinguishes characterization observations (`currently_*`) from asserted intent, routes any change to an asserted expectation out to `ctdd-change` (test craft never changes requirements), adds property-based tests for invariants (idempotency, ordering, validation, state-machine rules) including the contract-derived authorization matrix, and suggests mutation testing on the critical core.

**`ctdd-review`** — the reviewer's side. Runs the deterministic spec-surface inventory first when `scripts/check-spec-surface.py` is available, then the PR checklist against a finished diff: changed or deleted tests are changed requirements, contract diffs are boundary changes, new behavior needs a behavior-level test, structural decisions need an ADR, thin-coverage or distributed-systems changes escalate severity, and an implicated-but-unstated NFR budget — or a missing hold-out record on a high-risk diff — is a finding, not a pass.

`ctdd-change` defers to `ctdd-tests` for the test-writing discipline; `ctdd-review` calls it for the test portion of a diff; `ctdd-tests` also stands alone whenever you just need to write or review tests.

Triggering is description-driven: the skills fire on natural phrases ("implement this endpoint", "review these tests", "check this before I merge"). If one doesn't fire when you expect — or fires too eagerly — edit its `description` frontmatter; nothing about the workflow changes. A trigger eval set ships in `evals/` (one file per skill, should/shouldn't-trigger queries), so the `skill-creator` optimizer can tune a description empirically instead of by feel. Nothing runs the eval sets automatically yet — treat them as a release-checklist step.

**Enforcement honesty:** almost everything in this plugin is *prompted* — a skill is prose a model follows, not a gate. The deterministic pieces are exactly five: the spec-edit hook (when a team enables it; advisory, not blocking), `scripts/check-plan.py` (when run; an omission detector for the plan that, given `--diff`, also mechanically contradicts a trivial claim when spec surface moved), `scripts/check-spec-surface.py` (when run; a diff-surface inventory that sees the renames, deletions, and Bash-lane edits the hook structurally can't), `scripts/gen-authz-matrix.py` (derives the authorization matrix from the OpenAPI contract; `--check` fails CI when an endpoint ships without its rows), and the test suites that pin the scripts and the hook. The only genuinely *blocking* gate in the whole workflow is Claude Code plan mode, which the plugin recommends but the host provides.

### Who owns which artifact

| Artifact / activity | `ctdd-change` | `ctdd-tests` | `ctdd-review` |
|---|---|---|---|
| Design plan (brief why) | ✓ | | |
| ADR (structural decisions, standalone requests) | ✓ | | checks presence |
| API contract (OpenAPI / protobuf / AsyncAPI) | ✓ | | checks compatibility |
| Consumer contract (Pact) | ✓ | | checks presence |
| Implementation plan (pre-coding gate, risk call) | ✓ | | checks diff against it |
| Hold-out decision & record (load-bearing changes) | ✓ requires + records | | missing record is a finding |
| Behavior-level tests | calls → | ✓ owns the *how* | |
| Characterization tests (`currently_*`) | calls → | ✓ | escalates when missing |
| Property tests / mutation testing | calls → | ✓ | |
| NFR budgets & authz matrix (weakness #7) | plan states budgets | proposes the checks | absence is a finding |
| Reviewing/critiquing existing tests | | ✓ | calls → |
| Pre-merge review of a whole change | | | ✓ |

## The hook (optional, off by default)

The plugin ships a `PostToolUse` hook (`hooks/spec-edit-guard.py`) that is **not active on install**. The skills are the product; the hook is an opt-in backstop for teams that want mechanical enforcement, and it stays dormant until a team turns it on. This keeps a company-wide install from ever interrupting a colleague who didn't ask for it.

What it does when enabled: when an **existing test file is modified** (Edit/MultiEdit) — or is about to be overwritten wholesale via Write, caught by a PreToolUse companion with an existence check — it injects a note that a changed test is a changed spec — say which requirement changed and why; a test weakened to make failing code pass is a spec regression. When **any contract file is touched** (OpenAPI, protobuf, AsyncAPI, Pact), it injects a boundary-change note — state backward compatibility; breaking changes need the consumer contract updated. It's the one enforcement that doesn't depend on a skill staying in Claude's attention over a long session. Creating a *new* test file stays silent by design; only modifying an existing one fires.

**To enable it for your team:** copy the shipped example into the standard location and reload.

```
cp hooks/hooks.json.example hooks/hooks.json
/reload-plugins
```

Because the hook fires on every Edit/Write, consider narrowing it before enabling — e.g. contract files only, which are higher-stakes and edited far less often than tests — by deleting the test branch's patterns via the env override below, or trimming the matcher in your copied `hooks.json`.

Tune detection with semicolon-separated regexes, matched case-insensitively against the forward-slash path (set these in your shell or your team's `settings.json` env block):

```
CTDD_TEST_PATTERNS="(^|/)quality/;\.robot$"
CTDD_CONTRACT_PATTERNS="(^|/)api-specs/"
```

Three honest limits and one caveat. The PreToolUse overwrite note relies on `additionalContext` support in current Claude Code builds; community docs report it preserved (even when the tool call fails) from around v2.1.110 — on older builds it may be silently dropped, while the Edit/MultiEdit branch is unaffected either way. Edits made through **Bash** (`sed -i`, heredocs, `patch`, `git apply`) never reach tool-matched hooks — the hook prices the Edit/Write lane only; a regex scan of Bash command strings was considered and rejected because it would false-fire on every test *run*. An override **replaces** the defaults, so re-include them if you want both; SOAP shops: `CTDD_CONTRACT_PATTERNS="\.wsdl$;\.xsd$"`. And a plugin **update may replace the plugin directory** — re-check that your copied `hooks/hooks.json` survived after every upgrade (unverified whether updates clobber it; assume they might).

**To turn it back off:** delete `hooks/hooks.json` (the `.example` stays), then `/reload-plugins`.

## Hold-out acceptance tests — sealing is CI's job

For load-bearing changes (money, auth, state machines, boundary semantics) the plan now carries a mandatory **Hold-out** line, and `ctdd-review` treats a missing record on a high-risk diff as a finding. Be clear about the division of labor: the skill can *require the decision and record it* ("required / requested / declined by human"); it **cannot seal anything** — an instruction cannot guarantee the agent never sees a file in its own workspace. Sealing lives in CI: keep the 1–3 human-written acceptance tests in a branch or repo the agent session doesn't read (or inject them in CI), and run them once, after the visible suite is green. A hold-out the agent could read is just another visible test.

Use a trait or category — e.g. `[Trait("ctdd", "hold-out")]` or `[Category("HoldOut")]` — **only as the selector CI uses** to pick the sealed set from its separate location. Do **not** turn it into an in-repo convention like `tests/HoldOut/<ticket>/`: a well-known path in the working repo makes hold-outs *more* discoverable to the agent while labeling them sealed — sealing theater, worse than nothing.

## CI recipe (GitLab)

The two scripts bind only when run; CI is where "when run" becomes "always." A minimal `.gitlab-ci.yml` fragment for merge-request pipelines:

```yaml
ctdd:spec-surface:
  stage: test
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - git fetch origin $CI_MERGE_REQUEST_TARGET_BRANCH_NAME
    - git diff --name-status -M "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME...HEAD" > surface.txt
    # Inventory is attention, not error — print it loudly, never fail on it:
    - python3 scripts/check-spec-surface.py surface.txt || echo "SPEC SURFACE TOUCHED — review changed tests as changed requirements"
    # If you adopted the generated authz matrix: fail when the contract
    # gained an endpoint without matrix rows (regenerate + review as a spec change)
    - python3 scripts/gen-authz-matrix.py openapi/payments.yaml --check tests/authz-matrix.json
    # The gate: MR description must be a conforming plan, and a 'trivial'
    # claim is mechanically contradicted if the diff moved spec surface:
    - echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 scripts/check-plan.py - --diff surface.txt

ctdd:hold-out:
  stage: hold-out            # a stage AFTER the normal test stage is green
  rules:
    - if: $CI_MERGE_REQUEST_LABELS =~ /load-bearing/
  script:
    # Sealed tests live where the agent's session cannot read them — a
    # separate repo/branch, cloned only here. The trait is CI's selector:
    - git clone --depth 1 "$CTDD_HOLDOUT_REPO_URL" holdout
    - dotnet test holdout --filter "ctdd=hold-out"   # adjust to your runner/trait syntax
```

Adapt the filter syntax and stage names to your stack; the shape is what matters — surface inventory always printed, plan lint as the failing gate, hold-outs executed from outside the working tree only after green.

## Co-installing with Superpowers (and similar workflow plugins)

Superpowers and CTDD make the same bet — discipline as plain text — at different altitudes: Superpowers governs the *loop* (brainstorm, task plans, red/green, subagent dispatch); CTDD governs the *spec* (what tests mean, who may change them, where the contract and hold-outs sit). They compose, with one collision: both claim workflow entry for "build/change something," and Superpowers' session-start bootstrap tends to win by first-mover — you'd get its task-list plan (written to specify *execution* for a context-free subagent) instead of the CTDD plan (written to specify *intent* for a human approver). `check-plan.py` will correctly fail the former; that's a format mismatch, not a defect in either plugin. The fix is one adjudication note in the project's `CLAUDE.md`:

```markdown
## CTDD owns backend-change planning
For any change to a backend service's behavior, contract, or tests, the
ctdd-change skill owns the plan gate and its plan format. Superpowers'
brainstorming applies upstream, when intent is genuinely fuzzy (greenfield
ideation feeding the business spec). Its execution-level skills (worktrees,
systematic-debugging, subagent dispatch) apply inside ctdd-change's
implementation step. Never substitute a task-list plan for the CTDD plan.
```

Superpowers' utility skills coexist freely — nothing in CTDD conflicts with worktrees, debugging discipline, or fresh-context subagents, and they serve the implementation step well.

## Install

```
/plugin marketplace add mzorec/ctdd
/plugin install ctdd
```

From a local clone (e.g. while developing the plugin), point the marketplace at the checkout directory instead:

```
/plugin marketplace add /path/to/ctdd
/plugin install ctdd
```

The skills also work standalone without the plugin: copy `skills/*` into `.claude/skills/` in a project, or `~/.claude/skills/` for every project. The scripts are plain Python 3 with no dependencies beyond PyYAML (`gen-authz-matrix.py` only) — on Windows, invoke them with `python` or `py` where the docs say `python3`.

## Adopting CTDD from zero

The rationale is honest that the marginal cost is low only if the artifacts already exist. If they don't, adopt in this order — each rung pays for itself before the next:

1. **Behavior-level test naming** — costs nothing but discipline; makes the suite readable as a spec at all.
2. **Contract validation in CI** — request/response validation against the OpenAPI/protobuf definition; the contract stops being prose in YAML.
3. **Enable the spec-edit hook, contract-only at minimum** — the method's one mechanical reminder; copy `hooks.json.example` into place, and if test-edit reminders feel noisy, override `CTDD_TEST_PATTERNS` down and keep the contract branch.
4. **Consumer-driven contracts (Pact)** — the moment a second service depends on the first; cross-service drift protection nothing else provides.
5. **Property-based tests** — where real invariants live: money, quotas, idempotency, ordering, state machines.
6. **Mutation testing** — critical core only; proves the tests protect the rules they cover.

Stop climbing when the remaining rungs cost more than the failures they'd prevent — a CRUD service with one consumer may never need rung 6.

## Repository layout

```
ctdd/
├── .claude-plugin/plugin.json
├── README.md                          ← you are here
├── CHANGELOG.md
├── docs/
│   ├── ctdd-in-practice.md            ← ten-minute introduction for first-timers
│   └── ctdd-in-depth.md               ← the rationale: full argument, weaknesses, prior art
├── hooks/
│   ├── hooks.json.example             ← copy to hooks.json to enable (off by default)
│   ├── spec-edit-guard.py             ← the spec-edit reminder (PostToolUse + PreToolUse)
│   └── test_spec_edit_guard.py        ← the hook's own test suite (26 cases)
├── scripts/
│   ├── check-plan.py                  ← lints a plan; --diff cross-checks trivial claims
│   ├── test_check_plan.py             ← the linter's own test suite (10 cases)
│   ├── gen-authz-matrix.py            ← identity × operation authz matrix from OpenAPI (--check = CI drift gate)
│   ├── test_gen_authz_matrix.py       ← the generator's own test suite (12 cases)
│   ├── check-spec-surface.py          ← deterministic diff inventory: tests/contracts/ADRs,
│   │                                     renames and deletions included (shares hook patterns)
│   └── test_check_spec_surface.py     ← the classifier's own test suite (11 cases)
├── evals/                             ← trigger eval sets, one per skill
└── skills/
    ├── ctdd-change/
    │   ├── SKILL.md                   ← the change workflow
    │   └── references/adr-template.md ← ADR scaffold
    ├── ctdd-tests/SKILL.md            ← the test craft
    └── ctdd-review/SKILL.md           ← the pre-merge review
```

## Not included (by design)

The customer's business spec (external — the source of intent this plugin consumes, not produces) and any long-lived technical prose spec (CTDD replaces it with contracts, tests, ADRs, and short disposable plans). The design plan is *not* missing — it's a step inside `ctdd-change`, deliberately too lightweight to be its own skill.
