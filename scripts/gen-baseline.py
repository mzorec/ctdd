#!/usr/bin/env python3
"""Emit step 0's Baseline statement, and refuse when the base is not ours to pick.

    python3 gen-baseline.py [--target <branch>] [--repo <path>]

Why this exists: `diff-base` is not a note for the reader. It is the literal
argument four later checks take — `check-spec-surface.py --git <diff-base>` at
3.3 and 8.4, the packet's re-run at 9.3, and `git diff <diff-base> --stat` at
9.4 — so a hand-derived value is a hand-derived input to every mechanical check
the method has. Deriving it here makes those four agree by construction.

The second half is step 0.3. "Stop and ask which base to use when the target
branch is absent, disputed, or has no merge-base" was a condition the agent had
to *notice*; noticing is exactly what degrades. Here it is detected: an absent
or ambiguous target, or a target sharing no history with HEAD, exits 1 and says
what the choice is. Exit 1 is a decision, not a failure — the same reading
`check-spec-surface.py` gives it.

Exit codes:
    0  baseline established; the Baseline line is on stdout
    1  the base is the human's call; nothing is claimed
    2  cannot run — not a git checkout, or git is unavailable

Plain Python 3, stdlib only.
"""

from __future__ import annotations

import subprocess
import sys

FIELD_CAP = 5          # files named per field before the count takes over
SHORT_SHA = 7


def _git(repo, *args):
    """Run a git command. Returns (returncode, stdout) with only the trailing
    newline removed.

    Deliberately not `.strip()`. `git status --porcelain` encodes the index in
    column 1 and the worktree in column 2, so a leading space is data:
    stripping it shifted every column of the first line, and a file that was
    modified-but-unstaged came back as staged under the path `eed.txt`. Call
    sites wanting a single token strip for themselves.
    """
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    except (OSError, ValueError) as exc:            # git missing, bad repo path
        return 127, str(exc)
    return r.returncode, r.stdout.rstrip(chr(10))


def _summarise(names):
    """`none`, or the names, or the first few and a count of the rest.

    An unbounded list is why this is capped: a baseline taken in a tree with
    two hundred untracked files pushed the whole statement off the terminal,
    and the fields after it are the ones later steps read.
    """
    if not names:
        return "none"
    if len(names) <= FIELD_CAP:
        return ", ".join(names)
    return ", ".join(names[:FIELD_CAP]) + f", +{len(names) - FIELD_CAP} more"


def worktree_state(repo):
    """Staged, unstaged and untracked paths, by git's own porcelain classing."""
    code, out = _git(repo, "status", "--porcelain")
    if code != 0:
        return None
    staged, unstaged, untracked = [], [], []
    for line in out.split("\n"):
        if not line.strip():
            continue
        x, y, path = line[0], line[1], line[3:].strip()
        # A rename reads `R  old -> new`; the new path is the one that exists.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if x == "?" and y == "?":
            untracked.append(path)
            continue
        if x not in " ?":
            staged.append(path)
        if y not in " ?":
            unstaged.append(path)
    return staged, unstaged, untracked


def current_branch(repo):
    """The branch name, or None when HEAD is detached."""
    code, out = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    out = out.strip()
    return out if code == 0 and out else None


def _exists(repo, ref):
    return _git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}")[0] == 0


