#!/usr/bin/env python3
"""check-plan.py — lints a CTDD implementation plan for its mandatory sections.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" plan.md
    <plan text> | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" -
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" plan.md --diff surface.txt
    echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" - --diff surface.txt
    echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" - --from-description --diff surface.txt
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" plan.md --gate
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" plan.md --next

--next says where a change stands, from the files alone: the plan, its
approval log and the evidence steps 7 and 8 save beside it, each judged by the
checker the workflow already uses for it. It prints one `Evidence:` line and
one `Next:` line naming the first step whose evidence is missing; it runs no
test and writes nothing. One real session lost the skill's text at a
compaction and went on without the red pause's content, without a saved
verification and without step 9. This is what a hook, or a person, reads to
pick a change up where it is. Exit 0 = a next step is named, or the change is
done; 1 = the plan fails its checks or was amended since approval; 2 = it
cannot run.

--gate emits the step 6.1 gate presentation from the plan file, after every
check has passed and never for a plan that fails one: the path and derived
tier, the decision summary verbatim, the categorical line, then `Hold-out`,
`Behavior flow`, `Known gaps`, `Assumptions`, `Uncovered or ambiguous` and the
altitude table, each in full and read from the approved region. It exists
because the alternative is the agent retyping them, and in one real session it
did that at eleven consecutive gates and compressed every one — a seven-step
flow became a prose arrow, the hold-out's nine fields became a sentence. Copy
the block into your reply unaltered: running this command is not showing its
output, which lands in a tool result the human may never expand. A summary of
it is the defect.

After an amendment --gate prints a delta block instead: the entries recorded
under `Amendments` and `Decisions confirmed in session` since the revision the
approval log last names (before any approval: since the last plan printed in
full), every gate-visible part that changed, a line naming the parts that did
not, and whether the tests - their names and `covers:` lines - are unchanged,
which is what grants the lighter lane. --full forces the whole block. To have
something to compare with, --gate keeps two copies of the plan beside it,
`<name>.gate-shown.md` and `<name>.gate-base.md`, and, while the plan has no
approval yet, `<name>.gate-dirty.txt`: what git reports changed or untracked
before this change wrote anything, which `check-spec-surface.py --plan` reads.
They are the only files this script writes. Under the block it prints the
Approval record line to append.

--approval verifies the approval record against the current revision, and
refuses a plan that still asks a BLOCKING question, as --post-approval does.

Placement. With `layers` named in `.ctdd.json`, lowest first, a new-behavior
test must sit at the layer of the file that turns it green. With `harnesses`
named too, lightest first, a test in a heavier harness must carry a `- needs:`
line saying what it reaches there, wherever a lighter project of the same
layer sits on disk beside its own. The altitude table prints the reason.

--from-description keeps CI and the runtime pointing at the SAME artifact. The
skill writes the canonical plan to docs/plans/<name>.md and puts a pointer in
the MR description; without this mode CI would validate the description
instead — which can reject an MR that correctly points at a valid plan, or
bless a stale copy pasted into the description, recreating the two-plan drift
the runtime exists to prevent. With it the chain is consistent:
skill writes the plan file -> MR points at it -> review reads it -> CI validates it.

The description carries one line:  CTDD-Plan: docs/plans/PAY-123-partial-capture.md
A trivial change instead carries its visible  Risk: trivial - <reason>  line,
which is validated directly against the diff.

Honest scope: this is an omission detector, not a quality gate. It verifies
the required sections EXIST — it cannot tell a considered "Hold-out: not
required — semantics unchanged" from a lazy one. That judgment stays human.
What it converts is silent omission into visible omission: a plan can no
longer simply not mention NFR budgets or the hold-out decision.

The one claim it CAN contradict mechanically is triviality. A declared
trivial skip is exempt from the section checks — but when a
`git diff --name-status -M` output is supplied via --diff, the claim is
cross-checked against the spec surface (test/contract patterns shared with
check-spec-surface.py and the spec-edit hook, env overrides included):
touched test or contract surface contradicts "trivial" and fails, whatever
the narration says. This is the deterministic counterweight the skills point
at — an edit to an existing test or a contract file is never trivial.
A diff that only *adds* a test is reported distinctly: that is the
compressed bug-fix lane (short plan), not the trivial lane. A diff that
changes `.ctdd.json` contradicts it too: that file decides what the
cross-check calls surface.

Settings. `.ctdd.json` is read before anything else. A file that cannot be
read, or a key this plugin reads holding a value it cannot, stops the run:
`layers`, `harnesses`, `planDir` and the surface patterns would otherwise
fall back to their defaults and every check would pass on them. A key this
plugin does not read is named on stderr and ignored.

Exit 0 = plan OK (sections present, or a trivial claim that survived the check).
Exit 1 = sections missing, or a trivial claim contradicted by the diff.
Exit 2 = usage or input error, or a settings file that cannot be read.
"""

import contextlib
import importlib.util
import hashlib
import io
import os
import re
import sys
from pathlib import Path

