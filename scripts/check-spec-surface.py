#!/usr/bin/env python3
"""check-spec-surface.py — deterministic inventory of the spec surface a diff touches.

Usage:
    git diff --name-status -M | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" -
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" name-status.txt
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git [extra git-diff args...]
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git <base> --plan <plan-path>
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-spec-surface.py" --git <base> [--plan <plan-path>] --stat [--patch <file>]

--stat prints `git diff --stat` against the base and --patch writes the full
diff to a file, both with the files git does not track yet included. They are
taken from a copy of the index, so the real one is never changed: nothing is
staged, unstaged or reset. With --plan the plan's own untracked files beside
it are left out. Neither prints the inventory or gives a verdict; exit 0.

--plan compares the inventory against the plan in both directions and reports
three things, none of which moves the verdict or the exit code: planned files
the diff never touched, touched surface the plan never named, and production
files with no row under the plan's `## Intended change`. That last one is
silent when the plan has no such section, which is every plan before 7.12
appends one and every plan in the `red pause: skip` lane. The plan's own
artifacts beside it — the verify, red-state, pin-state and approval logs and
the pre-implementation diff — are excluded by filename stem, and so are the
files `check-plan.py --gate` found dirty before the plan had any approval
(`<plan>.gate-dirty.txt`) and, with `--baseline "<step-0 Baseline line>"`, the
files that line lists as already dirty. Planned files are read from the plan's
`Files likely to change` section only.

A diff that changes `.ctdd.json`, the workflow's own settings, is listed under
`Workflow settings` and counts as spec surface: that file decides what the
rest of this inventory calls a test, a contract or an ADR. With `--git` every
path is then classified under the settings the diff base had as well as under
the current ones. A settings file that cannot be read stops the run with exit
2, and so does a key this plugin reads holding a value it cannot read.

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
    2  usage or input error, or a settings file that cannot be read
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
_guard = None
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
def _adr_patterns(named=None):
    """`named` is the directories another revision of the settings file names;
    without it, the ones this repository has and the one its settings name."""
    pats = [re.compile(r"(^|/)adrs?/[^/]+\.md$", re.IGNORECASE)]
    # The *configured* directory, resolved exactly as `--adr-dir` resolves it —
    # `adr_dirs()` reports what exists on disk, which is a different question and
    # is empty in a repo that has not written its first ADR yet.
    seen = {"adr", "adrs"}
    if named is None:
        named = list(adr_dirs()) + [_setting("CTDD_ADR_DIR", "adrDir", None) or ""]
    for d in named:
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


def settings_stop(who, root=None):
    """Say what is wrong with the settings file; True when the run stops.

    A file that cannot be read, or a key this plugin reads that cannot, stops
    every script that reads settings: each would fall back to its defaults
    while the repository says otherwise, and pass. A key this plugin does not
    read is one line on stderr, where it reaches whoever runs the script
    without becoming part of what the script reports.
    """
    if _guard is None:
        return False
    stop, notes = _guard.settings_problems(root)
    for line in notes:
        print(f"{who}: {line}", file=sys.stderr)
    for line in stop:
        print(f"{who}: {line}")
    if stop:
        print(f"{who}: none of the file's settings are in force until that is "
              f"fixed, so nothing was checked and this is not a pass. The file "
              f"is the human's to change: tell them what is wrong with it.")
    return bool(stop)


def is_settings(path):
    """True for the workflow's own settings file, wherever it sits in the
    path: a diff's paths start at the repository's top, and a project that is
    one folder of it keeps the file in that folder."""
    return os.path.basename((path or "").replace("\\", "/")) == CONFIG_NAME


def settings_at_base(repo, git_args):
    """The settings as the diff base held them: a dict, empty when the base
    had no settings file or one that could not be read, and None when git
    cannot say which revision the diff starts from."""
    rev = next((a for a in git_args if not a.startswith("-")), "HEAD")
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        # `--revs-only` prints nothing for an argument that is a path, so a
        # diff limited to some paths and naming no revision is not read as
        # starting from one of them.
        told = subprocess.run(["git", "rev-parse", "--revs-only", rev], cwd=repo,
                              capture_output=True, text=True, env=env)
        shas = told.stdout.split() if told.returncode == 0 else []
        # `A..B` and `A...B` print the revision the diff starts from with a
        # caret; a single revision is that revision.
        base = next((s[1:] for s in shas if s.startswith("^")),
                    shas[0] if shas else None)
        if not base:
            return None
        shown = subprocess.run(["git", "show", f"{base}:./{CONFIG_NAME}"], cwd=repo,
                               capture_output=True, env=env)
    except OSError:
        return None
    if shown.returncode != 0:
        return {}
    return _guard.parse_config(shown.stdout)[0]


def patterns_under(config):
    """(contracts, tests, adrs) as `config`, a settings dict, defines them. A
    list that does not compile reads as the defaults: the scripts refused to
    run on it at that revision, and the defaults are the widest reading left."""
    def of(env_var, default):
        try:
            return _guard.patterns(env_var, default, config=config)
        except ValueError:
            return _guard.patterns(env_var, default, config={})
    named = _guard.setting("CTDD_ADR_DIR", "adrDir", config=config)
    return (of("CTDD_CONTRACT_PATTERNS", _guard.CONTRACT_DEFAULT),
            of("CTDD_TEST_PATTERNS", _guard.TEST_DEFAULT),
            _adr_patterns(named.split(os.pathsep)))


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


def _class_under(path, contracts, tests, adrs):
    """`adrs` is a function, so the ADR directories are looked for only when
    the path is neither a contract nor a test."""
    p = path.replace("\\", "/")
    if _matches(p, contracts):
        return "contract"
    if _matches(p, tests):
        return "test"
    if _matches(p, adrs()):
        return "adr"
    return None


def classify(path):
    """Return the surface class of one path: 'contract', 'test', 'adr', or None."""
    ensure_patterns_loaded()
    return _class_under(
        path, CONTRACT_PATTERNS, TEST_PATTERNS,
        lambda: ADR_PATTERNS if ADR_PATTERNS is not None else _adr_patterns())


STATUS_WORD = {"A": "added", "M": "modified", "D": "deleted", "T": "type-changed"}

EARLIER_SETTINGS = "  (surface under the settings the diff base had, not under these)"
SETTINGS_WHY = (
    "  This file decides what the checks read: which paths are test, contract "
    "and ADR surface, and the layers and harnesses a plan is checked against. "
    "Changing it changes the workflow, so it counts as spec surface: the change "
    "summary says what changed in it and why, and a human decides it.")


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


def _files_heading():
    """The `Files likely to change` heading, from check-plan.py's own REQUIRED
    list, so the two scripts cannot disagree on which line opens the section."""
    path = Path(__file__).resolve().parent / "check-plan.py"
    spec = importlib.util.spec_from_file_location("check_plan_for_surface", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return re.compile(dict(mod.REQUIRED)["files to change"], re.I)


NO_FILES_SECTION = "no-files-section"


def plan_paths_from(path):
    """Backticked repository paths under the plan's `Files likely to change`.

    That section only. Reading every backticked path in the document made
    "planned" mean "mentioned": a legacy file cited as evidence in `Existing
    behavior`, an amendment's old location and every pin's test file were all
    reported as planned files the diff never touched, on one real change at
    three consecutive runs. `None` when the plan cannot be read, and
    `NO_FILES_SECTION` when it has no such section, which the caller reports
    rather than falling back to the whole document - the fallback is the
    defect.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            body = fh.read(200_000)
    except OSError:
        return None
    heading = _files_heading()
    lines = body.split("\n")
    start = next((n for n, l in enumerate(lines) if heading.match(l)), None)
    if start is None:
        return NO_FILES_SECTION
    # The heading line itself may carry the list (`Files likely to change:
    # `a`, `b``); after it, bullets, their indented continuations and blank
    # lines, ending at the next unindented line that is not a bullet - the
    # next section's label.
    block = [lines[start]]
    for line in lines[start + 1:]:
        if line.strip() and not line[:1].isspace() \
                and not line.lstrip().startswith(("-", "*", "|")):
            break
        block.append(line)
    out = set()
    # A table's first cell is read with or without backticks, as
    # `intended_change_paths` reads its rows: a table that does not use them
    # would otherwise extract nothing and switch the comparison off.
    for line in block:
        if line.lstrip().startswith("|"):
            cell = line.strip().strip("|").split("|")[0].strip().strip("`").strip()
            if "/" in cell and _ROW_PATH.match(cell):
                out.add(cell)
    for m in re.finditer(r"`([^`\n]{3,160})`", "\n".join(block)):
        tok = m.group(1).strip()
        if "/" in tok and re.search(r"\.[A-Za-z0-9]{1,6}$", tok) and " " not in tok:
            out.add(tok)
    return out


