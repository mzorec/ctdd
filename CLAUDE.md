# Working on the CTDD plugin

This repo *is* the CTDD Claude Code plugin. This file is for an agent doing meta-work **on the plugin** — editing skills, scripts, hooks, docs — not for using CTDD on a service. (Using CTDD is what the skills themselves do; the method is in `docs/ctdd-in-practice.md` and `docs/ctdd-in-depth.md`.)

## What this is

A skills-based plugin that brings Contract- and Test-Driven Development to backend work: three skills (`ctdd-change`, `ctdd-tests`, `ctdd-review`), an advisory hook, and four deterministic Python scripts. The skills route and instruct; the scripts are the only mechanical enforcement; CI (a README recipe) is where "when run" becomes "always run." A skill can never *reject* — it can only route. Keep that boundary in mind when someone asks the plugin to "enforce" something.

## Layout

- `skills/{ctdd-change,ctdd-tests,ctdd-review}/SKILL.md` — the three skills. `ctdd-change` owns the change workflow and the plan gate; `ctdd-tests` owns test craft; `ctdd-review` owns spec-level review.
- `scripts/` — `check-spec-surface.py` (diff → tests/contracts/ADRs inventory), `check-plan.py` (plan linter + `--diff` trivial-vs-surface cross-check), `gen-authz-matrix.py` (OpenAPI → authz matrix), `check-redstate.py` (verifies named new tests were observed failing before implementation). Each has a `test_*.py` beside it.
- `hooks/spec-edit-guard.py` (+ `test_`, `hooks.json.example`) — advisory PreToolUse reminder on spec-surface edits.
- `evals/*.json` — trigger cases per skill (incl. pressure scenarios).
- `docs/` — `ctdd-in-practice.md` (first-timers), `ctdd-in-depth.md` (rationale + status pin), `backlog.md` (deferred ideas + triggers).
- `.claude-plugin/{plugin.json,marketplace.json}` — manifest + marketplace entry.

## Non-negotiable rules for changing this repo

**1. Behavior changes ship with tests in the same commit.** This is a hard-learned rule: a `check-plan.py` regex fix once broke a fixture silently because the change had no test. Any edit to a script's behavior updates or adds cases in its `test_*.py`. Run `python3 -m pytest scripts/ hooks/ -q` — it must stay green (currently **92**: 19 check-plan + 24 check-redstate + 11 check-spec-surface + 12 gen-authz + 26 hook — re-count when you add cases; this line has gone stale before).

**2. One definition of "spec surface."** `check-spec-surface.py` holds the test/contract/ADR patterns. `check-plan.py` and the hook import or mirror that one definition (env overrides included) — never fork a second copy. If you touch the patterns, touch them there.

**3. Skill prose is FROZEN (since v0.7.0).** The scarce resource is the agent's *attention across rules*, not word count. New guidance must **displace**, not accumulate. A new skill instruction must argue for its tokens against everything already there, and the bar is "a real-use finding demanded it" — not "a review suggested it." Reviews are an exhausted source; three rounds re-proposed each other's rejections. If you're adding skill prose because it seems tidier, stop.

**4. Deterministic > prompted.** If a check can live in a script (mechanical, testable) instead of skill prose (attention-costly, unenforceable), it goes in the script. The skills point at the scripts; they don't reimplement them.

**5. Grep exact anchors before editing docs.** `docs/ctdd-in-depth.md` is edited between sessions and its wording drifts. Before any `str_replace`, grep the current exact string — do not edit from memory. Verify all anchors across all target files *before* writing any; apply atomically or abort.

**6. This repo is public — never name a client project in it.** The changelog, `docs/pilot-findings.md`, and every doc are MIT-licensed and headed for GitHub. Findings come from real client work, so anonymise as you write: no employer or client names, no service/solution/database/schema names, no domain nouns that identify a sector, no real class, test, or identifier names, no absolute paths, no commit hashes, and no third-party vendor names that would fingerprint the stack. Describe the *shape* — "a list endpoint", "a hand-written projection replaced by a generated one", "a status-filter rule" — which is what makes a finding portable to another reader anyway. If a lesson cannot survive anonymisation, it is a project note, not a finding, and it does not belong here.

**7. Honesty tags are load-bearing.** Unbuilt mechanisms are tagged `(Proposed — not yet built.)`. Rejected ideas are recorded *with their reason* (changelog + `backlog.md` table) so a future round argues with the reasoning instead of re-litigating. Never quietly upgrade a proposal to shipped, or a rejection to open.

## Versioning & release

- **Version bumps only on runtime changes** (skills, scripts, hooks). Docs-only changes collect under `## Unreleased` in `CHANGELOG.md` and fold into the next runtime release. The rationale's status pin dates every doc change already.
- On a runtime release: bump `.claude-plugin/plugin.json`, add a dated CHANGELOG entry (say what changed *and why*, record rejections with reasons), re-pin `docs/ctdd-in-depth.md` ("This appendix describes plugin **vX.Y.Z**…") and re-measure the sizes/eval-counts in that pin if they changed.
- Validate before packaging: pytest green; every `SKILL.md` frontmatter parses as YAML; every JSON manifest/eval parses; in-depth heading anchors resolve. Clean `__pycache__`/`.pytest_cache`. Exclude them from any zip.

## The standing priority

The runtime is frozen pending **pilot data** — real changes run through the loop on a real service, with pre-registered criteria and an annoyance journal. The grade is B+, capped by *Evidence: Incomplete*, and only the pilot moves it. So: the highest-value change to this repo is usually **no change** — resist polishing. A runtime edit is justified when a real-use finding demands it (v0.8.0's file-backed plan output was the first such: the plan gate was too dense to review in a terminal). Backlog items are gated on their named triggers in `docs/backlog.md`; don't build one because it's cheap — build it because the pilot asked.

## Scripts note

Plain Python 3, no deps except PyYAML (`gen-authz-matrix.py` only). On Windows the docs say `python3`; use `python`/`py` or alias it. `.gitattributes` pins LF — keep it, or shebang'd scripts break on CRLF checkouts.
