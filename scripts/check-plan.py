#!/usr/bin/env python3
"""check-plan.py — lints a CTDD implementation plan for its mandatory sections.

Usage:  python3 scripts/check-plan.py plan.md      (or pipe the plan on stdin)

Honest scope: this is an omission detector, not a quality gate. It verifies
the required sections EXIST — it cannot tell a considered "Hold-out: not
required — semantics unchanged" from a lazy one. That judgment stays human.
What it converts is silent omission into visible omission: a plan can no
longer simply not mention NFR budgets or the hold-out decision.

Exit 0 = all sections present (or a valid trivial-skip declaration).
Exit 1 = sections missing (listed on stdout).
"""

import re
import sys

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


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if args and args[0] != "-":
        try:
            text = open(args[0], encoding="utf-8").read()
        except OSError as exc:
            print(f"check-plan: cannot read {args[0]}: {exc}")
            return 2
    else:
        text = sys.stdin.read()

    if TRIVIAL.search(text):
        # A declared trivial skip needs only the visible one-liner with a reason.
        print("check-plan: trivial-skip declaration found (risk line + reason). "
              "The human can veto the classification; no further sections required.")
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
