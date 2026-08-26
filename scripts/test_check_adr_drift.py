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
