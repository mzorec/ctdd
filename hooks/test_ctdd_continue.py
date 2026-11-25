#!/usr/bin/env python3
"""Tests for ctdd-continue.py, the Stop hook that sends an agent back to work
when it ends a turn inside an approved change with nothing owed to the human.

Run:  python3 -m unittest hooks.test_ctdd_continue
Stdlib only. Each case builds a throwaway project with a plan folder, leaves
beside the plan what a change has at one point, writes a synthetic transcript
(the record shapes are the harness's; every name in them is made up), runs the
hook as the harness does, with the payload on stdin, and reads back the block
or the silence.

Why the hook exists: the workflow stops for the human at a closed list of
moments, and nothing held an agent to that list. The payload below is the one
a real session handed a stop hook on 2026-11-25, and a block there did
continue the turn.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = str(HERE / "ctdd-continue.py")
NL = chr(10)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The project, the plan fixtures and the transcript records are the ones the
# resume hook's tests use, so the two hooks cannot drift apart on what a
# session looks like.
R = _load("resume_tests_for_continue", HERE / "test_ctdd_resume.py")
F = R.F
SKIP = F.NEXT_PLAN.replace("red pause: pause", "red pause: skip")
PHASED = F.NEXT_PLAN.replace("red pause: pause", "red pause: phased")
MARK = "CTDD: this change stops only at"


def human(text="go on"):
    return R.said(text)


def agent(text):
    return R.said([{"type": "text", "text": text}], role="assistant")


def ran(command="python3 check-plan.py docs/plans/orders.md --next"):
    """A turn's worth of work that also names the plan: one shell command."""
    return R.tool_call(command=command)


def feedback(text):
    """What the harness writes into the transcript when a stop hook blocks."""
    record = R.said("Stop hook feedback:" + NL + text)
    record["isMeta"] = True
    return record


class Case(unittest.TestCase):

    def setUp(self):
        self.p = R.Project(self)

    def stop(self, transcript, project=None, **overrides):
        """Run the hook as the harness does: the payload on stdin, and the
        process started somewhere that is not the project."""
        project = project or self.p
        payload = {"session_id": "0f1e", "transcript_path": transcript,
                   "cwd": str(project.root), "hook_event_name": "Stop",
                   "stop_hook_active": False, "permission_mode": "default",
                   "last_assistant_message": "The pins are written.",
                   "background_tasks": [], "session_crons": [],
                   "effort": {"level": "medium"}, "prompt_id": "0a1b"}
        payload.update(overrides)
        for key in [k for k, v in payload.items() if v is None]:
            del payload[key]
        return subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                              cwd=project.elsewhere, env=R.clean_env(), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60)

    def pushed(self, result):
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(result.stdout.strip(), "expected the agent to be sent back to work, "
                                               "got silence")
        out = json.loads(result.stdout)
        self.assertEqual(["decision", "reason"], sorted(out))
        self.assertEqual("block", out["decision"])
        return out["reason"]

    def assert_silent(self, result):
        self.assertEqual("", result.stdout.strip(), "expected the stop to stand")
        self.assertEqual("", result.stderr.strip())
        self.assertEqual(0, result.returncode)

    def working(self, upto="pins", text=F.NEXT_PLAN, said="The pins are written."):
        """A session that invoked ctdd-change, was told to go on, ran something
        that names the plan, and is now ending its turn."""
        self.p.plan("orders", upto, text)
        return self.p.transcript(R.skill_call(), human(), ran(), agent(said))