def resolve_target(repo, requested=None):
    """(target, candidates, why) — `why` is set only when the target is unresolved.

    Inference order is deliberate. `origin/HEAD` is what the remote itself calls
    default, so it beats guessing; only when that is absent do local `main` and
    `master` get a say, and *both* existing is the disputed case 0.3 names
    rather than a tie to break silently.
    """
    if requested:
        if not _exists(repo, requested):
            return None, [], f"the requested target `{requested}` does not exist here"
        return requested, [], None

    code, out = _git(repo, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    out = out.strip()
    if code == 0 and out:
        if _exists(repo, out):
            return out, [], None

    local = [b for b in ("main", "master") if _exists(repo, b)]
    if len(local) == 1:
        return local[0], [], None
    if len(local) > 1:
        return None, local, "more than one default-looking branch exists and none is marked"
    return None, [], "no `origin/HEAD`, `main`, or `master` to infer a target from"


def on_target(branch, target):
    """True when the change is being made on the target branch itself.

    `main` and `origin/main` are the same branch to a person and different
    strings to `==`, which is why this is not an equality test: inferring the
    target from `origin/HEAD` is the common case, so a bare comparison never
    fired the report and working directly on the default branch went unsaid.
    Only the remote prefix is stripped — `release/main` is not `main`.
    """
    if branch is None:
        return False
    short = target.split("/", 1)[1] if target.startswith(("origin/", "upstream/")) else target
    return branch in (target, short)


def diff_base(repo, branch, target):
    """(base, why). On the target branch the work is uncommitted, so HEAD is it.

    Off it, the base is where this branch left the target — a merge-base. No
    merge-base means unrelated histories, which is 0.3's third case and not
    something to paper over with HEAD: every later `--git <diff-base>` would
    then read the whole branch as the change.
    """
    if branch is not None and branch == target:
        return "HEAD", None
    code, out = _git(repo, "merge-base", target, "HEAD")
    out = out.strip()
    if code != 0 or not out:
        return None, f"`{target}` and HEAD share no merge-base"
    return out[:SHORT_SHA], None


def build(repo, requested=None):
    """(exit_code, lines). Never raises for an ordinary git condition."""
    if _git(repo, "rev-parse", "--git-dir")[0] != 0:
        return 2, ["gen-baseline: not a git checkout (or git is unavailable); "
                   "step 0 is unestablished, which blocks the workflow rather "
                   "than defaulting a base."]

    state = worktree_state(repo)
    if state is None:
        return 2, ["gen-baseline: `git status` failed; the working tree is unreadable."]
    staged, unstaged, untracked = state

    branch = current_branch(repo)
    target, candidates, why = resolve_target(repo, requested)
    if target is None:
        lines = [f"gen-baseline: the base is yours to choose — {why}."]
        if candidates:
            lines.append("    candidates: " + ", ".join(candidates))
        lines.append("    Re-run with --target <branch>. Nothing is claimed until you do.")
        return 1, lines

    base, why = diff_base(repo, branch, target)
    if base is None:
        return 1, [f"gen-baseline: the base is yours to choose — {why}.",
                   "    Re-run with --target <branch>, or name the commit to diff "
                   "against. Nothing is claimed until you do."]

    lines = []
    if branch is None:
        lines.append("gen-baseline: HEAD is detached; `branch` reads as `(detached)`.")
    elif on_target(branch, target):
        # 0.1's report. Not an error: it is legitimate for uncommitted work, and
        # it is also how a change lands on the default branch without anyone
        # meaning it, so it is said out loud rather than inferred from the line.
        scope = ("only uncommitted work is in scope" if base == "HEAD" else
                 "the base covers every commit this branch has that the target "
                 "does not, so unpushed commits are in scope")
        lines.append(f"gen-baseline: the current branch IS the target (`{target}`) — "
                     f"{scope}.")

    lines.append(
        f"Baseline: branch={branch or '(detached)'}; target={target}; "
        f"diff-base={base}; staged={_summarise(staged)}; "
        f"unstaged={_summarise(unstaged)}; untracked={_summarise(untracked)}.")
    return 0, lines


def main(argv):
    repo, requested, rest = ".", None, list(argv)
    while rest:
        arg = rest.pop(0)
        if arg == "--target" and rest:
            requested = rest.pop(0)
        elif arg == "--repo" and rest:
            repo = rest.pop(0)
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        else:
            print(f"gen-baseline: unknown argument {arg!r}", file=sys.stderr)
            print("usage: gen-baseline.py [--target <branch>] [--repo <path>]",
                  file=sys.stderr)
            return 2
    code, lines = build(repo, requested)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