REQUIRED = [
    # EVERY pattern is anchored to the start of a line. Unanchored ones matched the
# category word anywhere in prose, so a paragraph merely *mentioning* existing
# behaviour, assumptions, contract changes and hold-outs passed as though all of
# them were present sections. Anchored to the start of a line: the earlier bare patterns matched the words
    # anywhere in the document, so prose like "nothing here is blocking and I am
    # proceeding unless something breaks" satisfied both buckets without either
    # heading existing. A presence detector that matches prose is not detecting
    # presence of the thing it names.
    ("decision summary: BLOCKING",  r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*blocking\b"),

    ("decision summary: proceeding", r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*proceed(ing)?\s+unless\b"),
    ("risk level",            r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*risk\s*(level)?\s*[:—-]"),
    ("existing behavior",     r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*existing\s+behaviou?r\b"),
    # v0.41.0: the flow narrative. A plan carried behavior as one `Intended
    # behavior` sentence plus test bullets, so the reader at the gate could not
    # reconstruct the runtime sequence or see how it changes. Three anchored
    # patterns, not one: finding #39 is the standing evidence that a subheading
    # required by format prose alone is a subheading plans omit and the gate
    # never misses.
    ("behavior flow",         r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*behaviou?r\s+flow\b"),
    ("current flow",          r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*current\s+flow\b"),
    ("flow after change",     r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*flow\s+after\s+change\b"),
    ("assumptions",           r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*assumptions?\b"),
    ("uncovered/ambiguous",   r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*(uncovered|ambiguous)\b"),
    # Both test headings, always — even when one is empty. One pattern used to
    # cover the whole section, so a plan with a single heading passed the gate and
    # then had no correct lane at step 7: the default check reads pins as new
    # tests and blocks falsely, while --expect-pass finds no pin section and exits
    # on a usage error. Finding #39 made both headings mandatory in the format
    # prose only, so the gate stayed silent and the failure surfaced after
    # approval, after the tests were written. Line-anchored like the buckets.
    ("proposed tests: new-behavior heading",
     r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*new[- ]behaviou?r\s+tests?\b"),
    ("proposed tests: preservation-pin heading",
     r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*preservation\s+pins?\b"),
    # The v0.22.0 format made seven more sections mandatory ("omit only the sections
    # marked conditional") without extending this list, so a plan missing all of
    # them exited 0 and step 5 read that as validation. Presence, not quality — but
    # a presence detector that stops covering the format it detects has stopped
    # being one. Every pattern below is line-anchored for the same reason as above.
    ("business requirement",  r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*business\s+requirement\b"),
    ("intended behavior",     r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*intended\s+behaviou?r\b"),
    ("known gaps",            r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*known\s+gaps?\b"),
    ("case coverage not reached", r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*case\s+coverage\s+not\s+reached\b"),
    ("implementation slices", r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*implementation\s+slices?\b"),
    ("verification",          r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*verification\b"),
    ("residual risk",         r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*residual\s+risks?\b"),
    ("contract changes",      r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*contract\s+changes?\b"),
    ("NFR budgets",           r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*(nfr|budget)"),
    ("hold-out decision",     r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*hold.?out\b"),
    ("files to change",       r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*files\s+(likely\s+)?to\s+change\b"),
    # Intent-born, 2026-11: the owner asked that the first gate show structure.
    # In one real change the human first saw type names, ports, folders and
    # test projects at the 7.12 pause, after twenty-nine tests and every stub
    # existed, and questioned each in turn: four amendments, four gates and a
    # second pass over every test file followed. No bullet prefix: `structure`
    # is an ordinary word, and a bullet opening with it is not this section.
    ("structure",             r"^\s*(?:#{1,6}\s+)?[`*_]*structure\b"),
]

# The keys above are internal, and two of them name no heading a plan has: a
# real run reported `MISSING sections … decision summary: BLOCKING` after a
# compaction dropped the `BLOCKING - I will not guess` heading, and the agent
# had to read this file to learn what to restore. Messages print the heading.
_SHOWN = {
    "decision summary: BLOCKING": "BLOCKING — I will not guess",
    "decision summary: proceeding": "Proceeding unless you object",
}


def heading_of(name):
    return _SHOWN.get(name, name)


# Reason must sit on the SAME line as the risk call: with re.S a bare
# "Risk: trivial —\n" would let the next section masquerade as the reason.
# Line-anchored, like every other REQUIRED pattern. Unanchored, the word
# `trivial` anywhere skipped every section, duplicate, tier and hold-out
# check — including inside the mandatory `Residual risk` section, which is
# reachable by writing the format correctly, and in prose describing the
# lane. Steps 3.7 and 8.6 are the workflow's own routes for putting
# withdrawn trivial wording into a plan file.
TRIVIAL = re.compile(r"^\s*[`*_]*risk\s*(level)?\s*[:—-]\s*trivial\b[^\n]{3,}",
                     re.I | re.M)

# --- Plan tiers -------------------------------------------------------------
# The 2026-07-27 Flik change produced a 31,448-character plan: 3,166 words, ~14
# minutes to read at the gate, 5.8x the canonical example. The format had one
# gear, and closing the "no diff exists" triviality hole in v0.23.0 routed every
# fresh change into it. A gate a human skims is a gate that does not gate
# (finding #30 is the standing evidence for what gets skipped when it is
# expensive).
#
# The tier is DERIVED, never self-declared: it is a function of the categorical
# line and the new-behavior heading the plan already writes, both of which this
# checker already reads. Declaring `small` while carrying a contract delta is
# not possible, because nothing is declared.
_CONTRACT_NONE = re.compile(r"contract\s*[:=]\s*none\b", re.I)
_HIGH_RISK = re.compile(r"risk\s*(level)?\s*[:—-]\s*high-risk\b", re.I)
# The categorical line, matched without assuming field order. The old pattern
# required `contract:` before `hold-out:`, so a plan that ordered those fields
# differently was not recognised as categorical and was counted as a second
# `risk level` section — a DUPLICATED error naming a section that does not
# exist, which step 5.4's "re-run until it exits 0" cannot converge on because
# plan-format never ordered the fields.
CATEGORICAL_LINE = re.compile(
    r"^\s*[`*_]*risk\s*[:—-].*?(?:contract\s*:|hold.?out\s*:)", re.I)


def strip_fences(text):
    """Blank out fenced-code content, keeping line numbering intact.

    Every pattern here is line-anchored but none was context-aware, so a plan
    quoting a withdrawn declaration, a worked example or a superseded amendment
    inside a fence had that text read as live. `Risk: trivial` in a fence skipped
    all nineteen checks; the format's own worked example is fenced, so quoting it
    was enough.
    """
    out, fenced = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    return "\n".join(out)


def categorical_line(text):
    """The one line the tier, triviality and hold-out reads must come from.

    Every one of those three read the whole document with an unanchored pattern,
    so a stray `contract: none` in prose downgraded the tier, an `hold-out:` in a
    superseded amendment won over the real declaration, and the word `trivial`
    anywhere — including inside the mandatory `Residual risk` section — skipped
    every section, duplicate, tier and hold-out check.
    """
    for line in text.splitlines():
        if CATEGORICAL_LINE.search(line):
            return line
    return ""
# The block ended on a blank line or end-of-document, so in a plan written
# without blank lines it ran to EOF and swallowed every later section — any
# stray `options:` or `recommended:` anywhere below satisfied the actionability
# check, including `rollout options:` and `recommended: none needed` in the very
# last line. End it at the next section-shaped line instead.
HOLDOUT_BLOCK = re.compile(
    r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*hold.?out\b"
    r"(?:\n(?:[ \t]+\S|[-*]\s)[^\n]*|[^\n]*)*",
    re.I | re.M)
# The skeleton uses an em dash as a field separator elsewhere, so accept it
# here: `hold-out — required: 2 sealed tests` silently read as no field at
# all, which switched the actionability check off.
_HOLDOUT_FIELD = re.compile(r"hold.?out\s*[:=—–-]\s*([^\n·|]*)", re.I)
_DECISION_FIELD = re.compile(r"^\s*[-*]\s*[`*_]*decision[`*_]*\s*:", re.I | re.M)


def holdout_block(text):
    """The `Hold-out` section's block, or None.

    The first line opening with `hold-out` used to be taken, wherever it was. A
    real plan recorded `- Hold-out: declined by human.` under its decisions,
    and that bullet became the hold-out: the actionability check reported
    `options:` and `recommended:` missing from a section that had both, the
    gate printed the bullet, and the revision normalised the wrong `result:`.
    The section is the block that carries the format's `- decision:` field;
    without one anywhere, an unbulleted label beats a bullet, and only then
    the first match. The actionability check, the revision and the gate all
    read this one function.
    """
    found = list(HOLDOUT_BLOCK.finditer(text))
    for m in found:
        if _DECISION_FIELD.search(m.group(0)):
            return m
    for m in found:
        if not re.match(r"\s*[-*]\s", m.group(0)):
            return m
    return found[0] if found else None


def _first_line(text, m):
    """The line index of a match's first non-blank character. Patterns opening
    `^\\s*` under MULTILINE can begin on a blank line above."""
    g = m.group(0)
    return text.count(chr(10), 0, m.start() + len(g) - len(g.lstrip()))


# 7.12 mandates appending the intended-change table to the plan as
# `## Intended change`, "dating it after approval - a record of what will be
# built, never part of what was approved", and rules 7 and 8 mandate replacing
# the hold-out `result:` and `human-verified expected values:` before the
# packet. All three are post-approval by the skill's own instruction, and the
# digest covered every byte - so obeying the skill invalidated the approval it
# had just recorded. Two real changes each spent a turn writing a note
# explaining that nothing approved had changed. The prose is the side with
# stated intent, so the digest follows it: one of the two statements had to be
# wrong, and "never part of what was approved" is the deliberate one.
#
# Values are NORMALISED, not dropped. The label stays in the digested text, so
# an edit to the LABEL still reports STALE, which dropping the lines
# outright would hide: these rules mandate replacing the VALUE, not
# rewriting the field, and an agent regenerating the block can easily
# emit a different casing or bullet. Deletion and duplication are caught
# either way, because the blank line left behind is itself a difference -
# two probes were vacuous before the real distinguishing case was found,
# so the justification here is the one the tests actually establish. Excluding the whole line would have made the digest
# blind to a deletion, which is the wrong trade for a check whose entire job
# is detecting post-approval edits.
_POST_APPROVAL_VALUE = (
    re.compile(r"^(\s*(?:[-*]\s+)?[`*_]*human.verified\s+expected\s+values"
               r"[`*_]*\s*:).*$", re.I | re.M),
    re.compile(r"^(\s*(?:[-*]\s+)?[`*_]*result[`*_]*\s*:).*$", re.I | re.M),
)
_INTENDED_CHANGE = re.compile(
    r"^(#{1,6}\s*[`*_]*intended\s+change\b).*\Z", re.I | re.M | re.S)


def _untailed(text):
    """The plan without its post-approval `## Intended change` tail, hold-out
    values left as written. The gate presentation reads this: it must not
    print the tail as though the approval covered it, and it must print the
    hold-out's `result:` and expected values, which `approved_region` blanks
    so that replacing them does not move the revision. Reading that region
    for display printed both fields empty at ten consecutive gates of one
    change, after a decline whose whole point was the listed values."""
    m = _INTENDED_CHANGE.search(text)
    # Heading included, unlike the hold-out fields `approved_region` keeps.
    # Those lines exist at approval time, so their labels are approved and
    # keeping them makes a deletion visible. This section does not exist at
    # approval time at all - 7.12 appends it afterwards - so retaining the
    # heading would mean the mandated append still moved the revision, which
    # is the whole contradiction. `hidden_in_intended_change` carries the risk.
    return text[:m.start()] if m else text


def approved_region(text):
    """The plan text the approval covers, with post-approval content normalised.

    Both digest call sites use this. They must: computing one over the raw text
    and the other over this would make every plan read stale, which is the
    one-definition rule (CLAUDE.md rule 2) applied to a second pair.
    """
    text = _untailed(text)
    hb = holdout_block(text)
    if hb:
        block = hb.group(0)
        for rx in _POST_APPROVAL_VALUE:
            block = rx.sub(lambda mm: mm.group(1), block)
        text = text[:hb.start()] + block + text[hb.end():]
    # 7.12 appends the section, so the append also introduces the blank-line
    # separator before its heading. Without normalising the tail that separator
    # alone moved the revision and the mandated append still read STALE - the
    # defect surviving its own fix, one newline wide.
    return text.rstrip() + chr(10)


def plan_revision(text):
    """The 12-hex revision the Approval record and the packet carry."""
    return hashlib.sha256(
        approved_region(text).encode("utf-8")).hexdigest()[:12]


def gate_token(revision):
    """The eight hex characters `--gate` prints inside the presentation block
    and the Approval record must carry back.

    Derived from the plan revision, so it needs no stored state and any later
    run can recompute it: same plan, same token; amended plan, new token. Its
    only job is to leave a trace that the block was actually put in front of
    the human. This script can already see that a record names the right
    revision - but a revision is printed by every run, so an agent that never
    copied the presentation can still quote one. The token appears ONLY inside
    the block, so a record carrying it is evidence the block was rendered
    somewhere a human could read it. That is traceability, not proof: an agent
    determined to fake it can compute the same digest. It closes the accident,
    not the lie.
    """
    return hashlib.sha256(
        ("ctdd-gate:" + revision).encode("utf-8")).hexdigest()[:8]


def hidden_in_intended_change(text, required):
    """Required section headings sitting in the un-approved tail.

    `## Intended change` runs to EOF because 7.12 appends it and, under
    `phased`, its body carries `## Phase N` headings of its own - so bounding
    it at the next heading would leave those inside the digest and defeat the
    exemption. The cost is that anything appended after it is also exempt, so
    check the one thing that would matter: a mandatory section cannot live
    where the approval does not reach.
    """
    m = _INTENDED_CHANGE.search(text)
    if not m:
        return []
    tail = m.group(0)[len(m.group(1)):]
    return [name for name, pat in required
            if re.search(pat, tail, re.IGNORECASE | re.MULTILINE)]


def _holdout_required(text):
    r"""The categorical line reads `hold-out: <not required | required: ...>`.

    A regex looking for the word `required` matches `not required` too, and a
    negative lookahead does not help because `\s*` backtracks to zero width and
    steps over it. Read the field and look at what it starts with.
    """
    m = _HOLDOUT_FIELD.search(categorical_line(text) or text)
    return bool(m) and m.group(1).strip().lower().startswith("required")
_NEW_BEHAVIOUR_NONE = re.compile(
    r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*new[- ]behavio(?:u)?r\s+tests?\b[^\n]*?"
    r":\s*none\b", re.I | re.MULTILINE)

SMALL_SECTIONS = {
    "decision summary: BLOCKING", "decision summary: proceeding", "risk level",
    "existing behavior", "proposed tests: new-behavior heading",
    "proposed tests: preservation-pin heading", "verification", "files to change",
    # The guardrail calls the business requirement the source of intent and step
    # 9.2 back-translates against it, so dropping it below `large` gated the modal
    # case on a plan that never said what it was for. Every bug fix lands at
    # `medium` by construction: 5.3 requires the regression test be named, so the
    # new-behavior heading is never `none` and the small tier is unreachable.
    "business requirement", "intended behavior",
}
MEDIUM_SECTIONS = SMALL_SECTIONS | {
    "assumptions", "uncovered/ambiguous", "implementation slices",
    "hold-out decision", "residual risk",
    # All three flow headings, or the medium tier re-derives the finding-#39
    # shape: the parent heading present, the two blocks the reader actually
    # compares silently absent.
    "behavior flow", "current flow", "flow after change",
    # Wherever a plan has new behaviour to place, it has structure to show.
    "structure",
}


# The same heading prefix every REQUIRED pattern allows: a plan writing its
# sections as `## New-behavior tests` or `- Preservation pins` is well formed.
# Omitting it here meant a cosmetic markdown choice decided whether a plan
# declaring zero tests in both lanes derived `small` — reopening the hole the
# guard below was written to close, through the guard's own regex.
_HEADING = r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*"

_LANE_NONE = {
    "new-behavior": re.compile(
        _HEADING + r"new[- ]behavio(?:u)?r\s+tests?\b[^\n]*?:\s*none\b", re.I | re.M),
    "preservation": re.compile(
        _HEADING + r"preservation\s+pins?\b[^\n]*?:\s*none\b", re.I | re.M),
}


_LANE_HEADING = {
    "new-behavior": re.compile(
        _HEADING + r"new[- ]behavio(?:u)?r\s+tests?\b", re.I | re.M),
    "preservation": re.compile(
        _HEADING + r"preservation\s+pins?\b", re.I | re.M),
}

# Any identifier-shaped token is a name; a length floor rejected short test
# names and would have re-derived the tier from a stylistic choice, which is
# the class of bug this predicate exists to close.
# `none` is a declaration, not an identifier. Reading it as a test name made this
# guard reject the form plan-format rule 4 MANDATES (`Preservation pins: none —
# <reason>`) while accepting `- none — <reason>` as a named test — the same
# inversion the guard was written to close, reintroduced through the guard.
_NOT_A_NAME = {"none", "n", "na", "tbd", "todo", "nothing"}
# A test name is an identifier: no spaces before its separator. `- We will add
# coverage once the shape settles.` matched `We`, so a sentence in an evidence
# lane passed the gate at 19 of 19 and step 8 then could not be entered.
_BULLET_NAME = re.compile(
    r"^\s*[-*]\s+[`'\"]?([A-Za-z_][\w.\-]*)[`'\"]?\s*(?:[—–:(]|\s-\s|$)", re.M)


def _bullet_names_a_test(line):
    m = _BULLET_NAME.match(line)
    if not m:
        return False
    return m.group(1).replace("/", "").lower() not in _NOT_A_NAME


def _names_a_test(text):
    """True when either evidence lane actually names a test.

    This inferred "a test exists" from the *absence* of the word `none`, so the
    tier inverted: an honest `New-behavior tests: none — pure refactor` derived
    large, while headings left empty with no test named anywhere derived medium
    and passed at 15 of 19. The guard was defeated by deleting a word, and the
    agent that noticed was rewarded for the less honest plan. Look for names.
    """
    lines = text.split("\n")
    for rx in _LANE_HEADING.values():
        for n, line in enumerate(lines):
            if not rx.search(line):
                continue
            if re.search(r":\s*none\b", line, re.I):
                break
            for follow in lines[n + 1:]:
                if not follow.strip():
                    continue
                if not follow.lstrip().startswith(("-", "*")):
                    break
                if _bullet_names_a_test(follow):
                    return True
            break
    return False

# ---------------------------------------------------------------- altitude
# Every test's level follows from which production file turns it green, and
# `Implementation slices` already carries that link as `turns green:`. A real
# plan wrote it three times for nineteen tests, by wildcard - "every
# `Discovery_*` test" - so nothing made the author say, per test, who owns the
# behaviour. The agent's own diagnosis once the human asked: "my slices never
# said who owns the batch bound; altitude follows ownership, so leaving
# ownership vague left the altitude arbitrary." Several plans in a row needed
# that question asked by hand after the plan was written. Two prose fixes
# (v0.48.0's guardrail and the reachability rewrite of the altitude row) did
# not stop it, so the question is asked here, of every test, before the gate.
#
# Reuses this file's own lane walker rather than importing check-redstate's
# extractor, which has three recorded fail-silent defects and reads a path
# rather than text. One definition of "the tests a lane names" in this file.
_TURNS_GREEN = re.compile(r"turns\s+green\s*:", re.I)
_TICK = re.compile(r"`([^`\n]+)`")
_PATH_SUB = re.compile(r"^\s+[-*]\s+path\s*:\s*`([^`\n]+)`", re.I)


def _lane_block(text, lane):
    """The lines under one evidence-lane heading: bullets, their indented
    continuations and interior blanks, ending at the next unindented
    non-bullet line. `<lane>: none` yields nothing."""
    lines = text.split("\n")
    rx = _LANE_HEADING[lane]
    for n, line in enumerate(lines):
        if not rx.search(line):
            continue
        if re.search(r":\s*none\b", line, re.I):
            return []
        block = []
        for follow in lines[n + 1:]:
            if not follow.strip():
                block.append(follow)
                continue
            if follow[:1].isspace() or follow.lstrip().startswith(("-", "*")):
                block.append(follow)
                continue
            break
        return block
    return []


def lane_tests(text, lane):
    """[(name, path or None)] for every test the lane names, in order. Only an
    unindented bullet names a test; `  - path:` is read as that test's path."""
    out = []
    for line in _lane_block(text, lane):
        if not line.strip():
            continue
        if not line[:1].isspace() and _bullet_names_a_test(line):
            out.append([_BULLET_NAME.match(line).group(1), None])
            continue
        m = _PATH_SUB.match(line)
        if m and out and out[-1][1] is None:
            out[-1][1] = m.group(1).strip()
    return [(n, p) for n, p in out]


def _bullet_section(text, name):
    """A section's heading line plus its bullets, their indented
    continuations and blank lines, ending at the next unindented line that is
    not a bullet. Empty when the plan has no such heading."""
    lines = text.split("\n")
    pat = dict(REQUIRED + _EXTRA_BOUNDARIES)[name]
    start = next((n for n, l in enumerate(lines) if re.match(pat, l, re.I)), None)
    if start is None:
        return []
    block = [lines[start]]
    for line in lines[start + 1:]:
        # Table rows belong to the section too: a file list written as a table
        # would otherwise end the section at its header row and go unchecked.
        if line.strip() and not line[:1].isspace() \
                and not line.lstrip().startswith(("-", "*", "|")):
            break
        block.append(line)
    return block


_PATH_LINE = re.compile(r"^\s*[-*]\s+[`*_]*path[`*_]*\s*:", re.I)
_INVARIANTS = re.compile(r"^\s*[-*]\s+[`*_]*invariants[`*_]*\s*:", re.I)


def _file_listings(text):
    """The parts of a plan that list files, where field rule 9 applies:
    `Files likely to change`, `Implementation slices`, `Contract changes`,
    `Colocated notes`, and every `path:` line. Scanning the whole document
    failed a real plan twice for prose - directory names in an amendment's
    account of a move, and a method signature - and the first repair replaced
    exact folder names with vaguer words, which is the opposite of what rule 9
    is for. `## Intended change` is deliberately not read: it is written after
    approval, and check-spec-surface already accepts its rows abbreviated
    (`App/.../Foo.cs`) to fit the column, which the whole-document scan
    rejected as a `...`."""
    out = []
    for name in ("files to change", "implementation slices", "contract changes",
                 "colocated notes"):
        out += _bullet_section(text, name)
    out += [l for l in text.split("\n") if _PATH_LINE.match(l)]
    return "\n".join(out)


def slice_claims(text):
    """([(owner_path, [exact test names])], [(owner, clause, wildcards)]).

    The second list is every `turns green:` clause that names no backticked
    test or names one by wildcard. Those are rejected, not expanded: expanding
    "every `Discovery_*` test" would hide exactly the vagueness this exists to
    surface. Rule 9's exactness for paths applies to the tests a slice claims.
    """
    lines = text.split("\n")
    pat = dict(REQUIRED)["implementation slices"]
    start = next((n for n, l in enumerate(lines) if re.match(pat, l, re.I)), None)
    if start is None:
        return [], []
    bullets, cur = [], None
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        if not line[:1].isspace() and line.lstrip().startswith(("-", "*")):
            cur = [line]
            bullets.append(cur)
            continue
        if line[:1].isspace() and cur is not None:
            cur.append(line)
            continue
        break
    claims, bad = [], []
    for b in bullets:
        joined = " ".join(l.strip() for l in b)
        m = _TURNS_GREEN.search(joined)
        if not m:
            continue
        ticks = _TICK.findall(joined[:m.start()])
        owner = ticks[0].strip() if ticks else joined.lstrip("-* ")[:60]
        names = [t.strip() for t in _TICK.findall(joined[m.end():])]
        wild = [t for t in names if re.search(r"[*?]", t)]
        if not names or wild:
            bad.append((owner, joined[m.end():].strip()[:80], wild))
            continue
        claims.append((owner, names, [t.strip() for t in ticks]))
    return claims, bad


def owner_layer(owner, tokens, layers):
    """The layer index of the first backticked token before `turns green:`
    that resolves to a configured layer, or None.

    The owner was the first token, full stop. A real plan opened phase bullets
    with a `.sql` path and with a route name, so twenty of twenty-nine tests
    had owner `?` - which skipped the comparison in silence - and the phases
    were reworded only so the checker could find an owner, which moved the
    revision and cost a gate. First RESOLVING token, not the highest of all of
    them: a bullet naming an interface and its implementation would otherwise
    take whichever layer sorts higher, a new false MISPLACED on plans that
    already work.
    """
    for t in tokens or [owner]:
        i = layer_of(t, layers)
        if i is not None:
            return i
    return None


def configured_layers(root):
    """Ordered layer names, lowest first, from CTDD_LAYERS or .ctdd.json
    `layers` (`;`-separated, like testPatterns). Empty when unconfigured."""
    raw = os.environ.get("CTDD_LAYERS", "").strip()
    if not raw:
        try:
            raw = _load_surface()._setting("CTDD_LAYERS", "layers", root)
        except Exception:
            raw = ""
    return [l.strip() for l in raw.split(";") if l.strip()] if raw else []


def layer_of(path, layers):
    """Index of the longest layer name that appears in the path bounded by
    non-identifier characters, so `Domain` matches `X.Domain/Rule.cs` and not
    `DomainEvents.cs`, and `Infrastructure.Persistence` beats `Infrastructure`.
    None when no layer matches."""
    best = None
    for i, layer in enumerate(layers):
        rx = r"(?<![A-Za-z0-9])" + re.escape(layer) + r"(?![A-Za-z0-9])"
        if re.search(rx, path or ""):
            if best is None or len(layer) > len(layers[best]):
                best = i
    return best


# ----------------------------------------------------------------- harness
# A layer has more than one test project, and the layer check reads them as
# one. A real plan put seven handler tests in the integration project of a
# layer whose unit project could hold them; test layer and owning layer
# matched, so the table said nothing, and the human found it by reading
# project names. What a test needs from the heavier project is a judgement no
# checker makes, so this asks for it in the plan, per test, before the gate,
# and prints the answer where the human reads it.
# Intent-born, 2026-11: the owner asked for the check after that finding, with
# `Tests by file` only a day old and no pilot run yet showing whether seeing
# the project at the first gate was enough.
def configured_harnesses(root):
    """Test-project kinds, lightest first, from CTDD_HARNESSES or .ctdd.json
    `harnesses` (`;`-separated, like `layers`). Empty when unconfigured, and
    then nothing below runs."""
    raw = os.environ.get("CTDD_HARNESSES", "").strip()
    if not raw:
        try:
            raw = _load_surface()._setting("CTDD_HARNESSES", "harnesses", root)
        except Exception:
            raw = ""
    return [k.strip() for k in raw.split(";") if k.strip()] if raw else []


def lighter_beside(path, kinds, idx, root):
    """The lighter kinds this test could have gone to instead: those with a
    project on disk beside the test's own, found by renaming the directory
    that carries the kind. `tests/Shop.Api.IntegrationTests/T.cs` has a
    lighter one beside it only when `tests/Shop.Api.UnitTests` exists.

    Asking a layer with one test project why its tests are not in another
    would be asked of every test there and answered the same way each time.
    Where the kind is in the file's own name (`order.integration.test.ts`) a
    lighter file can sit in the same folder, so every lighter kind counts.
    """
    p = (path or "").replace("\\", "/")
    m = re.search(r"(?<![A-Za-z0-9])" + re.escape(kinds[idx]) + r"(?![A-Za-z0-9])", p)
    if not m:
        return []
    end = p.find("/", m.end())
    if end == -1:
        return list(kinds[:idx])
    return [k for k in kinds[:idx]
            if os.path.isdir(os.path.join(root, p[:m.start()] + k + p[m.end():end]))]


_NO_REASON = re.compile(r"[`*_\s]*(?:none|nothing|n/?a|tbd|todo)[`*_]*\s*(?:$|[—–.,;:(-])", re.I)


def gives_reason(text):
    """A `needs:` line that says something. A dash, an unfilled
    `<placeholder>` and the words a plan uses for nothing are not a reason:
    `needs: none` is the plan saying the test belongs in the lighter project."""
    said = (text or "").strip()
    return bool(re.search(r"\w", said)) and not said.startswith("<") \
        and not _NO_REASON.match(said)


def approved_where(plan_file, approval):
    """Was this test at this path in the revision the human approved?

    Never, while the plan has no approval. Once it has one, a test is asked
    about only where the plan has moved it or added it since: a repository
    that names its harnesses in the middle of a change would otherwise fail
    every plan already approved, for a reason that is not the plan's, and the
    fix would move the revision and cost a gate. `Structure` and the
    invariant suite are not asked of an approved plan for the same reason.
    With no copy of the approved revision kept beside the plan there is
    nothing to compare with, and nothing is asked. A test that gave a reason
    in the approved revision still owes one: what was approved was the test
    there for that reason, and deleting the line afterwards is not that.
    """
    if not last_approved(plan_file, approval):
        return lambda name, path: False
    was, _revision, _approved = gate_base(plan_file, approval)
    if was is None:
        return lambda name, path: True
    then = strip_fences(was)
    at = dict(lane_tests(then, "new-behavior"))
    reasoned = {name for name, detail in lane_detail(then, "new-behavior").items()
                if gives_reason(detail.get("needs", ""))}
    return lambda name, path: name in at and at[name] == path and name not in reasoned


def plan_tier(text):
    """large | medium | small — derived, so it cannot be claimed.

    Read from the categorical line alone. Searching the document let prose
    control the tier: a plan declaring `contract: additive` but containing the
    sentence "the wire contract: none of it changes shape" derived `medium`,
    dropping six checked sections including `contract changes` itself.
    """
    cat = categorical_line(text) or text
    if (not _CONTRACT_NONE.search(cat)) or _HIGH_RISK.search(cat) \
            or _holdout_required(text):
        return "large"
    if not _names_a_test(text):
        # No evidence in either lane: this cannot be the lightest tier.
        return "large"
    if _NEW_BEHAVIOUR_NONE.search(text):
        return "small"
    return "medium"


def required_for(tier):
    if tier == "large":
        return REQUIRED
    allowed = SMALL_SECTIONS if tier == "small" else MEDIUM_SECTIONS
    return [(n, rx) for n, rx in REQUIRED if n in allowed]


def _load_surface():
    """Import the sibling classifier so 'spec surface' has one definition."""
    path = Path(__file__).resolve().parent / "check-spec-surface.py"
    spec = importlib.util.spec_from_file_location("check_spec_surface", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(src):
    if src == "-":
        return sys.stdin.read()
    return open(src, encoding="utf-8").read()


# The pointer allowed none of the markdown prefixes every REQUIRED pattern
# allows, and nothing after the path — so `- CTDD-Plan: …`, `**CTDD-Plan:**
# …`, a backticked line and `CTDD-Plan: … (committed)` all missed. The miss
# was a NOTE, so the description was then validated *as* the plan and a
# leftover `Risk: trivial` line in it skipped every check while the real
# plan file was never opened.
POINTER = re.compile(
    r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]{0,3}CTDD-Plan[`*_]{0,3}\s*:[`*_]{0,3}\s*"
    r"[`'\"]?([^\s`'\"*]+)", re.I | re.M)


PLAN_DIR_DEFAULT = "docs/plans"


def plan_dir(root=None):
    """Where this repository keeps plans — `planDir` in `.ctdd.json`, else the
    default. `docs/plans/` used to be not a default but a rejection: a repo
    keeping plans elsewhere could not use the CTDD-Plan pointer at all.

    The configured value is validated exactly as strictly as the pointer it
    gates. This runs in CI over untrusted MR descriptions, and a settings file
    permitted to name an absolute or traversing directory would hand that back.
    """
    value = ""
    try:
        guard = Path(__file__).resolve().parents[1] / "hooks" / "spec-edit-guard.py"
        spec = importlib.util.spec_from_file_location("seg_cfg", guard)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        value = mod.setting("CTDD_PLAN_DIR", "planDir", root)
    except Exception:
        value = ""
    # Validate the raw value, then normalise. Stripping first turns "/etc" into
    # "etc" and lets an absolute path through the check meant to reject it.
    raw = (value or PLAN_DIR_DEFAULT).strip()
    if not raw or ".." in raw or raw.startswith("/") or "\\" in raw or ":" in raw:
        return PLAN_DIR_DEFAULT
    return raw.strip("/") or PLAN_DIR_DEFAULT


def _git(args, cwd):
    """(returncode, stdout) of a read-only git command, or (None, '') when git
    cannot run. GIT_OPTIONAL_LOCKS=0: these reads run in repositories other
    sessions are editing, and must not take the index lock."""
    import subprocess
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           env=env, timeout=30)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, ""
    return r.returncode, r.stdout


def plan_dir_status(pdir, root=None):
    """Whether git ignores a NEW plan file in `pdir`, and so what step 5.5
    does with the plan once it passes: that step points here and says nothing
    of its own, so each line is the whole instruction.

    Probed with a file that does not exist, because `git check-ignore` reports
    nothing for tracked files: a directory that is ignored but holds one
    committed plan would otherwise read as not ignored. Said as ignored or
    not ignored, never "tracked", which this does not establish.
    """
    root = root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    code, _ = _git(["check-ignore", "-q", pdir.rstrip("/") + "/.ctdd-probe.md"], root)
    if code == 0:
        return (f"{pdir}/ is ignored by git here — a plan written there is not "
                f"committed. Step 5.5: paste the complete plan into the PR/MR "
                f"description when there is one, instead of a CTDD-Plan pointer.")
    if code == 1:
        return (f"{pdir}/ is not ignored by git. Step 5.5: once the plan passes "
                f"this checker, commit the plan file, and put the pointer "
                f"`CTDD-Plan: {pdir}/<name>.md` in the PR/MR description when "
                f"there is one.")
    return (f"could not tell whether git ignores {pdir}/ (not a git repository, "
            f"or git unavailable).")


def project_root(plan_file):
    """`CLAUDE_PROJECT_DIR`, else the git work tree holding the plan file, else
    None. Never the current directory: a plan read from stdin in the wrong
    directory would be checked against a repository it does not describe."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return env
    if plan_file and plan_file != "-":
        where = os.path.dirname(os.path.abspath(plan_file))
        code, out = _git(["rev-parse", "--show-toplevel"], where)
        if code == 0 and out.strip():
            return out.strip()
    return None


def _ident(name):
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")


def pin_path_findings(text, root):
    """([(name, path, exists, [found in])], [(name, path)]) for preservation
    pins whose name is not in the file their `path:` names.

    A real plan named a pin that existed in another class, covering another
    document, at a path that did not exist - and the pin run passed, because
    check-redstate matches names. It cost a gate. A pin's name found elsewhere
    in the repository's test surface is that mistake and fails. A name found
    nowhere is a pin step 7.5 has not written yet, which is legitimate and is
    only said.
    """
    pins = [(n, p) for n, p in lane_tests(text, "preservation") if p]
    pending = []
    for name, path in pins:
        try:
            with open(os.path.join(root, path), encoding="utf-8",
                      errors="replace") as fh:
                body = fh.read()
        except OSError:
            body = None
        if body is not None and _ident(name).search(body):
            continue
        pending.append((name, path, body is not None))
    if not pending:
        return [], []
    surface = _load_surface()
    surface.ensure_patterns_loaded()
    where = {name: [] for name, _p, _e in pending}
    rxs = {name: _ident(name) for name in where}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in surface._SKIP_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            if surface.classify(rel) != "test":
                continue
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    body = fh.read()
            except OSError:
                continue
            for name, rx in rxs.items():
                if rx.search(body):
                    where[name].append(rel)
    wrong = [(n, p, e, sorted(where[n])) for n, p, e in pending if where[n]]
    unwritten = [(n, p) for n, p, _e in pending if not where[n]]
    return wrong, unwritten


def _resolve_pointer(description):
    """(path_or_None, error_or_None) — find and sanity-check a CTDD-Plan pointer.

    Path shape is constrained deliberately: a value read out of an MR
    description is untrusted input, and this runs in CI. Only
    docs/plans/<name>.md is accepted, with no traversal.
    """
    m = POINTER.search(description)
    if not m:
        return None, None
    path = m.group(1).strip().strip("`\"'")
    if ".." in path or path.startswith("/") or "\\" in path:
        return None, (f"check-plan: refusing the CTDD-Plan pointer {path!r} — a path "
                      f"from an MR description must not traverse or be absolute.")
    pdir = plan_dir()
    if not (path.startswith(pdir + "/") and path.endswith(".md")):
        return None, (f"check-plan: CTDD-Plan pointer {path!r} is not under "
                      f"{pdir}/ with a .md suffix — that is where this "
                      f"repository keeps plans.")
    return path, None


# Stdin and stdout carry em dashes, `·` separators and non-ASCII paths. On a
# legacy-codepage console they decoded to replacement characters, and a
# mangled `Risk level: trivial —` changed what the pattern matched: the
# newline-bypass rejection turned into an acceptance. check-redstate already
# guards its streams; this one did not.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


# Sections REQUIRED does not carry, because each is conditional and so cannot be
# a presence check. They appear here only as terminators: a gate-visible section
# ends where the next section starts, whichever one that is.
_EXTRA_BOUNDARIES = [
    ("decisions confirmed",  r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*decisions?\s+confirmed\b"),
    ("changed assertions",   r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*changed\s+existing\s+assertions?\b"),
    ("colocated notes",      r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*colocated\s+notes?\b"),
    ("ADR draft",            r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*adr\s+draft\b"),
]
# `## Intended change` is deliberately NOT a boundary here. It was, and probing
# showed no mutation could make it the rule that kept the post-approval tail out
# of the presentation - `approved_region` had already removed that text before
# this function saw it. Two mechanisms for one rule, one of them unguarded and
# the redundant one the weaker: a boundary only stops the tail leaking out of
# the section above it, while the region rule is the reason the tail is absent.
# Deliberately NOT boundaries: `current flow` and `flow after change` are
# subheadings *inside* `Behavior flow`, so treating them as sections would cut
# that section at its own first subheading - emitting the narrative's title and
# none of the narrative, which is the compression this flag exists to remove.
_INNER = {"current flow", "flow after change"}


def _boundary_patterns():
    """Every line that starts a section, from REQUIRED plus the conditionals.

    REQUIRED's patterns, not a second list of literal names: they already carry
    the heading prefixes and the spelling variants a plan really uses - the
    section the format calls `Uncovered or ambiguous` is written `Uncovered /
    ambiguous` in this repo's own fixture, and a literal-prefix match reported
    it missing while the checker two functions away matched it.
    """
    return [(n, re.compile(rx, re.I)) for n, rx in REQUIRED
            if n not in _INNER] + [(n, re.compile(rx, re.I))
                                   for n, rx in _EXTRA_BOUNDARIES]


def _section_bounds(text):
    """Section name -> (start, end) line indices, end exclusive.

    A section runs to the next section's first line, not to the next blank line
    or heading: the sections this is built for carry numbered walks, bullet
    lists and their own subheadings, and every cheaper terminator cuts one.
    """
    lines = text.split(chr(10))
    pats = _boundary_patterns()
    hits = []
    for i, line in enumerate(lines):
        for name, rx in pats:
            if rx.match(line):
                hits.append((i, name))
                break
    # The hold-out is located by its block's shape, not by first match - see
    # `holdout_block`. Every other section keeps first-occurrence.
    hb = holdout_block(text)
    hold_line = _first_line(text, hb) if hb else None
    out = {}
    for n, (i, name) in enumerate(hits):
        end = hits[n + 1][0] if n + 1 < len(hits) else len(lines)
        if name == "hold-out decision" and hold_line is not None:
            if i == hold_line:
                out[name] = (i, end)
            continue
        # First occurrence wins: a later line repeating the label - a
        # cross-reference in prose - must not replace the real section.
        out.setdefault(name, (i, end))
    return lines, out


# The order the Gate presentation names, by the checker's own section keys.
_GATE_SECTIONS = (("hold-out decision", "Hold-out"),
                  ("behavior flow", "Behavior flow"),
                  ("known gaps", "Known gaps"),
                  ("assumptions", "Assumptions"),
                  ("uncovered/ambiguous", "Uncovered or ambiguous"),
                  ("structure", "Structure"))
_SUMMARY, _RISK_LINE = "the decision summary", "the `Risk:` line"


def _squash(s):
    return " ".join((s or "").split())


def _gate_visible(text):
    """{label: text} for every gate-visible part of a plan, in the row's
    order: the summary, the categorical line, then each section it has.

    Read from `_untailed`, never the raw text: after 7.12 appends `## Intended
    change`, a re-gate would otherwise print that tail as though the approval
    had covered it.
    """
    body = _untailed(text)
    lines, bounds = _section_bounds(body)
    cat = categorical_line(body)
    # The summary has no heading - it is everything above the categorical line -
    # so it is the one gate-visible part with nothing marking it, and the one
    # the agent is most likely to replace with its own words.
    head = min([i for i, _ in bounds.values()] or [len(lines)])
    if cat:
        for i, line in enumerate(lines):
            if line.strip() == cat.strip():
                head = i
                break
    out = {_SUMMARY: chr(10).join(lines[:head]).strip(), _RISK_LINE: cat.strip()}
    for key, label in _GATE_SECTIONS:
        if key in bounds:
            out[label] = chr(10).join(lines[slice(*bounds[key])]).rstrip()
    return out


# ------------------------------------------------------------- test detail
_SUB = re.compile(r"^\s+[-*]\s+[`*_]*(covers|path|red|needs)[`*_]*\s*:\s*(.*?)\s*$", re.I)
_ANY_SUB = re.compile(r"^\s+[-*]\s")
_CONSTRAINED = re.compile(r"constrained\s+by\b", re.I)


def lane_detail(text, lane):
    """{test name: {"covers": …, "path": …, "red": …, "needs": …}} for one
    evidence lane, in order, a wrapped field joined to its first line."""
    out, name, field = {}, None, None
    for line in _lane_block(text, lane):
        if not line.strip():
            continue
        if not line[:1].isspace() and _bullet_names_a_test(line):
            name, field = _BULLET_NAME.match(line).group(1), None
            out.setdefault(name, {})
            continue
        if name is None:
            continue
        m = _SUB.match(line)
        if m:
            field = m.group(1).lower()
            out[name].setdefault(field, m.group(2))
        elif _ANY_SUB.match(line):
            field = None
        elif field is not None and line[:1].isspace():
            out[name][field] += " " + line.strip()
    return out


def constrained_tests(text):
    """New-behaviour tests whose `red:` line declares them constrained by a
    later slice: an honest stub already lets them pass, so step 7 will not
    show them failing, and the plan says so instead of shaping a stub."""
    return [n for n, d in lane_detail(text, "new-behavior").items()
            if _CONSTRAINED.search(d.get("red", ""))]


def tests_by_file(text):
    """`  2 new + 1 pin — <path>` for every file the plan's tests live in:
    which project holds which group of tests, derived from the `path:` lines
    rather than written a second time. The altitude table names a layer, and
    a unit-test project and an integration-test project of one layer read the
    same there; in one real change seven tests sat in the wrong one of the
    two and the table matched them all."""
    rows = {}
    for lane, word in (("new-behavior", "new"), ("preservation", "pin")):
        for name, path in lane_tests(text, lane):
            rows.setdefault(path or "(no path given)", {}).setdefault(word, 0)
            rows[path or "(no path given)"][word] += 1
    out = []
    for path, count in rows.items():
        bits = []
        if "new" in count:
            bits.append(f"{count['new']} new")
        if "pin" in count:
            bits.append(f"{count['pin']} pin" + ("" if count["pin"] == 1 else "s"))
        out.append(f"  {' + '.join(bits)} — {path}")
    return out


def _expectation_text(text):
    """Everything in a plan that states a test input or an expected value:
    both evidence lanes, `Changed existing assertions`, and the hold-out's
    request and hand-check values."""
    parts = _lane_block(text, "new-behavior") + _lane_block(text, "preservation")
    lines, bounds = _section_bounds(_untailed(text))
    if "changed assertions" in bounds:
        parts += lines[slice(*bounds["changed assertions"])]
    hb = holdout_block(_untailed(text))
    if hb:
        parts += [l for l in hb.group(0).split(chr(10))
                  if re.match(r"\s*[-*]\s*[`*_]*(request|human.verified)", l, re.I)]
    return chr(10).join(parts)


def _span_tokens(s):
    toks = set()
    for span in _TICK.findall(s):
        toks |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", span))
    return toks


def _renamed_in_spans(s, renames):
    """`s` with each (old, new) applied inside its backticked spans only.
    Outside them a word like `note` is prose about the thing, not its name."""
    if not renames:
        return s

    def fix(m):
        inner = m.group(1)
        for old, new in renames:
            inner = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(old) + r"(?![A-Za-z0-9_])", new, inner)
        return "`" + inner + "`"
    return _TICK.sub(fix, s)


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def declared_renames(entries, base, text):
    """[(old, new)] an amendment entry declares, by one backticked identifier
    after `Old:` and one after `New:`.

    A rename is told from a swapped value by what a rename leaves behind: the
    old name is gone from every expectation afterwards, and the new name was
    in none of them before. `Packed` to `Shipped` is identifier-shaped and
    fails both, because other tests still say `Packed` and already said
    `Shipped`. Known limit, stated: a value replaced everywhere by one never
    used before reads as a rename here. The entry's own old and new forms are
    in front of the human at that gate either way.
    """
    before, after = _span_tokens(_expectation_text(base)), _span_tokens(_expectation_text(text))
    out = []
    for entry in entries:
        old = re.search(r"\bold\s*:(.*?)(?=\bnew\s*:)", entry, re.I | re.S)
        new = re.search(r"\bnew\s*:(.*)", entry, re.I | re.S)
        if not (old and new):
            continue
        news = [t for t in _TICK.findall(new.group(1)) if _IDENT.fullmatch(t)]
        for o in (t for t in _TICK.findall(old.group(1)) if _IDENT.fullmatch(t)):
            # A name the expectations never used renames nothing in them: an
            # entry about two types moving folders is not a rename of a test
            # input, whatever identifiers it quotes.
            if o not in before or o in after:
                continue
            n = next((n for n in news if n != o and n not in before), None)
            if n and (o, n) not in out:
                out.append((o, n))
    return out


def tests_delta(base, text, renames):
    """What changed in the two evidence lanes between two revisions of a plan,
    and whether the expectations outside them moved."""
    d = {"added": [], "removed": [], "covers": [], "path": [], "red": [], "needs": [],
         "other": []}
    for lane in ("new-behavior", "preservation"):
        b, c = lane_detail(base, lane), lane_detail(text, lane)
        d["added"] += [n for n in c if n not in b]
        d["removed"] += [n for n in b if n not in c]
        for name in c:
            if name not in b:
                continue
            # `needs:` is why a test sits in a heavier harness. Like `red:` it
            # states no input and no expected value, so a change to it is named
            # at the gate and leaves the lighter lane's condition alone.
            for field in ("covers", "path", "red", "needs"):
                was = b[name].get(field, "")
                if field != "path":
                    was = _renamed_in_spans(was, renames)
                if _squash(was) != _squash(c[name].get(field, "")):
                    d[field].append(name)

    def outside(t):
        """(changed assertions, hold-out request, hand-check values)."""
        lines, bounds = _section_bounds(_untailed(t))
        changed = chr(10).join(lines[slice(*bounds["changed assertions"])]) \
            if "changed assertions" in bounds else ""
        request = values = ""
        hb = holdout_block(_untailed(t))
        for line in (hb.group(0).split(chr(10)) if hb else []):
            m = re.match(r"\s*[-*]\s*[`*_]*(request|human.verified\s+expected\s+values)"
                         r"[`*_]*\s*:\s*(.*)$", line, re.I)
            if m and m.group(1).lower().startswith("request"):
                request = m.group(2)
            elif m:
                values = m.group(2)
        # The list comes and goes with the hold-out decision: it appears on a
        # decline and returns to `n/a` when the human writes the sealed tests
        # after all. Neither is a changed expectation. One real amendment did
        # the second and was told its tests had changed.
        if _squash(values).lower().rstrip(".") in ("", "n/a", "none", "pending"):
            values = ""
        return tuple(_squash(_renamed_in_spans(x, renames)) if t is base else _squash(x)
                     for x in (changed, request, values))
    was, now = outside(base), outside(text)
    if was[0] != now[0]:
        d["other"].append("`Changed existing assertions` changed")
    if was[1] != now[1]:
        d["other"].append("the hold-out's request changed")
    if was[2] and now[2] and was[2] != now[2]:
        d["other"].append("the hold-out's hand-check values changed")
    return d


# ------------------------------------------------------------- amendments
# One place a plan records what changed after it was shown at a gate. A real
# change invented three ("Decided at the gate", "Amended at Phase 3
# verification", "Amended at the review packet") and edited four more
# amendments in place with no record at all, so nothing could print what had
# changed, and six of nine re-presentations were byte-identical to the block
# before them. No bullet prefix on the heading: an entry may itself open with
# the word.
_AMENDMENTS = r"^\s*(?:#{1,6}\s+)?[`*_]*amendments\b"
_OLD_FORM = re.compile(r"\bold\s*:", re.I)
_NEW_FORM = re.compile(r"\bnew\s*:", re.I)


def _entries(text, pattern):
    """The unindented bullets under the heading `pattern` matches, each with
    its indented continuation lines, ending at the next unindented line that
    is not a bullet."""
    lines = text.split(chr(10))
    start = next((n for n, l in enumerate(lines) if re.match(pattern, l, re.I)), None)
    if start is None:
        return []
    out = []
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        if not line[:1].isspace() and line.lstrip().startswith(("-", "*")):
            out.append(line.rstrip())
        elif line[:1].isspace() and out:
            out[-1] += chr(10) + line.rstrip()
        else:
            break
    return out


def amendment_entries(text):
    return _entries(text, _AMENDMENTS)


def recorded_changes(text):
    """[(kind, entry)] for every bullet under `Amendments` and under
    `Decisions confirmed in session`. Field rule 11 already records an
    answered BLOCKING question in the second; asking for it under both would
    be the hand-synced duplicate this section exists to end."""
    decisions = dict(_EXTRA_BOUNDARIES)["decisions confirmed"]
    return ([("amendment", e) for e in amendment_entries(text)]
            + [("decision", e) for e in _entries(text, decisions)])


def new_changes(base, text):
    seen = {_squash(e) for _kind, e in recorded_changes(base)}
    return [(kind, e) for kind, e in recorded_changes(text) if _squash(e) not in seen]


# ------------------------------------------------------------- what was shown
# `--gate` keeps two copies of the plan beside it: `<name>.gate-shown.md`, the
# plan as its block was last printed, and `<name>.gate-base.md`, what the next
# block is a delta against. With `<name>.gate-dirty.txt` (see `record_dirty`)
# they are the only files this script writes.
# The base is the revision the human last approved; before any approval it is
# the last plan printed in full. Never merely the last block printed: an
# amended draft run through `--gate` and then edited again would become a base
# nobody saw, and the amendment in it would be approved unseen.
def _sidecar(plan_file, suffix):
    return os.path.splitext(plan_file)[0] + suffix


def _slurp(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _spit(path, text):
    try:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    except OSError as exc:
        print(f"check-plan: could not write {path}: {exc}. The next gate will "
              f"print the full block.", file=sys.stderr)


def _rev(raw):
    return plan_revision(strip_fences(raw))


def last_approved(plan_file, approval_path=None):
    """The revision the approval log's last record names, or None."""
    if not plan_file or plan_file == "-":
        return None
    rec = _slurp(approval_path or _sidecar(plan_file, ".approval.log"))
    if not rec:
        return None
    starts = [m.start() for m in re.finditer(r"(?im)^[ \t]*approved\s+by\s*:", rec)]
    if not starts:
        return None
    m = re.search(r"@([0-9a-f]{12})\b", rec[starts[-1]:])
    return m.group(1) if m else None


def gate_base(plan_file, approval_path=None, promote=False):
    """(base text, its revision, the approved revision) - each None when
    there is none. With an approval on record the base is that revision or
    nothing; `promote` saves it once the approved revision is the one last
    shown, which only a `--gate` run does."""
    if not plan_file or plan_file == "-":
        return None, None, None
    approved = last_approved(plan_file, approval_path)
    base_path = _sidecar(plan_file, ".gate-base.md")
    base, shown = _slurp(base_path), _slurp(_sidecar(plan_file, ".gate-shown.md"))
    if approved:
        if (base is None or _rev(base) != approved) and shown is not None \
                and _rev(shown) == approved:
            base = shown
            if promote:
                _spit(base_path, base)
        if base is not None and _rev(base) == approved:
            return base, approved, approved
        return None, None, approved
    if base is not None:
        return base, _rev(base), None
    return None, None, None


def remember_gate(plan_file, raw, revision, approved, full):
    """Keep what this run printed. A full block printed before any approval
    becomes the base, and so does the approved revision when it is the one
    presented."""
    if not plan_file or plan_file == "-":
        return
    _spit(_sidecar(plan_file, ".gate-shown.md"), raw)
    if (full and not approved) or approved == revision:
        _spit(_sidecar(plan_file, ".gate-base.md"), raw)


def record_dirty(plan_file):
    """Write `<name>.gate-dirty.txt`: every path git reports changed or
    untracked while a plan has no approval yet.

    Until a plan is approved the only file the workflow writes is the plan
    itself, so whatever else is dirty when a gate prints is not this change's:
    the requester's own edits, there before it began. `check-spec-surface.py
    --plan` reads the list and does not ask for an `## Intended change` row
    for those files. Recorded here, by the script, at the one moment the
    answer is known: a `Baseline:` line handed over at step 8 is one an agent
    can re-derive after the change exists, and one real session printed
    exactly that line, with the change's own forty files in it. Passing that
    would have silenced the report it was meant to tidy.
    """
    if not plan_file or plan_file == "-":
        return
    code, out = _git(["status", "--porcelain"], os.path.dirname(os.path.abspath(plan_file)))
    if code != 0:
        return
    stem = os.path.splitext(os.path.basename(plan_file))[0]
    names = []
    for line in out.split(chr(10)):
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and not os.path.basename(path.rstrip("/")).startswith(stem):
            names.append(path)
    _spit(_sidecar(plan_file, ".gate-dirty.txt"), chr(10).join(sorted(names)) + chr(10))


def gate_presentation(text, plan_src, tier, required_names, altitude):
    """Every gate-visible section, from the plan file, in the row's order.

    Written because the alternative is the agent retyping them from memory, and
    across eleven consecutive gates in one real session it did exactly that:
    `Behavior flow`'s seven-step walk became a one-line prose arrow and the
    hold-out's nine fields became a sentence. The human approved eleven changes
    on sections they had not seen. Nothing checked it, because what reaches the
    terminal was the one step of this workflow left on the agent's honour.
    """
    visible = _gate_visible(text)
    out = [f"Plan: {plan_src} ({tier})", ""]
    if visible[_SUMMARY]:
        out += ["Decision summary, verbatim:", "", visible[_SUMMARY], ""]
    if visible[_RISK_LINE]:
        out += [visible[_RISK_LINE], ""]
    for key, label in _GATE_SECTIONS:
        if label in visible:
            out += [visible[label], ""]
        elif key in required_names:
            # Unreachable through the workflow, since the same run fails on a
            # missing required section before reaching here. Printed rather
            # than skipped so that a future tier change cannot turn a hole into
            # silence.
            out += [f"{label}: MISSING from the plan file.", ""]
    by_file = tests_by_file(text)
    if by_file:
        out += ["Tests by file:"] + by_file + [""]
    out += altitude or ["Test altitude: no named tests to place.", ""]
    out += _constrained_line(text)
    return out


def _constrained_line(text):
    names = constrained_tests(text)
    if not names:
        return []
    return ["Not shown red at step 7, as the plan declares — an honest stub already "
            "passes them, so each is constrained by a later slice: " + ", ".join(names) + ".", ""]


def delta_presentation(base, text, plan_src, tier, base_rev, approved, altitude):
    """(lines, eligible) - the block for a plan amended since `base`: the
    entries recorded since then, every gate-visible part that changed in full,
    a line naming the parts that did not, and what happened to the tests.

    `eligible` is the lighter lane's condition, decided here from the two
    files and not from how the agent describes its edit: the same test names
    in both lanes with the same `covers:` lines, and the same expectations
    outside them, once a declared rename is applied.
    """
    fresh = new_changes(base, text)
    was, now = _gate_visible(base), _gate_visible(text)
    labels = [_SUMMARY, _RISK_LINE] + [label for _key, label in _GATE_SECTIONS]
    changed = [l for l in labels if l in now and _squash(was.get(l)) != _squash(now[l])]
    gone = [l for l in labels if l in was and l not in now]
    same = [l for l in labels if l in now and l not in changed]

    seen = "which you approved" if approved else "the last plan shown in full"
    out = [f"Plan: {plan_src} ({tier}) — what changed since revision {base_rev}, {seen}", ""]
    amendments = [e for kind, e in fresh if kind == "amendment"]
    decisions = [e for kind, e in fresh if kind == "decision"]
    if amendments:
        out += ["Amendments since then:"] + amendments + [""]
    if decisions:
        out += ["Decisions confirmed since then:"] + decisions + [""]
    for label in changed:
        if label == _SUMMARY:
            out += ["Decision summary, verbatim:", "", now[label], ""]
        else:
            out += [now[label], ""]
    if changed:
        out += ["Changed since then, and shown in full above: " + ", ".join(changed) + "."]
    if gone:
        out += ["Removed since then: " + ", ".join(gone) + "."]
    if same:
        out += [f"Otherwise unchanged since revision {base_rev}: " + ", ".join(same) + "."]
    out += [""]

    renames = declared_renames(amendments, base, text)
    d = tests_delta(base, text, renames)
    eligible = not (d["added"] or d["removed"] or d["covers"] or d["other"])
    count = (f"{len(lane_tests(text, 'new-behavior'))} new-behavior and "
             f"{len(lane_tests(text, 'preservation'))} preservation")
    if eligible:
        apart = ("" if not renames else ", apart from the rename " + ", ".join(
            f"`{o}` → `{n}`" for o, n in renames))
        out += [f"Tests: unchanged since then — the same {count} test names, with the same "
                f"`covers:` lines{apart}. After approval, verification is scoped to what this "
                f"amendment touches, and the whole verification still runs once before the "
                f"review packet."]
    else:
        what = [f"{word}: {', '.join(d[key])}" for key, word in
                (("added", "added"), ("removed", "removed"), ("covers", "`covers:` changed"))
                if d[key]] + d["other"]
        out += ["Tests: changed since then — " + "; ".join(what) + ". After approval this "
                "re-enters at the lowest invalidated step: red state again for what changed, "
                "and the whole verification."]
    if d["path"]:
        out += ["Test files moved: " + ", ".join(d["path"]) + "."]
    if d["red"]:
        out += ["`red:` changed: " + ", ".join(d["red"]) + "."]
    if d["needs"]:
        out += ["`needs:` changed: " + ", ".join(d["needs"]) + "."]
    out += [""]

    def placing(t):
        return _squash(chr(10).join(_lane_block(t, "new-behavior")
                                    + _bullet_section(t, "implementation slices")))
    if altitude and placing(base) != placing(text):
        out += altitude
    out += _constrained_line(text)
    return out, eligible




# ------------------------------------------------------------------- --next
# Where a change stands, read from what steps 5 to 9 leave on disk. One real
# session lost the whole skill at a compaction: the harness re-attached
# another skill and not this one, and the session went on from what the
# summary remembered. The red pause came out without its content, no
# verification was saved and step 9 never ran. Nothing in that conversation
# could say which step was next. The files could: every step that matters
# leaves one beside the plan.
def _load_redstate():
    """The sibling that verifies a captured run against a plan's named tests."""
    path = Path(__file__).resolve().parent / "check-redstate.py"
    spec = importlib.util.spec_from_file_location("check_redstate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _quiet(run, argv):
    """(exit code, what it printed) of one of this plugin's checkers, run in
    this process: `--next` reads their verdicts and copies none of them."""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = run(argv)
    except Exception as exc:      # a checker that crashed verified nothing
        out.write(f"{type(exc).__name__}: {exc}")
        code = 2
    return (code if isinstance(code, int) else 2), out.getvalue()


def _says(out, cap=170):
    """The last line a checker printed under its own name, without the name.
    A refusal's heading is the last such line; the table and notes a run
    prints before it are not."""
    named = [l.strip() for l in out.split("\n") if re.match(r"\s*check-[a-z-]+:", l)]
    line = re.sub(r"^check-[a-z-]+:\s*", "", named[-1]) if named else ""
    return line if len(line) <= cap else line[:cap].rstrip() + "…"


_RED_PAUSE = re.compile(r"red[ -]?pause\s*[:=—–-]\s*[`*_]*([a-z]+)", re.I)
_MARK = {"yes": "✓", "no": "✗", "n/a": "n/a"}
# The human's release of the 7.12 pause, and of each phase checkpoint after it,
# appended to the approval log as `execution.md` has the agent write them. Under
# `phased` the pause's release starts phase 1, and `Phase N` names the phase the
# human released the change to continue to. They quote the human's words as the
# agent wrote them down, so `--next` reports them as recorded, never as verified.
# Without them nothing on disk told a pause still waiting for the human from one
# the human had released, and a session that lost its context could only guess.
_PAUSE_RELEASE = re.compile(r"(?im)^[ \t]*pause\s+released\s+by\s*:")
_PHASE_RELEASE = re.compile(r"(?im)^[ \t]*phase\s+(\d+)\s+released\s+by\s*:")


def next_step(plan_file):
    """What the files beside a plan show was done, and the first step that
    was not.

    Reads files and runs nothing. Returns a dict: `code` (0 a next step is
    named, 1 the plan needs attention first, 2 nothing could be read, with
    `why`), `evidence` (one (name, state, note) per item in workflow order,
    the state `yes`, `no` or `n/a`), `next`, `done`, `revision`, `approved`.

    Evidence does not arrive in order. One real plan had its pins re-run
    after the change and no saved verification, so the first gap is what is
    named, and what is already there after it is said beside it.
    """
    raw = _slurp(plan_file)
    if raw is None:
        return {"code": 2, "why": f"cannot read {plan_file}"}
    text = strip_fences(raw)
    if TRIVIAL.search(text):
        return {"code": 2, "why": "this is a trivial-risk declaration, which has no "
                                  "gate and leaves no evidence files to read"}
    revision = plan_revision(text)
    name = os.path.splitext(os.path.basename(plan_file))[0]
    items = []

    code, out = _quiet(main, [plan_file])
    if code not in (0, 1):
        return {"code": 2, "why": _says(out) or "check-plan could not run on the plan"}
    plan_ok = code == 0
    items.append(("plan", "yes" if plan_ok else "no", "" if plan_ok else _says(out)))

    approved = last_approved(plan_file)
    if approved is None:
        approval = ("no", "no record")
    elif approved != revision:
        approval = ("no", f"approves {approved}, the plan is now {revision}")
    elif not plan_ok:
        approval = ("no", "not checked while the plan fails")
    else:
        code, out = _quiet(main, [plan_file, "--approval",
                                  _sidecar(plan_file, ".approval.log")])
        approval = ("yes", revision) if code == 0 else \
            ("no", _says(out) or "the record is not accepted")
    items.append(("approval",) + approval)

    redstate = []

    def lane(label, suffix, named, expect_pass):
        """A lane the plan names no test for is skipped, as 7.4 and 7.8 skip it."""
        if not named:
            items.append((label, "n/a", "the plan names none"))
            return
        log = _sidecar(plan_file, suffix)
        if not os.path.isfile(log):
            items.append((label, "no", "missing"))
            return
        if not redstate:
            redstate.append(_load_redstate())
        code, _out = _quiet(redstate[0].main, [log, "--tests-from", plan_file]
                            + (["--expect-pass"] if expect_pass else []))
        items.append((label, "yes" if code == 0 else "no", "" if code == 0 else "unverified"))

    pins = lane_tests(text, "preservation")
    lane("pins before", ".pinstate.log", pins, True)
    lane("red state", ".redstate.log", lane_tests(text, "new-behavior"), False)

    said = _RED_PAUSE.search(categorical_line(text))
    pause = said.group(1).lower() if said else ""
    if pause == "skip":
        items.append(("pre-red diff", "n/a", "red pause: skip"))
        items.append(("Intended change", "n/a", "red pause: skip"))
    else:
        items.append(("pre-red diff", "yes" if os.path.isfile(
            _sidecar(plan_file, ".prered.diff")) else "no", ""))
        items.append(("Intended change",
                      "yes" if _INTENDED_CHANGE.search(text) else "no", ""))
    # Any release in the log counts, before an amendment or after it: one taken
    # since the last approval only would refuse an amendment that the lighter
    # lane carries on from without a new pause.
    log = _slurp(_sidecar(plan_file, ".approval.log")) or ""
    if pause == "skip":
        items.append(("release recorded", "n/a", "red pause: skip"))
    else:
        items.append(("release recorded",
                      "yes" if _PAUSE_RELEASE.search(log) else "no", ""))

    verify = _sidecar(plan_file, ".verify.log")
    items.append(("verification", "yes" if os.path.isfile(verify)
                  and os.path.getsize(verify) > 0 else "no", ""))
    lane("pins after", ".pinstate-after.log", pins, True)
    items.append(("packet", "yes" if os.path.isfile(
        _sidecar(plan_file, ".packet.md")) else "no", ""))

    first = next((n for n, item in enumerate(items) if item[1] == "no"), None)
    result = {"plan": plan_file, "revision": revision, "approved": approved,
              "evidence": items, "pause": pause, "done": first is None,
              "code": 1 if not plan_ok or (approved is not None
                                           and approval[0] == "no") else 0}
    if first is None:
        result["next"] = "done: every step left its evidence, the packet included."
        return result
    label, _state, note = items[first]
    later = [l for l, state, _n in items[first + 1:] if state == "yes"]
    if label == "plan":
        nxt = "5.4: fix the plan and re-run check-plan until it exits 0." \
            + (f" It says: {note}" if note else "")
    elif label == "approval" and note == "no record":
        nxt = ("6: the gate. Print the gate presentation with `--gate`, copy it into "
               "the reply unaltered and stop for the human's approval.")
    elif label == "approval" and approved != revision:
        nxt = (f"6: the gate. Revision {approved} was approved and the plan is now "
               f"{revision}: record what changed under `Amendments` first, then "
               f"print the gate presentation and stop for approval.")
    elif label == "approval":
        nxt = f"6: the gate. The approval record is not accepted: {note}"
    elif label == "pins before" and note == "missing":
        nxt = (f"7.5–7.7: write the preservation pins through `ctdd-tests`, run them "
               f"against the unchanged implementation, save the run to "
               f"{name}.pinstate.log and verify it with check-redstate `--expect-pass`.")
    elif label == "pins before":
        nxt = (f"7.6–7.7: {name}.pinstate.log does not verify as pin pass. Run "
               f"check-redstate on it with `--expect-pass` and stop on any other state.")
    elif label == "red state" and note == "missing":
        nxt = (f"7.9–7.11: write the new-behavior tests through `ctdd-tests`, run them "
               f"before implementing, save the run to {name}.redstate.log and verify "
               f"it with check-redstate.")
    elif label == "red state":
        nxt = (f"7.10–7.11: {name}.redstate.log does not verify as intended red. Run "
               f"check-redstate on it and stop on any other state.")
    elif label in ("pre-red diff", "Intended change"):
        owed = [what for key, what in (
            ("pre-red diff", f"the pre-implementation diff ({name}.prered.diff)"),
            ("Intended change", "`## Intended change` in the plan"))
            if ("no" in [s for l, s, _n in items if l == key])]
        later = [l for l in later if l not in ("pre-red diff", "Intended change")]
        nxt = ("7.12: print the pause and stop for the release; read "
               "`references/execution.md` first. Still missing: "
               + " and ".join(owed) + ".")
    elif label == "release recorded":
        nxt = (f"7.12: the pause's records exist and no release is recorded. If the "
               f"pause was not printed in this session, print it; then stop for the "
               f"human's release, and record it as `Pause released by: \"<their "
               f"message>\"` in {name}.approval.log.")
    elif label == "verification" and pause == "skip":
        nxt = (f"8: implement what the plan approves, then 8.3: run the verification "
               f"and save it to {name}.verify.log.")
    elif label == "verification" and pause == "phased":
        phase = max([int(n) for n in _PHASE_RELEASE.findall(log)] or [1])
        nxt = (f"8: implement phase {phase}, the last one released, and stop at its "
               f"checkpoint (8.7) unless it is already waiting there; when no phase "
               f"remains, 8.3: run the verification and save it to {name}.verify.log.")
    elif label == "verification":
        nxt = (f"8: implement what the human released, then 8.3: run the verification "
               f"and save it to {name}.verify.log.")
    elif label == "pins after" and note == "missing":
        nxt = (f"8.3: re-run the preservation pins and save the run to "
               f"{name}.pinstate-after.log.")
    elif label == "pins after":
        nxt = (f"8.3: {name}.pinstate-after.log does not verify as pin pass. A pin "
               f"that passed before the change and fails after it is a broken pin: "
               f"stop and report it.")
    else:
        nxt = ("9: stop at 9.1 for the hold-out result, or for the hand check if the "
               "hold-out was declined at the gate; then the review packet (9.3, read "
               f"`references/execution.md`), saved as {name}.packet.md, and the 9.4 "
               "handover.")
    if later:
        nxt += (" Out of order: " + ", ".join(later)
                + (" is" if len(later) == 1 else " are") + " already there.")
    result["next"] = nxt
    return result


def next_lines(result):
    """The two lines `--next` prints."""
    cells = []
    for label, state, note in result["evidence"]:
        cell = f"{label} {_MARK[state]}"
        if label == "approval" and state == "yes":
            cell += f" {note}"
        elif label == "approval" and note != "no record":
            cell += f" ({note})"
        cells.append(cell)
    return ["Evidence: " + " · ".join(cells), "Next: " + result["next"]]


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    # Before anything reads a setting. A settings file with one comma too many
    # is no settings at all, and a JSON array where a string was expected read
    # as an unset key: `layers` and `harnesses` went quiet and the plan that
    # the harness check refuses passed with exit 0.
    try:
        reader = _load_surface()
    except Exception:
        reader = None
    if reader is not None and reader.settings_stop("check-plan"):
        return 2

    # --next: where the change stands, from the files beside the plan.
    if "--next" in args:
        rest = [a for a in args if a != "--next"]
        if len(rest) != 1 or rest[0].startswith("-"):
            print("check-plan: --next takes the plan's path and nothing else: "
                  "`check-plan.py <plan-path> --next`. It reads the plan and the "
                  "files beside it.")
            return 2
        result = next_step(rest[0])
        if result["code"] == 2:
            print(f"check-plan: --next cannot say where this stands: {result['why']}.")
            return 2
        for line in next_lines(result):
            print(line)
        return result["code"]

    # --gate: emit the step 6.1 presentation instead of describing it in prose.
    gate = "--gate" in args
    if gate:
        args = [a for a in args if a != "--gate"]
    # --full: print the whole block even where a delta would do. The human can
    # always ask to see all of it again.
    force_full = "--full" in args
    if force_full:
        args = [a for a in args if a != "--full"]

    diff_src = None
    if "--diff" in args:
        i = args.index("--diff")
        try:
            diff_src = args[i + 1]
        except IndexError:
            print("check-plan: --diff needs a file argument (or '-')")
            return 2
        args = args[:i] + args[i + 2:]

    # --plan-dir: report the configured plan directory, the way check-spec-surface
    # reports --adr-dir. The script already honoured `planDir` and *rejected* any
    # pointer outside it, while the skill hardcoded `docs/plans/` in six places —
    # so a repository that configured one got an exit-1 CI failure on a correct
    # plan. Configurable and unusable was the worst of both.
    if "--plan-dir" in args:
        pdir = plan_dir()
        print(pdir)
        # stdout stays the bare path, because 5.4 captures it. Whether git
        # ignores the directory goes to stderr: it decides 5.5 (commit the plan
        # and point at it, or paste it into the description), and a real
        # session told the human at two gates that the directory was tracked
        # when `.gitignore` ignored it.
        print(f"check-plan: {plan_dir_status(pdir)}", file=sys.stderr)
        return 0

    from_description = "--from-description" in args
    if from_description:
        args = [a for a in args if a != "--from-description"]
    # Checked after approval only: an open BLOCKING question is correct at 5.4.
    post_approval = "--post-approval" in args
    if post_approval:
        args = [a for a in args if a != "--post-approval"]
    # --approval <path>: the Approval record as a file, so the workflow can resume.
    approval = None
    if "--approval" in args:
        i = args.index("--approval")
        if i + 1 >= len(args):
            return _fail("--approval needs a path")
        approval = args[i + 1]
        args = args[:i] + args[i + 2:]

    # A surplus positional or a misspelled flag used to be discarded in silence, so

    # `check-plan.py plan.md diff.status` ran with no cross-check at all and

    # `--from-descriptino` was accepted as if it were the real flag. The one

    # deterministic triviality check could be disabled by a typo.

    if len(args) > 1:

        print(f"check-plan: unexpected extra argument(s): {' '.join(args[1:])}. "

              f"A diff goes after --diff; a plan is the single positional. "

              f"Refusing rather than running without the cross-check you meant to pass.")

        return 2

    plan_src = args[0] if args else "-"
    if plan_src == "-" and diff_src == "-":
        print("check-plan: plan and --diff cannot both read stdin")
        return 2

    try:
        # Fenced content is quoted, not declared: a withdrawn declaration or a
        # copied worked example inside a fence was read as live, and `Risk:
        # trivial` there skipped all nineteen checks.
        raw = _read(plan_src)
        text = strip_fences(raw)
    except OSError as exc:
        print(f"check-plan: cannot read {plan_src}: {exc}")
        return 2

    plan_file = plan_src
    if from_description:
        resolved, err = _resolve_pointer(text)
        if err:
            print(err)
            return 1
        if resolved is not None:
            try:
                raw = open(resolved, encoding="utf-8").read()
                text = strip_fences(raw)
            except OSError:
                print(f"check-plan: MR points at {resolved}, but that file is not "
                      f"in the repository. Most likely docs/plans/ is git-ignored — "
                      f"CI can only validate a plan it can see. Either commit "
                      f"docs/plans/ (the plan becomes a PR-linked audit trail), or "
                      f"drop the pointer and paste the plan into the description "
                      f"(then CI validates that copy instead).")
                return 1
            plan_file = resolved
            print(f"check-plan: validating the canonical plan at {resolved} "
                  f"(resolved from the MR description).")
        elif not TRIVIAL.search(text):
            print("check-plan: NOTE — no `CTDD-Plan:` pointer found; validating the "
                  "description itself. Preferred: write the plan to docs/plans/ and "
                  "point at it, so CI and the reviewer read the same artifact.")

    if TRIVIAL.search(text):
        if diff_src is None:
            print("check-plan: trivial-skip declaration found (risk line + reason). "
                  "The human can veto the classification; no further sections required. "
                  "(Pass --diff with `git diff --name-status -M` output once edits "
                  "exist to cross-check this claim against the actual surface.)")
            return 0
        try:
            diff_text = _read(diff_src)
        except OSError as exc:
            print(f"check-plan: cannot read --diff {diff_src}: {exc}")
            return 2
        try:
            surface = _load_surface()
            surface.ensure_patterns_loaded()
        except Exception as exc:
            print(f"check-plan: could not load the authoritative spec-surface "
                  f"classifier ({exc}); trivial claim NOT cross-checked.",
                  file=sys.stderr)
            print("check-plan: trivial-skip declaration found, but the "
                  "cross-check could not run — a trivial claim that was never "
                  "verified is not a passing claim.")
            return 2
        touched, added_only = [], True
        if not diff_text.strip():
            print("check-plan: the --diff input is empty — nothing was inspected, "
                  "so the triviality claim is NOT verified. A wrong base ref, a "
                  "shallow clone, or staged work against an unstaged diff all "
                  "produce this.")
            return 2
        entries, malformed = surface.parse_name_status(diff_text)
        if malformed:
            # The standalone checker refuses a verdict over discarded input; the
            # composed one must too, or "could not parse" silently becomes
            # "no surface touched" and a trivial claim passes unverified.
            print(f"check-plan: the diff has {len(malformed)} unparseable line(s); "
                  f"first: {malformed[0][:80]!r}. The triviality cross-check is "
                  f"incomplete, so this is not a pass.")
            return 2
        for status, old, new in entries:
            for p in (old, new):
                # "adr" was omitted, so CI blessed as trivial the same diff the
                # runtime gate calls SPEC SURFACE TOUCHED — opposite verdicts on
                # a change that rewrites a decision record.
                if p and surface.classify(p) in ("test", "contract", "adr"):
                    touched.append(p)
                    # Only a pure addition of *test* surface stays in the
                    # compressed bug-fix lane; contract files and edits to
                    # existing tests never do.
                    if not (status.upper().startswith("A")
                            and surface.classify(p) == "test"):
                        added_only = False
        if touched:
            shown = ", ".join(dict.fromkeys(touched[:3]))
            more = "" if len(set(touched)) <= 3 else f" (+{len(set(touched)) - 3} more)"
            if added_only:
                print(f"check-plan: TRIVIAL CLAIM CONTRADICTED — the diff ADDS "
                      f"test surface: {shown}{more}. Adding a test is adding spec, "
                      f"so this is not the trivial lane — it is the compressed "
                      f"bug-fix lane: produce the short plan (sections present, "
                      f"most as one-liners), not the full ceremony and not a "
                      f"one-line skip. (check-spec-surface has the inventory.)")
            else:
                print(f"check-plan: TRIVIAL CLAIM CONTRADICTED — the diff touches "
                      f"test/contract surface: {shown}{more}. An edit to an existing "
                      f"test or a contract file is never trivial; produce the full "
                      f"plan. (check-spec-surface has the complete inventory.)")
            return 1
        # The settings file decides what the loop above calls surface, so a
        # diff that changes it was read under settings the diff itself wrote.
        # This mode is handed paths and no base, so it cannot read the earlier
        # ones; check-spec-surface --git does.
        if any(surface.is_settings(p) for _s, old, new in entries for p in (old, new)):
            print("check-plan: TRIVIAL CLAIM CONTRADICTED — the diff changes "
                  "`.ctdd.json`, the settings that decide which paths are test, "
                  "contract and ADR surface. A change to them is never trivial; "
                  "produce the full plan. (check-spec-surface --git <base> lists "
                  "what the earlier settings called surface.)")
            return 1
        # The lane has two conditions and this inspects one. 3.3 is path-based
        # and checkable; 3.4 (a changed limit, validation rule, generated file
        # or file of unknown type is plan-gated) needs intent, and three
        # attempts at that heuristic were killed at 43-50% false positives.
        # So say what was checked, not that the claim stands.
        # `ADR:` on the categorical line, cross-checked against the diff.
        # The trivial lane has no categorical line, so read the whole
        # declaration: what matters is whether an ADR is claimed at all.
        adr_claimed = bool(re.search(r"\bADR\s*[:=]\s*(?!none\b)\S", text, re.I))
        adr_touched = any(
            surface.classify(e[1]) == "adr" for e in entries if len(e) > 1 and e[1])
        if adr_claimed and not adr_touched:
            print("check-plan: the categorical line claims an ADR and the diff "
                  "touches no ADR surface. A decision record that is named and not "
                  "written is a decision nothing records.")
            return 1
        if adr_touched and not adr_claimed:
            print("check-plan: the diff rewrites a decision record and the "
                  "categorical line claims no ADR. `ADR: none` over an ADR edit is "
                  "the claim check-spec-surface exists to contradict.")
            return 1

        print("check-plan: trivial claim survives the surface check — no test, "
              "contract or ADR path touched. NOT checked: 3.4's "
              "behavior-preserving requirement. This reads paths, not hunks, so "
              "a changed limit or validation rule inside one production file "
              "looks identical to a mechanical rename.")
        return 0

    # A plan naming no test in either lane derives `large` and then
    # passes at 19 of 19 — and dead-ends: 7.4 and 7.8 skip both evidence lanes, so
    # step 8's Enter can never be met, after a human has already approved. Since
    # v0.60.0 that Enter is `--next` naming step 8, and `--next` runs this check
    # first, so this refusal is the rule that a plan names at least one test. Reachable on a mechanical refactor in an
    # untested area: plan-gated by 3.5, nothing to pin, no new behaviour. Reject
    # it here, where the cost is a re-plan rather than a dead session.
    if not _names_a_test(text):
        print("check-plan: NO EVIDENCE LANE — neither `New-behavior tests` nor "
              "`Preservation pins` names a test.")
        print("Step 8 cannot be entered from this plan: both evidence lanes are "
              "skipped and its Enter requires at least one named test. If the "
              "change is behaviour-preserving in an untested area, pin the "
              "behaviour first; if it is genuinely trivial, use the 3.x lane.")
        return 1

    # An open BLOCKING question is correct at 5.4 and wrong at approval: 6.4 asks
    # only for "an affirmative message approving this plan", so a bare "Approved."
    # over an unanswered question satisfies the gate — and step 7 then begins with
    # the agent obliged to guess the one thing the section titled "BLOCKING — I
    # will not guess" said it would not. Only enforced with --post-approval, since
    # the question must still be open when the plan is first checked.
    def still_asking():
        blocking = [l for l in text.split("\n")
                    if re.match(r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*blocking\b", l, re.I)]
        open_q = [l for l in blocking if not re.search(r":\s*none\b", l, re.I)]
        if open_q and not re.search(r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*decisions\s+confirmed",
                                    text, re.I | re.M):
            print("check-plan: UNANSWERED BLOCKING AT APPROVAL — the plan still "
                  "asks a question and records no `Decisions confirmed in session`.")
            print("Field rule 11: an approved plan must not still be asking. Move "
                  "the answer there and remove the question, or write "
                  "`BLOCKING — I will not guess: none — <reason>`.")
            return True
        return False

    if post_approval and still_asking():
        return 1

    if approval is not None:
        # Four decision artifacts are stdout-only, and the Approval record is one
        # — so after a session ends there is no legal way to establish that 6.4
        # was satisfied: 6.4 rules out the agent's own restatement, silence, a
        # subagent verdict and harness acceptance, leaving only "artifacts exist
        # therefore approval happened", which is inference-as-approval. And 8.6
        # edits the plan in place, so a pre-amendment approval is textually
        # identical to a current one.
        try:
            with open(approval, encoding="utf-8", errors="replace") as fh:
                rec = fh.read()
        except OSError as exc:
            print(f"check-plan: NO APPROVAL RECORD at {approval}: {exc}")
            print("Write it at step 6 with the plan revision this checker prints; "
                  "without it a resumed session cannot establish that 6.4 was "
                  "satisfied without inferring approval from artifacts.")
            return 1
        # A log, not a slot: read the LAST record and keep the rest as
        # history. Reading the first meant an appended approval reported STALE
        # against the record before it, so a real change overwrote the file
        # and lost the history of five approvals. A record opens at a line
        # starting `Approved by:` and runs to the next one, so a quoted message
        # spanning lines stays one record. Earlier records are never judged.
        starts = [m.start() for m in
                  re.finditer(r"(?im)^[ \t]*approved\s+by\s*:", rec)]
        history = max(len(starts) - 1, 0)
        if starts:
            rec = rec[starts[-1]:]
        want = plan_revision(text)
        found = re.search(r"@([0-9a-f]{12})\b", rec)
        if not found:
            print(f"check-plan: the approval record names no plan revision. "
                  f"Expected `plan: <path>@{want}`.")
            return 1
        if found.group(1) != want:
            print(f"check-plan: APPROVAL STALE — the record approves revision "
                  f"{found.group(1)}, the plan is now {want}.")
            print("An 8.6 amendment edits the plan in place at the same path, so "
                  "re-approve before resuming; the record cannot show the plan "
                  "changed after approval.")
            return 1
        if not re.search(r"approved\s+by\s*:\s*\S", rec, re.I):
            print("check-plan: the approval record quotes no human message. "
                  "6.4 excludes your own restatement, silence, a subagent verdict "
                  "and harness acceptance.")
            return 1
        # An interactive selector resolves on one keystroke, and a harness can
        # resolve a pending one with its highlighted default while the human is
        # typing something else entirely — so a record quoting the option label
        # verbatim is indistinguishable from an approval nobody gave. That is not
        # hypothetical: one landed, and the production edit ran on it. 6.3 now
        # prints the options and ends the turn; this catches the label that shows
        # a selector was used anyway. Only the three labels 6.3 prints, because a
        # wider set would start judging how enthusiastic a real approval must be,
        # which this script does not do.
        _GATE_LABELS = {"approve", "approve with changes", "reject"}
        said = re.search(r"approved\s+by\s*:\s*(.*?)\s*;\s*plan\s*:", rec, re.I | re.S) \
            or re.search(r"approved\s+by\s*:\s*(.+)", rec, re.I)
        if said is not None:
            quoted = said.group(1).strip()
            bare = re.sub(r'^["“‘\']+|["”’\']+$', "", quoted).strip()
            spoken = bare.rstrip(".!,").strip().casefold()
            # v0.55.0, intent-born: the owner asked for selectable options at
            # every stop, the gate included, so a bare label is now a legitimate
            # way to approve and rejecting it would fail every gate. What the
            # record still may not do is leave the reader unable to tell WHICH
            # happened. This is traceability, not prevention: with selectors
            # allowed, nothing in the record distinguishes a deliberate click
            # from a selector resolving on a harness default, which is how a
            # production file was once edited against a gate nobody passed. That
            # protection now belongs to the harness. The record at least says so.
            # No separate "does it carry provenance" test: any wording beyond
            # the label itself already takes `spoken` out of the set above, so a
            # second check would be a branch no mutation could reach.
            if spoken in _GATE_LABELS:
                print(f"check-plan: the approval record carries the bare option "
                      f"label {quoted} and does not say how it arrived. A label "
                      f"alone reads the same whether the human chose it or a "
                      f"selector resolved on a default, and only one of those is "
                      f"approval.")
                print("Say which, in the record itself — "
                      f"`Approved by: \"{bare}\" (selected at the gate)` or "
                      f"`Approved by: \"{bare}\" (typed at the gate)` — or quote "
                      "the human's own words instead of the label.")
                return 1
        # The revision alone cannot show the presentation was ever rendered:
        # every run prints it, so a record can name it without a human having
        # seen the block. The token appears only inside the block. A record
        # written before this check existed can still pass, but only by saying
        # so in writing - an absent token is a failure, an explicitly waived
        # one is a decision someone recorded.
        want_token = gate_token(want)
        tok = re.search(r"gate-token\s*:\s*([0-9a-f]{8}|n/a)\b", rec, re.I)
        if tok is None:
            print(f"check-plan: the approval record carries no gate token. "
                  f"Re-run with --gate, copy the whole presentation into your "
                  f"reply, and record `gate-token: {want_token}` alongside the "
                  f"revision.")
            print("A record written before gate tokens existed may carry "
                  "`gate-token: n/a (predates gate tokens)` instead — "
                  "deliberately, in writing, so the gap is visible rather than "
                  "assumed.")
            return 1
        got = tok.group(1).casefold()
        if got != "n/a" and got != want_token:
            print(f"check-plan: GATE TOKEN MISMATCH — the record carries {got}, "
                  f"this plan's presentation prints {want_token}. The token is "
                  f"derived from the plan revision, so a stale one means the "
                  f"block the human saw was not this plan.")
            return 1
        # An approval typed together with the change it dictates covers that
        # change and nothing else. What a script can hold it to: every entry
        # recorded since the base quotes the approving message. An extra edit
        # the agent made on its own account, recorded as its own entry, is
        # then not covered - the case the owner named when deciding this. An
        # extra edit folded into the dictated entry, or made with no entry at
        # all, is not caught here; the delta block puts every changed section
        # and test in front of the human instead.
        if re.search(r"covers\s+the\s+amendment", rec, re.I):
            said_it = re.search(r'approved\s+by\s*:\s*["“]([^"”]+)["”]', rec, re.I)
            message = _squash(said_it.group(1)).casefold() if said_it else ""
            prior = _slurp(_sidecar(plan_file, ".gate-base.md")) if plan_file != "-" else None
            if prior is not None and _rev(prior) != want:
                fresh = new_changes(strip_fences(prior), text)
            else:
                fresh = recorded_changes(text)[-1:]
            # An answered BLOCKING question is recorded under `Decisions
            # confirmed in session` by field rule 11, and it answers a
            # question the gate put to them; only an amendment has to carry
            # their words.
            stray = [e for kind, e in fresh if kind == "amendment"
                     and (not message or message not in _squash(e).casefold())]
            # The message has to say it approves. The first agent run under
            # this rule took `A, <a name>` - a choice among two offered fixes -
            # as an approval that covered its own change, recorded it so and
            # went on to edit code. Picking a fix dictates the change; it does
            # not approve the amended plan. Narrow on purpose, and it errs
            # toward one more `approve` from the human, never one fewer.
            if not re.search(r"\bapprov", message):
                print("check-plan: NOT AN APPROVAL — the record says the human's message "
                      f"covers the amendment it dictated, and that message (\"{said_it.group(1) if said_it else ''}\") "
                      "does not say it approves.")
                print("A choice among offered fixes, or an answer to a question, dictates a "
                      "change and approves nothing. Present the delta block, stop for their "
                      "approval of it, and record that approval.")
                return 1
            if not fresh or stray:
                print("check-plan: APPROVAL COVERS ONLY WHAT IT DICTATED — the record "
                      "says the human's message covers the amendment it dictated, and "
                      + ("the plan records no amendment since the last block they saw."
                         if not fresh else
                         "these entries do not quote that message: "
                         + "; ".join(_squash(e)[:60] for e in stray)))
                print("Quote their words in each entry they dictated. Anything else is "
                      "your own amendment: present the delta block, stop for approval "
                      "of it, and record that approval without `covers the amendment`.")
                return 1
        # The record is for this revision, so this is an approved plan, and an
        # approved plan is not still asking. The same check has sat behind
        # `--post-approval` since it was written; one reference line named
        # that flag, no step ran it, and in one real session it never ran. A
        # stale record never reaches here: a plan amended after approval may
        # carry a new question, and that is what its next gate is for.
        if still_asking():
            return 1
        print(f"check-plan: approval record verified for revision {want}"
              + (f" (the last of {history + 1} records; the earlier ones are "
                 f"history)." if history else "."))

    # 4.5 routes a changed existing assertion as an amendment and rule 3 gives it
    # its own section, but the section is conditional and no rule tied it to the
    # thing that triggers it — so a change carried entirely by retargeting an
    # assertion could declare both evidence lanes `none` and pass with the
    # amendment recorded nowhere. It cannot be required unconditionally; it can
    # be required when the plan says an assertion changed.
    _CHANGED = re.compile(
        r"^\s*(?:[-*]\s+|#{1,6}\s+)?[`*_]*changed\s+existing\s+assertions?\b",
        re.I | re.M)
    claims_change = re.search(
        r"retarget\w*|changed?\s+(?:the\s+)?(?:existing\s+)?assertion", text, re.I)
    if claims_change and not _CHANGED.search(text):
        print("check-plan: MISSING `Changed existing assertions` — the plan says an "
              "existing assertion changes and records no old and new form.")
        print("Field rule 3 gives that its own section; a retargeted assertion is a "
              "spec amendment, and both evidence lanes may legitimately read `none` "
              "while it carries the whole change.")
        return 1

    # Field rule 9: exact file paths, never wildcards, bare directories,
    # `(+ tests)`, `TBD` or unnamed future files. Mechanically checkable and
    # unchecked — and these paths feed `check-redstate --tests-from`, so the gate
    # blessed paths no test file can be written to.
    vague = []
    for m in re.finditer(r"`([^`\n]{2,120})`", _file_listings(text)):
        tok = m.group(1).strip()
        if "/" not in tok and "." not in tok:
            continue
        # A token with no directory that carries a call, an argument list or
        # a space is code, not a path: `IRepo.SetAsync(..., message, ...)`
        # failed the gate for its `...`. `(+ tests)` is rule 9's own case and
        # is judged before this exemption can reach it.
        if "/" not in tok and not re.search(r"\(\+", tok) \
                and re.search(r"[(), ]", tok):
            continue
        if re.search(r"[*?]|/\s*$|\(\+[^)]*\)|\bTBD\b|\.\.\.", tok):
            vague.append(tok)
    if vague:
        print("check-plan: UNRESOLVED PATHS — " + ", ".join(sorted(set(vague))[:8]))
        print("Field rule 9 requires exact file paths; a wildcard, a bare directory, "
              "`(+ tests)` or `TBD` names no file.")
        return 1

    # A pin's path is checked against the repository: pins assert behaviour
    # that already exists, so their file is readable now. New-behaviour tests
    # are not checked - their files are what step 7 writes.
    if any(p for _n, p in lane_tests(text, "preservation")):
        root = project_root(plan_file)
        if root is None:
            print("check-plan: pin paths not checked — no repository root. Pass "
                  "the plan by its path inside the repository, or set "
                  "CLAUDE_PROJECT_DIR.")
        else:
            wrong, unwritten = pin_path_findings(text, root)
            if unwritten:
                print("check-plan: pins not written yet (7.5 writes them against "
                      "the current implementation): " + ", ".join(
                          f"{n} at `{p}`" for n, p in unwritten))
            if wrong:
                print("check-plan: PIN NOT AT ITS PATH — the name is not in the "
                      "file the plan gives, and it is in another:")
                for name, path, exists, found in wrong:
                    print(f"  {name} — `{path}` "
                          f"{'does not contain it' if exists else 'does not exist'}"
                          f"; found in: {', '.join(found[:4])}"
                          + (f" (+{len(found) - 4} more)" if len(found) > 4 else ""))
                print("check-redstate verifies a pin by its name, so a pin pointing "
                      "at the wrong file passes on another test's run. Correct the "
                      "path, or the name if the planned test is a different one.")
                return 1

    # The categorical line is what tier, triviality and hold-out all read, and
    # nothing required it to exist. `categorical_line(text) or text` then fell
    # back to the whole document, so one prose sentence containing `contract:
    # none` derived a lighter tier on a breaking change and deleted four sections
    # from the gate; and omitting the `hold-out:` field switched the actionability
    # check off while the body still declared one required.
    cat = categorical_line(text)
    if not cat:
        print("check-plan: MISSING the categorical line — no `Risk: … · contract: "
              "… · hold-out: …` line was found.")
        print("Tier, triviality and the hold-out check all read it; without it "
              "they fall back to the whole document and prose decides the tier.")
        return 1
    # `ADR: NNNN required` sits on a mandatory line and was parsed by nothing, so
    # a plan could claim a decision record and never write one — or say `ADR: none`
    # while the diff rewrites one. The `--diff` path already classifies surface, so
    # both directions are checkable there; here, only that the field exists.
    # `red pause` joined the line in v0.42.0. Absent, step 7.12 has no
    # instruction and the pause silently never fires — a decision nobody made,
    # which is the finding-#2/#21/#28 shape (the mechanism exists and is not
    # invoked). Existence-only, like `ADR:`: the workflow reads the value.
    for field, fpat in (("contract", "contract"), ("hold-out", "hold.?out"),
                        ("ADR", "ADR"), ("red pause", "red[ -]?pause")):
        if not re.search(rf"{fpat}\s*[:=—–-]", cat, re.I):
            print(f"check-plan: the categorical line names no `{field}:` field — "
                  f"{cat.strip()[:70]!r}")
            print("An absent field is not a declared one; it silences the check "
                  "that reads it.")
            return 1

    tier = plan_tier(text)
    required = required_for(tier)
    altitude_lines = []
    # `Structure` is what the FIRST gate shows. A plan approved before the
    # section existed gains nothing from being failed for it now, and adding
    # it would move the revision and cost a re-approval: a checker failure for
    # a reason that is not the plan's.
    has_structure = bool(re.search(dict(REQUIRED)["structure"], text, re.I | re.M))
    if not has_structure and last_approved(plan_file, approval):
        required = [(n, rx) for n, rx in required if n != "structure"]

    # A section appearing twice is a corrupted plan, not a complete one. The
    # 2026-08-03 session rewrote its plan 28 times with 16 silent-failing `sed`
    # calls and spliced a duplicate section in; the agent found it by hand, and
    # this checker passed the corrupt file 19/19 because it only ever asked
    # whether each heading was present at least once.
    # The categorical line (`Risk: ... · contract: ... · hold-out: ...`) is matched
    # by the `risk level` pattern too, because that pattern makes `level` optional
    # on purpose. It is one line by construction, so exclude it from the count
    # rather than loosen the pattern that the gate depends on.
    # Third instance of one defect: the count matched a section NAME anywhere a
    # line began with it, so any line merely labelled with one read as a second
    # section. (1) A categorical line ordering its fields differently counted as
    # a second `risk level` - patched by excluding that one line, recorded in the
    # comment above. (2) A decision-summary line labelled with a section name;
    # the format's own example passes only because its labels are abbreviated
    # far enough to evade this, which nothing recorded. (3) `Current flow,
    # unchanged adjacent paths` - a heading the format's example demonstrates -
    # rejected a valid plan as corrupt. Patching instances is what produced
    # three of them, so the discriminator is the shape: this check counts
    # SECTIONS, and a section heading is a line that is nothing but its own
    # name. A line that continues into other words is a different label.
    #
    # A shape rule was tried first and deleted the check: `Existing behavior
    # (openapi.yaml; CaptureTests.cs):` is a heading form the format's own
    # example demonstrates, so "a heading is nothing but its own name"
    # excluded the real headings along with the labels and a spliced duplicate
    # passed. Its own control test caught that, which is why the control is
    # written as the corruption that actually happened.
    #
    # What separates them is the text AFTER the name. Two lines are the same
    # section when that text is the same; a line continuing into different
    # words is a different label. The recorded corruption was a failed `sed`
    # splicing a block in, which duplicates a heading verbatim.
    #
    # Known limit, stated rather than left to be found: two same-name headings
    # with DIFFERENT trailing text are not flagged. Narrower than the four
    # false-positive classes it replaces, and unlike them it cannot reject a
    # valid plan.
    duplicated = []
    for name, pat in required:
        seen = {}
        for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            # Bounded from m.end(), never m.start(). Every pattern opens
            # `^\s*` and `\s` matches newlines, so under MULTILINE a match
            # can BEGIN on the blank line above, so m.start() is not on the
            # name's line at all and the extracted line came out empty.
            # m.end() is always inside the name.
            #
            # UNGUARDED, and said so rather than implied: `rest` already
            # derives from m.end(), so every duplicate-count test passes
            # with this reverted - a probe proved it. What it fixes is the
            # CATEGORICAL_LINE filter reading an empty string whenever a
            # blank line precedes the line it must exclude. No realistic
            # plan makes that observable, because the excluded line then
            # gets its own key and only collides if another line's text
            # after the name is identical. Kept because it is correct;
            # filed rather than claimed as guarded.
            # `find` returns -1 on a final line with no trailing newline,
            # which sliced to text[start:-1] and dropped its last character.
            ls = text.rfind(chr(10), 0, m.end()) + 1
            le = text.find(chr(10), m.end())
            line = text[ls:] if le < 0 else text[ls:le]
            if CATEGORICAL_LINE.search(line):
                continue
            rest = text[m.end():] if le < 0 else text[m.end():le]
            key = " ".join(rest.split()).strip("`*_#:").strip().lower()
            seen[key] = seen.get(key, 0) + 1
        worst = max(seen.values()) if seen else 0
        if worst > 1:
            duplicated.append((name, worst))
    hidden = hidden_in_intended_change(text, required)
    if hidden:
        print("check-plan: SECTION IN THE UN-APPROVED TAIL — "
              + ", ".join(sorted(heading_of(n) for n in hidden)))
        print("`## Intended change` is appended after approval and is excluded "
              "from the plan revision, so a mandatory section written below it "
              "is a section the approval never covered. Move it above.")
        return 1

    if duplicated:
        print("check-plan: DUPLICATED sections — " +
              ", ".join(f"{heading_of(n)} (x{c})" for n, c in duplicated))
        print("A section written twice is a corrupted plan; the gate cannot tell "
              "which copy the human approved.")
        return 1

    # A required hold-out has to name the work, or the human cannot start it.
    # 2026-08-03 wrote `request: 2 sealed tests written and withheld by the
    # human` — the unbounded phrasing plan-format rule 6 exists to replace — and
    # the human had to ask "what is my task".
    holdout = holdout_block(text)
    if holdout and _holdout_required(text):
        block = holdout.group(0)
        absent = [f for f in ("options:", "recommended:") if f not in block]
        if absent:
            print("check-plan: HOLD-OUT NOT ACTIONABLE — missing " +
                  ", ".join(absent))
            print("A required hold-out states the assertions to write, gives "
                  "`write` and `decline` with their consequences, and recommends "
                  "one (plan-format rule 6). Without them the human is handed a "
                  "label, not a task.")
            return 1

        # `defer` was struck from 9.1's options in v0.43.0 because it was the
        # same escape under another name. A real session then answered the
        # prompt with `Defer / NOT RUN` and the plan recorded `result: NOT RUN,
        # deferred by the human ... (not a decline)`, leaving load-bearing
        # boundary evidence neither owed nor waived, which is the state
        # `declined by human` exists to record. The prompt is prose and was
        # ignored; the result is written into the plan, so it is checked where
        # it lands. Only a present `result:` is judged: an absent one is the
        # actionability check's territory above, and two fixtures rely on that.
        found = re.search(r"(?mi)^\s*[-*]?\s*result\s*:\s*(.+?)\s*$", block)
        if found:
            value = found.group(1)
            allowed = ("pending", "passed", "failed", "declined by human",
                       "not run")
            if not value.lower().startswith(allowed):
                print("check-plan: hold-out `result: %s` is not one of %s."
                      % (value[:60], ", ".join(allowed)))
                print("A value outside that set records neither an outcome nor "
                      "a waiver, so the packet cannot say what became of the "
                      "evidence.")
                return 1
            if "defer" in value.lower():
                print("check-plan: the hold-out result defers (%s)."
                      % value[:70])
                print("Deferral is not an outcome. `NOT RUN` is for a runner "
                      "that is unavailable; a human who will not run it now "
                      "declines, and `declined by human` is what carries the "
                      "waiver and the hand-computed expected values. Choose one.")
                return 1

    # Count the same lines the duplicate scan counts. That scan excludes the
    # categorical `Risk: … · contract: … · hold-out: …` line because the `risk
    # level` pattern matches it too; this one did not, so the categorical line
    # satisfied the `Risk level:` section and deleting that section entirely still
    # exited 0 — the one required section that could never be reported missing,
    # and the section every tier keys on.
    def _present(pat):
        for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            end = text.find("\n", m.start())
            line = text[m.start():] if end < 0 else text[m.start():end]
            if not CATEGORICAL_LINE.search(line):
                return True
        return False

    missing = [name for name, pat in required if not _present(pat)]
    if missing:
        print(f"check-plan: MISSING sections for a {tier} plan — "
              + ", ".join(heading_of(n) for n in missing))
        print("A plan that omits a section hasn't decided it; it has skipped it.")
        return 1

    if has_structure and any(n == "structure" for n, _ in required):
        block = _gate_visible(text).get("Structure", "")
        absent = [w for w in ("Types", "Ports", "Configuration")
                  if not re.search(r"(?im)^\s*[-*]\s+[`*_]*" + w + r"\b", block)]
        if absent:
            print("check-plan: STRUCTURE INCOMPLETE — no line for: " + ", ".join(absent))
            print("`Structure` says, one bullet each: `Types` (new or changed public "
                  "types and where each lives), `Ports` (the abstractions the change "
                  "crosses) and `Configuration` (bindings). `none` is an answer; an "
                  "absent line is not. The test project per group is printed for you.")
            return 1

    # The repository's own standing rules, named where a plan has something to
    # place and run before anything is built on the placement. One real change
    # returned a feature-folder type from a port in its first stub and learned
    # that at the last phase's verification, three approved revisions later -
    # from a test that had been there the whole time. Not asked of a plan that
    # already has an approval, for the reason `Structure` is not.
    if any(n == "implementation slices" for n, _ in required) \
            and not last_approved(plan_file, approval) \
            and not any(_INVARIANTS.match(l) for l in _bullet_section(text, "verification")):
        print("check-plan: NO INVARIANT SUITE — `Verification` has no `- invariants:` line.")
        print("Name the fast command that checks this repository's standing rules, such "
              "as its architecture or layering tests, and read what those rules say about "
              "where new types may live: `- invariants: `<command>` — expected: passes`. "
              "It runs at step 7.10 and at every checkpoint, so a rule this plan breaks "
              "fails before implementation and not at the last verification. Where the "
              "repository has no such suite, write `- invariants: none — <reason>`.")
        return 1

    # Test altitude. Runs whenever `Implementation slices` is required (medium
    # and large), which is exactly when a plan has new behaviour to place.
    if any(n == "implementation slices" for n, _ in required):
        tests = lane_tests(text, "new-behavior")
        claims, vague = slice_claims(text)
        if vague:
            print("check-plan: VAGUE OWNERSHIP — `turns green:` must name each test "
                  "exactly:")
            for owner, clause, wild in vague:
                print(f"  {owner} — turns green: {clause}"
                      + (f"   [wildcard: {', '.join(wild)}]" if wild
                         else "   [no test named]"))
            print("Altitude follows ownership. A slice that names, exactly, the tests "
                  "it turns green is the plan deciding which layer owns each "
                  "behaviour; a wildcard defers that decision to implementation, "
                  "which is where real plans have put tests at the wrong level.")
            return 1
        owners = {}
        for owner, names, tokens in claims:
            for nm in names:
                owners.setdefault(nm, []).append((owner, tokens))
        known = {n for n, _ in tests} | {n for n, _ in lane_tests(text, "preservation")}
        unknown = sorted(set(owners) - known)
        if unknown:
            print("check-plan: UNKNOWN TEST in `turns green:` — " + ", ".join(unknown))
            print("No test bullet names it. A misspelt claim orphans the real test "
                  "silently; fix the name on one side.")
            return 1
        root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        layers = configured_layers(root)
        kinds = configured_harnesses(root)
        said = lane_detail(text, "new-behavior") if kinds else {}
        there_at_approval = approved_where(plan_file, approval) if kinds else None
        rows, orphans, misplaced, unplaced = [], [], [], []
        unkinded, unasked, unreasoned, settled = [], [], [], []
        for name, path in tests:
            own = owners.get(name, [])
            if not own:
                orphans.append(name)
            t_idx = layer_of(path, layers) if layers else None
            o_idx = [i for i in (owner_layer(o, toks, layers) for o, toks in own)
                     if i is not None] if layers else []
            need = max(o_idx) if o_idx else None
            t_lbl = layers[t_idx] if t_idx is not None else "?"
            o_lbl = (", ".join(sorted({layers[i] for i in o_idx})) if o_idx
                     else ("—" if not own else "?"))
            k_idx = layer_of(path, kinds) if kinds else None
            reason = ""
            if kinds and k_idx is None:
                unkinded.append(name)
            elif k_idx:
                beside = lighter_beside(path, kinds, k_idx, root)
                reason = said.get(name, {}).get("needs", "")
                if gives_reason(reason):
                    pass
                elif not beside:
                    unasked.append(name)
                elif there_at_approval(name, path):
                    settled.append(name)
                else:
                    unreasoned.append((name, kinds[k_idx], path, ", ".join(beside)))
            rows.append((name, t_lbl, o_lbl, kinds[k_idx] if k_idx is not None else "?",
                         reason if gives_reason(reason) else ""))
            if t_idx is not None and need is not None and t_idx != need:
                misplaced.append((name, t_lbl, layers[need],
                                  "above" if t_idx > need else "below"))
            # A `?` while layers are configured means no comparison ran. That
            # used to pass in silence, which reads exactly like a test placed
            # correctly.
            if layers and own and (t_idx is None or need is None):
                unplaced.append((name, "its path resolves to no layer"
                                 if t_idx is None else
                                 "no backticked path before `turns green:` "
                                 "resolves to a layer"))
        if tests:
            # Without `harnesses` every line here is what it was before the
            # setting existed, header included.
            body = []
            for name, t_lbl, o_lbl, k_lbl, reason in rows:
                body.append(f"  {name}  {t_lbl} · {k_lbl} | {o_lbl}" if kinds
                            else f"  {name}  {t_lbl} | {o_lbl}")
                if reason:
                    body.append(f"      needs: {reason}")
            if not layers:
                body.append("  (layers not configured — set `layers` in "
                            ".ctdd.json, lowest;…;highest, or CTDD_LAYERS, to "
                            "check placement)")
            # Under --gate it belongs inside the block the human reads, not
            # scrolled off above it: 5.4 says re-run until this exits 0, so on
            # 0 the table printed here reached nobody. That is the defect
            # v0.52.0 fixed by naming it gate-visible, and it stays fixed by
            # the table travelling with the rest of the presentation.
            #
            # Without the flag this prints exactly what it printed before the
            # flag existed, header wording included: 5.4's run is the one every
            # plan makes, and moving its output would be a change nobody asked
            # for riding along with one they did.
            if unplaced:
                body.append(f"  NOT PLACED — layers are configured and the "
                            f"comparison did not run for {len(unplaced)} test(s):")
                body += [f"    {n} — {why}" for n, why in unplaced]
            # Said, not skipped, for the reason NOT PLACED is: a `?` in the
            # column reads like a test nobody had a question about.
            if unkinded:
                body.append(f"  HARNESS NOT NAMED — `harnesses` is configured and names "
                            f"none in the path of {len(unkinded)} test(s): "
                            + ", ".join(unkinded))
            if unasked:
                body.append(f"  (no reason is asked of {len(unasked)} test(s) in a heavier "
                            f"harness: no lighter project sits beside theirs)")
            if settled:
                body.append(f"  (no reason is asked of {len(settled)} test(s) in a heavier "
                            f"harness: they sit where the plan you approved had them)")
            columns = ("test layer · harness | owning layer" if kinds
                       else "test layer | owning layer")
            altitude_lines = ["Test altitude — " + columns] + body + [""]
            if not gate:
                print("check-plan: test altitude — " + columns)
                for line in body:
                    print(line)
        if orphans:
            print("check-plan: NO OWNER — no slice turns these green: "
                  + ", ".join(orphans))
            print("Altitude follows ownership: name the file that turns each one "
                  "green under `Implementation slices`, and the test's level "
                  "follows from that file's layer.")
            return 1
        if misplaced:
            print("check-plan: MISPLACED TESTS —")
            for name, t_lbl, need, where in misplaced:
                print(f"  {name} sits at {t_lbl}, {where} the {need} code that "
                      f"turns it green")
            print("A test above its owner pays for a boundary it does not assert; "
                  "one below cannot reach the code. The lowest project that "
                  "observes the behaviour is the owning layer's.")
            return 1
        if unreasoned:
            print("check-plan: HEAVIER HARNESS, NO REASON —")
            for name, kind, path, beside in unreasoned:
                print(f"  {name} sits in {kind} ({path}); the same layer has {beside} "
                      f"beside it")
            print("Move each test to the lighter project (its `path:` line, and its file "
                  "under `Files likely to change`), or say under it what only the heavier "
                  "one can reach: `  - needs: <a real database, a broker, the running host "
                  "— what, and why a stand-in for it would not do>`. A test in the heavier "
                  "harness pays for it on every run, and the reason is what the human "
                  "judges at the gate.")
            return 1
    # Gate-reading cost, reported not enforced. Plans have run 5,432 (the canonical
    # example), 17,801, 31,448 and 57,321 characters; the last is ~31 minutes of
    # reading before a human can approve. Nobody chose that — it accrued over 28
    # amendment rounds. A number on the screen at the moment of writing is the
    # cheapest thing that makes the cost visible; the tier already sets the floor.
    # Under --gate only: it is a cost of reading at the gate. Printed on every
    # run, it repeated through every 5.4, 8.6 and packet re-check of one real
    # change (33,575 characters at its first gate, 51,161 at its tenth), where
    # nobody was about to read the plan.
    words = len(text.split())
    if gate and words > 1500:
        print(f"check-plan: plan is {len(text):,} chars / {words:,} words "
              f"(~{round(words/220)} min to read at the gate). The human has to "
              f"read this before approving; consolidate if amendment rounds have "
              f"left superseded material behind.")
    # The summary is the plan's opening prose — before the categorical `Risk:` line
    # and with no heading of its own, which is why nothing could extract it and why
    # deleting it from the format's own example still exited 0 at 19 of 19. A regex
    # cannot express "not any of the section headings", so check it against them.
    first = next((l for l in text.split("\n") if l.strip()), "")
    if (any(re.match(pat, first, re.IGNORECASE) for _, pat in REQUIRED)
            or CATEGORICAL_LINE.search(first) or len(first.strip()) < 20):
        print("check-plan: MISSING the decision summary — the plan opens with "
              f"{first.strip()[:48]!r} rather than prose. 6.1 leads the gate "
              f"presentation with it and 6.2 copies it verbatim, so the gate "
              f"rests on it.")
        return 1

    # A content digest, so "the current plan revision" in the write freeze is
    # something the Approval record can carry. 8.6 edits the plan in place at the
    # same path, so without one a pre-amendment approval is textually identical to
    # a current one — and one pilot plan ran to 28 amendment rounds.
    digest = plan_revision(text)

    # An amendment says what it replaced. 8.6 asked for "the old and new form"
    # in prose and field rule 3 asked the same of a changed assertion; neither
    # was checked, and four of one change's nine amendments were edited in
    # place with nothing recording what had been there.
    formless = [e for e in amendment_entries(text)
                if not (_OLD_FORM.search(e) and _NEW_FORM.search(e))]
    if formless:
        print("check-plan: AMENDMENT WITHOUT OLD AND NEW FORM — "
              + "; ".join(_squash(e)[:70] for e in formless))
        print("Each bullet under `Amendments` gives both, as `Old: …` and `New: …`. "
              "The gate shows the human that bullet in place of the whole plan, so a "
              "bullet that says only what is now true shows them half of the change.")
        return 1

    # What the last gate showed, and whether this plan has moved since.
    base, base_rev, approved_rev = gate_base(plan_file, approval, promote=gate)
    base_text = strip_fences(base) if base is not None else None
    amended = base_text is not None and base_rev != digest
    fresh = new_changes(base_text, text) if amended else []
    if amended and approved_rev and not fresh:
        print(f"check-plan: AMENDED WITHOUT AN ENTRY — the plan is not the revision "
              f"{approved_rev} that was approved, and neither `Amendments` nor "
              f"`Decisions confirmed in session` records anything since.")
        print("Every change to an approved plan is an amendment. Record it as one "
              "bullet under `Amendments`, with `Old:` and `New:`: that bullet is what "
              "the next gate shows.")
        return 1

    print(f"check-plan: plan revision {digest} — carry it in the Approval record "
          f"and the packet as `plan: <path>@{digest}`.")
    print(f"check-plan: all mandatory sections present for a {tier} plan "
          f"({len(required)} of {len(REQUIRED)}; presence, not quality — the "
          f"review still owns quality).")

    # Last, and only after every check passed: a gate presentation for a plan
    # that does not validate would put a human in front of an approval surface
    # the workflow has not cleared.
    if gate:
        delta = amended and bool(fresh) and not force_full
        if approved_rev and base is None and approved_rev != digest:
            print(f"check-plan: no copy of the approved revision {approved_rev} is kept "
                  f"beside the plan, so there is nothing to compare with and this is the "
                  f"full block.")
        print()
        print("check-plan: ---- gate presentation: copy this block into your reply unaltered; the human does not see tool output ----")
        eligible = None
        if delta:
            # After an amendment the human reads what changed, not the plan
            # again: six of one change's nine re-presentations were
            # byte-identical to the block before them.
            lines, eligible = delta_presentation(
                base_text, text, plan_src, tier, base_rev, bool(approved_rev), altitude_lines)
        else:
            lines = gate_presentation(text, plan_src, tier,
                                      {n for n, _ in required}, altitude_lines)
        for line in lines:
            print(line)
        # Inside the block deliberately: a token printed outside it could be
        # quoted by an agent that never showed the block to anyone.
        print()
        token = gate_token(digest)
        print(f"Gate token: {token} — carry it in the Approval "
              f"record as `gate-token: {token}`, which is how a "
              f"later run can tell this presentation was put in front of you.")
        print("check-plan: ---- end of gate presentation ----")
        remember_gate(plan_file, raw, digest, approved_rev, full=not delta)
        if not approved_rev:
            record_dirty(plan_file)

        # What to do with the block, said here because here is where it is
        # needed and the record's revision and token are known. The skill's
        # Output contract used to carry the record's shape and lacked the
        # token, so a record written to the contract failed `--approval`.
        log = os.path.splitext(plan_src)[0] + ".approval.log"
        record = (f'Approved by: "<their message>" (typed at the gate{{}}); '
                  f'plan: {plan_src}@{digest}; gate-token: {token}')
        if delta:
            print(f"check-plan: when the human's own message dictated everything recorded "
                  f"in this block and also said it approves, append to {log}: "
                  + record.format("; covers the amendment it dictated")
                  + " — and carry on without another stop. Each new `Amendments` entry must "
                  "quote that message; `--approval` checks both. A choice among offered "
                  "fixes is not an approval. When their message did not say it approves, or "
                  "any part of this block goes beyond their words, stop for approval of the "
                  "block and record it as: " + record.format(""))
            if eligible:
                print("check-plan: the tests are unchanged, so once approved this amendment "
                      "takes the lighter lane: test edits through `ctdd-tests`' craft-edit "
                      "lane, then the build, the plan's invariant suite and the tests the "
                      "amendment touches. Step 8.3 runs in full once before the review "
                      "packet.")
            else:
                print("check-plan: test expectations changed, so there is no lighter lane: "
                      "once approved, re-enter at the lowest invalidated step.")
        else:
            print(f"check-plan: when the human approves this block, append to {log}: "
                  + record.format("") + " — write `(selected at the gate)` when they picked "
                  f"an option — then verify with `--approval {log}`.")
            print("check-plan: when their reply states a change, record it before anything "
                  "else: a bullet under `Amendments` with `Old:` and `New:` and their words "
                  "quoted, or under `Decisions confirmed in session` for an answered "
                  "question. Run `--gate` again and it prints only what changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
