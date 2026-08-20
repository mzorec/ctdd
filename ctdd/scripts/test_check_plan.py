#!/usr/bin/env python3
"""Tests for check-plan.py — pinning the section checks, the trivial-skip
exemption, the newline bypass fix, and the new trivial-vs-diff cross-check.

Run:  python3 scripts/test_check_plan.py   (or via pytest)
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "check-plan.py")

FULL_PLAN = """Allow one capture below the authorized amount while preserving over-capture rejection.
Risk: normal · contract: none · ADR: none · hold-out: not required
BLOCKING — I will not guess:
- auth hold on the released remainder? (recommend: expires with the auth)
Proceeding unless you object:
- zero capture rejected
Business requirement: allow one capture below the authorized amount
Intended behavior: capture accepts 0 < amount <= authorized and moves to CAPTURED
Risk level: normal — money path
Existing behavior (openapi.yaml; CaptureTests.cs):
- x
Assumptions:
- y
Uncovered / ambiguous:
- z
Known gaps: none — the caller contract is covered
New-behavior tests — must be observed failing first:
- t
Case coverage not reached: none — every applicable row is covered
Preservation pins — must pass before and after: none
Contract changes: none
NFR budgets touched: none
Implementation slices:
- a.cs — accept the lower amount; turns green: `t`
Verification:
- `dotnet test --filter t` — expected: passes after the slice lands
Hold-out: not required — read path
Files likely to change:
- a.cs
Residual risk: none beyond the planned verification
"""


def run(plan_text, extra_args=None):
    return subprocess.run([sys.executable, SCRIPT, "-"] + (extra_args or []),
                          input=plan_text, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=15)


def diff_file(content):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    f.write(content); f.close()
    return f.name


class CheckPlanTests(unittest.TestCase):

    def test_full_plan_passes(self):
        r = run(FULL_PLAN)
        self.assertEqual(r.returncode, 0)
        self.assertIn("all mandatory sections present", r.stdout)

    def test_missing_sections_fail_and_are_named(self):
        r = run("A summary line long enough to read as the decision summary.\n"
                "Risk: normal · contract: none · ADR: none · hold-out: not required\n"
                "Risk level: normal — x\nExisting behavior: y\nAssumptions: z\n"
                "Uncovered: q\nNew-behavior tests — must be observed failing first:\n- t\n"
                "Preservation pins — must pass before and after: none\nContract changes: none\n"
                "Files likely to change: a\n")
        self.assertEqual(r.returncode, 1)
        # `NFR budgets` is conditional below `large`, and this plan derives
        # medium; assert on a section every tier requires.
        self.assertIn("decision summary", r.stdout)
        self.assertIn("hold-out decision", r.stdout)

    def test_trivial_without_diff_passes_with_hint(self):
        r = run("Risk: trivial — typo in log message. Skipping the plan gate.\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--diff", r.stdout)

    def test_trivial_newline_bypass_still_rejected(self):
        r = run("Risk level: trivial —\nExisting behavior: smuggled\n")
        # Rejected either way; the evidence-lane check now reports first, so
        # assert the rejection rather than which message wins the race.
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn("trivial-skip declaration found", r.stdout)

    def test_trivial_with_clean_diff_stands(self):
        d = diff_file("M\tsrc/Payments/Capture.cs\n")
        try:
            r = run("Risk: trivial — null check in logging. Skipping the plan gate.\n",
                    ["--diff", d])
            self.assertEqual(r.returncode, 0)
            self.assertIn("trivial claim survives the surface check", r.stdout)
            # and must not claim more than it inspected: 3.4 needs intent,
            # this reads paths.
            self.assertIn("NOT checked", r.stdout)
        finally:
            os.unlink(d)

    def test_trivial_contradicted_by_test_edit(self):
        d = diff_file("M\ttests/CaptureTests.cs\nM\tsrc/foo.cs\n")
        try:
            r = run("Risk: trivial — small cleanup. Skipping the plan gate.\n",
                    ["--diff", d])
            self.assertEqual(r.returncode, 1)
            self.assertIn("TRIVIAL CLAIM CONTRADICTED", r.stdout)
            self.assertIn("tests/CaptureTests.cs", r.stdout)
        finally:
            os.unlink(d)

    def test_trivial_contradicted_by_contract_edit(self):
        d = diff_file("M\tcontracts/openapi.yaml\n")
        try:
            r = run("Risk: trivial — comment fix. Skipping the plan gate.\n",
                    ["--diff", d])
            self.assertEqual(r.returncode, 1)
            self.assertIn("CONTRADICTED", r.stdout)
        finally:
            os.unlink(d)

    def test_trivial_contradicted_by_rename_out_of_tests(self):
        d = diff_file("R100\ttests/OldTests.cs\tsrc/Old.cs\n")
        try:
            r = run("Risk: trivial — moving a file. Skipping the plan gate.\n",
                    ["--diff", d])
            self.assertEqual(r.returncode, 1)
        finally:
            os.unlink(d)

    def test_the_example_only_uses_case_categories_the_table_defines(self):
        """The example is the operative instruction — models copy it, which is how
        the worked example once made xUnit the effective default while the prose
        claimed neutrality (#53). Shrinking the coverage table from sixteen rows
        to seven immediately left the example citing four categories that no
        longer existed. A category the table does not define is a category the
        reader cannot look up."""
        import re as _re, pathlib as _p
        fmt = (_p.Path(__file__).resolve().parents[1] / "skills" / "ctdd-change"
               / "references" / "plan-format.md").read_text(encoding="utf-8")
        table = fmt[fmt.find("| Case | Required trigger"):]
        defined = {c.strip().lower()
                   for c in _re.findall(r"^\| ([A-Z][a-z ]+) \|", table, _re.M)} - {"case"}
        self.assertGreater(len(defined), 3, "coverage table no longer parses")
        used = set(_re.findall(r"case: ([a-z ]+);", fmt[fmt.find("## Complete example"):]))
        self.assertTrue(used, "the example names no case categories")
        self.assertEqual(used - defined, set(),
                         f"the example cites categories the table does not define: "
                         f"{sorted(used - defined)}")

    def test_required_covers_every_unconditional_section_of_the_format(self):
        """v0.22.0 made seven more sections mandatory in plan-format.md and left
        REQUIRED at twelve, so a plan missing all seven exited 0 and step 5 read
        that as validation. This checker is honestly scoped as an omission
        detector rather than a quality gate, but an omission detector that stops
        covering the format it detects has stopped being one. Reads the format's
        own skeleton so the two cannot drift again silently."""
        import re as _re, importlib.util, pathlib as _p
        fmt = (_p.Path(__file__).resolve().parents[1] / "skills" / "ctdd-change"
               / "references" / "plan-format.md").read_text(encoding="utf-8")
        skel = _re.search(r"Omit only the sections marked conditional\.\s*\n\s*"
                          r"```markdown\n(.*?)```", fmt, _re.S)
        self.assertIsNotNone(skel, "plan-format.md no longer exposes its skeleton")
        headings = [l for l in skel.group(1).split("\n")
                    if l.strip() and not l.startswith(("-", " ", "\t", "`", "<"))
                    and "(conditional" not in l]
        # Floor lowered from 15 to 12: nine sections are now marked conditional
        # because a tier omits them, and this guard counts unconditional lines
        # only. The sanity check is that extraction found *something*, not that
        # a particular number of sections is unconditional.
        self.assertGreater(len(headings), 8, "skeleton extraction found too little")
        spec = importlib.util.spec_from_file_location("cp_mod", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        for h in headings:
            self.assertTrue(
                any(_re.search(rx, h, _re.I | _re.M) for _, rx in cp.REQUIRED),
                f"plan-format.md makes {h.split(':')[0].strip()!r} mandatory and no "
                f"REQUIRED pattern detects it; the gate would pass a plan without it")

    def test_every_tier_enforces_what_the_format_calls_mandatory(self):
        """The format-drift guard asserted each mandatory heading has a pattern in
        REQUIRED, but `required_for(tier)` is what runtime enforces — so deleting a
        name from MEDIUM_SECTIONS left the guard green while the drift was live.
        Rule 8's own test applies: delete the rule the guard covers and confirm it
        fails. It did not.

        Anything a tier drops must be marked conditional in plan-format, because
        that file says `omit only the sections marked conditional` and two files
        disagreeing about what is mandatory is how six sections were dropped
        without anyone noticing."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_tiers", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        fmt = (Path(SCRIPT).resolve().parents[1] / "skills" / "ctdd-change"
               / "references" / "plan-format.md").read_text(encoding="utf-8")
        skel = fmt.split("```markdown", 1)[1].split("```", 1)[0]
        marked = {l.split("(")[0].strip().rstrip(":").lower()
                  for l in skel.split("\n") if "conditional" in l.lower()}
        every = {n for n, _ in cp.REQUIRED}
        for tier in ("small", "medium", "large"):
            dropped = every - {n for n, _ in cp.required_for(tier)}
            for name in dropped:
                head = name.split(":")[0].replace("/", " or ").strip().lower()
                self.assertTrue(
                    any(head in mk or mk in head for mk in marked),
                    f"{tier} drops {name!r} but plan-format does not mark it "
                    f"conditional; marked: {sorted(marked)}")

    def test_a_plan_with_no_evidence_lane_is_rejected_at_the_gate(self):
        """Making both-lanes-`none` derive `large` left the lane with no
        route. 7.4 and 7.8 skip both evidence lanes, so step 8's Enter can never
        be met — after a human has already approved. Reachable on a mechanical
        refactor in an untested area: plan-gated by 3.5, nothing to pin, no new
        behaviour."""
        import re
        dead = FULL_PLAN.replace(
            "New-behavior tests — must be observed failing first:\n- t\n",
            "New-behavior tests — must be observed failing: none — refactor\n")
        dead = re.sub(r"(?m)^Preservation pins.*$",
                      "Preservation pins — must pass before and after: none — nothing covers it",
                      dead)
        r = run(dead)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("NO EVIDENCE LANE", r.stdout)
        self.assertEqual(run(FULL_PLAN).returncode, 0)

    def test_an_open_blocking_question_fails_at_approval_only(self):
        """6.4 asks only for an affirmative message, so a bare "Approved." over an
        unanswered question satisfied the gate — and step 7 then began with the
        agent obliged to guess the one thing the section titled "BLOCKING — I will
        not guess" said it would not. An open question is correct at 5.4, so this
        is checked only with --post-approval."""
        import re
        asking = re.sub(r"(?m)^BLOCKING.*$",
                        "BLOCKING — I will not guess:\n- does the hold expire with the auth?",
                        FULL_PLAN)
        self.assertEqual(run(asking).returncode, 0, "an open question is fine at plan time")
        r = run(asking, ["--post-approval"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("UNANSWERED BLOCKING", r.stdout)
        answered = asking + "\nDecisions confirmed in session:\n- it expires with the auth.\n"
        self.assertEqual(run(answered, ["--post-approval"]).returncode, 0)

    def test_the_approval_record_is_checkable_and_goes_stale(self):
        """Four decision artifacts are stdout-only, the Approval record among them,
        so a resumed session had no legal way to establish 6.4 was satisfied —
        6.4 excludes the agent's own restatement, silence, a subagent verdict and
        harness acceptance, leaving only inference-as-approval. And 8.6 edits the
        plan in place, so a pre-amendment record is textually identical."""
        import hashlib, tempfile, os
        rev = hashlib.sha256(FULL_PLAN.encode("utf-8")).hexdigest()[:12]

        def with_record(body):
            f = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False,
                                            encoding="utf-8")
            f.write(body); f.close()
            try:
                return run(FULL_PLAN, ["--approval", f.name])
            finally:
                os.unlink(f.name)

        self.assertEqual(
            with_record(f'Approved by: "looks right, go"; plan: p.md@{rev}.\n').returncode,
            0)
        stale = with_record('Approved by: "go"; plan: p.md@000000000000.\n')
        self.assertEqual(stale.returncode, 1)
        self.assertIn("APPROVAL STALE", stale.stdout)
        quiet = with_record(f"plan: p.md@{rev}.\n")
        self.assertEqual(quiet.returncode, 1)
        self.assertIn("quotes no human message", quiet.stdout)

    def test_the_categorical_line_must_exist_and_carry_its_fields(self):
        """Tier, triviality and the hold-out check all read this line, and nothing
        required it to exist. `categorical_line(text) or text` then fell back to
        the whole document, so one prose sentence containing `contract: none`
        derived a lighter tier on a breaking change and deleted four sections from
        the gate; and omitting the `hold-out:` field silenced the actionability
        check while the body still declared one required."""
        import re as _re
        self.assertEqual(run(FULL_PLAN).returncode, 0, run(FULL_PLAN).stdout)
        gone = _re.sub(r"(?m)^Risk: .*·.*$", "", FULL_PLAN)
        r = run(gone)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("MISSING the categorical line", r.stdout)
        for partial in ("Risk: normal · contract: none · ADR: none",
                        "Risk: normal · ADR: none · hold-out: not required"):
            r2 = run(_re.sub(r"(?m)^Risk: .*·.*$", partial, FULL_PLAN))
            self.assertEqual(r2.returncode, 1, f"{partial!r} accepted:\n{r2.stdout}")
            self.assertIn("names no", r2.stdout)

    def test_an_em_dash_separator_still_declares_the_holdout(self):
        """The skeleton uses an em dash as a field separator elsewhere, so
        `hold-out — required: 2 sealed tests` read as no field at all and switched
        the actionability check off."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_em", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        self.assertTrue(cp._holdout_required("hold-out — required: 2 sealed tests"))
        self.assertTrue(cp._holdout_required("hold-out: required: 2 sealed tests"))
        self.assertFalse(cp._holdout_required("hold-out — not required"))

    def test_the_plan_pointer_survives_markdown(self):
        """`POINTER` allowed none of the prefixes every REQUIRED pattern allows and
        nothing after the path, and the miss was a NOTE — so the description was
        validated *as* the plan and a leftover `Risk: trivial` line in it skipped
        every check while the real plan file was never opened."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_ptr", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        for line in ("CTDD-Plan: docs/plans/PAY-1.md",
                     "- CTDD-Plan: docs/plans/PAY-1.md",
                     "**CTDD-Plan:** docs/plans/PAY-1.md",
                     "`CTDD-Plan: docs/plans/PAY-1.md`",
                     "CTDD-Plan: docs/plans/PAY-1.md (committed)"):
            m = cp.POINTER.search(line)
            self.assertIsNotNone(m, f"not recognised: {line!r}")
            self.assertEqual(m.group(1), "docs/plans/PAY-1.md", line)

    def test_the_holdout_block_stops_at_the_next_section(self):
        """`(?=\\n\\s*\\n|\\Z)` ended on a blank line or end-of-document, so in a plan
        written without blank lines the block ran to EOF: any stray `options:` or
        `recommended:` below satisfied the actionability check, including
        `rollout options:` and `recommended: none needed` in the last line."""
        plan = FULL_PLAN.replace("hold-out: not required",
                                 "hold-out: required: 2 sealed tests").replace(
            "Hold-out: not required — read path",
            "Hold-out: required: 2 sealed tests\n- request: 2 sealed tests from the human")
        import re as _re
        # Replace, not append — a second `Residual risk` trips the duplicate check
        # first and the guard would never reach the block it is testing.
        plan = _re.sub(r"(?m)^Residual risk:.*$",
                       "Residual risk: rollout options: single deploy; "
                       "recommended: none needed", plan)
        r = run(plan)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("HOLD-OUT NOT ACTIONABLE", r.stdout)

    def test_the_v32_gate_integrity_changes_are_guarded(self):
        """Six gate-integrity changes shipped in one commit that touched the test
        file only to lower a floor and add one unrelated case: TRIVIAL
        line-anchoring, tier/triviality/hold-out reading the categorical line
        alone, order-independent field matching, `--diff` refusing empty input,
        `--diff` counting ADR surface, and the `text.find` off-by-one in the
        duplicate scan. All six behave as claimed — this is unguarded surface, and
        the identical condition in the predecessor survived two releases."""
        import importlib.util, tempfile, os, subprocess, sys as _s, re as _re
        spec = importlib.util.spec_from_file_location("cp_v32", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)

        # 1. TRIVIAL is line-anchored: a mid-line mention is not a declaration.
        self.assertFalse(cp.TRIVIAL.search("we rejected the risk: trivial lane"))
        self.assertTrue(cp.TRIVIAL.search("Risk: trivial — one-line typo fix"))

        # 2/3. tier and hold-out read the categorical line, whatever the order.
        for line in ("Risk: normal · contract: none · hold-out: not required",
                     "Risk: normal · hold-out: not required · contract: none"):
            self.assertTrue(cp.CATEGORICAL_LINE.search(line), line)
        prose = ("Risk: normal · contract: additive · hold-out: not required\n"
                 "The wire contract: none of it changes shape.\n"
                 "New-behavior tests:\n- t\n")
        self.assertEqual(cp.plan_tier(prose), "large",
                         "prose must not decide the tier")

        # 4/5. --diff refuses empty input and counts ADR surface.
        def diff(content):
            f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                            encoding="utf-8")
            f.write(content); f.close()
            plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                               encoding="utf-8")
            plan.write("A summary long enough to read as a decision summary.\n"
                       "Risk: trivial — rename only. Skipping the plan gate.\n")
            plan.close()
            try:
                return subprocess.run(
                    [_s.executable, SCRIPT, plan.name, "--diff", f.name],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=15)
            finally:
                os.unlink(f.name); os.unlink(plan.name)
        self.assertEqual(diff("").returncode, 2, "an empty diff verified nothing")
        adr = diff("M\tdocs/adr/0007-x.md")
        self.assertEqual(adr.returncode, 1, adr.stdout)

        # 6. the duplicate scan reads a final line with no trailing newline.
        one = ("A summary long enough to read as a decision summary.\n"
               "Risk: normal · contract: none · ADR: none · hold-out: not required\n"
               "Residual risk: none")   # deliberately unterminated
        self.assertNotIn("DUPLICATED", run(one).stdout)

    def test_fenced_content_is_quoted_not_declared(self):
        """Every pattern is line-anchored and none was context-aware, so a plan
        quoting a withdrawn declaration, a superseded amendment or a copied worked
        example inside a fence had that text read as live. `Risk: trivial` in a
        fence skipped all nineteen checks — and the format's own worked example is
        fenced, so quoting it was enough."""
        fenced = ("A summary long enough to read as the decision summary here.\n\n"
                  "## Superseded amendment (withdrawn at step 3.7)\n"
                  "```\nRisk: trivial - one-line typo fix\n```\n")
        r = run(fenced)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn("trivial-skip declaration found", r.stdout)

    def test_every_required_section_can_be_reported_missing(self):
        """The duplicate scan excludes the categorical `Risk: … · contract: …` line
        because the `risk level` pattern matches it too; the missing scan did not,
        so that line satisfied the `Risk level:` section and deleting the section
        outright still exited 0 — the one required section that could never be
        reported missing, and the one every tier keys on."""
        import re as _re
        # The fixture must carry a categorical line, or deleting `Risk level:`
        # fails for the ordinary reason and the guard never exercises the bug:
        # the categorical line is what satisfied the section.
        base = FULL_PLAN
        self.assertEqual(run(base).returncode, 0, run(base).stdout)
        without = "\n".join(l for l in base.split("\n")
                            if not _re.match(r"\s*Risk level\s*:", l))
        r = run(without)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("risk level", r.stdout)

    def test_the_honest_declaration_never_costs_more_than_an_empty_one(self):
        """`_names_a_test` inferred "a test exists" from the *absence* of the word
        `none`, so the tier inverted: an honest `New-behavior tests: none — pure
        refactor` derived large, while headings left empty with no test named
        anywhere derived medium and passed at 15 of 19. The v0.30.0 guard was
        defeated by deleting a word, and an agent that noticed was rewarded for the
        less honest plan."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_inv", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        cat = "Risk: normal · contract: none · ADR: none · hold-out: not required\n"
        honest = cat + ("New-behavior tests: none — pure refactor\n"
                        "Preservation pins: none — covered by the suite\n")
        empty = cat + "New-behavior tests\nPreservation pins\n"
        self.assertEqual(cp.plan_tier(honest), "large")
        self.assertEqual(
            cp.plan_tier(empty), "large",
            "empty lanes must not reach a lighter tier than the same plan that "
            "says `none` out loud")
        # and naming a test in either lane still earns a lighter tier
        named = cat + ("New-behavior tests: none — refactor\n"
                       "Preservation pins — must pass:\n- `pin_holds`\n")
        self.assertEqual(cp.plan_tier(named), "small")

    def test_the_decision_summary_is_checked(self):
        """The one section a human reads at the gate, invisible to the linter:
        deleting it from the format's own example still exited 0 at 19 of 19.
        It is the plan's opening prose with no heading of its own, so it is
        checked against the known headings rather than by a pattern of its own —
        a first attempt matched any opening line and passed on a plan starting
        with `BLOCKING`."""
        self.assertEqual(run(FULL_PLAN).returncode, 0)
        without = FULL_PLAN.split("\n", 1)[1]
        r = run(without)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("MISSING the decision summary", r.stdout)

    def test_unresolved_paths_fail_the_gate(self):
        """Field rule 9 is mechanically checkable and was unchecked. These paths
        feed `check-redstate --tests-from`, so the gate blessed paths no test file
        can be written to."""
        base = FULL_PLAN.replace("- a.cs", "- `payments/api/Capture.cs`")
        self.assertEqual(run(base).returncode, 0, run(base).stdout)
        for bad in ("payments/**/*.cs", "payments/api/",
                    "payments/api/Capture.cs (+ tests)", "payments/api/TBD.cs"):
            r = run(base.replace("`payments/api/Capture.cs`", f"`{bad}`"))
            self.assertEqual(r.returncode, 1, f"{bad!r} accepted:\n{r.stdout}")
            self.assertIn("UNRESOLVED PATHS", r.stdout)

    def test_the_plan_revision_digest_changes_with_the_plan(self):
        """`the current plan revision` was named in the write freeze and defined
        nowhere. 8.6 edits the plan in place at the same path, so a pre-amendment
        Approval record was textually identical to a current one — and one pilot
        plan ran to 28 amendment rounds."""
        import re as _re
        a = _re.search(r"plan revision ([0-9a-f]{12})", run(FULL_PLAN).stdout)
        b = _re.search(r"plan revision ([0-9a-f]{12})",
                       run(FULL_PLAN.replace("capture", "capturing", 1)).stdout)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertNotEqual(a.group(1), b.group(1))

    def test_both_lanes_none_derives_large_in_every_heading_style(self):
        """v0.30.0 made both lanes declaring `none` derive `large`, because a plan
        naming no test in either lane passed at 8 of 19 with no red-state log, no
        pin log and no ctdd-tests invocation — step 8's `satisfied every applicable
        evidence lane` met vacuously, weaker than the trivial lane it was built to
        close.

        That fix shipped with no tests, and its own regex omitted the heading
        prefix every REQUIRED pattern allows — so `## New-behavior tests: none`
        missed the guard and still derived `small`. A cosmetic markdown choice
        decided whether a zero-test plan passed the gate."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_lanes", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        base = ("Risk: normal · contract: none · ADR: none · hold-out: not required\n"
                "{p}New-behavior tests — must be observed failing: none — refactor\n"
                "{p}Preservation pins — must pass before and after: none — covered\n")
        for prefix in ("", "## ", "### ", "- ", "* ", "**"):
            self.assertEqual(
                cp.plan_tier(base.format(p=prefix)), "large",
                f"a plan with {prefix!r} headings and no test in either lane "
                f"must not reach a lighter tier")

    def test_a_named_test_in_either_lane_still_allows_a_lighter_tier(self):
        """The guard must not simply force everything to large."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_lanes2", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        base = ("Risk: normal · contract: none · ADR: none · hold-out: not required\n"
                "## New-behavior tests — must be observed failing: none — refactor\n"
                "## Preservation pins — must pass before and after:\n"
                "- `capture_rounds_half_up` — path: `t.cs`; case: legacy behavior.\n")
        self.assertEqual(cp.plan_tier(base), "small")

    def test_the_tier_is_derived_from_declarations_not_claimed(self):
        """The 2026-07-27 Flik plan ran to 31,448 chars — ~14 minutes to read at
        the gate, 5.8x the canonical example — because the format had one gear
        and v0.23.0's triviality fix routed every fresh change into it. Tiers
        shrink documentation, never evidence: both test headings, the gate, and
        verification stay required at every tier. And the tier is a function of
        the categorical line, so `small` cannot be asserted over a contract
        delta the way `trivial` once could be asserted over an absent diff."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_tier", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)

        base = ("Risk: normal · contract: none · ADR: none · hold-out: not required\n"
                "New-behavior tests — must be observed failing:\n- t\n")
        # `small` means behaviour-preserving, which still has to name the pins it
        # preserves — the earlier fixture declared `none` in the new-behaviour lane
        # and carried no preservation lane at all, so it named no test anywhere and
        # was encoding the inverted predicate it was written to guard.
        preserving = base.replace(
            "failing:\n- t\n",
            "failing: none — unchanged\nPreservation pins — must pass:\n- `pin_holds`\n")
        self.assertEqual(cp.plan_tier(preserving), "small")
        self.assertEqual(cp.plan_tier(base), "medium")
        self.assertEqual(cp.plan_tier(base.replace("contract: none", "contract: additive")), "large")
        self.assertEqual(cp.plan_tier(base.replace("Risk: normal", "Risk: high-risk")), "large")
        self.assertEqual(
            cp.plan_tier(base.replace("hold-out: not required", "hold-out: required: 2 sealed")),
            "large")

    def test_not_required_is_not_read_as_required(self):
        """`hold-out: not required` contains the word `required`. The first
        pattern matched it and made every plan large; a negative lookahead did
        not help because `\\s*` backtracks to zero width and steps over it."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_ho", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        self.assertFalse(cp._holdout_required("hold-out: not required"))
        self.assertTrue(cp._holdout_required("hold-out: required: 2 sealed tests"))

    def test_every_tier_keeps_both_test_headings_and_verification(self):
        """Tiers shrink documentation, never evidence. If a tier could drop a
        test heading or the verification commands, it would rebuild the
        triviality hole under a friendlier name."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_sec", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        for tier in ("small", "medium", "large"):
            names = {n for n, _ in cp.required_for(tier)}
            for must in ("proposed tests: new-behavior heading",
                         "proposed tests: preservation-pin heading",
                         "verification", "risk level", "files to change"):
                self.assertIn(must, names, f"{tier} dropped {must}")

    def test_the_plan_directory_is_configurable_but_cannot_escape(self):
        """`docs/plans/` was a rejection, not a default: a repo keeping plans
        anywhere else could not use the CTDD-Plan pointer at all. It is now
        `planDir` in `.ctdd.json` — validated exactly as strictly as the pointer
        it gates, because this runs in CI over untrusted MR descriptions. The
        first cut stripped before validating, which turned `/etc` into `etc` and
        walked it straight through the check meant to stop it."""
        import importlib.util, json as _json
        spec = importlib.util.spec_from_file_location("cp_pd", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        root = tempfile.mkdtemp()
        def cfg(v):
            with open(os.path.join(root, ".ctdd.json"), "w", encoding="utf-8") as fh:
                _json.dump({"planDir": v}, fh)
            return cp.plan_dir(root)
        self.assertEqual(cfg(".plans"), ".plans")
        self.assertEqual(cfg("plans/"), "plans")
        for hostile in ("../etc", "/etc", "C:/x", "a\\b", ""):
            self.assertEqual(cfg(hostile), cp.PLAN_DIR_DEFAULT,
                             f"{hostile!r} must not be accepted")

    def test_a_duplicated_section_fails_the_gate(self):
        """2026-08-03: the plan was rewritten 28 times with 16 silent-failing `sed`
        calls, one of which spliced a duplicate section in. The agent caught it by
        hand; this checker passed the corrupt file 19/19 because presence-at-least-
        once was all it asked. The gate cannot tell which copy was approved."""
        plan = FULL_PLAN.replace("Assumptions:\n- y\n", "Assumptions:\n- y\nAssumptions:\n- y\n")
        r = run(plan)
        self.assertEqual(r.returncode, 1)
        self.assertIn("DUPLICATED sections", r.stdout)
        self.assertIn("assumptions", r.stdout)

    def test_the_categorical_line_is_not_counted_as_a_duplicate_risk_section(self):
        """`Risk: ... · contract: ... · hold-out: ...` is matched by the `risk level`
        pattern too, because that pattern makes `level` optional on purpose. Every
        correct plan has both lines, so counting it would fail every plan."""
        r = run(FULL_PLAN)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("DUPLICATED", r.stdout)

    def test_a_required_holdout_without_options_fails_the_gate(self):
        """2026-08-03 wrote `request: 2 sealed tests written and withheld by the
        human` — the unbounded phrasing plan-format rule 6 exists to replace — with
        no options and no recommendation. The human had to ask "what is my task".
        Seven declines and one deferral, and not once was the work named."""
        plan = FULL_PLAN.replace(
            "hold-out: not required", "hold-out: required: 2 sealed tests").replace(
            "Hold-out: not required — read path",
            "Hold-out: required: 2 sealed tests\n- request: 2 sealed tests from the human")
        r = run(plan)
        self.assertEqual(r.returncode, 1)
        self.assertIn("HOLD-OUT NOT ACTIONABLE", r.stdout)

    def test_a_required_holdout_with_options_and_a_recommendation_passes(self):
        plan = FULL_PLAN.replace(
            "Hold-out: not required — read path",
            "Hold-out: required: 2 sealed tests\n"
            "- request: assert the remaining authorized amount after capturing 33.33 of 100.00\n"
            "- options: `write` ~5 minutes; `decline` recorded as declined by human\n"
            "- recommended: `write` — the edge came from the same document the code reads")
        r = run(plan)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_holdout_that_is_not_required_needs_no_options(self):
        r = run(FULL_PLAN)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("HOLD-OUT", r.stdout)

    def test_a_single_test_heading_fails_the_gate(self):
        """Both headings are mandatory, even when one is empty. A plan with only
        one has no correct lane at step 7 — the default check reads pins as new
        tests, --expect-pass finds no pin section — so the gate is where that
        must be caught, not after approval with the tests already written."""
        for single in ("New-behavior tests — must be observed failing first:\n- t\n",
                       "Preservation pins — must pass before and after:\n- currently_x\n"):
            plan = FULL_PLAN.replace(
                "New-behavior tests — must be observed failing first:\n- t\n"
                "Case coverage not reached: none — every applicable row is covered\n"
                "Preservation pins — must pass before and after: none\n", single)
            r = run(plan)
            self.assertEqual(r.returncode, 1, f"single heading must fail:\n{r.stdout}")


    def test_missing_decision_summary_buckets_fail(self):
        plan = FULL_PLAN.replace("BLOCKING — I will not guess:", "Open questions:")
        plan = plan.replace("Proceeding unless you object:", "Decided:")
        r = run(plan)
        self.assertEqual(r.returncode, 1)
        self.assertIn("BLOCKING", r.stdout)
        self.assertIn("proceeding", r.stdout.lower())

    def test_compressed_bug_fix_adding_a_test_is_reported_as_its_own_lane(self):
        # The ordinary CTDD bug fix: one-line code fix + a NEW regression test.
        # It is not the trivial lane, but the message must not claim an
        # "edit to an existing test" — nothing existing was edited.
        d = diff_file("A\ttests/Payments/NullGuardTests.cs\nM\tsrc/Payments/Handler.cs\n")
        try:
            r = run("Risk: trivial — one-line null guard\n", ["--diff", d])
            self.assertEqual(r.returncode, 1)
            self.assertIn("ADDS", r.stdout)
            self.assertIn("compressed", r.stdout)
            self.assertNotIn("edit to an existing test", r.stdout)
        finally:
            os.unlink(d)

    def test_added_test_plus_contract_change_is_not_the_compressed_lane(self):
        d = diff_file("A\ttests/PayTests.cs\nM\tpayments/contract/openapi.yaml\n")
        try:
            r = run("Risk: trivial — tiny\n", ["--diff", d])
            self.assertEqual(r.returncode, 1)
            self.assertIn("edit to an existing test or a contract file", r.stdout)
        finally:
            os.unlink(d)

    def test_from_description_validates_the_pointed_at_plan(self):
        d = tempfile.mkdtemp()
        plans = Path(d) / "docs" / "plans"; plans.mkdir(parents=True)
        (plans / "PAY-1-x.md").write_text(FULL_PLAN, encoding="utf-8")
        cwd = os.getcwd(); os.chdir(d)
        try:
            r = run("Implements partial capture.\n\nCTDD-Plan: docs/plans/PAY-1-x.md\n",
                    ["--from-description"])
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("canonical plan", r.stdout)
        finally:
            os.chdir(cwd)

    def test_from_description_missing_file_names_the_gitignore_cause(self):
        r = run("CTDD-Plan: docs/plans/nope.md\n", ["--from-description"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("git-ignored", r.stdout)

    def test_from_description_rejects_traversal(self):
        r = run("CTDD-Plan: ../../etc/passwd\n", ["--from-description"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("traverse", r.stdout)

    def test_from_description_rejects_path_outside_docs_plans(self):
        r = run("CTDD-Plan: notes/myplan.md\n", ["--from-description"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("where this\nrepository keeps plans".replace("\n", " "), r.stdout)

    def test_from_description_falls_back_with_a_nudge_when_no_pointer(self):
        r = run(FULL_PLAN, ["--from-description"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no `CTDD-Plan:` pointer", r.stdout)

    def test_from_description_trivial_claim_still_validated_directly(self):
        d = diff_file("M\tsrc/Handler.cs\n")
        try:
            r = run("Risk: trivial — rename a local\n", ["--from-description", "--diff", d])
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            os.unlink(d)

    def test_both_stdin_is_usage_error(self):
        r = run("Risk: trivial — x. Skipping.\n", ["--diff", "-"])
        self.assertEqual(r.returncode, 2)

    def test_help_exits_zero(self):
        r = subprocess.run([sys.executable, SCRIPT, "--help"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        self.assertEqual(r.returncode, 0)
        self.assertIn("omission detector", r.stdout)


class ComposedCheckerTests(unittest.TestCase):
    """The standalone checker refusing malformed input is not enough: check-plan
    imports the same parser, and a fail-open there turns 'could not parse' into
    'no surface touched', which passes an unverified trivial claim."""

    def test_trivial_claim_fails_when_authoritative_classifier_is_unavailable(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            scripts = Path(d) / "scripts"
            scripts.mkdir()
            for name in ("check-plan.py", "check-spec-surface.py"):
                shutil.copy(Path(__file__).resolve().parent / name, scripts / name)
            plan = Path(d) / "plan.md"
            diff = Path(d) / "diff.txt"
            plan.write_text("Risk: trivial — rename only\n", encoding="utf-8")
            diff.write_text("M\tsrc/PaymentTests.cs\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(scripts / "check-plan.py"),
                                str(plan), "--diff", str(diff)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        self.assertEqual(r.returncode, 2)
        self.assertIn("authoritative spec-surface classifier", r.stderr)
        self.assertNotIn("trivial claim survives", r.stdout)

    def test_help_does_not_print_literal_newline_escapes(self):
        r = subprocess.run([sys.executable, SCRIPT, "--help"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("\\nA diff", r.stdout)

    def test_trivial_claim_with_malformed_diff_fails_closed(self):
        import subprocess, sys, os, tempfile
        d = tempfile.mkdtemp()
        plan = os.path.join(d, "plan.md")
        diff = os.path.join(d, "diff.txt")
        Path(plan).write_text(
            "Risk: trivial — code-only formatting change. Skipping the plan gate.\n",
            encoding="utf-8")
        # space-separated, not the tab-separated name-status format
        Path(diff).write_text("M tests/payment_tests.py\n", encoding="utf-8")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-plan.py")
        r = subprocess.run([sys.executable, script, plan, "--diff", diff],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 2, f"must not pass over discarded input:\n{r.stdout}")
        self.assertIn("unparseable", r.stdout)
        self.assertNotIn("trivial claim survives", r.stdout)

    def test_parser_does_not_leak_state_between_calls(self):
        """Malformed lines are returned, not accumulated in module state, so one
        caller cannot inherit another's leftovers."""
        import importlib.util, os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-spec-surface.py")
        spec = importlib.util.spec_from_file_location("cs", path)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        _, bad = mod.parse_name_status("M nope\n")
        self.assertEqual(len(bad), 1)
        entries, bad2 = mod.parse_name_status("M\ttests/ok.py\n")
        self.assertEqual(bad2, [], "a clean second call must not inherit the first's malformed lines")
        self.assertEqual(len(entries), 1)

    def test_prose_mentioning_blocking_does_not_satisfy_the_bucket_check(self):
        """The bucket patterns matched the words anywhere in the document, so
        'nothing here is blocking and I am proceeding unless something breaks'
        satisfied both buckets with neither heading present. A presence detector
        that matches prose is not detecting the presence of what it names."""
        import subprocess, sys, os, tempfile
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("A summary line long enough to read as the decision summary.\n"
                   "Risk: normal · contract: none · ADR: none · hold-out: not required\n"
                   "Risk level: normal.\n"
                   "Nothing here is blocking and I am proceeding unless something breaks.\n"
                   "Existing behavior: x\nAssumptions: none\n"
                   "Uncovered or ambiguous: none\n"
                   "New-behavior tests — must be observed failing first:\n- some_test\n"
                   "Preservation pins — must pass before and after: none\n"
                   "Contract changes: none\nNFR budgets: none\n"
                   "Hold-out: not required. result: n/a\nFiles likely to change: y\n")
        plan.close()
        try:
            r = subprocess.run([sys.executable, os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "check-plan.py"), plan.name],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 1)
            self.assertIn("BLOCKING", r.stdout)
        finally:
            os.unlink(plan.name)

    def test_surplus_or_misspelled_arguments_are_refused(self):
        """A diff passed as a positional, or `--from-descriptino`, used to be
        discarded in silence — so a typo disabled the only deterministic
        triviality cross-check while the run still exited 0."""
        import subprocess, sys, os, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-plan.py")
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("Risk: trivial — docs only. Skipping the plan gate.\n"); plan.close()
        diff = tempfile.NamedTemporaryFile("w", suffix=".status", delete=False, encoding="utf-8")
        diff.write("M\ttests/Changed.cs\n"); diff.close()
        try:
            r = subprocess.run([sys.executable, script, plan.name, diff.name],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 2, f"surplus positional:\n{r.stdout}")
            self.assertIn("extra argument", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(diff.name)

    def test_prose_mentioning_section_names_is_not_a_plan(self):
        """Only the two buckets were line-anchored; the rest matched category
        words anywhere, so a paragraph merely mentioning them passed as though
        every section existed."""
        plan = ("BLOCKING — none.\nProceeding unless you object: x.\n"
                "Risk level: normal — local change.\n"
                "New-behavior tests — must be observed failing first:\n- a_test\n"
                "Preservation pins — must pass before and after: none\n\n"
                "This paragraph mentions existing behavior, assumptions, uncovered and\n"
                "ambiguous cases, contract changes, NFR budgets, hold-out, and files to\n"
                "change, but defines none of them as sections.\n")
        r = run(plan)
        self.assertEqual(r.returncode, 1, f"prose mentions are not sections:\n{r.stdout}")


if __name__ == "__main__":
    unittest.main(verbosity=1)
