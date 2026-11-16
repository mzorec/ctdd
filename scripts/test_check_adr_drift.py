"""Tests for check-adr-drift.py."""

import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

_spec = importlib.util.spec_from_file_location(
    "check_adr_drift",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-adr-drift.py"))
drift = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(drift)


def tree(files):
    """Materialize {relative path: text} under a temporary root."""
    root = tempfile.mkdtemp()
    for rel, text in files.items():
        p = pathlib.Path(root, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


class RemovedMarkerTests(unittest.TestCase):
    def test_reports_a_marker_on_a_removed_line(self):
        diff = "--- a/x.cs\n+++ b/x.cs\n-/// <remarks>ADR-0002</remarks>\n+// nothing\n"
        self.assertEqual(drift.removed_marker_ids(diff), ["2"])

    def test_ignores_the_minus_minus_minus_file_header(self):
        # `--- a/docs/adr/0002-x.md` starts with a minus and names a number;
        # read as content it would invent a removal on every ADR edit.
        diff = "--- a/docs/adr/ADR-0002-thing.md\n+++ b/docs/adr/ADR-0002-thing.md\n+text\n"
        self.assertEqual(drift.removed_marker_ids(diff), [])

    def test_added_lines_are_not_removals(self):
        self.assertEqual(drift.removed_marker_ids("+// ADR-0007 governs this\n"), [])

    def test_widths_normalize_to_one_decision(self):
        diff = "-// ADR-7\n-// ADR-0007\n"
        self.assertEqual(drift.removed_marker_ids(diff), ["7"])


class TreeScanTests(unittest.TestCase):
    def test_finds_markers_in_code(self):
        root = tree({"src/a.cs": "/// <remarks>ADR-0002</remarks>"})
        self.assertEqual(drift.markers_in_tree(root), {"2"})

    def test_excludes_the_adr_directory_itself(self):
        # An ADR naming its own number, or the one it supersedes, is not code
        # claiming to be governed by it — counting it would hide every orphan.
        root = tree({"docs/adr/0002-thing.md": "# 0002 — thing\nADR-0002 supersedes ADR-0001"})
        self.assertEqual(drift.markers_in_tree(root), set())


class OrphanTests(unittest.TestCase):
    def test_marker_removed_and_none_left_is_an_orphan(self):
        root = tree({"src/a.cs": "// no markers here"})
        self.assertEqual(drift.orphaned("-// ADR-0002\n", root), ["2"])

    def test_marker_removed_but_present_elsewhere_is_not(self):
        root = tree({"src/b.cs": "/// <remarks>ADR-0002</remarks>"})
        self.assertEqual(drift.orphaned("-// ADR-0002\n", root), [])


class StatusTests(unittest.TestCase):
    def test_reports_the_status_of_the_matching_adr(self):
        root = tree({"docs/adr/0002-scoping.md": "# 0002 — scoping\n\n- **Status:** Accepted\n"})
        name, status = drift.adr_status("2", root)
        self.assertEqual(name, "0002-scoping.md")
        self.assertEqual(status, "Accepted")

    def test_missing_adr_file_reports_nothing_rather_than_raising(self):
        self.assertEqual(drift.adr_status("9", tree({"src/a.cs": ""})), (None, None))


class ExitCodeTests(unittest.TestCase):
    def test_clean_change_exits_zero(self):
        root = tree({"src/a.cs": "/// <remarks>ADR-0002</remarks>"})
        self.assertEqual(drift.main(["--root", root, "--git", "HEAD"]), 0)

    def test_no_arguments_is_usage_not_a_false_pass(self):
        self.assertEqual(drift.main([]), 2)


if __name__ == "__main__":
    unittest.main()


class UnreadDiffTests(unittest.TestCase):
    """A checker that cannot read its input must not claim a pass.

    `read_diff` took `subprocess.run(...).stdout` and ignored the exit code. An
    unresolvable base writes to stderr and leaves stdout empty; an empty diff
    removes no marker; so `check-adr-drift --git nosuchref` printed *no ADR lost
    its last marker* and exited 0. That is a pass claimed over input the checker
    never read, which is the defect shape `ctdd-in-depth.md` records more often
    than any other, and it shipped in the newest checker.

    The other way to get this wrong is to fail always, so the clean-diff and
    stdin paths are asserted here beside the failure.
    """

    def setUp(self):
        import shutil
        import subprocess
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.run_git = lambda *a: subprocess.run(
            ["git", "-C", self.dir, *a], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        self.run_git("init", "-q", "-b", "main")
        self.run_git("config", "user.email", "t@example.com")
        self.run_git("config", "user.name", "T")
        pathlib.Path(self.dir, "x.cs").write_text("// ADR-0002\n", encoding="utf-8")
        self.run_git("add", "-A")
        self.run_git("commit", "-q", "-m", "seed")

    def _run(self, *args):
        import subprocess
        import sys
        return subprocess.run(
            [sys.executable,
             os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "check-adr-drift.py"), *args],
            cwd=self.dir, capture_output=True, text=True,
            encoding="utf-8", errors="replace")

    def test_an_unresolvable_base_is_unverified_not_a_pass(self):
        r = self._run("--git", "definitely-not-a-ref")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("no ADR lost its last marker", r.stdout)
        self.assertIn("not a pass", r.stdout)

    def test_a_clean_diff_still_passes(self):
        r = self._run("--git", "HEAD")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no ADR lost its last marker", r.stdout)

    def test_a_piped_diff_still_works(self):
        import subprocess
        import sys
        r = subprocess.run(
            [sys.executable,
             os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "check-adr-drift.py"), "-"],
            cwd=self.dir, input="--- a/x.cs\n+++ b/x.cs\n-// ADR-0002\n",
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)
        self.assertNotIn("not a pass", r.stdout)

    def test_read_diff_reports_why_rather_than_returning_none_silently(self):
        class Args:
            stdin = False
            git = "definitely-not-a-ref"
            rest = []
        import os as _os
        cwd = _os.getcwd()
        _os.chdir(self.dir)
        try:
            text, why = drift.read_diff(Args())
        finally:
            _os.chdir(cwd)
        self.assertIsNone(text)
        self.assertIn("exited", why)


SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check-adr-drift.py")
ADR = "0007-domain-has-no-framework-dependency.md"
ADR_TEXT = "# ADR-0007: The domain does not depend on frameworks\n\n- Status: Accepted\n"
REMOVED = ("--- a/src/Rule.cs\n+++ b/src/Rule.cs\n"
           "-// ADR-0007: the domain does not depend on frameworks\n")


class NamedAdrFolderTests(unittest.TestCase):
    """The folder `adrDir` names is an ADR folder here too.

    This script knew only folders named `adr` or `adrs`. In a repository
    whose settings named `docs/decisions`, the ADR files were scanned as code,
    so an ADR titled with its own number kept that marker in the tree and a
    change that removed the last real one passed as `no ADR lost its last
    marker`. `check-spec-surface.py --adr-dir` resolved the right folder in
    the same tree.
    """

    FILES = {"docs/decisions/" + ADR: ADR_TEXT, "src/Rule.cs": "class Rule {}\n"}

    def setUp(self):
        saved = os.environ.pop("CTDD_ADR_DIR", None)
        if saved is not None:
            self.addCleanup(os.environ.__setitem__, "CTDD_ADR_DIR", saved)

    def named(self, value='"docs/decisions"', files=None):
        return tree(dict(files or self.FILES, **{".ctdd.json": '{"adrDir": %s}' % value}))

    def _run(self, root, script=SCRIPT):
        """From another directory: `--root` is what says where the settings
        and the tree are."""
        elsewhere = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, elsewhere, True)
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        return subprocess.run([sys.executable, script, "-", "--root", root], cwd=elsewhere,
                              input=REMOVED, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env)

    def test_an_adr_in_the_named_folder_does_not_carry_its_own_marker(self):
        root = self.named()
        self.assertEqual(drift.orphaned(REMOVED, root), ["7"])
        self.assertEqual(drift.adr_status("7", root), (ADR, "Accepted"))

    def test_without_the_setting_that_folder_is_documentation(self):
        """The control: the same tree, and the ADR file counts as a file that
        still names the decision."""
        root = tree(self.FILES)
        self.assertEqual(drift.orphaned(REMOVED, root), [])
        self.assertEqual(drift.adr_status("7", root), (None, None))

    def test_the_environment_variable_names_the_folder_too(self):
        root = tree(self.FILES)
        os.environ["CTDD_ADR_DIR"] = "docs/decisions"
        self.addCleanup(os.environ.pop, "CTDD_ADR_DIR", None)
        self.assertEqual(drift.orphaned(REMOVED, root), ["7"])

    def test_the_folder_is_found_however_the_settings_spell_it(self):
        for value in ('"./docs/decisions/"', '"docs\\\\decisions"', '"Docs/Decisions"',
                      '["docs/decisions"]'):
            self.assertEqual(drift.orphaned(REMOVED, self.named(value)), ["7"], value)
        capitalised = self.named(files={"Docs/Decisions/" + ADR: ADR_TEXT,
                                        "src/Rule.cs": "class Rule {}\n"})
        self.assertEqual(drift.orphaned(REMOVED, capitalised), ["7"])

    def test_a_folder_inside_the_named_one_holds_adrs_too(self):
        root = self.named(files={"docs/decisions/archive/" + ADR: ADR_TEXT,
                                 "src/Rule.cs": "class Rule {}\n"})
        self.assertEqual(drift.orphaned(REMOVED, root), ["7"])

    def test_a_folder_that_only_starts_with_the_name_is_not_one(self):
        root = self.named(files={"docs/decisions-log/notes.md": "Still follows ADR-0007.\n",
                                 "src/Rule.cs": "class Rule {}\n"})
        self.assertEqual(drift.orphaned(REMOVED, root), [])

    def test_the_script_names_the_file_and_its_status(self):
        r = self._run(self.named())
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ADR-7 lost its last marker (%s, Status: Accepted)" % ADR, r.stdout)

    def test_a_settings_file_that_cannot_be_read_is_not_a_pass(self):
        r = self._run(self.named('"docs/decisions",'))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("check-adr-drift: `.ctdd.json` is not valid JSON", r.stdout)
        self.assertNotIn("no ADR lost its last marker", r.stdout)

    def test_copied_without_its_sibling_it_says_the_setting_was_not_read(self):
        """It still knows the convention, and says what it could not read
        instead of passing over a folder it never looked for."""
        alone = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, alone, True)
        shutil.copy(SCRIPT, alone)
        root = tree({"docs/adr/" + ADR: ADR_TEXT, "src/Rule.cs": "class Rule {}\n"})
        r = self._run(root, os.path.join(alone, "check-adr-drift.py"))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("`adrDir` was not read", r.stderr)


