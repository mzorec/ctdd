# Colocated note rules

Load this file only at `SKILL.md` step 10.2, after 10.1 determines that no test or contract already expresses the behavior.

1. Write one note only for one of these subjects:
   - a universal invariant that cannot be executable;
   - a deliberately undefined boundary that cannot be executable;
   - a durable external fact required by the code.
2. Write the note at a path the plan's `Colocated notes` section names. That section is conditional: when 10.2 will fire, the path is approved at the gate with everything else.
3. Write one sentence.
4. State the rule before its provenance.
5. Add provenance only when it is stable.
6. Use the first available provenance form in this order: executable consumer contract, versioned schema identifier, stable ticket or ADR identifier, no provenance.
7. Do not cite another repository's mutable file path.
8. Put a time-bound fact in the plan or an ADR instead of a colocated note.
9. Delete the proposed note when the rule is derivable from repository code, tests, or contracts.

Use one of these exact shapes:

- Invariant: `<rule>; behavior for <boundary> is intentionally undefined.`
- External fact: `<external fact>; therefore <local rule>, per <stable identifier>.`
- External fact without stable provenance: `<external fact>; therefore <local rule>.`
