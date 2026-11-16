#!/usr/bin/env python3
"""Tests for spec-edit-guard.py — the executable spec of the hook's behavior.

Run:  python3 hooks/test_spec_edit_guard.py
Stdlib only (unittest + subprocess); no pytest required, though pytest will
also collect it. Each case is a (payload, expectation) pair lifted from the
runtime review's fixture table, plus the regressions that were actually
caught during development ('latest.md', 'LoadTest.md', spec-dir YAML).
"""

import importlib.util
import json
import os
import re
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
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, env=env,
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
        # `C:\\repo\\tests\\FooTests.cs` matched the PascalCase rule un-normalised,
        # because `[^/]*` never sees a forward slash — so this passed with
        # backslash normalisation deleted. The shape that actually needs it is a
        # directory match on a lowercase filename.
        self.assert_fires(run_guard(post("Edit", "C:\\repo\\tests\\handlers.py")),
                          "PostToolUse", "changed spec")
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

    def test_a_service_prefixed_openapi_snapshot_fires_contract(self):
        # A real change regenerated `docs/api/<service>-openapi-v1.json` and no
        # run printed a contract section: the name matched none of the
        # defaults, which required `openapi` at the start of the basename or
        # as a `.openapi.` infix. The word anywhere in the basename is enough.
        self.assert_fires(run_guard(post("Write", "docs/api/orders-openapi-v1.json")),
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
    def test_a_write_that_drops_assertions_says_so(self):
        """`tool_input` carries the replacement text and the branch discarded it,
        so a Write replacing a 400-line suite with an assertion-free stub got
        byte-identical advice to one that adds a case."""
        import tempfile, os, json, subprocess, sys as _s
        d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "tests"))
        with open(os.path.join(d, "tests", "CaptureTests.cs"), "w",
                  encoding="utf-8") as fh:
            fh.write("\n".join(f"Assert.Equal({i}, x);" for i in range(8)))

        def write_event(content):
            ev = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Write",
                             "tool_input": {"file_path": "tests/CaptureTests.cs",
                                            "content": content}})
            return subprocess.run([_s.executable, GUARD], input=ev, cwd=d,
                                  capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=15)

        stub = write_event("// TODO\n")
        self.assertIn("drops 8 of 8", stub.stdout)
        richer = write_event("\n".join(f"Assert.Equal({i}, x);" for i in range(9)))
        self.assertTrue(richer.stdout.strip(), "an overwrite must still warn")
        # the base message itself contains the word "drops"; assert on the count
        self.assertNotIn("assertion(s) (", richer.stdout)

    def test_approval_baselines_fire_in_a_dotted_test_project(self):
        """`AMBIGUOUS_EXT` suppressed any test match outside a literal `tests/`
        directory, and `src/Payments.Tests/` is not one — the dominant .NET Verify
        layout. So `.verified.json`, the commonest approval baseline there, was
        silent: re-recording it makes an implementation pass with no test file
        edited at all."""
        for path in ("src/Payments.Tests/CaptureTests.Capture.verified.json",
                     "src/Payments.Tests/CaptureTests.Capture.verified.txt",
                     "approvals/Capture.approved.json"):
            self.assert_fires(run_guard(post("Edit", path)),
                              "PostToolUse", "changed spec")

    def test_bash_tool_ignored(self):
        # A path that matches nothing cannot show that the *tool* filter works:
        # this passed with the filter deleted. Use a path that would fire.
        self.assert_silent(run_guard(post("Bash", "contracts/openapi.yaml")))

    def test_missing_file_path_silent(self):
        self.assert_silent(run_guard({"hook_event_name": "PostToolUse",
                                      "tool_name": "Edit", "tool_input": {}}))
        # An empty string matches nothing, so the absent-path branch could be
        # deleted and this stayed green. A whitespace path is the real shape.
        self.assert_silent(run_guard({"hook_event_name": "PostToolUse",
                                      "tool_name": "Edit",
                                      "tool_input": {"file_path": "   "}}))

    def test_malformed_stdin_silent_exit_zero(self):
        self.assert_silent(run_guard("not json"))

    def test_invalid_regex_override_is_bounded_configuration_error(self):
        r = run_guard(post("Edit", "tests/FooTests.cs"),
                      {"CTDD_TEST_PATTERNS": "["})
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertIn("invalid pattern configuration", r.stderr)
        self.assertIn("CTDD_TEST_PATTERNS", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

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


class AdrMarkerHookTests(unittest.TestCase):
    """This hook is the only component that fires when no skill triggered, so it
    is the only place an ADR reminder reaches an edit made outside the change
    workflow — which was the whole reason for putting the marker in the code."""

    def _file(self, body, name="Handler.cs"):
        d = tempfile.mkdtemp()
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    def test_editing_a_marked_file_reminds_about_the_decision(self):
        path = self._file("// ADR-0017: domain independence\nclass H {}\n")
        out = run_guard(post("Edit", path)).stdout
        self.assertIn("ADR-0017", out)
        self.assertIn("amend or supersede", out)

    def test_an_unmarked_file_stays_silent(self):
        path = self._file("class H {}\n")
        out = run_guard(post("Edit", path)).stdout
        self.assertNotIn("ADR-", out)

    def test_output_is_one_json_object_even_with_two_notes(self):
        """Two emits put two JSON objects on stdout; the harness reads the first
        and silently drops the second."""
        path = self._file("// ADR-0017\nclass H {}\n", name="HandlerTests.cs")
        out = run_guard(post("Edit", path)).stdout
        json.loads(out)  # raises on trailing data
        self.assertIn("ADR-0017", out)

    def test_an_unreadable_file_never_breaks_the_session(self):
        r = run_guard(post("Edit", "/nonexistent/x.cs"))
        out = r.stdout + r.stderr
        self.assertNotIn("Traceback", out)



SETTING_VARS = ("CTDD_TEST_PATTERNS", "CTDD_CONTRACT_PATTERNS", "CTDD_LAYERS",
                "CTDD_HARNESSES", "CTDD_ADR_DIR", "CTDD_PLAN_DIR")


def settings_root(text, encoding="utf-8"):
    """A throwaway project root holding `text` as its settings file: a string
    in `encoding`, or bytes as they are."""
    root = tempfile.mkdtemp()
    with open(os.path.join(root, ".ctdd.json"), "wb") as fh:
        fh.write(text if isinstance(text, bytes) else text.encode(encoding))
    return root


class SettingsFileTests(unittest.TestCase):
    """`.ctdd.json`, as the hook reads it and as the scripts are told about it.

    Three ways of writing the file slightly wrong switched checks off with
    exit 0: lists as JSON arrays, where only a string was read; a misspelt
    key; and a comma after the last entry, which dropped the whole file. The
    hook still reads what it can and says nothing. The scripts ask
    `settings_problems`: they stop on a file or a known key they cannot read,
    and name a key they do not know.
    """

    def setUp(self):
        spec = importlib.util.spec_from_file_location("guard_for_settings", GUARD)
        self.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.guard)
        saved = {k: os.environ.pop(k) for k in SETTING_VARS if k in os.environ}
        self.addCleanup(os.environ.update, saved)

    def problems(self, text, **how):
        return self.guard.settings_problems(settings_root(text, **how))

    def stops(self, text, **how):
        """The one thing that stops the scripts on this file."""
        stop, notes = self.problems(text, **how)
        self.assertEqual(1, len(stop), stop)
        self.assertEqual([], notes)
        return stop[0]

    # ------------------------------------------------------------- arrays
    def test_a_json_array_is_the_list_its_strings_make(self):
        as_array = settings_root('{"layers": ["Domain", "Application"], '
                                 '"harnesses": ["UnitTests", "IntegrationTests"]}')
        as_string = settings_root('{"layers": "Domain;Application", '
                                  '"harnesses": "UnitTests;IntegrationTests"}')
        for var, key, want in (("CTDD_LAYERS", "layers", "Domain;Application"),
                               ("CTDD_HARNESSES", "harnesses", "UnitTests;IntegrationTests")):
            self.assertEqual(want, self.guard.setting(var, key, as_array))
            self.assertEqual(want, self.guard.setting(var, key, as_string))
        self.assertEqual(([], []), self.guard.settings_problems(as_array))

    def test_an_array_of_adr_folders_joins_as_the_environment_variable_does(self):
        root = settings_root('{"adrDir": ["adr", "docs/adr"]}')
        self.assertEqual("adr" + os.pathsep + "docs/adr",
                         self.guard.setting("CTDD_ADR_DIR", "adrDir", root))

    def test_the_hook_classifies_by_patterns_written_as_an_array(self):
        """An override replaces the defaults, in either form."""
        root = settings_root('{"testPatterns": ["(^|/)quality/", "\\\\.robot$"]}')
        env = {"CLAUDE_PROJECT_DIR": root}
        fired = run_guard(post("Edit", "quality/order_rules.py"), env)
        self.assertIn("changed spec", fired.stdout)
        robot = run_guard(post("Edit", "suites/orders.robot"), env)
        self.assertIn("changed spec", robot.stdout)
        default = run_guard(post("Edit", "src/Payments.Tests/CaptureTests.cs"), env)
        self.assertEqual("", default.stdout.strip())

    def test_the_environment_still_wins_over_the_file(self):
        root = settings_root('{"layers": ["Domain", "Application"]}')
        os.environ["CTDD_LAYERS"] = "Core;Edge"
        self.addCleanup(os.environ.pop, "CTDD_LAYERS", None)
        self.assertEqual("Core;Edge", self.guard.setting("CTDD_LAYERS", "layers", root))

    def test_an_entry_holding_the_separator_would_be_read_as_two(self):
        self.assertIn("entry 2 of `testPatterns` contains `;`",
                      self.stops('{"testPatterns": ["(^|/)quality/", "a;b"]}'))

    # ----------------------------------------------- a file that is not read
    def test_a_comma_after_the_last_entry_stops_and_says_where(self):
        text = '{' + chr(10) + '  "layers": "Domain;Api",' + chr(10) + '}'
        root = settings_root(text)
        stop, notes = self.guard.settings_problems(root)
        self.assertEqual([], notes)
        self.assertEqual(1, len(stop), stop)
        # Which line and column depends on the interpreter: one points at the
        # brace that came too soon, a later one at the comma before it.
        self.assertRegex(stop[0], r"^`\.ctdd\.json` is not valid JSON, at line [23] "
                                  r"column \d+: \w")
        # Nothing in it is in force, which is why the scripts stop.
        self.assertEqual("", self.guard.setting("CTDD_LAYERS", "layers", root))

    def test_a_utf16_file_with_a_mistake_reports_the_mistake_not_the_encoding(self):
        self.assertIn("not valid JSON",
                      self.stops('{"layers": "Domain;Api",}', encoding="utf-16"))

    def test_a_utf16_file_is_read(self):
        root = settings_root('{"layers": "Domain;Api"}', encoding="utf-16")
        self.assertEqual("Domain;Api", self.guard.setting("CTDD_LAYERS", "layers", root))
        self.assertEqual(([], []), self.guard.settings_problems(root))

    def test_an_empty_file_and_json_that_is_not_an_object_stop(self):
        self.assertIn("is empty", self.stops("  " + chr(10)))
        for text in ('["layers"]', '"layers"', "3"):
            self.assertIn("not an object", self.stops(text), text)

    def test_bytes_that_are_not_text_stop_and_say_so(self):
        self.assertIn("is not text this plugin can decode",
                      self.stops(bytes([0xFF, 0xFE, 0xFF])))

    def test_something_there_that_cannot_be_opened_stops(self):
        root = tempfile.mkdtemp()
        os.mkdir(os.path.join(root, ".ctdd.json"))
        stop, _notes = self.guard.settings_problems(root)
        self.assertEqual(1, len(stop), stop)
        self.assertIn("`.ctdd.json` could not be opened", stop[0])

    def test_no_file_is_no_problem(self):
        self.assertEqual(([], []), self.guard.settings_problems(tempfile.mkdtemp()))

    # ------------------------------------------------ a key that is not read
    def test_a_known_key_holding_the_wrong_kind_of_value_stops(self):
        for text, said in (
                ('{"layers": 3}', "`layers` is a number; it takes a string with `;` "
                                  "between entries, or a JSON array of strings"),
                ('{"harnesses": {"unit": 1}}', "`harnesses` is an object"),
                ('{"testPatterns": true}', "`testPatterns` is true or false"),
                ('{"planDir": ["docs/plans"]}', "`planDir` is an array; it takes one string"),
                ('{"layers": ["Domain", 2]}', "entry 2 of `layers` is a number"),
                ('{"layers": ["Domain", null]}', "entry 2 of `layers` is null")):
            stop, notes = self.problems(text)
            self.assertEqual(1, len(stop), text)
            self.assertIn(said, stop[0])
            self.assertEqual([], notes)

    def test_every_unreadable_key_is_named_not_only_the_first(self):
        stop, _notes = self.problems('{"layers": 3, "harnesses": false}')
        self.assertEqual(2, len(stop), stop)

    def test_null_and_an_empty_value_are_a_key_switched_off(self):
        root = settings_root('{"harnesses": null, "layers": "", "testPatterns": []}')
        self.assertEqual(([], []), self.guard.settings_problems(root))
        for var, key in (("CTDD_HARNESSES", "harnesses"), ("CTDD_LAYERS", "layers"),
                         ("CTDD_TEST_PATTERNS", "testPatterns")):
            self.assertEqual("", self.guard.setting(var, key, root))

    def test_a_misspelt_key_is_named_with_the_key_it_resembles(self):
        stop, notes = self.problems('{"harness": "UnitTests;IntegrationTests", '
                                    '"LAYERS": "Domain;Api"}')
        self.assertEqual([], stop)
        self.assertEqual(
            ["`.ctdd.json` has a key this plugin does not read: `harness`. "
             "Did you mean `harnesses`? It is ignored.",
             "`.ctdd.json` has a key this plugin does not read: `LAYERS`. "
             "Did you mean `layers`? It is ignored."], notes)

    def test_an_unrelated_key_is_named_without_a_guess(self):
        stop, notes = self.problems('{"owner": "platform", "layers": "Domain;Api"}')
        self.assertEqual([], stop)
        self.assertEqual(["`.ctdd.json` has a key this plugin does not read: `owner`. "
                          "It is ignored."], notes)

    def test_every_setting_a_script_reads_is_a_known_key_and_the_reverse(self):
        """A key missing from the table would be reported as ignored while a
        script reads it, and a key nothing reads would never be reported."""
        here = Path(__file__).resolve().parent
        sources = [here / "spec-edit-guard.py"] + sorted(
            (here.parent / "scripts").glob("[!t]*.py"))
        read = set()
        for source in sources:
            read |= set(re.findall(r'"CTDD_[A-Z_]+"\s*[,:]\s*"([A-Za-z]+)"',
                                   source.read_text(encoding="utf-8")))
        self.assertEqual(set(self.guard.SETTINGS), read)

    # --------------------------------------------------------------- the hook
    def test_the_hook_reads_what_it_can_and_says_nothing(self):
        """It runs on every edit, so a typo in the settings must not break
        editing: it falls back to its defaults and writes nothing to stderr."""
        for text in ('{"testPatterns": "(^|/)quality/",}', '{"testPatterns": 3}',
                     '{"harness": "UnitTests"}'):
            r = run_guard(post("Edit", "src/Payments.Tests/CaptureTests.cs"),
                          {"CLAUDE_PROJECT_DIR": settings_root(text)})
            self.assertEqual(0, r.returncode, text)
            self.assertEqual("", r.stderr.strip(), text)
            self.assertIn("changed spec", r.stdout, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
