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

    def test_empty_diff_refuses_a_verdict_unless_allowed(self):
        """CHANGED REQUIREMENT (was: empty diff is clean, exit 0).

        Empty stdin from a failed `git diff` is indistinguishable from a
        genuinely empty diff, and the skill's own pipeline had no error check —
        so a broken baseline produced 'no surface touched', exit 0, with a
        modified test sitting in the tree. A caller that really means empty now
        says so with --allow-empty.
        """
        r = run("")
        self.assertEqual(r.returncode, 2)
        self.assertIn("empty input", r.stdout)
        r2 = subprocess.run([sys.executable, SCRIPT, "-", "--allow-empty"],
                            input="", capture_output=True, text=True, timeout=15)
        self.assertEqual(r2.returncode, 0)

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
        # "somewhere" is not "before it is needed". The load instruction must come
        # before the inline section it backs, because that section is the part that
        # gets truncated: an agent that reaches the skeleton without having been
        # told to fetch the authoritative version works from the stub alone.
        for ref, inline_section in (("plan-format.md", "## The implementation plan"),
                                    ("adr-rules.md", "## ADR rules")):
            self.assertLess(
                self.skill.index(ref), self.skill.index(inline_section),
                f"the instruction to read {ref} must precede the inline section it "
                f"replaces, not follow it")

    def test_plan_skeleton_does_not_offer_a_trivial_risk_level(self):
        """A trivial change produces no plan, so `trivial` inside a plan's risk
        line is a contradiction the authoritative format already excludes."""
        m = re.search(r"\*\*Risk level\*\*[^\n]*", self.skill)
        self.assertIsNotNone(m)
        self.assertNotIn("trivial /", m.group(0),
                         "the skeleton must not offer a risk level the format forbids")

    # Claude Code re-attaches only the first 5,000 *model tokens* of a skill after
    # auto-compaction. No authoritative tokenizer is available here, so this uses a
    # deliberately pessimistic character proxy: 3 chars/token rather than the ~4
    # typical of English prose, because markdown with backticks, paths and code
    # tokenizes worse than prose. The property being asserted is therefore MARGIN —
    # these rules sit comfortably inside the surviving window — not a simulation of
    # the real boundary. Keep required rules well ahead of it, never near it.
    COMPACTION_PROXY_CHARS = 5000 * 3

    def _surviving_head(self):
        return re.sub(r"^---\n.*?\n---\n", "", self.skill,
                      flags=re.S)[:self.COMPACTION_PROXY_CHARS]

    def test_load_bearing_rules_survive_conservative_compaction_proxy(self):
        """Presence in the file is not the property that matters; presence in the
        re-attached head is. A rule past the boundary is gone for the rest of a
        long session, which is exactly when the discipline matters most."""
        head = self._surviving_head()
        must_survive = {
            "no status claim without a run (#8, #12, #26)": "status claim",
            "changed test is a changed requirement (amendments)": "### Amendments",
            "artifacts disagreeing is a stop condition": "### When artifacts disagree",
            "a bug fix is not the trivial lane": "### Bug fixes",
            "preservation claims need a named detector (#4)": "preserve",
            "distributed-systems escalation (#6)": "distributed-systems",
            "plan written before entering plan mode (#25)": "before entering plan mode",
            "presentation copied, not composed (#28)": "copy it in verbatim",
            "working tree can move mid-session (#32)": "working tree moves under you",
            # the three with the worst drift history in the whole log — guarded
            # last, which is exactly backwards
            "red state needs a captured run and a verdict (#12, #26)":
                "No red-state claim without",
            "pin evidence is green-then-still-green (#21)":
                "A pin's evidence runs the other way",
            # the clause that reconciles "observe it fail" with "pins run green";
            # #19 was a shipped contradiction the agent resolved by judgment
            "the pin exemption turns on what the test asserts (#19)":
                "turns on what the test *asserts*, not when it was written",
            "a required hold-out must actually run (#30, 0% execution)":
                "not finished until it has run",
        }
        for label, probe in must_survive.items():
            self.assertIn(probe, head,
                          f"'{label}' falls outside the surviving head — "
                          f"move it ahead of the sequential steps")

    def test_reference_loaders_survive_the_same_boundary(self):
        """Content moved to a reference is only safe if the instruction to READ it
        survives. A loader past the boundary leaves the agent with 'assemble the
        plan (format below)' and neither the format nor the instruction to fetch
        it — the fallback silently stops existing."""
        head = self._surviving_head()
        for name in sorted(f.name for f in (self.base / "references").glob("*.md")):
            if name == "adr-template.md":
                continue  # fetched by adr-rules.md, which is itself loaded early
            self.assertIn(name, head,
                          f"the instruction to read references/{name} falls outside "
                          f"the surviving head, so the fallback it backs would vanish")


