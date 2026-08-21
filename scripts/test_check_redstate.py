#!/usr/bin/env python3
"""Tests for check-redstate.py — the executable spec of "observed failing".

Run:  python3 scripts/test_check_redstate.py   (or via pytest)
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "check-redstate.py")

DOTNET_LOG = """\
  Determining projects to restore...
  Failed capture_succeeds_when_amount_is_below_authorized [3 ms]
  Error Message:
   Assert.Equal() Failure
  Passed unrelated_existing_test [1 ms]
Failed!  - Failed:     1, Passed:    42, Skipped:     0, Total:    43
"""

PYTEST_LOG = """\
FAILED tests/test_capture.py::test_capture_releases_remainder - AssertionError
PASSED tests/test_other.py::test_something_else
1 failed, 12 passed in 0.44s
"""

JEST_LOG = """\
  ✕ capture_fails_when_amount_is_zero (4 ms)
  ✓ some_existing_behaviour (1 ms)
Tests: 1 failed, 9 passed, 10 total
"""


def write(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8")
    f.write(text); f.close()
    return f.name


def write_bytes(data):
    f = tempfile.NamedTemporaryFile("wb", suffix=".log", delete=False)
    f.write(data); f.close()
    return f.name


def run(*args, stdin=None):
    # Pin the child's stdio to UTF-8: the logs carry ✕/✓/✗ markers, and a
    # Windows shell's cp1252 default would fail to encode them into stdin (and
    # decode them from stdout), which is a harness artifact, not a script fact.
    return subprocess.run([sys.executable, SCRIPT, *args],
                          input=stdin, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=20)


class CheckRedstateTests(unittest.TestCase):

    def test_dotnet_failing_test_is_verified(self):
        log = write(DOTNET_LOG)
        try:
            r = run(log, "--test", "capture_succeeds_when_amount_is_below_authorized")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("red state verified", r.stdout)
        finally:
            os.unlink(log)

    def test_pytest_failing_test_is_verified(self):
        log = write(PYTEST_LOG)
        try:
            r = run(log, "--test", "test_capture_releases_remainder")
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            os.unlink(log)

    def test_jest_failing_test_is_verified(self):
        log = write(JEST_LOG)
        try:
            r = run(log, "--test", "capture_fails_when_amount_is_zero")
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            os.unlink(log)

    def test_junit_surefire_failure_marker_is_recognised(self):
        log = write("orderIsPaged(OrderTest)  Time elapsed: 0.01 sec  <<< FAILURE!\n")
        try:
            r = run(log, "--test", "orderIsPaged")
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            os.unlink(log)

    def test_go_and_tap_markers_are_recognised(self):
        log = write("--- FAIL: TestCaptureRejectsZero (0.00s)\nnot ok 3 - capture_is_idempotent\n")
        try:
            r = run(log, "--test", "TestCaptureRejectsZero", "--test", "capture_is_idempotent")
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            os.unlink(log)

    def test_test_that_passed_before_implementation_fails_the_check(self):
        log = write(DOTNET_LOG)
        try:
            r = run(log, "--test", "unrelated_existing_test")
            self.assertEqual(r.returncode, 1)
            self.assertIn("passed before implementation", r.stdout)
            self.assertIn("unrelated_existing_test", r.stdout)
        finally:
            os.unlink(log)

    def test_absent_test_fails_the_check(self):
        log = write(DOTNET_LOG)
        try:
            r = run(log, "--test", "never_ran_this_one")
            self.assertEqual(r.returncode, 1)
            self.assertIn("not found in the log", r.stdout)
        finally:
            os.unlink(log)

    def test_summary_line_is_not_evidence_of_failure(self):
        # "Failed:  1, Passed: 42" mentions a name-like token only in aggregate;
        # a test named only there must not count as observed failing.
        log = write("Failed!  - Failed:     1, Passed:    42, Total: 43\n")
        try:
            r = run(log, "--test", "Passed")
            self.assertEqual(r.returncode, 1)
        finally:
            os.unlink(log)

    def test_mixed_results_report_every_offender(self):
        log = write(DOTNET_LOG)
        try:
            r = run(log, "--test", "capture_succeeds_when_amount_is_below_authorized",
                    "--test", "unrelated_existing_test", "--test", "missing_test")
            self.assertEqual(r.returncode, 1)
            self.assertIn("unrelated_existing_test", r.stdout)
            self.assertIn("missing_test", r.stdout)
        finally:
            os.unlink(log)

    def test_log_can_come_from_stdin(self):
        r = run("-", "--test", "capture_fails_when_amount_is_zero", stdin=JEST_LOG)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_no_names_is_usage_error_not_a_pass(self):
        log = write(DOTNET_LOG)
        try:
            r = run(log)
            self.assertEqual(r.returncode, 2)
            self.assertIn("not a pass", r.stdout)
        finally:
            os.unlink(log)

    def test_names_can_be_extracted_from_a_plan(self):
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("Proposed tests:\n"
                   "- capture_fails_when_amount_is_zero\n"
                   "- `capture_succeeds_when_amount_is_below_authorized` — the happy path\n"
                   "- not a test name, just prose\n")
        plan.close()
        log = write(JEST_LOG)
        try:
            r = run(log, "--tests-from", plan.name)
            # one of the two extracted names is absent from the jest log -> exit 1,
            # but extraction itself must have found both underscore-style names.
            self.assertEqual(r.returncode, 1)
            self.assertIn("capture_succeeds_when_amount_is_below_authorized", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_tests_from_ignores_preservation_pin_section(self):
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("### New-behavior tests — must be observed failing\n"
                   "- capture_fails_when_amount_is_zero\n\n"
                   "### Preservation pins — must pass before and after\n"
                   "- maps_missing_reference_to_null\n")
        plan.close()
        log = write(JEST_LOG)   # contains the new-behavior test failing only
        try:
            r = run(log, "--tests-from", plan.name)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("maps_missing_reference_to_null", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_tests_from_ignores_currently_prefixed_pins_anywhere(self):
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("Proposed tests:\n"
                   "- capture_fails_when_amount_is_zero\n"
                   "- currently_returns_200_for_unknown_id\n")
        plan.close()
        log = write(JEST_LOG)
        try:
            r = run(log, "--tests-from", plan.name)
            # It must not be demanded to fail (findings #29, #36), and it must not
            # be certified either. plan-format puts `currently_` names under
            # `Preservation pins`, so one under the new-behaviour heading is a plan
            # defect; step 7.12 stops on any state but intended red and step 8
            # demands intended red for *every* named test, and both key on this
            # exit code. v0.30.0 reported the reclassification and still exited 0,
            # which let an agent proceed with a named test never observed either way.
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("characterization observations", r.stdout)
            self.assertIn("currently_returns_200_for_unknown_id", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_expect_pass_verifies_a_pin_baseline(self):
        log = write("  Passed Entity_to_dto_projection_is_unchanged [2 ms]\n"
                    "Passed!  - Failed:     0, Passed:     2, Total: 2\n")
        try:
            r = run(log, "--expect-pass", "--test", "Entity_to_dto_projection_is_unchanged")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("preservation baseline captured", r.stdout)
        finally:
            os.unlink(log)

    def test_expect_pass_flags_a_pin_that_fails_against_current_code(self):
        log = write("  Failed Entity_to_dto_projection_is_unchanged [2 ms]\n")
        try:
            r = run(log, "--expect-pass", "--test", "Entity_to_dto_projection_is_unchanged")
            self.assertEqual(r.returncode, 1)
            self.assertIn("the pin is wrong, not the code", r.stdout)
        finally:
            os.unlink(log)

    def test_expect_pass_flags_an_unrun_pin(self):
        log = write("  Passed something_else [1 ms]\n")
        try:
            r = run(log, "--expect-pass", "--test", "never_ran_pin")
            self.assertEqual(r.returncode, 1)
            self.assertIn("not found in the log", r.stdout)
        finally:
            os.unlink(log)

    def test_expect_pass_ignores_aggregate_summary_lines(self):
        log = write("Passed!  - Failed:     0, Passed:     2, Total: 2\n")
        try:
            r = run(log, "--expect-pass", "--test", "Passed")
            self.assertEqual(r.returncode, 1)
        finally:
            os.unlink(log)

    def test_prose_mentioning_pins_does_not_swallow_later_names(self):
        # Regression: PIN_HEADING_RX used to be searched anywhere in a line, so a
        # prose line flipped the parser into skip mode and silently dropped every
        # following bullet — while still reporting success for the smaller set.
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("### Proposed tests\n\n"
                   "- capture_fails_when_amount_is_zero\n"
                   "- We considered characterization tests here but it is already pinned.\n"
                   "- capture_rejects_negative_amount\n")
        plan.close()
        log = write("  Failed capture_fails_when_amount_is_zero [3 ms]\n")
        try:
            r = run(log, "--tests-from", plan.name)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("capture_rejects_negative_amount", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_bullet_label_still_starts_a_pin_section(self):
        # The skill's plan format puts the marker in a bullet, not a heading.
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("- `New-behavior tests — must be observed failing`\n"
                   "- capture_fails_when_amount_is_zero\n"
                   "- `Preservation pins — must pass before and after`\n"
                   "- maps_missing_reference_to_null\n")
        plan.close()
        log = write(JEST_LOG)
        try:
            r = run(log, "--tests-from", plan.name)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("maps_missing_reference_to_null", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_expect_pass_tests_from_reads_the_pin_section(self):
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("- `New-behavior tests — must be observed failing`\n"
                   "- brand_new_behaviour\n"
                   "- `Preservation pins — must pass before and after`\n"
                   "- projection_is_unchanged\n")
        plan.close()
        log = write("  Passed projection_is_unchanged [1 ms]\n")
        try:
            r = run(log, "--expect-pass", "--tests-from", plan.name)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("projection_is_unchanged", r.stdout)
            self.assertNotIn("brand_new_behaviour", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_success_message_names_what_it_checked(self):
        log = write(DOTNET_LOG)
        try:
            r = run(log, "--test", "capture_succeeds_when_amount_is_below_authorized")
            self.assertEqual(r.returncode, 0)
            self.assertIn("capture_succeeds_when_amount_is_below_authorized", r.stdout)
        finally:
            os.unlink(log)

    def test_mention_without_a_verdict_is_not_reported_as_a_failing_pin(self):
        log = write("Running projection_is_unchanged now...\n")
        try:
            r = run(log, "--expect-pass", "--test", "projection_is_unchanged")
            self.assertEqual(r.returncode, 1)
            self.assertIn("without a pass/fail marker", r.stdout)
            self.assertNotIn("the pin is wrong", r.stdout)
        finally:
            os.unlink(log)

    def test_existing_behavior_citations_are_not_extracted(self):
        # The plan format cites existing test names under "Existing behavior".
        # Pulling those into the red-state set produced a false "passed before
        # implementation" / "not found" verdict on a fully compliant plan.
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("Existing behavior (openapi.yaml):\n"
                   "- capture_requires_exact_amount — asserts amount == authorized\n\n"
                   "Proposed tests:\n"
                   "- capture_fails_when_amount_is_zero\n")
        plan.close()
        log = write("  Failed capture_fails_when_amount_is_zero [3 ms]\n")
        try:
            r = run(log, "--tests-from", plan.name)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("capture_requires_exact_amount", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_pascalcase_new_test_is_not_silently_dropped(self):
        # A PascalCase name (dotnet/xunit style) must be extracted, not skipped
        # for lacking an underscore — a skipped name let a subset verdict read
        # as a whole-plan "red state verified".
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("Proposed tests:\n"
                   "- ReportsTotalCountAcrossAllPages\n"
                   "- capture_fails_when_amount_is_zero\n")
        plan.close()
        log = write("  Failed capture_fails_when_amount_is_zero [3 ms]\n")
        try:
            r = run(log, "--tests-from", plan.name)
            self.assertEqual(r.returncode, 1, r.stdout)   # PascalCase name absent from log
            self.assertIn("ReportsTotalCountAcrossAllPages", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_expect_pass_tests_from_reads_currently_prefixed_pins(self):
        # currently_* marks a characterization *observation* (nobody has confirmed the
        # behavior is intended). It shares the Preservation pins evidence lane with
        # unmarked pins because both run green-before-and-after; under --expect-pass it must be
        # extracted, not filtered out (which left nothing to verify — exit 2).
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        plan.write("- `Preservation pins — must pass before and after`\n"
                   "- currently_returns_200_for_unknown_id\n")
        plan.close()
        log = write("  Passed currently_returns_200_for_unknown_id [1 ms]\n")
        try:
            r = run(log, "--expect-pass", "--tests-from", plan.name)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("currently_returns_200_for_unknown_id", r.stdout)
        finally:
            os.unlink(plan.name); os.unlink(log)

    def test_utf16_log_file_is_read_not_crashed(self):
        # PowerShell 5.1 `>` writes UTF-16; the mandated capture-to-file path
        # must decode it to a verdict, not die with a UnicodeDecodeError.
        log = write_bytes("  Failed capture_fails_when_amount_is_zero [3 ms]\n".encode("utf-16"))
        try:
            r = run(log, "--test", "capture_fails_when_amount_is_zero")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("red state verified", r.stdout)
        finally:
            os.unlink(log)

    def test_cp1252_byte_in_log_does_not_crash(self):
        # A stray cp1252 byte (0x96) in an otherwise-UTF-8 log must fail closed
        # with a verdict via errors="replace", not a traceback.
        log = write_bytes(b"  Failed capture_fails_when_amount_is_zero \x96 [3 ms]\n")
        try:
            r = run(log, "--test", "capture_fails_when_amount_is_zero")
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            os.unlink(log)

    def test_missing_log_argument_is_usage_error(self):
        r = subprocess.run([sys.executable, SCRIPT],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        self.assertEqual(r.returncode, 2)
        self.assertIn("missing log argument", r.stderr)

    def test_help_exits_zero(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("observed failing", r.stdout)

class GoldenExampleTests(unittest.TestCase):
    """The plan example embedded in ctdd-change/SKILL.md must satisfy the parsers
    it illustrates. Without this, the example and the scripts drift apart silently
    and every agent imitating the example produces plans the gate rejects."""

    @staticmethod
    def _example():
        # The example lives with the format it illustrates. Search the skill and its
        # references so this test follows the example wherever it is kept.
        base = os.path.join(os.path.dirname(__file__), "..", "skills", "ctdd-change")
        for rel in ("references/plan-format.md", "SKILL.md"):
            path = os.path.join(base, rel)
            if not os.path.exists(path):
                continue
            text = open(path, encoding="utf-8").read()
            for block in re.finditer(r"```(?:[A-Za-z0-9_-]+)?\n(.*?)```", text, re.S):
                if "capture_succeeds_when_amount_is_below_authorized" in block.group(1):
                    return block.group(1)
        raise AssertionError("no plan example found in ctdd-change skill or references")

    def test_example_carries_the_mandated_categorical_line(self):
        ex = self._example()
        self.assertRegex(ex, r"Risk:.*contract:",
                         "the example must model the closing categorical line")

    def test_example_carries_both_mandated_test_headings(self):
        """The format requires both headings; the example modelled a bare
        `Proposed tests:` and both checkers certified the contradiction. Agents
        imitate the example, so the example is the operative instruction."""
        ex = self._example()
        for heading in ("New-behavior tests", "Preservation pins"):
            self.assertIn(heading, ex,
                          f"the authoritative example must model `{heading}`")

    def test_example_passes_check_plan(self):
        ex = self._example()
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(ex)
            path = fh.name
        try:
            r = subprocess.run(
                [sys.executable,
                 os.path.join(os.path.dirname(__file__), "check-plan.py"), path],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(r.returncode, 0,
                             f"the skill's own example fails its own linter:\n{r.stdout}")
        finally:
            os.unlink(path)

    def test_example_test_names_are_all_extracted(self):
        ex = self._example()
        names = (
            "capture_succeeds_when_amount_is_below_authorized",
            "capture_succeeds_when_amount_is_one_cent",
            "capture_succeeds_when_amount_is_one_cent_below_authorized",
            "capture_fails_when_released_remainder_is_recaptured",
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(ex)
            plan = fh.name
        log = write("".join(f"  Failed {n} [1 ms]\n" for n in names))
        try:
            r = run(log, "--tests-from", plan)
            self.assertEqual(r.returncode, 0,
                             f"parser did not extract the example's own tests:\n{r.stdout}")
            for n in names:
                self.assertIn(n, r.stdout, f"{n} was silently dropped")
        finally:
            os.unlink(plan); os.unlink(log)


class ExtractionHardeningTests(unittest.TestCase):
    """Tenth instance of the fail-silent shape: names dropped, success reported
    for the subset that survived. Each case below is from a real plan."""

    @staticmethod
    def _plan(text):
        fh = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        fh.write(text); fh.close(); return fh.name

    def test_prose_inside_the_list_does_not_truncate_the_section(self):
        plan = self._plan("- `New-behavior tests — must be observed failing`\n"
                          "- FirstTest\n- SecondTest\n\n"
                          "These cover the paging surface; the next covers the gate.\n\n"
                          "- ThirdTest\n")
        log = write("  Failed FirstTest [1 ms]\n  Failed SecondTest [1 ms]\n")
        try:
            r = run(log, "--tests-from", plan)
            self.assertEqual(r.returncode, 1, "ThirdTest was dropped and never run")
            self.assertIn("ThirdTest", r.stdout)
        finally:
            os.unlink(plan); os.unlink(log)

    def test_emphasis_and_colon_separators_do_not_drop_names(self):
        plan = self._plan("- `New-behavior tests — must be observed failing`\n"
                          "- **BoldName** — why\n- _ItalicName_ — why\n"
                          "- ColonName: why\n")
        log = write("  Failed BoldName [1 ms]\n")
        try:
            r = run(log, "--tests-from", plan)
            for n in ("ItalicName", "ColonName"):
                self.assertIn(n, r.stdout, f"{n} was silently dropped")
        finally:
            os.unlink(plan); os.unlink(log)

    def test_pin_lane_names_the_missing_section_instead_of_a_usage_error(self):
        plan = self._plan("Proposed tests:\n- MapsAllColumns\n")
        log = write("  Passed MapsAllColumns [1 ms]\n")
        try:
            r = run(log, "--expect-pass", "--tests-from", plan)
            self.assertIn("no preservation-pin names", r.stdout)
            self.assertNotIn("usage error", r.stdout)
        finally:
            os.unlink(plan); os.unlink(log)

    def test_authoritative_example_satisfies_both_checkers(self):
        """The authoritative reference example must pass both consumers."""
        ex = GoldenExampleTests._example()
        plan = self._plan(ex)
        names = (
            "capture_succeeds_when_amount_is_below_authorized",
            "capture_succeeds_when_amount_is_one_cent",
            "capture_succeeds_when_amount_is_one_cent_below_authorized",
            "capture_fails_when_released_remainder_is_recaptured",
        )
        log = write("".join(f"  Failed {n} [1 ms]\n" for n in names))
        try:
            cp = subprocess.run([sys.executable, os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "check-plan.py"), plan],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(cp.returncode, 0, f"example fails check-plan:\n{cp.stdout}")
            r = run(log, "--tests-from", plan)
            self.assertEqual(r.returncode, 0, f"example fails check-redstate:\n{r.stdout}")
        finally:
            os.unlink(plan); os.unlink(log)

    def test_a_plan_contributing_no_names_is_reported(self):
        """--test plus a --tests-from that yields nothing reported success for the
        one explicit name, so the plan cross-check silently stopped operating and
        a swapped test would have passed unnoticed."""
        plan = self._plan("No test section here at all.\n")
        log = write("  Failed SomeTest [1 ms]\n")
        try:
            r = run(log, "--test", "SomeTest", "--tests-from", plan)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("contributed no test names", r.stdout)
        finally:
            os.unlink(plan); os.unlink(log)

    def test_every_marker_rendering_is_classified_as_an_observation(self):
        """Extraction learned PascalCase at finding #29; this classification
        filter did not, so `CurrentlyReturnsX` read as a new-behaviour test and
        landed in the red-state set it is exempt from. Fix-one-call-site again."""
        plan = self._plan("- `New-behavior tests — must be observed failing`\n"
                          "- CurrentlyReturns200ForUnknownId\n"
                          "- Currently_returns_200\n"
                          "- currently_returns_200\n"
                          "- ReturnsPagedResult\n")
        log = write("  Failed ReturnsPagedResult [1 ms]\n")
        try:
            r = run(log, "--tests-from", plan)
            self.assertEqual(r.returncode, 2, f"a marked name under the new-behaviour "
                             f"heading is a plan defect, not a pass:\n{r.stdout}")
            for marked in ("CurrentlyReturns200ForUnknownId", "Currently_returns_200"):
                # It must not appear in the verified red-state list; it must
                # appear in the reclassification report, so a name leaving the
                # red set is visible rather than silent.
                verified = r.stdout.split("observed failing", 1)[0].split(
                    "characterization observations", 1)[-1]
                self.assertNotIn(marked, verified.split("check-redstate:")[-1],
                                 f"{marked} is an observation, not new behaviour")
                self.assertIn(marked, r.stdout,
                              f"{marked} was reclassified without being reported")
        finally:
            os.unlink(plan); os.unlink(log)

    def test_a_name_must_match_as_a_whole_identifier(self):
        """`--test Foo` was satisfied by a log line mentioning `FooBar`, so the
        checker certified a test that never ran."""
        log = write("FAILED tests/test_x.py::FooBar - assertion failed\n")
        try:
            r = run(log, "--test", "Foo")
            self.assertEqual(r.returncode, 1, f"Foo did not run:\n{r.stdout}")
        finally:
            os.unlink(log)

    def test_marker_words_inside_a_test_name_are_not_verdicts(self):
        """`error_handling_is_logged` contains 'error' and `success_is_logged`
        contains 'success'; scanning the whole line let each certify itself
        from a log with no verdict anywhere in it."""
        for text, args in ((("RUNNING error_handling_is_logged\n"),
                            ("--test", "error_handling_is_logged")),
                           (("RUNNING success_is_logged\n"),
                            ("--expect-pass", "--test", "success_is_logged"))):
            log = write(text)
            try:
                r = run(log, *args)
                self.assertEqual(r.returncode, 1, f"no verdict present:\n{r.stdout}")
            finally:
                os.unlink(log)

    def test_the_bug_fix_lane_states_its_format_requirement(self):
        """The worked bug-fix example was removed when the skill was rewritten as
        procedure, and that is defensible: finding #46 found four competing
        heading vocabularies across duplicated examples, and one canonical
        example (guarded separately) has no drift surface. But finding #41's
        lesson stands — the bug-fix lane is the modal case — so the *rule* must
        still say the plan is short AND complete, or an agent reading only this
        skill will produce the partial plan that started #41."""
        import os
        skill = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "skills", "ctdd-change", "SKILL.md")
        text = open(skill, encoding="utf-8").read()
        self.assertRegex(text, r"bug fix, require a short complete plan",
                         "the bug-fix lane must require a complete plan, not a partial one")
        self.assertRegex(text, r"New-behavior tests. section names the regression test",
                         "and must say where the regression test is declared")

    def test_fully_qualified_dotnet_names_are_matched(self):
        """`dotnet test --logger "console;verbosity=detailed"` prints every test as
        Namespace.Class.Method. The identifier-boundary rule added for the
        Foo/FooBar case rejected a leading dot, so the most common real log
        format matched nothing — found in real use, not by review."""
        log = write("  Passed Acme.Svc.IntegrationTests.RepoTests."
                    "GetByDocumentNumberAsync_OrdersCorrectly [12 ms]\n")
        try:
            r = run(log, "--expect-pass", "--test", "GetByDocumentNumberAsync_OrdersCorrectly")
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            os.unlink(log)

    def test_a_trailing_dot_still_rejects_a_prefix_match(self):
        """A dot before is a namespace separator; a dot after means the match is
        a prefix of a longer qualified name, which is a different test."""
        log = write("  Passed Acme.Svc.Method [1 ms]\n")
        try:
            r = run(log, "--expect-pass", "--test", "Svc")
            self.assertEqual(r.returncode, 1, f"'Svc' is a class, not the test:\n{r.stdout}")
        finally:
            os.unlink(log)



