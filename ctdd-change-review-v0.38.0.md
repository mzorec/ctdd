# `ctdd-change` review — 89 findings, v0.38.0 post-repair pass

**Scope:** `skills/ctdd-change/SKILL.md` (112 lines, 16,325 B) and all seven files in
`skills/ctdd-change/references/` — `plan-format.md` (142 l), `worked-change.md` (91 l),
`execution.md` (41 l), `adr-rules.md` (19 l), `colocated-notes.md` (18 l),
`adr-template.md` (12 l), `rationale.md` (106 l). The four scripts and the hook the skill
invokes were read and executed as evidence, not reviewed as a target in their own right.

**Repo state:** clean working tree at `962d0f7` — **V.0.38.0**, committed 2026-08-21 14:45,
30 minutes before this review began. No diff to review: the whole current content was read.

**This is a re-review after a repair pass.** `962d0f7` is the fix commit for the previous
`ctdd-change` review (`ctdd-change-review-findings.md`, 41 findings, 2026-08-20). Repo
rule 10 — *"a repair pass is where the next defects come from"* — is the standing reason
this pass exists. Findings that the repair introduced, half-applied, or claimed without
delivering are marked **[R]**.

**Method:** 12 independent review angles run in parallel (11 completed; the end-to-end sandbox walk
was lost to a session rate limit and its ground is only partly covered by the others), each blind to the others and
(except the one assigned to it) blind to the previous review, then deduplicated and
verified in one context that had read every target file. Angles: internal contradictions ·
prose-vs-script fidelity (executed) · step-graph executability · destructive & safety ·
command/path/placeholder correctness (executed) · reference-loading contract · routing,
frontmatter & evals · missing capability / new features · cross-skill seams · guard-coverage
audit · repair-pass regression audit · end-to-end dry run in a sandbox repository.

**Evidence convention.** ✅ = reproduced by running a command or by direct file comparison,
with the output recorded in the finding. Unmarked = derived from the file text alone
(a quoted contradiction is still primary-source evidence; an inferred consequence is not).

> **This file is a working artifact, not part of the plugin.** Delete it when the findings
> are dispositioned. Note that `ctdd-change-review-findings.md` — the previous review, which
> carried the same instruction — **was committed** (see `REPO-2`). This repository is public
> (repo rule 6).

---

## Read this before acting

The reviewing session was told to ignore `CLAUDE.md` rule 3 and "The standing priority" so it
could propose freely. **You have not been.** Before changing anything:

- **Rule 3 — skill prose changes need the human's approval. Stop and ask.** Most items here
  touch `SKILL.md` or a reference. Say what each change displaces, what it costs against the
  body and route budgets, and what evidence demanded it — then wait.
- **Rule 1 — behavior changes ship with tests in the same commit.** Every script-side item
  needs cases in the matching `test_*.py`.
- **Rule 4 — deterministic > prompted.** The highest-value items here are the ones that
  convert prose into a checker call, several with no new script — only a flag that already
  exists and is already unit-tested.
- **Rule 8 — a guard can pass without guarding.** After fixing anything a guard covers,
  delete the rule it covers and confirm the guard fails.
- **Rule 9 — when a budget guard fires, displace or decide; never shave.**

### Environment this review ran in — read before reproducing anything

| Fact | Consequence |
|---|---|
| `python3` on PATH is the **Microsoft Store stub**. It prints an install message and runs nothing. | Every command in this file uses `py -3`. This is not cosmetic — see the `python3` findings. |
| **pytest is not installed** (`No module named pytest`) — but `unittest` discovers the suite. | **The suite is green.** `py -3 -m unittest discover -s scripts` → `Ran 288 tests … OK (skipped=1)`; `-s hooks` → `Ran 33 tests … OK`. **321 total, 320 passing, 1 skipped.** `CLAUDE.md` rule 1 claims "**317 passing, 2 skipped**" — close, but not the number this box produces, and pytest would collect ≥ what unittest does, never fewer. Re-count with pytest before trusting either figure (see `CI-1`). |
| Platform is Windows 11 / PowerShell 7, with Git Bash also available. | Shell-portability findings were tested on both. |

**Suggested order:** the URGENT items first — they are the ones that can lose a human's
uncommitted work, record evidence that was never observed, or carry an unapproved change past
the gate. Then the two repo-hygiene items (`REPO-1`, `REPO-2`), which need no rule-3
conversation and no skill edit at all. Then HIGH as one approval conversation, since most of
it is a handful of related seams rather than a list.

---

## Index by severity — 89 findings

| Severity | Count | IDs |
|---|---|---|
| **URGENT** | 14 | `U1`–`U12`, `R1`, `R2` |
| **HIGH** | 33 | `H1`–`H27`, `R3`–`R6`, `REPO-1`, `CI-1` |
| **MEDIUM** | 27 | `M1`–`M21`, `R7`–`R10`, `REPO-2`, `REL-1` |
| **LOW** | 15 | `L1`–`L12`, `R11`, `R12`, `REL-2` |

`U` = urgent findings · `H`/`M`/`L` = high/medium/low · `R` = introduced or left half-applied by the
v0.38.0 repair pass (repo rule 10) · `REPO`/`REL`/`CI` = repository and release hygiene, needing no
skill edit and no rule-3 conversation.

**The four cheapest high-value closes**, all zero-cost against the skill budgets: `U2` (hash raw
bytes, not fence-stripped text), `U4`+`R4` (one predicate swap in `check-plan.py`), `R1` (constrain
the contract directory pattern), and `CI-1` (add CI to a repo that ships a CI recipe and has none).

---

## Repository & release hygiene — `REPO-1` (HIGH), `REPO-2` (MEDIUM), `REL-1` (MEDIUM), `REL-2` (LOW), `CI-1` (HIGH)

These five were established directly, not by a review angle. They need no `SKILL.md` edit and
no rule-3 conversation.

### REPO-1 ✅ Half the repository is a stale, tracked copy of itself — including a second `check-spec-surface.py`
`ctdd/` (39 tracked files)

```
$ git ls-files | wc -l          -> 79
$ git ls-files ctdd/ | wc -l    -> 39      (49% of the repo)
$ cat ctdd/.claude-plugin/plugin.json | grep version   -> "version": "0.37.0"
$ git diff --no-index --stat ctdd/skills/ctdd-change/SKILL.md skills/ctdd-change/SKILL.md
  1 file changed, 13 insertions(+), 13 deletions(-)
$ git diff --no-index --stat ctdd/scripts/check-spec-surface.py scripts/check-spec-surface.py
  1 file changed, 22 insertions(+), 2 deletions(-)
```

A complete v0.37.0 snapshot of the plugin — every skill, every reference, every script, the
hook, the evals, the docs and the CHANGELOG — is committed at `ctdd/`. It was added in
`e7a639b` (v0.37.0, 37 files) and **no CHANGELOG entry, doc, or manifest mentions it**, which
is what makes it accidental rather than deliberate: almost certainly an archive unpacked into
the working tree and committed with everything else.

Three consequences, in order of severity:

1. **It forks the one definition rule 2 exists to protect.** `CLAUDE.md` rule 2 — *"never fork
   a second copy"* — is about `check-spec-surface.py`'s patterns specifically. There is now a
   literal second `check-spec-surface.py`, 22 lines behind the live one. A future session that
   greps for the patterns has a 50% chance of editing the dead copy.
