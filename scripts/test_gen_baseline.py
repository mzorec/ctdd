#!/usr/bin/env python3
"""Tests for gen-baseline.py — step 0 made mechanical.

Run:  python3 scripts/test_gen_baseline.py   (or via pytest)
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "gen-baseline.py")
SKILL = Path(__file__).resolve().parents[1] / "skills" / "ctdd-change"


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {r.stderr}")
    return r.stdout.strip()


def run(repo, *args):
    return subprocess.run([sys.executable, SCRIPT, "--repo", str(repo), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


class BaselineTestCase(unittest.TestCase):
    """A real git repo per test. Nothing here mocks git: the whole point of the
    script is that it agrees with git, so a fake would test the wrong thing."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        git(self.dir, "init", "-q", "-b", "main")
        git(self.dir, "config", "user.email", "t@example.com")
        git(self.dir, "config", "user.name", "T")
        self.write("seed.txt", "seed")
        git(self.dir, "add", "seed.txt")
        git(self.dir, "commit", "-q", "-m", "seed")

    def write(self, rel, text="x"):
        p = Path(self.dir) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def fields(self, out):
        """Parse the Baseline line the way the format intends: split on `; `.

        The first version of this helper used `name=([^;.]+)[;.]` and every
        filename broke it — `staged=staged.txt` returned `staged`. That is not
        only a test bug: `diff-base` is read out of this line by a person or an
        agent on the way to four later commands, so the line has to survive an
        obvious parse. It does, on `; `, which is why that is what is used here.
        """
        line = [l for l in out.split("\n") if l.startswith("Baseline:")]
        self.assertEqual(len(line), 1, f"expected one Baseline line in: {out!r}")
        body = line[0][len("Baseline:"):].strip()
        if body.endswith("."):
            body = body[:-1]
        parsed = {}
        for part in body.split("; "):
            self.assertIn("=", part, f"unparseable field {part!r}")
            key, value = part.split("=", 1)
            parsed[key.strip()] = value.strip()
        return parsed

    def field(self, out, name):
        parsed = self.fields(out)
        self.assertIn(name, parsed, f"no `{name}` field in: {out!r}")
        return parsed[name]


class ResolutionTests(BaselineTestCase):

    def test_on_the_target_branch_the_base_is_head_and_it_says_so(self):
        """0.2's first half, and 0.1's report. Working straight on the default
        branch is legitimate for uncommitted work and is also how a change lands
        on main by accident, so it is stated rather than left to be inferred
        from `diff-base=HEAD`."""
        r = run(self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.field(r.stdout, "diff-base"), "HEAD")
        self.assertIn("the current branch IS the target", r.stdout)
        self.assertIn("only uncommitted work is in scope", r.stdout)

    def test_off_the_target_branch_the_base_is_the_merge_base(self):
        """0.2's second half. HEAD would scope the diff to uncommitted work and
        make every commit on the branch invisible to `--git <diff-base>`."""
        git(self.dir, "checkout", "-q", "-b", "feature/x")
        self.write("a.txt", "a")
        git(self.dir, "add", "a.txt")
        git(self.dir, "commit", "-q", "-m", "work")
        expected = git(self.dir, "merge-base", "main", "HEAD")[:7]
        r = run(self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.field(r.stdout, "diff-base"), expected)
        self.assertEqual(self.field(r.stdout, "branch"), "feature/x")
        self.assertNotIn("the current branch IS the target", r.stdout)

    def test_a_remote_prefixed_target_still_counts_as_the_same_branch(self):
        """`main` and `origin/main` are one branch to a person and two strings to
        `==`. The first version compared them directly, so on the common setup —
        target inferred from `origin/HEAD` — the on-target report never fired and
        working directly on the default branch went unsaid."""
        git(self.dir, "checkout", "-q", "-b", "other")
        r = run(self.dir, "--target", "other")
        self.assertIn("the current branch IS the target", r.stdout)
        # and the prefix-stripping must not over-match
        git(self.dir, "checkout", "-q", "-b", "release/main")
        r = run(self.dir, "--target", "main")
        self.assertNotIn("the current branch IS the target", r.stdout,
                         "`release/main` is not `main`")

    def test_an_absent_target_is_the_humans_decision_not_a_default(self):
        """0.3. The tempting failure is to fall back to HEAD, which answers a
        question nobody asked and scopes every later check to uncommitted work."""
        r = run(self.dir, "--target", "no-such-branch")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("yours to choose", r.stdout)
        self.assertIn("no-such-branch", r.stdout)
        self.assertNotIn("Baseline:", r.stdout, "nothing may be claimed on exit 1")

    def test_two_default_looking_branches_are_disputed_not_tie_broken(self):
        """0.3's `disputed`. Picking `main` silently would be wrong exactly when
        the repository is mid-rename, which is when it matters."""
        git(self.dir, "branch", "master")
        r = run(self.dir)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("candidates:", r.stdout)
        self.assertIn("main", r.stdout)
        self.assertIn("master", r.stdout)
        self.assertNotIn("Baseline:", r.stdout)

    def test_unrelated_histories_have_no_base_and_say_so(self):
        """0.3's third case. A missing merge-base papered over with HEAD would
        make every later `--git <diff-base>` read the whole branch as the change."""
        git(self.dir, "checkout", "-q", "--orphan", "detached-history")
        git(self.dir, "rm", "-q", "-rf", ".")
        self.write("only.txt", "only")
        git(self.dir, "add", "only.txt")
        git(self.dir, "commit", "-q", "-m", "unrelated")
        r = run(self.dir, "--target", "main")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("no merge-base", r.stdout)
        self.assertNotIn("Baseline:", r.stdout)

    def test_a_detached_head_is_reported_rather_than_guessed(self):
        head = git(self.dir, "rev-parse", "HEAD")
        git(self.dir, "checkout", "-q", head)
        r = run(self.dir, "--target", "main")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("detached", r.stdout)
        self.assertEqual(self.field(r.stdout, "branch"), "(detached)")


