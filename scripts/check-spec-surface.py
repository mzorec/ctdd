#!/usr/bin/env python3
"""check-spec-surface.py — deterministic inventory of the spec surface a diff touches.

Usage:
    git diff --name-status -M | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" -
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" name-status.txt
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git [extra git-diff args...]

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

PATTERN_LOAD_ERROR = None
try:
    _guard = _load_guard()
    TEST_PATTERNS = _guard.patterns("CTDD_TEST_PATTERNS", _guard.TEST_DEFAULT)
    CONTRACT_PATTERNS = _guard.patterns("CTDD_CONTRACT_PATTERNS", _guard.CONTRACT_DEFAULT)
except Exception as exc:
    PATTERN_LOAD_ERROR = exc
    TEST_PATTERNS = []
    CONTRACT_PATTERNS = []

# ADRs are review surface too (a changed decision record is a changed "why"),
# but they are not the hook's business, so the pattern lives here.
# `--adr-dir` honours CTDD_ADR_DIR / `.ctdd.json adrDir`; classify() hardcoded
# `adr/`. So the ADR that adr-rules.md rule 4 told you to write — into the
# directory this same script resolved — landed as `other`, and the run reported
# "no test/contract/ADR surface touched": the verdict the trivial lane opens on.
# One script, two definitions. Rule 2 says there is one.
def _adr_patterns():
    pats = [re.compile(r"(^|/)adrs?/[^/]+\.md$", re.IGNORECASE)]
    # The *configured* directory, resolved exactly as `--adr-dir` resolves it —
    # `adr_dirs()` reports what exists on disk, which is a different question and
    # is empty in a repo that has not written its first ADR yet.
    seen = {"adr", "adrs"}
    for d in list(adr_dirs()) + [_setting("CTDD_ADR_DIR", "adrDir", None) or ""]:
        seg = (d or "").strip("/")
        if not seg or seg.lower() in seen:
            continue
        seen.add(seg.lower())
        pats.append(re.compile(rf"(^|/){re.escape(seg)}/[^/]+\.md$", re.IGNORECASE))
    return pats


ADR_PATTERNS = None   # resolved on first use; see ensure_patterns_loaded()

# An ADR marker is a comment naming a decision that governs this file, e.g.
#   // ADR-0017: Domain must not depend on frameworks
# The marker lives with the code it governs, so it moves when the file moves and
# anyone deleting the file sees the reference they are orphaning. That is the
# only pointer between a decision and the code it constrains that does not rot
# independently of what it points at.
# Four digits is adr-tools' and MADR's convention, not a rule: teams number
# ADR-001 and ADR-12 too. A width-locked pattern did not merely fail on those
# — it saw nothing, so the report said nothing, and silence reads as "no
# decision applies". Match any width and compare by value.
ADR_MARKER = re.compile(r"\bADR-(\d{1,4})\b")


def markers_in(path, root=None):
    """The ADR ids a changed file names, in first-seen order."""
    f = os.path.join(_project_root(root), path)
    try:
        with open(f, "r", encoding="utf-8", errors="replace") as fh:
            # Capped like the sibling hook (spec-edit-guard.py reads 200 KB).
            # Uncapped, one large binary in a diff decoded entirely into a str:
            # 7.75s wall clock and the whole file in memory. Two readers of the
            # same marker convention must agree on how much of a file carries it.
            text = fh.read(200_000)
    except (OSError, ValueError):
        return []
    seen, out = set(), []
    for m in ADR_MARKER.finditer(text):
        if m.group(1) not in seen:
            seen.add(m.group(1)); out.append(m.group(1))
    return out


def _setting(env_var, config_key, root="."):
    """Delegates to the hook, which owns configuration for the whole plugin, so
    the scripts and the hook can never resolve a setting differently."""
    try:
        return _guard.setting(env_var, config_key, root)
    except Exception:
        return os.environ.get(env_var, "").strip()


def _setting_with_source(env_var, config_key, root="."):
    if os.environ.get(env_var, "").strip():
        return os.environ[env_var].strip(), env_var
    value = _setting(env_var, config_key, root)
    return value, f"{CONFIG_NAME} ({config_key})" if value else ""


CONFIG_NAME = ".ctdd.json"

_SKIP_DIRS = {".git", "node_modules", "bin", "obj", "dist", "build",
              "packages", "target", "vendor", ".venv", "__pycache__"}


for _stream in (sys.stdout, sys.stderr):
    # A non-ASCII path raised UnicodeEncodeError on a legacy-codepage console,
    # truncating the inventory mid-list and exiting 1 — the same code that means
    # SPEC SURFACE TOUCHED, so a crash read as a finding while step 8.5 compared
    # a silently short inventory against "Files likely to change".
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def _project_root(root=None):
    """`--git` mode anchors to CLAUDE_PROJECT_DIR; the ADR lookups defaulted to
    cwd, so running from a subdirectory returned a confidently wrong directory
    rather than the ambiguity the escape hatch is written for — and wrote 0001
    beside an existing series."""
    if root:
        return root
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return env
    # `git diff --name-status` emits paths from the repository root while
    # `git ls-files --others` is cwd-relative, so falling back to cwd made every
    # path resolve against the wrong base when run from a subdirectory: markers
    # unread, ADRs unresolved, untracked files invisible — all silently, and all
    # under-reporting rather than erroring.
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "."


def adr_dirs(root=None):
    """Directories this repository keeps ADRs in — discovered, never assumed.

    `docs/adr/` is where *this* plugin writes a new ADR. It is not where every
    repository keeps them: `adr/`, `doc/adr/`, `architecture/adrs/` are all in
    the wild. Guessing a fixed list means a correctly-marked test in a repo that
    organises differently resolves to nothing and gets reported as a broken
    pointer — a false alarm on a healthy repo, which is worse than silence.
    Set CTDD_ADR_DIR (os.pathsep-separated, repo-relative) for a layout the
    `adrs?` convention does not cover.
    """
    root = _project_root(root)
    override = _setting("CTDD_ADR_DIR", "adrDir", root)
    if override:
        return [d for d in (x.strip() for x in override.split(os.pathsep))
                if d and os.path.isdir(os.path.join(root, d))]
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in _SKIP_DIRS and not d.startswith(".")]
        if os.path.basename(dirpath).lower() in ("adr", "adrs"):
            rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
            found.append(rel)
    return sorted(found)


def adr_dir(root=None):
    """The one directory this repository keeps ADRs in — (path, reason).

    Read and write must agree. When they disagree the numbering breaks: the
    writer scans an empty `docs/adr/`, writes 0001 beside an `adr/` that already
    has 0001-0014, and the reader then finds two ADRs with the same number.
    Resolution is therefore single and explicit:

      1. CTDD_ADR_DIR when set — the human's decision, and it wins.
      2. The one existing ADR directory, when exactly one exists.
      3. Ambiguous when several exist: stop and ask rather than pick.
      4. `docs/adr` when the repository has none yet — a new convention, and
         the only case where this plugin gets to choose.
    """
    root = _project_root(root)
    override, source = _setting_with_source("CTDD_ADR_DIR", "adrDir", root)
    if override:
        first = [x.strip() for x in override.split(os.pathsep) if x.strip()][:1]
        return (first[0] if first else None), source
    found = adr_dirs(root)
    if len(found) == 1:
        return found[0], "the repository's existing ADR directory"
    if len(found) > 1:
        return None, "ambiguous: " + ", ".join(found)
    return "docs/adr", "no existing ADR directory; this would create one"


# `ADR-NNNN-slug.md` is a common convention and the match was position-anchored
# to a digit, so every such file resolved to nothing: a repository whose ADRs are
# named that way got "BROKEN ADR markers — no such ADR file exists" on a healthy
# tree, which adr_dirs' own docstring calls worse than silence.
def resolve_adr(adr_id, root=None, dirs=None):
    """The ADR file for `NNNN`, or None."""
    root = _project_root(root)
    for base in (adr_dirs(root) if dirs is None else dirs):
        d = os.path.join(root, base)
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for name in names:
            if not name.lower().endswith(".md"):
                continue
            lead = re.match(r"(?:adr[-_]?)?0*(\d{1,4})", name, re.I)
            if lead and int(lead.group(1)) == int(adr_id):
                return f"{base}/{name}" if base != "." else name
    return None
# A path with no extension and no directory separator is, in a name-status
# diff, almost always a submodule pointer. Treated as `other` it read as
# "no surface touched"; it is unknown content, which is different.
GITLINK_RX = re.compile(r"^[^/.]+$")

PACT_HINT = re.compile(r"pact", re.IGNORECASE)


def ensure_patterns_loaded():
    if PATTERN_LOAD_ERROR is not None:
        raise RuntimeError(
            "could not load the authoritative patterns from "
            f"hooks/spec-edit-guard.py: {PATTERN_LOAD_ERROR}"
        )


def _matches(path, pats):
    return any(pattern.search(path) for pattern in pats)


def classify(path):
    """Return the surface class of one path: 'contract', 'test', 'adr', or None."""
    ensure_patterns_loaded()
    p = path.replace("\\", "/")
    if _matches(p, CONTRACT_PATTERNS):
        return "contract"
    if _matches(p, TEST_PATTERNS):
        return "test"
    if _matches(p, ADR_PATTERNS if ADR_PATTERNS is not None else _adr_patterns()):
        return "adr"
    return None


STATUS_WORD = {"A": "added", "M": "modified", "D": "deleted", "T": "type-changed"}


def unquote_git_path(path):
    """Undo git's C-style quoting of non-ASCII paths.

    With core.quotePath at its default, `git diff --name-status` emits
    `"tests/Ra\\304\\215unTests.cs"` for a path containing c-caron. The leading
    quote defeats every path pattern here, so a modified test file in any
    non-ASCII codebase classified as untouched surface and passed CI as trivial.
    The piped caller cannot set git's flags, so this is undone in the parser.
    """
    if len(path) < 2 or not (path.startswith('"') and path.endswith('"')):
        return path
    inner = path[1:-1]
    try:
        # octal escapes decode to bytes, which git emitted as UTF-8
        return inner.encode("latin-1", "backslashreplace").decode(
            "unicode_escape").encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return inner


def parse_name_status(text):
    """Return (entries, malformed) for `git diff --name-status` text.

    `entries` is a list of (status, old_path, new_path_or_None). `malformed`
    holds any non-empty line that could not be parsed. It is returned rather
    than accumulated in module state so that a caller cannot forget to reset it
    between runs, and cannot silently inherit another caller's leftovers.
    """
    entries, malformed = [], []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        # Exact field counts. A rename or copy carries three columns; every other
        # status carries two. Accepting ">= 2" and reading only column two let
        # `M<TAB>README.md<TAB>tests/Hidden.cs` report clean while a changed test
        # sat in column three — the subset-verified-and-passed shape reached
        # through the record's own shape. Too many fields is as malformed as too
        # few, and a line we cannot parse is input we did not see: reporting a
        # clean verdict over discarded input is what this script exists to stop.
        if status[:1] in ("R", "C"):
            if len(parts) == 3:
                entries.append((status, unquote_git_path(parts[1]),
                                unquote_git_path(parts[2])))
            else:
                malformed.append(raw)
        elif len(parts) == 2:
            entries.append((status, unquote_git_path(parts[1]), None))
        else:
            malformed.append(raw)
    return entries, malformed


def plan_paths_from(path):
    """Backticked repository paths named anywhere in the plan."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            body = fh.read(200_000)
    except OSError:
        return None
    out = set()
    for m in re.finditer(r"`([^`\n]{3,160})`", body):
        tok = m.group(1).strip()
        if "/" in tok and re.search(r"\.[A-Za-z0-9]{1,6}$", tok) and " " not in tok:
            out.add(tok)
    return out