class ExtractionDefectTests(unittest.TestCase):
    """Four ways a named test left the evidence set with nothing said about it."""

    H = "New-behavior tests — must be observed failing:\n"
    P = "Preservation pins — must pass before and after: none — n/a\n"

    def _names(self, body):
        import importlib.util
        spec = importlib.util.spec_from_file_location("cr_x", SCRIPT)
        cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
        return cr.names_from_plan(write(self.H + body + self.P))[0]

    def test_a_hyphenated_name_is_not_truncated_to_its_first_stem(self):
        """The terminator alternation included a bare `-`, so
        `capture-fails-when-zero` captured as `capture` — and `_match_span` then
        accepted that stem against every hyphenated name in the log, because `-`
        is a boundary. Two distinct tests collapsed to one and a single failing
        run certified both."""
        got = self._names("- capture-fails-when-zero — path: x.\n"
                          "- capture-fails-when-negative — path: x.\n")
        self.assertEqual(got, ["capture-fails-when-zero", "capture-fails-when-negative"])

    def test_a_wrapped_bullet_does_not_close_the_section(self):
        """`_is_heading` treated any short non-bullet line without terminal
        punctuation as a boundary, so a wrapped `- name — path: …; case: …` ended
        the list and the checker verified the shorter one."""
        got = self._names("- capture_fails_when_zero — path: `t.cs`; case: negative\n"
                          "  and leaves the payment untouched\n"
                          "- capture_fails_when_negative — path: `t.cs`.\n")
        self.assertEqual(len(got), 2, got)

    def test_a_long_section_label_still_closes_the_section(self):
        """The 72-character ceiling meant plan-format.md's own 76-character
        conditional label failed to close the section, so copying the skeleton
        verbatim extracted the `n/a` coverage rows as test names and sent the
        agent hunting for a test that never existed."""
        got = self._names(
            "- capture_fails_when_zero — path: `t.cs`.\n"
            "Case coverage not reached (conditional: omitted at the small or medium tier)\n"
            "- authorization — n/a — no auth surface.\n")
        self.assertEqual(got, ["capture_fails_when_zero"])

    def test_a_bullet_that_yields_no_name_is_reported_not_dropped(self):
        """Only `currently_` names reached `skipped`; everything else hit
        `if not m: continue`. A fully-qualified name, a generic parameter or an
        unbalanced backtick produced an empty section with nothing reported, and
        the tier, the evidence lanes and the packet all agreed there were no
        tests."""
        log = write("  Failed capture_fails_when_zero [1 ms]\n")
        for body in ("- tests/T.cs::capture_fails\n", "- Capture_Fails<Decimal>\n"):
            r = run(log, "--tests-from", write(self.H + body + self.P))
            self.assertEqual(r.returncode, 2, f"{body!r} vanished:\n{r.stdout}")
            self.assertIn("yielded no test name", r.stdout)

    def test_explanatory_prose_in_a_list_is_not_reported(self):
        """Plans legitimately put a sentence in the list; only a bullet that looks
        like a name and is not one must be reported."""
        r = run(write("  Failed capture_fails_when_zero [1 ms]\n"), "--tests-from",
                write(self.H + "- capture_fails_when_zero — path: `t.cs`.\n"
                      "- We considered a characterization test here.\n" + self.P))
        self.assertEqual(r.returncode, 0, r.stdout)