def baseline_dirty(line):
    """([paths], capped) — the staged, unstaged and untracked names a step-0
    `Baseline:` line lists, as `gen-baseline.py` prints it.

    `capped` is True when a field ended in `+N more`: the line names only the
    first few, so the rest are not known here and stay reported.
    """
    names, capped = [], False
    for m in re.finditer(r"\b(?:staged|unstaged|untracked)=([^;]*)", line or ""):
        value = m.group(1).strip()
        if value.endswith("."):
            value = value[:-1]
        for name in (v.strip() for v in value.split(",")):
            if not name or name == "none":
                continue
            if re.fullmatch(r"\+\d+ more", name):
                capped = True
                continue
            names.append(name.replace("\\", "/"))
    return names, capped


def diff_with_untracked(repo, base_args, want_stat, patch_out, is_plan_artifact=None):
    """Print the stat, and write the full diff, of the working tree against
    the base - files git does not track yet included - without touching the
    index.

    `git diff <base>` leaves untracked files out, and a change's new files are
    untracked until someone stages them. The way to get them in is to mark
    them intent-to-add, and doing that to the real index changes what the
    repository's owner sees staged. So the marking is done to a copy: git is
    pointed at it with GIT_INDEX_FILE for these commands only.

    Two kinds of untracked file stay out, because neither is the change: the
    file `--patch` writes, which a second run would otherwise embed in itself,
    and, with `--plan`, the plan's own logs beside it.
    """
    import shutil
    import tempfile

    def git(args, env=None, raw=False):
        merged = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
        merged.update(env or {})
        if raw:
            return subprocess.run(["git", *args], cwd=repo, capture_output=True, env=merged)
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=merged)

    def failed(what, run):
        err = run.stderr
        if not isinstance(err, str):
            err = err.decode("utf-8", "replace")
        print(f"check-spec-surface: {what}: {err.strip()}")
        return 2

    where = git(["rev-parse", "--git-path", "index"])
    if where.returncode != 0:
        return failed("git failed", where)
    index = where.stdout.strip()
    if not os.path.isabs(index):
        index = os.path.join(repo, index)
    top = git(["rev-parse", "--show-toplevel"]).stdout.strip() or repo
    own = os.path.normcase(os.path.abspath(patch_out)) if patch_out else None
    tmp = tempfile.mkdtemp(prefix="ctdd-index-")
    try:
        copy = os.path.join(tmp, "index")
        if os.path.exists(index):
            shutil.copyfile(index, copy)
        env = {"GIT_INDEX_FILE": copy}
        # The whole repository, whatever directory this runs from, and NUL-
        # separated so a quoted or non-ASCII name arrives as the name it is.
        listed = git(["ls-files", "-z", "--others", "--exclude-standard",
                      "--full-name", ":/"])
        if listed.returncode != 0:
            # Carrying on would print a stat that silently lacks the new files,
            # which is the defect this mode exists to remove.
            return failed("could not list untracked files", listed)
        new, left_out = [], 0
        for name in listed.stdout.split(chr(0)):
            if not name:
                continue
            if own and os.path.normcase(os.path.abspath(os.path.join(top, name))) == own:
                continue
            if is_plan_artifact and is_plan_artifact(name):
                left_out += 1
                continue
            new.append(":(top,literal)" + name)
        for i in range(0, len(new), 100):
            added = git(["add", "-N", "--", *new[i:i + 100]], env)
            if added.returncode != 0:
                return failed("could not mark untracked files in the copy of the "
                              "index", added)
        base = " ".join(base_args)
        note = ""
        if left_out:
            note = (f"; {left_out} untracked file(s) of the plan's own beside it, "
                    f"the plan and its logs, are left out")
        if want_stat:
            stat = git(["diff", "--stat=200,160", "-M", *base_args], env)
            if stat.returncode != 0:
                return failed("git failed", stat)
            print(f"check-spec-surface: diff stat against {base}, untracked files "
                  f"included; the index is untouched{note}")
            print(stat.stdout.rstrip() or " nothing changed")
        if patch_out:
            # Bytes, as git wrote them: a text read drops the carriage returns
            # of a CRLF file and replaces what is not UTF-8.
            full = git(["diff", "-M", *base_args], env, raw=True)
            if full.returncode != 0:
                return failed("git failed", full)
            try:
                with open(patch_out, "wb") as fh:
                    fh.write(full.stdout)
            except OSError as exc:
                print(f"check-spec-surface: cannot write {patch_out}: {exc}")
                return 2
            print(f"check-spec-surface: wrote the full diff against {base} to "
                  f"{patch_out} ({full.stdout.count(bytes([10]))} lines, untracked "
                  f"files included; the index is untouched{note})")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _dirty_at_baseline(path, dirty):
    """True when `path` is one of the baseline's names, or under one of its
    untracked directories (`git status` collapses those to `dir/`)."""
    return any(path == d or (d.endswith("/") and path.startswith(d))
               for d in dirty)


