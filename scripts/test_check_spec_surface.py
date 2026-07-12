#!/usr/bin/env python3
"""Tests for check-spec-surface.py — the executable spec of the classifier.

Run:  python3 scripts/test_check_spec_surface.py   (or via pytest)
Feeds synthetic `git diff --name-status -M` text and asserts the classifier's
inventory and exit codes. The interesting cases are the ones the hook is
structurally blind to: renames, deletions, and Bash-lane edits that only the
diff can see.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "check-spec-surface.py")


def run(text, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    return subprocess.run([sys.executable, SCRIPT, "-"],
                          input=text, capture_output=True, text=True,
                          timeout=15, env=env)


class SpecSurfaceTests(unittest.TestCase):

    def test_modified_test_file_touches_surface(self):
        r = run("M\ttests/CaptureTests.cs\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Test surface", r.stdout)
        self.assertIn("modified: tests/CaptureTests.cs", r.stdout)

    def test_deleted_test_flagged_as_dropped_requirement(self):
        r = run("D\ttests/CaptureTests.cs\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("silently dropped requirement", r.stdout)

    def test_rename_within_test_surface(self):
        r = run("R100\ttests/OldTests.cs\ttests/NewTests.cs\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("renamed: tests/OldTests.cs -> tests/NewTests.cs", r.stdout)

    def test_rename_out_of_test_surface_treated_as_deletion(self):
        r = run("R100\ttests/CaptureTests.cs\tsrc/Capture.cs\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("renamed OUT of test surface", r.stdout)
        self.assertIn("treat as a deletion", r.stdout)

    def test_contract_and_pact_classified(self):
        r = run("M\tcontracts/openapi.yaml\nM\tpacts/checkout.pact.json\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Contract surface (2)", r.stdout)
        self.assertIn("consumer contract", r.stdout)

    def test_adr_is_review_surface(self):
        r = run("M\tdocs/adr/0007-payments-in-domain-layer.md\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ADR surface", r.stdout)

    def test_fixture_under_tests_dir_is_test_surface(self):
        # mirrors the hook's 0.4.1 fixture rule: data under tests/ is spec
        r = run("M\ttests/fixtures/capture_response.json\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Test surface", r.stdout)

    def test_plain_source_change_is_clean(self):
        r = run("M\tsrc/Payments/Capture.cs\nA\tsrc/Payments/Refund.cs\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("no test/contract/ADR surface touched", r.stdout)
        self.assertIn("Other files touched: 2", r.stdout)

    def test_env_override_shared_with_hook_contract(self):
        r = run("M\tquality/capture.robot\n",
                env_extra={"CTDD_TEST_PATTERNS": r"(^|/)quality/;\.robot$"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("Test surface", r.stdout)

    def test_empty_diff_is_clean(self):
        r = run("")
        self.assertEqual(r.returncode, 0)

    def test_help_exits_zero(self):
        r = subprocess.run([sys.executable, SCRIPT, "--help"],
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0)
        self.assertIn("name-status", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
