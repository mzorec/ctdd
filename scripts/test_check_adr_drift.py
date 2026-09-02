"""Tests for check-adr-drift.py."""

import importlib.util
import os
import pathlib
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