class PushTests(Case):
    """The stretches where nothing is owed to the human, so the stop is blocked."""

    def test_between_the_approval_and_the_failing_tests_it_sends_the_agent_on(self):
        reason = self.pushed(self.stop(self.working("pins")))
        self.assertEqual(
            "CTDD: this change stops only at the gate, a phase checkpoint, an amendment, a "
            "question or a finding, or the hold-out. The plan is approved at its current "
            "revision and none of those applies here. Next: 7.9–7.11: write the new-behavior "
            "tests through `ctdd-tests`, run them before implementing, save the run to "
            "orders.redstate.log and verify it with check-redstate. Carry on without waiting. "
            "If you do need the human, ask it as a Decision prompt and stop again.", reason)

    def test_right_after_the_approval_it_sends_the_agent_to_the_pins(self):
        reason = self.pushed(self.stop(self.working("approval")))
        self.assertIn(" Next: 7.5–7.7: write the preservation pins", reason)

    def test_during_implementation_of_a_plan_that_skips_the_pause(self):
        reason = self.pushed(self.stop(self.working("red", SKIP)))
        self.assertIn(" Next: 8: implement what the plan approves, then 8.3:", reason)

    def test_during_implementation_after_a_single_pause_was_released(self):
        reason = self.pushed(self.stop(self.working("release")))
        self.assertIn(" Next: 8: implement what the human released, then 8.3:", reason)

    def test_between_the_saved_verification_and_the_packet(self):
        reason = self.pushed(self.stop(self.working("verify")))
        self.assertIn(" Next: 8.3: re-run the preservation pins", reason)
        reason = self.pushed(self.stop(self.working("pins-after")))
        self.assertIn(" Next: 9: the review packet (9.3", reason)
        self.assertIn("9.1 owes no stop", reason)

    def test_a_holdout_declined_at_the_gate_owes_no_stop_at_step_nine(self):
        """Until 0.61.0 a declined hold-out stopped at 9.1 for a hand check."""
        declined = F.NEXT_HOLDOUT.replace("- result: pending", "- result: declined by human")
        reason = self.pushed(self.stop(self.working("pins-after", declined)))
        self.assertIn(" Next: 9: the review packet (9.3", reason)

    def test_the_block_names_the_plan_the_session_named_last(self):
        self.p.plan("orders", "packet")
        self.p.plan("refunds", "pins")
        t = self.p.transcript(R.skill_call(), human(),
                              ran("python3 check-plan.py docs/plans/orders.md"),
                              ran("python3 check-plan.py docs/plans/refunds.md"),
                              agent("The pins are written."))
        self.assertIn("refunds.redstate.log", self.pushed(self.stop(t)))


