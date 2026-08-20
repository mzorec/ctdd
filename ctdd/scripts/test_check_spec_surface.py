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
import re as _re_mod
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "check-spec-surface.py")


def run(text, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    return subprocess.run([sys.executable, SCRIPT, "-"],
                          input=text, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=15, env=env)


def _norm(s):
    """Numbers and f-string interpolations collapse to a placeholder."""
    s = _re_mod.sub(r"\{[^}]*\}", "#", s)
    return _re_mod.sub(r"\d+", "#", s)


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
                            input="", capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        self.assertEqual(r2.returncode, 0)

    def test_help_exits_zero(self):
        r = subprocess.run([sys.executable, SCRIPT, "--help"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
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
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
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
        run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
        run("git", "init", "-q"); run("git", "config", "user.email", "t@t")
        run("git", "config", "user.name", "t")
        Path(repo, "readme.md").write_text("x", encoding="utf-8")
        run("git", "add", "-A"); run("git", "commit", "-qm", "init")
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
        Path(repo, "tests", "test_capture.py").write_text("def test_x(): pass", encoding="utf-8")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "check-spec-surface.py")
        r = subprocess.run([sys.executable, script, "--git"], cwd=repo,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
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
        run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
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
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
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
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertIn("test_new_behavior.py", r.stdout,
                      "a new test in a sibling directory must still be reported")

    def test_mr_pointer_stays_repository_relative(self):
        """Filesystem writes are rooted at the project dir; the CTDD-Plan line in
        the MR is repository metadata read by CI in a different checkout, and
        check-plan.py refuses an absolute pointer from an untrusted description.
        Rooting every path once broke this and CI failed on conformant changes."""
        # The checker honours `planDir` and *rejects* any pointer outside it,
        # while the skill hardcoded `docs/plans/` — so a repository that
        # configured one got an exit-1 CI failure on a correct plan. The
        # pointer must name the resolved directory, not a literal.
        self.assertIn("CTDD-Plan: <plan-dir>/", self.skill)
        self.assertIn("--plan-dir", self.skill)
        self.assertNotIn("CTDD-Plan: ${CLAUDE_PROJECT_DIR}", self.skill)

    def test_malformed_input_refuses_to_give_a_verdict(self):
        """Space-separated input is not name-status output. Skipping the line and
        printing 'no surface touched' claims something never established."""
        import subprocess, sys, os, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "check-spec-surface.py")
        r = subprocess.run([sys.executable, script, "-"],
                           input="M tests/payment_tests.py\n",
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
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
            # 6.1 stopped demanding the whole plan in the terminal: the 2026-07-27
            # plans ran 31,448 and 27,976 chars (~14 and ~12 minutes), so agents
            # compressed, and what survived compression was whatever they chose to
            # volunteer. The hold-out — the one item needing the human to go and do
            # something, and skipped six times running — was the most compressible.
            "Print the Gate presentation outside a plan-mode approval surface",
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
    # tokenizes worse than prose. The property asserted is MARGIN — these rules sit
    # comfortably inside the surviving window — not a simulation of the boundary.
    #
    # Raised to 3.5 in v0.31.0 and restored here. Two things were wrong with that
    # raise. It was made because a guard fired, and the guard that fired was the
    # 500-char reserve — the early warning this file itself labels "NOT
    # PROTECTION" — so the response raised the constant the probes slice on, by
    # 2,500, which rule 9 names as the thing to check first. And its stated
    # justification, "measured 4.00", was `len(body)/(len(body)//4)`: 4.00 for any
    # text at all, a tautology rather than a measurement. External tokenizers put
    # this content at 4.16-4.50, so a raise may well be defensible — but it needs a
    # measurement and a reason that is not the early-warning guard going off.
    COMPACTION_PROXY_CHARS = 5000 * 3

    # Position, not presence. While the body is smaller than the proxy the head
    # slice IS the whole body, so every probe assertion is position-independent
    # and a probe can only fall out of a body that already failed the size guard —
    # structurally unreachable. Measured: the last probe sits at 12,961 of 14,660.
    # This ceiling is the real constraint and it can fail: move a must-survive rule
    # to the end of the body and this fires, where the presence checks do not.
    MAX_PROBE_OFFSET_CHARS = 13_500

    MUST_SURVIVE = {
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

    def _surviving_head(self):
        return re.sub(r"^---\n.*?\n---\n", "", self.skill,
                      flags=re.S)[:self.COMPACTION_PROXY_CHARS]

    def test_every_must_survive_rule_sits_well_inside_the_window(self):
        """Presence in the surviving head is not the property that matters once the
        head is the whole body — then it is vacuous. Assert *offset*: each rule that
        must survive compaction has to sit inside MAX_PROBE_OFFSET_CHARS, so growth
        that pushes one toward the boundary fails here rather than silently."""
        body = re.sub(r"^---\n.*?\n---\n", "", self.skill, flags=re.S)
        worst = []
        for label, probe in self.MUST_SURVIVE.items():
            at = body.find(probe)
            self.assertGreaterEqual(at, 0, f"the rule '{label}' is gone: {probe!r}")
            worst.append((at, label))
        at, label = max(worst)
        self.assertLessEqual(
            at, self.MAX_PROBE_OFFSET_CHARS,
            f"'{label}' sits at {at} chars, past the {self.MAX_PROBE_OFFSET_CHARS} "
            f"ceiling — it is drifting toward the compaction boundary")

    def test_load_bearing_rules_survive_conservative_compaction_proxy(self):
        """Presence in the file is not the property that matters; presence in the
        re-attached head is. A rule past the boundary is gone for the rest of a
        long session, which is exactly when the discipline matters most."""
        head = self._surviving_head()
        must_survive = self.MUST_SURVIVE
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
            if name == "rationale.md":
                continue  # marked do-not-load during a change, by design
            # Assert the *loader sentence*, not the bare filename. Every reference
            # is also named in the Output contract table, so `name in head` stayed
            # true when step 5.1's `Read references/plan-format.md.` was replaced
            # with prose — the guard was green while the fallback it protects had
            # stopped existing. Rule 8's `a path pattern that matched zero
            # references once the paths were normalised`, one level up.
            self.assertRegex(
                head, rf"(?i:read)\s+`references/{re.escape(name)}`",
                f"no `Read references/{name}` loader survives the boundary, so the "
                f"fallback it backs would vanish")


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
    # 1,500 -> 1,000 (v0.24.0). The proxy is 5,000 tokens x 3 chars/token; these
    # bodies measure 4.00, so 15,000 is already about a third more conservative
    # than observed — ctdd-change is ~3,370 tokens against Anthropic's ~5,000
    # guidance. The reserve was a round number I picked, not a measurement, and
    # it was the binding constraint while the actual guidance had 1,600 tokens
    # spare. The alternative was relocating steps 7-10, which converts four
    # guaranteed-present survival probes into conditionally-loaded ones; that
    # stays filed with a trigger rather than forced to fit a number.
    # EARLY WARNING, NOT PROTECTION. The real constraint is now
    # MAX_PROBE_OFFSET_CHARS, which asserts where each must-survive rule sits
    # rather than merely that it is present — the presence form went vacuous the
    # moment the body was smaller than the proxy, because then the head slice is
    # the whole body.
    #
    # The body limit is now its OWN number, not `proxy - margin`. Those were two
    # different properties sharing one dial, which is how v0.31.0 went wrong: the
    # margin fired, and the response moved the constant the survival probes slice
    # on. The probes now assert *offset* against MAX_PROBE_OFFSET_CHARS
    # instead, so the proxy no longer carries that job and can stay put.
    #
    # 14,700 -> 15,500, on request. What it costs and what it does not:
    #   - It does NOT weaken the probes. Every must-survive rule is asserted to sit
    #     within 13,500 chars; the last one is at ~13,000.
    #   - It DOES mean up to 500 characters of body may sit past the 15,000-char
    #     compaction proxy. Content there is lost after a long session — acceptable
    #     only while the probe list covers everything load-bearing, which is the
    #     standing assumption this whole guard rests on.
    #   - Against the external number there is room: at the 4.16-4.50 chars/token
    #     an outside tokenizer measures for this content, 15,500 chars is roughly
    #     3,450-3,730 tokens, or 69-75% of Anthropic's ~5,000-token guidance.
    BODY_LIMIT_CHARS = 15_500

    # Kept as the early warning it always was, now against the proxy rather than
    # as the body limit itself.
    MINIMUM_MARGIN_CHARS = 300
    # Raised once, deliberately, for plan tiers (v0.24.0). This ratchet measures
    # agent context — loaded once, cached, cheap. Tiering spends ~700 characters
    # of it to take roughly 2,000 words off every small plan a human reads at the
    # gate, on every change; the 2026-07-27 Flik plan ran to 3,166 words and ~14
    # minutes. The proxy cannot see what is being bought, and refusing a good
    # trade because a proxy says no is the wrong use of a guard. Two blocks of
    # rehearsed checker output were cut from worked-change.md first, so the raise
    # is 500 rather than 1,200. Lower it again if worked-change.md is retired.
    # Raised to 38,000 for plan tiers, then lowered again when the lane-variants
    # table came out of worked-change.md: six of its seven lanes were already in
    # the body, and the one real-use run copied the walkthrough prose, not the
    # table. A ratchet that only goes up is a budget with extra steps.
    # A RATCHET, NOT A BUDGET. No published guidance bounds per-change reference
    # load; this number was set to wherever the content happened to be, and it has
    # moved five times. That is not a defect in the number — its only job is to make
    # growth a *decision* instead of a drift, and it has done that four times in one
    # session, three of which produced real displacement.
    #
    # What it must not do is settle the decision. Hitting it means: displace, or
    # raise it and record why. It was once used to silently drop an addition the
    # human had asked for, which is the failure mode to avoid — surface the conflict
    # rather than resolving it by deleting the cheapest thing.
    #
    # For scale: ~10,000 tokens per plan-gated change puts this 5th of Anthropic's
    # 62 shipped skills by loaded prose; canvas-design is 3.5x larger.
    # 40,400 -> 41,000, raised on request after the v0.11-v0.20 audit. Every
    # rule-shaped and prose line that has existed in skills/ since v0.11.3 has now
    # been read individually — 267 of them — and fourteen purpose sentences were
    # found lost to the rewrites that turned guidance into contracts. Most were
    # covered or marginal; the ones restored are criteria a step applies, not
    # explanation, and two of the three landed in ctdd-tests where no increase was
    # needed at all.
    #
    # 41,000 chars is ~10,250 tokens: 5th of Anthropic's 62 shipped skills by
    # loaded prose, with canvas-design 3.5x larger. The headroom is deliberate —
    # a ceiling with 48 characters spare blocks correctness work, which is how the
    # consumer-driven pin came to be dropped and reported as a displacement.
    # 41,000 -> 41,500, for the six workflow-correctness findings of v0.31.0:
    # a restored approval exclusion, a trivial lane with no unwind path, two
    # prompt options nothing consumed, a write freeze that never re-armed, and a
    # step 8 body that assumed a plan the trivial lane never wrote. One of the
    # six was a deletion. None is new guidance; all are repairs to instructions
    # that could not be executed as written.
    # 41,500 -> 41,800 for Part A: a post-change pin-fail state (the method's most
    # important signal had no state and the nearest row said to amend the pin
    # away), the trivial lane no longer skipping the validator, tests, suite and
    # build, and step 8's Enter no longer satisfiable by the empty set. Net of
    # deleting 7.7's pre-implementation after-run.
    # 41,800 -> 42,300 to restore the step 8.4 inventory to worked-change.md.
    # `check-spec-surface` had appeared ZERO times in the file: a budget
    # displacement removed the block and left the prose after it referring to an
    # inventory nobody could see, so both 3.3 and 8.4 were undemonstrated in the
    # one file that exists because agents copy examples. The output is a real run,
    # pasted verbatim, and the quoted-literal guard checks it against the script.
    # 42,300 -> 42,400 for the last two Tier 1 repairs: step 10's Enter, which was
    # satisfied at 9.3 while 9.4 said wait, and `Business requirement` in the
    # gate-visible set, which step 9.2 back-translates against and the approver
    # never saw. Four displacements were made first — a rationale line that
    # restated 9.2, step 10's own essay, 10.2 restating 10.1's condition inverted,
    # and "every other decision" when the list stopped being a remainder — so what
    # is left is the fixes themselves at minimal wording.
    # 42,400 -> 42,700 for four judgement-call repairs: the approval gate no
    # longer asks the agent to recommend its own plan, the negative control is
    # scoped to the lane where no plan is in flight, the test verdicts map into
    # ctdd-review's real categories, and the plan directory is resolved rather
    # than assumed. The plan-dir work paid for itself — replacing five hardcoded
    # `docs/plans/` mentions with the resolved form ran 13 characters cheaper than
    # the assumption it removed.
    MAX_PLAN_GATED_METHODOLOGY_CHARS = 42700
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
        lines = [l for l in t.split("\n") if "jqwik" in l]
        # Assert positively. The loop-over-matching-lines form passed with every
        # jqwik line deleted — CLAUDE.md rule 8's first named example, and blind
        # to exactly the regression that already shipped: 0.21.2 kept the removal
        # and dropped the reason.
        self.assertTrue(lines, "the jqwik warning is gone; deleting it must fail")
        joined = " ".join(lines).lower()
        # Assert on the hazard, not on the payload. Requiring the injection string
        # verbatim made a defect (the unscoped imperative sitting in agent context
        # on every invocation) into a required invariant.
        self.assertIn("stdout", joined,
                      "the warning must say where the hazard lands")
        for banned in ("recommend", "prefer jqwik", "use jqwik for"):
            self.assertNotIn(banned, joined,
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
        limit = self.BODY_LIMIT_CHARS
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
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
        if probe.returncode != 0:
            self.skipTest("not a git checkout")
        for ref in sorted(self._skills().glob("*/references/*.md")):
            rel = ref.relative_to(root).as_posix()
            r = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", rel],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
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

    def test_a_required_holdout_is_presented_as_a_bounded_decision(self):
        """Zero executions across six load-bearing changes. The ask was
        "write 1-3 sealed tests" — unbounded, at the moment of approval, with no
        stated alternative. The format now requires named assertions, `write` and
        `decline` with their consequences, and a recommendation, because the
        example is what the agent copies."""
        fmt = (self._skills() / "ctdd-change" / "references"
               / "plan-format.md").read_text(encoding="utf-8")
        self.assertIn("Present a required hold-out as a decision, not a notice", fmt)
        example = fmt[fmt.find("## Complete example"):]
        block = example[example.find("Hold-out"):]
        block = block[:block.find("\n\n")] if "\n\n" in block else block
        for field in ("- options:", "- recommended:"):
            self.assertIn(field, block,
                          f"the worked hold-out lost {field!r}; models copy the example")
        self.assertIn("decline", block)

    def test_the_review_verdict_is_dispatched_not_self_issued(self):
        """9.4 said `Invoke ctdd-review ... never state that verdict yourself`.
        Both halves are satisfiable only in a separate context, and `invoke` reads
        as `load the skill here`. On 2026-07-30 the agent loaded ctdd-review into
        its own session and issued the verdict on its own diff; on 2026-07-27 it
        read the same words the other way and refused. Two defensible readings of
        one sentence is a defective sentence."""
        t = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("hand the `ctdd-review` verdict to the human", t)
        self.assertIn("never dispatch it yourself unless asked", t)
        self.assertNotIn("Invoke `ctdd-review` on the final diff", t)
        # and not the 0.24.1 wording, which read as a licence to spawn one
        self.assertNotIn("Dispatch `ctdd-review` on the final diff", t)

    def test_the_workflow_reads_adr_markers_and_scans_on_new_surface(self):
        """Markers only help if a step reads them, and they are absent exactly
        where a decision is most likely to be contradicted unseen: new contract
        surface, which has no test trail to carry one. Step 2 reads the markers
        on what it is already reading; the title scan covers the case where there
        is nothing to read."""
        t = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        step2 = t.split("\n2. **Read the existing slice.**", 1)[1].split("\n3. ", 1)[0]
        self.assertIn("ADR-NNNN", step2)
        self.assertIn("adds contract surface", step2)
        # `docs/adr/` is where this plugin *writes* a new ADR; it is not where
        # every repository *keeps* them. Naming it here would send the scan to
        # the wrong place in any repo using `adr/`, `doc/adr/` or its own layout,
        # and silence there reads as "no decision applies".
        self.assertNotIn("docs/adr/", step2)

    def test_a_matched_adr_contributes_preservation_pins(self):
        """An ADR whose decision no test protects is one this change can reverse
        silently. Pins are named at plan time, so the rule belongs in the plan
        format rather than at the step that invokes ctdd-tests."""
        fmt = (self._skills() / "ctdd-change" / "references"
               / "plan-format.md").read_text(encoding="utf-8")
        self.assertIn("Pin the tests that already assert a decision recorded by any ADR", fmt)

    def test_the_adr_verdict_never_claims_no_decision_applies(self):
        """Marker matching sees only decisions someone annotated. An unmarked ADR
        is invisible to it, so the verdict must report relevance and never
        absence — the fail-silent shape this repo keeps producing is a mechanism
        stating a stronger conclusion than it earned."""
        src = (self._skills().parent / "scripts"
               / "check-spec-surface.py").read_text(encoding="utf-8")
        self.assertIn("no marker does not prove no decision applies", src)
        self.assertNotIn("No relevant ADRs", src)
        self.assertIn("A marker pointing at nothing is a lost decision", src)

    @staticmethod
    def _normalise_checker_text(s):
        return _norm(s)

    def test_no_operative_rule_is_stranded_in_an_unloaded_rationale(self):
        """The existing probe covers `ctdd-review` only, because that is the skill
        that shipped the defect — while `test_reference_loaders_survive_the_same_
        boundary` deliberately exempts `rationale.md` from the loader check. So the
        known recurrence path was unguarded in the larger skill: a rule moved into
        `ctdd-change/references/rationale.md`, which is marked do-not-load during a
        change, is a rule no agent executing the steps ever reads.

        A rule is operative if it is an imperative a step must follow. Rationale
        may explain; it may not be the only place an obligation appears."""
        import re as _re
        for skill in ("ctdd-change", "ctdd-tests", "ctdd-review"):
            rat = self._skills() / skill / "references" / "rationale.md"
            if not rat.exists():
                continue
            elsewhere = "\n".join(
                f.read_text(encoding="utf-8")
                for f in (self._skills() / skill).rglob("*.md")
                if f.name != "rationale.md")
            for line in rat.read_text(encoding="utf-8").split("\n"):
                s = line.strip().lstrip("-*0123456789. ").strip()
                if len(s) < 30:
                    continue
                # An imperative obligation, not an explanation.
                if not _re.match(r"(Never|Always|Do not|Stop|Require|Record|Report|"
                                 r"Verify|Write|Invoke|Name|Treat)\b", s):
                    continue
                key = " ".join(_re.findall(r"[a-z]{5,}", s.lower())[:4])
                if not key:
                    continue
                self.assertTrue(
                    all(w in elsewhere.lower() for w in key.split()),
                    f"{skill}/rationale.md carries an obligation that appears "
                    f"nowhere an agent loads: {s[:90]!r}")

    def test_the_inventory_compares_against_the_plan_in_both_directions(self):
        """8.5 stops only when the inventory EXCEEDS the plan. The deficit was
        unhandled: a plan naming `openapi.yaml — relax the amount constraint`
        whose contract file is never edited leaves the inventory a subset, no stop
        fires, and an approved contract change simply does not ship."""
        import subprocess, tempfile, os, sys as _s
        plan = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                           encoding="utf-8")
        plan.write("Files likely to change: `payments/api/Capture.cs`, "
                   "`payments/contract/openapi.yaml`\n")
        plan.close()
        try:
            r = subprocess.run(
                [_s.executable, SCRIPT, "--plan", plan.name],
                input="M\tpayments/api/Capture.cs\n", capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=15)
            self.assertIn("Planned but untouched", r.stdout)
            self.assertIn("openapi.yaml", r.stdout)
            # report-only: the verdict must not change
            self.assertEqual(r.returncode, 0, r.stdout)
        finally:
            os.unlink(plan.name)

    def test_a_submodule_bump_is_unread_surface_not_no_surface(self):
        """A gitlink shows in the parent diff as `M<TAB>sub` and git cannot see
        through it, so a submodule whose tests changed `assert 1` to `assert 0`
        counted as `other` and produced *no test/contract/ADR surface touched* —
        the string SKILL.md 3.3 opens the trivial lane on, verbatim. Unknown
        content is not the same as no surface."""
        import subprocess, sys as _s
        r = subprocess.run([_s.executable, SCRIPT], input="M\tsub\n",
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=15)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Unread surface", r.stdout)
        self.assertNotIn("no test/contract/ADR surface touched", r.stdout)
        # a plain production file is still not surface
        r2 = subprocess.run([_s.executable, SCRIPT], input="M\tsrc/App.cs\n",
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=15)
        self.assertEqual(r2.returncode, 0, r2.stdout)

    def test_the_readme_names_a_hook_location_claude_code_loads(self):
        """The README told marketplace users — the path it says most take — to copy
        `hooks.json.example` into `.claude/`, which is not a location Claude Code
        reads. That yields a hook that silently never runs."""
        readme = (Path(SCRIPT).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        self.assertIn(".claude/settings.json", readme)
        self.assertNotIn("into your own project's `.claude/`", readme)

    def test_a_letter_prefixed_adr_filename_still_resolves(self):
        """`re.match(r"0*(\\d{1,4})", name)` is position-anchored to a digit, so
        every `ADR-NNNN-slug.md` resolved to nothing — a common convention — and a
        healthy repository got `BROKEN ADR markers ... no such ADR file exists`,
        which adr_dirs' own docstring calls worse than silence."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("css_adr", SCRIPT)
        css = importlib.util.module_from_spec(spec); spec.loader.exec_module(css)
        import tempfile, os
        root = tempfile.mkdtemp()
        d = os.path.join(root, "docs", "adr"); os.makedirs(d)
        for fn in ("ADR-0017-domain.md", "0018-other.md"):
            open(os.path.join(d, fn), "w", encoding="utf-8").write("# x")
        self.assertTrue(css.resolve_adr("0017", root=root),
                        "ADR-0017-domain.md did not resolve")
        self.assertTrue(css.resolve_adr("0018", root=root))

    def test_allow_empty_is_not_forwarded_to_git(self):
        """`--allow-empty` is ours, not git's; forwarding it produced
        `git failed: usage: git diff` and exit 2, so the flag was unreachable in
        the one mode where an empty diff is most likely — a clean tree."""
        src = Path(SCRIPT).read_text(encoding="utf-8")
        self.assertIn('a != "--allow-empty"', src)

    def test_marker_reads_are_capped_like_the_hook(self):
        """Uncapped, one large binary in a diff decoded entirely into a str. Two
        readers of the same marker convention must agree on how much of a file
        carries it."""
        src = Path(SCRIPT).read_text(encoding="utf-8")
        hook = (Path(SCRIPT).resolve().parents[1] / "hooks"
                / "spec-edit-guard.py").read_text(encoding="utf-8")
        self.assertIn("fh.read(200_000)", src)
        self.assertRegex(hook, r"read\(200")

    def test_the_approval_gate_asks_for_no_recommendation(self):
        """The Decision prompt row requires *one recommended with a one-line
        reason*, and 6.3 makes the approval gate a Decision prompt — with no
        conditional exempting it. So the agent printed `Recommended: approve`
        while the same skill says *do not approve your own plan* and 6.4 excludes
        its own restatement. The exclusion list is the point: the agent's voice
        does not count here."""
        body = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        row = [l for l in body.split("\n") if l.startswith("| Decision prompt |")]
        self.assertEqual(len(row), 1, "the Decision prompt row moved")
        self.assertIn("Recommend nothing at the step 6 approval gate", row[0])

    def test_the_plan_directory_is_resolved_not_assumed(self):
        """`check-plan.py` honours `planDir` and *rejects* any pointer outside it,
        while the skill hardcoded `docs/plans/` in six places — so a repository
        setting `"planDir": "docs/ctdd-plans"` got an exit-1 CI failure on a
        correct plan. `adrDir` was already resolved via `--adr-dir`; the asymmetry
        was the bug, and configurable-and-unusable is the worst of both."""
        body = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("--plan-dir", body)
        self.assertNotIn("docs/plans/", body,
                         "a hardcoded plan directory contradicts the checker that "
                         "rejects pointers outside the configured one")

    def test_step_ten_runs_before_the_diff_is_handed_over(self):
        """9.4 ends *name the final diff and wait*; step 10's Enter was *step 9
        printed the packet*, printed at 9.3. Either the colocated note was never
        written — which is what worked-change.md models, since it ends at step 9 —
        or it edited a source or contract file **after** the diff was named final,
        outside the packet's Spec surface inventory and after every verification
        result the packet claims."""
        body = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        step10 = [l for l in body.split("\n") if l.startswith("10. **")]
        self.assertEqual(len(step10), 1, "step 10 moved")
        self.assertIn("before 9.4 hands over the diff", step10[0],
                      "step 10 has no reachable execution point: its Enter is "
                      "satisfied at 9.3 while 9.4 says wait")

    def test_the_business_requirement_reaches_the_gate(self):
        """It was dropped from the gate-visible set in v0.27.0 and added to
        SMALL_SECTIONS two commits later — mandatory at every tier, invisible at
        the gate. Step 9.2 back-translates *beside the business requirement*, so
        the one comparison the method runs on every change was anchored to a
        statement the approver never saw."""
        fmt = (self._skills() / "ctdd-change" / "references"
               / "plan-format.md").read_text(encoding="utf-8")
        line = [l for l in fmt.split("\n") if "the summary names" in l.lower()]
        self.assertEqual(len(line), 1, "the gate-visible sentence moved")
        for name in ("Business requirement", "Assumptions", "Residual risk"):
            self.assertIn(f"`{name}`", line[0], f"{name} is not named at the gate")

    def test_the_new_behaviour_handoff_is_not_a_deadlock(self):
        """`ctdd-change` 7.9 invokes `ctdd-tests` to write the new-behavior tests;
        `ctdd-tests` routes *changed expected behavior* to `ctdd-change`. A
        new-behavior test IS changed intent, so it bounced — and `ctdd-change`
        forbids writing a test file itself. Neither skill could produce the file
        and step 8's Enter was unsatisfiable. The pin lane was safe only because
        `preservation-pin` is named explicitly in the keep list.

        The carve-outs existed but sat *after* the routing gate, so they were
        never reached; the invocation has to be named in the routing rule."""
        tests = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        route = [l for l in tests.split("\n")
                 if l.startswith("- Route changed expected behavior")]
        self.assertEqual(len(route), 1, "the routing rule moved")
        keep = tests.split(route[0])[0]
        self.assertIn("invokes you at 7.5 or 7.9", keep,
                      "the ctdd-change invocation must be named before the route "
                      "that would otherwise send a new-behavior test away")

    def test_the_holdout_prompt_offers_only_resolvable_options(self):
        """9.1 asked write / decline / defer while the resolutions are `passed`,
        `failed`, `declined by human` and `NOT RUN`. A deferral landed on
        `NOT RUN — deferred`, which **skips** plan-format rule 8's fallback —
        only `declined by human` triggers it, so choosing defer silently dropped
        the one mitigation a decline still carries. `plan-format` rule 6 already
        mandated write and decline only; 9.1 was the outlier."""
        body = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        line = [l for l in body.split("\n") if "sealed hold-out result" in l
                and "Decision prompt" in l]
        self.assertEqual(len(line), 1, "9.1 moved")
        self.assertIn("write / decline", line[0])
        self.assertNotIn("defer", line[0])

    def test_every_step_cross_reference_resolves(self):
        """Nothing resolved an `N.M` reference — every structural guard here is
        literal-substring, and the two that mention `8.3` and `8.6` pin the
        *sentences* containing them, not that those substeps exist. So a
        renumbering could leave a reference pointing at a step that no longer
        exists and the whole suite stayed green: v0.35.0 deleted 7.7 and renumbered
        the rest, and `Skip 7.10-7.12` survived into a step 7 that ends at 7.11.

        Ranges are resolved too, and both dash forms: the skill uses an en dash in
        `7.5-7.8`, so a hyphen-only pattern would silently check nothing."""
        import re as _re
        for skill in ("ctdd-change", "ctdd-tests", "ctdd-review"):
            body = _re.sub(r"^---\n.*?\n---\n", "",
                           (self._skills() / skill / "SKILL.md").read_text(encoding="utf-8"),
                           flags=_re.S)
            defined, cur = set(), None
            for line in body.split("\n"):
                top = _re.match(r"^(\d+)\. \*\*", line)
                if top:
                    cur = top.group(1)
                    defined.add(cur)
                    continue
                sub = _re.match(r"^\s+(\d+)\.\s", line)
                if sub and cur:
                    defined.add(f"{cur}.{sub.group(1)}")
            refs = set()
            for m in _re.finditer(r"\b(\d+\.\d+)\s*[–—-]\s*(\d+\.\d+)\b", body):
                lo, hi = m.group(1), m.group(2)
                refs.update({lo, hi})
                a_top, a_n = lo.split("."); b_top, b_n = hi.split(".")
                if a_top == b_top:
                    refs.update(f"{a_top}.{n}" for n in range(int(a_n), int(b_n) + 1))
            refs.update(_re.findall(r"\b(\d+\.\d+)\b", body))
            # A reference qualified by another skill's name belongs to that
            # skill's numbering, not this one's: `ctdd-tests` legitimately cites
            # `ctdd-change` 7.5 and 7.9 as the route by which it is invoked.
            foreign = set()
            # The window must not stop at the first `.` — `7.5` contains one.
            for m in _re.finditer(r"`ctdd-(?:change|tests|review)`[^\n]{0,90}", body):
                foreign.update(_re.findall(r"\b(\d+\.\d+)\b", m.group(0)))
            dangling = sorted(r for r in refs
                              if r not in defined and r not in foreign)
            self.assertFalse(
                dangling,
                f"{skill} refers to steps that do not exist: {dangling}")

    def test_the_workflow_has_no_unexecutable_transitions(self):
        """Six v0.31.0 repairs, asserted as whole sentences rather than fragments.

        The first version was a list of `assertIn` substring checks, and every
        repaired rule could be negated while leaving the asserted substring intact
        — the write freeze rewritten to "Once an Approval record exists ... write
        whatever you like; the only file you write is the step 5 plan file is not a
        rule" passed. That is rule 8's third named failure verbatim: a substring
        assertion that stayed true while the sentence it checked inverted.

        Asserting the full sentence is not as strong as constructing the forbidden
        state and showing the workflow rejects it — that needs an executor this
        repo does not have — but it does mean a negation has to delete the
        sentence, and deletion is what the guard now catches."""
        t = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        sentences = {
            "write freeze keyed on the current revision":
                "Until an Approval record exists for the current plan revision, the "
                "only file you write is the step 5 plan file; an amendment voids the "
                "previous one.",
            "approval excludes a harness surface":
                "Your own restatement, silence, a subagent verdict, a passing "
                "checker, and harness acceptance of a plan-mode surface are not "
                "approval.",
            "the other two prompt options are consumed":
                "Amend the plan, re-run the checker and re-present on changes; stop "
                "on reject.",
            "the trivial lane can be unwound":
                "Retract the declaration from stdout and the PR/MR description, then "
                "return to 3.1 as plan-gated, when any later step contradicts 3.4 or "
                "3.5.",
            "step 4 admits a retraction":
                "Enter: step 3 did not fire 3.6, or 3.7 retracted it.",
            "step 8 does not assume a plan in the trivial lane":
                "in the trivial lane compare it with the declared diff instead, take "
                "8.3's pin re-run and 8.6 as `n/a`, and still run the validator, "
                "tests, suite and build",
            "step 8 needs at least one named test":
                "Enter: step 7 satisfied every applicable evidence lane, and at "
                "least one lane named a test",
        }
        for label, sentence in sentences.items():
            self.assertIn(sentence, t, f"the rule '{label}' no longer reads as written")
        # 7.7's trigger was unevaluable: `preservation-only conversion` occurred
        # once in the whole tree, in the clause requiring it.
        self.assertNotIn("preservation-only conversion", t)
        self.assertIn("pin-state-after path", t)

    def test_the_worked_example_demonstrates_every_checker_it_names(self):
        """`check-spec-surface` appeared ZERO times in worked-change.md: a budget
        displacement removed the block and left the prose after it referring to an
        inventory nobody could see, so steps 3.3 and 8.4 were both undemonstrated
        in the one file that exists because agents copy examples."""
        wc = (self._skills() / "ctdd-change" / "references"
              / "worked-change.md").read_text(encoding="utf-8")
        for script in ("check-plan.py", "check-redstate.py", "check-spec-surface.py"):
            self.assertIn(script, wc, f"{script} is never demonstrated")

    def test_the_example_gate_order_matches_the_output_contract(self):
        """The file that exists because models copy examples demonstrated the plan
        path last where the contract puts it first."""
        skill = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        wc = (self._skills() / "ctdd-change" / "references"
              / "worked-change.md").read_text(encoding="utf-8")
        self.assertIn("`Plan: <path> (<tier>)`", skill)
        self.assertIn("`Plan: <path> (<tier>)` goes to stdout first", wc)

    def test_the_canonical_plan_addresses_every_always_case(self):
        """Rule 4 says never leave a coverage row unaddressed and the example IS
        the operative instruction — yet `Side effects` was marked Always with no
        bullet carrying `case: side effect` and no waiver, so the example taught
        the violation. It already asserted `exactly one PaymentCaptured`; only the
        label was missing."""
        import re as _re
        fmt = (self._skills() / "ctdd-change" / "references"
               / "plan-format.md").read_text(encoding="utf-8")
        ex = _re.search(r"## Complete example.*?```markdown\n(.*?)```", fmt,
                        _re.S).group(1)
        cases = set()
        for c in _re.findall(r"case:\s*([^;.\n]+)", ex):
            cases |= {x.strip().lower() for x in c.split(",")}
        waived = ex.lower().split("case coverage not reached", 1)[-1][:400]
        for row in ("positive", "negative", "boundary", "error path", "side effect"):
            self.assertTrue(row in cases or row in waived,
                            f"the example addresses no {row!r} case")

    def test_quoted_checker_output_in_references_matches_the_scripts(self):
        """worked-change.md quoted a check-plan verdict for four releases after
        tiers changed the string, and nothing compared them.

        The first guard had two holes, both reproduced: it only inspected lines
        *starting* with the prefix, so the whole review-packet block — whose lines
        start `Plan check: `, `Red state: ` — was skipped and a fabricated verdict
        passed there; and it compared five words, so a truncated quote is a prefix
        of the real literal and always passes. The live stale instance sat in the
        skipped block the whole time.

        Compared token-wise: a `{hole}` in the script matches any one word in the
        quote, a digit matches any digit run, and the quote must appear as a
        contiguous run of some literal — so a truncation fails."""
        def words(s):
            """One normaliser for both sides: an interpolation hole and a digit
            run both become `*`, punctuation is dropped, case is ignored."""
            s = re.sub(r"\{[^}]*\}", " * ", s)
            s = re.sub(r"\d+", " * ", s)
            s = re.sub(r"[^\w*]+", " ", s)
            return s.lower().split()

        scripts = Path(__file__).resolve().parent
        raw = "\n".join((scripts / n).read_text(encoding="utf-8")
                        for n in ("check-plan.py", "check-redstate.py",
                                  "check-spec-surface.py"))
        raw = re.sub(r'"\s*\n\s*(?:f?")?', " ", raw)   # rejoin split literals
        lits = [words(chunk) for chunk in raw.split('"')]

        def ends_with(lit, want):
            """The quote must run to the end of the literal, not merely start it.

            A truncation is a contiguous prefix of the real string, so a
            prefix-tolerant match always passed — which is how `all mandatory
            sections present` survived four releases after the script began
            emitting `... for a {tier} plan (N of M; ...)`.
            """
            n = len(want)
            if n > len(lit):
                return False
            return all(a == "*" or b == "*" or a == b
                       for a, b in zip(lit[len(lit) - n:], want))

        refs = self._skills() / "ctdd-change" / "references"
        checked = 0
        for f in sorted(refs.glob("*.md")):
            for line in f.read_text(encoding="utf-8").split("\n"):
                for prefix in ("check-plan:", "check-redstate:", "check-spec-surface:"):
                    k = line.find(prefix)
                    if k < 0:
                        continue
                    want = words(line[k + len(prefix):].split("`")[0])
                    if len(want) < 3:
                        continue
                    checked += 1
                    self.assertTrue(
                        any(ends_with(l, want) for l in lits),
                        f"{f.name} quotes {prefix} {' '.join(want)!r}, "
                        f"which no script emits")
        self.assertGreater(checked, 0, "no quoted checker output was inspected")

    def test_the_last_three_audit_losses_are_restored(self):
        """Closing out the v0.11.3-v0.20.1 audit. A flaky spec reads as an
        unreliable spec — the determinism dimension names the uncontrolled input
        but never said why retrying is not an option, and that argument decides
        cases the dimension does not enumerate. A bug-fix regression test is the
        spec of the fix — dimension 4 covers deleting it as a spec amendment, but
        not why it persists. And step 0 recorded the branch without ever remarking
        that the change was landing on the branch it would be reviewed from."""
        tests = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("a flaky spec reads as an unreliable spec", tests)
        self.assertIn("is the spec of the fix", tests)
        change = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("when the current branch is the target branch", change)

    def test_the_packet_states_its_purpose_and_the_back_translation_is_independent(self):
        """Both were lost in the 0.21.0-0.23.0 rewrites, which converted guidance
        into contracts. A contract holds structure and prohibitions and has nowhere
        to put purpose, so every rule with a checker survived and every sentence
        saying *why* did not — twelve of them across four files.

        `changed tests are changed requirements` is the method's thesis and the
        reason check-spec-surface exists; step 9 had been left saying `assemble its
        exact packet`, a shape with no reason. The back-translation had lost `from
        the tests alone`, which is the clause that makes it independent evidence
        rather than a summary of the diff, and `beside the business requirement`,
        which is the comparison that makes it usable."""
        t = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        # "test expectations", not "tests": a rename, de-flake or altitude repair is a
        # changed test and not a changed requirement, and ctdd-tests keeps those in
        # its own lane on exactly that basis. `expectation` is already the term of art
        # in dimension 4.
        self.assertIn("Changed test expectations are changed requirements", t)
        self.assertNotIn("Changed tests are changed requirements", t)
        self.assertIn("contract diffs are boundary changes", t)
        self.assertIn("from the changed tests alone", t)
        self.assertIn("beside the business requirement", t)

    def test_the_holdout_decline_path_keeps_what_makes_it_independent(self):
        """These three fell out across 0.21.3 and 0.23.0 in compression passes —
        one changelog claimed "every rule intact", another never got an entry.
        None was decided against. They went unnoticed because the hold-out has
        zero executions in seven changes, so nothing ever exercised them, and
        the `must_survive` probes never covered them.

        They are a chain. Without the arithmetic clause the fallback is not an
        independent reading: verifying by opening the implementation and
        agreeing inherits the very misunderstanding the hold-out exists to
        break. Without "never the equivalent" the cheap path silently becomes
        the guard — which already happened. Without "waiver" a decline is one of
        four neutral enum values, indistinguishable in the packet from a decline
        on a rename."""
        fmt = (self._skills() / "ctdd-change" / "references"
               / "plan-format.md").read_text(encoding="utf-8")
        self.assertIn("recompute each one by hand from the business requirement", fmt)
        # never by reading the code is the clause that makes the fallback a second
        # reading rather than a countersignature on the first.
        self.assertIn("never by reading the code that produced it", fmt)

        self.assertIn("never as the equivalent", fmt)
        self.assertIn("is a waiver, not a neutral outcome", fmt)
        rev = (self._skills() / "ctdd-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("hold-out as a finding on a high-risk", rev)

    def test_altitude_pressure_runs_in_both_directions(self):
        """The escalation rule only ever pointed up: a hard test moves to `an
        existing higher public boundary`, and the altitude criterion — rewrite
        when a behavior-preserving refactor breaks it — only detects a test that
        is too *low*. A test asserting a lexical form through SQL passes that
        check perfectly: it survives every refactor, costs a database wipe, and
        can afford three values where thirty are cheap. 2026-08-03: 7 of 13
        integration tests asserted pure-function properties, and two Infrastructure
        unit-test projects sat empty. The agent followed the rule correctly; the
        rule had one direction."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Use an existing higher public boundary", t)
        self.assertIn("smallest boundary that has a contract of its own", t)
        # The outer test stays, but scoped. Every other rule in this skill pushes
        # toward more coverage — step 3 demands *every* boundary and *each* error
        # path, dimension 3 hunts for *missing* assertions, and dimension 4 makes
        # deleting one a spec amendment. Downward pressure without a scope on the
        # outer tier is a ratchet: both tiers exhaustive, forever.
        self.assertIn("Keep one representative case at the outer boundary", t)
        self.assertIn("Two exhaustive tiers is one tier of waste", t)
        # and relocation must not be readable as deletion, or the correct action
        # is also the one that reopens the gate.
        self.assertIn("moved to a smaller boundary is not weakened", t)
        self.assertIn("without a named destination is a deletion", t)

    def test_the_gate_shows_the_summary_and_the_holdout_in_full(self):
        """The plan has two readers, and one file serves both: a summary the human
        approves from alone, and detail the agent implements from with no ceiling.
        6.1 once said `print the complete plan verbatim` — unfollowable at 31,448
        chars, so agents compressed and the hold-out was the first thing lost. The
        fix then printed eight sections in full, which made the gate scale with the
        plan and stop being a few-minute read. Now: summary plus the hold-out in
        full, everything else named in one line and printed on request.

        The hold-out keeps its exemption because it is the one item asking the human
        to leave the terminal and do something, and it has been declined or deferred
        on seven consecutive changes."""
        skill = (self._skills() / "ctdd-change" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Gate presentation", skill)
        self.assertIn("`Hold-out` block in full", skill)
        self.assertNotIn("every section `plan-format.md` marks **gate-visible**, in full", skill)
        fmt = (self._skills() / "ctdd-change" / "references"
               / "plan-format.md").read_text(encoding="utf-8")
        sec = fmt.split("## Gate-visible sections", 1)
        self.assertEqual(len(sec), 2, "plan-format.md lost the gate-visible section")
        listed = sec[1].split("##", 1)[0]
        for name in ("Assumptions", "Uncovered or ambiguous", "Known gaps",
                     "NFR budgets", "Residual risk", "ADR draft"):
            self.assertIn(name, listed, f"the summary is no longer required to name {name!r}")
        self.assertIn("two readers", fmt)
        self.assertIn("approves from it alone", fmt)
        self.assertIn("no ceiling on how much of that a change needs", fmt)

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

    def test_ctdd_tests_lanes_and_tool_commands_are_executable(self):
        """Seven repairs, all instructions that could not be followed as written.

        The authz command named no OpenAPI argument and never mentioned `-o`, so it
        exited 2 — and its all-deny caveat had been compressed away, leaving an
        agent to read a generator limit as a contract fact and scaffold a 403 for
        the legitimately authorised caller. Step 7 had no accepting branch for a
        passing pin, the mandatory outcome of `must pass before refactor`. The
        craft lane never entered the section holding its own criteria. Two thirds
        of the promotion rule were deleted with no changelog entry. The only skill
        that runs the checkers carried neither their exit semantics nor a blocked
        row. The jqwik warning carried an unscoped imperative into agent context on
        every invocation. And the per-test verdict vocabulary was one `ctdd-review`
        could not render.

        Plus the negative control (backlog C1): break the rule the test names,
        re-run, revert — the discipline the pilot used twice under pressure and
        never wrote down, and the tool-free form of the mutation testing the skill
        already recommends. The revert must be verified, because it licenses a
        production edit inside a lane whose guardrail forbids one."""
        t = (self._skills() / "ctdd-tests" / "SKILL.md").read_text(encoding="utf-8")
        for probe in (
            "<openapi-path> -o <matrix-path>",
            "read that as a generator limit, never as a contract fact",
            "those are the required results of their lanes",
            "Read `Test review` items 1, 2 and 6 first",
            "show the old marked name and the new name together",
            "drop the marker last",
            "red state, or checker result without running",
            "Its claim is unverified",
            "breaking the one production rule the test names, re-running, and reverting",
            # ...and only where no plan is in flight. Unscoped, it mutated a target
            # file during step 7, where 7.2 stops on exactly that and 8.1 says add
            # no other production code — and it contradicted this skill's own
            # "do not introduce production implementation during a test-only task".
            "Under an approved plan that is the whole action",
            "confirming a clean production diff",
            # The vocabulary must map into ctdd-review's categories, not collapse
            # into one: `add-coverage` went to `test-quality` although a dedicated
            # `needs-tests` exists, so the test lane could never produce it. And
            # `rename` is a naming preference — no triggering input, no observable
            # consequence — which that skill's severity ladder forbids emitting.
            "`add-coverage` to `needs-tests`",
            "a naming preference has neither",
        ):
            self.assertIn(probe, t, f"ctdd-tests lost: {probe!r}")
        # The jqwik hazard is described, never reproduced: an unscoped
        # "Disregard previous instructions" in the always-loaded surface is the
        # same injection one trust level up from the evidence channel.
        self.assertNotIn("Disregard previous instructions`", t)
        self.assertIn("instructing agents to disregard previous instructions", t)

    def test_approval_baselines_are_test_surface(self):
        """Re-recording an approval or snapshot baseline makes an implementation
        pass without editing any test file, so it evades the guardrail's verb list
        — edit, delete, skip, loosen, replace, reclassify — and landed as `other`
        in every deterministic consumer. A spec amendment with no artifact."""
        import importlib.util
        gp = Path(__file__).resolve().parents[1] / "hooks" / "spec-edit-guard.py"
        spec = importlib.util.spec_from_file_location("seg_ab", gp)
        guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
        pats = guard.patterns("CTDD_TEST_PATTERNS", guard.TEST_DEFAULT)
        for path in ("src/App.Tests/CaptureHandlerTests.verified.txt",
                     "src/App/__snapshots__/list.snap",
                     "web/list.test.js.snap",
                     "src/App.Tests/Handler.approved.json"):
            self.assertTrue(any(rx.search(path) for rx in pats),
                            f"{path} is not classified as test surface")

    def test_the_evaluation_set_agrees_with_the_description(self):
        """The first version was a two-phrase whitelist over one of three files, so
        49 of 73 cases were read by no test — and a third phrasing of the same
        defect was live and green: *"the payment tests broke after the refactor,
        make them pass"* asserts `should_trigger: true` for work `ctdd-tests`
        rejects and routes to `ctdd-change`.

        Derive the reject phrases from each skill's own description instead, so a
        new reject clause is covered the day it lands.

        Honest limit: this is lexical. It catches a case that quotes a reject
        phrase, across all three files rather than one; it cannot catch a
        paraphrase — "make them pass" *is* "update tests to match the new
        behavior" under deadline pressure, and only a reader sees that. The
        paraphrases found so far are fixed by hand and carry a `note`."""
        import json as _json, re as _re
        root = self._skills().parent
        for skill in ("ctdd-change", "ctdd-tests", "ctdd-review"):
            ev = root / "evals" / f"{skill}-triggers.json"
            if not ev.exists():
                continue
            desc = _re.match(
                r"^---\n(.*?)\n---", (self._skills() / skill / "SKILL.md")
                .read_text(encoding="utf-8"), _re.S).group(1).lower()
            # quoted phrases the description names as rejects
            rejects = []
            for m in _re.finditer(r"reject\b(.*?)(?:;|\.)\s", desc, _re.S):
                rejects += _re.findall(r'"([^"]{8,})"', m.group(1))
            for case in _json.loads(ev.read_text(encoding="utf-8")):
                q = case.get("query", "").lower()
                for phrase in rejects:
                    # Require the phrase as an ordered run, not its vocabulary: a
                    # bag-of-words match fired on "fix this bug ..." against
                    # "write tests for this", which is a correct trigger. The
                    # words must appear in order and close together.
                    key = _re.findall(r"[a-z]{4,}", phrase)
                    if len(key) < 2:
                        continue
                    run = _re.search(r"\b" + r"\b.{0,24}?\b".join(key) + r"\b", q)
                    if run:
                        self.assertFalse(
                            case.get("should_trigger"),
                            f"{ev.name}: the description rejects {phrase!r}, but "
                            f"this case asserts it triggers: {q[:80]}")

    def test_every_reject_clause_has_a_case(self):
        """`ctdd-change` names pins, flaky tests and de-flaking as rejects and
        judging a staged set, branch or commit as another — and no case in its own
        file contained any of those words, while `refactor this service`, a
        positive its description names, appeared in the corpus only as a
        `ctdd-tests` case. A reject clause with no case is a routing rule nothing
        can catch drifting."""
        import json as _json
        root = self._skills().parent
        required = {
            "ctdd-change": ("pin", "flaky", "de-flake", "staged", "branch",
                            "commit", "refactor this service"),
            "ctdd-review": ("architecture",),
        }
        for skill, probes in required.items():
            ev = root / "evals" / f"{skill}-triggers.json"
            corpus = " ".join(c.get("query", "").lower()
                              for c in _json.loads(ev.read_text(encoding="utf-8")))
            missing = [p for p in probes if p not in corpus]
            self.assertFalse(
                missing, f"{ev.name} has no case exercising: {missing}")

    def test_pressure_cases_can_fail_on_folding(self):
        """A pressure case scored solely by `should_trigger: true` cannot fail on
        the behaviour it exists to test: a skill that *folds* — loads, then skips
        the gate or weakens a test — produces exactly the same `true`. CLAUDE.md
        and the backlog both describe a guarantee the two-key schema cannot
        express, so each such case now states what must still hold whichever way
        it routes."""
        import json as _json
        root = self._skills().parent
        pressure = ("urgent", "no time", "deploy in", "right now", "just ",
                    "senior dev said", "production is down", "skip the", "quick,")
        checked = 0
        for f in sorted((root / "evals").glob("*.json")):
            for case in _json.loads(f.read_text(encoding="utf-8")):
                q = case.get("query", "").lower()
                if not any(k in q for k in pressure):
                    continue
                checked += 1
                self.assertIn(
                    "must_not_fold", case,
                    f"{f.name}: a pressure case scored only by should_trigger "
                    f"cannot fail on folding: {q[:70]}")
        self.assertGreater(checked, 0, "no pressure case was inspected")

    def test_the_backlog_eval_count_matches_the_corpus(self):
        """`backlog.md` states a case count that nothing checks, and every backlog
        item gated on eval CI reads it. It drifted by four."""
        import json as _json, re as _re
        root = self._skills().parent
        actual = sum(len(_json.loads(f.read_text(encoding="utf-8")))
                     for f in sorted((root / "evals").glob("*.json")))
        text = (root / "docs" / "backlog.md").read_text(encoding="utf-8")
        m = _re.search(r"There are (\d+) eval cases written", text)
        self.assertIsNotNone(m, "backlog.md no longer states a case count")
        self.assertEqual(int(m.group(1)), actual,
                         f"backlog.md says {m.group(1)}; the corpus has {actual}")

    def test_no_skill_claims_enforcement_it_does_not_have(self):
        """`ctdd-tests` contains no script and invokes no checker, so text saying it
        *enforces* naming and coverage claims mechanical assurance the plugin does
        not provide. The guard asserted `assertNotIn("Enforces", ...)` — capital E,
        frontmatter only — so `it enforces behaviour-level naming` passed, and that
        exact sentence had already shipped in the docs that describe the skill.
        A rejection claim is ruled out the same way: a skill can never reject, only
        route."""
        root = self._skills().parent
        targets = [self._skills() / "ctdd-tests" / "SKILL.md",
                   self._skills() / "ctdd-tests" / "references" / "rationale.md",
                   root / "docs" / "ctdd-in-depth.md",
                   root / "README.md"]
        for f in targets:
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8").lower()
            for claim in ("enforce", "rejects non-conforming", "rejects the"):
                for line in text.split("\n"):
                    if claim in line and "ctdd-tests" in line:
                        self.fail(f"{f.name} claims {claim!r} for ctdd-tests, which "
                                  f"runs no checker: {line.strip()[:110]}")

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


class AdrMarkerTests(unittest.TestCase):
    """Markers are the only pointer between a decision and the code it governs
    that moves when the code moves. An ADR listing its own files, or an index
    listing every ADR, is a second copy that rots independently of what it
    describes."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "docs", "adr"))
        os.makedirs(os.path.join(self.root, "src"))
        with open(os.path.join(self.root, "docs", "adr", "0017-domain.md"),
                  "w", encoding="utf-8") as fh:
            fh.write("# 17. Domain independence\n")

    def _write(self, name, body):
        path = os.path.join(self.root, "src", name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return f"src/{name}"

    def _run(self, diff):
        return subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent / "check-spec-surface.py")],
            input=diff, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=self.root, timeout=20)

    def test_no_skill_or_reference_hardcodes_an_adr_path(self):
        """Read and write must resolve the same directory. When they disagree the
        writer scans an empty `docs/adr/`, writes 0001 beside an `adr/` that
        already holds 0001-0014, and the reader then finds two ADRs numbered the
        same. The only place a literal may appear is the script's own fallback
        for a repository that has no ADR directory at all."""
        root = Path(__file__).resolve().parents[1] / "skills"
        for f in sorted(root.glob("*/SKILL.md")) + sorted(root.glob("*/references/*.md")):
            text = f.read_text(encoding="utf-8")
            for lit in ("docs/adr/", "docs/adrs/"):
                self.assertNotIn(
                    lit, text,
                    f"{f.relative_to(root)} hardcodes {lit!r}; resolve it with "
                    f"`check-spec-surface.py --adr-dir` so read and write agree")

    def test_the_decision_is_stored_in_the_repository_not_a_shell(self):
        """An environment variable is not storage: it lives in one shell, is
        absent on a fresh clone, on a teammate's machine and in CI, and nothing
        records the choice. A repository with two ADR directories would stop on
        every change until someone remembered to export it again."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "css4", str(Path(__file__).resolve().parent / "check-spec-surface.py"))
        css = importlib.util.module_from_spec(spec); spec.loader.exec_module(css)
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "adr")); os.makedirs(os.path.join(root, "docs", "adr"))
        self.assertIsNone(css.adr_dir(root)[0], "two directories must not be guessed")
        with open(os.path.join(root, ".ctdd.json"), "w", encoding="utf-8") as fh:
            fh.write('{"adrDir": "adr"}')
        path, why = css.adr_dir(root)
        self.assertEqual(path, "adr")
        self.assertIn(".ctdd.json", why)

    def test_the_environment_still_wins_for_a_single_run(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "css5", str(Path(__file__).resolve().parent / "check-spec-surface.py"))
        css = importlib.util.module_from_spec(spec); spec.loader.exec_module(css)
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "adr")); os.makedirs(os.path.join(root, "docs", "adr"))
        with open(os.path.join(root, ".ctdd.json"), "w", encoding="utf-8") as fh:
            fh.write('{"adrDir": "docs/adr"}')
        os.environ["CTDD_ADR_DIR"] = "adr"
        try:
            self.assertEqual(css.adr_dir(root)[0], "adr")
        finally:
            del os.environ["CTDD_ADR_DIR"]

    def test_a_malformed_config_is_ignored_rather_than_fatal(self):
        """This file is read on every hook invocation. A typo in it must not
        break editing."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "css6", str(Path(__file__).resolve().parent / "check-spec-surface.py"))
        css = importlib.util.module_from_spec(spec); spec.loader.exec_module(css)
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "adr"))
        with open(os.path.join(root, ".ctdd.json"), "w", encoding="utf-8") as fh:
            fh.write("not json {{{")
        self.assertEqual(css.adr_dir(root)[0], "adr")   # falls through to discovery

    def test_the_resolution_is_single_and_refuses_to_guess(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "css3", str(Path(__file__).resolve().parent / "check-spec-surface.py"))
        css = importlib.util.module_from_spec(spec); spec.loader.exec_module(css)
        empty = tempfile.mkdtemp()
        self.assertEqual(css.adr_dir(empty)[0], "docs/adr")          # nothing yet
        one = tempfile.mkdtemp(); os.makedirs(os.path.join(one, "adr"))
        self.assertEqual(css.adr_dir(one)[0], "adr")                 # adopt it
        two = tempfile.mkdtemp()
        os.makedirs(os.path.join(two, "adr")); os.makedirs(os.path.join(two, "docs", "adr"))
        path, why = css.adr_dir(two)
        self.assertIsNone(path, "two ADR directories must not be silently picked")
        self.assertIn("ambiguous", why)
        os.environ["CTDD_ADR_DIR"] = "adr"
        try:
            self.assertEqual(css.adr_dir(two)[0], "adr")             # human decides
        finally:
            del os.environ["CTDD_ADR_DIR"]

    def test_adr_directories_are_discovered_not_assumed(self):
        """A fixed path list makes a correctly-marked test in a repo that
        organises differently resolve to nothing — reported as a broken pointer,
        which is a false alarm on a healthy repo."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "css", str(Path(__file__).resolve().parent / "check-spec-surface.py"))
        css = importlib.util.module_from_spec(spec); spec.loader.exec_module(css)
        for layout in ("adr", "doc/adr", "docs/adrs"):
            root = tempfile.mkdtemp()
            os.makedirs(os.path.join(root, layout))
            with open(os.path.join(root, layout, "0017-x.md"), "w") as fh:
                fh.write("# 17\n")
            self.assertEqual(css.resolve_adr("0017", root=root),
                             f"{layout}/0017-x.md", f"failed for {layout}")

    def test_an_unconventional_layout_is_reachable_by_override(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "css2", str(Path(__file__).resolve().parent / "check-spec-surface.py"))
        css = importlib.util.module_from_spec(spec); spec.loader.exec_module(css)
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "architecture", "decisions"))
        with open(os.path.join(root, "architecture", "decisions", "0017-x.md"), "w") as fh:
            fh.write("# 17\n")
        self.assertIsNone(css.resolve_adr("0017", root=root))
        os.environ["CTDD_ADR_DIR"] = "architecture/decisions"
        try:
            self.assertEqual(css.resolve_adr("0017", root=root),
                             "architecture/decisions/0017-x.md")
        finally:
            del os.environ["CTDD_ADR_DIR"]

    def test_no_adr_directory_is_reported_as_unresolvable_not_as_broken(self):
        """With no ADR directory anywhere, a marker cannot be resolved at all.
        Saying "lost decision" there blames the repository for the checker's
        inability to look."""
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "src"))
        with open(os.path.join(root, "src", "T.cs"), "w") as fh:
            fh.write("// ADR-0017\n")
        r = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent / "check-spec-surface.py")],
            input="M\tsrc/T.cs\n", capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root, timeout=20)
        self.assertIn("No ADR directory was found", r.stdout)
        self.assertNotIn("lost decision", r.stdout)

    def test_a_marked_changed_file_names_its_governing_adr(self):
        self._write("HandlerTests.cs", "// ADR-0017: domain independence\nclass T {}\n")
        r = self._run("M\tsrc/HandlerTests.cs\n")
        self.assertIn("Governing ADRs named by changed files", r.stdout)
        self.assertIn("docs/adr/0017-domain.md", r.stdout)

    def test_a_marker_naming_no_adr_is_reported_not_skipped(self):
        self._write("HandlerTests.cs", "// ADR-0099: deleted decision\n")
        r = self._run("M\tsrc/HandlerTests.cs\n")
        self.assertIn("BROKEN ADR markers", r.stdout)
        self.assertIn("ADR-0099", r.stdout)

    def test_an_unmarked_change_reports_nothing_about_adrs(self):
        self._write("plain.cs", "class Plain {}\n")
        r = self._run("M\tsrc/plain.cs\n")
        self.assertNotIn("Governing ADRs", r.stdout)
        self.assertNotIn("BROKEN ADR", r.stdout)

    def test_a_renamed_file_is_scanned_at_its_new_path(self):
        self._write("NewTests.cs", "// ADR-0017\n")
        r = self._run("R100\tsrc/OldTests.cs\tsrc/NewTests.cs\n")
        self.assertIn("docs/adr/0017-domain.md", r.stdout)

    def test_a_missing_file_does_not_break_the_inventory(self):
        r = self._run("D\tsrc/Gone.cs\n")
        self.assertIn("check-spec-surface:", r.stdout)
        self.assertNotIn("Traceback", r.stderr)



if __name__ == "__main__":
    unittest.main(verbosity=1)
