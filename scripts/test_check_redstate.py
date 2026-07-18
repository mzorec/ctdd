#!/usr/bin/env python3
"""Tests for check-redstate.py — the executable spec of "observed failing".

Run:  python3 scripts/test_check_redstate.py   (or via pytest)
"""

import os
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


def run(*args, stdin=None):
    return subprocess.run([sys.executable, SCRIPT, *args],
                          input=stdin, capture_output=True, text=True, timeout=20)


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
        log = write("taxPayerIsPaged(TaxPayerTest)  Time elapsed: 0.01 sec  <<< FAILURE!\n")
        try:
            r = run(log, "--test", "taxPayerIsPaged")
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
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("currently_", r.stdout)
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

    def test_help_exits_zero(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("observed failing", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
