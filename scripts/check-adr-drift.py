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

ADR files are the ones in a folder named `adr` or `adrs`, and in the folder
`adrDir` names in `.ctdd.json` (or `CTDD_ADR_DIR`), read through
check-spec-surface.py so that this script and `--adr-dir` cannot disagree
about where the decisions live.

Exit 0: no ADR lost its last marker.
Exit 1: at least one did — confirm the decision still holds, disclose it, or
supersede it under adr-rules rule 16.
Exit 2: nothing was read — no diff, or a settings file that cannot be read.
"""

import argparse
import importlib.util
import os
import re
import subprocess
import sys

ADR_MARKER = re.compile(r"\bADR-(\d{1,4})\b")
ADR_DIR_RE = re.compile(r"(^|/)adrs?/", re.IGNORECASE)
SKIP_DIRS = {".git", "node_modules", "bin", "obj", "__pycache__", ".vs", "dist"}


def _surface():
    """check-spec-surface.py, which reads the settings for every script, or
    None when it is not beside this file."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "check-spec-surface.py")
    try:
        spec = importlib.util.spec_from_file_location("check_spec_surface_for_drift", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def named_adr_dirs(root=".", surface=None):
    """The ADR folders the repository's settings name, as lower-case paths
    from the root. The `adr`/`adrs` convention needs no naming; this is for a
    repository that keeps its decisions somewhere else and says so in `adrDir`.

    This script knew the convention only. In a repository whose `adrDir` named
    another folder, the ADR files were scanned as code: an ADR titled with its
    own number kept that marker "in the tree", so removing the last real one
    passed as no drift, while `check-spec-surface.py --adr-dir` resolved the
    right folder in the same tree.
    """
    surface = surface or _surface()
    if surface is None:
        return []
    out = []
    for d in surface._setting("CTDD_ADR_DIR", "adrDir", root).split(os.pathsep):
        d = d.strip().replace("\\", "/").strip("/")
        while d.startswith("./"):
            d = d[2:]
        out.append(d.lower())
    return out


def _is_adr_dir(rel_dir, named):
    """True for a folder ADR files live in: by convention, or by name."""
    if ADR_DIR_RE.search("/" + rel_dir + "/"):
        return True
    low = rel_dir.lower()
    return any(low == d or low.startswith(d + "/") for d in named)


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


def markers_in_tree(root=".", named=None):
    """Every marker id the working tree still carries.

    ADR files themselves are excluded: an ADR naming its own number, or the
    number it supersedes, is not code claiming to be governed by it.
    """
    named = named_adr_dirs(root) if named is None else named
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if _is_adr_dir(rel_dir, named):
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


def adr_status(adr_id, root=".", named=None):
    """The `Status` line of the matching ADR file, when one is findable."""
    named = named_adr_dirs(root) if named is None else named
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if not _is_adr_dir(rel_dir, named):
            continue
        for name in sorted(filenames):
            if not name.lower().endswith(".md"):
                continue
            # A file name is read as `resolve_adr` in check-spec-surface.py
            # reads it. This lookup anchored on a digit, so a file named
            # `ADR-0007-slug.md` was "no ADR file found" here, beside a
            # decision that had just lost its last marker, while that script
            # resolved the same file.
            head = re.match(r"(?:adr[-_]?)?0*(\d{1,4})", name, re.I)
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


def orphaned(diff_text, root=".", named=None):
    """Ids whose marker this diff removed and which the tree no longer carries."""
    remaining = markers_in_tree(root, named)
    return [i for i in removed_marker_ids(diff_text) if i not in remaining]


def read_diff(args):
    """(diff_text, why). `why` is set only when no diff could be produced.

    git's exit code is the whole point. An unresolvable base writes to stderr
    and leaves stdout empty, an empty diff removes no marker, so ignoring the
    code turned every bad base into `no ADR lost its last marker` at exit 0:
    a pass claimed over input this checker never read, which is the failure
    shape this plugin records more often than any other. Encoding is pinned
    because a mis-decode would drop marker lines the same silent way.
    """
    if args.stdin:
        return sys.stdin.read(), None
    cmd = ["git", "diff", args.git] + list(args.rest)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", check=False)
    except OSError as exc:
        return None, "git could not be run (%s)" % exc
    if r.returncode != 0:
        detail = [l for l in (r.stderr or "").splitlines() if l.strip()]
        return None, "`git diff %s` exited %d: %s" % (
            args.git, r.returncode, detail[0].strip() if detail else "no detail")
    return r.stdout, None


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
    surface = _surface()
    if surface is None:
        print("check-adr-drift: check-spec-surface.py is not beside this script, "
              "so `adrDir` was not read: only folders named `adr` or `adrs` "
              "count as ADR folders in this run.", file=sys.stderr)
    elif surface.settings_stop("check-adr-drift", args.root):
        return 2
    named = named_adr_dirs(args.root, surface)
    diff_text, why = read_diff(args)
    if diff_text is None:
        print("check-adr-drift: %s. Nothing was read, so nothing is "
              "verified, and this is not a pass." % why)
        return 2
    lost = orphaned(diff_text, args.root, named)
    if not lost:
        print("check-adr-drift: no ADR lost its last marker in this change.")
        return 0
    for adr_id in lost:
        name, status = adr_status(adr_id, args.root, named)
        where = name or "no ADR file found"
        state = f", Status: {status}" if status else ""
        print(f"check-adr-drift: ADR-{adr_id} lost its last marker "
              f"({where}{state}) — nothing in the tree names it now. Confirm the "
              f"decision still holds and re-mark it, or supersede it.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