2. **It is staged to ship, though it has not yet.** `marketplace.json` declares `"source": "./"`,
   so the plugin root is the repo root and a package built from HEAD would carry the stale tree.
   Checked against the installed build to be sure: `…\plugins\cache\ctdd\ctdd\0.43.0\ctdd\`
   exists but contains **0 files**, so no consumer has received it *yet*. The next publish from
   HEAD is what changes that.
3. **It poisons search.** Every grep for a rule in this plugin returns two hits with different
   text. This review had to explicitly instruct twelve subagents to ignore `ctdd/` — that
   instruction is the evidence of the cost.

**Fix:** confirm with the author that it is accidental, then `git rm -r ctdd/` and add `ctdd/`
to `.gitignore` if the packaging step unpacks there. **Do not delete without confirming** —
if some packaging flow depends on it, the fix is to gitignore rather than remove.

### REPO-2 ✅ The previous review was committed to a public repository, against its own instruction
`ctdd-change-review-findings.md` (tracked, 41,035 B)

```
$ git ls-files --error-unmatch ctdd-change-review-findings.md
ctdd-change-review-findings.md
```

The file is tracked. Its sibling `ctdd-tests-review-findings.md` (untracked) carries the
banner *"This file is untracked and not part of the plugin. Delete it when the findings are
dispositioned. Do not commit it — repo rule 6 (this repo is public)."* The `ctdd-change` one
was committed anyway.

This matters beyond tidiness: repo rule 6 governs what may appear in a public repo, and a
41 KB working review is exactly the artifact most likely to carry unfiltered detail. It also
means the v0.38.0 commit shipped a document listing 41 unfixed defects alongside the release
that fixed some of them, with no marker saying which.

**Fix:** decide deliberately. Either (a) `git rm --cached` both review files and add
`*-review-*.md` to `.gitignore`, or (b) keep them as a deliberate public record and add the
banner + a dispositioned/not-dispositioned marker per finding. Silence is the one option that
is wrong, because the next reader cannot tell which findings are live.

### REL-1 ✅ The status pin in `docs/ctdd-in-depth.md` is fourteen releases stale, and its measurements are 18–28% low
`docs/ctdd-in-depth.md:463`

> "This appendix describes plugin **v0.24.0** (2026-07-27)."

The repo is at **v0.38.0**. `CLAUDE.md`'s release rule requires: *"re-pin `docs/ctdd-in-depth.md`
… and re-measure the sizes/eval-counts in that pin if they changed."* `962d0f7` touched no file
under `docs/`.

Measured now, at the pin's own ≈4 chars/token convention:

| Pinned figure | Pin says | Actual (v0.38.0) | Drift |
|---|---|---|---|
| `ctdd-change` body | ≈3.2k tok | 16,325 B = **≈4,081 tok** | +28% |
| references unconditionally loaded on a plan-gated route | ≈6.0k tok | 28,524 B = **≈7,131 tok** | +19% |
| `ctdd-change` references in total | ≈9.2k tok | 43,342 B = **≈10,836 tok** | +18% |

The pin's closing clause is the finding's own argument: *"a runtime description that overstates
its runtime would be doc-to-code drift in a document about doc-to-code drift."* It does, and
it is.

**Fix:** re-pin to v0.38.0 with the measured numbers above. Then make it mechanical — see the
`--measure` proposal in the feature section; a hand-maintained measurement in a document about
drift will drift again, and this is the fourteenth release proving it.

### REL-2 ✅ The pin sentence is syntactically broken, and one parenthetical is duplicated
`docs/ctdd-in-depth.md:463`

> "**Status pin (re-measure on every release.** (What shipped when is the changelog's job, and
> unbuilt mechanisms are tagged inline as *(Proposed: not yet built.) not yet built.)*; …"

The bolded parenthesis never closes, `(Proposed: not yet built.)` is immediately followed by a
second `not yet built.`, and the sentence that begins "These numbers are re-measured at every
re-pin" runs into "(quoted anywhere else they'd be stale within two releases." with an unclosed
bracket. The paragraph is unreadable at exactly the place it asks to be trusted.

**Fix:** rewrite the pin as a short block with one fact per line while re-pinning for REL-1.

### CI-1 ✅ The plugin ships a CI recipe for its users and has no CI of its own
`README.md:186–214` (the recipe) vs the repository root (no `.github/`, no `.gitlab-ci.yml`)

```
$ Test-Path .github        -> False
$ Test-Path .gitlab-ci.yml -> False
```

`CLAUDE.md` states the design boundary: *"the scripts are the only mechanical enforcement; CI
(a README recipe) is where 'when run' becomes 'always run.'"* For the plugin's own repository
that second half does not exist. Rule 1 requires `pytest scripts/ hooks/ -q` green at a named
count (**317 passing, 2 skipped** as of `962d0f7`) — and nothing runs it except a human who
remembers to. **On the machine this review ran on, pytest is not installed at all**, so the
count in `CLAUDE.md` was last verified at some unknown point by some unknown run.

The release checklist in `CLAUDE.md` names four more things nothing enforces: every `SKILL.md`
frontmatter parses as YAML, every JSON manifest and eval parses, in-depth heading anchors
resolve, and `__pycache__`/`.pytest_cache` are clean and excluded. `.pytest_cache/` is present
in the working tree right now (gitignored, so harmless — but it is the same class).

**Fix:** add `.github/workflows/ci.yml` running, on push and PR: `pytest scripts/ hooks/ -q`;
a YAML parse of all three `SKILL.md` frontmatters; a JSON parse of every manifest and eval; and
the in-depth anchor resolution check. This is the single highest-leverage change in this review
that touches no skill prose: it converts five hand-checked release rules into one gate, and it
is what would have caught REL-1 fourteen releases ago.

---

---

## Before you fix anything: there is no room

Measured against the repo's own budget guards, at `962d0f7`:

| Budget | Limit | Actual | Headroom |
|---|---|---|---|
| `ctdd-change/SKILL.md` body | `BODY_LIMIT_CHARS = 15_500` | 15,304 | **196 chars** |
| Plan-gated route (body + `worked-change` + `plan-format` + `execution`) | `MAX_PLAN_GATED_METHODOLOGY_CHARS = 43_700` | 43,645 | **55 chars** |
| Survival-probe offset | `MAX_PROBE_OFFSET_CHARS = 13_500` | last probe at 8,823 | comfortable |

**The body affords roughly one sentence across this entire review, and the reference route
affords less than one line.** `CLAUDE.md` rule 9 forbids shaving to fit, so almost every prose
fix below is a *decision*, not an edit. That is why the fixes are engineered script-side
wherever they possibly can be: **the majority cost zero characters of skill budget.**

Read the severity groups with that in mind. A finding rated URGENT whose fix lives in a script
is cheaper to close than a LOW one whose fix needs a sentence.

---

## URGENT — 12 items
*Can destroy uncommitted human work, record evidence that was never observed, or carry an
unapproved change past the gate while every checker reports clean.*

### U1 ✅ The Approval record exists only on `stdout`, so 8.6's `--approval <approval-path>` can never succeed — and the cheapest way out is to forge one
`SKILL.md:102` · `SKILL.md:38` · `check-plan.py:625-652` — found independently by five of the twelve angles

> 8.6 — "re-run `check-plan.py <plan-path> --approval <approval-path>`, return to step 6, and resume at the lowest invalidated step **only after that reports the new revision approved**."

> Output contract — "| Approval record | `stdout` | `Approved by: <human message quoted>; plan: <plan-dir>/<name>.md@<checker revision>.` |"

`<approval-path>` occurs **exactly once in the entire skill** — in this command — and is defined
nowhere. No substep of step 6 writes a file: 6.1 prints, 6.2 copies, 6.3 stops, 6.4 excludes,
6.5 interprets. The checker treats the argument as a real file and fails closed:

```
$ py -3 scripts/check-plan.py <plan> --approval ./no-such-approval.txt
check-plan: NO APPROVAL RECORD at ./no-such-approval.txt: [Errno 2] No such file or directory
Write it at step 6 with the plan revision this checker prints; without it a resumed
session cannot establish that 6.4 was satisfied without inferring approval from artifacts.
exit=1
```

The script's own remediation text instructs step 6 to write a file that no step-6 substep writes.
8.6 permits resumption *only* on "reports the new revision approved", which exit 1 never says. So
the amendment path — the sole escape from an approved specification that turns out to be wrong —
**deadlocks with the implementation already half-written.** Step 7 cannot be re-entered (its Enter
needs step 6's record) and step 9 cannot be reached.

**Why URGENT rather than HIGH:** the deadlock has one cheap exit, and it is fabrication. The agent
writes the file itself containing `Approved by: "Approved."; plan: …@<the digest the checker just
printed>`. Verified: after hand-creating a file in exactly the Output-contract shape, the same
command prints **`check-plan: approval record verified for revision feb1190694a4.` exit=0.** The
accept criteria (`check-plan.py:634-652`) are `@<12-hex>` matching the digest and
`Approved by:\s*\S` — both typeable from memory. That line is then copied into the packet, and a
human reads machine-verified approval of a record the agent authored. `check-plan.py:618-623` names
this exact hole in a code comment; the skill never grew the substep.

Compounding: `--approval` is **not in `--help`** (which lists only `--diff` and
`--from-description`), so the agent's natural recovery — read the help — cannot recover the
contract either.

**Fix — three parts.** (a) Add `check-plan.py --record-approval "<human message>"`: it computes the
digest itself, refuses to write over a plan failing any section check, and writes
`<plan-path minus .md>.approval.md`. Make `--approval` take no argument and derive the same path.
(b) Amend the line-46 write freeze to "the only files you write are the step 5 plan file and the
step 6 Approval record", or the new write is itself frozen. (c) **Stop overclaiming**: change
`check-plan.py:652` to `approval record attested for revision {want} — the record is agent-written
and not independently verifiable; the digest match shows only that the plan is unchanged since the
record was written.` Document both flags in `__doc__`. Body cost ≈ +58 of 196 chars.

### U2 ✅ The plan-revision digest is blind to any edit inside a fenced block
`check-plan.py:458` → `:634`, `:809`

The digest is the entire mechanism binding an approval to one plan revision. It is computed over
the **fence-stripped** text, and `strip_fences` blanks every line inside a ``` block:

```
$ py -3 digest_probe.py     # edits only the Verification commands, inside a fence
  as check-plan.py computes it (strip_fences first):
    before = 769f170ed25f   after = 769f170ed25f   -> SAME - EDIT INVISIBLE
  over raw bytes (the fix):
    before = b8b74e48343b   after = aecff00b6bc4   -> DIFFERS - edit detected
```

Change `dotnet test --filter CaptureTests` to `dotnet test --filter NothingAtAll` inside a fence
after approval and `--approval` still reports the plan unchanged; `APPROVAL STALE` never fires.

**The trigger is ordinary, not exotic.** `plan-format.md` displays the skeleton, the complete
example, the `Verification` list and the `Hold-out` block fenced, so a plan written by copying it
carries fenced content by construction. And 8.6 says "amend the plan file with the old and new
form" — quoting an old form in a fence is the natural way to do that, and `strip_fences`'s own
docstring says quoted material inside a fence is *supposed* to be inert.

**Fix:** hash the raw bytes. Keep `strip_fences` for the pattern matching it was written for, but
compute the digest at `:634` and `:809` from `_read(plan_src)` directly. Add a `test_check_plan.py`
case that edits only fenced content and asserts the digest changes — then, per repo rule 8, revert
the fix and confirm the new test fails. **Cost: zero skill budget.**

### U3 ✅ `execution.md` orders the agent to `revert` files it never backed up, and the alternative it offers is unreachable
`execution.md:24` · triggered from `SKILL.md:85-86`

> "| A target file changed outside the approved plan (7.2) | Stop. Name the files. **Revert them**, or amend under 8.6 and re-approve; 7.2 does not self-clear. |"

7.1 is "Re-check the working tree against step 0", so 7.2 fires precisely on changes **the agent did
not make** — concurrent human edits. The remedy names no target state, and **nothing in the workflow
ever creates one**: step 0 emits `staged=<summary>; unstaged=<summary>; untracked=<summary>` to
stdout as prose (`SKILL.md:32`). That is a statement, not a snapshot. No `git stash create`, no
`git diff HEAD > .patch`, no copy.

The only concrete verb on offer is "revert", and the commands that implement it —
`git checkout -- <file>`, `git restore <file>` — discard working-tree changes that were **never
objects in the object database**. No reflog entry, no dangling blob, no `git fsck` recovery.
Uncommitted human work is gone permanently, and the agent reports it as compliance with a
break-point rule.

**The escape hatch is also broken.** "amend under 8.6" is unreachable from step 7: 8.6 lives inside
step 8, whose Enter requires "step 7 satisfied every applicable evidence lane" — and 7.2 fires
*before* 7.3-7.11 run. 8.6's trigger list is closed to three items and an out-of-plan file edit is
none of them. **The row offers one action that destroys data and one that cannot be taken.**

**Fix:** delete "Revert them," from the row, leaving "Stop. Name the files. Return to step 6 with the
plan updated to cover them, and re-enter step 7 from 7.1 after a new Approval record." Add to the
unordered guardrails: *"Never run `git checkout --`, `git restore`, `git reset`, `git stash`, or
`git clean` on a working tree you did not create."* Deterministic backstop: have step 0 write
`<plan-dir>/<name>.baseline.patch` from `git diff HEAD` plus the untracked list, and make that
restore point a named field in the packet.

### U4 ✅ A prose bullet in an evidence lane passes the plan gate, makes step 8 unenterable, and the packet still renders clean
`SKILL.md:96` · `check-plan.py:238-245` vs `check-redstate.py:387` · `execution.md:40`

`check-plan.py`'s `_bullet_names_a_test` accepts **any identifier-shaped first token** on a bullet.
`check-redstate.py`'s extractor rejects prose. The gate and the evidence lanes therefore disagree
about what "names a test" means.

Reproduced end-to-end on *"extract the fee calculation into a domain service; no behavior change"*
in an untested area. The plan writes `Preservation pins: none — the area has no tests today.` and
one bullet under `New-behavior tests`: `- covered by the existing suite; this change adds no
behavior.`

- `check-plan.py` → **exit 0**, "all mandatory sections present for a medium plan". Gate passes.
- 7.4 and 7.8 both see "no test named" → 7.5-7.11 all skipped.
- Step 8's Enter demands "at least one lane named a test"; 3.6 did not fire → **no legal entry to step 8**.
- Run the lanes anyway and both exit 2 ("contributed no test names" / "no preservation-pin names found").
- `execution.md:40` then licenses `Red state: n/a — plan declares none` and `Pin state before/after:
  n/a — plan declares none`, so **the step 9 packet looks entirely normal on a change that produced
  zero test evidence.**

The inversion is the sharp part: the *honest* form `New-behavior tests: none — <reason>` is
**rejected** (exit 1, `NO EVIDENCE LANE`), while the vague bullet passes. That is exactly the failure
`_names_a_test`'s own docstring says it was written to close — *"the guard was defeated by deleting a
word, and the agent that noticed was rewarded for the less honest plan"* — reintroduced one layer up,
now rewarding the *vaguer* plan instead.