class GoAndTapPinTests(unittest.TestCase):
    """`FAIL_MARKERS` carried `fail:` and `not ok`, so both runners could report
    red state; the pass side had no `--- PASS:` and `ok ` self-disqualified,
    because the character after it is the TAP test number and a digit joins. So a
    Go or TAP repository could never verify a preservation pin — the lane every
    change needs."""

    def test_go_verifies_a_pin(self):
        r = run(write("--- PASS: TestCaptureRejectsZero (0.00s)\n"),
                "--test", "TestCaptureRejectsZero", "--expect-pass")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_tap_verifies_a_pin(self):
        r = run(write("ok 1 - capture rejects zero\n"),
                "--test", "capture rejects zero", "--expect-pass")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_go_pass_is_still_not_red_state(self):
        r = run(write("--- PASS: TestX (0.00s)\n"), "--test", "TestX")
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_go_and_tap_failures_still_verify_red(self):
        for log, name in (("--- FAIL: TestX (0.00s)\n", "TestX"),
                          ("not ok 1 - capture rejects zero\n", "capture rejects zero")):
            r = run(write(log), "--test", name)
            self.assertEqual(r.returncode, 0, r.stdout)


class MarkerDelimiterTests(unittest.TestCase):
    """v0.29.0 disqualified a marker only when the adjacent character was
    alphanumeric or `_`, so it fixed one spelling of the bug and its guard tested
    only underscore identifiers. Path separators, dots, hyphens and spaces still
    voted:

        tests/error/test_capture.py::test_x PASSED   -> "red state verified"
        tests/success/CaptureTests.cs::pin FAILED    -> "baseline captured"

    The pin lane is the worse half: it fails *open*, so a pin that never passed is
    recorded as a baseline and 8.3's re-run has nothing to compare against — which
    makes the `broken pin` state added in v0.35.0 undetectable in any repository
    with a `success/` or `ok/` path segment."""

    GREEN = ("tests/error/t.py::test_x PASSED\n",
             "tests/error-paths/t.py::test_x PASSED\n",
             "src/error.handling/t.py::test_x PASSED\n",
             "tests/Error Paths/T.cs::test_x PASSED\n",
             "tests/test_error_paths.py::test_x PASSED\n")

    def test_a_marker_inside_a_path_never_certifies_red_state(self):
        for log in self.GREEN:
            r = run(write(log), "--test", "test_x")
            self.assertEqual(r.returncode, 1, f"{log!r} certified as red:\n{r.stdout}")

    def test_a_marker_inside_a_path_never_certifies_a_pin_baseline(self):
        for seg in ("success", "success-paths", "ok", "passed.paths"):
            log = f"tests/{seg}/T.cs::pin_holds FAILED\n"
            r = run(write(log), "--test", "pin_holds", "--expect-pass")
            self.assertEqual(r.returncode, 1, f"{log!r} certified as a baseline:\n{r.stdout}")

    def test_real_runner_output_still_verifies(self):
        for log, name, extra in (
                ("  Failed Ns.CaptureTests.rejects_zero [4 ms]\n", "rejects_zero", []),
                ("tests/test_capture.py::test_rejects FAILED\n", "test_rejects", []),
                ("  \u2715 rejects_zero (4 ms)\n", "rejects_zero", []),
                ("--- FAIL: TestRejectsZero (0.00s)\n", "TestRejectsZero", []),
                ("  Passed Ns.CaptureTests.pin_holds [2 ms]\n", "pin_holds", ["--expect-pass"]),
                ("  \u2713 pin_holds (2 ms)\n", "pin_holds", ["--expect-pass"])):
            r = run(write(log), "--test", name, *extra)
            self.assertEqual(r.returncode, 0, f"{log!r} stopped verifying:\n{r.stdout}")


