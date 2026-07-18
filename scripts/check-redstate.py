#!/usr/bin/env python3
"""check-redstate.py — verify new tests were *observed failing* before implementation.

Usage:
    python3 scripts/check-redstate.py run.log --test Name1 --test Name2
    dotnet test 2>&1 | python3 scripts/check-redstate.py - --test Name1
    python3 scripts/check-redstate.py run.log --tests-from docs/plans/<plan>.md

Why this exists: "run the new tests and watch them fail first" is the cheapest
guard against a vacuously-passing test — a test that has never failed is
unvalidated as a detector. In practice that instruction is *prompted*, and
prompted discipline drifts: an agent under time pressure writes the
implementation first and the check silently doesn't happen. This converts the
promise into an artifact — a captured run in which the named tests are
demonstrably red — that a reviewer (or CI) can verify without trusting anyone's
recollection.

What it does: for each named test, scan the log for a line mentioning that name
and decide whether that line reports a failure. A name that appears only on a
passing line, or does not appear at all, fails the check.

Honest ceiling: this is a text scan over a runner's output, not an
understanding of the runner. It recognises the common markers of the major
runners (dotnet/xunit `Failed X`, pytest `FAILED …::X`, jest `✕ X`, generic
`FAIL`/`ERROR`), and it can be fooled by a log that prints a test name inside
unrelated failing output. It proves *a* failing run mentioning the test, not
that the failure was for the right reason — reading the assertion message is
still the reviewer's job. It is a floor, not a substitute for judgement.

Runner coverage: it is not tied to one framework — it recognises `Failed`/
`FAILURE` (dotnet, xunit, MSTest, NUnit, JUnit/Surefire), `FAILED` (pytest),
`--- FAIL:` (Go), `✕`/`✗` (jest, vitest, mocha) and `not ok` (TAP). The real
limit is structural rather than per-framework: the test name and the failure
marker must appear on the **same line**. Runners that print the name on one
line and the failure on the next (RSpec's `1) description` / `Failure/Error:`)
will read as not-found — in that case pass the evidence explicitly or say at
review that capture wasn't possible, rather than letting a silent miss look
like a pass.

--expect-pass inverts the check for **pin / characterization** tests, whose
evidence runs the other way: they assert behavior that already exists, so the
proof is a captured run in which they are GREEN against the old implementation
(then still green after the change). Capture that to
docs/plans/<name>.pinstate.log, the counterpart of the .redstate.log.

Exit 0 = every named test was observed failing (or, with --expect-pass, passing).
Exit 1 = at least one named test was not observed failing (passing, or absent).
Exit 2 = usage or input error.
"""

import re
import sys

# Markers that indicate the line reports a failure, not a pass.
FAIL_MARKERS = (
    "failed", "failure", "fail:", "[fail]", "fail ", "✕", "✗", "×",
    "error", "assert", "expected:", "did not", "not ok",
)

# Markers that positively indicate a *pass*, checked first so that a summary
# line like "Failed: 0, Passed: 12" does not count as evidence of failure.
PASS_MARKERS = ("passed", "✓", "√", "ok ", "success")

# Summary/aggregate lines: never evidence about an individual test.
SUMMARY_RX = re.compile(
    r"(failed:\s*\d|passed:\s*\d|total tests|test run|\d+\s+passed|\d+\s+failed)",
    re.I,
)


def looks_like_failure(line):
    """True if this line reports the named test failing."""
    low = line.lower()
    if SUMMARY_RX.search(low):
        return False
    has_fail = any(m in low for m in FAIL_MARKERS)
    if not has_fail:
        return False
    # A line carrying both markers is ambiguous; prefer the pass reading unless
    # the failure marker leads (e.g. "Failed X" vs "X ... passed").
    has_pass = any(m in low for m in PASS_MARKERS)
    if has_pass:
        first_fail = min((low.find(m) for m in FAIL_MARKERS if m in low), default=len(low))
        first_pass = min((low.find(m) for m in PASS_MARKERS if m in low), default=len(low))
        return first_fail < first_pass
    return True


def looks_like_pass(line):
    """True if this line reports the named test passing."""
    low = line.lower()
    if SUMMARY_RX.search(low):
        return False
    has_pass = any(m in low for m in PASS_MARKERS)
    if not has_pass:
        return False
    has_fail = any(m in low for m in FAIL_MARKERS)
    if has_fail:
        first_fail = min((low.find(m) for m in FAIL_MARKERS if m in low), default=len(low))
        first_pass = min((low.find(m) for m in PASS_MARKERS if m in low), default=len(low))
        return first_pass < first_fail
    return True


def observed_passing(log, name):
    """(seen, passed) — the mirror of observed_failing, for pin evidence."""
    seen = False
    for line in log.splitlines():
        if name in line:
            seen = True
            if looks_like_pass(line):
                return True, True
    return seen, False


def observed_failing(log, name):
    """(seen, failed) — was the test mentioned at all, and on a failing line?"""
    seen = False
    for line in log.splitlines():
        if name in line:
            seen = True
            if looks_like_failure(line):
                return True, True
    return seen, False


