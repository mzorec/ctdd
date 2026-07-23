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

FULL_PLAN = """BLOCKING — I will not guess:
- auth hold on the released remainder? (recommend: expires with the auth)
Proceeding unless you object:
- zero capture rejected
Risk level: normal — money path
Existing behavior (openapi.yaml; CaptureTests.cs):
- x
Assumptions:
- y
Uncovered / ambiguous:
- z
Proposed tests:
- t
Contract changes: none
NFR budgets touched: none
Hold-out: not required — read path
Files likely to change:
- a.cs
"""


def run(plan_text, extra_args=None):
    return subprocess.run([sys.executable, SCRIPT, "-"] + (extra_args or []),
                          input=plan_text, capture_output=True, text=True,
                          timeout=15)


def diff_file(content):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    f.write(content); f.close()
    return f.name


class CheckPlanTests(unittest.TestCase):

    def test_full_plan_passes(self):
        r = run(FULL_PLAN)
        self.assertEqual(r.returncode, 0)
        self.assertIn("all mandatory sections present", r.stdout)

    def test_missing_sections_fail_and_are_named(self):
        r = run("Risk level: normal — x\nExisting behavior: y\nAssumptions: z\n"
                "Uncovered: q\nProposed tests: t\nContract changes: none\n"
                "Files likely to change: a\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("NFR budgets", r.stdout)
        self.assertIn("hold-out decision", r.stdout)

    def test_trivial_without_diff_passes_with_hint(self):
        r = run("Risk: trivial — typo in log message. Skipping the plan gate.\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--diff", r.stdout)

    def test_trivial_newline_bypass_still_rejected(self):
        r = run("Risk level: trivial —\nExisting behavior: smuggled\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("MISSING", r.stdout)

    def test_trivial_with_clean_diff_stands(self):
        d = diff_file("M\tsrc/Payments/Capture.cs\n")
        try:
            r = run("Risk: trivial — null check in logging. Skipping the plan gate.\n",
                    ["--diff", d])
            self.assertEqual(r.returncode, 0)
            self.assertIn("trivial claim stands", r.stdout)
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

    def test_pins_only_plan_satisfies_the_test_section(self):
        # A behavior-preserving refactor's plan lists preservation pins instead
        # of "Proposed tests" — the heading vocabulary the skill itself mandates.
        # It must satisfy the required test-section check, not be rejected.
        plan = FULL_PLAN.replace("Proposed tests:\n- t\n",
                                 "Preservation pins — must pass before and after:\n"
                                 "- currently_maps_entity_to_dto\n")
        r = run(plan)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("all mandatory sections present", r.stdout)

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
        self.assertIn("canonical location", r.stdout)

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
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0)
        self.assertIn("omission detector", r.stdout)


class ComposedCheckerTests(unittest.TestCase):
    """The standalone checker refusing malformed input is not enough: check-plan
    imports the same parser, and a fail-open there turns 'could not parse' into
    'no surface touched', which passes an unverified trivial claim."""

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
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, f"must not pass over discarded input:\n{r.stdout}")
        self.assertIn("unparseable", r.stdout)
        self.assertNotIn("trivial claim stands", r.stdout)

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


if __name__ == "__main__":
    unittest.main(verbosity=1)