class ContradictoryVerdictTests(unittest.TestCase):
    """Exit 2 while printing "red state verified" put a verdict the packet copies
    verbatim (worked-change.md:108) on a run the same command refuses to certify —
    a conformant packet recording verified red state from an uncertified run."""

    PLAN = ("New-behavior tests — must be observed failing:\n"
            "- `t_one`\n- `currently_t_two`\n"
            "Preservation pins — must pass before and after: none — n/a\n")

    def test_a_reclassified_name_never_prints_a_verified_verdict(self):
        plan = write(self.PLAN)
        r = run(write("  Failed t_one [1 ms]\n"), "--tests-from", plan)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertNotIn("red state verified", r.stdout)
        self.assertIn("RED STATE NOT VERIFIED", r.stdout)

    def test_a_clean_run_still_prints_the_verified_verdict(self):
        plan = write("New-behavior tests — must be observed failing:\n- `a_one`\n"
                     "Preservation pins — must pass before and after: none — n/a\n")
        r = run(write("  Failed a_one [1 ms]\n"), "--tests-from", plan)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("red state verified", r.stdout)


class SetupErrorTests(unittest.TestCase):
    """pytest reports a fixture collapse as `ERROR tests/x.py::t - KeyError`, and
    `error` is a FAIL_MARKER — so two tests that only ERRORed in setup certified as
    "red state verified" with no assertion ever executed. `execution.md` has a
    state for exactly this: **wrong red**, *the failure comes from setup,
    environment, a typo, or an unrelated defect*."""

    PLAN = ("New-behavior tests — must be observed failing:\n"
            "- `test_rejects_zero`\n- `test_accepts_partial`\n"
            "Preservation pins — must pass before and after: none — n/a\n")

    def test_a_fixture_error_is_not_intended_red(self):
        log = write("ERROR tests/test_capture.py::test_rejects_zero - KeyError: 'f'\n"
                    "ERROR tests/test_capture.py::test_accepts_partial - KeyError: 'f'\n")
        r = run(log, "--tests-from", write(self.PLAN))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("errored before the test body ran", r.stdout)
        self.assertNotIn("red state verified", r.stdout)
        # and it must not be misdiagnosed as behaviour that already exists
        self.assertNotIn("passed before implementation", r.stdout)

    def test_a_real_assertion_failure_still_verifies(self):
        log = write("FAILED tests/test_capture.py::test_rejects_zero - AssertionError\n"
                    "FAILED tests/test_capture.py::test_accepts_partial - AssertionError\n")
        r = run(log, "--tests-from", write(self.PLAN))
        self.assertEqual(r.returncode, 0, r.stdout)


