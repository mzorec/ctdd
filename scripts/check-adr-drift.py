#!/usr/bin/env python3
"""Report ADRs whose last `ADR-NNNN` marker this change removes.

    python3 check-adr-drift.py --git <diff-base> [extra git-diff args...]
    git diff <base> | python3 check-adr-drift.py -

An accepted ADR goes quietly stale when the code it governs is rewritten and
its marker goes with it: nothing in the tree names the decision any more, so no
later reader is pointed at a record that may already be false. Marker *removal*
is the cheap mechanical signal for that. A whole-repo audit is the obvious
alternative and the wrong one: it reports the same never-marked ADRs on every
run, which is the shape findings #24/#27 record people learning to ignore.

Exit 0: no ADR lost its last marker.
Exit 1: at least one did — confirm the decision still holds, disclose it, or
supersede it under adr-rules rule 16.
"""

import argparse
import os
import re
import subprocess
import sys

ADR_MARKER = re.compile(r"\bADR-(\d{1,4})\b")
ADR_DIR_RE = re.compile(r"(^|/)adrs?/", re.IGNORECASE)
SKIP_DIRS = {".git", "node_modules", "bin", "obj", "__pycache__", ".vs", "dist"}


def normalize(adr_id):
    """`ADR-7`, `ADR-007` and `ADR-0007` are the same decision."""
    return str(int(adr_id))


def removed_marker_ids(diff_text):
    """Marker ids on removed lines, first-seen order.

    `---` file headers start with a minus too and would otherwise read as
    deleted content, so they are skipped explicitly.
    """
    ids = []
    for line in diff_text.splitlines():
        if not line.startswith("-") or line.startswith("---"):
            continue
        for m in ADR_MARKER.finditer(line):
            key = normalize(m.group(1))
            if key not in ids:
                ids.append(key)
    return ids


def markers_in_tree(root="."):
    """Every marker id the working tree still carries.

    ADR files themselves are excluded: an ADR naming its own number, or the
    number it supersedes, is not code claiming to be governed by it.
    """
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if ADR_DIR_RE.search("/" + rel_dir + "/"):
            continue
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            for m in ADR_MARKER.finditer(text):
                found.add(normalize(m.group(1)))
    return found


def adr_status(adr_id, root="."):
    """The `Status` line of the matching ADR file, when one is findable."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if not ADR_DIR_RE.search("/" + rel_dir + "/"):
            continue
        for name in sorted(filenames):
            if not name.lower().endswith(".md"):
                continue
            head = re.match(r"0*(\d{1,4})", name)
            if not head or normalize(head.group(1)) != adr_id:
                continue
            with open(os.path.join(dirpath, name), "r",
                      encoding="utf-8", errors="ignore") as fh:
                for line in fh.read().splitlines():
                    m = re.match(r"\s*-?\s*\*{0,2}Status:?\*{0,2}\s*(.+)", line, re.I)
                    if m:
                        return name, m.group(1).strip().strip("*")
            return name, None
    return None, None


def orphaned(diff_text, root="."):
    """Ids whose marker this diff removed and which the tree no longer carries."""
    remaining = markers_in_tree(root)
    return [i for i in removed_marker_ids(diff_text) if i not in remaining]


def read_diff(args):
    if args.stdin:
        return sys.stdin.read()
    cmd = ["git", "diff", args.git] + list(args.rest)
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--git", metavar="BASE")
    ap.add_argument("--root", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    ap.add_argument("rest", nargs="*")
    argv = list(sys.argv[1:] if argv is None else argv)
    ap.set_defaults(stdin=False)
    if "-" in argv:
        argv.remove("-")
        args = ap.parse_args(argv)
        args.stdin = True
    else:
        args = ap.parse_args(argv)
        if not args.git:
            print("check-adr-drift: pass --git <base> or pipe a diff and pass -")
            return 2
    lost = orphaned(read_diff(args), args.root)
    if not lost:
        print("check-adr-drift: no ADR lost its last marker in this change.")
        return 0
    for adr_id in lost:
        name, status = adr_status(adr_id, args.root)
        where = name or "no ADR file found"
        state = f", Status: {status}" if status else ""
        print(f"check-adr-drift: ADR-{adr_id} lost its last marker "
              f"({where}{state}) — nothing in the tree names it now. Confirm the "
              f"decision still holds and re-mark it, or supersede it.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