class QuotedPathTests(unittest.TestCase):
    """git quotes non-ASCII paths by default, and the leading quote defeated every
    path pattern — so an edited test in any Slovenian, German, French or Japanese
    codebase classified as untouched surface and passed CI as trivial."""

    def test_git_quoted_non_ascii_test_path_is_still_test_surface(self):
        r = run('M\t"tests/Ra\\304\\215unTests.cs"\n')
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("SPEC SURFACE TOUCHED", r.stdout)

    def test_git_quoted_non_ascii_contract_path_is_contract_surface(self):
        r = run('M\t"contracts/pla\\304\\215ilo.yaml"\n')
        self.assertEqual(r.returncode, 1, r.stdout)

    @staticmethod
    def _skill_dir():
        return Path(__file__).resolve().parents[1] / "skills"

    def test_plan_placeholder_is_consistent(self):
        """`<n>` reads as a number and `<name>` as a slug; v0.9.4 recorded fixing
        this split once already, and a bulk path edit reintroduced it."""
        text = (self._skill_dir() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("docs/plans/<n>", text)

    def test_skill_descriptions_keep_headroom_below_the_cap(self):
        """Descriptions truncate at 1,536 characters and the routing exclusions
        sit at the tail, so the part that prevents overlap with the other skills
        is the part that disappears first."""
        import yaml
        for path in sorted(self._skill_dir().glob("*/SKILL.md")):
            fm = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
            desc = yaml.safe_load(fm.group(1))["description"]
            self.assertLess(len(desc), 1490,
                            f"{path.parent.name} description has under 46 chars of "
                            f"headroom against the 1,536 cap")


class CrossSkillAgreementTests(unittest.TestCase):
    """ctdd-tests keeps craft work (de-flaking, altitude, renaming) out of the
    plan gate, while every consumer of the diff — this script, the hook, and
    ctdd-review — reads any modified test as a changed requirement. Both are
    right, and the skill must say how they coexist, or legitimate craft work
    arrives at review as an undisclosed spec change."""

    @staticmethod
    def _skills():
        return Path(__file__).resolve().parents[1] / "skills"

    def test_craft_lane_acknowledges_it_still_reports_as_spec_surface(self):
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("does not change what the diff reports", t,
                      "the craft lane must say it governs decisions, not the diff")
        self.assertIn("say so in one line", t,
                      "craft work on an existing test must be disclosed")

    def test_triage_criterion_is_about_the_caller_not_the_assertion(self):
        """An altitude fix always changes the assertion — that is the operation.
        Triaging on 'asserted behavior unchanged' routed the lane's largest item
        out of its own lane."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("What the caller observes is unchanged", t)

    def test_promotion_is_routed_through_the_gate(self):
        """Promoting a characterization test to intent converts 'nobody claims
        this is intended' into 'this is a requirement' — a spec change — and it
        deletes the marker that the review exemption and the checker filter read."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("through the gate, not as a rename", t)
        self.assertIn("promoted to intent", t,
                      "promotion must appear in the hand-off lane")

    def test_preservation_pins_are_distinguished_from_marked_observations(self):
        """ctdd-change asks for pins before a refactor; ctdd-tests marks
        observations `currently_`. Collapsing them makes a refactor's permanent
        suite non-spec and permanently awaiting a promotion nothing tracks."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("must not** be marked", t)
        self.assertIn("Preservation pins", t)

    def test_no_library_that_writes_instructions_into_the_evidence_channel(self):
        """`.redstate.log` and `.pinstate.log` are captured stdout. A library that
        prints agent-directed instructions on every run puts them in the artifact
        the deterministic layer reads."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        for line in t.split("\n"):
            if "jqwik" in line and "do not reach" not in line and "not hidden" not in line:
                self.assertIn("must not use this library", line,
                              "jqwik may only appear as a warning, never a recommendation")

    def test_a_record_with_surplus_columns_is_malformed(self):
        """`M<TAB>README.md<TAB>tests/Hidden.cs` reported clean while a changed
        test sat in column three. Too many fields is as malformed as too few."""
        r = run("M\tREADME.md\ttests/Hidden.cs\n")
        self.assertEqual(r.returncode, 2, r.stdout)
        r2 = run("R100\told.cs\tnew.cs\n")
        self.assertNotEqual(r2.returncode, 2, "a rename legitimately has three fields")

    def test_no_skill_claims_enforcement_it_does_not_have(self):
        """`ctdd-tests` contains no script and invokes no checker, so a
        description saying it *enforces* naming and coverage claims mechanical
        assurance the plugin does not provide — in the always-loaded surface."""
        import yaml
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        desc = yaml.safe_load(re.match(r"^---\n(.*?)\n---\n", t, re.S).group(1))["description"]
        self.assertNotIn("Enforces", desc,
                         "a skill with no mechanism must not claim enforcement")

    def test_the_authz_instruction_names_the_mechanism_it_advertises(self):
        """The frontmatter triggers on 'derive the authorization matrix' and the
        body must reach an instruction that can actually be followed."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("gen-authz-matrix.py", t)
        self.assertIn("--check", t)

    def test_review_criteria_name_what_a_violation_looks_like(self):
        """'Is it mostly asserting on mocks?' and 'will it flake?' let two
        reviewers follow the rule exactly and reach opposite verdicts."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("what determines the verdict", t)
        self.assertIn("Name the uncontrolled input", t)

    def test_both_evidence_artifacts_share_the_stated_plan_lane(self):
        """A preservation pin and a marked observation both run green-before-and-
        after, so both land under the same heading; collapsing or separating them
        left one of the two with no stated place in the plan."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("names the direction the evidence runs", t)
        v = (self._skills() / "ctdd-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("characterization observation", v,
                      "the reviewer must accept either artifact for thin coverage")


if __name__ == "__main__":
    unittest.main(verbosity=1)