class AnsiColourTests(unittest.TestCase):
    """An SGR escape terminates in `m`, an alphanumeric, so a coloured `FAILED`
    disqualified its own marker. The mention survived as a verdict-less line and
    routed to *passing*: a red test was reported as "passed before implementation"
    and the remediation accused a correct test of asserting nothing. Most CI
    runners emit colour by default."""

    def test_a_coloured_failure_verifies_red_state(self):
        r = run(write("tests/t.py::test_x \x1b[31mFAILED\x1b[0m  [100%]\n"), "--test", "test_x")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_coloured_pass_verifies_a_pin(self):
        r = run(write("tests/t.py::pin \x1b[32mPASSED\x1b[0m\n"),
                "--test", "pin", "--expect-pass")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_coloured_pass_is_not_red_state(self):
        r = run(write("tests/t.py::test_x \x1b[32mPASSED\x1b[0m\n"), "--test", "test_x")
        self.assertEqual(r.returncode, 1, r.stdout)


class MarkerWordTests(unittest.TestCase):
    """A fully green pytest run certified as red state. `_verdict_text` stripped
    the matched test name but left the rest of the line, so `test_error_paths.py`
    put `error` at index 12 against `passed` at 30, and first-marker-wins read a
    PASSED line as a failure. Step 7.11 runs exactly this command and 7.12 treats
    exit 0 as intended red, so an agent that implemented first and captured green
    passed the gate — the vacuous-test case the script exists to catch.

    Markers must be whole words. `--expect-pass` failed closed on the same input,
    so only the safety-critical lane was wrong."""

    def test_a_green_run_in_a_module_named_error_is_not_red_state(self):
        log = ("tests/test_error_paths.py::test_rejects_expired PASSED\n"
               "tests/test_error_paths.py::test_accepts_valid PASSED\n")
        r = run(write(log), "--test", "test_rejects_expired", "--test", "test_accepts_valid")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertNotIn("red state verified", r.stdout)

    def test_a_marker_word_inside_any_identifier_does_not_vote(self):
        for ident in ("test_failure_modes", "assert_helpers", "success_paths"):
            log = f"tests/{ident}.py::t_case PASSED\n"
            r = run(write(log), "--test", "t_case")
            self.assertEqual(r.returncode, 1, f"{ident}: {r.stdout}")

    def test_a_real_failure_still_verifies(self):
        r = run(write("  Failed Ns.T_Case [4 ms]\n"), "--test", "T_Case")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_real_pass_still_verifies_a_pin(self):
        r = run(write("tests/test_error_paths.py::T_Pin PASSED\n"),
                "--test", "T_Pin", "--expect-pass")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_pass_lane_was_never_wrong_and_stays_right(self):
        r = run(write("tests/test_error_paths.py::T_Pin PASSED\n"), "--test", "T_Pin")
        self.assertEqual(r.returncode, 1)


