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
import tempfile
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

    def test_missing_authoritative_hook_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            scripts = Path(d) / "scripts"
            scripts.mkdir()
            copied = scripts / "check-spec-surface.py"
            copied.write_text(Path(SCRIPT).read_text(encoding="utf-8"), encoding="utf-8")
            diff = Path(d) / "diff.txt"
            diff.write_text("M\tsrc/PaymentTests.cs\n", encoding="utf-8")
            r = subprocess.run([sys.executable, str(copied), str(diff)],
                               capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 2)
        self.assertIn("authoritative patterns", r.stderr)
        self.assertNotIn("Verdict:", r.stdout)

    def test_invalid_pattern_override_fails_closed(self):
        r = run("M\tsrc/PaymentTests.cs\n", env_extra={"CTDD_TEST_PATTERNS": "["})
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid regex", r.stderr)
        self.assertNotIn("Verdict:", r.stdout)

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

    ROUTES = ["For a bug fix, require a short complete plan",
              "Route a changed existing assertion as an amendment",
              "Stop on incompatible claims about the same observable constraint",
              "For a standalone ADR request"]

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
        """Both path styles must be checked. Normalizing every reference load to a
        relative `references/x.md` moved all six of them off the ${CLAUDE_PLUGIN_ROOT}
        pattern this test matched, taking its coverage from five references to zero
        — and `worked-change.md` then shipped untracked, so a fresh clone had a step
        ordering the agent to read a file nobody else had. Both guards passed."""
        root = self.base.parents[1]
        for rel in set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", self.skill)):
            self.assertTrue((root / rel).exists(),
                            f"skill points at {rel}, which is not bundled")
        for rel in set(re.findall(r"(?<!/)\breferences/([A-Za-z0-9_.-]+\.md)", self.skill)):
            self.assertTrue((self.base / "references" / rel).exists(),
                            f"skill points at references/{rel}, which is not bundled")

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
        "canonical plan is written outside plan mode":
            "Leave plan mode before writing or updating the canonical plan.",
        "the repository file is authoritative":
            "Treat every harness plan file as non-authoritative.",
        "presentation copies canonical text":
            "Copy the canonical decision summary verbatim",
        "approval stops execution":
            "Stop for explicit approval.",
        "approval authorizes the plan file":
            "Treat approval as authorization to execute the plan file.",
        "full plan reaches stdout outside plan mode":
            "Print the complete plan verbatim followed by its path",
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
        """Every reference is named, and each executable reference is loaded before use."""
        refs = {f.name for f in (self.base / "references").glob("*.md")}
        for name in sorted(refs):
            self.assertIn(name, self.skill,
                          f"references/{name} exists but SKILL.md never names it")
        ordered = (
            ("plan-format.md", "Write the Implementation plan to its exact path."),
            ("adr-rules.md", "draft the structural ADR inside the future plan"),
            ("colocated-notes.md", "write one Colocated note"),
        )
        for ref, use in ordered:
            self.assertLess(self.skill.index(ref), self.skill.index(use),
                            f"load {ref} before the instruction it governs")

    def test_plan_format_does_not_offer_a_trivial_risk_level(self):
        """A trivial change produces no plan, so the reference must exclude it."""
        text = (self.base / "references" / "plan-format.md").read_text(encoding="utf-8")
        self.assertIn("Risk: <normal | high-risk>", text)
        self.assertNotIn("Risk: <trivial", text)

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
            "no result claim without current-turn run": "Do not claim a test, build, gate, checker",
            "tests are delegated before edits": "Invoke `ctdd-tests` before creating",
            "artifact conflicts stop": "Stop on incompatible claims",
            "bug fix remains non-trivial": "For a bug fix, require a short complete plan",
            "preservation needs named tests": "Name the tests that detect every behavior",
            "distributed systems escalate": "Require property tests, boundary contract tests",
            "canonical plan leaves plan mode": "Leave plan mode before writing",
            "presentation is verbatim": "Copy the canonical decision summary verbatim",
            "working tree is rechecked": "Re-check the working tree against step 0",
            "red-state verdict is required": "Verify red state with",
            "pin verdict is required": "Verify pins with",
            "hold-out blocks review": "Stop for the required sealed hold-out result",
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
    MINIMUM_MARGIN_CHARS = 1500
    # Raised once, deliberately, for plan tiers (v0.24.0). This ratchet measures
    # agent context — loaded once, cached, cheap. Tiering spends ~700 characters
    # of it to take roughly 2,000 words off every small plan a human reads at the
    # gate, on every change; the 2026-07-27 Flik plan ran to 3,166 words and ~14
    # minutes. The proxy cannot see what is being bought, and refusing a good
    # trade because a proxy says no is the wrong use of a guard. Two blocks of
    # rehearsed checker output were cut from worked-change.md first, so the raise
    # is 500 rather than 1,200. Lower it again if worked-change.md is retired.
    MAX_PLAN_GATED_METHODOLOGY_CHARS = 38000
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

    def test_every_skill_body_fits_the_compaction_proxy(self):
        """The survival guard's probe list is per-skill and binds to ctdd-change
        alone, so ctdd-tests overflowed the same proxy by 1,085 characters and
        shipped that way through a full review round with three load-bearing
        rules already outside the window. Nothing measured it, because nothing
        was looking. Probes stay per-skill; size is checkable for all of them."""
        # A boundary test is not a margin test: `< 15000` passes at 14,999, which is
        # how ctdd-change reached +109 and then went red on an ordinary correctness
        # fix (anchoring four script paths to ${CLAUDE_PLUGIN_ROOT}). Reserve the
        # space explicitly so the guard fails while there is still room to think.
        limit = ChangeSkillStructureTests.COMPACTION_PROXY_CHARS - self.MINIMUM_MARGIN_CHARS
        for path in sorted(self._skills().glob("*/SKILL.md")):
            body = re.sub(r"^---\n.*?\n---\n", "",
                          path.read_text(encoding="utf-8"), flags=re.S)
            self.assertLessEqual(
                len(body), limit,
                f"{path.parent.name}/SKILL.md body is {len(body)} chars; keep at "
                f"least {self.MINIMUM_MARGIN_CHARS} chars of compaction margin "
                f"below the {ChangeSkillStructureTests.COMPACTION_PROXY_CHARS}-char "
                f"proxy, so a correctness fix never has to fight the budget")

    def test_plan_gated_methodology_has_a_route_cost_ratchet(self):
        """The body-size guard stayed green while mandatory references doubled the
        real plan-gated instruction load from 19,179 to 40,800 characters. Count
        the route the skill actually orders, not just the always-loaded body."""
        root = self._skills() / "ctdd-change"
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        body = re.sub(r"^---\n.*?\n---\n", "", skill, flags=re.S)
        unconditional = {
            "worked-change.md", "plan-format.md", "execution.md",
        }
        total = len(body) + sum(
            len((root / "references" / name).read_text(encoding="utf-8"))
            for name in unconditional
        )
        self.assertLessEqual(
            total, self.MAX_PLAN_GATED_METHODOLOGY_CHARS,
            f"plan-gated methodology is {total} chars; the ratchet is "
            f"{self.MAX_PLAN_GATED_METHODOLOGY_CHARS}. Displace or condition "
            "existing instruction before adding more")

    def test_route_budget_names_every_unconditional_reference_load(self):
        """A route ceiling is accounting theatre if a new mandatory reference can
        be added without entering the sum. ADR and colocated-note references are
        excluded only because their load lines carry observable conditions."""
        skill = (self._skills() / "ctdd-change" / "SKILL.md").read_text(
            encoding="utf-8")
        actual = set()
        for line in skill.splitlines():
            match = re.search(r"\bread `references/([^`]+)`", line, re.I)
            if not match:
                continue
            prefix = line[:match.start()].lower()
            conditional = any(marker in prefix for marker in (
                "when ", "if ", "stop on", "for a standalone"))
            if not conditional:
                actual.add(match.group(1))
        self.assertEqual(
            actual, {"worked-change.md", "plan-format.md", "execution.md"},
            f"update the plan-gated route budget when unconditional loads change: "
            f"{sorted(actual)}")

    def test_review_packet_reloads_execution_and_verifies_both_pin_runs(self):
        """The final packet named execution.md without re-reading it after a long
        session, then mechanically checked only the pre-change pin log even though
        ctdd-review requires both the before and after runs."""
        root = self._skills() / "ctdd-change"
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        step9 = skill.split("\n9. **Produce the review packet.**", 1)[1].split(
            "\n10. ", 1)[0]
        self.assertIn("Read `references/execution.md` now", step9)
        execution = (root / "references" / "execution.md").read_text(
            encoding="utf-8")
        self.assertIn("<pin-log>", execution)
        self.assertIn("<pin-after-log>", execution)
        self.assertIn("Pin state before:", execution)
        self.assertIn("Pin state after:", execution)
        worked = (root / "references" / "worked-change.md").read_text(
            encoding="utf-8")
        self.assertIn("Pin state before:", worked)
        self.assertIn("Pin state after:", worked)

    def test_holdout_packet_preserves_not_run_and_named_runner(self):
        """A CI outage was previously converted into a human decline, and the
        packet's exact schema then omitted the NOT RUN state the workflow allowed."""
        root = self._skills() / "ctdd-change"
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("result from the named runner", skill)
        execution = (root / "references" / "execution.md").read_text(
            encoding="utf-8")
        packet = execution.split("## Review packet shape", 1)[1]
        self.assertIn("NOT RUN — <reason>", packet)

    def test_every_plan_edit_refreshes_the_checker_result(self):
        """A resolved BLOCKING answer edited the canonical plan after check-plan
        passed, but the worked example said the checker need not run again. The
        approval then authorized content the recorded checker never inspected."""
        root = self._skills() / "ctdd-change" / "references"
        fmt = (root / "plan-format.md").read_text(encoding="utf-8")
        self.assertIn("Re-run the checker after every plan edit", fmt)
        worked = (root / "worked-change.md").read_text(encoding="utf-8")
        self.assertIn("Every plan edit", worked)
        self.assertNotIn("checker did not have to run again", worked)

    def test_every_bundled_reference_is_tracked_by_git(self):
        """Existence on disk is not shipping. `worked-change.md` existed locally,
        was never added, and every guard passed — the skill ordered a read of a
        file no clone had. Writing this guard reproduced the bug immediately:
        `execution.md` was untracked too. Skipped outside a git checkout so the
        suite still runs from an export."""
        import subprocess
        root = self._skills().parent
        probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-dir"],
                               capture_output=True, text=True)
        if probe.returncode != 0:
            self.skipTest("not a git checkout")
        for ref in sorted(self._skills().glob("*/references/*.md")):
            rel = ref.relative_to(root).as_posix()
            r = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", rel],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0,
                             f"{rel} is bundled and loaded but not tracked; it will "
                             f"be absent for everyone but its author")

    def test_every_script_reference_is_anchored_to_the_plugin_root(self):
        """The scripts live in Claude Code's plugin directory, not the repository
        under review, so a bare `check-spec-surface.py` runs nothing — or worse,
        whatever happens to sit at that name in the target project. The changelog
        already records this exact failure for the CI recipe; the procedural
        rewrites then reintroduced it in ctdd-review and ctdd-tests by stripping
        the anchor along with everything else they compressed."""
        for path in sorted(self._skills().glob("*/SKILL.md")):
            text = path.read_text(encoding="utf-8")
            for i, line in enumerate(text.split("\n"), 1):
                for m in re.finditer(r"[\w.-]*\.py\b", line):
                    self.assertTrue(
                        line[:m.start()].endswith("${CLAUDE_PLUGIN_ROOT}/scripts/"),
                        f"{path.parent.name}/SKILL.md:{i} names {m.group(0)} without "
                        f"the ${{CLAUDE_PLUGIN_ROOT}}/scripts/ anchor")

    def test_review_discriminators_are_in_the_body_not_the_unloaded_rationale(self):
        """ctdd-review marks `references/rationale.md` do-not-load, and the v0.23.0
        rewrite left four operative discriminators there: proportionality, ADR
        decision-vs-description, test-and-code agreeing on the wrong thing, and
        silent fixes erasing the record. The checklist survived; the judgment that
        makes each item decidable did not. `additive is compatible` was in neither
        file. A rule shelved behind a do-not-load pointer is deleted with a filing
        cabinet attached."""
        t = (self._skills() / "ctdd-review" / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ("three-line fix gets a three-line review",
                       "records the decision **and its tradeoffs**",
                       "agree on the wrong thing",
                       "Additive changes are compatible",
                       "silent fix erases the review record"):
            self.assertIn(phrase, t,
                          f"ctdd-review lost the discriminator: {phrase!r}")

    def test_review_verification_step_is_marked_re_enterable(self):
        """Step 5 runs verification; steps 6 and 7 produce the candidates. Stated
        as a strict precondition chain, `reproduced` — the top evidence class —
        depended on a run that preceded the thing it verifies."""
        t = (self._skills() / "ctdd-review" / "SKILL.md").read_text(encoding="utf-8")
        step5 = t.split("\n5. **Run relevant verification.", 1)[1].split("\n6. ", 1)[0]
        self.assertIn("Re-enterable", step5)

    def test_every_shown_invocation_carries_its_required_arguments(self):
        """A compression pass anchored the paths and dropped the arguments, so
        step 9 displayed `check-plan.py` and `check-redstate.py` bare. Run exactly
        as shown they exit 1 and 2 — a command in a procedure is an instruction to
        run it, and one that cannot run teaches the agent the checker is optional."""
        for path in sorted(self._skills().glob("*/SKILL.md")):
            for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
                if "check-plan.py" in line:
                    self.assertRegex(
                        line, r"<[a-z-]*plan[a-z-]*>|docs/plans/",
                        f"{path.parent.name}/SKILL.md:{i} shows check-plan.py with no "
                        f"plan argument; as displayed it exits 1")
                if "check-redstate.py" in line:
                    self.assertTrue(
                        "--tests-from" in line or "--test " in line,
                        f"{path.parent.name}/SKILL.md:{i} shows check-redstate.py with "
                        f"no names; as displayed it exits 2")

    def test_expect_pass_is_never_shown_without_the_names_it_needs(self):
        """`--expect-pass` with no --test/--tests-from exits 2: 'no test names
        given ... this is a usage error, not a pass.' ctdd-review gave the
        new-behavior lane the full command and the pin lane only the flag — the
        pin lane getting the less complete instruction, which is finding #39's
        shape."""
        for path in sorted(self._skills().glob("*/SKILL.md")):
            for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
                if "--expect-pass" in line:
                    self.assertTrue(
                        "--tests-from" in line or "--test " in line,
                        f"{path.parent.name}/SKILL.md:{i} shows --expect-pass without "
                        f"the names it requires; that invocation is a usage error")

    def test_the_reviewer_is_never_told_to_author_a_test(self):
        """ctdd-review forbids editing tests and then required running 'the
        narrowest reproducer'. A reviewer-authored reproducer lands in the same
        spec-surface inventory the review reported at step 1 and trips the
        spec-edit hook: the reviewer contaminates the diff it is judging."""
        t = (self._skills() / "ctdd-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Author no test, fixture, or script", t)
        self.assertNotIn("Run the narrowest reproducer", t)

    def test_step_eight_admits_every_evidence_lane_not_only_red(self):
        """Entry read 'step 7 recorded intended red, or step 3.6 fired'. A
        preservation-only refactor skips 7.10-7.12 so never records intended red,
        and is not trivial because its pins have to be written — it satisfied
        neither door and had no route into implementation."""
        t = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        step8 = t.split("\n8. **Implement and verify.**", 1)[1].split("\n9. ", 1)[0]
        self.assertIn("every applicable evidence lane", step8)
        self.assertNotIn("Enter: step 7 recorded intended red, or step 3.6 fired", t)

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

    def test_the_ordered_workflow_names_the_lanes_that_do_not_write_a_test(self):
        """The v0.21.2 rewrite replaced the old "When writing" / "When reviewing"
        modes with one unconditional `Execute steps 1-8 in order`, while the
        description still triggers on renaming, de-flaking and isolated review.
        Those tasks hit step 3 (derive the case set) and step 4 (assign an
        evidence direction) with nothing to derive and no direction to assign.
        A sequence claim without an entry condition is worse than the modes it
        replaced, because it reads as mandatory."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        wf = t.split("## Ordered test-writing workflow", 1)[1].split("\n1. ", 1)[0]
        self.assertIn("when the task adds a test", wf,
                      "the 8-step sequence must name the lane it applies to")
        self.assertIn("Craft edit to an existing test", wf,
                      "rename/de-flake/altitude repair write a file but derive no case set")
        self.assertIn("Isolated review or gap-finding", wf,
                      "a review that writes nothing must have a stated path")
        self.assertIn("Entered from the review lane above, or from `ctdd-review`",
                      t, "the review section must name its callers")

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
        # The substring above certifies the phrase is present, not that it plays
        # the right role: a compression once rendered it *inside a code span* as
        # `Preservation pins - names the direction the evidence runs`, which reads
        # as a literal heading and is not the one the format mandates. Models copy
        # examples, so a backticked heading variant is an instruction to write it.
        for span in re.findall(r"`([^`\n]*Preservation pins[^`\n]*)`", t):
            self.assertEqual(span, "Preservation pins",
                             "a code span naming the plan heading must carry the "
                             "mandated form alone, not a gloss shaped like a heading")
        v = (self._skills() / "ctdd-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("characterization observation", v,
                      "the reviewer must accept either artifact for thin coverage")

    def test_test_conventions_are_repository_owned_and_verified(self):
        """Framework, assertions, naming, fixtures, paths, and runner are project
        facts. The skill discovers and verifies them instead of publishing a
        plugin-wide default that can override the repository."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`CLAUDE.md`", t)
        self.assertIn("`.claude/rules/`", t)
        self.assertIn("target test project", t)
        self.assertIn("adjacent tests", t)
        self.assertIn("Do not introduce or default to a test framework", t)
        self.assertIn("stop and report any conflict", t)

    def test_worked_case_derivation_does_not_anchor_one_framework(self):
        """A concrete framework specimen dominates a generic instruction to
        adapt it. Keep the case derivation concrete and take syntax only from
        the target repository."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        worked = t.split("## Worked case derivation", 1)[1].split("## Test review", 1)[0]
        for framework_token in ("xUnit", "[Fact]", "[Theory]", "Assert.Equal"):
            self.assertNotIn(framework_token, worked)
        self.assertIn("Use an adjacent behavior-level test", worked)
        self.assertIn("Do not copy framework syntax", worked)
        self.assertIn("Representative positive", worked)
        self.assertIn("Upper boundary", worked)
        self.assertIn("Below lower boundary", worked)
        self.assertIn("Forbidden side effect", worked)

    def test_blocked_test_design_reports_pressure_without_prescribing_a_production_fix(self):
        """A test-craft skill can expose design pressure, but it must not invent
        the contract or prescribe a production redesign such as adding DI."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        blocked = t.split("## When blocked", 1)[1].split("## Worked case derivation", 1)[0]
        self.assertIn("Expected behavior or public API is unclear", blocked)
        self.assertIn("nearly every dependency needs a mock", blocked)
        self.assertIn("setup obscures the rule", blocked)
        self.assertIn("do not invent an API", blocked)
        self.assertIn("do not expose internals", blocked)
        self.assertIn("do not expose internals, substitute call counts, or change production design here", blocked)
        for overreach in ("Write wished-for API", "Use dependency injection", "Delete means delete"):
            self.assertNotIn(overreach, blocked)

    def test_invalid_substitutes_respect_the_assigned_evidence_direction(self):
        """Tests-after and manual checks do not replace witnessed RED for new
        behavior, while green-before is required for pins and observations."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        blocked = t.split("## When blocked", 1)[1].split("## Worked case derivation", 1)[0]
        for substitute in (
            "Manual testing", "coverage", "code inspection",
            "a test written after implementation", "time already spent",
            "retained exploration", "executable RED",
        ):
            self.assertIn(substitute, blocked)
        self.assertIn("must fail before implementation", blocked)
        self.assertIn("preservation pins and characterization observations", blocked)
        self.assertIn("must pass before refactor", blocked)


if __name__ == "__main__":
    unittest.main(verbosity=1)
