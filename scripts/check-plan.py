#!/usr/bin/env python3
"""check-plan.py — lints a CTDD implementation plan for its mandatory sections.

Usage:
    python3 scripts/check-plan.py plan.md
    <plan text> | python3 scripts/check-plan.py -
    python3 scripts/check-plan.py plan.md --diff surface.txt
    echo "$CI_MERGE_REQUEST_DESCRIPTION" | python3 scripts/check-plan.py - --diff surface.txt

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

Exit 0 = plan OK (sections present, or a trivial claim that survived the check).
Exit 1 = sections missing, or a trivial claim contradicted by the diff.
Exit 2 = usage or input error.
"""

import importlib.util
import re
import sys
from pathlib import Path

REQUIRED = [
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

    plan_src = args[0] if args else "-"
    if plan_src == "-" and diff_src == "-":
        print("check-plan: plan and --diff cannot both read stdin")
        return 2

    try:
        text = _read(plan_src)
    except OSError as exc:
        print(f"check-plan: cannot read {plan_src}: {exc}")
        return 2

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
        touched = []
        for status, old, new in surface.parse_name_status(diff_text):
            for p in (old, new):
                if p and surface.classify(p) in ("test", "contract"):
                    touched.append(p)
        if touched:
            shown = ", ".join(dict.fromkeys(touched[:3]))
            more = "" if len(set(touched)) <= 3 else f" (+{len(set(touched)) - 3} more)"
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
