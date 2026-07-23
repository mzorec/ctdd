# ADR rules

Read this when a change involves a structural decision, or when asked for a standalone ADR.
The template is beside this file at `adr-template.md`.

An ADR is a short record (a page or less) of one significant decision, in three parts: **context** (the situation and forces), **decision** (what was chosen), **consequences** (what was accepted, good and bad). Scaffold new ADRs from `${CLAUDE_PLUGIN_ROOT}/skills/ctdd-change/references/adr-template.md`.

- Store as a numbered, append-only file, e.g. `docs/adr/0007-payments-in-domain-layer.md`.
- **Append-only:** never edit a past ADR to reflect a new decision. If a decision is reversed, write a new ADR that supersedes the old one and mark the old one "Superseded by NNNN". The record is what was believed *at the time*.
- Capture the decision and its tradeoffs, not a description of current behavior. The moment it narrates what the code does, it has drifted into spec territory — stop.

### Standalone ADR requests

When the ask is only to record a decision ("write an ADR for choosing RabbitMQ over Kafka"), skip the workflow and apply the ADR rules directly: interview for context, decision, and consequences where they aren't given; find the next number in the ADR directory; write the file from the template.
