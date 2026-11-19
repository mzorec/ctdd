#!/usr/bin/env python3
"""CTDD resume note (SessionStart hook, `compact` and `resume` sources).

A compaction re-attaches the skills the harness still knows were invoked. That
is not every skill the session invoked: one real change went through two
compactions that each re-attached `ctdd-tests` and not `ctdd-change`, and what
followed ran without it. The red pause came out without its content, no
verification was saved, and step 9 never ran. Reproduced since on one CLI
version: a session that is resumed loses, at its next compaction, every skill
it invoked before the resume, unless an earlier compaction had already carried
that skill through.

So after a compaction this hook says what the conversation can no longer be
trusted to say. It finds the plan the session's tools named last, asks
`check-plan.py --next` where that change stands from the files beside it, and
adds a short note to the compacted context: the plan, its approved revision,
the evidence on disk, the next step, and to invoke `ctdd-change` again before
anything else.

It reads and never writes, and it is silent unless `ctdd-change` ran in this
session: no output when the source is neither `compact` nor `resume`, when the
transcript shows no `ctdd-change` invocation, when no plan is found, when the
change is done, and when anything at all fails. A hook must never break a
session start.

It ships registered in the plugin's `hooks/hooks.json` for both sources. A
resume is where the loss is decided: the resumed session keeps a skill through
its next compaction only if the skill is invoked again after the resume, so
the note on resume asks for exactly that, before any compaction can drop it.
"""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

# For each source the hook answers: when the note was written, and why the
# skill has to be invoked again.
SOURCES = {
    "compact": ("after compaction",
                "A compaction can leave out the ctdd-change skill."),
    "resume": ("on resume",
               "After a resume, the next compaction keeps only the skills invoked again "
               "since the resume."),
}
# Files `check-plan.py --gate` and a saved packet leave beside a plan. They end
# in `.md` and are not plans.
NOT_PLANS = (".gate-shown.md", ".gate-base.md", ".packet.md")
LIMIT = 1500    # characters of note; the harness cuts a hook's context at 10,000

_COMMAND = re.compile(r"<command-name>/?(?:ctdd:)?ctdd-change</command-name>")
_LOADED = re.compile(r"Base directory for this skill: \S*ctdd-change(?![A-Za-z0-9_-])")


def _check_plan():
    """check-plan.py, which owns the plan directory, the revision and --next."""
    path = Path(__file__).resolve().parent.parent / "scripts" / "check-plan.py"
    spec = importlib.util.spec_from_file_location("check_plan_for_resume", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _texts(content):
    """The text a message carries, whether it is a string or a list of blocks."""
    if isinstance(content, str):
        return [content]
    return [c.get("text") or "" for c in content or []
            if isinstance(c, dict) and c.get("type") == "text"]


def invoked(record):
    """True when this transcript record shows `ctdd-change` being invoked: a
    Skill tool call, the slash command, or the skill's text arriving."""
    content = (record.get("message") or {}).get("content")
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("type") == "tool_use" \
                and block.get("name") == "Skill" \
                and (block.get("input") or {}).get("skill") in ("ctdd:ctdd-change",
                                                                "ctdd-change"):
            return True
    return any(_COMMAND.search(t) or _LOADED.search(t) for t in _texts(content))


def _strings(value):
    """Every string inside a tool call's input."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for inner in value.values():
            yield from _strings(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _strings(inner)


def plan_stems(folder):
    """The plans in `folder`, by file name without `.md`."""
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    return [n[:-3] for n in names if n.endswith(".md") and not n.endswith(NOT_PLANS)]


def read_transcript(path, plan_dir, stems):
    """(ctdd-change ran here, the plan its tools named last).

    A plan is found by its stem after the plan directory, not by a path ending
    in `.md`: one session reached its plan only through a shell variable,
    `P=<plan-dir>/<stem>; ... $P.md`, and through the log files beside it.
    Lines are filtered as bytes before any is parsed, because a transcript
    runs to a hundred megabytes.
    """
    ran, last = False, (-1, -1, "")
    slashed = plan_dir.encode("utf-8")
    escaped = plan_dir.replace("/", "\\\\").encode("utf-8")
    finders = [(stem, re.compile(re.escape(plan_dir + "/" + stem) + r"(?![A-Za-z0-9_-])"))
               for stem in stems]
    with open(path, "rb") as fh:
        for n, raw in enumerate(fh):
            about_skill = not ran and b"ctdd-change" in raw
            about_plan = slashed in raw or escaped in raw
            if not (about_skill or about_plan):
                continue
            try:
                record = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            if about_skill and invoked(record):
                ran = True
            if not about_plan:
                continue
            content = (record.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                for text in _strings(block.get("input")):
                    text = text.replace("\\", "/")
                    for stem, finder in finders:
                        for hit in finder.finditer(text):
                            # Two names found at one place are one name and a
                            # longer one that continues it (`orders` where
                            # `orders.v2` is written). The longer sorts after
                            # the shorter, so it is the one kept.
                            last = max(last, (n, hit.start(), stem))
    return ran, last[2] or None


def resume_note(payload):
    """The note for this session start, or None when there is nothing to say."""
    source = SOURCES.get(payload.get("source"))
    if source is None:
        return None
    when, why = source
    cwd = payload.get("cwd") or os.getcwd()
    os.chdir(cwd)       # the plan's path, and the files beside it, are read from here
    check_plan = _check_plan()
    plan_dir = check_plan.plan_dir(cwd)
    stems = plan_stems(os.path.join(cwd, plan_dir))
    if not stems:
        return None     # no plan to find, so the transcript is not read at all
    ran, stem = read_transcript(payload["transcript_path"], plan_dir, stems)
    if not ran or stem is None:
        return None
    plan = f"{plan_dir}/{stem}.md"
    found = check_plan.next_step(plan)
    if found.get("done", True):
        return None     # finished, or `--next` could not read it
    revision, approved = found["revision"], found["approved"]
    if approved is None:
        standing = f"No approval is recorded; the plan is at revision {revision}."
    elif approved == revision:
        standing = f"Approved revision {approved}, and the plan is still that revision."
    else:
        standing = (f"Revision {approved} was approved and the plan is now {revision}: "
                    f"it was amended after approval, so the gate comes first.")
    evidence, nxt = check_plan.next_lines(found)
    head = [
        f"CTDD resume, written by the ctdd plugin {when} from files on disk:",
        f"This session was running ctdd-change for {plan}. {standing}",
        evidence,
    ]
    then = (why + " Before anything else, invoke "
            f"the ctdd:ctdd-change skill with the argument `resume {plan}`, then continue at "
            "the step above; do not start again at step 0. Skill arguments that name a "
            "different plan revision are out of date: the plan file and its approval log "
            "decide.")
    # The instruction is what the note is for, so when the note runs long it
    # is the `Next:` line that gives way, from its end.
    room = LIMIT - sum(len(line) + 1 for line in head) - len(then) - 1
    if len(nxt) > room:
        nxt = nxt[:max(room - 1, 0)].rstrip() + "…"
    return "\n".join(head + [nxt, then])


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
        note = resume_note(payload) if isinstance(payload, dict) else None
    except Exception:
        return 0
    if note:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": note}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
