#!/usr/bin/env python3
"""check-spec-surface.py — deterministic inventory of the spec surface a diff touches.

Usage:
    git diff --name-status -M | python3 scripts/check-spec-surface.py -
    python3 scripts/check-spec-surface.py name-status.txt
    python3 scripts/check-spec-surface.py --git [extra git-diff args...]

Reads `git diff --name-status` output (use -M so renames are detected) and
classifies every touched path against the SAME test/contract patterns the
spec-edit hook uses — imported from hooks/spec-edit-guard.py, so there is one
definition of "spec surface", and the CTDD_TEST_PATTERNS /
CTDD_CONTRACT_PATTERNS environment overrides apply here identically.

Why this exists: the hook only sees Edit/Write tool events. Bash-mediated
edits (sed -i, patch, git apply), renames (git mv), and deletions (rm) never
reach it. This script closes that lane at review time by looking at the diff
itself instead of the editing tool. It also gives triviality claims a
deterministic counterweight: a change whose diff touches test or contract
surface is not trivial, whatever the narration says.

Honest scope: this is an inventory, not a judgment. It cannot tell a benign
rename from a dropped requirement — it can only make sure a human looks.

Exit codes:
    0  no test/contract/ADR surface touched
    1  spec surface touched (attention, not error — see the summary)
    2  usage or input error
"""

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# One source of truth for "what is a test / contract path": the hook.
# ---------------------------------------------------------------------------

def _load_guard():
    guard_path = Path(__file__).resolve().parent.parent / "hooks" / "spec-edit-guard.py"
    spec = importlib.util.spec_from_file_location("spec_edit_guard", guard_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

try:
    _guard = _load_guard()
    TEST_PATTERNS = _guard.patterns("CTDD_TEST_PATTERNS", _guard.TEST_DEFAULT)
    CONTRACT_PATTERNS = _guard.patterns("CTDD_CONTRACT_PATTERNS", _guard.CONTRACT_DEFAULT)
except Exception as exc:  # standalone copy without the hook alongside
    print(f"check-spec-surface: WARNING — could not load hook patterns ({exc}); "
          "using minimal built-in defaults. Keep this script next to "
          "hooks/spec-edit-guard.py for the shared pattern contract.",
          file=sys.stderr)
    TEST_PATTERNS = [r"(^|/)(tests?|__tests__|specs?)(/|$)"]
    CONTRACT_PATTERNS = [r"(^|/)(contracts?|pacts?)(/|$)", r"\.proto$",
                         r"(^|/)(openapi|swagger|asyncapi)[^/]*\.(ya?ml|json)$"]

# ADRs are review surface too (a changed decision record is a changed "why"),
# but they are not the hook's business, so the pattern lives here.
ADR_PATTERNS = [r"(^|/)adrs?/[^/]+\.md$"]
PACT_HINT = re.compile(r"pact", re.IGNORECASE)


def _matches(path, pats):
    return any(re.search(p, path, re.IGNORECASE) for p in pats)


def classify(path):
    """Return the surface class of one path: 'contract', 'test', 'adr', or None."""
    p = path.replace("\\", "/")
    if _matches(p, CONTRACT_PATTERNS):
        return "contract"
    if _matches(p, TEST_PATTERNS):
        return "test"
    if _matches(p, ADR_PATTERNS):
        return "adr"
    return None


STATUS_WORD = {"A": "added", "M": "modified", "D": "deleted", "T": "type-changed"}


def parse_name_status(text):
    """Yield (status, old_path, new_path_or_None) per name-status line."""
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        if status[:1] in ("R", "C") and len(parts) >= 3:
            yield status, parts[1], parts[2]
        elif len(parts) >= 2:
            yield status, parts[1], None
        # silently skip unparseable lines rather than crash mid-review


def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    if args and args[0] == "--git":
        cmd = ["git", "diff", "--name-status", "-M"] + args[1:]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"check-spec-surface: git failed: {r.stderr.strip()}")
            return 2
        text = r.stdout
    elif args and args[0] != "-":
        try:
            text = open(args[0], encoding="utf-8").read()
        except OSError as exc:
            print(f"check-spec-surface: cannot read {args[0]}: {exc}")
            return 2
    else:
        text = sys.stdin.read()

    findings = {"contract": [], "test": [], "adr": []}
    other = 0

    for status, old, new in parse_name_status(text):
        if status[:1] in ("R", "C"):
            verb = "renamed" if status[:1] == "R" else "copied"
            old_cls, new_cls = classify(old), classify(new)
            if old_cls and not new_cls:
                findings[old_cls].append(
                    f"{verb} OUT of {old_cls} surface: {old} -> {new} "
                    f"(treat as a deletion until shown otherwise)")
            elif new_cls and not old_cls:
                findings[new_cls].append(f"{verb} INTO {new_cls} surface: {old} -> {new}")
            elif old_cls or new_cls:
                findings[old_cls or new_cls].append(f"{verb}: {old} -> {new}")
            else:
                other += 1
        else:
            cls = classify(old)
            if cls:
                word = STATUS_WORD.get(status[:1], status)
                label = f"{word}: {old}"
                if cls == "contract" and PACT_HINT.search(old):
                    label += "  (consumer contract — blast radius includes another team)"
                if cls == "test" and status[:1] == "D":
                    label += "  (a deleted test is a silently dropped requirement unless justified)"
                findings[cls].append(label)
            else:
                other += 1

    touched = any(findings.values())
    print("check-spec-surface: spec-surface inventory (deterministic; "
          "patterns shared with the spec-edit hook, env overrides honored)")
    for cls, title in (("contract", "Contract surface"),
                       ("test", "Test surface"),
                       ("adr", "ADR surface")):
        if findings[cls]:
            print(f"\n{title} ({len(findings[cls])}):")
            for f in findings[cls]:
                print(f"  - {f}")
    print(f"\nOther files touched: {other}")

    if touched:
        print("\nVerdict: SPEC SURFACE TOUCHED — changed tests are changed "
              "requirements, contract diffs are boundary changes, and this "
              "change is not trivial whatever the plan's risk line says. "
              "(exit 1 = attention, not error)")
        return 1
    print("\nVerdict: no test/contract/ADR surface touched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
