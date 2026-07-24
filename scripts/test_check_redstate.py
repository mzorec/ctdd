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
            block = re.search(r"```\n(.*?)```", open(path, encoding="utf-8").read(), re.S)
            if block and "Risk:" in block.group(1):
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
                capture_output=True, text=True)
            self.assertEqual(r.returncode, 0,
                             f"the skill's own example fails its own linter:\n{r.stdout}")
        finally:
            os.unlink(path)

    def test_example_test_names_are_all_extracted(self):
        ex = self._example()
        names = re.findall(r"^- ([a-z][a-z0-9_]*)$", ex, re.M)
        self.assertGreaterEqual(len(names), 3, "example should propose several tests")
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
            self.assertIn("no preservation-pin section", r.stdout)
            self.assertNotIn("usage error", r.stdout)
        finally:
            os.unlink(plan); os.unlink(log)

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


if __name__ == "__main__":
    unittest.main(verbosity=1)