def main():
    args = sys.argv[1:]
    # --plan <path>: compare the inventory against the plan in BOTH
    # directions. Report-only; the verdict is unchanged.
    plan_paths = None
    if "--plan" in args:
        i = args.index("--plan")
        if i + 1 < len(args):
            plan_paths = plan_paths_from(args[i + 1])
            args = args[:i] + args[i + 2:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    if "--adr-dir" in args:
        # One answer for every step that reads or writes an ADR, so the two
        # cannot drift apart and split the numbering.
        path, why = adr_dir()
        if path is None:
            print(f"check-spec-surface: ADR directory {why}.")
            print("  Set CTDD_ADR_DIR to the one this repository uses. Writing "
                  "into the wrong one restarts the numbering beside an existing "
                  "series.")
            return 1
        print(path)
        print(f"  ({why})", file=sys.stderr)
        return 0

    try:
        ensure_patterns_loaded()
    except RuntimeError as exc:
        print(f"check-spec-surface: {exc}. No classification was attempted.",
              file=sys.stderr)
        return 2

    if args and args[0] == "--git":
        # Anchor to the project root: `git ls-files --others` is relative to the
        # current directory, so running from a subdirectory silently omits a new
        # test living elsewhere in the repo. The agent changes directory often.
        repo = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        # Default to HEAD, not a bare `git diff`. A bare diff compares the working
        # tree against the *index*, so a test that has been modified and staged
        # reports as no surface touched at all — the fail-silent shape this whole
        # script exists to prevent. HEAD covers staged and unstaged together.
        # `--allow-empty` is ours, not git's: forwarding it produced
        # "git failed: usage: git diff" and exit 2, so the flag was unreachable in
        # the one mode where an empty diff is most likely — a clean tree.
        git_args = [a for a in args[1:] if a != "--allow-empty"] or ["HEAD"]
        cmd = ["git", "diff", "--name-status", "-M", *git_args]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=repo)
        if r.returncode != 0:
            print(f"check-spec-surface: git failed: {r.stderr.strip()}")
            return 2
        # A bare `git diff` reports nothing for a file that is not yet tracked, so a
        # change whose only spec artifact is a NEW test file would read as touching no
        # surface at all. List untracked files alongside it and mark them added, so the
        # convenience mode cannot quietly reopen the blind spot the pipeline closes.
        u = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                           capture_output=True, text=True, cwd=repo)
        if u.returncode != 0:
            # Failing quietly here would under-report surface, which is the one
            # outcome this script must never produce.
            print(f"check-spec-surface: could not list untracked files: {u.stderr.strip()}")
            return 2
        untracked = "".join(f"A\t{line}\n"
                            for line in u.stdout.splitlines() if line.strip())
        text = r.stdout + untracked
    elif args and args[0] != "-":
        try:
            text = open(args[0], encoding="utf-8").read()
        except OSError as exc:
            print(f"check-spec-surface: cannot read {args[0]}: {exc}")
            return 2
    else:
        text = sys.stdin.read()

    findings = {"contract": [], "test": [], "adr": []}
    other, unread = 0, []

    entries, malformed = parse_name_status(text)
    for status, old, new in entries:
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
            elif GITLINK_RX.match(old):
                unread.append(old)
            else:
                other += 1

    # Unknown content cannot clear the lane. SKILL.md 3.3 opens the trivial lane
    # on this exact verdict string, and a submodule bump can carry any change.
    touched = any(findings.values()) or bool(unread)
    if not text.strip() and "--allow-empty" not in sys.argv:
        print("check-spec-surface: empty input — nothing was inspected, so no "
              "verdict is given. If the diff really is empty, pass --allow-empty.")
        return 2

    if malformed:
        print(f"check-spec-surface: {len(malformed)} unparseable input line(s); "
              f"the inventory is incomplete, so no verdict is given. First: "
              f"{malformed[0][:80]!r}. Expected tab-separated `git diff --name-status` output.")
        return 2

    print("check-spec-surface: spec-surface inventory (deterministic; "
          "patterns shared with the spec-edit hook, env overrides honored)")
    if plan_paths is not None:
        # 8.5 stops only when the inventory EXCEEDS the plan. The deficit is
        # unhandled: a plan naming `openapi.yaml — relax the amount constraint`
        # whose contract file is never edited leaves the inventory a subset, no
        # stop fires, and an approved contract change simply does not ship.
        seen = {f.split(": ", 1)[-1].split("  (")[0].strip()
                for group in findings.values() for f in group}
        seen |= set(unread)
        untouched = sorted(q for q in plan_paths
                           if not any(q in s or s in q for s in seen))
        unplanned = sorted(s for s in seen
                           if not any(q in s or s in q for q in plan_paths))
        if untouched:
            print("\nPlanned but untouched:")
            for q in untouched:
                print(f"  - {q}")
            print("  An approved change that never reaches its file does not "
                  "ship. Report-only: this does not change the verdict.")
        if unplanned:
            print("\nUnplanned surface:")
            for s in unplanned:
                print(f"  - {s}")

    if unread:
        # A gitlink is a change of *unknown content*: the parent diff shows only
        # `M<TAB>sub`, and git cannot see through it, so a submodule whose tests
        # changed `assert 1` to `assert 0` counted as `other` and the verdict read
        # "no test/contract/ADR surface touched" — the trivial-lane precondition,
        # verbatim. Unknown content is not the same as no surface.
        print("\nUnread surface (submodule pointers) — content not visible to this "
              "diff:")
        for u in unread:
            print(f"  - {u}")
        print("  A submodule bump can carry any change. Inspect it in its own "
              "repository, or treat this change as plan-gated.")

    for cls, title in (("contract", "Contract surface"),
                       ("test", "Test surface"),
                       ("adr", "ADR surface")):
        if findings[cls]:
            print(f"\n{title} ({len(findings[cls])}):")
            for f in findings[cls]:
                print(f"  - {f}")
    print(f"\nOther files touched: {other}")

    # Governing ADRs, from the markers the changed files carry. This reports
    # relevance, never absence: a decision with no marker anywhere is invisible
    # here, so the wording must not let silence read as "no ADR applies".
    changed = [new_p if status[:1] in ("R", "C") else old_p
               for status, old_p, new_p in entries]
    dirs = adr_dirs()
    governing, broken = {}, {}
    for path in changed:
        for adr in markers_in(path):
            target = resolve_adr(adr, dirs=dirs)
            (governing if target else broken).setdefault(
                target or adr, []).append(path)
    if governing:
        print(f"\nGoverning ADRs named by changed files ({len(governing)}):")
        for target in sorted(governing):
            print(f"  - {target}")
            for src in sorted(set(governing[target])):
                print(f"      marked in {src}")
    if broken:
        print(f"\nBROKEN ADR markers ({len(broken)}):")
        for adr in sorted(broken):
            print(f"  - ADR-{adr} is named by "
                  f"{', '.join(sorted(set(broken[adr])))} but no such ADR file exists")
        if dirs:
            print("    A marker pointing at nothing is a lost decision, not an absent one.")
        else:
            print("    No ADR directory was found in this repository, so these could "
                  "not be resolved at all. Set CTDD_ADR_DIR if the decisions live "
                  "somewhere the `adr`/`adrs` convention does not cover — this is "
                  "not evidence that the ADRs are missing.")

    if touched:
        print("\nVerdict: SPEC SURFACE TOUCHED — changed tests are changed "
              "requirements, contract diffs are boundary changes, and this "
              "change is not trivial whatever the plan's risk line says. "
              "(exit 1 = attention, not error)")
        return 1
    print("\nVerdict: no test/contract/ADR surface touched. ADR markers report "
          "relevance only — no marker does not prove no decision applies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
