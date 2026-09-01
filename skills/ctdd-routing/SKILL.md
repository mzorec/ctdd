---
name: ctdd-routing
description: >-
  Use when it is not yet clear which workflow owns a piece of work: the requirement cannot be stated
  in a sentence or two, a defect's cause is unknown, the work needs an isolated workspace, or a
  finished branch needs landing. Also use whenever the superpowers plugin is installed alongside
  ctdd, to decide which of its skills applies and which are superseded — brainstorming,
  systematic-debugging, using-git-worktrees, finishing-a-development-branch, writing-plans,
  executing-plans, test-driven-development, verification-before-completion, requesting-code-review,
  receiving-code-review, subagent-driven-development. Routes and hands off; writes nothing itself.
  Not needed when the requirement is already statable — that is ctdd-change, directly.
---

# Routing between ctdd and the phases around it

`ctdd-change` owns every production edit. Everything here decides what happens before it starts or
after it finishes. This skill produces no plan, no code, and no artifact: it names the owner and
gets out of the way.

## Which workflow owns this

| The situation | Owner |
| --- | --- |
| The requirement is statable in a sentence or two | `ctdd-change` |
| Nobody can state it yet, or different directions compete | `brainstorming`, then `ctdd-change` |
| Something is broken and the cause is unknown | `systematic-debugging`, then `ctdd-change` |
| The cause is known and only the fix remains | `ctdd-change`, bug-fix lane |
| The work must not disturb the current workspace | `using-git-worktrees`, then `ctdd-change` |
| `ctdd-change` reached step 10 and the branch needs landing | `finishing-a-development-branch` |
| A structural decision needs recording, no code changes | `ctdd-change`, standalone ADR procedure |
| Finished work needs judging | `ctdd-review`, dispatched separately |

Most work is the first row. Reach for a companion only when the row above genuinely fits — a design
phase on a statable requirement is exploration nobody asked for, and a debugging phase on a known
cause is ceremony.

## What each companion hands over

- **`brainstorming`** ends at a committed spec, and that spec is `ctdd-change`'s business
  requirement. The spec must carry everything the change needs: `ctdd-change` reads the document,
  never the brainstorming conversation. Two of its own exits bypass this workflow and are not
  followed — Path 2 step 5 implements directly with no plan document, and Path 3 step 9 invokes
  `writing-plans`; both hand off to `ctdd-change` instead. It never edits production files.

  Shape the spec around what `ctdd-change` cannot recover from a conversation it never reads:

  - **The requirement in one or two sentences** — it becomes `Business requirement` verbatim.
  - **Success stated as observable behavior**, not as implementation: what an outside caller sees
    differ. Vague success criteria produce untestable plans, and the test lanes are derived from
    this.
  - **Constraints that bound the solution**, each with its source — a cost, a policy, a platform
    limit. They land as assumptions, budgets, or known gaps rather than being rediscovered.
  - **Options considered and why each lost.** This is the content ADR drafting needs at step 4.3
    and the only part a later reader cannot reconstruct from the code. A spec that records the
    chosen approach and nothing else forces the decision to be re-argued or an ADR to be written
    with an empty `Options` section.
  - **What is explicitly out of scope**, so the plan gate is not the first place scope is tested.

  Keep out of it: behavior flows, file lists, function or test names, and anything else about code
  shape. None of it is knowable before the code is read and the tests exist, so a spec-time guess
  becomes a stale commitment the plan then has to contradict. Approving the spec is not approving
  a plan either — the gate at step 6 is still where a change is authorized.
- **`systematic-debugging`** ends at a diagnosis and a reproduction. The reproduction becomes the
  new-behavior test of a `ctdd-change` bug-fix plan, so red state is that reproduction failing and
  nothing is re-derived. Investigate without leaving edits in the tree: step 7.2 requires the
  pre-implementation diff to hold only planned artifacts.
- **`using-git-worktrees`** hands over a workspace, not an artifact. Inside it, changes still go
  through `ctdd-change`; diff bases are per-worktree, so gates, pauses, and packets behave normally.
- **`finishing-a-development-branch`** consumes rather than feeds, and runs only after step 10. A
  branch closed before the packet exists carries no verdict.

## Superseded — do not use alongside ctdd

| Skill | Why |
| --- | --- |
| `writing-plans`, `executing-plans` | Plans as complete briefs for a zero-context executor; ctdd plans carry behavior, and the code shape is shown at the red pause instead. Two workflows claiming "how changes happen" collide on triggering. |
| `test-driven-development` | Prose RED/GREEN discipline. `ctdd-tests` covers the same ground, and ctdd's red state is a verified log rather than a described intention. |
| `verification-before-completion` | The review packet and `ctdd-review` own completion, with evidence requirements this does not carry. |
| `requesting-code-review`, `receiving-code-review` | `ctdd-review` owns the verdict, including its independence rule. |
| `subagent-driven-development` | Forking the change spine trades continuity for context thrift; ctdd bet on continuity. Independence forks — the review, blind eval comparison — are the exception, not the pattern. |

If one of these fires anyway, the work still passes through `ctdd-change`: an edit reaching
production without an approval record for the current plan revision is the failure this routing
exists to prevent, whichever skill proposed it.
