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
import re
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

class GitModeTests(unittest.TestCase):
    """--git must not be a quieter way to reopen the new-test blind spot."""

    def test_git_mode_reports_an_untracked_test_file(self):
        import subprocess, tempfile, os, sys
        repo = tempfile.mkdtemp()
        run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True)
        run("git", "init", "-q"); run("git", "config", "user.email", "t@t")
        run("git", "config", "user.name", "t")
        Path(repo, "readme.md").write_text("x", encoding="utf-8")
        run("git", "add", "-A"); run("git", "commit", "-qm", "init")
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
        Path(repo, "tests", "test_capture.py").write_text("def test_x(): pass", encoding="utf-8")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "check-spec-surface.py")
        r = subprocess.run([sys.executable, script, "--git"], cwd=repo,
                           capture_output=True, text=True)
        self.assertIn("test_capture.py", r.stdout,
                      "an untracked new test must appear in --git output")


class ChangeSkillStructureTests(unittest.TestCase):
    """A restructure must not move load-bearing routing into a conditional
    reference. This exact defect shipped in v0.14.0: four workflow sections were
    carried into a file loaded only when a colocated note is written, so an
    ordinary bug fix ran without its own lane rule. Nothing caught it."""

    ROUTES = ["### Bug fixes", "### Amendments",
              "### When artifacts disagree", "### Standalone ADR requests"]

    def setUp(self):
        base = Path(__file__).resolve().parents[1] / "skills" / "ctdd-change"
        self.skill = (base / "SKILL.md").read_text(encoding="utf-8")
        self.notes = (base / "references" / "colocated-notes.md").read_text(encoding="utf-8")
        self.base = base

    def test_workflow_routing_stays_in_the_always_loaded_skill(self):
        for heading in self.ROUTES:
            self.assertIn(heading, self.skill,
                          f"{heading} must stay in SKILL.md — it decides which lane runs")

    def test_note_reference_holds_only_note_craft(self):
        for heading in self.ROUTES:
            self.assertNotIn(heading, self.notes,
                             f"{heading} is workflow routing, not colocated-note craft")

    def test_every_referenced_bundled_file_exists(self):
        root = self.base.parents[1]
        for rel in set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", self.skill)):
            self.assertTrue((root / rel).exists(),
                            f"skill points at {rel}, which is not bundled")

    @staticmethod
    def _repo():
        """A throwaway repo with one committed test file and a src/ subdirectory."""
        import subprocess, tempfile, os
        repo = tempfile.mkdtemp()
        run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True)
        run("git", "init", "-q"); run("git", "config", "user.email", "t@t")
        run("git", "config", "user.name", "t")
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
        os.makedirs(os.path.join(repo, "src"), exist_ok=True)
        Path(repo, "tests", "test_capture.py").write_text("x", encoding="utf-8")
        Path(repo, "src", "app.py").write_text("y", encoding="utf-8")
        run("git", "add", "-A"); run("git", "commit", "-qm", "init")
        return repo, run

    def test_git_mode_reports_a_staged_test_change(self):
        """A bare `git diff` compares against the index, so a staged test edit
        reads as no surface at all — success reported for what was never seen."""
        import subprocess, sys, os
        repo, run = self._repo()
        Path(repo, "tests", "test_capture.py").write_text("changed", encoding="utf-8")
        run("git", "add", "tests/test_capture.py")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "check-spec-surface.py")
        r = subprocess.run([sys.executable, script, "--git"], cwd=repo,
                           capture_output=True, text=True)
        self.assertIn("test_capture.py", r.stdout,
                      "a staged test change must be reported as touched surface")
        self.assertEqual(r.returncode, 1, "touched spec surface must exit 1")

    def test_git_mode_finds_an_untracked_test_from_a_nested_directory(self):
        """`git ls-files --others` is relative to cwd, so running from a
        subdirectory would otherwise hide a new test living elsewhere."""
        import subprocess, sys, os
        repo, _ = self._repo()
        Path(repo, "tests", "test_new_behavior.py").write_text("z", encoding="utf-8")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "check-spec-surface.py")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=repo)
        r = subprocess.run([sys.executable, script, "--git"],
                           cwd=os.path.join(repo, "src"),
                           capture_output=True, text=True, env=env)
        self.assertIn("test_new_behavior.py", r.stdout,
                      "a new test in a sibling directory must still be reported")

    def test_mr_pointer_stays_repository_relative(self):
        """Filesystem writes are rooted at the project dir; the CTDD-Plan line in
        the MR is repository metadata read by CI in a different checkout, and
        check-plan.py refuses an absolute pointer from an untrusted description.
        Rooting every path once broke this and CI failed on conformant changes."""
        self.assertIn("CTDD-Plan: docs/plans/", self.skill)
        self.assertNotIn("CTDD-Plan: ${CLAUDE_PROJECT_DIR}", self.skill)

    def test_malformed_input_refuses_to_give_a_verdict(self):
        """Space-separated input is not name-status output. Skipping the line and
        printing 'no surface touched' claims something never established."""
        import subprocess, sys, os, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "check-spec-surface.py")
        r = subprocess.run([sys.executable, script, "-"],
                           input="M tests/payment_tests.py\n",
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, f"must not conclude over discarded input:\n{r.stdout}")
        self.assertNotIn("no test/contract/ADR surface touched", r.stdout)

    # --- guards for the deferred step-6 split -------------------------------
    # Written before the refactor, on purpose. The v0.14.0 restructure silently
    # dropped four workflow sections into a conditional reference and nothing
    # noticed; these make the same mistake fail loudly. Each rule below traces to
    # a specific pilot finding, so losing one is a regression, not a tidy-up.

    GATE_RULES = {
        "plan file written before entering plan mode (#25)":
            "before entering plan mode",
        "the repo file is the authority, not the harness scratch (#25, #28)":
            "never the harness",
        "material change mid-gate goes into the file (#28)":
            "ask to leave plan mode",
        "presentation is copied, not composed (#28)":
            "copy it in verbatim",
        "short and verbatim are compatible (#24, #28)":
            "not in tension",
        "approval means implement from this plan (#7)":
            "go-signal",
        "the gate stops and waits":
            "STOP for review",
        "full plan reaches the terminal as well as the file (#24)":
            "to the terminal as well as the file",
    }

    def test_gate_rules_stay_in_the_always_loaded_skill(self):
        for label, probe in self.GATE_RULES.items():
            self.assertIn(probe, self.skill,
                          f"gate rule lost from SKILL.md: {label}")

    def test_a_plan_mode_reference_holds_presentation_craft_only(self):
        """Inert until the split happens, binding the moment it does."""
        ref = self.base / "references" / "plan-mode.md"
        if not ref.exists():
            self.skipTest("plan-mode.md not split out yet")
        text = ref.read_text(encoding="utf-8")
        for label, probe in self.GATE_RULES.items():
            self.assertNotIn(
                probe, text,
                f"{label} is a gate transition and must stay in the skill, "
                f"not move into a conditionally-loaded reference")

    def test_every_reference_is_loaded_somewhere_before_it_is_needed(self):
        """A reference nobody is told to read is a rule that is not followed."""
        refs = {f.name for f in (self.base / "references").glob("*.md")}
        for name in sorted(refs):
            self.assertIn(name, self.skill,
                          f"references/{name} exists but the skill never tells "
                          f"the agent to read it")

    def test_load_bearing_rules_survive_post_compaction_truncation(self):
        """Claude Code re-attaches only the first 5,000 tokens of a skill after
        auto-compaction. Presence in the file is therefore not enough: a rule
        past that point is gone for the rest of a long session, which is exactly
        when the discipline matters most. Rules that apply *throughout* must sit
        before the step-by-step detail, and anything truncated must be backed by
        a reference the skill loads or a checker that fails without it."""
        head = re.sub(r"^---\n.*?\n---\n", "", self.skill, flags=re.S)[:5000 * 4]
        must_survive = {
            "no status claim without a run (#8, #12, #26)": "status claim",
            "changed test is a changed requirement (amendments)": "### Amendments",
            "artifacts disagreeing is a stop condition": "### When artifacts disagree",
            "a bug fix is not the trivial lane": "### Bug fixes",
            "preservation claims need a named detector (#4)": "preserve",
            "distributed-systems escalation (#6)": "distributed-systems",
            "plan written before entering plan mode (#25)": "before entering plan mode",
            "presentation copied, not composed (#28)": "copy it in verbatim",
            "working tree checked before implementing (#32)": "re-check the tree",
        }
        for label, probe in must_survive.items():
            self.assertIn(probe, head,
                          f"'{label}' falls past the 5,000-token truncation point — "
                          f"move it ahead of the sequential steps")


if __name__ == "__main__":
    unittest.main(verbosity=1)