**Fix (script-side, so the two cannot drift again):** in `check-plan.py`, replace `_BULLET_NAME` /
`_bullet_names_a_test` with a call into `check-redstate.py`'s extractor, loaded the way
`_load_surface()` already loads the shared surface classifier. A bullet counts only if
`names_from_plan` would parse it; any bullet it would drop fails the plan at 5.4 with the message
`check-redstate` already prints. This is repo rule 2's "one definition" applied to the second thing
the two scripts both need to agree on. **Cost: zero skill budget.**

### U5 ✅ Nineteen literal `python3` invocations, and the one-line fallback reaches none of the reference files
`SKILL.md:12` (the warning) · commands at `SKILL.md:61,76,90,94,100,102`, `execution.md:33,38,39,41`, `worked-change.md:43,72,81,98`, `adr-rules.md:8`

> "`python3` on PATH is a dead stub on many Windows installs; fall back to `py -3` or the full `python.exe` path."

Counted with `grep -o` (occurrences, not lines): **`python3` appears 20 times across 4 files** —
`SKILL.md` 9, `execution.md` 6, `worked-change.md` 4, `adr-rules.md` 1. One is the warning itself,
leaving **19 literal invocations**. `py -3` appears **once**, in the warning. **Zero times in any
reference file.**

```
PS> python3 --version    ->  "Python was not found; run without arguments to install from the
                              Microsoft Store..."      $LASTEXITCODE = 9009
bash$ python3 --version  ->  same message, exit 49
```

The warning is prose at line 12 of a 112-line file, 50-90 lines above the step 7/8/9 commands, and no
instruction anywhere says *substitute the working interpreter into every command below*. A reference
loaded fresh at step 9.3 — which `SKILL.md:106` mandates, "Read `references/execution.md` now even if
read earlier" — hands the agent six more `python3` commands with the warning nowhere in sight.

Under `SKILL.md:113` / `execution.md:23`, exit 49 is "a checker that cannot run", which resolves to
`NOT RUN — <reason>` in the packet. **So on Windows the entire deterministic enforcement layer —
plan lint, red state, pin state, spec surface, approval — resolves to `NOT RUN` while the workflow
completes and emits a review packet.** `docs/backlog.md:160` records the pilot hitting exactly this,
twice.

**Fix:** a step 0.0 that probes once — try `python3`, then `py -3`, then `python`; record the first
that prints a path as `PY`; stop and ask if none does; every command below that shows `python3` runs
under `PY`. Then replace all 19 tokens with `<PY>`. Better: ship `scripts/ctdd` + `scripts/ctdd.cmd`
launcher shims and spell every command `"<PLUGIN>/scripts/ctdd" check-plan …`. **The repo already
solved this once** — `hooks/hooks.windows.json.example` uses `py -3` — the skill prose never received
the same treatment.

### U6 ✅ `${CLAUDE_PLUGIN_ROOT}` is substituted in `SKILL.md` and **not** in reference files, and `${VAR}` does not expand in PowerShell at all
`execution.md:33,38,39,41` · `worked-change.md:43,72,73,74,81,82,83,98` · `adr-rules.md:8,10`

Two independent breakages that land on the same commands, and the one most likely to be waved off as
already-fixed.

**(a) References are never substituted.** The harness *does* substitute the placeholder in
`SKILL.md` — a skill-load probe returned a fully resolved
`C:/Users/…/plugins/cache/ctdd/ctdd/0.43.0/scripts/check-spec-surface.py`. Reference files are
delivered by the **Read tool as raw bytes** and are substituted by nothing. Confirmed against the
live installed plugin, not just the working tree: **16 occurrences of `${CLAUDE_` remain in the
installed `references/`.**

**(b) PowerShell cannot expand it even when set.** `${NAME}` in PowerShell reads the *PowerShell
variable* namespace, not the environment; environment variables require `$env:NAME`.

```
PS> $env:CLAUDE_PLUGIN_ROOT = "C:\_Git\ctdd"       # correctly set
PS> py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" <plan>
    python.exe: can't open file 'C:\scripts\check-plan.py'                       exit 2
    # what the shell actually passed: '/scripts/check-plan.py'
PS> py -3 "$env:CLAUDE_PLUGIN_ROOT/scripts/check-plan.py" <plan>
    check-plan: all mandatory sections present for a large plan (19 of 19...)    exit 0
bash$ py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" --plan-dir
    can't open file 'C:\Program Files\Git\scripts\check-plan.py'                 exit 2
```

The variable is also simply not exported to the shell (`env | grep CLAUDE` lists 20 `CLAUDE*` vars;
these two are not among them). **Neither shell errors on the empty expansion** — both produce a
plausible-looking wrong path, so the failure arrives as "checker unavailable" rather than
"misconfiguration".

Combined with U5 and H21's `<` parse error, the single command at `execution.md:38` has **three
independent reasons to fail on Windows**, and the packet records all of it as `NOT RUN`.

**Fix:** references cannot rely on harness substitution — replace all 12 `${CLAUDE_PLUGIN_ROOT}` and
5 `${CLAUDE_PROJECT_DIR}` uses under `references/` with resolved tokens (`<PLUGIN>`, `<PROJECT>`)
established by the step 0.0 probe. Add a guard `test_no_unsubstituted_placeholder_in_references`
asserting `${CLAUDE_` appears **zero** times under `skills/*/references/`.
**Note for whoever writes it:** `docs/pilot-findings.md:206` records this as fixed and verified
"anywhere it appears in skill content" — true of `SKILL.md`, false of anything the Read tool
delivers. The earlier fix was correct and incomplete.

### U7 ✅ `worked-change.md` restores the self-dispatch 9.4 forbids, and the guard written to prevent exactly this reads only `SKILL.md`
`worked-change.md:135` ↔ `SKILL.md:107` · guard at `scripts/test_check_spec_surface.py:830-842`

> 9.4 — "Stop and hand the `ctdd-review` verdict to the human: name the final diff and wait. **Never load `ctdd-review` here, and never dispatch it yourself unless asked** — a review this session commissions and frames is not independent, whichever context runs it."

> `worked-change.md`, final line — "**`ctdd-review` is then invoked on the final diff.** Its verdict is not written here."

`worked-change.md` is the *copy these shapes* file, loaded at step 4.1 and resident for the whole
change. Its closing line states unconditionally that `ctdd-review` **is invoked** — and the guard's
own docstring records that this precise failure already occurred: *"On 2026-07-30 the agent loaded
ctdd-review into its own session and issued the verdict on its own diff."*

The guard written to prevent the recurrence asserts
`assertNotIn("Invoke \`ctdd-review\` on the final diff", t)` against **`ctdd-change/SKILL.md` only**.
It never opens `references/`. This is `CLAUDE.md` rule 8 stated exactly — *a guard that passes
without guarding* — living inside the guard set that covers this skill, protecting against a
recurrence that has already partially recurred in the file the guard does not read.

**Fix:** rewrite `worked-change.md:135` to mirror 9.4 — *"The final diff is named and handed to the
human for an independent `ctdd-review`; nothing is dispatched from here, and its verdict is not
written here."* Widen the guard to glob `skills/ctdd-change/**/*.md`. Per rule 8: after widening it,
restore the old sentence and confirm the guard fails.

### U8 ✅ The trivial lane is gated on "you did not write it", which the agent cannot observe — so it can route its own change through the no-plan, no-approval lane
`SKILL.md:60-64`

> 3.2 — "Require a diff that already exists against `diff-base`, **that you did not write in this session**, and that contains the complete requested change"
> 3.6 — "Print the Trivial-risk declaration, add it to the PR/MR description, and **go to step 8**."

Authorship is the load-bearing precondition of the entire trivial lane — the lane that skips the
plan, the gate, and every evidence log — and **nothing checks it**. `check-spec-surface.py --git`
sees the diff and cannot tell who produced it. `check-plan.py --diff` contradicts a trivial claim
only when a **test/contract/ADR** path is touched (`check-plan.py:530`); a production-code-only diff
is invisible to both.

Two ways in. **(a)** The agent, a prior session, or a `ctdd-tests` subagent already edited the
production file, and at 3.2 the agent asserts the diff pre-existed. **(b)** More mundane and more
likely: after context compaction or a `/resume`, the agent genuinely **cannot** establish what it
wrote — git shows the diff, never its author-of-record, and "session" is itself undefined (harness
session? conversation? turn?). 3.1 requires *every* condition in 3.2-3.5 to hold, and nothing tells
the agent which way to fail when one is unknowable.

Either way 3.3 exits 0 with "no test/contract/ADR surface touched", 3.4-3.5 are judgment calls the
agent makes about its own work, 3.6 fires, and it jumps to step 8. The change reaches the packet as
`Plan: n/a — trivial`, `Approval: n/a — trivial` — fully conformant, **no plan, no human approval,
production code shipped**. The guardrail at `SKILL.md:28` ("Do not approve your own plan") is
satisfied on a technicality: there is no plan to approve.

**Fix:** make provenance mechanical instead of attested. Require the trivial lane to name a commit
range whose commits predate the session (`git log --format='%H %aI %an' <diff-base>..HEAD`) and
refuse the lane for **any uncommitted working-tree change** — the agent's own edits are exactly the
uncommitted ones. Encode it as `--trivial-provenance` in `check-plan.py`, exiting 1 when the declared
diff includes uncommitted paths. Rewrite 3.2 to end: *"when you cannot establish it, the change is
plan-gated."*

### U9 ✅ An approved contract change that was never written reads as "no spec surface touched" in the packet
`SKILL.md:100-102` (8.4/8.5/8.6) · `execution.md:41`, `:45` · `check-spec-surface.py:483-495`, `:555-561`

Three gaps compound into one false clearance. With a plan naming four files and a diff touching none
of them:

```
$ py -3 check-spec-surface.py --git HEAD --plan <plan>
Planned but untouched:
  - pacts/checkout-web-payments.json
  - payments/contract/openapi.yaml
  - payments/domain/CaptureService.cs
  - tests/payments/CaptureTests.cs
  An approved change that never reaches its file does not ship. Report-only: this does not
  change the verdict.
Other files touched: 1

Verdict: no test/contract/ADR surface touched. ...
exit=0
```

**(a)** The deficit is report-only, and the script's own source comment concedes *"The deficit is
unhandled"*. `SKILL.md`'s only stop condition is 8.6's "when 8.5 **exceeds** the plan" — nothing
fires on *falls short of* the plan.
**(b)** The verdict string emitted is **byte-identical** to the one `SKILL.md:61` uses as the
**trivial-lane precondition**.
**(c)** `execution.md:41` re-runs spec-surface at packet time **without `--plan`**, so the
"Planned but untouched" block is never even computed for the packet, and `execution.md:45` specifies
only `<Verdict line>`.

Net: plan approved with a contract delta, agent implements the handler and forgets `openapi.yaml`,
8.4 exits 0, 8.5 finds nothing exceeding, and the packet handed to the human reads
**`Spec surface: Verdict: no test/contract/ADR surface touched.`** for a change whose approved
contract never moved. The human approves it.

**Fix:** add a stop to 8.5 — *"Stop when 8.4 reports `Planned but untouched`: an approved artifact
that was never written did not ship."* Change `execution.md:41` to re-run **with**
`--plan <plan-path>`, and `execution.md:45`'s field to
`Spec surface: <Verdict line + any Planned-but-untouched block>`.