_INTENDED_CHANGE = re.compile(r"^[ \t]*#{1,6}[ \t]*Intended change\b", re.I | re.M)
_ROW_PATH = re.compile(r"[A-Za-z0-9_.\-/]+\.[A-Za-z0-9]{1,6}$")


def intended_change_paths(path):
    """Repository paths named under the plan's `## Intended change`.

    `None` when the plan has no such section, which is the `red pause: skip`
    case and every plan before 7.12 appends one - silence there, because
    reporting the absence needs the `red pause` value, and that field is parsed
    in check-plan.py. A second parse of it here to drive one report line would
    fork a definition; the deficit is filed instead.

    Read from BOTH the first cell of each table row and any backticked token,
    because the sibling above requires backticks and a table that does not use
    them would extract nothing and pass in silence - the fail-silent shape
    `--tests-from` produced three times.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            body = fh.read(200_000)
    except OSError:
        return None
    m = _INTENDED_CHANGE.search(body)
    if not m:
        return None
    # To EOF: 7.12 appends the section last and, under `phased`, its body
    # carries `## Phase N` headings of its own, so stopping at the next heading
    # would read only the first phase's table.
    tail = body[m.end():]
    out = set()
    for line in tail.split("\n"):
        if line.lstrip().startswith("|"):
            cell = line.strip().strip("|").split("|")[0].strip().strip("`").strip()
            if "/" in cell and _ROW_PATH.match(cell):
                out.add(cell)
    for t in re.finditer(r"`([^`\n]{3,160})`", tail):
        tok = t.group(1).strip()
        if "/" in tok and re.search(r"\.[A-Za-z0-9]{1,6}$", tok) and " " not in tok:
            out.add(tok)
    return out


def _plan_artifacts(plan_path):
    """Predicate: is this changed path one of the plan's own artifacts?

    Keyed on the plan's FILENAME STEM, not on its directory, because the caller
    may pass the plan as a repository-relative path or an absolute one while
    diff paths are always repository-relative - so a directory comparison
    silently stops excluding anything the moment an absolute path is used, and
    the report fills with the logs on every run. Every artifact step 7 and 7.12
    write is `<plan stem>.<suffix>` beside the plan - the verify, red-state,
    both pin-state and approval logs, and the pre-implementation diff - so the
    stem identifies all of them under either form.

    A directory comparison stood beside this and was deleted: probing showed no
    case where it was the rule that excluded anything, because every artifact
    is stem-named. An unguarded branch is worse than a missing one.
    """
    norm = plan_path.replace("\\", "/")
    stem = os.path.splitext(os.path.basename(norm))[0]

    def is_artifact(path):
        return bool(stem) and os.path.basename(
            path.replace("\\", "/")).startswith(stem)
    return is_artifact


def _covered(path, rows):
    """A diff path is covered when some row names it.

    Containment in both directions, as the sibling comparison does, plus
    basename equality - a plan that abbreviates a long path to fit the column
    (`Application/.../Commands/Foo.cs`) matches neither direction, and a row
    that is present but unmatched reads here as a row that is missing.
    """
    base = os.path.basename(path)
    return any(r in path or path in r or os.path.basename(r) == base
               for r in rows)


def main():
    args = sys.argv[1:]
    # --plan <path>: compare the inventory against the plan in BOTH
    # directions. Report-only; the verdict is unchanged.
    plan_paths = None
    intended, is_plan_artifact = None, None
    # --baseline "<step-0 Baseline line>": files already dirty before the
    # change began belong to the requester, not to this plan, so they are not
    # reported as missing `## Intended change` rows. That report only: a test
    # edited before the session is still a changed requirement.
    dirty, dirty_capped = [], False
    if "--baseline" in args:
        i = args.index("--baseline")
        if i + 1 >= len(args):
            print("check-spec-surface: --baseline needs the step-0 `Baseline:` line")
            return 2
        dirty, dirty_capped = baseline_dirty(args[i + 1])
        args = args[:i] + args[i + 2:]
    # --stat / --patch <file>: the diff against the base with untracked files
    # included, taken from a copy of the index. Only with --git.
    want_stat = "--stat" in args
    args = [a for a in args if a != "--stat"]
    patch_out = None
    if "--patch" in args:
        i = args.index("--patch")
        if i + 1 >= len(args):
            print("check-spec-surface: --patch needs the file to write the diff to")
            return 2
        patch_out = args[i + 1]
        args = args[:i] + args[i + 2:]
    if (want_stat or patch_out) and not (args and args[0] == "--git"):
        print("check-spec-surface: --stat and --patch read the repository, so they "
              "go with --git <base>.")
        return 2
    gate_dirty = False
    if "--plan" in args:
        i = args.index("--plan")
        if i + 1 < len(args):
            plan_paths = plan_paths_from(args[i + 1])
            intended = intended_change_paths(args[i + 1])
            # What `check-plan.py --gate` found dirty before the plan had any
            # approval: the requester's files, not this change's.
            try:
                with open(os.path.splitext(args[i + 1])[0] + ".gate-dirty.txt",
                          encoding="utf-8", errors="replace") as fh:
                    listed = [l.strip().replace("\\", "/") for l in fh if l.strip()]
                gate_dirty = bool(listed)
                dirty = dirty + listed
            except OSError:
                pass
            # 7.12 puts the red-state log, the pin-state logs, the approval
            # record and the pre-implementation diff *beside the plan*. They
            # are changed files that classify as nothing, so without this they
            # are reported as missing rows on every run - the shape
            # check-adr-drift.py refuses, and what readers learn to ignore.
            is_plan_artifact = _plan_artifacts(args[i + 1])
            args = args[:i] + args[i + 2:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    if settings_stop("check-spec-surface"):
        return 2

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

    base_of = None      # (repository, git-diff arguments), when the base is known
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
        base_of = (repo, git_args)
        if want_stat or patch_out:
            return diff_with_untracked(repo, git_args, want_stat, patch_out, is_plan_artifact)
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
    # `other` stays a count for the line that reports it; `production` keeps the
    # paths, which the `## Intended change` comparison below needs. A file that
    # classifies as no surface at all is what 7.12 calls a production file.
    other, unread, production = 0, [], []

    entries, malformed = parse_name_status(text)
    # A change to the settings file is reported on its own, and when the base
    # is known every path is classified under the settings it had as well. A
    # change that rewrote `testPatterns` and weakened a test in the folder the
    # old value named was reported as touching no surface at all: the file
    # that decides what counts as a test had been edited by the diff being
    # judged. So was a first settings file whose `testPatterns` left out the
    # default folders, since an override replaces the defaults.
    settings = [(s, o, n) for s, o, n in entries if is_settings(o) or is_settings(n)]
    earlier = None
    if settings and base_of is not None:
        was = settings_at_base(*base_of)
        earlier = patterns_under(was) if was is not None else None

    def surface_of(path):
        """(class, only_earlier): the second is True when only the settings
        the diff base had call the path surface."""
        cls = classify(path)
        if cls or earlier is None:
            return cls, False
        cls = _class_under(path, earlier[0], earlier[1], lambda: earlier[2])
        return cls, cls is not None

    for status, old, new in entries:
        if is_settings(old) or is_settings(new):
            continue
        if status[:1] in ("R", "C"):
            verb = "renamed" if status[:1] == "R" else "copied"
            (old_cls, old_only), (new_cls, new_only) = surface_of(old), surface_of(new)
            under = EARLIER_SETTINGS if old_only or new_only else ""
            if old_cls and not new_cls:
                findings[old_cls].append(
                    f"{verb} OUT of {old_cls} surface: {old} -> {new} "
                    f"(treat as a deletion until shown otherwise){under}")
            elif new_cls and not old_cls:
                findings[new_cls].append(
                    f"{verb} INTO {new_cls} surface: {old} -> {new}{under}")
            elif old_cls or new_cls:
                findings[old_cls or new_cls].append(f"{verb}: {old} -> {new}{under}")
            else:
                other += 1
                production.append(new or old)
        else:
            cls, only_earlier = surface_of(old)
            if cls:
                word = STATUS_WORD.get(status[:1], status)
                label = f"{word}: {old}"
                if cls == "contract" and PACT_HINT.search(old):
                    label += "  (consumer contract — blast radius includes another team)"
                if cls == "test" and status[:1] == "D":
                    label += "  (a deleted test is a silently dropped requirement unless justified)"
                if only_earlier:
                    label += EARLIER_SETTINGS
                findings[cls].append(label)
            elif GITLINK_RX.match(old):
                unread.append(old)
            else:
                other += 1
                production.append(old)

    # Unknown content cannot clear the lane. SKILL.md 3.3 opens the trivial lane
    # on this exact verdict string, and a submodule bump can carry any change.
    # A file the plan approved and the diff never touched is not "no surface":
    # the run produced the same verdict a clean tree does, so an approved contract
    # change that was never written read as nothing to see.
    untouched_planned = []
    no_files_section = plan_paths == NO_FILES_SECTION
    no_planned_paths = plan_paths is not None and not no_files_section \
        and not plan_paths
    if no_files_section or no_planned_paths:
        plan_paths = None
    if plan_paths is not None:
        # Compare against every changed path, not only classified surface: a
        # production file the plan named is touched even though it classifies as
        # nothing, and treating it as missing reported a healthy diff as a gap.
        _seen = {q for _s, o, n in entries for q in (o, n) if q}
        untouched_planned = sorted(q for q in plan_paths
                                   if not any(q in s or s in q for s in _seen))
    touched = (any(findings.values()) or bool(unread) or bool(untouched_planned)
               or bool(settings))
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
    if no_files_section:
        print("\nPlanned vs touched: the plan has no `Files likely to change` "
              "section, so nothing was compared in either direction.")
    if no_planned_paths:
        print("\nPlanned vs touched: the plan's `Files likely to change` names no "
              "path this checker can read (a backticked or table-cell path with "
              "a directory and an extension), so nothing was compared.")
    if plan_paths is not None:
        # 8.5 stops only when the inventory EXCEEDS the plan. The deficit is
        # unhandled: a plan naming `openapi.yaml — relax the amount constraint`
        # whose contract file is never edited leaves the inventory a subset, no
        # stop fires, and an approved contract change simply does not ship.
        seen = {f.split(": ", 1)[-1].split("  (")[0].strip()
                for group in findings.values() for f in group}
        seen |= set(unread)
        unplanned = sorted(s for s in seen
                           if not any(q in s or s in q for q in plan_paths))
        # Printed from the same set the verdict reads. The list used to be
        # recomputed against `seen` - classified surface only - so every
        # planned production file was listed as untouched on every run while
        # the verdict above it, comparing against every changed path, did not
        # count it. One real session told the human the checker "only sees
        # committed history"; it had read the diff and printed the wrong set.
        if untouched_planned:
            print("\nPlanned but untouched:")
            for q in untouched_planned:
                print(f"  - {q}")
            print("  An approved change that never reaches its file does not "
                  "ship.")
        if unplanned:
            print("\nUnplanned surface:")
            for s in unplanned:
                print(f"  - {s}")

    # 7.12's table is "one row per production file the change touches, new files
    # included". Observed twice in real use, both times shrinking the output: the
    # phrase was read as "per file each phase actively edits", so files whose only
    # change was step-7 stub plumbing were dropped - eight of seventeen on one
    # change - and the plan's record of what was built had holes a later reader
    # cannot tell from deliberate omission. Driven from the diff, not the table:
    # under `phased` the diff holds only the phases implemented so far, so a file
    # not yet touched cannot be reported missing.
    # `is not None`, never a truth test: an empty set means the section is there
    # and named no file at all, which is the failure rather than the absence of
    # one. A truth test read that as nothing to compare and passed in silence -
    # found by probing this check, and the same fail-silent shape `--tests-from`
    # produced three separate times.
    if intended is not None:
        # A file dirty at the step-0 baseline is the requester's edit; 7.12's
        # rows describe what this change builds. It was reported as a missing
        # row on a real change, and so was `.ctdd.json`, which configures this
        # workflow and is not production. That one no longer reaches this
        # list: the loop above takes a settings change out of the production
        # files and it is reported on its own. Excluded here only, never from
        # the verdict.
        missing, predirty = [], []
        for p in sorted(set(production)):
            if _covered(p, intended) or (is_plan_artifact and is_plan_artifact(p)):
                continue
            if _dirty_at_baseline(p, dirty):
                predirty.append(p)
                continue
            missing.append(p)
        if predirty:
            when = "before the first gate" if gate_dirty else "at the step-0 baseline"
            print(f"\nNot counted for `## Intended change`, dirty {when}: "
                  f"{', '.join(predirty)}")
        if dirty_capped:
            print("  The baseline line names only the first few dirty files of "
                  "a field; any it did not name are still reported below.")
        if missing:
            print(f"\nProduction files with no `## Intended change` row "
                  f"({len(missing)}):")
            for p in missing:
                print(f"  - {p}")
            print("  7.12 wants one row per production file the change touches, "
                  "new files included — a file already carrying step-7 plumbing "
                  "is touched. Without its row a later reader cannot tell a file "
                  "that was considered and deliberately left alone from one that "
                  "was forgotten.")

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

    if settings:
        print(f"\nWorkflow settings ({len(settings)}):")
        for status, old, new in settings:
            if new:
                verb = "renamed" if status[:1] == "R" else "copied"
                print(f"  - {verb}: {old} -> {new}")
            else:
                print(f"  - {STATUS_WORD.get(status[:1], status)}: {old}")
        print(SETTINGS_WHY)
        if earlier is not None:
            print("  Every path is classified under the settings the diff base "
                  "had as well as under these, so no file leaves this inventory "
                  "by being reclassified.")
        elif base_of is None:
            print("  This run was given a list of paths and no base, so they "
                  "are classified under the current settings only. `--git "
                  "<base>` also lists what the earlier settings called surface.")
        else:
            print("  Git could not say which revision this diff starts from, so "
                  "paths are classified under the current settings only.")

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