class SilenceTests(Case):
    """Every case where the stop stands. Each starts from a state the hook
    would otherwise block, so the one condition under test is what decides."""

    def test_it_pushes_once_and_never_twice(self):
        t = self.working()
        self.pushed(self.stop(t))
        self.assert_silent(self.stop(t, stop_hook_active=True))

    def test_its_own_feedback_in_this_turn_counts_as_the_push(self):
        """The harness's flag is one witness and the transcript is another: a
        stop this hook already blocked is in the turn as its feedback."""
        self.p.plan("orders", "pins")
        t = self.p.transcript(R.skill_call(), human(), ran(), agent("The pins are written."),
                              feedback(MARK + " the gate. Next: 7.9. Carry on."),
                              ran(), agent("Still on it."))
        self.assert_silent(self.stop(t))
        earlier = self.p.transcript(R.skill_call(), human(), ran(), agent("Done."),
                                    feedback(MARK + " the gate. Next: 7.9. Carry on."),
                                    human("thanks, keep going"), ran(),
                                    agent("The pins are written."))
        self.pushed(self.stop(earlier))

    def test_plan_mode_is_left_alone(self):
        t = self.working()
        self.assert_silent(self.stop(t, permission_mode="plan"))
        self.pushed(self.stop(t, permission_mode="acceptEdits"))

    def test_a_pending_background_task_or_wakeup_is_waiting_not_stopping(self):
        t = self.working()
        self.assert_silent(self.stop(t, background_tasks=[{"id": "b1", "type": "shell"}]))
        self.assert_silent(self.stop(t, session_crons=[{"id": "c1"}]))

    def test_a_subagents_stop_is_not_the_changes(self):
        self.assert_silent(self.stop(self.working(), hook_event_name="SubagentStop"))

    def test_a_question_in_the_closing_lines_stands(self):
        t = self.working()
        self.assert_silent(self.stop(t, last_assistant_message=(
            "The repository has two test projects." + NL + NL
            + "Which one should the pins go in?" + NL
            + "1. Shop.Tests (recommended: the handler's tests are there)" + NL
            + "2. Shop.IntegrationTests" + NL + "Free text is fine too.")))

    def test_a_question_far_above_the_closing_lines_does_not(self):
        """A report that opened by quoting the human's question is not asking."""
        report = ["You asked: why two test projects?"] + [f"- step {n} done" for n in range(9)]
        self.pushed(self.stop(self.working(), last_assistant_message=NL.join(report)))

    def test_a_question_mark_in_quoted_code_is_not_a_question(self):
        """A report of work in a typed language ends on nullable types and
        query strings all the time. What a message quotes, in a fenced block,
        a code span or a table row, is not what it says."""
        t = self.working()
        fence = "`" * 3
        for said in (
                "Phase 1 is in. The handler now takes `string? note` and passes it on.",
                "The repository method changed:" + NL + fence + "csharp" + NL
                + "public Task<OrderStateChange> SetStateAsync(int number, string? note)" + NL
                + fence + NL + "The build passes.",
                # No code span here: only being a table row keeps this mark out.
                "Both tests are green." + NL + NL + "| File | Intended change |" + NL
                + "| --- | --- |" + NL + "| Handler.cs | Maps a missing outcome (null?) to 404. |",
                "The diff so far, cut where it gets long:" + NL + fence + "diff" + NL
                + "+    string? note = null;"):
            self.pushed(self.stop(t, last_assistant_message=said))
        self.assert_silent(self.stop(t, last_assistant_message=(
            "The repository method changed:" + NL + fence + "csharp" + NL
            + "public Task SetStateAsync(int number, string? note)" + NL + fence + NL
            + "Should the note be trimmed here or in the handler?")))

    def test_a_printed_decision_prompt_stands_without_a_question_mark(self):
        t = self.working()
        self.assert_silent(self.stop(t, last_assistant_message=(
            "The pins are written." + NL + "**Decision** — where the regression test goes:"
            + NL + "- beside the handler tests" + NL + "- in the integration project")))

    def test_a_named_finding_stands(self):
        t = self.working()
        for said in ("The new test passed before any code was written: premature green.",
                     "currently_accepts_note_of_500 is a broken pin.",
                     "The run is wrong red: it fails on a missing fixture.",
                     "One pin failed after the change: currently_accepts_note_of_500.",
                     "Verification: NOT RUN — the build agent is offline."):
            self.assert_silent(self.stop(t, last_assistant_message=said))

    def test_not_run_is_the_workflows_token_and_not_the_phrase(self):
        """A progress report says what has not run yet in ordinary words. The
        finding is the token the workflow writes, in its capitals."""
        t = self.working()
        self.pushed(self.stop(t, last_assistant_message=(
            "The pins are written. The whole suite has not run yet: it waits for the last "
            "phase.")))
        self.assert_silent(self.stop(t, last_assistant_message=(
            "The pins are written. Contract validator: NOT RUN — no validator is "
            "configured.")))

    def test_with_no_last_message_in_the_payload_the_transcript_is_asked(self):
        self.pushed(self.stop(self.working(), last_assistant_message=None))
        asking = self.working(said="Which test project should the pins go in?")
        self.assert_silent(self.stop(asking, last_assistant_message=None))

    def test_a_turn_that_edited_nothing_and_ran_nothing_stands(self):
        """An answer to a side question is a finished turn, however much work
        came before the question."""
        self.p.plan("orders", "pins")
        answer = self.p.transcript(
            R.skill_call(), human(), ran(), agent("The pins are written."),
            human("what does the second pin cover"),
            R.tool_call("Read", file_path="tests/a_tests.cs"),
            agent("It covers a note of exactly 500 characters."))
        self.assert_silent(self.stop(answer))
        worked = self.p.transcript(
            R.skill_call(), human(), ran(), agent("The pins are written."),
            human("what does the second pin cover"),
            R.tool_call("Edit", file_path="tests/a_tests.cs", old_string="a", new_string="b"),
            agent("It covers a note of exactly 500 characters, and I renamed it."))
        self.pushed(self.stop(worked))

    def test_a_tool_result_is_not_the_humans_message(self):
        """A tool's result arrives as a user record, and the harness can attach
        a note of its own to it as text. Taking that for the turn's start would
        hide the work done before it. The first version of this test had no
        text beside the result, and passed with the condition deleted."""
        self.p.plan("orders", "pins")
        result = {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_02", "content": "ok"},
            {"type": "text", "text": "<system-reminder>The task list has not been updated "
                                     "recently.</system-reminder>"}]}}
        t = self.p.transcript(R.skill_call(), human(), ran(), result,
                              agent("The pins are written."))
        self.pushed(self.stop(t))

    def test_a_subagents_records_are_not_the_turns(self):
        """Older transcripts hold a subagent's records beside the session's own,
        marked as a side chain. Its prompt is not the human's message, and what
        it ran is not what the agent ran."""
        self.p.plan("orders", "pins")
        prompt = R.said("Find where notes are validated.")
        prompt["isSidechain"] = True
        t = self.p.transcript(R.skill_call(), human(), ran(), prompt,
                              agent("The pins are written."))
        self.pushed(self.stop(t))
        search = R.tool_call(command="grep -rn note src/")
        search["isSidechain"] = True
        t = self.p.transcript(R.skill_call(), human(), ran(), agent("The pins are written."),
                              human("where are notes validated"), search,
                              agent("In the command validator."))
        self.assert_silent(self.stop(t))

    def test_a_session_that_never_ran_ctdd_change_stands(self):
        self.p.plan("orders", "pins")
        t = self.p.transcript(human(), ran(), agent("The pins are written."))
        self.assert_silent(self.stop(t))
        t = self.p.transcript(R.skill_call("ctdd:ctdd-tests"), human(), ran(),
                              agent("The pins are written."))
        self.assert_silent(self.stop(t))

    def test_with_no_plan_to_find_it_stands(self):
        self.p.plan("orders", "pins")
        t = self.p.transcript(R.skill_call(), human(), ran("dotnet build"),
                              agent("It builds."))
        self.assert_silent(self.stop(t))
        empty = R.Project(self)
        t = empty.transcript(R.skill_call(), human(), ran(), agent("It builds."))
        self.assert_silent(self.stop(t, project=empty))

    def test_at_the_gate_it_stands(self):
        self.assert_silent(self.stop(self.working(None)))
        t = self.working("red")
        self.p.put("orders.md", F.with_amendment(
            F.NEXT_PLAN.replace("500 pass", "500 and fewer pass"),
            "- A1. Old: 500 pass. New: 500 and fewer pass."))
        self.assert_silent(self.stop(t))
        t = self.working("red")
        self.p.put("orders.md", F.NEXT_PLAN.replace(
            "BLOCKING — I will not guess: none — answered before approval" + NL, ""))
        self.assert_silent(self.stop(t))

    def test_at_the_red_pause_it_stands(self):
        self.assert_silent(self.stop(self.working("red")))
        self.assert_silent(self.stop(self.working("intended")))

    def test_during_a_phased_implementation_it_stands(self):
        """The files cannot tell a finished phase from the middle of one, so a
        checkpoint and a needless stop look the same, and the hook is silent."""
        t = self.working("release", PHASED)
        self.assert_silent(self.stop(t))
        with open(self.p.root / "docs" / "plans" / "orders.approval.log", "a",
                  encoding="utf-8", newline=NL) as fh:
            fh.write('Phase 3 released by: "all of them"' + NL)
        self.assert_silent(self.stop(t))
        self.pushed(self.stop(self.working("verify", PHASED)))

    def test_at_a_holdout_that_still_waits_it_stands(self):
        self.assert_silent(self.stop(self.working("pins-after", F.NEXT_HOLDOUT)))

    def test_at_the_handover_it_stands(self):
        self.assert_silent(self.stop(self.working("packet")))

    def test_anything_that_fails_is_silence(self):
        self.p.plan("orders", "pins")
        self.assert_silent(self.stop(str(self.p.root / "no-such-transcript.jsonl")))
        self.assert_silent(self.stop(self.working(), cwd=str(self.p.root / "no-such-folder")))
        for raw in ("not json", "[1, 2]", ""):
            r = subprocess.run([sys.executable, HOOK], input=raw, cwd=self.p.elsewhere,
                               env=R.clean_env(), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=60)
            self.assert_silent(r)

    def test_it_writes_nothing(self):
        t = self.working()
        folder = self.p.root / "docs" / "plans"
        before = {f.name: f.read_bytes() for f in folder.iterdir()}
        self.pushed(self.stop(t))
        self.assertEqual(before, {f.name: f.read_bytes() for f in folder.iterdir()})