class StackTraceTests(unittest.TestCase):
    """v0.24.0 regression, caught by the 2026-07-30 session. A .NET failure block
    names the test twice — `Failed <FQN> [4 ms]`, then `at <FQN>() in ...` in the
    stack trace, with no marker. The duplicate-name fix required every occurrence
    to agree and read the unmarked line as dissent, so ordinary red state stopped
    verifying: two RED STATE NOT VERIFIED before the agent worked around it. An
    unmarked mention is not a dissenting verdict; it is not a verdict."""

    FAIL_WITH_TRACE = ("  Failed Ns.Tests.T_Boundary [4 ms]\n"
                       "  Error Message:\n   Assert.True() Failure\n"
                       "  Stack Trace:\n     at Ns.Tests.T_Boundary() in D:\\src\\a.cs:line 42\n")

    def test_a_stack_trace_repeating_the_name_still_verifies_red(self):
        r = run(write(self.FAIL_WITH_TRACE), "--test", "T_Boundary")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_stack_trace_is_not_reported_as_disagreement(self):
        r = run(write(self.FAIL_WITH_TRACE), "--test", "T_Boundary")
        self.assertNotIn("occurrences disagree", r.stdout)

    def test_a_pin_log_with_a_trailing_unmarked_mention_still_verifies(self):
        log = "  Passed Ns.T_Pin [1 ms]\n  (also referenced by Ns.T_Pin in the summary)\n"
        r = run(write(log), "--test", "T_Pin", "--expect-pass")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_genuine_disagreement_is_still_caught_alongside_a_stack_trace(self):
        log = ("  Failed A.T_Dup [1 ms]\n     at A.T_Dup() in a.cs:line 1\n"
               "  Passed B.T_Dup [1 ms]\n")
        r = run(write(log), "--test", "T_Dup")
        self.assertEqual(r.returncode, 1)
        self.assertIn("occurrences disagree", r.stdout)
        self.assertIn("T_Dup (2 occurrences)", r.stdout)