### U10 ✅ `--post-approval` is the only check for "approved while still asking a BLOCKING question", no step invokes it, and the guard asserting every flag is invoked is a substring test a narrative sentence satisfies
`worked-change.md:65` · `SKILL.md` step 6 (78-83) · `execution.md:38` · guard at `scripts/test_check_spec_surface.py:1247`

The flag works, and it catches a real defect. On the canonical example, which carries an open
`BLOCKING — I will not guess` and no `Decisions confirmed in session`:

```
$ py -3 check-plan.py <canonical-plan> --post-approval
check-plan: UNANSWERED BLOCKING AT APPROVAL — the plan still asks a question and records
no `Decisions confirmed in session`.
exit=1
$ py -3 check-plan.py <canonical-plan>
check-plan: all mandatory sections present for a large plan (19 of 19...)
exit=0
```

Every `check-plan.py` invocation the skill actually orders: 3.3 `--diff`, 5.4 `--plan-dir`, 5.4
positional, 8.6 `--approval`, `execution.md:38` positional. **`--post-approval` appears in no ordered
step.** Its sole mention anywhere is `worked-change.md:65` — *"…and `check-plan.py --post-approval`
must exit 0"* — a description of a property, in a file loaded at step 4.1, *before the plan exists*,
described by its own header as shapes to copy rather than a command list.

**And the guard is the rule-8 instance.** `test_every_checker_flag_is_invoked_by_some_step`
concatenates `SKILL.md` + `references/*.md` and asserts `assertIn(flag, surfaces, f"{flag} is
implemented but no step invokes it")`. That is a **substring** test, and the narrative sentence
satisfies it. Apply rule 8's own procedure — delete the rule the guard covers and confirm it fails —
and it cannot be done, because there is no invocation to delete. The guard has been green the whole
time over a flag nothing calls.

Consequence: human types "Approved." over an open BLOCKING question, 6.4 is satisfied (an affirmative
human message), and step 7 begins with the agent obliged to guess the one thing the section titled
*"BLOCKING — I will not guess"* said it would not.