# Headings that introduce tests whose evidence runs the OTHER way: a pin /
# characterization test asserts behavior that already exists, so it must be
# observed *passing*, not failing. Feeding one to this checker reports a false
# finding — so extraction skips these sections entirely.
PIN_HEADING_RX = re.compile(
    r"(preservation\s+pins?|pin\s+tests?|characterization\s+tests?"
    r"|must\s+pass\s+before\s+and\s+after)", re.I)
# Headings that return extraction to new-behavior tests.
NEW_HEADING_RX = re.compile(
    r"(new[-\s]behaviou?r\s+tests?|proposed\s+(new\s+)?tests?"
    r"|must\s+be\s+(observed\s+)?(red|failing))", re.I)
HEADING_RX = re.compile(r"^\s*(#{1,6}\s|\*\*|[A-Z][^\n]{0,60}:\s*$)")


def names_from_plan(path):
    """Pull *new-behavior* test names out of a plan's bullet lists.

    Heuristic: bullet lines whose content is a single identifier-ish token
    containing an underscore — the naming convention this method asks for
    (`capture_fails_when_amount_exceeds_authorized`). Names with other shapes
    must be passed explicitly with --test.

    Two exclusions keep pin/characterization tests out, because their evidence
    is green-then-still-green and red-state does not apply to them:
      1. bullets under a preservation-pin heading are skipped wholesale;
      2. any name prefixed `currently_` is skipped wherever it appears — that
         is the marker the method mandates for pinned observations.
    """
    text = open(path, encoding="utf-8").read()
    found, in_pin = [], False
    for line in text.splitlines():
        if HEADING_RX.match(line) or PIN_HEADING_RX.search(line):
            if PIN_HEADING_RX.search(line):
                in_pin = True
            elif NEW_HEADING_RX.search(line) or HEADING_RX.match(line):
                in_pin = False
        if in_pin:
            continue
        m = re.match(r"\s*[-*]\s+`?([A-Za-z][\w.]*_[\w.]*)`?\s*(?:—|-|\(|$)", line)
        if m and not m.group(1).lower().startswith("currently_"):
            found.append(m.group(1))
    return list(dict.fromkeys(found))


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    expect_pass = "--expect-pass" in args
    args = [a for a in args if a != "--expect-pass"]

    log_src = args[0]
    names, rest = [], args[1:]
    while rest:
        flag = rest.pop(0)
        if flag == "--test" and rest:
            names.append(rest.pop(0))
        elif flag == "--tests-from" and rest:
            try:
                names.extend(names_from_plan(rest.pop(0)))
            except OSError as exc:
                print(f"check-redstate: cannot read plan: {exc}")
                return 2
        else:
            print(f"check-redstate: unknown or incomplete argument: {flag}")
            return 2

    if not names:
        print("check-redstate: no test names given (--test NAME or --tests-from PLAN). "
              "Nothing to verify — this is a usage error, not a pass.")
        return 2

    try:
        log = sys.stdin.read() if log_src == "-" else open(log_src, encoding="utf-8").read()
    except OSError as exc:
        print(f"check-redstate: cannot read {log_src}: {exc}")
        return 2

    if expect_pass:
        # Pin / characterization evidence: the named tests assert behavior that
        # ALREADY exists, so the proof is green-against-the-old-implementation.
        ok, red, missing = [], [], []
        for name in names:
            seen, passed = observed_passing(log, name)
            (ok if passed else (red if seen else missing)).append(name)
        if not red and not missing:
            print(f"check-redstate: all {len(ok)} pin test(s) observed PASSING against the "
                  f"current implementation — preservation baseline captured. Re-run the same "
                  f"tests after the change; they must still pass.")
            return 0
        print("check-redstate: PIN BASELINE NOT VERIFIED.")
        if red:
            print(f"  failed against the current implementation ({len(red)}): {', '.join(red)}")
            print("    A pin that fails before the change does not describe what the code "
                  "actually does — the pin is wrong, not the code. Fix the pin first, or you "
                  "will 'preserve' behavior that was never there.")
        if missing:
            print(f"  not found in the log ({len(missing)}): {', '.join(missing)}")
            print("    An unrun pin proves nothing about preservation.")
        return 1

    failing, passing, absent = [], [], []
    for name in names:
        seen, failed = observed_failing(log, name)
        (failing if failed else (passing if seen else absent)).append(name)

    if not passing and not absent:
        print(f"check-redstate: all {len(failing)} new test(s) observed failing — "
              f"red state verified. (That they failed for the *right* reason is "
              f"still the reviewer's read.)")
        return 0

    print("check-redstate: RED STATE NOT VERIFIED.")
    if passing:
        print(f"  passed before implementation ({len(passing)}): {', '.join(passing)}")
        print("    A new test that passes before the implementation exists is a finding: "
              "either the behavior already existed and the plan missed it, or the test "
              "asserts nothing.")
    if absent:
        print(f"  not found in the log ({len(absent)}): {', '.join(absent)}")
        print("    Either the test was never run, or the name differs from the plan. "
              "An unrun test is not a detector.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