class WorktreeTests(BaselineTestCase):

    def test_staged_unstaged_and_untracked_are_classified_separately(self):
        """One file can be in two of them at once — staged, then edited again —
        and the fields have to say so, because 7.1 re-checks the tree against
        exactly this snapshot."""
        self.write("staged.txt", "s")
        git(self.dir, "add", "staged.txt")
        self.write("seed.txt", "edited")
        self.write("new.txt", "n")
        r = run(self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("staged.txt", self.field(r.stdout, "staged"))
        self.assertIn("seed.txt", self.field(r.stdout, "unstaged"))
        self.assertIn("new.txt", self.field(r.stdout, "untracked"))

    def test_a_file_staged_then_edited_again_appears_in_both_lanes(self):
        self.write("both.txt", "one")
        git(self.dir, "add", "both.txt")
        self.write("both.txt", "two")
        r = run(self.dir)
        self.assertIn("both.txt", self.field(r.stdout, "staged"))
        self.assertIn("both.txt", self.field(r.stdout, "unstaged"))

    def test_a_clean_tree_reads_none_not_empty(self):
        """`staged=` with nothing after it is ambiguous with a parse failure."""
        r = run(self.dir)
        for lane in ("staged", "unstaged", "untracked"):
            self.assertEqual(self.field(r.stdout, lane), "none")

    def test_a_rename_reports_the_path_that_now_exists(self):
        git(self.dir, "mv", "seed.txt", "renamed.txt")
        r = run(self.dir)
        self.assertIn("renamed.txt", self.field(r.stdout, "staged"))

    def test_many_files_are_capped_so_the_later_fields_stay_readable(self):
        """The fields after the file lists are the ones later steps read. An
        unbounded list pushes `diff-base` off a terminal, which is the field
        four checks take as an argument."""
        for i in range(9):
            self.write(f"f{i}.txt", "x")
        r = run(self.dir)
        untracked = self.field(r.stdout, "untracked")
        self.assertIn("more", untracked, untracked)
        self.assertLess(len(untracked), 120, untracked)
        self.assertEqual(self.field(r.stdout, "diff-base"), "HEAD",
                         "the capped field must not swallow the ones after it")


class ContractTests(BaselineTestCase):
    """The script's output and the skill's Output contract are one shape. Two
    places stating it is how the format drifts; the check is here so a change to
    either fails."""

    def test_the_line_matches_the_output_contract_field_by_field(self):
        row = [l for l in (SKILL / "SKILL.md").read_text(encoding="utf-8").split("\n")
               if l.startswith("| Pre-plan statements")]
        self.assertEqual(len(row), 1, "the Pre-plan statements row moved")
        declared = re.findall(r"(\w[\w-]*)=<", row[0])
        self.assertGreaterEqual(len(declared), 6, f"contract parsed as {declared}")
        r = run(self.dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        line = [l for l in r.stdout.split("\n") if l.startswith("Baseline:")]
        self.assertEqual(len(line), 1, "exactly one Baseline line")
        emitted = re.findall(r"(\w[\w-]*)=", line[0])
        self.assertEqual(emitted, declared,
                         "the script emits different fields, or a different order, "
                         "than the Output contract declares")
        self.assertTrue(line[0].endswith("."), "the contract ends the statement with a period")

    def test_the_line_survives_an_obvious_parse_with_dotted_filenames(self):
        """Every field value here contains a `.`, which is the ordinary case and
        the one that breaks a naive `[^;.]+` split. `diff-base` is read off this
        line on the way to four later commands, so the parse has to hold."""
        self.write("a.b.txt", "x")
        git(self.dir, "add", "a.b.txt")
        self.write("seed.txt", "edited")
        self.write("un.tracked.md", "x")
        parsed = self.fields(run(self.dir).stdout)
        self.assertEqual(parsed["staged"], "a.b.txt")
        self.assertEqual(parsed["unstaged"], "seed.txt")
        self.assertEqual(parsed["untracked"], "un.tracked.md")
        self.assertEqual(parsed["diff-base"], "HEAD")

    def test_the_worked_example_baseline_parses_the_same_way(self):
        """The example is what an agent copies, so it has to be a real specimen
        of what the script prints, not a paraphrase of it."""
        wc = (SKILL / "references" / "worked-change.md").read_text(encoding="utf-8")
        line = [l for l in wc.split("\n") if l.startswith("Baseline:")]
        self.assertEqual(len(line), 1, "the worked example lost its Baseline line")
        r = run(self.dir)
        self.assertEqual(re.findall(r"(\w[\w-]*)=", line[0]),
                         re.findall(r"(\w[\w-]*)=",
                                    [l for l in r.stdout.split("\n")
                                     if l.startswith("Baseline:")][0]),
                         "the worked example and the script disagree on the fields")


class UsageTests(BaselineTestCase):

    def test_outside_a_checkout_it_blocks_rather_than_defaulting(self):
        """Exit 2 is `unverified` everywhere else in this plugin, and step 0
        having no answer must stop the workflow, not start it on a guess."""
        plain = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, plain, ignore_errors=True)
        r = run(plain)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertNotIn("Baseline:", r.stdout)

    def test_an_unknown_argument_is_a_usage_error_not_a_silent_default(self):
        r = subprocess.run([sys.executable, SCRIPT, "--targat", "main"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Baseline:", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
