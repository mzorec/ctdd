#!/usr/bin/env python3
"""check-plan.py — lints a CTDD implementation plan for its mandatory sections.

Usage:
    python3 scripts/check-plan.py plan.md
    <plan text> | python3 scripts/check-plan.py -
    python3 scripts/check-plan.py plan.md --diff surface.txt
    echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 scripts/check-plan.py - --diff surface.txt
    echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 scripts/check-plan.py - --from-description --diff surface.txt

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
at — an edit to an existing test or a contract file is never trivial.\nA diff that only *adds* a test is reported distinctly: that is the\ncompressed bug-fix lane (short plan), not the trivial lane.

Exit 0 = plan OK (sections present, or a trivial claim that survived the check).
Exit 1 = sections missing, or a trivial claim contradicted by the diff.
Exit 2 = usage or input error.
"""

import importlib.util
import re
import sys
from pathlib import Path

REQUIRED = [
    ("decision summary: BLOCKING",  r"blocking"),
    ("decision summary: proceeding", r"proceed(ing)?\s+unless"),
    ("risk level",            r"risk\s*(level)?\s*[:—-]"),
    ("existing behavior",     r"existing\s+behavior"),
    ("assumptions",           r"assumptions?"),
    ("uncovered/ambiguous",   r"(uncovered|ambiguous)"),
    ("proposed tests",        r"(proposed|new).{0,20}tests?"),
    ("contract changes",      r"contract\s+changes?"),
    ("NFR budgets",           r"(nfr|budget)"),
    ("hold-out decision",     r"hold.?out"),
    ("files to change",       r"files\s+(likely\s+)?to\s+change"),
]

# Reason must sit on the SAME line as the risk call: with re.S a bare
# "Risk: trivial —\n" would let the next section masquerade as the reason.
TRIVIAL = re.compile(r"risk\s*(level)?\s*[:—-]\s*trivial\b[^\n]{3,}", re.I)


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


POINTER = re.compile(r"^\s*CTDD-Plan:\s*(\S+)\s*$", re.I | re.M)


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
    if not (path.startswith("docs/plans/") and path.endswith(".md")):
        return None, (f"check-plan: CTDD-Plan pointer {path!r} is not under "
                      f"docs/plans/ with a .md suffix — that is the canonical "
                      f"location the skill writes to.")
    return path, None


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

    from_description = "--from-description" in args
    if from_description:
        args = [a for a in args if a != "--from-description"]

    plan_src = args[0] if args else "-"
    if plan_src == "-" and diff_src == "-":
        print("check-plan: plan and --diff cannot both read stdin")
        return 2

    try:
        text = _read(plan_src)
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
                text = open(resolved, encoding="utf-8").read()
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
        except Exception as exc:
            print(f"check-plan: WARNING — could not load check-spec-surface "
                  f"({exc}); trivial claim NOT cross-checked.", file=sys.stderr)
            print("check-plan: trivial-skip declaration found; cross-check "
                  "unavailable — classification unverified.")
            return 0
        touched, added_only = [], True
        for status, old, new in surface.parse_name_status(diff_text):
            for p in (old, new):
                if p and surface.classify(p) in ("test", "contract"):
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
        print("check-plan: trivial claim stands — the diff touches no "
              "test/contract surface.")
        return 0

    missing = [name for name, pat in REQUIRED
               if not re.search(pat, text, re.IGNORECASE)]
    if missing:
        print("check-plan: MISSING sections — " + ", ".join(missing))
        print("A plan that omits a section hasn't decided it; it has skipped it.")
        return 1
    print("check-plan: all mandatory sections present "
          "(presence, not quality — the review still owns quality).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
