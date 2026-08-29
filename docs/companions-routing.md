# Routing: ctdd and its companions

One rule underneath everything: **`ctdd-change` owns every production edit.** The companions
(`ctdd-companions`, vendored from obra/superpowers) own the phases *around* a change — shaping an
idea, finding a cause, isolating a workspace, closing a branch. They hand off; they never edit.

## The decision, in order

```
Is a change to production code the next action?
├─ No, the idea has no stated requirement yet ............ 1. brainstorming
├─ No, something is broken and the cause is unknown ...... 2. systematic-debugging
├─ No, the work is finished and needs landing ............ 5. finishing-a-development-branch
├─ No, only a decision needs recording .................. 6. standalone ADR
└─ Yes
   ├─ It must not disturb the current workspace ......... 4. using-git-worktrees, then ctdd-change
   └─ Otherwise .......................................... 3. ctdd-change
```

Then, whatever the entry point, judging the finished work is variant 7.

## 1. Shapeless idea → `brainstorming`

**Use when** nobody can state the requirement in a sentence or two, or genuinely different
directions compete. **Do not use** when the requirement is already statable — that is most work,
and the vendored description routes it straight to `ctdd-change` at no token cost. This is the one
companion whose upstream trigger was inverted on purpose: it demanded itself before *any* creative
work, which would have paid for design exploration on every trivial change.

**Exit:** a spec or design document, committed. **Handoff:** that document becomes
`ctdd-change`'s business requirement, confirmed at step 1.

**The one discipline:** everything the change needs goes *in the document*. `ctdd-change` reads the
spec, never the brainstorming conversation.

## 2. Broken behavior, unknown cause → `systematic-debugging`

**Use when** there is a defect, a failing test, or unexplained behavior and the cause is not yet
established. **Do not use** when the cause is known and only the fix remains — that is a bug-fix
change, so go to `ctdd-change`.

**Exit:** a diagnosis plus a *reproduction*. **Handoff:** the reproduction is the new-behavior test
of a `ctdd-change` bug-fix plan — red state is that reproduction failing, and the fix turns it
green. Nothing needs re-deriving.

**Watch:** investigation that edits the tree is visible at step 7.2, which requires the diff to hold
only planned artifacts. Investigate in scratch space, or revert before planning.

## 3. Stated requirement → `ctdd-change`

The default path, and the only one that writes production code. Plan gate at step 6, red state at
7, implementation at 8, packet at 9. Two choices are yours at the gate, on the categorical line:

- `red pause: skip` — small changes: straight from red state to implementation.
- `red pause: pause` — medium: one stop after red state showing the diff, the intended-change
  table, and what no flow step covers.
- `red pause: phased` — large, or three-plus phases: that stop, plus one after each implementation
  phase with its diff, build result, pin state, and red-set check.

## 4. Isolation needed → `using-git-worktrees`, then `ctdd-change`

**Use when** two changes are in flight, an experiment must not touch the main workspace, or you want
the same change run two ways and compared. **Do not use** for ordinary sequential work — a branch is
enough.

**Handoff:** inside the worktree, the change still goes through `ctdd-change`; diff bases are
per-worktree, so gates, pauses, and packets behave normally.

## 5. Work finished → `finishing-a-development-branch`

**Use when** `ctdd-change` reached step 10: packet produced, colocated notes written. Branch
mechanics — squash choices, PR shape, cleanup — live here.

**Do not use** earlier. A branch closed before the packet exists has no verdict attached to it.

## 6. Decision only → standalone ADR

**Use when** a structural decision needs recording and no code changes. Skip the change workflow;
`ctdd-change` routes to the standalone ADR procedure in `references/execution.md`. No companion
involved.

## 7. Judging finished work → `ctdd-review`

Dispatch it separately, never from the session that wrote the diff: a review that session
commissions and frames is not independent. It reads the plan, the packet, and the diff from disk.

## Deliberately not vendored

| Upstream skill | Why not |
| --- | --- |
| `writing-plans`, `executing-plans` | Plans as complete briefs for a zero-context executor — the opposite bet from behavior-only plans plus accumulated context. Two workflows claiming "how changes happen" collide on triggering. |
| `test-driven-development` | Prose RED/GREEN discipline; ctdd's equivalent is checked — approval records, verified red-state logs, pin evidence. |
| `verification-before-completion` | Same ground as the packet and `ctdd-review`, without the evidence requirements. |
| `requesting-code-review`, `receiving-code-review` | `ctdd-review` owns the verdict and its independence rule. |
| `subagent-driven-development` | Forking the change spine trades continuity for context thrift; ctdd bet on continuity and defends it with compaction guards. Independence forks (review, blind eval) are the exception. |

Re-sync vendored skills from upstream manually; `ATTRIBUTION.md` in `ctdd-companions` pins the
commit and lists local modifications.
