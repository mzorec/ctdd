# Proposal, 2026-11-25: a closed list of stops

*(Built in 0.61.0 on 2026-11-25, on the owner's approval of the wording below.)* Each numbered
part carries a **Status** line saying what was built and where its shape differs from this draft.
The last section is the exception: what it lists is still a proposal, and is filed in
`docs/backlog.md`.

The owner asked for two things. The workflow stops for the human at a short, closed list of
moments and at nothing else. And when a plan has phases, the human says how far the agent goes
before it stops again: one phase, several, or all of them. This file is the draft for that
decision: the list, what it changes against 0.60.0, the exact wording, the checker and hook that
go with it, and what moves as a consequence.

## The list

After this change a plan-gated change stops for the human only here:

1. **The gate.** The plan is presented (step 6).
2. **The phases.** Only when the plan says `red pause: phased`. Once after the failing tests
   (7.12), where the phases are shown and the human says how far to go. Then after the last phase
   they released (8.7), while phases remain, with the same question.
3. **An amendment.** The plan changed after it was approved, so it goes back to step 6. The lighter
   lane and the approval that covers the change it dictates stay as they are.
4. **A question or a finding.** A Decision prompt, or one of the states the workflow already stops
   on: a pin that fails before the change, a new test that passes before any code is written,
   preserved behaviour that broke, a green obtained by weakening an assertion, a target file
   changed outside the plan, a checker that cannot run, a base that is not ours to pick.
5. **The hold-out.** At 9.1, when the plan requires one and it was not declined at the gate.

The hand-over at 9.4 is the end of the change, not a stop inside it.

## What this changes against 0.60.0

Five things.

**The human says how far to go.** Today a phased plan implements one phase and stops, every time.
Under the list the human releases as many phases as they choose when the phases are shown, and the
agent stops after the last one released. "All" means no further phase stop.

**`phased` is drafted when the plan has more than one phase.** Today rule 13 drafts by tier:
`skip` at small, `pause` at medium, `phased` at large or at three phases. The human now chooses the
number of stops, so the draft only decides whether they are asked, and they are asked whenever
there is more than one phase to choose from. A plan with a single phase is drafted `skip`, a
high-risk one included: it runs from approval to the hold-out or the hand-over.

**`pause` is no longer drafted.** It leaves the template. A plan already approved with `pause`
keeps working, because 7.12 stops for every value that is not `skip` and that line does not change.

**A hold-out declined at the gate no longer stops at 9.1 for a hand check.** Today 9.1 then asks
the human to recompute the expected values by hand. Under the list a decline is recorded as the
waiver it is, and nothing is asked in its place. This reverses a decision taken in 0.57.0, where
the hand check was kept as its own stop and asked once.

**"Nothing else" gets something that enforces it.** Today nothing does. A stop hook, described
below, sends the agent back to work when it ends a turn inside an approved change with nothing to
ask and nothing owed to the human.

## Evidence

Measured on 2026-11-25 from session logs: 75 changes in five service repositories over 45 days.
The counts use timestamps, the plugin's own tokens, the length of an answer and whether it opens
with a go-ahead word. The scripts print totals only: no message text was shown or kept.

- 31 of the 49 plans seen at a gate were approved as `phased`, 7 as `skip` and 6 as `pause`.
- 39 of the 47 plans whose tier could be read were large, and 32 of the 33 plans drafted `phased`
  were large. Today a plan gets phase review for its tier far more often than for its phase count.
- The phases could be counted in 23 of the 31 plans approved as `phased`: one had a single phase,
  8 had two and 14 had three or more. Under the new drafting rule only the single-phase plan would
  have been drafted `skip`.
- The phases are shown after the failing tests, not at the gate. Only 5 of the 31 phased plans had
  a gate block that named a numbered phase. The human named a phase number in 5 of the 13 answers
  given where the phases were first shown, and in 4 of the 93 given at a gate.
- A phase stop is mostly answered with a go-ahead. At the 33 stops where the agent had printed a
  phase block, 27 answers were six words or fewer, 23 of them a bare go-ahead, and 14 named a
  phase number. Each go-ahead is a round trip the human could have saved by releasing more than
  one phase at once. The detector is narrow, so 33 undercounts the phase stops.
- Across every moment in the middle of the work under `phased`, the answers split evenly: 193 of
  seven words or more against 179 shorter. That count cannot tell a phase stop from any other
  moment, so it says the human steers phased changes often, not that the checkpoints are where
  they do it.
- The pilot record already says the hold-out ran zero times in seven changes.
- Of 271 short answers given while the agent was in the middle of the work, about 15 came in plans
  set to `skip` and 61 where the setting could not be read. Those are the stops no rule asked for.
  It is dozens in 45 days, not hundreds, and the hook is sized to that.

## 1. Wording: fourteen edits

**Status:** built as drafted, with one edit more. The draft missed a line of
`references/rationale.md` that argued for hand-checked values after a decline. It went too: 145
characters, in a file that is not on the route. Fifteen edits in all.

Eight edits remove 410 characters and six add 287. The body goes from 16,085 to 16,044 characters
against a limit of 16,400, and the plan-gated route from 52,041 to 51,918 against a ratchet of
52,050. The hold-out probe moves from offset 14,047 to 14,061 under its ceiling of 14,100: the one
edit above it, step 8.7, adds 14 characters.

What the additions displace: the stop after every phase, the drafting by tier, and the hand check.
What demanded them: the owner's directive of 2026-11-25, recorded as pilot intent, and the counts
above.

| File | Edit | Characters |
|---|---|---|
| `skills/ctdd-change/SKILL.md` | 8.7 implements the phases the human released | +14 |
| same | 9.1 does not stop after a decline at the gate | −55 |
| `skills/ctdd-change/references/plan-format.md` | template line offers two red pause values | −8 |
| same | rule 6 loses its pointer to the old rule 8 | −9 |
| same | rule 8: a decline asks for nothing | −230 |
| same | rule 13: the human says how far | +43 |
| same | example: the categorical line | −1 |
| same | example: what a decline costs | −29 |
| same | example: the field nobody fills in | −38 |
| `skills/ctdd-change/references/execution.md` | 7.12 row: under `phased`, ask how far | +159 |
| same | 8.7 row: the diff since the last stop | +17 |
| same | 8.7 row: ask how far to continue | +53 |
| same | 8.7 row: N is the last phase released | +1 |
| same | hold-out row: no hand-checked values | −40 |

The exact text, old then new.

**`SKILL.md`, step 8.7.**

> 7. With `red pause: phased`, implement ~~one phase at a time; stop after each~~ **the phases the
> human released; stop after the last** and read `references/execution.md` now even if read
> earlier.

**`SKILL.md`, step 9.1.** Only the middle clause changes; the sentence still opens with the words
the survival probe looks for.

> …asking write / decline; when it was declined at the gate, ~~stop here instead for the hand
> check of the plan's expected values.~~ **do not stop.** Resolve it to `passed`, `failed`…

**`plan-format.md`, the template line.**

> red pause: <phased | ~~pause |~~ skip>

**`plan-format.md`, rule 6.**

> …never the value, which the human computes ~~(rule 8)~~; give `write` and `decline`…

**`plan-format.md`, rule 8.** Old:

> 8. When the human declines a required hold-out, list the load-bearing expected values and ask
> them to recompute each one by hand from the business requirement, never by reading the code that
> produced it. Offer it as the fallback, never as the equivalent, and do not label it a hold-out
> result. Ask at step 9.1, once; approval at the gate does not confirm the values.

New:

> 8. When the human declines a required hold-out, at the gate or at step 9.1, record `declined by
> human` and ask for nothing in its place.

**`plan-format.md`, rule 13.** Old:

> 13. Set the red pause: `pause` stops after step 7, prints the pre-implementation diff and
> intended changes, and waits; `phased` adds a stop after each implementation phase with its diff
> and evidence; `skip` implements at once. Draft `skip` at small, `pause` at medium, and `phased`
> at large or when the planned files form three or more phases; the human flips it at the gate.

New:

> 13. Set the red pause: `phased` stops after step 7 with the pre-implementation diff and the
> intended changes by phase, and the human says how far to go: one phase, several, or all. It
> stops again after the last phase they released, with its diff and evidence, while any remain.
> `skip` implements at once. Draft `phased` when the planned files form more than one phase,
> otherwise `skip`; the human flips it at the gate.

The last sentence of the rule, about the field being required and the tier never reading it, is
unchanged.

**`plan-format.md`, the complete example.** Its categorical line reads `red pause: skip` in place
of `pause`: the example's slices all land in one file, which is one phase. Its `decline` option
reads "recorded as `declined by human`; nothing is asked of you in its place." The line
`- human-verified expected values: n/a` goes, since nobody fills it in any more. The checker never
required that field and goes on tolerating it in older plans.

**`execution.md`, the 7.12 row.** Its closing sentences, old:

> …Ask to proceed as a Decision prompt. A requested change is an 8.6 amendment; proceed only on an
> affirmative human message. Record their release as `Pause released by: "<their message>"` in the
> approval log.

New:

> …Ask to proceed as a Decision prompt; under `phased` ask how far instead (one phase, several, or
> all) and recommend nothing. A requested change is an 8.6 amendment; proceed only on an
> affirmative human message. Record their release as `Pause released by: "<their message>"` in the
> approval log, and under `phased` the last phase it covers as the next row records it.

**`execution.md`, the 8.7 row.** Three places change and the row's trigger does not, so the tests
that find the row by its trigger still find it.

> …Print ~~the phase's diff~~ **the diff since the last stop** and its evidence — build result,
> every pin green, the invariant suite green (a failure is an 8.6 finding), the intended-red set
> changed only by tests ~~the phase's own files~~ **the released phases' files** serve — then the
> block for the phase being continued to and never the one just finished, or that none remains,
> and ask ~~to continue as a Decision prompt~~ **how far to continue as a Decision prompt: the
> next phase, several, or all that remain**; recommend nothing. … Record each release as
> `Phase <N> released by: "<their message>"`, N the ~~phase continued to~~ **last phase
> released**.

**`execution.md`, the hold-out row.**

> …only then does the plan carry `declined by human` ~~with the human-verified expected values~~.

## 2. The checker says whether the change is waiting on the human

**Status:** built. Two differences. `hold-out` also covers a result of `failed`, which blocks the
packet. And the `Next:` line for step 9 names the 9.1 stop only while a required hold-out has no
answer, and says that 9.1 owes no stop when it has one or when none is required.

`check-plan.py --next` already reads the files beside a plan and names the first step that left no
evidence. The hook needs one more fact from the same reading, so it belongs in the same function
and not in a second copy of the logic: is the change, at this point, waiting on the human?

`next_step()` gains one key, `stop`, with one of these values.

| Value | When | Which stop of the list |
|---|---|---|
| `gate` | no approval record, a stale one, or a plan that fails the checker | 1 and 3 |
| `pause` | the red pause is not `skip` and its release is not recorded | 2 |
| `phase` | `phased`, the pause released, verification not yet saved | 2 |
| `hold-out` | everything through the pins is saved, the hold-out is required and its result is still `pending` | 5 |
| `done` | the packet is saved | the hand-over |
| `none` | anything else: the next step is the agent's own | — |

Three messages change with the wording. The `Next:` line for step 9 stops mentioning the hand
check, and the message that refuses a deferred hold-out stops mentioning hand-computed values. The
`Next:` line for a phased plan reads "implement through phase N, the last one released" where it
read "implement phase N": the record keeps its form, `Phase <N> released by`, and `--next` already
takes the highest N in the log. Nothing else in the checker moves. It goes on reading hand-check
values in an older plan that carries them, so an amendment to such a plan is still reported.

`phase` is deliberately coarse. Between the release of the pause and the last phase, the files
cannot tell a finished phase from a stop in the middle of one, so the hook stays silent for that
whole stretch, a release of every phase included. Two things would close the gap, and neither is
part of this proposal. Each checkpoint could leave a file. Or the release could carry the number
of phases, `Phase <N> of <M>`, so that the checker sees when nothing more is owed. Both read
records the logs show are seldom written, so they wait until the releases are recorded reliably.
Both are filed in `docs/backlog.md`.

## 3. The stop hook

**Status:** built, opt-in. One real session was run with a throwaway stop hook before this one was
written, to see what the harness hands it and that a block continues the turn. Its payload showed
three things the draft did not have. It lists pending background tasks and scheduled wake-ups, so
the hook is also silent while either is pending: that is waiting, not stopping. A blocked stop is
written into the transcript, so the hook reads that as a second witness that it already pushed in
this turn. And the event has a name, so it is silent at a subagent's stop. A question mark counts
as a question only in what the message says, not in what it quotes: a nullable type in a code span
is not the agent asking. The finished hook was then run in four real sessions against a synthetic
approved plan. It blocked a stop that followed a plain report and the turn continued, twice. It
said nothing when the agent ended on a question, and nothing during a phased implementation.

A new file, `hooks/ctdd-continue.py`, on the `Stop` event. It reads and never writes. It follows
the resume hook in every habit that matters: it finds the plan the session's tools named last, it
asks `check-plan.py` where that change stands, and it is silent when anything at all fails.

It lets the agent stop, saying nothing, in each of these cases, checked from the cheapest to the
dearest:

1. The harness says a stop hook already continued this turn. One push per stop, never two.
2. The session is in plan mode.
3. The agent's last message asks something or names a finding: a question mark in its closing
   lines, or one of the workflow's own state names.
4. The turn that is ending edited nothing and ran nothing. An answer to a side question is a
   finished turn.
5. `ctdd-change` did not run in this session, or no plan is found.
6. `stop` is anything but `none`.

Only when none of those holds does it block the stop, with this message:

> CTDD: this change stops only at the gate, a phase checkpoint, an amendment, a question or a
> finding, or the hold-out. The plan is approved at its current revision and none of those applies
> here. Next: *(the `Next:` line)*. Carry on without waiting. If you do need the human, ask it as
> a Decision prompt and stop again.

What it never does: approve anything, answer anything, or hold the agent against its will. A
second attempt to stop always succeeds, and the harness caps consecutive continuations as well.

It ships opt-in, as an entry in `hooks/hooks.json.example`, because whatever `hooks/hooks.json`
registers is live in every session that has the plugin on.

Tests go beside it in `hooks/test_ctdd_continue.py`, one per silent case above and one per
stretch where it must push: between approval and saved red state, during implementation under
`skip`, and between saved verification and the packet when no hold-out is owed. Each silent case
is then probed the way rule 8 asks, on a copy of the tree: delete the condition, see its test
fail.

## 4. What moves with it

**Status:** done, and larger than drafted on the eval side. The fixture's plan carried the
hand-check wording, and its phase states carried no pre-implementation diff, which `--next` has
read since 0.60.0, so both were updated. A third scenario was added: what a go-ahead that names no
phase releases, which the approved wording does not say. Results are in
`evals/workflow/RESULTS-2026-11-25.md`.

With all fourteen edits applied to a copy of the tree, 744 tests run and one fails because of the
wording. No test guards the stop after every phase today, so the new rule needs guards of its own.

- **One guard is retired on purpose.** `test_the_holdout_decline_path_keeps_what_makes_it_independent`
  protects the hand-check clauses of rule 8, and it is the one test that fails. Its two assertions
  that survive the decision stay: a decline is a waiver, and the review reports a declined hold-out
  on a high-risk change. A new assertion says 9.1 does not stop after a decline.
- **Three guards are added.** Step 8.7 stops after the last phase released and not after each one.
  The 7.12 row asks how far under `phased`. The 8.7 row asks how far to continue and records the
  last phase released. Each is probed the way rule 8 asks: restore the old wording on a copy, see
  the guard fail.
- **Three checker tests follow the messages.** The `--next` test that quotes the hand check, and
  the two that quote "implement phase N".
- **The evals follow the rule.** `d5-hand-check-pending` in `evals/workflow/scenarios.json` tests
  the stop that goes away; its replacement is a hold-out declined at the gate, where 9.1 does not
  stop. `h-checkpoint-scope` expects the agent to ask whether to continue; it becomes how far. One
  scenario is new: the human released two phases, and the agent does not stop after the first.
- **The record.** A changelog entry, intent-born, naming what it reverses, and a line in
  `backlog.md` under the hold-out redesign saying which option was chosen.

## What this reverses

- 0.57.0 kept the hand check as its own stop at 9.1, asked once. This removes it.
- 0.42.0 gave the red pause three values and drafted them by tier and width, on the reasoning
  that the tier measures risk and the phase count measures width. This drafts two values by
  whether there is more than one phase, because the human now chooses the stops and risk no longer
  has to choose them.
- 0.42.0 had step 8.7 implement one phase at a time. This implements the phases the human
  released.
- The hand-check guard was written because those clauses had once been lost by accident. This time
  they are removed by decision, and the guard's docstring should say so.

## What is left for the owner to decide

*(Proposed — not yet built.)* The first two are filed in `docs/backlog.md` under the stop list of
0.61.0, with the two ways of closing the hook's gap named in part 2.

- **Where the human says it.** The draft puts the question at the stop after the failing tests,
  because that is where the phases are shown today and where the logs show phase numbers being
  named. Asking at the gate instead would save that stop on every phased plan. The gate would
  first have to show the phases, as a new gate-visible part of the plan, and the phases would
  become part of what is approved, so changing them later would be an amendment. 16 of the 30
  phased plan files that could be read already number their phases, and the gate block showed
  them for 5. Not drafted.
- **`pause` in the checker.** The draft stops drafting it and goes on accepting it. Refusing it in
  new plans is a small addition; plans approved before the change would still need to pass.
- **How the hook ships.** Opt-in through the example file, as drafted, or registered like the
  resume hook.
- **Releases that are not recorded.** In the same 45 days the logs show 182 approvals written to
  approval logs and 13 releases. The rule asks for one per release, and `--next` reads them. A
  release now says how far the agent may go, so the record matters more than it did. Within a
  session the agent has the human's message in front of it and needs no record; a resumed session
  and the hook do. This proposal does not change how releases are recorded.