class DuplicateNameTests(unittest.TestCase):
    """Found by the 2026-07-27 Flik change: two preservation pins shared a name
    across the V1 and V2 handler test files. Both matchers returned on the first
    line matching the direction asked, so a name failing in one project and
    passing in the other was verified either way — the eleventh defect of the
    shape 'verify the subset you can read, report success'."""

    MIXED = "  Failed Dup [1 ms]\n  Passed Dup [1 ms]\n"

    def test_a_mixed_result_is_not_red_state(self):
        r = run(write(self.MIXED), "--test", "Dup")
        self.assertEqual(r.returncode, 1)
        self.assertIn("occurrences disagree", r.stdout)
        self.assertIn("Dup (2 occurrences)", r.stdout)

    def test_a_mixed_result_is_not_a_pin_baseline(self):
        r = run(write(self.MIXED), "--test", "Dup", "--expect-pass")
        self.assertEqual(r.returncode, 1)
        self.assertIn("occurrences disagree", r.stdout)

    def test_every_occurrence_agreeing_still_verifies_red(self):
        r = run(write("  Failed X [1 ms]\n  Failed X [2 ms]\n"), "--test", "X")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_every_occurrence_agreeing_still_verifies_pins(self):
        r = run(write("  Passed X [1 ms]\n  Passed X [2 ms]\n"),
                "--test", "X", "--expect-pass")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_single_occurrence_is_never_reported_as_ambiguous(self):
        r = run(write("  Failed Solo [1 ms]\n"), "--test", "Solo")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("occurrences disagree", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