class TurnTests(unittest.TestCase):
    """The turn is found from the end of the transcript, which runs to a
    hundred megabytes: these read it in this process with the tail shortened."""

    def setUp(self):
        self.hook = _load("ctdd_continue_under_test", HOOK)
        self.p = R.Project(self)

    def test_a_long_turn_is_read_back_to_the_humans_message(self):
        filler = [R.tool_call("Read", file_path=f"src/file{n}.cs") for n in range(400)]
        t = self.p.transcript(R.skill_call(), human(), ran(), *filler, agent("Done."))
        self.hook._TAIL = 2000
        self.assertEqual((True, False, "Done."), self.hook.this_turn(t))

    def test_past_the_limit_the_window_is_the_turn(self):
        """A turn longer than the limit is a long autonomous one. What the
        window holds is judged as the turn, never the whole file re-read."""
        early = [ran()] + [R.tool_call("Read", file_path=f"src/file{n}.cs") for n in range(400)]
        t = self.p.transcript(R.skill_call(), human(), *early, agent("Done."))
        self.hook._TAIL = self.hook._TAIL_MAX = 2000
        worked, pushed, said = self.hook.this_turn(t)
        self.assertEqual((False, False, "Done."), (worked, pushed, said))


class RegistrationTests(unittest.TestCase):
    """The hook is opt-in: it is in the example files and not in the
    `hooks/hooks.json` every session with the plugin on loads."""

    def example(self, name):
        text = (HERE / name).read_text(encoding="utf-8")
        body = NL.join(l for l in text.split(NL) if not l.lstrip().startswith("#"))
        return json.loads(body)

    def test_it_is_not_registered_for_every_session(self):
        config = json.loads((HERE / "hooks.json").read_text(encoding="utf-8"))
        self.assertNotIn("Stop", config["hooks"])
        self.assertNotIn("ctdd-continue", json.dumps(config))

    def test_both_example_files_offer_it_on_stop(self):
        for name in ("hooks.json.example", "hooks.windows.json.example"):
            entries = self.example(name)["hooks"].get("Stop")
            self.assertIsNotNone(entries, f"{name} has no Stop entry")
            self.assertEqual(1, len(entries), name)
            hook = entries[0]["hooks"][0]
            self.assertEqual("command", hook["type"], name)
            self.assertIn('"${CLAUDE_PLUGIN_ROOT}/hooks/ctdd-continue.py"', hook["command"], name)
            self.assertNotIn("matcher", entries[0], f"{name}: a Stop hook takes no matcher")

    def test_the_example_command_reaches_the_script(self):
        """Claude Code runs a hook's command in a shell, so it is run here the
        same way, with this interpreter standing in for the launcher."""
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("no bash to run the hook's command through")
        command = self.example("hooks.json.example")["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertTrue(command.startswith("python3 "), command)
        command = ('"' + Path(sys.executable).as_posix() + '" ' + command[len("python3 "):]) \
            .replace("${CLAUDE_PLUGIN_ROOT}", HERE.parent.as_posix())
        p = R.Project(self)
        p.plan("orders", "pins")
        t = p.transcript(R.skill_call(), human(), ran(), agent("The pins are written."))
        payload = {"transcript_path": t, "cwd": str(p.root), "hook_event_name": "Stop",
                   "stop_hook_active": False, "permission_mode": "default",
                   "last_assistant_message": "The pins are written."}
        r = subprocess.run([bash, "-c", command], input=json.dumps(payload),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, env=R.clean_env())
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertEqual("block", json.loads(r.stdout)["decision"])


if __name__ == "__main__":
    unittest.main()
