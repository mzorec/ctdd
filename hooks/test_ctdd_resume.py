#!/usr/bin/env python3
"""Tests for ctdd-resume.py, the SessionStart hook that speaks after a
compaction.

Run:  python3 -m unittest hooks.test_ctdd_resume
Stdlib only. Each case builds a throwaway project with a plan folder, writes a
synthetic transcript (the record shapes are the harness's; every name in them
is made up), runs the hook as the harness does, with the payload on stdin, and
reads back the note or the silence.

Why the hook exists: one real change went through two compactions that each
re-attached another skill and not `ctdd-change`. What followed ran without the
skill: the red pause had no content, no verification was saved, step 9 never
ran. The files beside the plan still said where the change stood.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = str(HERE / "ctdd-resume.py")
CHECK_PLAN = str(HERE.parent / "scripts" / "check-plan.py")
NL = chr(10)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The plan fixture and the runner lines that verify its lanes are the ones the
# `--next` tests use, so the two suites cannot drift apart on what a plan is.
F = _load("plan_fixtures_for_resume", HERE.parent / "scripts" / "test_check_plan.py")
STEPS = ("approval", "pins", "red", "prered", "intended", "release", "verify", "pins-after",
         "packet")
INVOKE = "invoke the ctdd:ctdd-change skill with the argument `resume "


def clean_env():
    env = dict(os.environ)
    for var in ("CTDD_LAYERS", "CTDD_HARNESSES", "CTDD_PLAN_DIR", "CLAUDE_PROJECT_DIR"):
        env.pop(var, None)
    return env


def skill_call(name="ctdd:ctdd-change"):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "toolu_01", "name": "Skill",
         "input": {"skill": name, "args": "Add the order-state endpoint."}}]}}


def tool_call(tool="Bash", **inputs):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "Checking."},
        {"type": "tool_use", "id": "toolu_02", "name": tool, "input": inputs}]}}


def said(text, role="user"):
    return {"type": role, "message": {"role": role, "content": text}}


class Project:
    """A throwaway repository root with a plan folder."""

    def __init__(self, test, plan_dir="docs/plans"):
        self.root = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, str(self.root), True)
        self.plan_dir = plan_dir
        (self.root / plan_dir).mkdir(parents=True)
        self.elsewhere = tempfile.mkdtemp()
        test.addCleanup(shutil.rmtree, self.elsewhere, True)

    def put(self, name, text):
        (self.root / self.plan_dir / name).write_text(text, encoding="utf-8", newline=NL)

    def plan(self, stem, upto, text=F.NEXT_PLAN):
        """Leave on disk what a change has once every step up to and including
        `upto` is done. Returns the approved revision, when there is one."""
        self.put(stem + ".md", text)
        done = STEPS[:STEPS.index(upto) + 1] if upto else ()
        rev = None
        if "approval" in done:
            gate = subprocess.run(
                [sys.executable, CHECK_PLAN, f"{self.plan_dir}/{stem}.md", "--gate"],
                cwd=str(self.root), env=clean_env(), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60)
            rev = re.search(r"plan revision ([0-9a-f]{12})", gate.stdout).group(1)
            tok = re.search(r"Gate token: ([0-9a-f]{8})", gate.stdout).group(1)
            self.put(stem + ".approval.log",
                     f'Approved by: "approve" (typed at the gate); plan: '
                     f'{self.plan_dir}/{stem}.md@{rev}; gate-token: {tok}' + NL)
        if "pins" in done:
            self.put(stem + ".pinstate.log", F.PIN_GREEN)
        if "red" in done:
            self.put(stem + ".redstate.log", F.NEW_RED)
        if "prered" in done:
            self.put(stem + ".prered.diff", "diff --git a/tests/a_tests.cs b/tests/a_tests.cs" + NL)
        if "intended" in done:
            self.put(stem + ".md", text + F.INTENDED)
        if "release" in done:
            with open(self.root / self.plan_dir / (stem + ".approval.log"), "a",
                      encoding="utf-8", newline=NL) as fh:
                fh.write(F.RELEASE + NL)
        if "verify" in done:
            self.put(stem + ".verify.log", "build: ok" + NL)
        if "pins-after" in done:
            self.put(stem + ".pinstate-after.log", F.PIN_GREEN)
        if "packet" in done:
            self.put(stem + ".packet.md", "Business requirement: the order-state endpoint" + NL)
        return rev

    def transcript(self, *records, raw=()):
        path = self.root / "session.jsonl"
        lines = [json.dumps(r) for r in records] + list(raw)
        path.write_text("".join(line + NL for line in lines), encoding="utf-8", newline=NL)
        return str(path)

    def hook(self, transcript, source="compact", **overrides):
        """Run the hook as the harness does: the payload on stdin, and the
        process started somewhere that is not the project."""
        payload = {"session_id": "0f1e", "transcript_path": transcript,
                   "cwd": str(self.root), "hook_event_name": "SessionStart",
                   "source": source}
        payload.update(overrides)
        return subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                              cwd=self.elsewhere, env=clean_env(), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60)


class ResumeNoteTests(unittest.TestCase):

    def setUp(self):
        self.p = Project(self)

    def note(self, result):
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(result.stdout.strip(), "expected a note, got silence")
        out = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(["additionalContext", "hookEventName"], sorted(out))
        self.assertEqual("SessionStart", out["hookEventName"])
        return out["additionalContext"]

    def assert_silent(self, result):
        self.assertEqual("", result.stdout.strip(), "expected silence")
        self.assertEqual("", result.stderr.strip())
        self.assertEqual(0, result.returncode)

    def running(self, stem="orders", upto="red", **how):
        """A session that invoked ctdd-change and checked this plan."""
        rev = self.p.plan(stem, upto, **how)
        t = self.p.transcript(
            skill_call(),
            tool_call(command=f"python3 check-plan.py docs/plans/{stem}.md --gate"))
        return rev, t

    # ------------------------------------------------------------ the note
    def test_after_red_state_it_names_the_pause_and_says_to_invoke_the_skill(self):
        rev, t = self.running()
        lines = self.note(self.p.hook(t)).split(NL)
        self.assertEqual(
            "CTDD resume, written by the ctdd plugin after compaction from files on disk:",
            lines[0])
        self.assertEqual(
            f"This session was running ctdd-change for docs/plans/orders.md. Approved "
            f"revision {rev}, and the plan is still that revision.", lines[1])
        self.assertTrue(lines[2].startswith(f"Evidence: plan ✓ · approval ✓ {rev} · "), lines[2])
        self.assertTrue(lines[3].startswith("Next: 7.12: print the pause and stop for the "
                                            "release"), lines[3])
        self.assertTrue(lines[4].startswith(
            "A compaction can leave out the ctdd-change skill. Before anything else, invoke"),
            lines[4])
        self.assertIn(INVOKE + "docs/plans/orders.md`", lines[4])
        self.assertIn("do not start again at step 0", lines[4])
        self.assertIn("Skill arguments that name a different plan revision are out of date: "
                      "the plan file and its approval log decide.", lines[4])
        self.assertEqual(5, len(lines))

    def test_a_plan_amended_after_approval_is_sent_to_the_gate(self):
        old, t = self.running()
        self.p.put("orders.md", F.with_amendment(
            F.NEXT_PLAN.replace("500 pass", "500 and fewer pass"),
            "- A1. Old: 500 pass. New: 500 and fewer pass."))
        note = self.note(self.p.hook(t))
        self.assertIn(f"Revision {old} was approved and the plan is now ", note)
        self.assertIn("it was amended after approval, so the gate comes first.", note)
        self.assertIn(NL + "Next: 6: the gate.", note)

    def test_a_plan_never_approved_is_said_to_have_no_approval(self):
        _rev, t = self.running(upto=None)
        note = self.note(self.p.hook(t))
        self.assertIn("No approval is recorded; the plan is at revision ", note)
        self.assertIn(NL + "Next: 6: the gate.", note)

    def test_on_resume_it_says_so_and_why_the_skill_must_be_invoked_again(self):
        """A resume is where the loss is decided: the resumed session keeps a
        skill through its next compaction only if it is invoked again after the
        resume. A note that blamed a compaction would be wrong about why."""
        _rev, t = self.running()
        lines = self.note(self.p.hook(t, source="resume")).split(NL)
        self.assertEqual(
            "CTDD resume, written by the ctdd plugin on resume from files on disk:", lines[0])
        self.assertTrue(lines[-1].startswith(
            "After a resume, the next compaction keeps only the skills invoked again since "
            "the resume. Before anything else, invoke"), lines[-1])
        self.assertNotIn("A compaction can leave out", lines[-1])
        self.assertIn(INVOKE + "docs/plans/orders.md`", lines[-1])

    def test_a_long_note_keeps_the_instruction_and_shortens_the_next_line(self):
        """Run in this process with the limit lowered, because a plan name long
        enough to pass 1,500 characters makes paths beside it that Windows
        refuses."""
        _rev, t = self.running(upto="pins-after")
        os.remove(self.p.root / "docs" / "plans" / "orders.pinstate.log")
        os.remove(self.p.root / "docs" / "plans" / "orders.verify.log")
        hook = _load("resume_hook_in_process", HOOK)
        self.assertEqual(1500, hook.LIMIT, "the README promises at most 1,500 characters")
        hook.LIMIT = 900
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        note = hook.resume_note({"source": "compact", "transcript_path": t,
                                 "cwd": str(self.p.root)})
        self.assertLessEqual(len(note), 900)
        self.assertTrue(note.endswith("the plan file and its approval log decide."), note[-80:])
        self.assertIn(INVOKE + "docs/plans/orders.md`", note)
        nxt = [line for line in note.split(NL) if line.startswith("Next: ")][0]
        self.assertTrue(nxt.startswith("Next: 7.5–7.7: write the preservation pins"), nxt)
        self.assertTrue(nxt.endswith("…"), nxt)

    def test_an_ordinary_note_is_not_shortened(self):
        _rev, t = self.running(upto="pins-after")
        os.remove(self.p.root / "docs" / "plans" / "orders.verify.log")
        note = self.note(self.p.hook(t))
        self.assertLessEqual(len(note), 1500)
        self.assertIn("Out of order: pins after is already there." + NL, note)

    # ------------------------------------------------------- when it is silent
    def test_a_session_that_never_invoked_ctdd_change_gets_nothing(self):
        self.p.plan("orders", "red")
        t = self.p.transcript(
            skill_call("ctdd:ctdd-tests"),
            said("Please use ctdd-change for this."),
            tool_call(command="python3 check-plan.py docs/plans/orders.md"))
        self.assert_silent(self.p.hook(t))

    def test_a_session_start_that_is_not_a_compaction_gets_nothing(self):
        _rev, t = self.running()
        for source in ("startup", "clear", "fork", None):
            self.assert_silent(self.p.hook(t, source=source))
        # In this process as well: run as a hook, anything that raises also
        # ends in silence, so the process alone cannot show that the source is
        # what decided it. A deletion probe found exactly that.
        hook = _load("resume_hook_for_sources", HOOK)
        for source in ("startup", "clear", "fork", None):
            self.assertIsNone(hook.resume_note({"source": source, "transcript_path": t,
                                                "cwd": str(self.p.root)}), source)

    def test_a_finished_change_gets_nothing(self):
        _rev, t = self.running(upto="packet")
        self.assert_silent(self.p.hook(t))
        # Named last through its saved packet, it is still that finished plan
        # and not a plan called `orders.packet`.
        t = self.p.transcript(skill_call(), tool_call(
            "Read", file_path="docs/plans/orders.packet.md"))
        self.assert_silent(self.p.hook(t))

    def test_a_file_whose_name_only_starts_like_a_plan_is_not_that_plan(self):
        self.p.plan("orders", "red")
        self.p.put("orders-draft.txt", "notes" + NL)
        t = self.p.transcript(skill_call(), tool_call(
            "Read", file_path="docs/plans/orders-draft.txt"))
        self.assert_silent(self.p.hook(t))

    def test_no_plan_named_by_a_tool_gets_nothing(self):
        """A path in something the human typed, or in a tool's output, is not
        the plan this session was working on."""
        self.p.plan("orders", "red")
        t = self.p.transcript(
            skill_call(),
            said("Continue with docs/plans/orders.md please."),
            {"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_02",
                 "content": "docs/plans/orders.md"}]}})
        self.assert_silent(self.p.hook(t))

    def test_nothing_it_cannot_read_breaks_a_session_start(self):
        _rev, t = self.running()
        self.assert_silent(self.p.hook(str(self.p.root / "no-such-transcript.jsonl")))
        self.assert_silent(self.p.hook(t, cwd=str(self.p.root / "no-such-folder")))
        self.assert_silent(self.p.hook(None))
        shutil.rmtree(self.p.root / "docs")
        self.assert_silent(self.p.hook(t))
        for garbage in ("", "not json {", "[]", '"compact"'):
            r = subprocess.run([sys.executable, HOOK], input=garbage, capture_output=True,
                               text=True, encoding="utf-8", timeout=60, env=clean_env(),
                               cwd=self.p.elsewhere)
            self.assert_silent(r)

    def test_lines_that_are_not_records_are_skipped(self):
        self.p.plan("orders", "red")
        t = self.p.transcript(
            skill_call(), tool_call(command="cat docs/plans/orders.md"),
            raw=['{"type": "assistant", "message": {"content": [{"type": "tool_use", '
                 '"name": "Bash", "input": {"command": "cat docs/plans/orders.md"',
                 '"ctdd-change docs/plans/orders"', "[1, 2]", "ctdd-change"])
        self.assertIn("Next: 7.12", self.note(self.p.hook(t)))

    def test_settings_that_cannot_be_read_get_nothing(self):
        _rev, t = self.running()
        (self.p.root / ".ctdd.json").write_text('{"planDir": "docs/plans",}', encoding="utf-8")
        self.assert_silent(self.p.hook(t))

    def test_it_writes_nothing(self):
        _rev, t = self.running()
        folder = self.p.root / "docs" / "plans"
        before = {f.name: f.read_bytes() for f in folder.iterdir()}
        self.note(self.p.hook(t))
        self.assertEqual(before, {f.name: f.read_bytes() for f in folder.iterdir()})
        self.assertEqual(["docs", "session.jsonl"], sorted(f.name for f in self.p.root.iterdir()))

    # ------------------------------------------- what counts as an invocation
    def test_each_way_the_skill_starts_counts(self):
        self.p.plan("orders", "red")
        check = tool_call(command="python3 check-plan.py docs/plans/orders.md")
        for label, record in (
                ("the Skill tool", skill_call("ctdd:ctdd-change")),
                ("the Skill tool, bare name", skill_call("ctdd-change")),
                ("the slash command",
                 said("<command-name>/ctdd:ctdd-change</command-name>" + NL
                      + "<command-args>add the endpoint</command-args>")),
                ("the skill's text arriving",
                 {"type": "user", "message": {"role": "user", "content": [
                     {"type": "text", "text": "Base directory for this skill: "
                                              "/home/dev/plugins/ctdd/skills/ctdd-change"
                                              + NL + NL + "# CTDD: drive a backend change"}]}})):
            self.assertIn("Next: 7.12", self.note(self.p.hook(self.p.transcript(record, check))),
                          label)

    def test_another_skill_or_a_mention_does_not(self):
        self.p.plan("orders", "red")
        check = tool_call(command="python3 check-plan.py docs/plans/orders.md")
        for label, record in (
                ("another skill", skill_call("ctdd:ctdd-tests")),
                ("a skill whose name only starts the same", skill_call("ctdd:ctdd-change-log")),
                ("another skill's text",
                 said("Base directory for this skill: /plugins/ctdd/skills/ctdd-change-log")),
                ("the name in a tool's arguments",
                 tool_call(command="grep -r ctdd-change skills/")),
                ("the name in prose", said("ctdd-change would be the skill for this."))):
            self.assert_silent(self.p.hook(self.p.transcript(record, check)))

    # ------------------------------------------------------- finding the plan
    def test_a_plan_reached_only_through_a_shell_variable_is_found(self):
        self.p.plan("orders", "red")
        t = self.p.transcript(skill_call(), tool_call(
            command="P=docs/plans/orders; python3 check-plan.py $P.md --approval $P.approval.log"))
        self.assertIn("for docs/plans/orders.md.", self.note(self.p.hook(t)))

    def test_a_plan_named_only_by_a_file_beside_it_is_found(self):
        self.p.plan("orders", "red")
        t = self.p.transcript(skill_call(), tool_call(
            "Read", file_path=str(self.p.root / "docs" / "plans" / "orders.redstate.log")))
        self.assertIn("for docs/plans/orders.md.", self.note(self.p.hook(t)))

    def test_a_windows_path_names_the_plan(self):
        self.p.plan("orders", "red")
        t = self.p.transcript(skill_call(), tool_call(
            "Read", file_path="C:\\work\\shop\\docs\\plans\\orders.md"))
        self.assertIn("for docs/plans/orders.md.", self.note(self.p.hook(t)))

    def test_of_two_plans_the_one_named_last_wins(self):
        self.p.plan("orders", "red")
        self.p.plan("refunds", "pins")
        first = tool_call(command="python3 check-plan.py docs/plans/orders.md")
        second = tool_call(command="python3 check-plan.py docs/plans/refunds.md")
        note = self.note(self.p.hook(self.p.transcript(skill_call(), first, second)))
        self.assertIn("for docs/plans/refunds.md.", note)
        self.assertIn("Next: 7.9–7.11", note)
        note = self.note(self.p.hook(self.p.transcript(skill_call(), second, first)))
        self.assertIn("for docs/plans/orders.md.", note)
        both = tool_call(command="diff docs/plans/refunds.md docs/plans/orders.md")
        self.assertIn("for docs/plans/orders.md.",
                      self.note(self.p.hook(self.p.transcript(skill_call(), both))))

    def test_a_plan_whose_name_starts_another_is_not_mistaken_for_it(self):
        self.p.plan("orders", "pins")
        self.p.plan("orders-v2", "red")
        self.p.plan("orders.v3", "red")
        for stem, step in (("orders-v2", "7.12"), ("orders.v3", "7.12"), ("orders", "7.9–7.11")):
            t = self.p.transcript(skill_call(), tool_call(
                command=f"python3 check-plan.py docs/plans/{stem}.md"))
            note = self.note(self.p.hook(t))
            self.assertIn(f"for docs/plans/{stem}.md.", note, stem)
            self.assertIn("Next: " + step, note, stem)

    def test_the_files_a_gate_leaves_are_not_plans(self):
        """`<name>.gate-shown.md` ends in `.md` and is the plan as it was shown."""
        self.p.plan("orders", "red")
        folder = self.p.root / "docs" / "plans"
        self.assertTrue((folder / "orders.gate-shown.md").exists())
        t = self.p.transcript(skill_call(), tool_call(
            "Read", file_path="docs/plans/orders.gate-shown.md"))
        self.assertIn("for docs/plans/orders.md.", self.note(self.p.hook(t)))

    def test_the_plan_folder_the_settings_name_is_the_one_read(self):
        p = Project(self, plan_dir="plans")
        (p.root / ".ctdd.json").write_text('{"planDir": "plans"}', encoding="utf-8")
        p.plan("orders", "red")
        t = p.transcript(skill_call(), tool_call(command="python3 check-plan.py plans/orders.md"))
        self.assertIn("for plans/orders.md.", self.note(p.hook(t)))


class RegistrationTests(unittest.TestCase):
    """`hooks/hooks.json`, which is what makes the note run wherever the
    plugin is enabled. Claude Code runs a hook's command in a shell, so the
    command is run here the same way, through bash."""

    def setUp(self):
        self.config = json.loads((HERE / "hooks.json").read_text(encoding="utf-8"))
        self.bash = shutil.which("bash")

    def entry(self):
        entries = self.config["hooks"]["SessionStart"]
        self.assertEqual(1, len(entries), entries)
        return entries[0]

    def command(self, **swap):
        text = self.entry()["hooks"][0]["command"]
        for old, new in swap.items():
            text = text.replace(old, new)
        return text.replace("${CLAUDE_PLUGIN_ROOT}", HERE.parent.as_posix())

    def shell(self, command, payload):
        if not self.bash:
            self.skipTest("no bash to run the hook's command through")
        return subprocess.run([self.bash, "-c", command], input=json.dumps(payload),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60, env=clean_env())

    def test_it_runs_after_a_compaction_and_after_a_resume(self):
        self.assertEqual({"compact", "resume"}, set(self.entry()["matcher"].split("|")))
        hook = self.entry()["hooks"][0]
        self.assertEqual("command", hook["type"])
        self.assertIn('"${CLAUDE_PLUGIN_ROOT}/hooks/ctdd-resume.py"', hook["command"])

    def test_the_spec_edit_guard_stays_off(self):
        """The README says it is opt-in, and its reminders fire on every edit."""
        self.assertEqual(["SessionStart"], sorted(self.config["hooks"]))

    def test_the_command_reaches_the_script(self):
        p = Project(self)
        p.plan("orders", "red")
        t = p.transcript(skill_call(), tool_call(command="python3 check-plan.py docs/plans/orders.md"))
        r = self.shell(self.command(), {"source": "compact", "transcript_path": t,
                                        "cwd": str(p.root), "hook_event_name": "SessionStart"})
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertTrue(r.stdout.strip(), "the command printed nothing: it never reached the "
                                          "script, and its `|| true` hid that")
        note = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("for docs/plans/orders.md.", note)

    def test_with_no_python_it_says_nothing_and_succeeds(self):
        """Every install runs this command, and a machine with no working
        launcher must not get an error, or a launcher's message in the model's
        context, at every compaction and resume. A dead `python3` stub writes
        its message to stderr and exits non-zero."""
        dead = self.command(**{"py -3": "no-such-launcher-for-ctdd -3",
                               "python3": "no-such-python-for-ctdd"})
        r = self.shell(dead, {"source": "compact"})
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertEqual("", r.stdout)
        self.assertEqual("", r.stderr)
        stub = self.command(**{"py -3": "no-such-launcher-for-ctdd -3",
                               "python3": "sh -c 'echo stub >&2; exit 49'"})
        r = self.shell(stub, {"source": "compact"})
        self.assertEqual((0, "", ""), (r.returncode, r.stdout, r.stderr))


if __name__ == "__main__":
    unittest.main(verbosity=2)