**Fix.** (a) Fold the check into `--record-approval` (U1) so it **refuses to write the record** on an
open BLOCKING — the only path to an approval record then runs through it, and no new prose is needed.
(b) Replace the guard: assert the flag appears inside a **backticked command line the skill orders** —
regex `` `[^`]*check-(plan|redstate|spec-surface)\.py[^`]*<flag>`` on a line also carrying an
imperative (`Run`, `Re-run`, `Verify`, `cross-check`) — and add a rule-8 negative case asserting the
guard **fails** when an invocation is replaced by a bare mention. (c) Document the flag in `--help`.
**Cost: zero skill budget.**

### U11 ✅ The guard against stranding rules in `rationale.md` runs **zero** assertions for `ctdd-change`, and passes any rule even when it does run
`scripts/test_check_spec_surface.py:883` (loop 902-912, assertion 913-916)

```python
if not _re.match(r"(Never|Always|Do not|Stop|Require|Record|Report|"
                 r"Verify|Write|Invoke|Name|Treat)\b", s):
    continue
key = " ".join(_re.findall(r"[a-z]{5,}", s.lower())[:4])
self.assertTrue(all(w in elsewhere.lower() for w in key.split()), ...)
```

The guard's own docstring names the risk: *"a rule moved into `ctdd-change/references/rationale.md`
… is a rule no agent executing the steps ever reads."* Measured:

```
ctdd-change: 0 lines enter the assertion
ctdd-tests:  0
ctdd-review: 1
```

**Two vacuities stacked.** (a) `ctdd-change/references/rationale.md` is written entirely in
declarative bullets — *"The API contract and tests precede…"*, *"A checker verdict matters
because…"* — so nothing matches the imperative-verb anchor and **the loop body never executes for
the skill the guard was written for**. (b) Even on the one line that does iterate, `key` is four
common words checked as bare substrings against ~40 KB of concatenated prose. Four fabricated,
genuinely-absent rules were tested and **all four left the guard green**.

Move any load-bearing rule into `rationale.md` in that file's own house style — *"An approval must
name the plan revision, because a record without one cannot be told from a stale one."* — and the
guard iterates zero times, stays green, and the rule is unreachable by every agent, because
`SKILL.md:12` forbids loading the file.

**Fix:** delete the imperative-verb filter (it is what makes the guard form-dependent), assert the
candidate list is **non-empty for the skill under test**, and match the whole normalised clause
rather than four scattered words.

### U12 ✅ The body is 303 characters past the compaction proxy, and the rule that decides whether step 8 may run at all sits in the unprotected tail with no guard
`test_check_spec_surface.py:343`, `:491`, `:669-683` · rule at `SKILL.md:113`

```
body = 15,303 chars (16,291 raw - 988 frontmatter)
body[15000:] = 303 chars, beginning: "**weakened green**. Only pin pass and intended red
                                      authorize step 8..."
any MUST_SURVIVE probe inside that tail? False
```

`grep -rF` across all five test files for `"Only pin pass and intended red"`,
`"weakened green"`, `"Classify every run"`, `"leaves its claim unverified"`, and
`"Evidence and break points"` → **zero matches each**. The entire section is 472 chars starting at
offset 14,831; 303 of them fall outside the proxy, and **no assertion protects any of it**.

Three compounding failures:

1. The raise to `BODY_LIMIT_CHARS = 15_500` is justified in-file as *"acceptable only while the
   probe list covers everything load-bearing"*. That precondition is now false — the gate deciding
   whether step 8 may run is in the unprotected tail.
2. The probe test's own comment justifies its presence-form as *"structurally unreachable"* because
   *"the body is smaller than the proxy, so the head slice IS the whole body."* That precondition
   inverted too (15,303 > 15,000) and nobody noticed.
3. `MINIMUM_MARGIN_CHARS = 300` appears **only inside the f-string failure message** — two grep
   hits, the definition and the message. The comment above says *"A boundary test is not a margin
   test… Reserve the space explicitly"*, and then `limit = self.BODY_LIMIT_CHARS` reserves nothing.
   **The guard tells you it enforces a margin it does not enforce.**

**This is live now.** No edit is needed to exploit it: deleting `## Evidence and break points`
outright leaves the suite green.

**Fix:** make the margin real — `limit = self.COMPACTION_PROXY_CHARS - self.MINIMUM_MARGIN_CHARS`
(14,700) — and add two probes: `"Only pin pass and intended red authorize step 8"` and
`"leaves its claim unverified"`. Adding them will immediately fail `MAX_PROBE_OFFSET_CHARS`, which
is the correct outcome and is H1 below.
---

## [R] Regressions introduced or left half-applied by the v0.38.0 repair pass

`CLAUDE.md` rule 10: *"A repair pass is where the next defects come from."* These twelve are the
current instance. Two are URGENT and both were reproduced by execution.

### R1 ✅ URGENT — The new contract patterns classify ordinary source directories, and test files, as contract surface
`hooks/spec-edit-guard.py:63-65` · precedence at `check-spec-surface.py:271-274`

v0.38.0 added `(^|/)(openapi|swagger|asyncapi|schemas?|api-specs?)(/|$)` to the contract patterns.
The segment matches **any** file under such a directory, and `classify()` tests `CONTRACT_PATTERNS`
**before** `TEST_PATTERNS`, so a test file wins the contract label. Reproduced:

```
app/schemas/user.py                        -> contract     <- standard FastAPI/Pydantic layout
tests/schemas/test_user_schema.py          -> contract     <- a test file, labelled contract
tests/openapi/test_routes.py               -> contract     <- a test file, labelled contract
frontend/src/schema/index.ts               -> contract
payments/contract/openapi.yaml             -> contract     (correct)
tests/payments/CaptureTests.cs             -> test         (correct)
```

Three consequences, all live:

1. **In any FastAPI/Pydantic repository, every model file is permanently contract surface** — so 3.3
   can never return "no test/contract/ADR surface touched" and the trivial lane is dead for a pure
   rename under `app/schemas/`. The advisory hook also fires on every such edit, which is the
   "trains the reader to ignore it" failure the repo's own CI comment warns about.
2. **A newly added test under `tests/openapi/` no longer satisfies `check-plan.py:535`'s
   `classify(p) == "test"`**, so it is routed to the wrong lane with the wrong message.
3. The inventory reports it in the wrong bucket, so the packet's `Spec surface:` line and the
   reviewer's read of "which tests changed" are both wrong.

**Rule 1 was also missed here:** `hooks/test_spec_edit_guard.py` was **not touched** by `962d0f7`,
so a hook behavior change shipped with no test in `hooks/`. The only coverage is indirect, via
`scripts/test_check_spec_surface.py`, and it tests none of the above.

**Fix:** constrain the directory pattern to contract-shaped extensions —
`…(/|$).*\.(ya?ml|json|proto|avsc|graphql)$` — and test `TEST_PATTERNS` before `CONTRACT_PATTERNS`
(or return the more specific match). Add the six cases above as fixtures.

### R2 ✅ URGENT — `--plan` reports every planned **production** file as "Planned but untouched", even when the diff just modified it
`check-spec-surface.py:478-495` (esp. 483-485) · consumed at `SKILL.md:100-102`

`seen` is built only from `findings.values()` — the contract and test buckets — plus `unread`
gitlinks. Production files land in the `Other files touched: N` counter, which is **not** in
`findings`. So every non-spec path named in `Files likely to change` is *always* absent from `seen`
and *always* prints under "Planned but untouched", edited or not.

Reproduced on the skill's own canonical plan, with a diff modifying all three named files:

```
Planned but untouched:
  ...
  - payments/domain/CaptureService.cs      <- the file that was just modified
```

**This is what makes U9 dangerous rather than merely wrong.** v0.38.0 rewrote 8.5 from
*"Compare its inventory with `Files likely to change`"* to *"Act on what 8.4 reported"* — delegating
the comparison entirely to a check that emits a **guaranteed false deficit on every run of the
shipped example.** An agent that sees the section cry wolf every time learns to ignore it, and that
is precisely the run on which a real deficit — an approved contract file that was never written —
appears. The new `Colocated notes` section, being a source path harvested by `plan_paths_from`,
inherits the same false alarm.

**Fix:** add the "other files touched" paths to `seen` (keep them out of the surface buckets, but
not out of the comparison). Add a test asserting a planned production file present in the diff does
**not** appear under "Planned but untouched".

### R3 ✅ HIGH — The new ADR cross-check does neither of the two things the CHANGELOG says it does
`check-plan.py:559-574`, nested inside `if TRIVIAL.search(text):` at `:486`

> CHANGELOG v0.38.0: *"so a plan could name a decision record and never write one — or say `ADR: none` while the diff rewrote one. `--diff` now cross-checks both directions."*

Three defects. (a) The whole block sits **inside the trivial-declaration branch**, so on a *plan*
`--diff` does nothing at all. (b) Inside that branch, any ADR path was already appended to `touched`
at `:530` and `return 1` fired at `:553` — so `adr_touched` can never be True and the second
direction is **dead code**. (c) The test asserts only `returncode == 1`, so it passes on the
*earlier* generic message and never executes the line it claims to guard — repo rule 8 again.

Reproduced: canonical plan (`ADR: none`) + diff `M docs/adr/0007-x.md` → *"all mandatory sections
present for a large plan (19 of 19)"*, **exit 0**. And the README CI recipe passes `--diff` with a
plan, so **CI gets zero ADR cross-checking too.**

**Fix:** hoist the check out of the trivial branch; evaluate `adr_touched` before the `touched` early
return; assert on message text, not the exit code.

### R4 ✅ HIGH — `_NOT_A_NAME` is a six-word denylist, and ordinary prose walks straight through it
`check-plan.py:237-245`

The v0.38.0 fix replaced `_BULLET_NAME.match(follow)` with a denylist of six English words
(`none, n, na, tbd, todo, nothing`) rather than a positive test for an identifier shape. Reproduced
via `plan_tier`, with `New-behavior tests: none`:

```
- No existing tests cover this area.        -> tier=small
- Not applicable - nothing to pin.          -> tier=small
- see below                                 -> tier=small
- nil                                       -> tier=small
```

In every case `NO EVIDENCE LANE` does not fire, the plan passes at the **small** tier with both lanes
effectively empty, and step 8's Enter is then unsatisfiable. **This is the mechanism behind U4** —
the guard closed the exact phrase it was shown and left the class open. (`.replace("/", "")` is dead
code: `/` cannot appear in `_BULLET_NAME`'s `[\w.]` capture.)

**Fix:** invert the predicate — require the captured token to *look like* a test identifier (`_`,
`::`, `(`, a path separator, or a `.`-qualified name) instead of avoiding a word list. Add the four
leaking phrases as cases.

### R5 ✅ HIGH — The new setup-error detector cannot see the per-test format the sibling fix in the same commit mandates
`check-redstate.py:162-171`

v0.38.0 added `SETUP_ERROR_RX` anchored to the start of the line. Only pytest's *short-summary* form
(`ERROR path::test - msg`) starts with `ERROR`; in `-v` mode the outcome is at the **end** of the
line, so the anchor never matches and `error` falls through to the FAIL_MARKER path.

Reproduced: a log of `tests/test_capture.py::test_rejects_zero ERROR   [ 50%]` (×2) →
**`all 2 new test(s) observed failing — red state verified`, exit 0** — the exact certification the
fix was written to stop. The same log in short-summary form correctly exits 1.

**Self-defeating:** `execution.md:25` — a row *added by this same commit* — tells the agent
"Re-run with per-test reporting", and per-test reporting is the one format the detector cannot see.

**Fix:** drop the `^` anchor for the `ERROR` alternative and match it as a standalone token anywhere
on the verdict line, with the non-alphanumeric-adjacency rule the FAIL_MARKER logic already uses.
Add a `-v` fixture.

### R6 ✅ HIGH — The hand comparison 8.5 supposedly displaced still runs at packet assembly, without `--plan`
`execution.md:41` · `worked-change.md:112`

8.5 dropped *"Compare its inventory with `Files likely to change`"*, but `execution.md:41` — untouched
— still says exactly that, and re-runs the checker **without `--plan`**. So the same checker is
invoked with two different flag sets in one workflow, and **the run whose output actually reaches the
packet is the one without `--plan`** — the deficit direction never appears in the packet at all. The
budget-guard comment justifying the repair's +100 chars ("net of displacing 8.5's hand comparison,
which `--plan` now does in both directions") is not true of the tree: the hand comparison survives in
two places, and the agent at 9.3 pays the attention cost twice for pre-repair semantics.

### R7 ✅ MEDIUM — The `NOT RUN` prompt requirement landed in `SKILL.md` only; both references still authorize the unilateral escape
`SKILL.md:104` vs `execution.md:29`, `plan-format.md:72`, `:173`

`execution.md:29` still reads *"The required hold-out runner is unavailable | Record `result: NOT RUN
— <reason>` and leave the packet unresolved"* with no prompt, and `plan-format.md:72` still lists the
value with no prompt. **9.3 explicitly orders the agent to re-read `execution.md` at packet time, so
the un-prompted version is the last text it sees.** The canonical example's
`storage: separate repository, unavailable to this session` still establishes unavailability by
construction — the enabler the CHANGELOG itself names. *(This is the same defect as H-tier
`execution.md` vs `SKILL.md` hold-out conflict; recorded here because the repair created the split.)*

### R8 ✅ MEDIUM — `Status: Accepted` at 7.3 collides with rule 15's freeze, strands the standalone route, and dropped a needed branch
`adr-rules.md:11` vs `:19`, `:20`, `:7`

Three losses from one rewrite. (a) 8.6 can fire after 7.3 and resume at 7.3 — but rule 15 now forbids
rewriting the Context/Decision/Consequences of an already-`Accepted` ADR, and rule 16's only escape is
a *new* ADR superseding one that never shipped. (b) The standalone route is now documented as
permanently unfrozen: "the gate is the acceptance" does not hold where there is no gate, so the defect
is enshrined rather than fixed. (c) *"unless the user explicitly supplies another valid status"* was
the only clause admitting `Superseded by NNNN` at write time, which rule 16 and `adr-template.md:3`
both require. **Fix:** write `Proposed` at 7.3, promote at step 9 when no 8.6 is pending, give the
standalone route its own promotion step, restore the user-supplied clause.

### R9 ✅ MEDIUM — The colocated-note repair deleted the escape hatch and supplied no replacement
`colocated-notes.md:9`

The old rule 2 carried one: *"No plan section names one, so the path is not pre-approved: report the
write in the packet as a post-approval spec-surface edit."* The repair replaced it with "a path the
plan's `Colocated notes` section names" — and **deleted the fallback**. No step in 4.x or 5.x asks
the agent to anticipate a note, and `check-plan.py` was never taught the section, so it is neither
required-when-triggered nor path-validated (a plan can name a directory or `TBD` there unchecked).
When 10.2 fires over a plan with no such section, the write the step requires is the write the Output
contract forbids — and the likely resolution is to do it anyway, unreported. **The original defect,
now silent.**

### R10 ✅ MEDIUM — The `Review:` field is set after the packet containing it has been emitted, and is missing from the packet agents copy
`SKILL.md:106-107` · `execution.md:42`, `:45` · `worked-change.md:120-133`

9.3 assembles and `execution.md` step 4 *emits* the packet; the dispatch request ("when asked")
arrives at 9.4, **after** emission. This is the identical ordering defect the same commit fixed for
colocated notes, reintroduced by the fix beside it. And `worked-change.md`'s packet — the shape the
skill orders copied at 4.1 — has no `Review:` line at all. The guard
`test_a_commissioned_review_declares_itself` checks only `SKILL.md` and `execution.md`.

### R11 ✅ LOW — `_adr_patterns()` is recomputed on every `classify()` call
`check-spec-surface.py:81`, `:255-260`

`ADR_PATTERNS = None` carries the comment *"resolved on first use; see `ensure_patterns_loaded()`"* —
but `ensure_patterns_loaded()` only raises on load failure and **never assigns it**. Measured: 20
non-surface `classify()` calls over a synthetic 9,000-file tree = **1.37 s (~68 ms/call)**, each an
`os.walk` of the whole repository. Cost is O(diff paths × repo files), and `check-plan.py --diff`
calls `classify` up to 3× per entry. **Fix:** memoize where the comment already promises it.

### R12 ✅ LOW — `test_a_lane_skip_does_not_swallow_the_other_lanes_skip` under-guards
It only catches a range spanning another skip rule's own number. `Skip 7.5–7.6` — omitting 7.7, the
lane's stop — passes silently.

---

## The v0.38.0 CHANGELOG, audited claim by claim

**Substantiated.** The `NO EVIDENCE LANE` inversion for the *mandated* form (`Preservation pins:
none — <reason>` now derives `large`); `openapi/`-as-directory, `*.schema.json` and Avro as contract
surface (over-broad — R1); the configured ADR directory as ADR surface; fixture `ERROR`s no longer
certifying as intended red **in short-summary form** (format gap — R5); the 7.2 and summary-only-run
break-point rows; 3.2's authorship clause; step 9's conditional stop; the trivial retraction as a
printed correction; the four-command `Verification` example; and the `Known gaps` self-contradiction.
**`Skip 7.5–7.8` → `7.5–7.7` is correct** — 7.8 is the other lane's own skip rule, and the old range
swallowed it.

**Claims that overstate:**

- *"`--diff` now cross-checks both directions"* (ADR field) — **false in both directions** (R3).
- *"Five checker flags were built and invoked by no step… a guard now asserts every flag is reachable."*
  — `--post-approval` is still invoked by no ordered step (U10). Additionally the guard globs
  `references/*.md`, **which includes `rationale.md`** — a file `SKILL.md:12` says never to load during
  a change — so it would pass on a flag mentioned only where the workflow forbids reading.
- *"8.5 compared inventory to plan by hand and in one direction while `--plan` does both"* — the hand
  comparison survives in two places, the packet run omits `--plan`, and `--plan`'s deficit direction is
  wrong for every production path (R2, R6).
- *"`Verification` was the one evidence lane with no artifact… They now save to `<name>.verify.log`."*
  — the log is written and **nothing reads it**; no checker exists for it and the packet's field does
  not cite it, so "`NOT RUN` accepted with nothing to check it against" is unchanged.
- *"Field rule 11 described a transition that could not converge"* — **premise disproved.** The presence
  regex matches the `BLOCKING — I will not guess` *heading*, not the question bullet; deleting the
  bullet and adding `Decisions confirmed in session` exits 0, `--post-approval` included. Worse,
  `check-plan.py:612-614`'s remediation text still says *"Move the answer there and remove the
  question"* — the phrasing the repair deleted as non-convergent — and the new wording ("replace the
  question with `none — answered before approval`") reads as a bullet, which `plan-format.md:11`
  rule 4 forbids.
- *"A duplicate `skills/skills/` tree… shipped in two packages… Removed."* — **unverifiable and not in
  this commit.** No commit in any branch has ever contained a `skills/skills/` path (checked by walking
  every reachable tree). Plausible if the duplicate was untracked, but nothing in the repository
  records it. *(Note the live duplicate that does exist and is tracked: `REPO-1`.)*

**Also:** the CHANGELOG dates v0.38.0 `2026-08-03`, the same date as v0.37.0, while the commit is
dated 2026-08-21.

## HIGH — 27 items

### The budget state is itself a finding

**H1 ✅ `MAX_PROBE_OFFSET_CHARS` has two characters of headroom, and its own measurement comment is 537 chars stale.**
`test_check_spec_surface.py:351`. Last probe (`hold-out blocks review`) sits at offset **13,498** of
a 13,500 ceiling. The comment above the constant reads *"Measured: the last probe sits at 12,961 of
14,660"*; the real figures are 13,498 of 15,303. Adding a 19-char routing bullet moves it to 13,514
and the guard fires. This is not vacuous — it is the one *real* structural constraint in the file,
and it is 99.99% consumed, so the next legitimate correctness fix anywhere before offset 13,498
forces a displace-or-decide with no slack. **Fix:** relocate the hold-out probe earlier (it is the
only probe past 11.5 K; probes 1-5 all sit under 1,500), or record the raise with a real,
dated measurement. Do not raise to fit.

**H2 ✅ The route ratchet has 55 characters left, and the file states the number was set to wherever the content happened to be.**
`test_check_spec_surface.py:606`. `43,645 of 43,700 (99.87%)`. Self-confessed in the comment block:
*"A RATCHET, NOT A BUDGET. No published guidance bounds per-change reference load; this number was
set to wherever the content happened to be, and it has moved five times"* — the block records
**twelve** raises. With 55 chars left it no longer makes growth *a decision*; it fires on the next
one-line repair, and the same comment warns this is exactly when it *"was once used to silently drop
an addition the human had asked for"* (repo rule 9). **Fix:** derive the number from something, or
delete the ratchet — a guard whose only remaining function is to block the next repair is not a guard.

### Commands the agent cannot execute as written

**H3 ✅ 8.6 orders the `--approval` re-run at the one moment it is guaranteed to fail.** `SKILL.md:102`.
The amendment necessarily changes the digest, so the run ordered *between* "amend" and "return to
step 6" can only ever exit 1: `APPROVAL STALE — the record approves revision feb1190694a4, the plan
is now 4f0927e29211.` Under 5.4's standing *"fix every reported failure, and re-run until it exits
0"*, exit 1 reads as a defect to repair — and **the cheapest repair is editing the approval record's
hash to the new revision**, i.e. forging approval for a plan the human never saw amended.
**Fix:** reorder to "amend …, return to step 6 for a new Approval record, *then* run `--approval`."

**H4 ✅ `<declaration-path>` and `<name-status>` have no producer, and the declaration does not exist until three substeps later.** `SKILL.md:61` vs `:33`, `:64`.
Both placeholders occur exactly once in the whole skill. The declaration's only declared homes are
`stdout` and the PR/MR description, and 3.6 — the sole step licensed to emit it — is **downstream**
of the 3.3 gate that consumes it. Nothing tells the agent to produce a name-status file. Verified:
a guessed path gives `check-plan: cannot read --diff …` exit 2, and 3.3 treats exit 2 as plan-gated —
so **the trivial lane's only deterministic cross-check can never legitimately pass.** The realistic
agent behaviour is to drop the cross-check and emit the declaration on `check-spec-surface` alone.
**Fix:** pipe instead of pointing at phantom files — write the name-status to a scratch path, then
`… check-plan.py - --diff <that file>` with the draft declaration on stdin.

**H5 ✅ Angle-bracket placeholders pasted verbatim are a parse error that kills the entire command block.** 10 sites.
`<` is a reserved redirection token in **both** PowerShell (`The '<' operator is reserved for future
use.`) and bash. Because it is a *parse* error, it aborts every other statement batched into the same
call — so the agent sees an error unrelated to what it was checking, and a plausible recovery is to
conclude the checker is broken and hand-verify. **Fix:** one sentence saying angle-bracket tokens are
fill-ins and never shell text, or switch the convention to bare uppercase (`PLAN_PATH`, `RED_LOG`).

**H6 ✅ `worked-change.md`'s backslash line-continuations are bash-only and are a ParserError in PowerShell.** `worked-change.md:72-74`, `:81-83`.
PowerShell's continuation character is a backtick. These two `check-redstate` invocations are the
exemplar of correct evidence verification, in the file the skill orders the agent to copy — and they
carry the `$` prompt marker and 4 of the 5 unsubstituted `${CLAUDE_PROJECT_DIR}` occurrences as well.
Three independent reasons to fail on one line. **Fix:** collapse to single-line commands with
resolved tokens; drop the `$` prefix.

### The step graph

**H7 ✅ Step 10's Enter places it inside step 9; once 9.4 runs it is permanently unenterable.** `SKILL.md:109` vs `:45`, `:107`.
The packet is printed by 9.3, so step 10's window is the gap between 9.3 and 9.4 — contradicting
"Execute steps 0-10 in ascending order" two lines above. And 9.4 is a *terminal wait*, not a
pass-through: an agent obeying ascending order executes 9.4, and "before 9.4" is false forever.
The Colocated note — a row in the Output contract — is never written and nothing reports it as
skipped. If the agent instead interleaves, the packet's spec-surface inventory was computed at 9.3
against a tree that does not yet contain the note. **Fix:** renumber the note as 9.3a, before packet
assembly, and change `:45` to "steps 0-9".

**H8 ✅ "The lowest invalidated step" is never defined, and resolves circularly on the only path that uses it.** `SKILL.md:46`, `:102`.
`grep -rn "invalidated"` returns exactly these two uses and no definition. An 8.6 amendment
demonstrably invalidates **step 6's own output** — `check-plan.py` prints `APPROVAL STALE` for
precisely that case — so "lowest invalidated step" computes to 6, and `:102` reads *"resume at step 6
only after step 6 reports approved."* A→6→A with no exit criterion. The one worked instance sits in
a file whose header says load it only at 4.1, and 8.6 names no reference — so under `:12`'s loading
discipline the agent at 8.6 may not open it. **Fix:** define it — 5 when any plan section changed,
7 when a named test/contract/ADR changed, 8 otherwise; step 6 is always re-executed and is never
itself a resume target.

**H9 ✅ 7.2's Stop routes to 8.6, which is unreachable from step 7 and does not accept 7.2's trigger.** `SKILL.md:86` · `execution.md:24`.
See U3 for the destructive half. The structural half: 7.2 fires before 7.3-7.11, so step 8's Enter is
false and 8.6 lives inside step 8; 8.6's trigger list is closed to three items and an out-of-plan
file edit is none of them. `execution.md` states "7.2 does not self-clear" — correct, and there is no
clearing path. **Fix:** route 7.2 to step 6, not 8.6, and extend 8.6's trigger list.

**H10 ✅ In the trivial lane, step 8's `<plan-path>` and every evidence-log `<name>` have no referent.** `SKILL.md:100`, `:42`, `:101`.
3.6 routes to step 8 with no plan file. `<name>` is defined only as the plan file's stem, so
`<plan-dir>/<name>.verify.log` cannot be constructed, and 8.5's exemption list is explicit and closed
("only 8.3's pin re-run and 8.6 as `n/a`") — so 8.4's `--plan` run and 8.3's log-saving are both
still mandatory in a lane that has neither. Worse, when `--plan` is handed a nonexistent path,
`plan_paths_from` catches `OSError` and **returns `None` silently**: the cross-check is not performed,
no error, no warning, exit 0 — so `execution.md:23`'s "a checker that cannot read its input" never
fires. **Fix:** make `--plan` on an unreadable path exit 2; give the trivial lane a defined log stem;
add 8.4's `--plan` argument to the exemption list.

**H11 ✅ 9.1 is an unconditional stop whose resolution list omits the value the packet expects.** `SKILL.md:103-104` vs `execution.md:45`, `plan-format.md:41`.
The stop condition is "when a plan exists", not "when a hold-out is required", and 9.1's four
resolutions omit `not required` — the fifth value the packet shape declares. A small-tier plan
(`hold-out: not required`, no `Hold-out` section) therefore either triggers a pointless write/decline
round trip, or gets recorded as `NOT RUN`, which both `plan-format.md:72` and `execution.md:29` treat
as an unresolved packet — **blocking a change that had no hold-out obligation.** `SKILL.md:37` also
requires printing "the `Hold-out` block in full" for a plan that has no such block. **Fix:** condition
the stop on the categorical line, and make the gate's hold-out print conditional.

**H12 ✅ 0.4's contamination Stop tests an undefined term and has no clearing condition anywhere.** `SKILL.md:51`, `:47`.
"Target file" is used at 0.4 and 7.2 and defined nowhere; at step 7 it resolves against the plan's
`Files likely to change`, but at step 0 no plan exists, so the test has no operand. `execution.md`'s
break-point table carries a row for 7.2 and **none for 0.4** — no remedy, no resumption, not even a
"does not self-clear" note. And the classification is unfixable in principle: whether a pre-existing
edit is "an intentional review diff" or contamination is a fact about human intent that no tool
reports. Step 1's Enter is satisfied while step 0's Stop is unresolved, so the graph both blocks and
permits advancing. **Fix:** make 0.4 a Decision prompt and treat the human's answer as the definition
of "target file" until step 5 replaces it.

### Cross-skill seams

**H13 ✅ "Invoke `ctdd-tests`" names no mechanism and transmits no payload.** `SKILL.md:89`, `:93` ↔ `ctdd-tests/SKILL.md:21`.
There is no `agents/` directory, no subagent frontmatter, and no statement of whether "invoke" means
a Skill tool call in-context, a subagent dispatch, or "go read that file". The two steps hand over
**nothing**: not the plan path, not the exact test names, not the `case:` types, not the
`expected pre-implementation failure` text, not which lane is running. `ctdd-tests` then re-derives
its own case set from scratch. The gate approved a case set; the delegate wrote a different one, and
only the intersection is ever verified — `check-spec-surface --plan` compares file paths, not test
names. **Fix:** define the payload in 7.5/7.9 ("handing it the plan path, the lane, and that lane's
bullets verbatim; it writes those tests and no others") and add the receiving clause to `ctdd-tests`.

**H14 ✅ Test naming has two owners and no tie-break; the checker turns the disagreement into an unrecoverable step-7 stop.** `plan-format.md:10`, `:78` ↔ `ctdd-tests/SKILL.md:66`.
The plan's exact names are approved by the human and are the **only key** `check-redstate --tests-from`
uses. But naming authority is explicitly delegated to `ctdd-tests`, whose own rule renames toward
observable intent. Neither says which wins. When they differ, 7.10 reports "not found in the log" and
7.11 stops — and the fix requires either renaming (violating the delegate's ownership) or amending the
plan, but the only amendment clause is 8.6, **unreachable from step 7**. **Fix:** state precedence —
the approved name is binding once the gate has run; a rename after approval is a plan amendment — and
give step 7 an explicit amendment pointer.

**H15 ✅ "Implementing its feedback stays here" points at a clause reachable only from inside step 8.** `SKILL.md:15`, `:102` ↔ `ctdd-review/SKILL.md:18`.
`review feedback` appears exactly once in the ordered workflow, inside 8.6. But the normal case is the
opposite: 9.4 ended the session and the review returns in a **new** session with no in-context plan
and no Approval record. 6.4 demands an affirmative human message on *this* plan; a prior session's
approval is not re-derivable; 3.2 excludes the trivial lane because the fix is still to be written.
So the skill's own advertised trigger — "implement the review comments", in the frontmatter — lands on
a workflow with no matching entry, and 8.6's "no new plan" valve is unusable because no plan is in
flight. **Fix:** add a routing clause that re-enters at step 0 with the findings as the change
request, resuming under 8.6 only when the plan and its Approval record are still on disk.

**H16 ✅ The packet's `Review:` field cannot express the outcome the architecture is designed to produce.** `execution.md:45` ↔ `SKILL.md:106-107`.
The value set admits only `n/a` and the self-incriminating `commissioned by the author — independence
not established`. The **designed happy path** — the human takes the diff, runs an independent
`ctdd-review`, and it approves — has no recordable value, so the agent writes `n/a`, which reads
identically to "no review happened". Second defect: the packet is assembled and emitted at 9.3, but
whether a review was commissioned is only established at 9.4, so any non-`n/a` value requires
re-emitting a packet already printed — which no step authorizes. **Fix:** extend the value set with
`independent, run by the human: <verdict>` and resolve the field at 9.4, using the `result: pending`
pattern the `Hold-out` block already uses.

**H17 ✅ "Never write a test file from this skill" has no mechanical backing, and the hook is silent *by design* on the exact event.** `SKILL.md:24` ↔ `hooks/spec-edit-guard.py:11-16`.
The hook's own docstring: *"Write creating a brand-NEW test file -> silent by design"* — which is
precisely what 7.9 produces. It is advisory-only, and `sed -i`/heredoc/`git apply` edits never reach
tool-matched hooks at all. And if "invoke" resolves to a Skill call in the same context — the only
mechanism the plugin ships — then **"from this skill" has no observable referent**: same agent, same
context, same tool call either way. The delegation can be skipped and nothing anywhere can tell.
**Fix:** make the boundary observable rather than asserted — require `ctdd-tests`' convention print in
the packet as `Test conventions: <block or NOT RUN — ctdd-tests not invoked>`, and have `ctdd-review`
treat its absence on a test-surface diff as a finding.

### Reference-loading and the worked example

**H18 ✅ Steps 4.2-4.5 draft the plan's content before `plan-format.md` — which holds the criteria they apply — may be loaded at 5.1.** `SKILL.md:66-73` vs `plan-format.md:6`.
What 4.2-4.5 need and cannot see: the **Required case coverage** table (seven rows deciding *which*
tests 4.5 drafts, plus the column deciding new-behavior vs pin), field rule 2 (the definition of
`contract: breaking`, exactly what 4.4 decides), field rule 5 (the seven domains forcing a hold-out,
feeding 4.2's highest risk), field rule 4, field rule 10, and the per-bullet grammar. **The file
defining the vocabulary of step 4's four drafting substeps is explicitly forbidden until the step
after them.** The agent enumerates cases from its own priors — typically positive and negative,
missing boundary/authorization/side-effect — then either rewrites everything at 5.1 or keeps the
draft and writes `Case coverage not reached` for cases it never considered. **Fix:** move the load to
4.1 alongside `worked-change.md`. **Zero net route chars — same file, read once, where it is used.**

**H19 ✅ `adr-rules.md` is loaded at 4.3 and executed at 7.3, across the approval gate, with no re-read.** `SKILL.md:69`, `:87`.
`SKILL.md:87` is the entire instruction at the point of execution — "Write each approved contract or
ADR artifact to its exact planned path" — and names neither `adr-rules.md` nor `adr-template.md`.
Everything needed at 7.3 sits in the file loaded at 4.3: resolve the directory with `--adr-dir`
("Never assume a path"), match the existing numbering width (`015`, not `0001`), render the template,
set `Status: Accepted`, and write the `ADR-NNNN` markers. Between the two lies **step 6's mandatory
stop for a human message — the workflow's only unbounded wait, and the most likely compaction point.**
Compare `SKILL.md:106`, which explicitly re-reads a 5.4 KB file. **Fix:** append "re-read
`references/adr-rules.md` when writing an ADR" to `:87` (~48 chars; conditional, so it does not enter
the route ratchet).

**H20 ✅ `execution.md`'s break-point table governs six steps; only two of them load it, and the sentence saying the table exists is outside the compaction head.** `execution.md:20-29` · `SKILL.md:113`.
Mapping the seven rows to the step each governs: checker-exits-2 → steps 3 and 5 (**no loader**);
target-file-changed → 7.2 (**no loader**); plan-mode-owns-write-location → 5.2 (**no loader**);
planned-test-difficult → 7.5/7.9 (**no loader**); unrelated-verification-failures → 8.3 (**no
loader**); hold-out-runner-unavailable → 9.1, loader at 9.3, **one substep late**. And the only
sentence telling the agent where the table lives begins at offset **15,145 of a 15,303-char body** —
145 chars past the compaction proxy, covered by no probe. After a long session the pointer that would
prompt a speculative load is gone from the re-attached head. **Fix:** add a loader at 7.2, fold the
8.3 and 7.5 one-clause actions inline, and move `:113`'s sentence ahead of step 9.

**H21 ✅ The plan's `Colocated notes` section must be decided at step 5 from criteria the skill forbids loading until 10.2.** `plan-format.md:34` · `colocated-notes.md:3`, `:9`.
The path must be in a plan written at step 5, from a prediction made at step 5, using rules readable
only at step 10.2 — five steps and one approval gate later. `SKILL.md:111` carries a compressed
trigger but **not the disqualifiers**: rule 9 ("Delete the proposed note when the rule is derivable
from repository code, tests, or contracts") and rule 8 ("Put a time-bound fact in the plan or an ADR
instead"). Both outcomes are bad: omit the section and at 10.2 the note is silently dropped (the
Output contract admits only "A path from the plan's `Colocated notes`", and no step reopens the gate);
include it speculatively and rule 9 may disqualify it, leaving an approved path with nothing written.
**Fix:** move the two disqualifiers into `SKILL.md:110` beside 10.1's existing check.

**H22 ✅ `worked-change.md`'s step-9 packet omits the `Review:` field the declared shape requires.** `worked-change.md:120-133` vs `execution.md:45`.
A programmatic diff of the two field lists: `execution.md` declares 13, the worked example emits 12 —
every one except `Review`. `SKILL.md:67` says "copy its artifact shapes", so an agent reconstructing
the packet from that memory emits 12. **The dropped field is the one whose whole purpose is to
surface that a review the author commissioned is not independent** — so its absence reads as "no
independence concern" rather than "not recorded". **Fix:** add the field (~66 chars), funded from
`worked-change.md:128`, which repeats `:127`'s 181-char verdict string verbatim *and wrongly* — the
"before"-run's text appears on an after-run line. Net change is negative.

**H23 ✅ The worked example prints the Approval record, then edits the plan, leaving a permanently stale digest — and omits the line that says where the digest comes from.** `worked-change.md:43-45`, `:55-65`.
Two defects in one transcript. (a) The step-5 run is shown producing exactly one line; the real run
produces two, and the missing one is `check-plan: plan revision feb1190694a4 — carry it in the
Approval record…` — the only line telling the agent where `@<checker revision>` comes from. The file
then hands it a concrete 12-hex literal at `:62`, so an agent copying the shape emits `@453959650ce8`
and later gets `APPROVAL STALE` for a plan nobody amended. (b) The example prints the record, *then*
mutates the plan (answer in, question out), which changes the hash — so the record it models is stale
the moment it is written. **Fix:** add the revision line to the transcript, replace the literal with
`@<revision the checker printed>`, and reorder so the edit and re-run precede the record.

### Routing

**H24 ✅ "Update the tests to match the new behavior" has no home — the two descriptions bounce it at each other.** `ctdd-change/SKILL.md:7-8` ↔ `ctdd-tests/SKILL.md:10-11`.
`ctdd-tests` names the phrase and pushes it to `ctdd-change`; `ctdd-change` never names it, and its own
reject clause catches it (updating a stale assertion *is* test-only work leaving observable behavior
unchanged — the behavior changed in a prior commit). Its admission clause reads present/future tense.
The loop repeats at body level. Result on *"these tests broke after my refactor — update them to match
the new code"*: `ctdd-tests` marks it `should_trigger:false`, no `ctdd-change` eval covers the neutral
phrasing, and the likely outcome is **neither skill fires and the base agent silently rewrites the
assertion — the single failure mode CTDD exists to prevent.** **Fix:** the load-bearing swap is
`unchanged` → `changes no existing assertion`. Adding a new test changes no existing assertion (→
`ctdd-tests`); editing one does (→ here). A full replacement description that also closes M-tier
routing items is in the angle report; it measures 1,138 chars against a ~1,490 cap.

**H25 ✅ The standalone-ADR lane has no exit condition, so a mixed request bypasses the plan gate entirely.** `SKILL.md:17`.
"Standalone ADR request" is never defined and the bullet has no re-entry clause for a request that also
changes code. On *"write an ADR for moving capture to the outbox pattern, and add the outbox table and
dispatcher while you're at it"*, the ADR lane fires, the agent skips steps 0-10 and **writes production
code with no plan, no gate, and no red-state evidence.** **Fix:** "For a request whose only deliverable
is an ADR… Any code, contract, or test change in the same request voids this lane: run steps 0-10 and
draft the ADR at 4.3."

**H26 ✅ The scope-widening rule that admits non-backend work is invisible to the skill selector.** `SKILL.md:16` vs `:4`.
Selection reads only the description. The description says *backend*; the widener ("Treat testable
state logic as backend-style behavior regardless of deployment tier") lives in the body, never read
unless the skill already fired. `ctdd-review` gets this right — its description carries "testable state
logic remains in scope". `ctdd-change` is the only one of the three whose widener is unreachable at
routing time, so *"the BFF's order-status state machine drops the CANCELLED transition — fix it"*
routes nowhere. **Fix:** move it into the description; delete the body bullet as a duplicate.

**H27 ✅ Behavioral config changes have no trigger phrase, and the eval suite trains "bump" as a negative.** `SKILL.md:4-9` · `evals/ctdd-change-triggers.json:61-63`.
Neither *timeout*, *limit*, *config*, nor *setting* appears in the description, while the reject list
carries "deployment, build-tooling" — which an `appsettings`/`values.yaml` path plausibly matches. Body
step 3.4 says "A changed limit, validation rule, generated file, or file of unknown type is
plan-gated", but that discriminator only exists **after** the skill fires. *"Bump the acquirer HTTP
client timeout from 5s to 30s in appsettings.Production.json"* changes observable failure behavior
under load and routes nowhere. **Fix:** add "bump this limit or timeout" to the trigger list, and add
the discriminating eval pair.

---

## MEDIUM — 21 items

**M1** `worked-change.md` is loaded at 4.1 to serve step 4 and is the one file demonstrating nothing about step 4: steps 0-3 = 20% (already complete), steps 4-5 = 10% (zero plan-body content), steps 6-9 = **48%**, needed after the gate and never re-read. The re-read policy is inverted — the 5.4 KB file says "re-read me", the 7.5 KB file whose examples are needed five steps later says nothing. *Fix: split it, or add a step-9 re-read.*

**M2** `plan-format.md` contradicts itself on whether the summary names the Hold-out — `:3` says "including the hold-out", `:54` says "other than the `Hold-out`" — inside the file that states *"two copies of a rule drift, and the one in this file is the copy nobody checks."* `:54` is operative and the example follows it. *Fix: delete 26 chars from `:3`. Self-funding.*

**M3** Step 5.3 writes the plan "to its exact path" **before** 5.4 resolves what that path is, in a repo where `.ctdd.json` may relocate it. The stray becomes the only pre-approval artifact, and the human may review the wrong copy. *Fix: swap the two substeps. Zero net chars.*

**M4** The same worked change carries **two different Business requirements** across the two example files — `plan-format.md:105` drops the "released remainder is never capturable" clause that four of its own artifacts exist to protect. Back-translation at 9.2 then compares against a requirement missing the clause, and the comparison passes. *Fix: restore the sentence, or delete the duplicated preamble from one file.*

**M5** `Case coverage not reached` is ordered omitted at small and medium tier, while field rule 4 says *"never leave a row unaddressed"* and makes that section the only legal home for an unreached row. A medium-tier change that skips authorization coverage tells the human nothing, and `required_for(tier)` only checks that *allowed* sections are present, so both the omission and a hand-added section pass. *Fix: make the section conditional on an unreached row, not on tier.*

**M6** The gate forbids recommending (`SKILL.md:36`) and requires printing in full two artifacts that both carry a recommendation (`plan-format.md:71`'s `recommended:` line and the BLOCKING "Recommended answer"). Strip them and the hold-out's decision framing is gutted — framing built precisely because bare asks *"have been declined six times"*. Print them and the agent recommends where its voice is excluded. *Fix: scope the exclusion to the approve/reject verdict itself.*

**M7** `colocated-notes.md` names three permitted subjects and supplies exact shapes for two, so a universal invariant with no undefined boundary has no legal shape — the agent writes "…; behavior for `<boundary>` is intentionally undefined" and **asserts a deliberate gap that does not exist**, in a file that outlives the change. The invariant shape also has no provenance slot, so rules 5-6 cannot be satisfied. *Fix: split the shape list into three.*

**M8** 10.2 can fire with no approved path and there is no route to obtain one: the trigger is only evaluable after implementation, 8.6 is over, and "a note turned out to be needed" is not one of its three triggers. *Fix: let 10.2 self-authorize with a visible `Colocated note (unplanned): <path>` packet line.*

**M9** `adr-rules.md` rule 17 orders `ADR-NNNN` comment markers into contract files, and **JSON has no comment syntax** — while `SKILL.md:40` lists JSON Schema and Pact as first-class contract types and `plan-format.md:146` names a `.json` pact as the consumer contract that "runs in CI". Writing `// ADR-0017` into it stops the file parsing, or a lenient parser drops it and the pact silently stops running — destroying the exact "a break fails the build, not production" guarantee the plan sold at the gate. *Fix: exempt comment-less formats; record the link in `Contract changes` instead.*

**M10** `adr-rules.md` rule 5 derives the next ADR number from the local directory with no check that `<dir>/NNNN-*.md` already exists, so a number added on the target branch since `diff-base` collides and 7.3 **overwrites an accepted decision record** that rule 15 forbids rewriting. *Fix: stop if the file exists; consider `--adr-dir --next-number`.*

**M11** Step 10 writes to the tree **after** 9.3 computed the packet's spec-surface inventory and pass claims, so the diff handed over at 9.4 differs from the one the packet describes — and if the note lands beside a contract file it matches the contract patterns, making the packet's "no spec surface touched" false. *Fix: stamp the packet with a tree digest and refuse one that no longer matches.*

**M12** `check-spec-surface --git HEAD` exits 2 on a committed tree ("empty input — nothing was inspected"), and the break-point row enumerates steps 3, 5, 7 and the packet — **step 8 is not listed**, so 8.4's exit 2 has no stated action and 8.5 proceeds with nothing reported. *Fix: add step 8 to the row.*

**M13** `--post-approval` reaches the agent only through a narrative aside in the file read at 4.1 and never re-read; `plan-format.md:76`'s field rule 11 — the rule the aside claims governs — omits the flag entirely. *(The guard half is U10.)*

**M14** `execution.md` rows 14 and 15 tell the agent to "Fix the test support and re-run" and "Fix that cause, re-run" with no mention of `ctdd-tests`, against `SKILL.md:24`'s unhedged *"never write a test file from this skill"*. Row 27 routes correctly; these two do not. The red-state log `check-redstate` then blesses was produced by a test the change skill wrote and adjusted itself — and `SKILL.md:98` only forbids weakening assertions *to obtain green*, not to obtain red. *Fix: route both rows through `ctdd-tests`.*

**M15** `currently_` characterization observations are required by `ctdd-review:41`, have no requesting step in `ctdd-change`, and no declared home in `plan-format.md` — so a conformant change earns a `needs-tests` finding. And if one is written and the change corrects the bug it encoded, `execution.md`'s broken-pin row forbids the only correct response. *Fix: name them at 7.5 and add an evidence-state row for a marked observation the plan declares this change alters.*

**M16** `expected pre-implementation failure` is approved at the gate and **read by nobody**: `ctdd-tests` is never handed the text, `check-redstate`'s success line explicitly disclaims it ("That they failed for the *right* reason is still the reviewer's read"), and `ctdd-review` requires only a captured failing run. So `execution.md:15`'s "wrong red never unlocks step 8" has no detector at the seam. *Fix: have 7.10 print `planned: … | observed: …` per test into the packet. No new script.*

**M17** `ctdd-tests` step 6's precondition — "only the declared test artifacts changed" — **cannot hold** when `ctdd-change` invokes it, because 7.3 already wrote the contract and ADR and a compile-only stub may have been added. A precondition that never holds either blocks the handoff or trains the delegate to ignore preconditions. Its blocked-table also has only one compile-red row where `execution.md` has two with opposite actions, so a missing test-project reference produces **production code for a problem that is not in production**. *Fix: reword to "no production behavior changed since this invocation began"; split the compile row.*

**M18** `ctdd-review` hands `ctdd-change` "finding IDs" that its own artifact contract never assigns (the format is `[severity][category][evidence-class] file:start-end — title`, carrying no identifier), and `ctdd-change` contains the word "finding" nowhere in its ordered workflow. The return path is named on both ends and defined on neither. *Fix: assign IDs, or change the wording, and give a finding a landing point.*

**M19** An 8.6 amendment voids the approval and **nothing unwinds the artifacts already written under it**. An ADR written at 7.3 with `Status: Accepted` survives an amendment that changed the decision, and rule 15 then forbids rewriting it — stranding a frozen, accepted record of a decision the human withdrew. *Fix: extend the `APPROVAL STALE` message to name the artifacts written under the void revision.*

**M20** Four different commands are told to write to one "verification path" (`SKILL.md:99` says "saving **each**"; `:42` names a single file whose shape is "the named run", singular). Three of four results are lost, while the packet must report four `command => result` pairs. *Fix: one path per run, or an append convention with command banners.*

**M21** Four evidence `.log` files are written into a plan directory the skill tells the agent to commit from, with **no ignore guidance anywhere** (`git check-ignore docs/plans/foo.redstate.log` → not ignored; `grep -rn "gitignore" skills/ctdd-change/` → zero hits). Raw broader-suite output routinely carries connection strings, tokens, and fixture data, and `check-plan.py:474` actively urges "commit docs/plans/". `ctdd-review/SKILL.md:42` shows the authors considered the question; `ctdd-change` never tells the writer what to do. *Fix: commit only the plan file; name the ignore pattern.*

---

## LOW — 12 items

**L1** `SKILL.md:12`'s `rationale.md` prohibition is bare, with no counterpart permission — unlike the sibling skills, which name a purpose. `docs/pilot-findings.md:413` records the failure this invites ("The agent read `references/rationale.md` unprompted, as its first action"), now a violation with no sanctioned alternative. ~20 chars to fix.

**L2** Placeholder names drift from the contract that defines their values: `<plan-path>`, `<pin-log>`, `<red-log>`, `<pin-after-log>` appear at 8 command sites and **zero** definition sites. Derivable, but resolved by inference at the same moment the agent is fighting U5, U6 and H5.

**L3** `SKILL.md:76` requires `<plan-dir>` to be produced by the `--plan-dir` call in the **first half of the same sentence** before the second half's path can be formed — a sequencing the sentence never makes explicit.

**L4** `plan-format.md:58`'s tier table promises `large` for "no named test in either lane", a classification the checker **never emits** — it exits 1 with `NO EVIDENCE LANE`. The sentence justifying the whole tier design rests on a branch that does not exist. *(Related to U4, which is the exploitable half.)*

**L5** `SKILL.md:76`'s "the checker rejects a pointer outside it" is **false for the invocation 5.4 orders**: location enforcement lives only in `--from-description`, which no step invokes. The positional form accepts a plan anywhere on disk at exit 0 — so an agent can write it somewhere valid-looking, pass 5.4, and have CI reject the MR.

**L6** `gen-authz-matrix.py` is unreachable from `ctdd-change`, though `plan-format.md:92` mandates an Authorization row and the generator derives exactly that matrix from OpenAPI. Worse, it is invoked only from `ctdd-tests`, i.e. **after** the gate that must already enumerate the authorization surface — so the human approves the agent's impression, and the mechanical enumeration arrives when disagreement costs an amendment.

**L7** `--allow-empty` is the only escape from `check-spec-surface`'s exit-2 empty-diff state and no step mentions it.

**L8** `check-redstate.py:503` cites "Step 7.12", which does not exist — step 7 ends at 7.11. Renumbering residue.

**L9** `check-plan.py:427` calls `_fail("--approval needs a path")` and **`_fail` is not defined anywhere in the file** — verified: `py -3 scripts/check-plan.py dummy.md --approval` raises `NameError: name '_fail' is not defined` and exits 1 with a traceback. It fails closed, so no evidence is corrupted, but the operator sees a crash instead of the usage message. One-line fix; needs a test.

**L10** The `--help` text documents `--diff` and `--from-description` and omits `--approval`, `--post-approval`, and `--plan-dir` — so the agent's natural recovery from U1 or H3 cannot recover the contract either.

**L11** Commit messages do not match the versions they ship: `ccd5c26` "V33.0 and v34.0" ships `0.35.0`; `05e78ca` "V32.0 and V33.0" ships `0.33.0`; `e0cef83` "version 26,2 to 27,2" ships `0.28.0`; `e85ffc1` "v2.26.0" ships `0.26.0`. Harmless in isolation; it makes bisecting a regression to a release meaningfully harder.

**L12** The installed plugin at `…\plugins\cache\ctdd\ctdd\0.43.0` is **ahead of this repository's HEAD (v0.38.0)** and its `skills/ctdd-change/SKILL.md` differs from HEAD by 21 lines each way — so **the skill the user's agents actually run is not the code in this repo**, and no commit here reproduces it. That build also ships `.pytest_cache/` (5 files), which the release checklist says to clean. Worth resolving before any fix is validated "in the plugin": the plugin under test and the plugin in use are different artifacts.

---

## What was checked and came back clean

Recorded so it is not re-audited: frontmatter for all three skills parses under PyYAML, `name` matches
its directory, and the folded scalar folds losslessly (933 chars, ~63% of the cap). `--diff`
missing/empty/malformed all exit 2, so 3.3's "treat exit 1 and exit 2 alike" is accurate. `--adr-dir`
ambiguity exits 1 with a clear message. The substring collision between
`capture_succeeds_when_amount_is_one_cent` and `…_one_cent_below_authorized` is handled correctly.
`plan-format.md` rule 4's bullet-`none` claim is true. The canonical plan exits 0 as `large`, matching
both `plan-format.md:58` and `worked-change.md:44`. The both-lanes-`none` case is correctly blocked at
5.4 with a message that names step 8's Enter by name. Skip ranges 7.4→"7.5-7.7" and 7.8→"7.9-7.11" are
exactly right. Every phrase `ctdd-change` rejects to `ctdd-tests` has a counterpart there; all five
nouns it rejects to `ctdd-review` are claimed there; "implement the review comments" is a clean
three-way agreement. And thirteen guards in the coverage audit are **real**, including the write-freeze
and approval-exclusion probes, which are full-sentence assertions rather than substrings.

`rationale.md` is an orphan **by design**, not a defect: all three skills use the convention, it costs
zero context, and it is excluded from the route ratchet.
