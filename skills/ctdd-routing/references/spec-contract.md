# What a spec must carry

Read this once `brainstorming` is the chosen route, before writing the spec. `ctdd-change` reads
the document and never the brainstorming conversation, so shape the spec around what it cannot
recover from a conversation it never sees.

- **The requirement in one or two sentences** — it becomes `Business requirement` verbatim.
- **Success stated as observable behavior**, not as implementation: what an outside caller sees
  differ. Vague success criteria produce untestable plans, and the test lanes are derived from
  this.
- **Constraints that bound the solution**, each with its source — a cost, a policy, a platform
  limit. They land as assumptions, budgets, or known gaps rather than being rediscovered.
- **Measured facts about the system being changed or replaced**, each with how it was
  established. A brainstorm that moves scope on evidence must carry the evidence: the measurements
  are expensive to obtain, easy to misremember, and cited by every plan the spec decomposes into.
  Without them each plan re-derives its own and they drift. This is distinct from a constraint —
  a constraint bounds what may be built, a measurement says what is already true.
- **Options considered and why each lost** — including **positions that were taken and then
  overturned, and what overturned them**. Options rarely arrive as a tidy set weighed at one
  moment; more often a recommendation is made and defeated by something the recommender did not
  know, and that reason is the part no later reader can reconstruct. This is the content ADR
  drafting needs at step 4.3. A spec that records the chosen approach and nothing else forces the
  decision to be re-argued or an ADR to be written with an empty `Options` section.
- **What is explicitly out of scope, and why each item is out**, so the plan gate is not the
  first place scope is tested. A bare list gets re-proposed at the next planning session; the
  reason is what makes an exclusion survive.
- **When the spec is more than one change, the split and its dependency order.** `ctdd-change`
  gates one change at a time and has no step that notices a business requirement covering three;
  unstated, the first plan swallows the lot or silently drops the rest.

Keep out the shape of code that does not exist yet: behavior flows, file lists, function or
test names, table columns. None of it is knowable before the code is read and the tests exist,
so a spec-time guess becomes a stale commitment the plan then has to contradict — and it is
also where a spec starts duplicating `Implementation slices`. Naming an existing artifact that
a requirement, constraint, decision or measurement is *about* is not this: that identifies the
subject rather than designing the solution.