class AdrFileNameTests(unittest.TestCase):
    """An ADR file is found whatever its name leads with.

    The status lookup anchored on a digit, so a file named `ADR-0007-slug.md`
    was reported as `no ADR file found`, beside a decision that had just lost
    its last marker, while `check-spec-surface.py` resolved the same file. The
    two scripts now read a file name the same way, and a test holds them to
    the same answer.
    """

    NAMES = ("0007-domain.md", "7-domain.md", "ADR-0007-domain.md", "adr_0007-domain.md",
             "ADR0007-domain.md", "ADR-7.md")
    NOT_THE_ADR = ("notes-on-0007.md", "ADR-template.md", "0070-other.md")

    def setUp(self):
        saved = os.environ.pop("CTDD_ADR_DIR", None)
        if saved is not None:
            self.addCleanup(os.environ.__setitem__, "CTDD_ADR_DIR", saved)
        self.surface = drift._surface()

    def test_a_file_named_with_the_adr_prefix_is_found_with_its_status(self):
        root = tree({"docs/adr/ADR-0007-domain.md": ADR_TEXT})
        self.assertEqual(drift.adr_status("7", root), ("ADR-0007-domain.md", "Accepted"))

    def test_both_scripts_find_the_same_file_under_every_name(self):
        for name in self.NAMES:
            root = tree({"docs/adr/" + name: ADR_TEXT})
            self.assertEqual(self.surface.resolve_adr("7", root), "docs/adr/" + name, name)
            self.assertEqual(drift.adr_status("7", root)[0], name, name)

    def test_a_file_that_is_not_that_adr_is_found_by_neither(self):
        for name in self.NOT_THE_ADR:
            root = tree({"docs/adr/" + name: ADR_TEXT})
            self.assertIsNone(self.surface.resolve_adr("7", root), name)
            self.assertEqual(drift.adr_status("7", root), (None, None), name)

    def test_the_script_names_the_file_when_its_decision_loses_its_marker(self):
        root = tree({"docs/adr/ADR-0007-domain.md": ADR_TEXT, "src/Rule.cs": "class Rule {}\n"})
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        r = subprocess.run([sys.executable, SCRIPT, "-", "--root", root], cwd=root,
                           input=REMOVED, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("ADR-7 lost its last marker (ADR-0007-domain.md, Status: Accepted)",
                      r.stdout)
