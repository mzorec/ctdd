#!/usr/bin/env python3
"""CTDD continue (Stop hook, opt-in).

A change made with ctdd stops for the human at a closed list of moments: the
gate, the red pause and the checkpoints of a phased plan, an amendment, a
question or a finding, and the hold-out. Anywhere else, an agent that ends its
turn has stopped for nothing, and the human finds out only when they next
look. Measured over six weeks of real changes, most of the time a change took
was spent waiting on the human, and some dozens of those waits were stops no
rule had asked for.

So when a turn ends, this hook asks `check-plan.py` where the change stands,
from the files beside its plan. If the plan is approved at its current
revision and the next step is the agent's own, it blocks the stop and names
that step. The agent goes on, or it asks what it needs to ask and stops again.

It reads and never writes, and it lets the stop stand, saying nothing, when:

- the harness says a stop hook already continued this turn, or the transcript
  shows this hook already did;
- the session is in plan mode;
- a background task or a scheduled wake-up is pending, which is waiting and
  not stopping;
- the agent's last message asks something or names a finding;
- the turn that is ending edited nothing and ran nothing, as an answer to a
  side question does;
- `ctdd-change` did not run in this session, or no plan is found;
- the change is waiting at one of its stops;
- anything at all fails.

It never approves anything and never answers a question, and a second attempt
to stop always succeeds. Under a phased plan it is silent from the release of
the pause to the saved verification, because the files cannot tell a finished
phase from the middle of one.

It ships opt-in, as the `Stop` entry of `hooks/hooks.json.example`: whatever
`hooks/hooks.json` registers runs in every session that has the plugin on.
"""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

MARK = "CTDD: this change stops only at"
MESSAGE = (MARK + " the gate, a phase checkpoint, an amendment, a question or a finding, "
           "or the hold-out. The plan is approved at its current revision and none of "
           "those applies here. {next} Carry on without waiting. If you do need the human, "
           "ask it as a Decision prompt and stop again.")
# A turn that called none of these edited nothing and ran nothing.
WORK = ("Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell")
# How far up from the end of the agent's last message a question still counts
# as what the message ends on: a printed Decision prompt puts its options, and
# a line saying free text is accepted, under the question.
CLOSING_LINES = 8
# The run states the workflow stops on, in any case, and its token for a claim
# nothing verified, in the workflow's own capitals: "has not run yet" is an
# ordinary sentence of a progress report, and `NOT RUN` is a finding.
_FINDING = re.compile(r"\b(?i:compile red|wrong red|premature green|pin fail\w*|broken pin|"
                      r"weakened green)\b|\bNOT RUN\b")
_DECISION = re.compile(r"(?mi)^[ \t>*_#-]*decision\b")
# What a message quotes and does not say: a fenced block, closed or left open,
# and a code span. A question mark in there is a nullable type or a query
# string, and reports of work in a typed language end on those all the time.
_FENCE = re.compile(r"(?ms)^[ \t]*```.*?^[ \t]*```[ \t]*$|^[ \t]*```.*\Z")
_SPAN = re.compile(r"`[^`\n]*`")
# Bytes read from the end of the transcript to find the turn that is ending,
# doubled until the human's last message is in them, and no further than this.
_TAIL = 1 << 20
_TAIL_MAX = 1 << 26


