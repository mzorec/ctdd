#!/usr/bin/env python3
"""Tests for check-plan.py — pinning the section checks, the trivial-skip
exemption, the newline bypass fix, and the new trivial-vs-diff cross-check.

Run:  python3 scripts/test_check_plan.py   (or via pytest)
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "check-plan.py")
NL = chr(10)

FULL_PLAN = """Allow one capture below the authorized amount while preserving over-capture rejection.
Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required
BLOCKING — I will not guess: none — answered before approval
Proceeding unless you object:
- zero capture rejected
Business requirement: allow one capture below the authorized amount
Intended behavior: capture accepts 0 < amount <= authorized and moves to CAPTURED
Risk level: normal — money path
Existing behavior (openapi.yaml; CaptureTests.cs):
- x
Behavior flow:
Current flow:
1. capture requires amount == authorized
Flow after change:
1. (changed) capture accepts 0 < amount <= authorized
Assumptions:
- y
Uncovered / ambiguous:
- z
Structure:
- Types: none new.
- Ports: none touched.
- Configuration: none.
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
- invariants: none — this fixture has no rule suite
- `dotnet test --filter t` — expected: passes after the slice lands
Hold-out: not required — read path
Files likely to change:
- a.cs
Residual risk: none beyond the planned verification
"""


# The same plan while its BLOCKING question is still open: correct at 5.4, and
# what an approval must not be recorded over.
STILL_ASKING = FULL_PLAN.replace(
    "BLOCKING — I will not guess: none — answered before approval" + chr(10),
    "BLOCKING — I will not guess:" + chr(10)
    + "- auth hold on the released remainder? (recommend: expires with the auth)" + chr(10))


def run(plan_text, extra_args=None, env=None):
    merged = dict(os.environ)
    merged.pop("CTDD_LAYERS", None)          # tests decide the layer config
    merged.pop("CTDD_HARNESSES", None)       # and the harness kinds
    merged.pop("CLAUDE_PROJECT_DIR", None)   # and the repository root pins resolve in
    merged.update(env or {})
    return subprocess.run([sys.executable, SCRIPT, "-"] + (extra_args or []),
                          input=plan_text, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=15, env=merged)


def diff_file(content):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    f.write(content); f.close()
    return f.name


class CheckPlanTests(unittest.TestCase):

    def test_full_plan_passes(self):
        r = run(FULL_PLAN)
        self.assertEqual(r.returncode, 0)
        self.assertIn("all mandatory sections present", r.stdout)

    def test_the_flow_narrative_is_mandatory_above_small(self):
        """v0.41.0: a plan carried behavior as one Intended-behavior sentence
        plus test bullets, so the gate reader could not reconstruct the runtime
        flow or see how it changes. All three headings are checked - parent and
        both blocks - because a subheading required by format prose alone is
        the finding-#39 failure shape."""
        for gone, named in (("Behavior flow:\n", "behavior flow"),
                            ("Current flow:\n", "current flow"),
                            ("Flow after change:\n", "flow after change")):
            broken = FULL_PLAN.replace(gone, "")
            r = run(broken)
            self.assertEqual(r.returncode, 1, f"{named}: {r.stdout}")
            self.assertIn("MISSING sections", r.stdout)
            self.assertIn(named, r.stdout)

    def test_the_flow_accepts_british_spelling_and_the_greenfield_escape(self):
        brit = FULL_PLAN.replace("Behavior flow:", "Behaviour flow:")
        self.assertEqual(run(brit).returncode, 0, run(brit).stdout)
        green = FULL_PLAN.replace(
            "Current flow:\n1. capture requires amount == authorized\n",
            "Current flow: none — greenfield\n")
        self.assertEqual(run(green).returncode, 0, run(green).stdout)

    def test_a_small_plan_omits_the_flow_narrative(self):
        """Tiers shrink documentation, never evidence: small means no new
        behavior, so there is no after-flow to narrate and the section is
        conditional, like the other five the small tier drops."""
        small = FULL_PLAN.replace(
            "New-behavior tests — must be observed failing first:\n- t\n",
            "New-behavior tests: none — behavior preserved\n")
        small = small.replace(
            "Preservation pins — must pass before and after: none\n",
            "Preservation pins — must pass before and after:\n- keeps_capture_shape\n")
        for line in ("Behavior flow:\n", "Current flow:\n",
                     "1. capture requires amount == authorized\n",
                     "Flow after change:\n",
                     "1. (changed) capture accepts 0 < amount <= authorized\n"):
            small = small.replace(line, "")
        r = run(small)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("small plan", r.stdout)

    def test_missing_sections_fail_and_are_named(self):
        r = run("A summary line long enough to read as the decision summary.\n"
                "Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
                "Risk level: normal — x\nExisting behavior: y\nAssumptions: z\n"
                "Uncovered: q\nNew-behavior tests — must be observed failing first:\n- t\n"
                "Preservation pins — must pass before and after: none\nContract changes: none\n"
                "Files likely to change: a\n")
        self.assertEqual(r.returncode, 1)
        # `NFR budgets` is conditional below `large`, and this plan derives
        # medium; assert on a section every tier requires. Named by the
        # plan's own heading, not the checker's internal key.
        self.assertIn("BLOCKING — I will not guess", r.stdout)
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

    def test_trivial_contradicted_by_a_settings_change(self):
        """`.ctdd.json` decides what this cross-check calls surface, so a diff
        that changes it was read under settings the diff itself wrote."""
        d = diff_file("M\t.ctdd.json\nM\tsrc/foo.cs\n")
        try:
            r = run("Risk: trivial — small cleanup. Skipping the plan gate.\n",
                    ["--diff", d])
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("TRIVIAL CLAIM CONTRADICTED — the diff changes `.ctdd.json`",
                          r.stdout)
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
        # v0.43.0 moved the category from a mid-line `case: <x>;` field onto the
        # first line of a multi-line bullet, so the old `case: ([a-z ]+);` regex
        # found nothing and `assertTrue(used)` caught it. That regex also carried
        # a hole worth not reproducing: `[a-z ]` excludes commas, so every
        # multi-category bullet (`case: positive, side effect;`) matched nothing
        # and was never checked at all. Parse by position and split on commas,
        # which covers them.
        used = set()
        lines = fmt[fmt.find("## Complete example"):].split(chr(10))
        for head in ("New-behavior tests", "Preservation pins"):
            self.assertIn(head, lines, f"the example lost its `{head}` section")
            for line in lines[lines.index(head) + 1:]:
                if not line.strip():
                    break
                # Backticks separate a test bullet from the `Case coverage not
                # reached` rows (`- authorization — n/a — ...`), which would
                # otherwise contribute `n/a` as a category.
                for cases in _re.findall(r"^- `[^`]+` — (.+)$", line):
                    used |= {c.strip().lower() for c in cases.split(",")}
        self.assertTrue(used, "the example names no case categories")
        # The table names the class (`Side effects`); a bullet names one instance
        # of it (`side effect`), which is also the value the schema line lists.
        trim = lambda s: s.rstrip("s")
        unknown = {c for c in used if trim(c) not in {trim(d) for d in defined}}
        self.assertEqual(unknown, set(),
                         f"the example cites categories the table does not define: "
                         f"{sorted(unknown)}")

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

        tok = gate_token_of(FULL_PLAN)
        self.assertEqual(
            with_record(f'Approved by: "looks right, go"; plan: p.md@{rev}. '
                        f'gate-token: {tok}.\n').returncode,
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
                        "Risk: normal · ADR: none · red pause: skip · hold-out: not required",
                        # The full pre-v0.42.0 line: only `red pause:` is absent,
                        # so a silently-never-pausing plan is the rejected shape.
                        "Risk: normal · contract: none · ADR: none · hold-out: not required"):
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
        for line in ("Risk: normal · contract: none · red pause: skip · hold-out: not required",
                     "Risk: normal · red pause: skip · hold-out: not required · contract: none"):
            self.assertTrue(cp.CATEGORICAL_LINE.search(line), line)
        prose = ("Risk: normal · contract: additive · red pause: skip · hold-out: not required\n"
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
               "Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
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

    def test_the_adr_field_is_cross_checked_against_the_diff(self):
        """`ADR: NNNN required` sits on a mandatory line and was validated by
        nothing — only `contract` and `hold-out` were — so a plan could name a
        decision record and never write one, or say `ADR: none` while the diff
        rewrote one."""
        import tempfile, os, subprocess, sys as _s

        def with_diff(decl, diff):
            d = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                            encoding="utf-8")
            d.write(decl); d.close()
            f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                            encoding="utf-8")
            f.write(diff); f.close()
            try:
                return subprocess.run([_s.executable, SCRIPT, d.name, "--diff", f.name],
                                      capture_output=True, text=True,
                                      encoding="utf-8", errors="replace", timeout=15)
            finally:
                os.unlink(d.name); os.unlink(f.name)

        trivial = "Risk: trivial - rename only. Skipping the plan gate.\n"
        # claims an ADR, writes none
        r = with_diff(trivial + "ADR: 0017 required\n", "M\tsrc/Handler.cs\n")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("claims an ADR", r.stdout)
        # claims none, rewrites one
        r2 = with_diff(trivial, "M\tdocs/adr/0007-x.md\n")
        self.assertEqual(r2.returncode, 1, r2.stdout)
        # neither: unaffected
        self.assertEqual(with_diff(trivial, "M\tsrc/Handler.cs\n").returncode, 0)

    def test_a_claimed_retarget_requires_its_section(self):
        """4.5 routes a changed existing assertion as an amendment and rule 3 gives
        it a section, but the section is conditional and nothing tied it to its
        trigger — so a change carried entirely by retargeting an assertion could
        declare both evidence lanes `none` and pass with the amendment recorded
        nowhere."""
        import re as _re
        claim = FULL_PLAN.replace(
            "Risk level:", "Intended behavior: the change retargets the existing "
            "assertion.\nRisk level:", 1)
        claim = _re.sub(r"(?im)^Changed existing assertions.*$", "", claim)
        r = run(claim)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Changed existing assertions", r.stdout)
        # a plan that claims nothing of the sort is unaffected
        self.assertEqual(run(FULL_PLAN).returncode, 0)

    def test_a_prose_bullet_is_not_a_named_test(self):
        """`_BULLET_NAME` matched the first word of any bullet, so *- We will add
        coverage once the shape settles.* counted as a test named `We`: the plan
        passed at 19 of 19, step 8's Enter then could not be met, and the packet
        still rendered clean. The sentence exclusion added for the unparsed-bullet
        check exempted it from being reported, too."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_prose", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        cat = "Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
        tail = "Preservation pins: none — n/a\n"
        for prose in ("- We will add coverage once the shape settles.\n",
                      "- The team agreed to defer this.\n"):
            self.assertFalse(
                cp._names_a_test(cat + "New-behavior tests\n" + prose + tail),
                f"a sentence is not a test name: {prose!r}")
        for real in ("- `capture_rejects_zero` — path: `t.cs`.\n",
                     "- capture_rejects_zero\n",
                     "- capture-rejects-zero — path: x.\n"):
            self.assertTrue(
                cp._names_a_test(cat + "New-behavior tests\n" + real + tail),
                f"a real name must still count: {real!r}")

    def test_a_none_bullet_is_not_a_named_test(self):
        """`_BULLET_NAME` read the word `none` as an identifier, so the evidence-lane
        guard **rejected the form plan-format rule 4 mandates** (`Preservation
        pins: none — <reason>`) and **accepted** `- none — <reason>` as a named
        test. That is the tier inversion this guard was written to close,
        reintroduced through the guard — rule 8 not applied to its own fix."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("cp_none", SCRIPT)
        cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)
        cat = "Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
        head = cat + "New-behavior tests: none — refactor\n"
        for pins in ("Preservation pins: none — no existing tests.\n",
                     "Preservation pins\n- none — the touched area has none.\n",
                     "Preservation pins\n- n/a — nothing to pin.\n",
                     "Preservation pins\n- TBD\n"):
            self.assertEqual(
                cp.plan_tier(head + pins), "large",
                f"a lane declaring nothing must not name a test:\n{pins}")
        named = head + "Preservation pins\n- `capture_rounds_half_up` — path: `t.cs`.\n"
        self.assertEqual(cp.plan_tier(named), "small")

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
        cat = "Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
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
        base = ("Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
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
        base = ("Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
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

        base = ("Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
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
        """`Risk: ... · contract: ... · red pause: skip · hold-out: ...` is matched by the `risk level`
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

    ACTIONABLE_HOLDOUT = (
        "Hold-out: required: 2 sealed tests\n"
        "- request: assert the remaining authorized amount after capturing 33.33 of 100.00\n"
        "- options: `write` ~5 minutes; `decline` recorded as declined by human\n"
        "- recommended: `write` — the edge came from the same document the code reads\n"
        "- result: {}")

    def _holdout(self, result):
        """Both edits are needed. `_holdout_required` reads the categorical line
        alone, so replacing only the section leaves the check dormant and the
        test green for the wrong reason — which is how the first draft of these
        tests passed against a defect they were written to catch."""
        return (FULL_PLAN
                .replace("hold-out: not required",
                         "hold-out: required: 2 sealed tests")
                .replace("Hold-out: not required — read path",
                         self.ACTIONABLE_HOLDOUT.format(result)))

    def test_a_deferred_holdout_result_is_rejected(self):
        """`defer` was struck from 9.1's options in v0.43.0 as the identical
        escape under another name. A real session answered the prompt with
        `Defer / NOT RUN` anyway, and the plan recorded `result: NOT RUN,
        deferred by the human ... (not a decline)` — load-bearing boundary
        evidence left neither owed nor waived, which is the state
        `declined by human` exists to record. The prompt is prose and was
        ignored; the result is written into the plan, so it is judged there."""
        r = run(self._holdout("NOT RUN — deferred by the human at packet time"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("defers", r.stdout)

    def test_the_sanctioned_holdout_results_are_accepted(self):
        """The other way to get this wrong is to reject everything. `NOT RUN`
        stays legitimate for a runner that is genuinely unavailable."""
        for value in ("pending", "passed", "declined by human",
                      "NOT RUN — the sealed runner is not installed here"):
            r = run(self._holdout(value))
            self.assertEqual(r.returncode, 0,
                             "%r was rejected:\n%s" % (value, r.stdout))

    def test_an_unsanctioned_holdout_result_is_rejected(self):
        """`maybe later` records neither an outcome nor a waiver, so the packet
        cannot say what became of the evidence."""
        r = run(self._holdout("maybe later"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("not one of", r.stdout)

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
                   "Risk: normal · contract: none · ADR: none · red pause: skip · hold-out: not required\n"
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



def revision(plan_text):
    """The 12-hex revision check-plan prints for a plan."""
    r = run(plan_text)
    m = re.search(r"plan revision ([0-9a-f]{12})", r.stdout)
    assert m, "no revision printed:" + chr(10) + r.stdout
    return m.group(1)


def gate_token_of(plan_text):
    """The 8-hex gate token, read back from `--gate` rather than recomputed.

    Recomputing the derivation here would make these tests pass against a
    checker whose own two call sites disagree - the defect
    `test_both_digest_call_sites_agree` exists to catch for the revision."""
    r = run(plan_text, ["--gate"])
    m = re.search(r"Gate token: ([0-9a-f]{8})", r.stdout)
    assert m, "no gate token printed:" + chr(10) + r.stdout
    return m.group(1)


HOLDOUT_PLAN = FULL_PLAN.replace(
    "hold-out: not required", "hold-out: required: 1 sealed test").replace(
    "Hold-out: not required " + chr(8212) + " read path",
    "Hold-out" + chr(10)
    + "- decision: required" + chr(10)
    + "- reason: money-path boundary semantics" + chr(10)
    + "- request: 1 sealed test asserting the response for a capture of 33.33."
    + chr(10)
    + "- options: `write` " + chr(8212) + " ~5 minutes; `decline` " + chr(8212)
    + " recorded as a waiver." + chr(10)
    + "- recommended: `write` " + chr(8212) + " the edge came from the same "
    "document the implementation reads." + chr(10)
    + "- storage: separate repository" + chr(10)
    + "- runner: CI hold-out job" + chr(10)
    + "- result: pending" + chr(10)
    + "- human-verified expected values: n/a")


class GatePresentationTests(unittest.TestCase):
    """`--gate` emits the step 6.1 presentation instead of prose describing it.

    Written from a real session: across eleven consecutive gates the agent
    printed the plan path, the summary and the risk line, and compressed every
    other gate-visible section - `Behavior flow`'s seven-step walk became a
    one-line prose arrow, the hold-out's nine fields became a sentence. The
    human approved eleven changes on sections they had not seen in full. The
    sections were reconstructed from memory each time; when the agent finally
    read the file, the output was correct. Every other step of this workflow
    has a mechanical check. What reached the terminal at the gate did not.
    """

    START = ("---- gate presentation: copy this block into your reply unaltered; "
             "the human does not see tool output ----")
    END = "---- end of gate presentation ----"

    def _block(self, out):
        self.assertIn(self.START, out)
        return out[out.index(self.START) + len(self.START):out.index(self.END)]

    def test_every_gate_visible_section_is_emitted_in_the_rows_order(self):
        b = self._block(run(FULL_PLAN, ["--gate"]).stdout)
        seen = [s for s in ("Hold-out", "Behavior flow", "Known gaps",
                            "Assumptions", "Uncovered", "Test altitude")
                if s in b]
        self.assertEqual(["Hold-out", "Behavior flow", "Known gaps",
                          "Assumptions", "Uncovered", "Test altitude"], seen)
        self.assertLess(b.index("Hold-out"), b.index("Behavior flow"))
        self.assertLess(b.index("Behavior flow"), b.index("Known gaps"))
        self.assertLess(b.index("Known gaps"), b.index("Test altitude"))

    def test_behavior_flow_carries_its_own_subheadings(self):
        """Its body is a numbered walk under `Current flow` and `Flow after
        change`. Cutting the section at the next heading would print the
        narrative's title and none of the narrative - which is the compression
        this flag exists to remove, reproduced by the flag itself."""
        b = self._block(run(FULL_PLAN, ["--gate"]).stdout)
        self.assertIn("Current flow", b)
        self.assertIn("Flow after change", b)
        self.assertIn("capture requires amount == authorized", b)
        self.assertIn("(changed) capture accepts", b)

    def test_the_summary_is_emitted_verbatim(self):
        """The summary has no heading - it is the prose above the categorical
        line - so it is the one gate-visible part with nothing marking it, and
        6.2 copies it verbatim into any plan-mode surface."""
        b = self._block(run(FULL_PLAN, ["--gate"]).stdout)
        self.assertIn("Allow one capture below the authorized amount while "
                      "preserving over-capture rejection.", b)
        self.assertIn("Decision summary, verbatim:", b)

    def test_the_categorical_line_is_emitted(self):
        b = self._block(run(FULL_PLAN, ["--gate"]).stdout)
        self.assertIn("Risk: normal", b)
        self.assertIn("hold-out: not required", b)

    def test_the_plan_path_and_derived_tier_lead_the_block(self):
        b = self._block(run(FULL_PLAN, ["--gate"]).stdout)
        self.assertRegex(b.strip(), r"^Plan: .*\((small|medium|large)\)")

    def test_the_post_approval_tail_is_never_presented(self):
        """`approved_region`, not the raw text: 7.12 appends `## Intended
        change` after approval, so a re-gate reading the whole file would put
        the un-approved tail in front of the human as though it were part of
        what they are approving."""
        # `Uncovered / ambiguous` is moved last so its slice runs to EOF.
        # With the tail still in the text that slice swallows it; the section
        # keeps its bounds only because the region rule cut the tail first.
        moved = (FULL_PLAN.replace("Uncovered / ambiguous:" + NL + "- z" + NL, "")
                 + "Uncovered / ambiguous:" + NL + "- z" + NL)
        tail = (moved + "## Intended change" + NL + NL
                + "| File | Intended change |" + NL + "| --- | --- |" + NL
                + "| `a.cs` | Accepts the lower amount. |" + NL)
        b = self._block(run(tail, ["--gate"]).stdout)
        self.assertIn("- z", b)
        self.assertNotIn("Intended change", b)
        self.assertNotIn("Accepts the lower amount", b)

    def test_a_tier_that_omits_a_section_is_not_reported_as_missing(self):
        """Tiers shrink documentation. A small-tier plan correctly has no
        `Known gaps`, and demanding it would make the flag reject plans the
        checker itself accepts."""
        r = run(FULL_PLAN, ["--gate"])
        self.assertEqual(0, r.returncode)
        self.assertNotIn("MISSING from the plan file", self._block(r.stdout))

    def test_a_required_section_that_is_absent_is_named_as_missing(self):
        """Silence would let the flag paper over the hole rather than show it."""
        stripped = FULL_PLAN.replace("Assumptions:" + NL + "- y" + NL, "")
        r = run(stripped, ["--gate"])
        self.assertNotEqual(0, r.returncode)
        self.assertNotIn(self.START, r.stdout)

    def test_no_gate_block_is_printed_for_a_plan_that_fails_its_checks(self):
        """A presentation for a plan the workflow has not cleared would put a
        human in front of an approval surface that does not validate."""
        r = run("too short" + NL, ["--gate"])
        self.assertNotEqual(0, r.returncode)
        self.assertNotIn(self.START, r.stdout)

    def test_the_altitude_table_travels_inside_the_block(self):
        """5.4 says re-run until this exits 0, so on 0 the table printed with
        the checker's own diagnostics reached nobody - the defect v0.52.0 fixed
        by naming it gate-visible. It stays fixed by travelling with the rest."""
        b = self._block(run(FULL_PLAN, ["--gate"]).stdout)
        self.assertIn("Test altitude", b)
        self.assertIn("t  ? | ?", b)

    def test_without_the_flag_nothing_changes(self):
        """Report-shaped addition: the flag is opt-in, and 5.4's run must be
        byte-identical to what it was before the flag existed."""
        bare = run(FULL_PLAN)
        self.assertEqual(0, bare.returncode)
        self.assertNotIn(self.START, bare.stdout)
        self.assertIn("check-plan: test altitude", bare.stdout)
        self.assertIn("plan revision", bare.stdout)

    def test_a_label_repeated_in_prose_does_not_replace_the_section(self):
        """First occurrence wins. A later line mentioning `Known gaps` is a
        cross-reference; taking it as the section would emit one stray line
        where the gate needs the list."""
        withref = FULL_PLAN.replace(
            "Residual risk: none beyond the planned verification",
            "Known gaps were listed above and are unchanged." + NL
            + "Residual risk: none beyond the planned verification")
        b = self._block(run(withref, ["--gate"]).stdout)
        self.assertIn("Known gaps: none — the caller contract is covered", b)

class PlanRevisionTests(unittest.TestCase):
    """The revision counted edits the skill itself mandates after approval.

    7.12: append the intended-change table to the plan as `## Intended
    change`, "dating it after approval " + a record of what will be built,
    never part of what was approved". Rule 7: before the packet, replace
    `result: pending`. Rule 8: on a decline, list the human-verified expected
    values. All three land after the Approval record is written, and the
    digest was sha256 over every byte " so obeying the skill invalidated the
    approval it had just recorded, and two real changes each spent a turn
    writing a note saying nothing approved had changed.

    One of the two statements had to be wrong. "Never part of what was
    approved" is the deliberate one, so the digest follows the prose.
    """

    def setUp(self):
        self.assertEqual(run(HOLDOUT_PLAN).returncode, 0,
                         "the hold-out fixture must pass before it can pin "
                         "anything about revisions")

    def test_appending_the_intended_change_table_keeps_the_approval(self):
        before = revision(HOLDOUT_PLAN)
        after = revision(
            HOLDOUT_PLAN + chr(10) + "## Intended change" + chr(10)
            + "Appended after approval; not part of what was approved."
            + chr(10) + "| File | Intended change |" + chr(10) + "|---|---|"
            + chr(10) + "| a.cs | Accept the lower amount. |" + chr(10))
        self.assertEqual(after, before,
                         "7.12 mandates this append and calls it no part of "
                         "the approval, so it cannot invalidate the approval")

    def test_the_mandated_holdout_field_edits_keep_the_approval(self):
        before = revision(HOLDOUT_PLAN)
        for label, edited in (
            ("rule 7 result", HOLDOUT_PLAN.replace("- result: pending",
                                                   "- result: declined by human")),
            ("rule 8 values",
             HOLDOUT_PLAN.replace("- human-verified expected values: n/a",
                                  "- human-verified expected values: 33.33 "
                                  "captures, state CAPTURED")),
        ):
            self.assertEqual(revision(edited), before,
                             label + " is mandated after approval, so it "
                             "cannot invalidate the approval")

    def test_the_exemption_does_not_swallow_an_ordinary_edit(self):
        """A region-scoped digest goes vacuous by exempting too much. This is
        the assertion that keeps it honest, and it is the reason values are
        normalised rather than lines dropped."""
        before = revision(HOLDOUT_PLAN)
        for label, edited in (
            ("prose in an ordinary section",
             HOLDOUT_PLAN.replace("Residual risk: none beyond the planned "
                                  "verification",
                                  "Residual risk: the expiry path is unpinned")),
            ("the result LABEL deleted outright",
             HOLDOUT_PLAN.replace("- result: pending" + chr(10), "")),
            ("the expected-values LABEL deleted outright",
             HOLDOUT_PLAN.replace(
                 "- human-verified expected values: n/a" + chr(10), "")),
            # These two are what distinguish normalising the value from
            # dropping the line, and finding them took three tries. Deleting
            # the line moves the revision either way, because the blank line it
            # leaves behind is itself a difference; so does duplicating it, for
            # the same reason. What only normalising catches is an edit to the
            # LABEL - the rule mandates replacing the value, not rewriting the
            # field, and an agent regenerating the block can easily emit a
            # different casing or bullet.
            ("the result LABEL re-cased",
             HOLDOUT_PLAN.replace("- result: pending", "- Result: pending")),
            ("the result line's bullet changed",
             HOLDOUT_PLAN.replace("- result: pending", "* result: pending")),
            ("the result line DUPLICATED by a splice",
             HOLDOUT_PLAN.replace("- result: pending",
                                  "- result: pending" + chr(10)
                                  + "- result: passed")),
            # Renamed in both places a real rename touches. Renaming only the
            # lane left the slice claiming `t`, which the altitude check now
            # rejects as an UNKNOWN TEST before any revision is printed - the
            # first fixture it caught was this repo's own.
            ("a test name in an evidence lane",
             HOLDOUT_PLAN.replace("- t" + chr(10), "- t_renamed" + chr(10))
                         .replace("turns green: `t`", "turns green: `t_renamed`")),
        ):
            self.assertNotEqual(revision(edited), before,
                                label + " is not a mandated post-approval "
                                "edit and must still read STALE")

    def test_both_digest_call_sites_agree(self):
        """The printed revision and the one `--approval` compares against are
        two call sites. Normalising one and not the other would make every
        plan read stale for the opposite reason."""
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d) / "p.md"
            plan.write_text(HOLDOUT_PLAN, encoding="utf-8")
            rev = revision(HOLDOUT_PLAN)
            rec = Path(d) / "p.approval.log"
            # A typed message, not the bare option label: the label is now its
            # own failure, and this test is about the two digest call sites.
            rec.write_text("Approved by: " + chr(34) + "looks right, go" + chr(34)
                           + "; plan: p.md@" + rev + "."
                           + " gate-token: " + gate_token_of(HOLDOUT_PLAN) + "."
                           + chr(10), encoding="utf-8")
            # the mandated append lands after the record is written
            plan.write_text(HOLDOUT_PLAN + chr(10) + "## Intended change"
                            + chr(10) + "Dated after approval." + chr(10),
                            encoding="utf-8")
            r = subprocess.run(
                [sys.executable, SCRIPT, str(plan), "--approval", str(rec)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15)
            self.assertNotIn("APPROVAL STALE", r.stdout,
                             "the two digest call sites disagree, so the "
                             "mandated append still voids the approval:"
                             + chr(10) + r.stdout)
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_required_section_cannot_hide_in_the_unapproved_tail(self):
        """`## Intended change` runs to EOF, because under `phased` its body
        carries `## Phase N` headings that bounding at the next heading would
        leave inside the digest. The cost is that anything below it is also
        exempt, so the one thing that would matter is checked."""
        r = run(HOLDOUT_PLAN + chr(10) + "## Intended change" + chr(10)
                + "Dated after approval." + chr(10) + chr(10)
                + "Residual risk: moved below the approval line." + chr(10))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("UN-APPROVED TAIL", r.stdout, r.stdout)


class ApprovalProvenanceTests(unittest.TestCase):
    """6.4 wants an affirmative typed message, and the record quotes it — but a
    quoted option label satisfied that check, and an option label is what an
    interactive selector returns. This is observed, not hypothetical: a gate was
    resolved with the highlighted default while the human typed an unrelated
    slash command, the agent quoted `"Approve"`, this checker said the record was
    verified, and the production edit ran.

    REVERSED 2026-09-21, intent-born: the owner asked for selectable options at
    every stop, the gate included, so a bare label is now a legitimate way to
    approve and rejecting it outright would fail every gate. What the guard
    still refuses is a label that does not say how it arrived, because a label
    alone reads the same whether the human chose it or a selector resolved on a
    default. Traceability, not prevention; prevention moved to the harness with
    the owner's decision, and that cost is recorded beside the route ratchet.
    """

    def record(self, message, plan_text=None):
        plan_text = FULL_PLAN if plan_text is None else plan_text
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d) / "p.md"
            plan.write_text(plan_text, encoding="utf-8")
            rec = Path(d) / "p.approval.log"
            rec.write_text("Approved by: " + chr(34) + message + chr(34)
                           + "; plan: p.md@" + revision(plan_text) + "."
                           + " gate-token: " + gate_token_of(plan_text) + "."
                           + chr(10), encoding="utf-8")
            return subprocess.run(
                [sys.executable, SCRIPT, str(plan), "--approval", str(rec)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15)

    def test_an_option_label_is_not_a_typed_approval(self):
        """The exact record that shipped the unapproved edit."""
        r = self.record("Approve")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("option label", r.stdout)

    def test_a_label_that_says_it_was_selected_is_approval(self):
        """The shape the reversal exists to allow. Before 2026-09-21 this was a
        failure; after it, refusing it would stop every gate the owner asked to
        be answered with a click."""
        r = self.record('approve" (selected at the gate)')
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("approval record verified", r.stdout)

    def test_a_label_that_says_it_was_typed_is_approval(self):
        """The escape hatch that predates the reversal still works, so a human
        who really typed the word is not pushed into claiming a selection."""
        r = self.record('approve" (typed at the gate)')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_refusal_asks_for_provenance_rather_than_a_retyped_message(self):
        """The message is the whole instruction the agent acts on. Left as-is it
        would tell the agent to re-present a gate the human already answered,
        which is the round-trip the reversal removes."""
        r = self.record("Approve")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("does not say how it arrived", r.stdout)
        self.assertIn("selected at the gate", r.stdout)
        self.assertNotIn("re-present the gate", r.stdout)

    def test_every_label_6_3_prints_is_caught_however_it_is_cased(self):
        for label in ("approve", "APPROVE", "Approve.", "Approve with changes",
                      "reject"):
            r = self.record(label)
            self.assertEqual(r.returncode, 1,
                             label + " reads as a typed message:" + chr(10)
                             + r.stdout)
            self.assertIn("option label", r.stdout)

    def test_the_canonical_typed_approval_survives_the_guard(self):
        """`worked-change.md` quotes a sentence that ends in the word Approved.
        Stripping punctuation to catch `Approve.` must not reach into it."""
        r = self.record("release the remainder when the authorization "
                        "expires. Approved.")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("approval record verified", r.stdout)

    def test_a_typed_message_that_merely_contains_a_label_survives(self):
        for message in ("approve, but watch the rounding",
                        "I approve", "looks right, go"):
            r = self.record(message)
            self.assertEqual(r.returncode, 0,
                             message + " is a typed message and must pass:"
                             + chr(10) + r.stdout)


class GateTokenTests(unittest.TestCase):
    """The revision alone cannot show the gate presentation was ever rendered:
    every run prints it, so a record can name the right revision while the
    human saw nothing. That is not hypothetical — it is how an 8.6 amendment
    was approved from the agent's summary of what changed rather than from the
    plan's own decision summary, which 8.6 requires and the agent skipped.

    The token is printed ONLY inside the block, so a record carrying it is
    evidence the block was rendered somewhere a human could read it.
    Traceability, not proof: an agent determined to fake it can recompute the
    digest. It closes the accident, not the lie.
    """

    def record(self, token_line, plan_text=None):
        plan_text = FULL_PLAN if plan_text is None else plan_text
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d) / "p.md"
            plan.write_text(plan_text, encoding="utf-8")
            rec = Path(d) / "p.approval.log"
            rec.write_text("Approved by: " + chr(34) + "looks right, go"
                           + chr(34) + "; plan: p.md@" + revision(plan_text)
                           + "." + token_line + chr(10), encoding="utf-8")
            return subprocess.run(
                [sys.executable, SCRIPT, str(plan), "--approval", str(rec)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15)

    def test_the_token_is_printed_only_inside_the_gate_block(self):
        """Its whole value rests on this. Printed among the summary lines every
        run emits, it could be quoted by an agent that never rendered the
        block, and it would be checking nothing."""
        plain = run(FULL_PLAN)
        self.assertEqual(plain.returncode, 0, plain.stdout)
        self.assertNotIn("Gate token:", plain.stdout)
        out = run(FULL_PLAN, ["--gate"]).stdout
        self.assertIn("Gate token:", out)
        self.assertLess(out.index("---- gate presentation:"),
                        out.index("Gate token:"), out)
        self.assertLess(out.index("Gate token:"),
                        out.index("---- end of gate presentation ----"), out)

    def test_a_record_without_a_token_is_not_approval(self):
        r = self.record("")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("no gate token", r.stdout)

    def test_the_refusal_names_the_token_the_record_should_carry(self):
        """The message is the whole instruction the agent acts on; without the
        value it would send the agent back to re-run the gate to read one
        number off it."""
        r = self.record("")
        self.assertIn("gate-token: " + gate_token_of(FULL_PLAN), r.stdout)

    def test_the_right_token_is_approval(self):
        r = self.record(" gate-token: " + gate_token_of(FULL_PLAN) + ".")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("approval record verified", r.stdout)

    def test_a_token_from_another_plan_is_caught(self):
        """The token is derived from the revision, so a stale one means the
        block the human read was a different plan."""
        r = self.record(" gate-token: " + gate_token_of(HOLDOUT_PLAN) + ".")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("GATE TOKEN MISMATCH", r.stdout)

    def test_a_waiver_passes_only_because_it_is_written_down(self):
        """Records predating this check are real approvals and must not be
        voided retroactively — but the gap is stated in the record rather than
        assumed by the reader."""
        r = self.record(" gate-token: n/a (predates gate tokens)")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("approval record verified", r.stdout)

    def test_a_stale_revision_is_still_reported_as_staleness(self):
        """Ordering: an amended plan must read STALE, not `no gate token`. The
        first names what happened; the second would send the agent to fix a
        record whose real problem is that the plan moved under it."""
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d) / "p.md"
            plan.write_text(FULL_PLAN, encoding="utf-8")
            rec = Path(d) / "p.approval.log"
            rec.write_text("Approved by: " + chr(34) + "go" + chr(34)
                           + "; plan: p.md@000000000000." + chr(10),
                           encoding="utf-8")
            r = subprocess.run(
                [sys.executable, SCRIPT, str(plan), "--approval", str(rec)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("APPROVAL STALE", r.stdout)
            self.assertNotIn("no gate token", r.stdout)


class DuplicateSectionShapeTests(unittest.TestCase):
    """Third instance of one defect: a NAME at the start of a line counted as
    a section, so any line merely labelled with one read as a duplicate.

    (1) A categorical line ordering its fields differently counted as a second
    `risk level`, patched by excluding that one line. (2) A decision-summary
    line labelled with a section name; the format's own example passes only
    because its labels are abbreviated far enough to evade this, which nothing
    recorded. (3) `Current flow, unchanged adjacent paths` " a heading the
    format demonstrates " rejected a valid plan as corrupt.

    Patching instances produced three of them, so the fix is the shape: this
    check counts SECTIONS, and a section heading is a line that is nothing but
    its own name. Latent fourth instance closed by the same rule: a plan with
    two `BLOCKING` questions, which the format positively invites.
    """

    def test_a_heading_that_continues_into_other_words_is_not_a_duplicate(self):
        r = run(FULL_PLAN.replace(
            "Flow after change:",
            "Current flow, unchanged adjacent paths:" + chr(10)
            + "- the refund path is untouched." + chr(10)
            + "Flow after change:"))
        self.assertEqual(r.returncode, 0,
                         "a compound heading beginning with a section name is "
                         "a different label, not a second section:" + chr(10)
                         + r.stdout)

    def test_a_summary_line_labelled_with_a_section_name_is_not_a_duplicate(self):
        r = run(FULL_PLAN.replace(
            "Risk level: normal",
            "- Existing behavior: unchanged on the read path." + chr(10)
            + "Risk level: normal"))
        self.assertEqual(r.returncode, 0,
                         "the gate-visible summary names one line per "
                         "refusable decision; labelling one with a section "
                         "name is not a second section:" + chr(10) + r.stdout)

    def test_two_blocking_questions_are_not_a_duplicate(self):
        r = run(STILL_ASKING.replace(
            "- auth hold on the released remainder? (recommend: expires with the auth)",
            "- auth hold on the released remainder? (recommend: expires with the auth)"
            + chr(10) + "BLOCKING: does the fee follow the partial amount?"))
        self.assertEqual(r.returncode, 0,
                         "a plan may carry more than one open question:"
                         + chr(10) + r.stdout)

    def test_a_genuinely_duplicated_heading_is_still_rejected(self):
        """Rule 8's own test: the shape rule must not have deleted the check.
        A corrupt plan spliced a duplicate section in and this checker passed
        it 19 of 19 by only asking whether each heading appeared at least
        once."""
        spliced = "Existing behavior (openapi.yaml; CaptureTests.cs):"
        self.assertIn(spliced, FULL_PLAN, "the heading to splice moved")
        r = run(FULL_PLAN + chr(10) + spliced + chr(10)
                + "- spliced in by a failed sed." + chr(10))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("DUPLICATED", r.stdout, r.stdout)



LAYERS = {"CTDD_LAYERS": "Domain;Application;Persistence"}


def layered_plan(test_path, owner_path, claim="`t`"):
    """FULL_PLAN with the one test given a path and the one slice given an owner."""
    return FULL_PLAN.replace(
        "New-behavior tests — must be observed failing first:" + chr(10) + "- t",
        "New-behavior tests — must be observed failing first:" + chr(10) + "- t"
        + chr(10) + "  - path: `" + test_path + "`.").replace(
        "- a.cs — accept the lower amount; turns green: `t`",
        "- `" + owner_path + "` — accept the lower amount; turns green: " + claim)


class TestAltitudeTests(unittest.TestCase):
    """Every test's level follows from which production file turns it green.
    `Implementation slices` already links them with `turns green:`, and a real
    plan wrote that link three times for nineteen tests, by wildcard. Nothing
    made the author say, per test, who owns the behaviour, and the altitude
    was wrong until the human asked. This was the fourth or fifth plan in a
    row where they had to. Two prose fixes preceded this and did not stop it.
    """

    def test_a_test_no_slice_turns_green_is_an_orphan(self):
        r = run(FULL_PLAN.replace("turns green: `t`", "no test named here"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("NO OWNER", r.stdout)
        self.assertIn("`t`", r.stdout.replace("t  ", "`t` "), r.stdout)

    def test_a_wildcard_claim_is_rejected_not_expanded(self):
        for claim in ("every `t_*` test", "the three `t?` tests"):
            r = run(FULL_PLAN.replace("turns green: `t`", "turns green: " + claim))
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("VAGUE OWNERSHIP", r.stdout, r.stdout)
            self.assertIn("wildcard", r.stdout, r.stdout)

    def test_a_claim_naming_no_test_is_rejected(self):
        r = run(FULL_PLAN.replace("turns green: `t`", "turns green: the boundary tests"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("VAGUE OWNERSHIP", r.stdout)
        self.assertIn("no test named", r.stdout)

    def test_a_claim_on_a_test_no_lane_names_is_unknown(self):
        """A misspelt claim would otherwise orphan the real test silently."""
        r = run(FULL_PLAN.replace("turns green: `t`", "turns green: `t_typo`"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("UNKNOWN TEST", r.stdout)
        self.assertIn("t_typo", r.stdout)

    def test_the_full_plan_and_a_claimed_pin_pass(self):
        self.assertEqual(run(FULL_PLAN).returncode, 0, run(FULL_PLAN).stdout)
        pinned = FULL_PLAN.replace(
            "Preservation pins — must pass before and after: none",
            "Preservation pins — must pass before and after:" + chr(10) + "- p_old").replace(
            "turns green: `t`", "turns green: `t`, `p_old`")
        r = run(pinned)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_small_tier_has_no_slices_and_is_not_checked(self):
        small = FULL_PLAN.replace(
            "New-behavior tests — must be observed failing first:" + chr(10) + "- t",
            "New-behavior tests: none — pure refactor").replace(
            "Preservation pins — must pass before and after: none",
            "Preservation pins — must pass before and after:" + chr(10) + "- p")
        r = run(small)
        self.assertNotIn("NO OWNER", r.stdout)
        self.assertNotIn("VAGUE", r.stdout)

    def test_the_table_prints_and_says_when_layers_are_unconfigured(self):
        r = run(FULL_PLAN)
        self.assertIn("test altitude", r.stdout)
        self.assertIn("layers not configured", r.stdout)

    def test_a_test_above_its_owner_is_misplaced(self):
        r = run(layered_plan("tests/Shop.Application.Tests/T.cs",
                             "src/Shop.Domain/Rule.cs"), env=LAYERS)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("MISPLACED", r.stdout)
        self.assertIn("above the Domain code", r.stdout, r.stdout)

    def test_a_test_below_its_owner_is_misplaced(self):
        r = run(layered_plan("tests/Shop.Domain.Tests/T.cs",
                             "src/Shop.Application/Handler.cs"), env=LAYERS)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("below the Application code", r.stdout, r.stdout)

    def test_a_test_at_its_owners_layer_passes(self):
        r = run(layered_plan("tests/Shop.Persistence.Tests/T.cs",
                             "src/Shop.Persistence/Repo.cs"), env=LAYERS)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Persistence | Persistence", r.stdout)

    def test_two_owners_mean_the_higher_layer(self):
        """A test turned green by a Domain rule and an Application handler must
        sit where it can observe both."""
        two = layered_plan("tests/Shop.Application.Tests/T.cs", "src/Shop.Domain/Rule.cs")
        two = two.replace(
            "Implementation slices:",
            "Implementation slices:" + chr(10)
            + "- `src/Shop.Application/Handler.cs` — wires the rule; turns green: `t`")
        r = run(two, env=LAYERS)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_layer_names_match_whole_segments_only(self):
        """A layer name inside an identifier is not that layer. The first version
        of this test used `DomainEvents.cs` under Application and was vacuous:
        matched bare, `Domain` (6) still loses to `Application` (11) under
        longest-match, so the boundary rule was masked and its probe did not
        fire. The load-bearing case needs the false substring to be the longest
        match: `PersistenceHelpers.cs` under Domain. Bounded, the owner is
        Domain and the Domain test sits at its layer; bare, `Persistence` wins
        and the same test reads as below its owner."""
        r = run(layered_plan("tests/Shop.Domain.Tests/T.cs",
                             "src/Shop.Domain/PersistenceHelpers.cs"), env=LAYERS)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Domain | Domain", r.stdout, r.stdout)
        # the original case, kept for intent; not what makes the probe fire
        r = run(layered_plan("tests/Shop.Application.Tests/T.cs",
                             "src/Shop.Application/DomainEvents.cs"), env=LAYERS)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_an_unclassifiable_path_never_reads_as_placed(self):
        r = run(layered_plan("tests/Misc/T.cs", "src/Shop.Domain/Rule.cs"), env=LAYERS)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("?", r.stdout)

    def test_the_owner_is_any_backticked_path_that_resolves_to_a_layer(self):
        """A real plan opened two phase bullets with a `.sql` path and a route
        name, so the first backticked token resolved to no layer and twenty of
        twenty-nine tests had owner `?`, which skipped the comparison. The plan
        was reworded only so the checker could find an owner."""
        plan = layered_plan("tests/Shop.Application.Tests/T.cs",
                            "db/SetState.sql").replace(
            "`db/SetState.sql` — accept",
            "`db/SetState.sql` and `src/Shop.Domain/Rule.cs` — accept")
        r = run(plan, env=LAYERS)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("MISPLACED", r.stdout)
        self.assertIn("above the Domain code", r.stdout, r.stdout)

    def test_an_owner_no_layer_resolves_is_said_not_skipped(self):
        """With layers configured, `?` means the comparison did not happen.
        That is said, in the plain run and inside the gate block."""
        plan = layered_plan("tests/Shop.Application.Tests/T.cs", "db/SetState.sql")
        r = run(plan, env=LAYERS)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("NOT PLACED", r.stdout)
        self.assertIn("t", r.stdout[r.stdout.index("NOT PLACED"):])
        g = run(plan, ["--gate"], env=LAYERS)
        block = g.stdout[g.stdout.index("---- gate presentation"):]
        self.assertIn("NOT PLACED", block)

    def test_malformed_slices_do_not_pass_silently(self):
        """Empty section, a slice with only prose, a lane with a bullet and no
        slices at all - each must reach a verdict about `t`, not a clean exit."""
        for broken in (
            FULL_PLAN.replace("- a.cs — accept the lower amount; turns green: `t`", ""),
            FULL_PLAN.replace("- a.cs — accept the lower amount; turns green: `t`",
                              "- a.cs — accept the lower amount."),
        ):
            r = run(broken)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("NO OWNER", r.stdout)


KINDS = "UnitTests;IntegrationTests"
UNIT_DIR = "tests/Shop.Application.UnitTests"
HEAVY_TEST = "tests/Shop.Application.IntegrationTests/T.cs"
HANDLER = "src/Shop.Application/Handler.cs"
REASON = "the unique index on the real database."


class HarnessTests(unittest.TestCase):
    """One layer, two test projects. The layer check reads a unit project and
    an integration project of one layer as the same place, so a real plan put
    seven handler tests in the heavier of the two, the table matched them all,
    and the human found it by reading project names. With `harnesses`
    configured, a test in a heavier project says what it needs from it,
    wherever a lighter project of the same layer exists to hold it instead.
    """

    def project(self, *dirs):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        for d in dirs:
            os.makedirs(os.path.join(root, d))
        return root

    def check(self, test_path=HEAVY_TEST, owner=HANDLER, dirs=(UNIT_DIR,), needs=None,
              kinds=KINDS, extra=None):
        plan = layered_plan(test_path, owner)
        if needs is not None:
            plan = plan.replace("  - path: `" + test_path + "`.",
                                "  - path: `" + test_path + "`." + NL + "  - needs: " + needs)
        env = dict(LAYERS, CLAUDE_PROJECT_DIR=self.project(*dirs))
        if kinds:
            env["CTDD_HARNESSES"] = kinds
        return run(plan, extra, env=env)

    def test_without_the_setting_nothing_is_asked_and_the_table_is_what_it_was(self):
        r = self.check(kinds=None)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("check-plan: test altitude — test layer | owning layer", r.stdout)
        self.assertIn("  t  Application | Application", r.stdout)
        self.assertNotIn("harness", r.stdout.lower())

    def test_a_heavier_test_beside_a_lighter_project_must_say_why(self):
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("HEAVIER HARNESS, NO REASON", r.stdout)
        self.assertIn("t sits in IntegrationTests (" + HEAVY_TEST + "); the same layer has "
                      "UnitTests beside it", r.stdout)
        # The refusal is where the line is taught: no skill or reference names it.
        self.assertIn("`  - needs: <", r.stdout)

    def test_a_reason_passes_and_is_printed_under_its_test(self):
        r = self.check(needs=REASON)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("check-plan: test altitude — test layer · harness | owning layer", r.stdout)
        lines = r.stdout.split(NL)
        row = lines.index("  t  Application · IntegrationTests | Application")
        self.assertEqual(lines[row + 1], "      needs: " + REASON)

    def test_the_reason_reaches_the_human_inside_the_gate_block(self):
        r = self.check(needs=REASON, extra=["--gate"])
        self.assertEqual(r.returncode, 0, r.stdout)
        block = r.stdout[r.stdout.index(GatePresentationTests.START):
                         r.stdout.index(GatePresentationTests.END)]
        self.assertIn("Test altitude — test layer · harness | owning layer", block)
        self.assertIn("  t  Application · IntegrationTests | Application" + NL
                      + "      needs: " + REASON, block)

    def test_no_gate_block_is_printed_while_a_reason_is_owed(self):
        r = self.check(extra=["--gate"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn(GatePresentationTests.START, r.stdout)

    def test_a_layer_with_one_test_project_is_not_asked(self):
        """Asked there, the question has one answer and every test gives it."""
        r = self.check(dirs=())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("  t  Application · IntegrationTests | Application", r.stdout)
        self.assertIn("no reason is asked of 1 test(s)", r.stdout)

    def test_the_lightest_harness_is_not_asked_and_shows_no_reason(self):
        r = self.check(test_path=UNIT_DIR + "/T.cs", needs="left over from a move.")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("  t  Application · UnitTests | Application", r.stdout)
        self.assertNotIn("needs:", r.stdout)

    def test_words_for_nothing_and_a_placeholder_are_not_a_reason(self):
        for said in ("none — a fake repository is enough.", "n/a", "Nothing.", "TBD",
                     "<what only that project can reach>", "", "—", "-"):
            r = self.check(needs=said)
            self.assertEqual(r.returncode, 1, repr(said) + NL + r.stdout)
            self.assertIn("HEAVIER HARNESS, NO REASON", r.stdout)

    def test_a_reason_that_only_begins_with_such_a_word_is_one(self):
        r = self.check(needs="none of the fakes models the unique index.")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_project_the_setting_does_not_name_is_said(self):
        """A `?` in the column reads like a test nobody had a question about."""
        r = self.check(test_path="tests/Shop.Application.Specs/T.cs")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("  t  Application · ? | Application", r.stdout)
        self.assertIn("HARNESS NOT NAMED", r.stdout)

    def test_only_the_lighter_projects_that_exist_are_named(self):
        three = "UnitTests;IntegrationTests;EndToEndTests"
        path = "tests/Shop.Application.EndToEndTests/T.cs"
        one = self.check(test_path=path, dirs=("tests/Shop.Application.IntegrationTests",), kinds=three)
        self.assertEqual(one.returncode, 1, one.stdout)
        self.assertIn("the same layer has IntegrationTests beside it", one.stdout)
        both = self.check(test_path=path, dirs=("tests/Shop.Application.IntegrationTests", UNIT_DIR),
                          kinds=three)
        self.assertIn("the same layer has UnitTests, IntegrationTests beside it", both.stdout)

    def test_the_rest_of_the_project_name_is_kept_when_looking_beside(self):
        """The directory that carries the kind is renamed, not replaced."""
        path = "tests/IntegrationTests.Shop.Application/T.cs"
        self.assertEqual(self.check(test_path=path, dirs=("tests/UnitTests.Shop.Application",)).returncode, 1)
        self.assertEqual(self.check(test_path=path, dirs=("tests/UnitTests",)).returncode, 0)

    def test_a_kind_named_by_a_folder_is_looked_for_as_a_folder(self):
        path, kinds = "tests/integration/Application/t.py", "unit;integration"
        r = self.check(test_path=path, dirs=("tests/unit",), kinds=kinds)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("the same layer has unit beside it", r.stdout)
        self.assertEqual(self.check(test_path=path, dirs=("tests/units",), kinds=kinds).returncode, 0)

    def test_a_kind_in_the_file_name_always_has_a_lighter_one(self):
        """A lighter file can sit in the same folder, so there is nothing on
        disk to look for and the question is always asked."""
        r = self.check(test_path="tests/Application/order.integration.test.ts", dirs=(),
                       kinds="unit;integration")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("HEAVIER HARNESS, NO REASON", r.stdout)

    def test_the_repository_file_configures_it(self):
        root = self.project(UNIT_DIR)
        with open(os.path.join(root, ".ctdd.json"), "w", encoding="utf-8") as fh:
            json.dump({"layers": LAYERS["CTDD_LAYERS"], "harnesses": KINDS}, fh)
        r = run(layered_plan(HEAVY_TEST, HANDLER), env={"CLAUDE_PROJECT_DIR": root})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("HEAVIER HARNESS, NO REASON", r.stdout)

    # ------------------------------------- the settings file, written wrong
    def settings(self, text):
        """The plan the check refuses, in a repository whose `.ctdd.json`
        holds `text`."""
        root = self.project(UNIT_DIR)
        with open(os.path.join(root, ".ctdd.json"), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return run(layered_plan(HEAVY_TEST, HANDLER), env={"CLAUDE_PROJECT_DIR": root})

    def test_lists_written_as_json_arrays_are_read(self):
        """Only a string was read, so an array was an unset key: `layers` and
        `harnesses` both went quiet and this plan passed with exit 0."""
        r = self.settings(json.dumps({"layers": LAYERS["CTDD_LAYERS"].split(";"),
                                      "harnesses": KINDS.split(";")}))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("HEAVIER HARNESS, NO REASON", r.stdout)

    def test_a_comma_after_the_last_entry_stops_the_check(self):
        """It dropped the whole file, `layers` included, and the plan passed."""
        r = self.settings('{"layers": "%s", "harnesses": "%s",}'
                          % (LAYERS["CTDD_LAYERS"], KINDS))
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("check-plan: `.ctdd.json` is not valid JSON", r.stdout)
        self.assertIn("not a pass", r.stdout)
        self.assertNotIn("test altitude", r.stdout)

    def test_a_known_key_holding_a_number_stops_the_check(self):
        r = self.settings('{"layers": "%s", "harnesses": 2}' % LAYERS["CTDD_LAYERS"])
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("check-plan: `.ctdd.json`: `harnesses` is a number", r.stdout)

    def test_a_misspelt_key_is_named_and_the_check_runs_without_it(self):
        r = self.settings('{"layers": "%s", "harness": "%s"}' % (LAYERS["CTDD_LAYERS"], KINDS))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("check-plan: `.ctdd.json` has a key this plugin does not read: "
                      "`harness`. Did you mean `harnesses`? It is ignored.", r.stderr)
        self.assertIn("check-plan: test altitude — test layer | owning layer", r.stdout)

    def test_an_unreadable_file_stops_it_before_it_names_the_plan_folder(self):
        """Carrying on would answer `docs/plans`, the default, for a
        repository whose file was pointing somewhere else."""
        root = self.project()
        with open(os.path.join(root, ".ctdd.json"), "w", encoding="utf-8") as fh:
            fh.write('{"planDir": "plans",}')
        r = run("", ["--plan-dir"], env={"CLAUDE_PROJECT_DIR": root})
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertNotIn("docs/plans", r.stdout)

    def test_a_misplaced_layer_is_settled_before_the_harness(self):
        """Moving a test to its owner's layer changes which project it is in,
        so asking about the project first would ask about the wrong one."""
        r = self.check(owner="src/Shop.Domain/Rule.cs")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("MISPLACED", r.stdout)
        self.assertNotIn("HEAVIER HARNESS", r.stdout)

    # ------------------------------------------------- a plan already approved
    def plan_run(self, root, *extra, kinds=KINDS):
        env = dict(os.environ, **LAYERS)
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.pop("CTDD_HARNESSES", None)
        if kinds:
            env["CTDD_HARNESSES"] = kinds
        return subprocess.run([sys.executable, SCRIPT, "p.md", *extra], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=20,
                              env=env, cwd=root)

    def approve(self, root, text):
        """Present the plan at a gate in a repository that names no harnesses
        yet, and record the approval."""
        Path(root, "p.md").write_text(text, encoding="utf-8")
        r = self.plan_run(root, "--gate", kinds=None)
        self.assertEqual(r.returncode, 0, r.stdout)
        rev = re.search(r"plan revision ([0-9a-f]{12})", r.stdout).group(1)
        tok = re.search(r"Gate token: ([0-9a-f]{8})", r.stdout).group(1)
        Path(root, "p.approval.log").write_text(
            f'Approved by: "approve" (typed at the gate); plan: p.md@{rev}; gate-token: {tok}' + NL,
            encoding="utf-8")

    def test_a_plan_approved_before_the_setting_is_not_asked(self):
        """Naming the harnesses in the middle of a change must not fail the
        plans already approved: that is a failure for a reason that is not the
        plan's, and its fix costs a gate."""
        root = self.project(UNIT_DIR)
        self.approve(root, layered_plan(HEAVY_TEST, HANDLER))
        r = self.plan_run(root)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("they sit where the plan you approved had them", r.stdout)

    def test_a_test_moved_into_a_heavier_project_after_approval_is_asked(self):
        root = self.project(UNIT_DIR)
        light = layered_plan(UNIT_DIR + "/T.cs", HANDLER)
        self.approve(root, light)
        Path(root, "p.md").write_text(with_amendment(
            light.replace(UNIT_DIR + "/T.cs", HEAVY_TEST),
            "- A1. Old: `t` sits in the unit project. New: `t` sits in the integration project."),
            encoding="utf-8")
        r = self.plan_run(root)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("HEAVIER HARNESS, NO REASON", r.stdout)

    def test_a_reason_given_at_approval_cannot_be_dropped_afterwards(self):
        """What was approved was the test there for that reason."""
        root = self.project(UNIT_DIR)
        reasoned = layered_plan(HEAVY_TEST, HANDLER).replace(
            "  - path: `" + HEAVY_TEST + "`.",
            "  - path: `" + HEAVY_TEST + "`." + NL + "  - needs: " + REASON)
        self.approve(root, reasoned)
        Path(root, "p.md").write_text(with_amendment(
            reasoned.replace(NL + "  - needs: " + REASON, ""),
            "- A1. Old: `t` says what it needs from the integration project. New: it says nothing."),
            encoding="utf-8")
        r = self.plan_run(root)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("HEAVIER HARNESS, NO REASON", r.stdout)

    def test_with_no_copy_of_the_approved_revision_nothing_is_asked(self):
        root = self.project(UNIT_DIR)
        self.approve(root, layered_plan(HEAVY_TEST, HANDLER))
        for kept in ("p.gate-shown.md", "p.gate-base.md"):
            if os.path.exists(os.path.join(root, kept)):
                os.remove(os.path.join(root, kept))
        self.assertEqual(self.plan_run(root).returncode, 0)


class SessionDefectTests(unittest.TestCase):
    """Checker failures one real change hit for reasons that were not the plan's.

    Six runs failed or misled: a hold-out bullet read as the hold-out section,
    a BLOCKING label naming no heading the plan has, an appended approval read
    as stale, UNRESOLVED PATHS on a method signature and on directory names in
    amendment prose, and a pin named at a path that did not exist while the
    checker passed it.
    """

    def test_a_holdout_bullet_elsewhere_is_not_the_holdout_section(self):
        """`- Hold-out: declined by human.` in an earlier section matched first,
        and the actionability check reported options and recommended missing
        from a block that had both. The block is the one carrying `decision:`."""
        plan = HOLDOUT_PLAN.replace(
            "- zero capture rejected" + NL,
            "- zero capture rejected" + NL + "- Hold-out: declined by human." + NL)
        r = run(plan)
        self.assertEqual(r.returncode, 0, r.stdout)
        g = run(plan, ["--gate"])
        block = g.stdout[g.stdout.index("---- gate presentation"):]
        self.assertIn("- decision: required", block)
        self.assertIn("- recommended:", block)

    def test_the_holdout_result_is_normalised_in_the_real_block(self):
        """The same locator feeds the revision. Replacing `result:` in the real
        block is post-approval by rule 7 and must not move it."""
        plan = HOLDOUT_PLAN.replace(
            "- zero capture rejected" + NL,
            "- zero capture rejected" + NL + "- Hold-out: declined by human." + NL)
        after = plan.replace("- result: pending", "- result: declined by human")
        self.assertEqual(revision(plan), revision(after))

    def test_a_missing_blocking_section_is_named_by_its_heading(self):
        broken = STILL_ASKING.replace(
            "BLOCKING — I will not guess:" + NL
            + "- auth hold on the released remainder? (recommend: expires with the auth)" + NL,
            "")
        r = run(broken)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("BLOCKING — I will not guess", r.stdout)
        self.assertNotIn("decision summary: BLOCKING", r.stdout)

    def test_a_missing_proceeding_section_is_named_by_its_heading(self):
        broken = FULL_PLAN.replace(
            "Proceeding unless you object:" + NL + "- zero capture rejected" + NL, "")
        r = run(broken)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Proceeding unless you object", r.stdout)
        self.assertNotIn("decision summary: proceeding", r.stdout)

    def test_the_size_line_prints_only_with_the_gate(self):
        long_plan = FULL_PLAN.replace(
            "- x" + NL, "- x " + ("word " * 1600) + NL, 1)
        self.assertNotIn("min to read", run(long_plan).stdout)
        self.assertIn("min to read", run(long_plan, ["--gate"]).stdout)

    def test_a_method_signature_in_prose_is_not_a_path(self):
        plan = FULL_PLAN.replace(
            "Proceeding unless you object:" + NL,
            "Amended at the review packet" + NL
            + "- Renamed with it: the `IOrderRepository.SetStateAsync(..., message, ...)` "
            "parameter." + NL + "Proceeding unless you object:" + NL)
        r = run(plan)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_method_signature_inside_a_slice_is_code_not_a_path(self):
        """Slices name the method that changes as often as the file. Scoping
        to file listings alone does not cover this one; the code-token rule
        does."""
        plan = FULL_PLAN.replace(
            "- a.cs — accept the lower amount; turns green: `t`",
            "- a.cs `IOrderRepository.SetStateAsync(..., message, ...)` — accept "
            "the lower amount; turns green: `t`")
        r = run(plan)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_with_no_decision_field_a_label_beats_an_earlier_bullet(self):
        """A `hold-out: not required` plan has no `decision:` field; an earlier
        bullet opening with `Hold-out` must still not become the section."""
        plan = FULL_PLAN.replace(
            "- zero capture rejected" + NL,
            "- zero capture rejected" + NL + "- Hold-out: see the section below." + NL)
        g = run(plan, ["--gate"])
        self.assertEqual(g.returncode, 0, g.stdout)
        block = g.stdout[g.stdout.index("---- gate presentation"):]
        self.assertIn("Hold-out: not required", block)
        self.assertNotIn("see the section below", block)

    def test_directory_names_in_prose_are_not_file_list_entries(self):
        plan = FULL_PLAN.replace(
            "Proceeding unless you object:" + NL,
            "Amended at verification" + NL
            + "- Two types move from `App/Abstractions/Persistence/` to "
            "`Domain/Orders/`." + NL + "Proceeding unless you object:" + NL)
        r = run(plan)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_file_lists_and_test_paths_are_still_checked(self):
        """The control for the two above: rule 9 still holds where files are
        listed - `Files likely to change`, slices, `Contract changes` and every
        `path:` line - including `(+ tests)` on a name with no directory."""
        for bad in ("payments/api/", "a.cs (+ tests)"):
            r = run(FULL_PLAN.replace("Files likely to change:" + NL + "- a.cs",
                                      "Files likely to change:" + NL + "- `" + bad + "`"))
            self.assertEqual(r.returncode, 1, f"{bad!r}: {r.stdout}")
            self.assertIn("UNRESOLVED PATHS", r.stdout)
        r = run(FULL_PLAN.replace(
            "New-behavior tests — must be observed failing first:" + NL + "- t",
            "New-behavior tests — must be observed failing first:" + NL + "- t"
            + NL + "  - path: `tests/*.cs`."))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("UNRESOLVED PATHS", r.stdout)

    def test_a_file_list_written_as_a_table_is_still_checked(self):
        r = run(FULL_PLAN.replace(
            "Files likely to change:" + NL + "- a.cs",
            "Files likely to change:" + NL + "| File | Change |" + NL
            + "| --- | --- |" + NL + "| `payments/api/` | x |"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("UNRESOLVED PATHS", r.stdout)

    def test_a_colocated_note_path_is_still_checked(self):
        """The Output contract writes a file at that path, so rule 9 holds."""
        r = run(FULL_PLAN.replace(
            "Contract changes: none" + NL,
            "Contract changes: none" + NL + "Colocated notes:" + NL
            + "- `payments/api/` — the rounding rule." + NL))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("UNRESOLVED PATHS", r.stdout)

    # ------------------------------------------------------------ pin paths
    PINNED = FULL_PLAN.replace(
        "Preservation pins — must pass before and after: none",
        "Preservation pins — must pass before and after:" + NL
        + "- `Mark_LeavesOrdersUnchanged` — legacy behavior" + NL
        + "  - path: `tests/Orders.Tests/OrderMarkTests.cs`." + NL
        + "- `Doc_HasNoEmptySummary` — legacy behavior" + NL
        + "  - path: `tests/Orders.Tests/PublicDocTests.cs`.").replace(
        "turns green: `t`", "turns green: `t`, `Mark_LeavesOrdersUnchanged`, "
        "`Doc_HasNoEmptySummary`")

    def _repo(self, files):
        root = Path(tempfile.mkdtemp())
        for rel, body in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
        return root

    def test_a_pin_whose_name_lives_in_another_file_fails(self):
        """The real case: the name existed in another class covering another
        document, at a path that did not exist, and the pin run passed."""
        root = self._repo({
            "tests/Orders.Tests/OrderMarkTests.cs": "void Mark_LeavesOrdersUnchanged() {}",
            "tests/Orders.Tests/Internal/InternalDocTests.cs": "void Doc_HasNoEmptySummary() {}",
        })
        r = run(self.PINNED, env={"CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("PIN NOT AT ITS PATH", r.stdout)
        self.assertIn("Doc_HasNoEmptySummary", r.stdout)
        self.assertIn("tests/Orders.Tests/Internal/InternalDocTests.cs", r.stdout)
        self.assertNotIn("Mark_LeavesOrdersUnchanged —", r.stdout)

    def test_a_pin_in_an_existing_file_that_lacks_it_fails_when_found_elsewhere(self):
        root = self._repo({
            "tests/Orders.Tests/OrderMarkTests.cs": "void Mark_LeavesOrdersUnchanged() {}",
            "tests/Orders.Tests/PublicDocTests.cs": "void Other() {}",
            "tests/Orders.Tests/Internal/InternalDocTests.cs": "void Doc_HasNoEmptySummary() {}",
        })
        r = run(self.PINNED, env={"CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("PIN NOT AT ITS PATH", r.stdout)

    def test_pins_at_their_paths_pass(self):
        root = self._repo({
            "tests/Orders.Tests/OrderMarkTests.cs": "void Mark_LeavesOrdersUnchanged() {}",
            "tests/Orders.Tests/PublicDocTests.cs": "void Doc_HasNoEmptySummary() {}",
        })
        r = run(self.PINNED, env={"CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("PIN NOT AT ITS PATH", r.stdout)

    def test_a_pin_not_yet_written_is_noted_not_failed(self):
        """7.5 writes pins against the current implementation, so a pin named
        nowhere in the repository is one step 7 will write - said, not failed."""
        root = self._repo({
            "tests/Orders.Tests/OrderMarkTests.cs": "void Mark_LeavesOrdersUnchanged() {}",
        })
        r = run(self.PINNED, env={"CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("not written yet", r.stdout)
        self.assertIn("Doc_HasNoEmptySummary", r.stdout)

    def test_with_no_repository_root_the_pins_are_said_unchecked(self):
        r = run(self.PINNED)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("pin paths not checked", r.stdout)

    # ------------------------------------------------------------ approval log
    def _approval(self, lines, plan_text=FULL_PLAN):
        d = Path(tempfile.mkdtemp())
        plan = d / "p.md"
        plan.write_text(plan_text, encoding="utf-8")
        rec = d / "p.approval.log"
        rec.write_text(NL.join(lines) + NL, encoding="utf-8")
        return subprocess.run(
            [sys.executable, SCRIPT, str(plan), "--approval", str(rec)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15)

    def _line(self, message, rev, token):
        return ('Approved by: "' + message + '" (typed at the gate); plan: p.md@'
                + rev + "; gate-token: " + token)

    def test_an_appended_approval_is_read_from_the_last_record(self):
        """The log was read at its first record, so appending the new approval
        reported STALE and the file had to be overwritten - losing the history
        of five approvals on one change."""
        old_plan = FULL_PLAN.replace("capture", "capturing", 1)
        r = self._approval([
            self._line("approve", revision(old_plan), gate_token_of(old_plan)),
            self._line("approve", revision(FULL_PLAN), gate_token_of(FULL_PLAN))])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("approval record verified", r.stdout)

    def test_a_stale_last_record_is_stale_whatever_came_before(self):
        old_plan = FULL_PLAN.replace("capture", "capturing", 1)
        r = self._approval([
            self._line("approve", revision(FULL_PLAN), gate_token_of(FULL_PLAN)),
            self._line("approve", revision(old_plan), gate_token_of(old_plan))])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("APPROVAL STALE", r.stdout)

    def test_earlier_records_are_history_and_never_judged(self):
        """A first record rejected for its bare label stays in the file; the
        current one is what is checked."""
        old_plan = FULL_PLAN.replace("capture", "capturing", 1)
        r = self._approval([
            'Approved by: "approve"; plan: p.md@' + revision(old_plan),
            self._line("approve", revision(FULL_PLAN), gate_token_of(FULL_PLAN))])
        self.assertEqual(r.returncode, 0, r.stdout)

    # ------------------------------------------------------------ --plan-dir
    def _git_repo(self, ignore):
        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(root)], check=True,
                       capture_output=True)
        if ignore:
            (root / ".gitignore").write_text("docs/plans/" + NL, encoding="utf-8")
        return root

    def _plan_dir(self, root):
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        return subprocess.run([sys.executable, SCRIPT, "--plan-dir"],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=15, cwd=str(root), env=env)

    def test_plan_dir_says_when_git_ignores_it(self):
        """Two gates told the human the plan directory was tracked; it was
        ignored. stdout stays the bare path, which 5.4 captures."""
        r = self._plan_dir(self._git_repo(ignore=True))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual("docs/plans", r.stdout.strip())
        self.assertIn("ignored by git", r.stderr)
        self.assertNotIn("not ignored", r.stderr)

    def test_plan_dir_says_when_git_does_not_ignore_it(self):
        r = self._plan_dir(self._git_repo(ignore=False))
        self.assertEqual("docs/plans", r.stdout.strip())
        self.assertIn("not ignored by git", r.stderr)

    def test_plan_dir_carries_step_5_5s_whole_instruction(self):
        """Step 5.5 says only `do what --plan-dir printed`. Its own sentence
        was displaced here, so each answer has to name the step and say
        everything that sentence said: what to commit, the pointer's exact
        form, what replaces it when the directory is ignored, and that a
        PR/MR may not exist yet."""
        tracked = self._plan_dir(self._git_repo(ignore=False)).stderr
        self.assertIn("Step 5.5: once the plan passes this checker, commit the plan file", tracked)
        self.assertIn("`CTDD-Plan: docs/plans/<name>.md`", tracked)
        self.assertIn("in the PR/MR description when there is one", tracked)
        ignored = self._plan_dir(self._git_repo(ignore=True)).stderr
        self.assertIn("Step 5.5: paste the complete plan into the PR/MR description "
                      "when there is one", ignored)
        self.assertIn("instead of a CTDD-Plan pointer", ignored)
        self.assertNotIn("commit the plan file", ignored)


STRUCTURE_LINES = ("Structure:" + NL + "- Types: none new." + NL
                   + "- Ports: none touched." + NL + "- Configuration: none." + NL)
ENTRY = ("- A1, at the phase 2 checkpoint. Old: zero capture is rejected with `400`. "
         "New: zero capture is rejected with `422`.")
ENTRY2 = "- A2, at the phase 3 checkpoint. Old: `a.cs` holds the rule. New: `b.cs` holds the rule."
# FULL_PLAN with one test that carries the sub-bullets a real plan writes.
LANE_PLAN = FULL_PLAN.replace(
    "New-behavior tests — must be observed failing first:" + NL + "- t" + NL,
    "New-behavior tests — must be observed failing first:" + NL
    + "- t — boundary" + NL
    + "  - covers: a `note` of 501 characters is rejected with `400`; 500 pass." + NL
    + "  - path: `tests/a_tests.cs`." + NL
    + "  - red: the stub has no rules." + NL)


def with_amendment(plan, *entries):
    """The plan with an `Amendments` section, where the format puts it."""
    return plan.replace("Business requirement:",
                        "Amendments" + NL + NL.join(entries) + NL + "Business requirement:", 1)


class AmendmentGateTests(unittest.TestCase):
    """What a re-presentation shows, and who decides how light it may be.

    One real change presented ten gates. Six of the nine re-presentations
    printed a block byte-identical to the one before, because the amendment
    sat in a section the gate does not show and the format had no place to
    record one; the agent hand-built a diff three times to say so. Four typed
    approvals were lost because the message that carried them also stated the
    change. And two full verification runs followed a two-file move and a
    field rename. These pin the checker's side: one `Amendments` section with
    old and new forms, a delta block against what was last approved, the
    approval that covers a dictated change, and the comparison that decides
    whether the lighter lane applies - names and `covers:` lines, not the
    agent's description of its own edit.
    """

    START = GatePresentationTests.START
    END = GatePresentationTests.END

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.plan = self.dir / "p.md"
        self.log = self.dir / "p.approval.log"

    def run_plan(self, *extra, env=None):
        merged = dict(os.environ)
        merged.pop("CTDD_LAYERS", None)
        merged.pop("CTDD_HARNESSES", None)
        merged.pop("CLAUDE_PROJECT_DIR", None)
        merged.update(env or {})
        return subprocess.run([sys.executable, SCRIPT, "p.md", *extra],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=20, env=merged, cwd=str(self.dir))

    def gate(self, text, *extra):
        self.plan.write_text(text, encoding="utf-8")
        return self.run_plan("--gate", *extra)

    def block(self, r):
        self.assertIn(self.START, r.stdout, r.stdout)
        return r.stdout[r.stdout.index(self.START) + len(self.START):r.stdout.index(self.END)]

    def record(self, r, said='"approve" (typed at the gate)'):
        rev = re.search(r"plan revision ([0-9a-f]{12})", r.stdout).group(1)
        tok = re.search(r"Gate token: ([0-9a-f]{8})", r.stdout).group(1)
        with open(self.log, "a", encoding="utf-8") as fh:
            fh.write(f"Approved by: {said}; plan: p.md@{rev}; gate-token: {tok}" + NL)
        return rev

    def approved(self, text):
        """Present `text` at a gate and record its approval."""
        return self.record(self.gate(text))

    # ---------------------------------------------------------- the section
    def test_an_amendment_entry_needs_both_forms(self):
        r = run(with_amendment(FULL_PLAN, "- A1: the status code becomes `422`."))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("AMENDMENT WITHOUT OLD AND NEW FORM", r.stdout)
        self.assertEqual(run(with_amendment(FULL_PLAN, ENTRY)).returncode, 0)

    def test_an_entry_may_wrap_onto_indented_lines(self):
        wrapped = "- A1, at the checkpoint." + NL + "  Old: rejected with `400`." + NL + "  New: rejected with `422`."
        self.assertEqual(run(with_amendment(FULL_PLAN, wrapped)).returncode, 0)

    # ---------------------------------------------------------- the first gate
    def test_the_first_gate_is_the_full_block(self):
        b = self.block(self.gate(FULL_PLAN))
        self.assertIn("Decision summary, verbatim:", b)
        self.assertIn("capture requires amount == authorized", b)

    def test_a_first_gate_that_already_carries_an_entry_is_still_full(self):
        """Nothing was shown before, so there is nothing to be a delta of."""
        b = self.block(self.gate(with_amendment(FULL_PLAN, ENTRY)))
        self.assertIn("Decision summary, verbatim:", b)

    # ---------------------------------------------------------- the delta
    def test_after_an_approval_the_gate_prints_only_the_delta(self):
        rev = self.approved(FULL_PLAN)
        amended = with_amendment(FULL_PLAN, ENTRY)
        r = self.gate(amended)
        self.assertEqual(r.returncode, 0, r.stdout)
        b = self.block(r)
        self.assertIn(ENTRY, b)
        self.assertIn("unchanged since revision " + rev, b)
        self.assertIn("which you approved", b)
        self.assertNotIn("Decision summary, verbatim:", b)
        self.assertNotIn("capture requires amount == authorized", b)
        self.assertIn("Gate token: " + gate_token_of(amended), b)

    def test_a_changed_gate_visible_section_is_shown_in_full(self):
        self.approved(FULL_PLAN)
        b = self.block(self.gate(with_amendment(
            FULL_PLAN.replace("Assumptions:" + NL + "- y", "Assumptions:" + NL + "- y, and the remainder expires"),
            ENTRY)))
        self.assertIn("- y, and the remainder expires", b)
        changed = [l for l in b.split(NL) if l.startswith("Changed since then")]
        same = [l for l in b.split(NL) if l.startswith("Otherwise unchanged")]
        self.assertEqual(len(changed), 1, b)
        self.assertIn("Assumptions", changed[0])
        self.assertNotIn("Assumptions", same[0])
        self.assertIn("Behavior flow", same[0])

    def test_an_approved_plan_amended_with_no_entry_fails(self):
        """`An amendment voids the previous approval` - so every change to an
        approved plan is one, and one with no record cannot be shown."""
        self.approved(FULL_PLAN)
        r = self.gate(FULL_PLAN.replace("- y", "- y2"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("AMENDED WITHOUT AN ENTRY", r.stdout)
        self.assertEqual(self.run_plan().returncode, 1)

    def test_before_any_approval_an_entry_makes_the_next_gate_a_delta(self):
        """The human answers the first block with a change. What they saw is
        the base, and the checker has it, because it printed it."""
        first = self.gate(FULL_PLAN)
        rev = re.search(r"plan revision ([0-9a-f]{12})", first.stdout).group(1)
        b = self.block(self.gate(with_amendment(FULL_PLAN, ENTRY)))
        self.assertIn(ENTRY, b)
        self.assertIn("unchanged since revision " + rev, b)
        self.assertNotIn("which you approved", b)

    def test_before_any_approval_an_edit_with_no_entry_is_a_full_block_again(self):
        """A draft corrected before anyone saw it is not an amendment."""
        self.gate(FULL_PLAN)
        r = self.gate(FULL_PLAN.replace("- y", "- y2"))
        self.assertEqual(r.returncode, 0, r.stdout)
        b = self.block(r)
        self.assertIn("Decision summary, verbatim:", b)
        self.assertIn("- y2", b)

    def test_a_second_run_on_the_same_revision_prints_the_same_delta(self):
        self.approved(FULL_PLAN)
        amended = with_amendment(FULL_PLAN, ENTRY)
        self.assertEqual(self.block(self.gate(amended)), self.block(self.gate(amended)))

    def test_an_unapproved_chain_is_cumulative_since_the_approval(self):
        """A revision shown and not approved is no base: the next gate still
        shows everything not yet approved, so nothing is approved unseen."""
        rev = self.approved(FULL_PLAN)
        self.gate(with_amendment(FULL_PLAN, ENTRY))
        b = self.block(self.gate(with_amendment(FULL_PLAN, ENTRY, ENTRY2)))
        self.assertIn(ENTRY, b)
        self.assertIn(ENTRY2, b)
        self.assertIn("unchanged since revision " + rev, b)

    def test_the_next_delta_starts_from_the_newly_approved_revision(self):
        self.approved(FULL_PLAN)
        rev2 = self.approved(with_amendment(FULL_PLAN, ENTRY))
        b = self.block(self.gate(with_amendment(FULL_PLAN, ENTRY, ENTRY2)))
        self.assertNotIn(ENTRY, b)
        self.assertIn(ENTRY2, b)
        self.assertIn("unchanged since revision " + rev2, b)

    def test_the_base_survives_a_second_unapproved_gate(self):
        """The approved copy is saved the first time it is needed, because the
        `shown` copy it came from is overwritten by the very next block."""
        self.approved(FULL_PLAN)
        rev2 = self.approved(with_amendment(FULL_PLAN, ENTRY))
        third = "- A3, later. Old: `b.cs` holds the rule. New: `c.cs` holds the rule."
        self.gate(with_amendment(FULL_PLAN, ENTRY, ENTRY2))
        b = self.block(self.gate(with_amendment(FULL_PLAN, ENTRY, ENTRY2, third)))
        self.assertIn("unchanged since revision " + rev2, b)
        self.assertIn(ENTRY2, b)
        self.assertIn(third, b)

    def test_before_any_approval_deltas_are_cumulative_since_the_full_block(self):
        """With nothing approved, the last plan printed in full is the base. A
        delta block is never one: what it showed was only a difference."""
        first = self.gate(FULL_PLAN)
        rev = re.search(r"plan revision ([0-9a-f]{12})", first.stdout).group(1)
        self.gate(with_amendment(FULL_PLAN, ENTRY))
        b = self.block(self.gate(with_amendment(FULL_PLAN, ENTRY, ENTRY2)))
        self.assertIn(ENTRY, b)
        self.assertIn(ENTRY2, b)
        self.assertIn("unchanged since revision " + rev, b)

    def test_a_section_removed_since_the_approval_is_named(self):
        self.approved(FULL_PLAN)
        b = self.block(self.gate(with_amendment(
            FULL_PLAN.replace("Known gaps: none — the caller contract is covered" + NL, ""),
            "- A1. Old: the plan listed its known gaps. New: the section is dropped, as the medium tier allows.")))
        self.assertIn("Removed since then: Known gaps.", b)

    def test_with_no_copy_of_the_approved_revision_the_block_is_full(self):
        """A plan approved before this existed has nothing to compare with.
        Showing everything is the safe answer; claiming `unchanged` is not."""
        self.plan.write_text(FULL_PLAN, encoding="utf-8")
        self.log.write_text('Approved by: "approve" (typed at the gate); plan: p.md@' + revision(FULL_PLAN)
                            + "; gate-token: " + gate_token_of(FULL_PLAN) + NL, encoding="utf-8")
        r = self.gate(with_amendment(FULL_PLAN, ENTRY))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Decision summary, verbatim:", self.block(r))
        self.assertNotIn("unchanged since", self.block(r))

    def test_full_forces_the_whole_block(self):
        self.approved(FULL_PLAN)
        b = self.block(self.gate(with_amendment(FULL_PLAN, ENTRY), "--full"))
        self.assertIn("Decision summary, verbatim:", b)

    def test_an_answered_blocking_question_is_part_of_the_delta(self):
        """Field rule 11 moves the answer under `Decisions confirmed in
        session`; that bullet is what changed, so it is what the gate shows."""
        self.gate(STILL_ASKING)
        answered = STILL_ASKING.replace(
            "BLOCKING — I will not guess:" + NL
            + "- auth hold on the released remainder? (recommend: expires with the auth)" + NL,
            "BLOCKING — I will not guess: none — answered before approval" + NL).replace(
            "Business requirement:",
            "Decisions confirmed in session:" + NL
            + "- The remainder's hold expires with the authorization." + NL + "Business requirement:", 1)
        b = self.block(self.gate(answered))
        self.assertIn("Decisions confirmed since then", b)
        self.assertIn("- The remainder's hold expires with the authorization.", b)
        self.assertNotIn("Decision summary, verbatim:", b)

    # ---------------------------------------------------------- the lighter lane
    def lane(self, amended):
        self.approved(LANE_PLAN)
        r = self.gate(amended)
        self.assertEqual(r.returncode, 0, r.stdout)
        return self.block(r), r.stdout[r.stdout.index(self.END):]

    def test_unchanged_tests_make_the_amendment_eligible(self):
        b, after = self.lane(with_amendment(LANE_PLAN, ENTRY))
        self.assertIn("Tests: unchanged since then", b)
        self.assertIn("lighter lane", after)
        # A moved type is the commonest amendment the lane takes, and a move
        # is what breaks a layering rule: the lane's own run names the suite.
        self.assertIn("the build, the plan's invariant suite and the tests the amendment touches",
                      " ".join(after.split()))

    def test_an_added_test_is_not_eligible(self):
        more = LANE_PLAN.replace("  - red: the stub has no rules." + NL,
                                 "  - red: the stub has no rules." + NL + "- t2 — positive" + NL
                                 + "  - covers: 500 characters pass." + NL).replace(
            "turns green: `t`", "turns green: `t`, `t2`")
        b, after = self.lane(with_amendment(more, ENTRY))
        self.assertIn("Tests: changed since then", b)
        self.assertIn("added: t2", b)
        self.assertNotIn("lighter lane", after.replace("no lighter lane", ""))

    def test_a_changed_expected_value_is_not_eligible(self):
        b, _ = self.lane(with_amendment(LANE_PLAN.replace("501", "201").replace("; 500 pass", "; 200 pass"), ENTRY))
        self.assertIn("Tests: changed since then", b)
        self.assertIn("`covers:` changed: t", b)

    def test_a_declared_rename_inside_code_spans_stays_eligible(self):
        """The session's own case: a request field renamed, every test name,
        input and expected value as it was."""
        renamed = with_amendment(LANE_PLAN.replace("a `note` of 501", "a `statusNote` of 501"),
                                 "- A1, at the checkpoint. Old: `note`. New: `statusNote`.")
        b, after = self.lane(renamed)
        self.assertIn("Tests: unchanged since then", b)
        self.assertIn("`note` → `statusNote`", b)
        self.assertIn("lighter lane", after)

    def test_identifiers_the_tests_never_used_are_not_reported_as_renames(self):
        """An entry about a type moving folders quotes identifiers too. The
        first run on a real fixture announced a rename of one type into
        another that no test line had ever mentioned."""
        b, _ = self.lane(with_amendment(
            LANE_PLAN, "- A1. Old: `OrderStateChange` lives in the feature folder. "
                       "New: it lives in the Domain, beside `OrderState`."))
        self.assertIn("Tests: unchanged since then", b)
        self.assertNotIn("apart from the rename", b)

    def test_a_rename_applied_to_some_lines_only_is_not_a_rename(self):
        two = LANE_PLAN.replace(
            "  - red: the stub has no rules." + NL,
            "  - red: the stub has no rules." + NL + "- t2 — positive" + NL
            + "  - covers: a `note` of 500 characters passes." + NL).replace(
            "turns green: `t`", "turns green: `t`, `t2`")
        self.approved(two)
        r = self.gate(with_amendment(two.replace("a `note` of 501", "a `statusNote` of 501"),
                                     "- A1. Old: `note`. New: `statusNote`."))
        # Named truthfully: `t` is the line that changed. Applying the rename
        # anyway would report `t2`, the one line nobody touched.
        self.assertIn("`covers:` changed: t. ", self.block(r))

    def test_a_rename_leaves_the_same_word_in_prose_alone(self):
        """`note` the field is renamed; "the note" in a sentence is the thing
        the sentence is about and stays."""
        prose = LANE_PLAN.replace("a `note` of 501 characters", "the note is trimmed; a `note` of 501 characters")
        self.approved(prose)
        r = self.gate(with_amendment(prose.replace("a `note` of 501", "a `statusNote` of 501"),
                                     "- A1. Old: `note`. New: `statusNote`."))
        self.assertIn("Tests: unchanged since then", self.block(r))

    def test_a_changed_hand_check_value_is_not_eligible(self):
        """The values a human recomputes by hand are expectations too."""
        declined = HOLDOUT_PLAN.replace("- result: pending", "- result: declined by human").replace(
            "- human-verified expected values: n/a",
            "- human-verified expected values: a capture of 33.33 answers `200`.")
        self.approved(declined)
        b = self.block(self.gate(with_amendment(declined.replace("answers `200`.", "answers `202`."), ENTRY)))
        self.assertIn("Tests: changed since then", b)
        self.assertIn("the hold-out's hand-check values changed", b)

    def test_a_hand_check_list_that_comes_or_goes_is_not_a_changed_expectation(self):
        """The human writes the sealed tests after all: the list returns to
        `n/a`. Found by a pressure run whose delta block called that a test
        change. Declining at the gate, which makes the list appear, is the
        same case the other way round."""
        declined = HOLDOUT_PLAN.replace("- result: pending", "- result: declined by human").replace(
            "- human-verified expected values: n/a",
            "- human-verified expected values: a capture of 33.33 answers `200`.")
        self.approved(declined)
        b = self.block(self.gate(with_amendment(HOLDOUT_PLAN, ENTRY)))
        self.assertIn("Tests: unchanged since then", b)
        self.approved(with_amendment(HOLDOUT_PLAN, ENTRY))
        b = self.block(self.gate(with_amendment(declined, ENTRY, ENTRY2)))
        self.assertIn("Tests: unchanged since then", b)

    def test_a_moved_test_file_brings_the_altitude_table_back(self):
        self.approved(LANE_PLAN)
        b = self.block(self.gate(with_amendment(
            LANE_PLAN.replace("`tests/a_tests.cs`", "`tests/unit/a_tests.cs`"), ENTRY)))
        self.assertIn("Test files moved: t.", b)
        self.assertIn("Test altitude", b)
        self.assertIn("Tests: unchanged since then", b)

    def test_an_undeclared_rename_is_a_changed_expectation(self):
        b, _ = self.lane(with_amendment(LANE_PLAN.replace("a `note` of 501", "a `statusNote` of 501"), ENTRY))
        self.assertIn("`covers:` changed: t", b)

    def test_a_value_swap_declared_as_a_rename_is_not_eligible(self):
        """`Packed` to `Shipped` is identifier-shaped and is a different
        expected value. A rename's old name is gone afterwards and its new
        name was not there before; a swapped value fails both."""
        two = LANE_PLAN.replace("is rejected with `400`; 500 pass.", "moves the order to `Packed`.").replace(
            "  - red: the stub has no rules." + NL,
            "  - red: the stub has no rules." + NL + "- t2 — positive" + NL
            + "  - covers: a second move reaches `Shipped`." + NL).replace(
            "turns green: `t`", "turns green: `t`, `t2`")
        self.approved(two)
        r = self.gate(with_amendment(two.replace("moves the order to `Packed`.", "moves the order to `Shipped`."),
                                     "- A1. Old: `Packed`. New: `Shipped`."))
        self.assertIn("`covers:` changed: t", self.block(r))

    def test_a_changed_red_line_alone_stays_eligible_and_is_named(self):
        """An honest stub lets a named test pass; the plan says so. Names,
        inputs and expected values are what they were."""
        b, _ = self.lane(with_amendment(
            LANE_PLAN.replace("  - red: the stub has no rules.",
                              "  - red: none at step 7 — the honest stub already rejects it; constrained by the validator slice."),
            ENTRY))
        self.assertIn("Tests: unchanged since then", b)
        self.assertIn("`red:` changed: t", b)
        self.assertIn("constrained by a later slice: t", b)

    def test_a_changed_needs_line_alone_stays_eligible_and_is_named(self):
        """Why a test sits in a heavier harness states no input and no
        expected value, so it is named at the gate and changes nothing else."""
        b, _ = self.lane(with_amendment(
            LANE_PLAN.replace("  - red: the stub has no rules.",
                              "  - red: the stub has no rules." + NL + "  - needs: " + REASON),
            ENTRY))
        self.assertIn("Tests: unchanged since then", b)
        self.assertIn("`needs:` changed: t", b)

    # ---------------------------------------------------------- the covering approval
    DICTATED = ('- A1, dictated at the checkpoint ("Domain, approve"). Old: the type lives in the '
                "feature folder. New: the type lives in the Domain.")
    COVERS = '"Domain, approve" (typed at the gate; covers the amendment it dictated)'

    def test_an_approval_that_states_the_change_covers_it(self):
        self.approved(FULL_PLAN)
        self.record(self.gate(with_amendment(FULL_PLAN, self.DICTATED)), self.COVERS)
        r = self.run_plan("--approval", "p.approval.log")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("approval record verified", r.stdout)

    def test_a_covering_approval_does_not_reach_an_entry_it_did_not_dictate(self):
        """The agent's own extra edit, recorded honestly as its own entry, is
        not what the human's words approved."""
        self.approved(FULL_PLAN)
        self.record(self.gate(with_amendment(FULL_PLAN, self.DICTATED, ENTRY2)), self.COVERS)
        r = self.run_plan("--approval", "p.approval.log")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("APPROVAL COVERS ONLY WHAT IT DICTATED", r.stdout)
        self.assertIn("A2", r.stdout)

    def test_the_same_plan_approved_after_seeing_the_delta_verifies(self):
        """The control: a plain approval of the delta block needs no quote."""
        self.approved(FULL_PLAN)
        self.record(self.gate(with_amendment(FULL_PLAN, self.DICTATED, ENTRY2)))
        self.assertEqual(self.run_plan("--approval", "p.approval.log").returncode, 0)

    def test_an_answer_and_an_approval_in_one_message_verify(self):
        """The worked example's own case: the BLOCKING answer and `Approved.`
        arrive together, and field rule 11 records the answer as a decision."""
        self.gate(STILL_ASKING)
        answered = STILL_ASKING.replace(
            "BLOCKING — I will not guess:" + NL
            + "- auth hold on the released remainder? (recommend: expires with the auth)" + NL,
            "BLOCKING — I will not guess: none — answered before approval" + NL).replace(
            "Business requirement:",
            "Decisions confirmed in session:" + NL
            + "- The remainder's hold expires with the authorization." + NL + "Business requirement:", 1)
        self.record(self.gate(answered),
                    '"expires with the authorization. Approved." (typed at the gate; covers the amendment it dictated)')
        r = self.run_plan("--approval", "p.approval.log", "--post-approval")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_choice_among_offered_fixes_is_not_a_covering_approval(self):
        """From the first agent run under the rule: the human answered `which
        do you want?` with a choice and a name, and the agent recorded that as
        an approval covering the amendment and began editing code."""
        self.approved(FULL_PLAN)
        chosen = ('- A1, chosen at the checkpoint ("A, statusNote"). Old: the field is `note`. '
                  "New: the field is `statusNote`.")
        self.record(self.gate(with_amendment(FULL_PLAN, chosen)),
                    '"A, statusNote" (typed at the gate; covers the amendment it dictated)')
        r = self.run_plan("--approval", "p.approval.log")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("NOT AN APPROVAL", r.stdout)

    def test_a_covering_approval_needs_an_entry_to_cover(self):
        self.gate(FULL_PLAN)
        self.record(self.gate(FULL_PLAN.replace("- y", "- y2")), self.COVERS)
        r = self.run_plan("--approval", "p.approval.log")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("APPROVAL COVERS ONLY WHAT IT DICTATED", r.stdout)

    # ---------------------------------------------------------- an approved plan is not asking
    def test_an_approval_does_not_verify_while_the_plan_still_asks(self):
        """Field rule 11: an approved plan must not still be asking. The check
        existed behind `--post-approval`, which one reference line named and
        no step ran, so in a real session it never ran at all. Verifying an
        approval is the moment it matters."""
        self.approved(STILL_ASKING)
        r = self.run_plan("--approval", "p.approval.log")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("UNANSWERED BLOCKING AT APPROVAL", r.stdout)
        self.assertNotIn("approval record verified", r.stdout)

    def test_a_stale_record_is_reported_stale_whatever_the_plan_asks(self):
        """A plan amended after approval may carry a new question for the
        human. That is what the next gate is for, and STALE is the finding."""
        self.approved(FULL_PLAN)
        self.plan.write_text(with_amendment(STILL_ASKING, ENTRY), encoding="utf-8")
        r = self.run_plan("--approval", "p.approval.log")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("APPROVAL STALE", r.stdout)
        self.assertNotIn("UNANSWERED BLOCKING", r.stdout)

    # ---------------------------------------------------------- the invariant suite
    def test_a_plan_above_the_small_tier_names_its_invariant_suite(self):
        """One real change returned a feature-folder type from a port in its
        first stub and learned it at the last phase's verification, three
        approved revisions later. The rule had a test the whole time."""
        r = run(FULL_PLAN.replace("- invariants: none — this fixture has no rule suite" + NL, ""))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("NO INVARIANT SUITE", r.stdout)
        named = FULL_PLAN.replace("- invariants: none — this fixture has no rule suite",
                                  "- invariants: `dotnet test --filter Architecture` — expected: passes")
        self.assertEqual(run(named).returncode, 0, run(named).stdout)

    def test_the_invariants_line_has_to_sit_under_verification(self):
        moved = FULL_PLAN.replace("- invariants: none — this fixture has no rule suite" + NL, "").replace(
            "Assumptions:" + NL + "- y", "Assumptions:" + NL + "- y" + NL + "- invariants: none — misplaced")
        r = run(moved)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("NO INVARIANT SUITE", r.stdout)

    def test_an_approved_plan_is_not_failed_for_a_missing_invariants_line(self):
        old = FULL_PLAN.replace("- invariants: none — this fixture has no rule suite" + NL, "")
        self.plan.write_text(old, encoding="utf-8")
        self.assertEqual(self.run_plan().returncode, 1)
        self.log.write_text('Approved by: "go ahead"; plan: p.md@0123456789ab; '
                            "gate-token: n/a (predates gate tokens)" + NL, encoding="utf-8")
        self.assertEqual(self.run_plan().returncode, 0, self.run_plan().stdout)

    def test_the_small_tier_needs_no_invariants_line(self):
        small = FULL_PLAN.replace(STRUCTURE_LINES, "").replace(
            "- invariants: none — this fixture has no rule suite" + NL, "").replace(
            "New-behavior tests — must be observed failing first:" + NL + "- t",
            "New-behavior tests: none — pure refactor").replace(
            "Preservation pins — must pass before and after: none",
            "Preservation pins — must pass before and after:" + NL + "- p")
        self.assertEqual(run(small).returncode, 0, run(small).stdout)

    # ---------------------------------------------------------- dirty before the first gate
    def _git(self, *args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "-c", "core.autocrlf=false", *args],
                       cwd=str(self.dir), check=True, capture_output=True)

    def _dirty_repo(self):
        (self.dir / "src").mkdir()
        (self.dir / "src" / "kept.cs").write_text("a" + NL, encoding="utf-8")
        (self.dir / "src" / "theirs.json").write_text("{}" + NL, encoding="utf-8")
        self._git("init", "-q")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "base")
        (self.dir / "src" / "theirs.json").write_text('{"edited": true}' + NL, encoding="utf-8")

    def test_the_first_gate_records_what_was_already_dirty(self):
        """Until a plan is approved the only file the workflow writes is the
        plan, so whatever else is dirty when the first gate prints is not this
        change's. Recorded then, by the checker: a `Baseline:` line passed by
        hand at step 8 is one the agent can re-derive after the change exists,
        and one real session printed exactly that line, the change's own
        forty files in it."""
        self._dirty_repo()
        self.gate(FULL_PLAN)
        self.assertTrue((self.dir / "p.gate-dirty.txt").exists(), "the first gate wrote no dirty list")
        listed = (self.dir / "p.gate-dirty.txt").read_text(encoding="utf-8").split(NL)
        self.assertIn("src/theirs.json", listed)
        self.assertNotIn("src/kept.cs", listed)
        # The plan and its own files beside it are not the requester's.
        self.assertEqual([l for l in listed if l.startswith("p.")], [])

    def test_the_dirty_list_is_not_rewritten_once_a_plan_is_approved(self):
        self._dirty_repo()
        self.approved(FULL_PLAN)
        (self.dir / "src" / "kept.cs").write_text("the change's own edit" + NL, encoding="utf-8")
        self.gate(with_amendment(FULL_PLAN, ENTRY))
        self.gate(with_amendment(FULL_PLAN, ENTRY), "--full")
        listed = (self.dir / "p.gate-dirty.txt").read_text(encoding="utf-8").split(NL)
        self.assertNotIn("src/kept.cs", listed)
        self.assertIn("src/theirs.json", listed)

    def test_outside_a_repository_the_gate_still_prints(self):
        r = self.gate(FULL_PLAN)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse((self.dir / "p.gate-dirty.txt").exists())

    # ---------------------------------------------------------- hold-out values
    def test_the_gate_prints_the_holdout_result_and_values_after_a_decline(self):
        """The block read the approved region, which blanks both fields so the
        revision survives their replacement - and so printed them blank at ten
        consecutive gates of one change, the values the human was asked to
        check included."""
        declined = HOLDOUT_PLAN.replace("- result: pending", "- result: declined by human — a waiver, not a pass").replace(
            "- human-verified expected values: n/a",
            "- human-verified expected values: a capture of 33.33 answers `200`.")
        r = run(declined, ["--gate"])
        self.assertEqual(r.returncode, 0, r.stdout)
        b = r.stdout[r.stdout.index(self.START):]
        self.assertIn("- result: declined by human — a waiver, not a pass", b)
        self.assertIn("a capture of 33.33 answers `200`.", b)
        self.assertEqual(revision(declined), revision(HOLDOUT_PLAN))

    # ---------------------------------------------------------- structure
    def test_structure_is_required_above_the_small_tier(self):
        r = run(FULL_PLAN.replace(STRUCTURE_LINES, ""))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("MISSING sections", r.stdout)
        self.assertIn("structure", r.stdout.lower())

    def test_structure_names_types_ports_and_configuration(self):
        r = run(FULL_PLAN.replace("- Ports: none touched." + NL, ""))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("STRUCTURE INCOMPLETE", r.stdout)
        self.assertIn("Ports", r.stdout)

    def test_a_plan_approved_before_structure_existed_is_not_failed(self):
        """Requiring it of a plan that already passed its first gate forces an
        amendment and a re-approval for nothing the gate would have shown."""
        old = FULL_PLAN.replace(STRUCTURE_LINES, "")
        self.plan.write_text(old, encoding="utf-8")
        self.assertEqual(self.run_plan().returncode, 1)
        self.log.write_text('Approved by: "go ahead"; plan: p.md@0123456789ab; '
                            "gate-token: n/a (predates gate tokens)" + NL, encoding="utf-8")
        r = self.run_plan()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_small_tier_needs_no_structure(self):
        small = FULL_PLAN.replace(STRUCTURE_LINES, "").replace(
            "New-behavior tests — must be observed failing first:" + NL + "- t",
            "New-behavior tests: none — pure refactor").replace(
            "Preservation pins — must pass before and after: none",
            "Preservation pins — must pass before and after:" + NL + "- p")
        self.assertEqual(run(small).returncode, 0, run(small).stdout)

    def test_the_gate_prints_structure_and_the_tests_by_file(self):
        b = self.block(self.gate(LANE_PLAN))
        self.assertIn("- Ports: none touched.", b)
        self.assertIn("Tests by file:", b)
        self.assertIn("1 new — tests/a_tests.cs", b)
        self.assertLess(b.index("Uncovered"), b.index("- Ports: none touched."))

    def test_the_gate_names_tests_the_plan_declares_without_red(self):
        b = self.block(self.gate(LANE_PLAN.replace(
            "  - red: the stub has no rules.",
            "  - red: none at step 7 — the honest stub already rejects it; constrained by the validator slice.")))
        self.assertIn("constrained by a later slice: t", b)


# A plan with both evidence lanes and a red pause, and the runner lines that
# verify each lane for it.
NEXT_PLAN = LANE_PLAN.replace("red pause: skip", "red pause: pause") \
    .replace("- t — boundary", "- rejects_note_over_500 — boundary") \
    .replace("turns green: `t`", "turns green: `rejects_note_over_500`") \
    .replace("Preservation pins — must pass before and after: none" + NL,
             "Preservation pins — must pass before and after:" + NL
             + "- currently_accepts_note_of_500 — the limit as it is today" + NL
             + "  - path: `tests/a_tests.cs`." + NL)
PIN_GREEN = "  Passed Shop.Tests.a_tests.currently_accepts_note_of_500 [1 ms]" + NL
PIN_RED = "  Failed Shop.Tests.a_tests.currently_accepts_note_of_500 [1 ms]" + NL
NEW_RED = "  Failed Shop.Tests.a_tests.rejects_note_over_500 [3 ms]" + NL
NEW_GREEN = "  Passed Shop.Tests.a_tests.rejects_note_over_500 [3 ms]" + NL
INTENDED = (NL + "## Intended change" + NL + NL + "| File | Intended change |" + NL
            + "| --- | --- |" + NL + "| `a.cs` | Accepts the lower amount. |" + NL)
# The human's release of the 7.12 pause, as `execution.md` has the agent record it.
RELEASE = 'Pause released by: "looks right, implement it"'


class NextStepTests(unittest.TestCase):
    """`--next` says where a change stands, from the files beside its plan.

    One real session lost the whole skill text at a compaction: the harness
    re-attached another skill and not this one. It went on from what the
    summary remembered, so the red pause came out without its content, no
    verification was saved and step 9 never ran. Every step that matters
    leaves a file beside the plan, and `--next` reads them: one `Evidence:`
    line, and one `Next:` line naming the first step whose evidence is
    missing. Each test below leaves on disk what a change has at one point
    and reads the two lines back.
    """

    STEPS = ("approval", "pins", "red", "prered", "intended", "release", "verify",
             "pins-after", "packet")

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.dir), True)
        self.plan = self.dir / "p.md"

    def run_plan(self, *args):
        env = dict(os.environ)
        for var in ("CTDD_LAYERS", "CTDD_HARNESSES", "CLAUDE_PROJECT_DIR"):
            env.pop(var, None)
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60,
                              env=env, cwd=str(self.dir))

    def put(self, name, text):
        (self.dir / name).write_text(text, encoding="utf-8", newline=NL)

    def approve(self):
        r = self.run_plan("p.md", "--gate")
        self.assertEqual(r.returncode, 0, r.stdout)
        rev = re.search(r"plan revision ([0-9a-f]{12})", r.stdout).group(1)
        tok = re.search(r"Gate token: ([0-9a-f]{8})", r.stdout).group(1)
        self.put("p.approval.log", f'Approved by: "approve" (typed at the gate); '
                                   f'plan: p.md@{rev}; gate-token: {tok}' + NL)
        return rev

    def reach(self, upto, plan=NEXT_PLAN):
        """Leave on disk what a change has once every step up to and including
        `upto` is done. Returns the approved revision, when there is one."""
        self.put("p.md", plan)
        done = self.STEPS[:self.STEPS.index(upto) + 1] if upto else ()
        rev = self.approve() if "approval" in done else None
        if "pins" in done:
            self.put("p.pinstate.log", PIN_GREEN)
        if "red" in done:
            self.put("p.redstate.log", NEW_RED)
        if "prered" in done:
            self.put("p.prered.diff", "diff --git a/tests/a_tests.cs b/tests/a_tests.cs" + NL)
        if "intended" in done:
            self.put("p.md", plan + INTENDED)
        if "release" in done:
            with open(self.dir / "p.approval.log", "a", encoding="utf-8", newline=NL) as fh:
                fh.write(RELEASE + NL)
        if "verify" in done:
            self.put("p.verify.log", "build: ok" + NL + NEW_GREEN + PIN_GREEN)
        if "pins-after" in done:
            self.put("p.pinstate-after.log", PIN_GREEN)
        if "packet" in done:
            self.put("p.packet.md", "Business requirement: allow the lower amount" + NL)
        return rev

    def next(self):
        """(run, the Evidence line, the Next line)"""
        r = self.run_plan("p.md", "--next")
        lines = [l for l in r.stdout.split(NL) if l.strip()]
        self.assertEqual(2, len(lines), r.stdout + r.stderr)
        self.assertTrue(lines[0].startswith("Evidence: "), r.stdout)
        self.assertTrue(lines[1].startswith("Next: "), r.stdout)
        return r, lines[0], lines[1]

    # ------------------------------------------------------- one row per step
    def test_a_plan_that_fails_its_checks_is_fixed_first(self):
        self.reach(None, NEXT_PLAN.replace(
            "BLOCKING — I will not guess: none — answered before approval" + NL, ""))
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 1)
        self.assertIn("plan ✗", evidence)
        self.assertTrue(nxt.startswith("Next: 5.4: fix the plan and re-run check-plan"), nxt)
        # The refusal's own heading, not the note check-plan printed before it.
        self.assertIn("It says: MISSING sections for a medium plan", nxt)

    def test_a_plan_with_no_approval_goes_to_the_gate(self):
        self.reach(None)
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("plan ✓ · approval ✗ · pins before ✗", evidence)
        self.assertTrue(nxt.startswith("Next: 6: the gate. Print the gate presentation"), nxt)

    def test_a_plan_amended_since_its_approval_goes_back_to_the_gate(self):
        old = self.reach("red")
        self.put("p.md", with_amendment(
            NEXT_PLAN.replace("500 pass", "500 and fewer pass"),
            "- A1. Old: 500 pass. New: 500 and fewer pass."))
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(f"approval ✗ (approves {old}, the plan is now ", evidence)
        self.assertTrue(nxt.startswith(f"Next: 6: the gate. Revision {old} was approved"), nxt)
        self.assertIn("record what changed under `Amendments` first", nxt)

    def test_an_amendment_with_no_entry_is_the_plans_failure_first(self):
        self.reach("red")
        self.put("p.md", NEXT_PLAN.replace("500 pass", "500 and fewer pass"))
        r, _evidence, nxt = self.next()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertTrue(nxt.startswith("Next: 5.4:"), nxt)
        self.assertIn("It says: AMENDED WITHOUT AN ENTRY", nxt)

    def test_an_approval_record_the_checker_refuses_is_not_an_approval(self):
        rev = self.reach("red")
        self.put("p.approval.log",
                 f'Approved by: "approve" (typed at the gate); plan: p.md@{rev}' + NL)
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("approval ✗ (", evidence)
        self.assertTrue(nxt.startswith("Next: 6: the gate. The approval record is not "
                                       "accepted: the approval record carries no gate token"),
                        nxt)

    def test_while_the_plan_fails_its_approval_is_not_judged(self):
        """The checker refuses the plan before it reads the record, so judging
        the record then would report the plan's failure a second time, as the
        approval's."""
        broken = NEXT_PLAN.replace(
            "BLOCKING — I will not guess: none — answered before approval" + NL, "")
        self.put("p.md", broken)
        spec = importlib.util.spec_from_file_location("check_plan_for_next_tests", SCRIPT)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        rev = checker.plan_revision(checker.strip_fences(broken))
        self.put("p.approval.log", f'Approved by: "approve" (typed at the gate); plan: '
                                   f'p.md@{rev}; gate-token: {checker.gate_token(rev)}' + NL)
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("plan ✗ · approval ✗ (not checked while the plan fails) · ", evidence)
        self.assertTrue(nxt.startswith("Next: 5.4:"), nxt)

    def test_approved_with_no_pin_run_writes_and_runs_the_pins(self):
        rev = self.reach("approval")
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(f"approval ✓ {rev} · pins before ✗", evidence)
        self.assertTrue(nxt.startswith("Next: 7.5–7.7: write the preservation pins"), nxt)
        self.assertIn("p.pinstate.log", nxt)

    def test_a_pin_run_that_is_not_pin_pass_stops_there(self):
        self.reach("approval")
        self.put("p.pinstate.log", PIN_RED)
        _r, evidence, nxt = self.next()
        self.assertIn("pins before ✗", evidence)
        self.assertTrue(nxt.startswith("Next: 7.6–7.7: p.pinstate.log does not verify "
                                       "as pin pass"), nxt)

    def test_pins_passing_with_no_red_run_writes_and_runs_the_new_tests(self):
        self.reach("pins")
        _r, evidence, nxt = self.next()
        self.assertIn("pins before ✓ · red state ✗", evidence)
        self.assertTrue(nxt.startswith("Next: 7.9–7.11: write the new-behavior tests"), nxt)
        self.assertIn("p.redstate.log", nxt)

    def test_a_red_run_that_is_not_intended_red_stops_there(self):
        self.reach("pins")
        self.put("p.redstate.log", NEW_GREEN)
        _r, evidence, nxt = self.next()
        self.assertIn("red state ✗", evidence)
        self.assertTrue(nxt.startswith("Next: 7.10–7.11: p.redstate.log does not verify "
                                       "as intended red"), nxt)

    def test_red_state_verified_stops_at_the_pause(self):
        rev = self.reach("red")
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(
            f"Evidence: plan ✓ · approval ✓ {rev} · pins before ✓ · red state ✓ · "
            f"pre-red diff ✗ · Intended change ✗ · release recorded ✗ · verification ✗ · "
            f"pins after ✗ · packet ✗",
            evidence)
        self.assertEqual(
            "Next: 7.12: print the pause and stop for the release; read "
            "`references/execution.md` first. Still missing: the pre-implementation diff "
            "(p.prered.diff) and `## Intended change` in the plan.", nxt)

    def test_the_pause_is_owed_until_both_of_its_records_exist(self):
        self.reach("prered")
        _r, evidence, nxt = self.next()
        self.assertIn("pre-red diff ✓ · Intended change ✗", evidence)
        self.assertTrue(nxt.endswith("Still missing: `## Intended change` in the plan."), nxt)
        self.reach("red")
        self.put("p.md", NEXT_PLAN + INTENDED)
        os.remove(self.dir / "p.prered.diff") if (self.dir / "p.prered.diff").exists() else None
        _r, evidence, nxt = self.next()
        self.assertIn("pre-red diff ✗ · Intended change ✓", evidence)
        self.assertTrue(nxt.endswith("Still missing: the pre-implementation diff "
                                     "(p.prered.diff)."), nxt)

    def test_appending_the_intended_change_leaves_the_approval_standing(self):
        rev = self.reach("intended")
        _r, evidence, _nxt = self.next()
        self.assertIn(f"approval ✓ {rev}", evidence)

    def test_a_pause_with_no_release_recorded_waits_for_the_human(self):
        """Before releases were recorded nothing on disk told a pause still
        waiting from one the human had released, so a session that lost its
        context could only guess, and the guess that costs nothing is to
        implement."""
        self.reach("intended")
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Intended change ✓ · release recorded ✗ · verification ✗", evidence)
        self.assertEqual(
            "Next: 7.12: the pause's records exist and no release is recorded. If the "
            "pause was not printed in this session, print it; then stop for the human's "
            "release, and record it as `Pause released by: \"<their message>\"` in "
            "p.approval.log.", nxt)

    def test_a_recorded_release_sends_it_to_implementation(self):
        self.reach("release")
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("release recorded ✓ · verification ✗", evidence)
        self.assertEqual("Next: 8: implement what the human released, then 8.3: run the "
                         "verification and save it to p.verify.log.", nxt)

    def test_a_phased_plan_is_sent_to_the_last_phase_released(self):
        """The pause's release starts phase 1; `Phase N` is the phase the human
        released the change to continue to."""
        phased = NEXT_PLAN.replace("red pause: pause", "red pause: phased")
        self.reach("release", phased)
        _r, _evidence, nxt = self.next()
        self.assertEqual(
            "Next: 8: implement phase 1, the last one released, and stop at its checkpoint "
            "(8.7) unless it is already waiting there; when no phase remains, 8.3: run the "
            "verification and save it to p.verify.log.", nxt)
        with open(self.dir / "p.approval.log", "a", encoding="utf-8", newline=NL) as fh:
            fh.write('Phase 3 released by: "go on"' + NL + 'Phase 2 released by: "next"' + NL)
        _r, _evidence, nxt = self.next()
        self.assertTrue(nxt.startswith("Next: 8: implement phase 3, the last one released"), nxt)

    def test_release_lines_leave_the_approval_standing(self):
        """They are appended after the approval record, and `--approval` reads
        that record to the end of the log."""
        rev = self.reach("release", NEXT_PLAN.replace("red pause: pause", "red pause: phased"))
        with open(self.dir / "p.approval.log", "a", encoding="utf-8", newline=NL) as fh:
            fh.write('Phase 2 released by: "next phase"' + NL)
        verified = self.run_plan("p.md", "--approval", "p.approval.log")
        self.assertEqual(verified.returncode, 0, verified.stdout)
        self.assertIn(f"approval record verified for revision {rev}", verified.stdout)
        r, evidence, _nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(f"approval ✓ {rev}", evidence)

    def test_the_release_lines_execution_md_teaches_are_the_ones_next_reads(self):
        """One wording for the agent to write and one for the script to read: a
        drift between the two would leave every pause waiting forever."""
        execution = (Path(SCRIPT).resolve().parents[1] / "skills" / "ctdd-change"
                     / "references" / "execution.md").read_text(encoding="utf-8")
        pause = re.search(r"`(Pause released by: [^`]+)`", execution)
        phase = re.search(r"`(Phase <N> released by: [^`]+)`", execution)
        self.assertIsNotNone(pause, "execution.md no longer teaches the pause's release line")
        self.assertIsNotNone(phase, "execution.md no longer teaches a phase's release line")
        self.reach("intended", NEXT_PLAN.replace("red pause: pause", "red pause: phased"))
        with open(self.dir / "p.approval.log", "a", encoding="utf-8", newline=NL) as fh:
            fh.write(pause.group(1).replace("<their message>", "yes, implement") + NL)
            fh.write(phase.group(1).replace("<N>", "2").replace("<their message>", "go") + NL)
        _r, evidence, nxt = self.next()
        self.assertIn("release recorded ✓", evidence)
        self.assertTrue(nxt.startswith("Next: 8: implement phase 2,"), nxt)

    def test_the_packet_path_execution_md_teaches_is_the_one_next_reads(self):
        execution = (Path(SCRIPT).resolve().parents[1] / "skills" / "ctdd-change"
                     / "references" / "execution.md").read_text(encoding="utf-8")
        saved = re.search(r"save it to `<plan-dir>/<name>(\.[a-z.]+)`", execution)
        self.assertIsNotNone(saved, "execution.md no longer says where the packet is saved")
        self.reach("pins-after")
        self.put("p" + saved.group(1), "Business requirement: allow the lower amount" + NL)
        _r, _evidence, nxt = self.next()
        self.assertEqual("Next: done: every step left its evidence, the packet included.", nxt)

    def test_a_plan_with_pins_only_reaches_step_eight(self):
        """A behaviour-preserving change names pins and no new test. Step 8's
        door is now `--next`, so the script is where a pin-only plan has to get
        through: an `Enter:` that read only intended red once left it no route
        into implementation."""
        pins_only = NEXT_PLAN.replace("red pause: pause", "red pause: skip").replace(
            "New-behavior tests — must be observed failing first:" + NL
            + "- rejects_note_over_500 — boundary" + NL
            + "  - covers: a `note` of 501 characters is rejected with `400`; 500 pass." + NL
            + "  - path: `tests/a_tests.cs`." + NL
            + "  - red: the stub has no rules." + NL,
            "New-behavior tests — must be observed failing first: none — behaviour preserved"
            + NL).replace("turns green: `rejects_note_over_500`",
                          "turns green: `currently_accepts_note_of_500`")
        self.reach("pins", pins_only)
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("red state n/a", evidence)
        self.assertEqual("Next: 8: implement what the plan approves, then 8.3: run the "
                         "verification and save it to p.verify.log.", nxt)

    def test_a_plan_naming_no_test_cannot_reach_step_eight(self):
        """Step 8 needs at least one named test, and that rule now lives in the
        checker that `--next` runs first."""
        none = NEXT_PLAN.replace(
            "Preservation pins — must pass before and after:" + NL
            + "- currently_accepts_note_of_500 — the limit as it is today" + NL
            + "  - path: `tests/a_tests.cs`." + NL,
            "Preservation pins — must pass before and after: none" + NL).replace(
            "New-behavior tests — must be observed failing first:" + NL
            + "- rejects_note_over_500 — boundary" + NL
            + "  - covers: a `note` of 501 characters is rejected with `400`; 500 pass." + NL
            + "  - path: `tests/a_tests.cs`." + NL
            + "  - red: the stub has no rules." + NL,
            "New-behavior tests — must be observed failing first: none — nothing new" + NL)
        self.reach(None, none)
        r, _evidence, nxt = self.next()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertTrue(nxt.startswith("Next: 5.4:"), nxt)
        self.assertIn("NO EVIDENCE LANE", nxt)

    def test_a_plan_that_skips_the_pause_is_not_asked_for_its_records(self):
        self.reach("red", NEXT_PLAN.replace("red pause: pause", "red pause: skip"))
        _r, evidence, nxt = self.next()
        self.assertIn("pre-red diff n/a · Intended change n/a · release recorded n/a · "
                      "verification ✗", evidence)
        self.assertEqual("Next: 8: implement what the plan approves, then 8.3: run the "
                         "verification and save it to p.verify.log.", nxt)

    def test_an_empty_verification_log_is_not_a_verification(self):
        """A redirect creates the file even when the command behind it never
        ran, and an empty log saved nothing."""
        self.reach("verify")
        self.put("p.verify.log", "")
        _r, evidence, nxt = self.next()
        self.assertIn("verification ✗", evidence)
        self.assertTrue(nxt.startswith("Next: 8: implement what the human released"), nxt)

    def test_verification_saved_with_no_pin_rerun_reruns_the_pins(self):
        self.reach("verify")
        _r, evidence, nxt = self.next()
        self.assertIn("verification ✓ · pins after ✗", evidence)
        self.assertEqual("Next: 8.3: re-run the preservation pins and save the run to "
                         "p.pinstate-after.log.", nxt)

    def test_a_pin_that_fails_after_the_change_is_a_broken_pin(self):
        self.reach("verify")
        self.put("p.pinstate-after.log", PIN_RED)
        _r, _evidence, nxt = self.next()
        self.assertTrue(nxt.startswith("Next: 8.3: p.pinstate-after.log does not verify "
                                       "as pin pass. A pin that passed before the change"),
                        nxt)

    def test_everything_but_the_packet_is_step_nine(self):
        self.reach("pins-after")
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("pins after ✓ · packet ✗", evidence)
        self.assertTrue(nxt.startswith("Next: 9: stop at 9.1 for the hold-out result, or for "
                                       "the hand check if the hold-out was declined"), nxt)
        self.assertIn("the 9.4 handover", nxt)
        self.assertIn("saved as p.packet.md", nxt)

    def test_with_the_packet_saved_it_is_done(self):
        self.reach("packet")
        r, evidence, nxt = self.next()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("✗", evidence)
        self.assertEqual("Next: done: every step left its evidence, the packet included.",
                         nxt)

    # ------------------------------------------------- evidence out of order
    def test_the_first_gap_is_named_even_when_later_evidence_is_there(self):
        """One real plan had its pins re-run after the change and no saved
        verification. That is step 8.3 still owed, not a finished change."""
        self.reach("pins-after")
        os.remove(self.dir / "p.verify.log")
        _r, evidence, nxt = self.next()
        self.assertIn("verification ✗ · pins after ✓", evidence)
        self.assertTrue(nxt.startswith("Next: 8: implement what the human released, then 8.3"),
                        nxt)
        self.assertTrue(nxt.endswith("Out of order: pins after is already there."), nxt)

    def test_a_release_never_recorded_is_named_before_later_evidence(self):
        """The plan the finding came from: its pause was released in the
        conversation, before releases were recorded, and its pins were re-run
        after the change. The release is still the first gap; quoting the
        human's earlier message is how it gets recorded."""
        self.reach("pins-after")
        os.remove(self.dir / "p.verify.log")
        self.put("p.approval.log", (self.dir / "p.approval.log").read_text(
            encoding="utf-8").replace(RELEASE + NL, ""))
        _r, evidence, nxt = self.next()
        self.assertIn("release recorded ✗ · verification ✗ · pins after ✓", evidence)
        self.assertTrue(nxt.startswith("Next: 7.12: the pause's records exist"), nxt)
        self.assertTrue(nxt.endswith("Out of order: pins after is already there."), nxt)

    def test_several_later_items_are_all_named(self):
        self.reach("packet")
        os.remove(self.dir / "p.pinstate.log")
        _r, _evidence, nxt = self.next()
        self.assertTrue(nxt.startswith("Next: 7.5–7.7:"), nxt)
        self.assertTrue(nxt.endswith("Out of order: red state, pre-red diff, Intended change, "
                                     "release recorded, verification, pins after, packet are "
                                     "already there."), nxt)

    # ------------------------------------------------------- skipped lanes
    def test_a_lane_the_plan_names_no_test_for_is_skipped(self):
        """As 7.4 and 7.8 skip it: a plan with no pins is not sent to write some."""
        no_pins = NEXT_PLAN.replace(
            "Preservation pins — must pass before and after:" + NL
            + "- currently_accepts_note_of_500 — the limit as it is today" + NL
            + "  - path: `tests/a_tests.cs`." + NL,
            "Preservation pins — must pass before and after: none" + NL)
        self.reach("approval", no_pins)
        _r, evidence, nxt = self.next()
        self.assertIn("pins before n/a · red state ✗", evidence)
        self.assertIn("pins after n/a", evidence)
        self.assertTrue(nxt.startswith("Next: 7.9–7.11:"), nxt)

    # ------------------------------------------------ it reads and nothing else
    def test_it_writes_nothing(self):
        """Not even the copies `--gate` keeps: a plan no gate has printed
        still has only itself beside it afterwards."""
        for upto in (None, "red"):
            self.reach(upto)
            before = {p.name: p.read_bytes() for p in self.dir.iterdir()}
            self.next()
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.dir.iterdir()}, upto)

    def test_it_needs_a_plan_file_it_can_read(self):
        self.reach("red")
        for args, said in ((("--next",), "--next takes the plan's path"),
                           (("-", "--next"), "--next takes the plan's path"),
                           (("p.md", "extra.md", "--next"), "--next takes the plan's path"),
                           (("missing.md", "--next"), "cannot read missing.md")):
            r = self.run_plan(*args)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn(said, r.stdout)
            self.assertNotIn("Next:", r.stdout)

    def test_a_trivial_declaration_has_nothing_to_resume(self):
        self.put("p.md", "Risk: trivial — typo in a log message. Skipping the plan gate." + NL)
        r = self.run_plan("p.md", "--next")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("trivial-risk declaration", r.stdout)
        self.assertNotIn("Next:", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
