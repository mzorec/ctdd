#!/usr/bin/env python3
"""Tests for spec-edit-guard.py — the executable spec of the hook's behavior.

Run:  python3 hooks/test_spec_edit_guard.py
Stdlib only (unittest + subprocess); no pytest required, though pytest will
also collect it. Each case is a (payload, expectation) pair lifted from the
runtime review's fixture table, plus the regressions that were actually
caught during development ('latest.md', 'LoadTest.md', spec-dir YAML).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = str(Path(__file__).resolve().parent / "spec-edit-guard.py")


def run_guard(payload, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    r = subprocess.run(
        [sys.executable, GUARD],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True, text=True, timeout=10, env=env,
    )
    return r


def post(tool, path):
    return {"hook_event_name": "PostToolUse", "tool_name": tool,
            "tool_input": {"file_path": path}}


def pre_write(path):
    return {"hook_event_name": "PreToolUse", "tool_name": "Write",
            "tool_input": {"file_path": path, "content": "..."}}


class SpecEditGuardTests(unittest.TestCase):

    # ---------- helpers ----------
    def assert_fires(self, result, event, keyword):
        out = result.stdout.strip()
        self.assertTrue(out, "expected a reminder, got silence")
        j = json.loads(out)
        self.assertEqual(j["hookSpecificOutput"]["hookEventName"], event)
        self.assertIn(keyword, j["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(result.returncode, 0)

    def assert_silent(self, result):
        self.assertEqual(result.stdout.strip(), "", "expected silence")
        self.assertEqual(result.returncode, 0)

    # ---------- PostToolUse: test-edit branch ----------
    def test_edit_dotnet_test_fires(self):
        self.assert_fires(run_guard(post("Edit", "src/Payments.Tests/CaptureTests.cs")),
                          "PostToolUse", "changed spec")

    def test_multiedit_tests_dir_fires(self):
        self.assert_fires(run_guard(post("MultiEdit", "tests/capture/handlers.py")),
                          "PostToolUse", "changed spec")

    def test_windows_path_fires(self):
        self.assert_fires(run_guard(post("Edit", "C:\\repo\\tests\\FooTests.cs")),
                          "PostToolUse", "changed spec")

    def test_write_new_test_file_silent_on_post(self):
        # Any Write is silent on the test branch of PostToolUse — the
        # overwrite case is owned by PreToolUse below.
        self.assert_silent(run_guard(post("Write", "src/Payments.Tests/RefundTests.cs")))

    # ---------- PostToolUse: contract branch ----------
    def test_edit_openapi_fires_contract(self):
        self.assert_fires(run_guard(post("Edit", "payments/contract/openapi.yaml")),
                          "PostToolUse", "boundary change")

    def test_write_new_proto_fires_contract(self):
        self.assert_fires(run_guard(post("Write", "proto/transfers.proto")),
                          "PostToolUse", "boundary change")

    def test_pact_file_fires_contract(self):
        self.assert_fires(run_guard(post("Edit", "pacts/checkout-payments.pact.json")),
                          "PostToolUse", "boundary change")

    def test_openapi_in_spec_dir_is_contract_not_test(self):
        self.assert_fires(run_guard(post("Edit", "spec/openapi.yaml")),
                          "PostToolUse", "boundary change")

    # ---------- false-positive regressions ----------
    def test_latest_md_silent(self):
        # 'la**test**' must not match Tests? case-insensitively.
        self.assert_silent(run_guard(post("Edit", "docs/latest.md")))

    def test_loadtest_md_silent(self):
        # A doc named *Test.md must not fire the test branch (extension guard).
        self.assert_silent(run_guard(post("Edit", "docs/LoadTest.md")))

    def test_fixture_json_under_tests_dir_fires(self):
        # weakness #3's fixture surface: golden/fixture data under tests/ IS spec
        self.assert_fires(run_guard(post("Edit", "tests/fixtures/capture_response.json")),
                          "PostToolUse", "test file patterns")

    def test_fixture_yaml_under_testdata_dir_fires(self):
        self.assert_fires(run_guard(post("Edit", "tests/testdata/expected.yaml")),
                          "PostToolUse", "test file patterns")

    def test_write_overwrite_of_existing_fixture_fires(self):
        # regenerating a golden file wholesale is a spec change too
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join(d, "tests", "fixtures")
            os.makedirs(fx)
            f = os.path.join(fx, "golden.json")
            open(f, "w").write("{}")
            self.assert_fires(run_guard(pre_write(f)),
                              "PreToolUse", "test file patterns")

    def test_spec_filename_yaml_outside_tests_dir_stays_silent(self):
        # payments.spec.yaml matches the .spec. filename pattern but is most
        # likely an API spec — pinned silent, deliberately
        self.assert_silent(run_guard(post("Edit", "payments.spec.yaml")))

    def test_yaml_in_spec_dir_not_mislabeled(self):
        # Contract-shaped file in a test-ish dir: silence beats mislabeling.
        self.assert_silent(run_guard(post("Edit", "spec/payments.yaml")))

    def test_attestation_silent(self):
        self.assert_silent(run_guard(post("Edit", "src/attestation_service.py")))

    def test_ordinary_source_silent(self):
        self.assert_silent(run_guard(post("Edit", "src/Payments/Domain/Capture.cs")))

    # ---------- PreToolUse: Write-overwrite hole ----------
    def test_pre_write_overwriting_existing_test_fires(self):
        with tempfile.TemporaryDirectory() as d:
            existing = os.path.join(d, "tests", "CaptureTests.cs")
            os.makedirs(os.path.dirname(existing))
            Path(existing).write_text("old")
            self.assert_fires(run_guard(pre_write(existing)),
                              "PreToolUse", "overwritten")

    def test_pre_write_new_test_file_silent(self):
        with tempfile.TemporaryDirectory() as d:
            new = os.path.join(d, "tests", "BrandNewTests.cs")  # does not exist
            self.assert_silent(run_guard(pre_write(new)))

    def test_pre_write_existing_non_test_silent(self):
        with tempfile.TemporaryDirectory() as d:
            existing = os.path.join(d, "src", "Capture.cs")
            os.makedirs(os.path.dirname(existing))
            Path(existing).write_text("old")
            self.assert_silent(run_guard(pre_write(existing)))

    def test_pre_edit_event_ignored(self):
        # PreToolUse only owns Write; anything else stays silent.
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                   "tool_input": {"file_path": "tests/CaptureTests.cs"}}
        self.assert_silent(run_guard(payload))

    # ---------- robustness + tuning ----------
    def test_bash_tool_ignored(self):
        self.assert_silent(run_guard(post("Bash", "irrelevant")))

    def test_missing_file_path_silent(self):
        self.assert_silent(run_guard({"hook_event_name": "PostToolUse",
                                      "tool_name": "Edit", "tool_input": {}}))

    def test_malformed_stdin_silent_exit_zero(self):
        self.assert_silent(run_guard("not json"))

    def test_env_override_replaces_defaults(self):
        env = {"CTDD_TEST_PATTERNS": r"(^|/)quality/;\.robot$"}
        self.assert_fires(run_guard(post("Edit", "quality/checks/foo.robot"), env),
                          "PostToolUse", "changed spec")
        # And the defaults are gone under an override:
        self.assert_silent(run_guard(post("Edit", "tests/capture/handlers.py"), env))

    def test_soap_contract_override(self):
        env = {"CTDD_CONTRACT_PATTERNS": r"\.wsdl$;\.xsd$"}
        self.assert_fires(run_guard(post("Edit", "schemas/DDV.xsd"), env),
                          "PostToolUse", "boundary change")


if __name__ == "__main__":
    unittest.main(verbosity=2)