def _sibling(name, module):
    """A script beside this one, loaded as a module."""
    spec = importlib.util.spec_from_file_location(
        module, Path(__file__).resolve().parent / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def asks(said):
    """True when the agent's last message asks the human something, or names
    one of the states the workflow stops on."""
    said = said or ""
    prose = [_SPAN.sub("", line) for line in _FENCE.sub("", said).splitlines()
             if not line.lstrip().startswith("|")]      # a table row is quoted too
    lines = [line for line in prose if line.strip()]
    closing = "\n".join(lines[-CLOSING_LINES:])
    if "?" in closing:
        return True
    if _DECISION.search(closing):
        return True
    return bool(_FINDING.search(said))


def _records(path, size):
    """(the records in the transcript's last `size` bytes, oldest first;
    whether that reached the start of the file)."""
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        start = max(0, fh.tell() - size)
        fh.seek(start)
        lines = fh.read().split(b"\n")
    records = []
    for raw in lines:
        if not raw.strip():
            continue
        try:
            record = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            continue    # the first line of a window is cut somewhere in its middle
        if isinstance(record, dict):
            records.append(record)
    return records, start == 0


def _texts(content):
    """The text a message carries, whether it is a string or a list of blocks."""
    if isinstance(content, str):
        return [content]
    return [c.get("text") or "" for c in content or []
            if isinstance(c, dict) and c.get("type") == "text"]


def _from_human(record):
    """True for a message the human sent: not a tool's result, not a note the
    harness wrote, not a subagent's."""
    if record.get("type") != "user" or record.get("isMeta") or record.get("isSidechain"):
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list) and any(
            isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
        return False
    return any(text.strip() for text in _texts(content))


def this_turn(path):
    """(worked, pushed, said) for the turn that is ending: whether the agent
    edited or ran anything since the human's last message, whether this hook
    already sent it back to work since then, and the last thing it said."""
    size = _TAIL
    while True:
        records, whole = _records(path, size)
        asked = [n for n, record in enumerate(records) if _from_human(record)]
        if asked or whole or size >= _TAIL_MAX:
            break
        size *= 2
    worked = pushed = False
    said = ""
    for record in records[asked[-1] + 1:] if asked else records:
        if record.get("isSidechain"):
            continue
        content = (record.get("message") or {}).get("content")
        if record.get("type") == "user":
            pushed = pushed or any(MARK in text for text in _texts(content))
        elif record.get("type") == "assistant":
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") in WORK:
                    worked = True
                elif block.get("type") == "text" and (block.get("text") or "").strip():
                    said = block["text"]
    return worked, pushed, said


def decide(payload):
    """The message that sends the agent back to work, or None to let the stop
    stand. The checks run from the cheapest to the dearest."""
    if payload.get("hook_event_name", "Stop") != "Stop":
        return None     # a subagent's stop is not the change's
    if payload.get("stop_hook_active"):
        return None     # one push per stop, never two
    if payload.get("permission_mode") == "plan":
        return None
    if payload.get("background_tasks") or payload.get("session_crons"):
        return None     # waiting on its own work, or on a wake-up it scheduled
    said = payload.get("last_assistant_message")
    if isinstance(said, str) and said.strip() and asks(said):
        return None
    worked, pushed, last_text = this_turn(payload["transcript_path"])
    if pushed:
        return None
    if not (isinstance(said, str) and said.strip()) and asks(last_text):
        return None     # a harness that hands over no last message
    if not worked:
        return None     # an answer to a side question is a finished turn
    cwd = payload.get("cwd") or os.getcwd()
    os.chdir(cwd)       # the plan's path, and the files beside it, are read from here
    resume = _sibling("ctdd-resume.py", "ctdd_resume_for_continue")
    check_plan = resume._check_plan()
    plan_dir = check_plan.plan_dir(cwd)
    stems = resume.plan_stems(os.path.join(cwd, plan_dir))
    if not stems:
        return None     # no plan to find, so the whole transcript is not read at all
    ran, stem = resume.read_transcript(payload["transcript_path"], plan_dir, stems)
    if not ran or stem is None:
        return None
    found = check_plan.next_step(f"{plan_dir}/{stem}.md")
    if found.get("stop") != "none":
        return None     # waiting at one of its stops, or `--next` could not read it
    return MESSAGE.format(next=check_plan.next_lines(found)[1])


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
        message = decide(payload) if isinstance(payload, dict) else None
    except Exception:
        return 0
    if message:
        print(json.dumps({"decision": "block", "reason": message}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
