#!/usr/bin/env python3
"""check-plan.py — lints a CTDD implementation plan for its mandatory sections.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" plan.md
    <plan text> | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" -
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" plan.md --diff surface.txt
    echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" - --diff surface.txt
    echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-plan.py" - --from-description --diff surface.txt

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
compressed bug-fix lane (short plan), not the trivial lane.

Exit 0 = plan OK (sections present, or a trivial claim that survived the check).
Exit 1 = sections missing, or a trivial claim contradicted by the diff.
Exit 2 = usage or input error.
"""

import importlib.util
import hashlib
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
]

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
_BULLET_NAME = re.compile(r"^\s*[-*]\s+[`'\"]?([A-Za-z_][\w.]*)", re.M)


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


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

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
        print(plan_dir())
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
        text = strip_fences(_read(plan_src))
    except OSError as exc:
        print(f"check-plan: cannot read {plan_src}: {exc}")
        return 2

    if from_description:
        resolved, err = _resolve_pointer(text)
        if err:
            print(err)
            return 1
        if resolved is not None:
            try:
                text = strip_fences(open(resolved, encoding="utf-8").read())
            except OSError:
                print(f"check-plan: MR points at {resolved}, but that file is not "
                      f"in the repository. Most likely docs/plans/ is git-ignored — "
                      f"CI can only validate a plan it can see. Either commit "
                      f"docs/plans/ (the plan becomes a PR-linked audit trail), or "
                      f"drop the pointer and paste the plan into the description "
                      f"(then CI validates that copy instead).")
                return 1
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
    # step 8's Enter ("at least one lane named a test") can never be met, after a
    # human has already approved. Reachable on a mechanical refactor in an
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
    if post_approval:
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
        want = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
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
        print(f"check-plan: approval record verified for revision {want}.")

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
    for m in re.finditer(r"`([^`\n]{2,120})`", text):
        tok = m.group(1).strip()
        if "/" not in tok and "." not in tok:
            continue
        if re.search(r"[*?]|/\s*$|\(\+[^)]*\)|\bTBD\b|\.\.\.", tok):
            vague.append(tok)
    if vague:
        print("check-plan: UNRESOLVED PATHS — " + ", ".join(sorted(set(vague))[:8]))
        print("Field rule 9 requires exact file paths; a wildcard, a bare directory, "
              "`(+ tests)` or `TBD` names no file.")
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
    for field in ("contract", "hold-out", "ADR"):
        if not re.search(rf"{field.replace('-', '.?')}\s*[:=—–-]", cat, re.I):
            print(f"check-plan: the categorical line names no `{field}:` field — "
                  f"{cat.strip()[:70]!r}")
            print("An absent field is not a declared one; it silences the check "
                  "that reads it.")
            return 1

    tier = plan_tier(text)
    required = required_for(tier)

    # A section appearing twice is a corrupted plan, not a complete one. The
    # 2026-08-03 session rewrote its plan 28 times with 16 silent-failing `sed`
    # calls and spliced a duplicate section in; the agent found it by hand, and
    # this checker passed the corrupt file 19/19 because it only ever asked
    # whether each heading was present at least once.
    # The categorical line (`Risk: ... · contract: ... · hold-out: ...`) is matched
    # by the `risk level` pattern too, because that pattern makes `level` optional
    # on purpose. It is one line by construction, so exclude it from the count
    # rather than loosen the pattern that the gate depends on.
    duplicated = []
    for name, pat in required:
        # `find` returns -1 on a final line with no trailing newline, which
        # sliced to text[start:-1] and dropped that line's last character.
        lines = []
        for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            end = text.find("\n", m.start())
            lines.append(text[m.start():] if end < 0 else text[m.start():end])
        real = [l for l in lines if not CATEGORICAL_LINE.search(l)]
        if len(real) > 1:
            duplicated.append((name, len(real)))
    if duplicated:
        print("check-plan: DUPLICATED sections — " +
              ", ".join(f"{n} (x{c})" for n, c in duplicated))
        print("A section written twice is a corrupted plan; the gate cannot tell "
              "which copy the human approved.")
        return 1

    # A required hold-out has to name the work, or the human cannot start it.
    # 2026-08-03 wrote `request: 2 sealed tests written and withheld by the
    # human` — the unbounded phrasing plan-format rule 6 exists to replace — and
    # the human had to ask "what is my task".
    holdout = HOLDOUT_BLOCK.search(text)
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
        print(f"check-plan: MISSING sections for a {tier} plan — " + ", ".join(missing))
        print("A plan that omits a section hasn't decided it; it has skipped it.")
        return 1
    # Gate-reading cost, reported not enforced. Plans have run 5,432 (the canonical
    # example), 17,801, 31,448 and 57,321 characters; the last is ~31 minutes of
    # reading before a human can approve. Nobody chose that — it accrued over 28
    # amendment rounds. A number on the screen at the moment of writing is the
    # cheapest thing that makes the cost visible; the tier already sets the floor.
    words = len(text.split())
    if words > 1500:
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
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    print(f"check-plan: plan revision {digest} — carry it in the Approval record "
          f"and the packet as `plan: <path>@{digest}`.")
    print(f"check-plan: all mandatory sections present for a {tier} plan "
          f"({len(required)} of {len(REQUIRED)}; presence, not quality — the "
          f"review still owns quality).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
