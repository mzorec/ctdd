#!/usr/bin/env python3
"""check-redstate.py — verify new tests were *observed failing* before implementation.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" run.log --test Name1 --test Name2
    dotnet test 2>&1 | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" - --test Name1
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-redstate.py" run.log --tests-from docs/plans/<plan>.md

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

# Logs are UTF-8 (jest/vitest/mocha emit ✕, TAP emits ✗) but Windows consoles
# default to cp1252: reading a piped log in the locale encoding turns the
# failure marker into mojibake, so a genuinely failing test reads as "passed
# before implementation" — and printing this module's own docstring crashes.
# Both symptoms, one cause.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def _decode(raw):
    """Decode captured log/plan bytes, tolerating the encodings shells emit.

    PowerShell 5.1 `>` writes UTF-16; a locale console can leave stray cp1252
    bytes in an otherwise-UTF-8 stream. Sniff a BOM, else UTF-8 with
    replacement. The skill mandates capturing the run to a *file*, so this path
    must fail closed with a verdict, never crash on a raw UnicodeDecodeError: a
    mojibake line that reads as "not found" is a verdict; a traceback is not.
    """
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _read_text(src):
    """Read a log or plan file as text, tolerant of shell-produced encodings."""
    with open(src, "rb") as fh:
        return _decode(fh.read())

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


def _match_span(line, name):
    """Return (start, end) where `name` appears as a whole identifier, else None.

    A bare `name in line` let `--test Foo` be satisfied by `FooBar`, certifying a
    test that never ran. Runner output surrounds a test name with `::`, `.`, `(`,
    whitespace and similar, so the boundary is "not a word character and not one
    of the characters a test name may itself contain".
    """
    for m in re.finditer(re.escape(name), line):
        before = line[m.start() - 1] if m.start() else " "
        after = line[m.end()] if m.end() < len(line) else " "
        # A dot BEFORE the name is a namespace separator, not part of the
        # identifier: `dotnet test --logger detailed` prints every test as
        # Namespace.Class.Method, so rejecting a leading dot rejected the most
        # common real-world log format outright. A dot AFTER still rejects,
        # because a match followed by `.` is a prefix of a longer qualified name.
        if not (before.isalnum() or before == "_") and \
           not (after.isalnum() or after in "_."):
            return m.start(), m.end()
    return None


def _verdict_text(line, name):
    """The runner's own text, with the matched test name removed.

    Marker words inside an identifier are not verdicts: `error_handling_is_logged`
    contains "error" and `success_is_logged` contains "success", and scanning the
    whole line let either certify itself with no verdict present anywhere.
    """
    span = _match_span(line, name)
    return line if span is None else line[:span[0]] + " " + line[span[1]:]


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
        if _match_span(line, name) is not None:
            seen = True
            if looks_like_pass(_verdict_text(line, name)):
                return True, True
    return seen, False


def observed_failing(log, name):
    """(seen, failed) — was the test mentioned at all, and on a failing line?"""
    seen = False
    for line in log.splitlines():
        if _match_span(line, name) is not None:
            seen = True
            if looks_like_failure(_verdict_text(line, name)):
                return True, True
    return seen, False


# Headings that introduce tests whose evidence runs the OTHER way: a pin /
# characterization test asserts behavior that already exists, so it must be
# observed *passing*, not failing. Default extraction skips these sections (a
# pin in the red-state set is a false finding); --expect-pass reads only them.
PIN_HEADING_RX = re.compile(
    r"(preservation\s+pins?|pin\s+tests?|characterization\s+tests?"
    r"|must\s+pass\s+before\s+and\s+after)", re.I)
# Headings that return extraction to new-behavior tests. The `proposed…tests`
# arm is deliberately loose so it also matches the plan format's own
# "Proposed new/changed tests" parent heading, not just "Proposed tests".
NEW_HEADING_RX = re.compile(
    r"(new[-\s]behaviou?r\s+tests?|proposed\b[\w/&,\s-]*\btests?"
    r"|must\s+be\s+(observed\s+)?(red|failing))", re.I)
# Strips the markdown that can precede a section label: heading hashes, bullet
# markers, bold, inline code.
LABEL_LEAD_RX = re.compile(r"^\s*(?:#{1,6}\s+|[-*]\s+)?[`*_]*")
# A bullet (candidate test-name line) vs a section label.
BULLET_RX = re.compile(r"^\s*[-*]\s")
# One test name per bullet: a single identifier token, PascalCase or snake_case.
# The old form required an underscore, which silently dropped PascalCase names
# (e.g. dotnet ReportsTotalCount) — extraction then verified a subset while the
# verdict still read as a whole-plan pass. Scoping to the test section (below)
# is what makes the looser token safe.
NAME_RX = re.compile(r"\s*[-*]\s+[`*_]{0,3}([A-Za-z](?:[\w.]*[A-Za-z0-9])?)[`*_]{0,3}\s*(?:—|–|-|:|\(|$)")
# Emphasis and separators are not optional in real plans: `- **Name** — why`,
# `- _Name_ — why` and `- Name: why` were each dropped silently, taking four of
# five names in one measured example.


def _section_label(line):
    """The line's content with leading markdown stripped, or None if it is prose.

    A label is what the line *starts with*, never merely what it contains.
    Scanning for the phrase anywhere was a fail-silent defect: a prose line
    mentioning characterization tests flipped the parser into skip mode and
    every following bullet was dropped from the extraction, while the verdict
    still reported success for the smaller set it had managed to read.
    """
    stripped = LABEL_LEAD_RX.sub("", line).strip()
    return stripped or None


def _is_heading(line, label):
    r"""True if the line introduces a section, not a test name.

    A section header is a known new/pin heading (which may be written as a
    bullet, e.g. `- \`New-behavior tests …\``), a markdown `#` heading, or any
    non-bullet, non-blank line (the plan's plain labels: "Existing behavior:",
    "Contract changes:"). Everything else is a candidate name bullet.
    """
    if PIN_HEADING_RX.match(label) or NEW_HEADING_RX.match(label):
        return True
    if line.lstrip().startswith("#"):
        return True
    if BULLET_RX.match(line):
        return False
    # A non-bullet line ends the section only if it is *label-shaped*: short, no
    # sentence punctuation, typically ending in a colon. Treating every prose
    # line as a boundary meant one explanatory sentence inside a test list
    # silently truncated it, and the checker then verified the shorter list and
    # reported success.
    text = (label or "").strip()
    if not text:
        return False
    return len(text) <= 72 and not text.rstrip().endswith((".", "!", "?"))


def names_from_plan(path, want_pins=False):
    """Pull test names out of *only* the relevant test section of a plan.

    Names are collected only while inside the wanted section — the new-behavior
    test section by default, the preservation-pin section under --expect-pass.
    Bullets in any other section (notably the "Existing behavior" citations the
    plan format mandates) are ignored: extracting those produced false "passed
    before implementation" / "not found" verdicts on fully compliant plans.

    Pin/characterization tests are kept out of the default (red-state) set two
    ways, because their evidence is green-then-still-green: bullets under a
    preservation-pin heading, and any `currently_`-prefixed name. Under
    --expect-pass those same `currently_` names are exactly what we want, so the
    prefix filter applies only outside pin mode.
    """
    text = _read_text(path)
    want = "pin" if want_pins else "new"
    found, section = [], "other"
    for line in text.splitlines():
        label = _section_label(line)
        if label is not None and _is_heading(line, label):
            if PIN_HEADING_RX.match(label):
                section = "pin"
            elif NEW_HEADING_RX.match(label):
                section = "new"
            else:
                section = "other"
            continue
        if section != want:
            continue
        m = NAME_RX.match(line)
        # The marker is recognised in every rendering an author writes:
        # `currently_x`, `Currently_X` and `CurrentlyReturnsX`. Extraction learned
        # PascalCase at finding #29 and this *classification* filter did not, so a
        # PascalCase observation read as a new-behaviour test — the same
        # fix-one-call-site shape as finding #36.
        if m and (want_pins or not re.match(r"currently", m.group(1), re.I)):
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
                _plan = rest.pop(0)
                _found = names_from_plan(_plan, want_pins=expect_pass)
                if expect_pass and not _found:
                    print(f"check-redstate: no preservation-pin section found in "
                          f"{_plan}. A behavior-preserving change still needs one: "
                          f"write `Preservation pins — must pass before and after` "
                          f"(or `Preservation pins: none` when there genuinely are "
                          f"none). Refusing to verify a pin lane that has no pins.")
                    return 2
                if not expect_pass and not _found:
                    print(f"check-redstate: {_plan} contributed no test names — "
                          f"the plan cross-check is not operating, so a test swapped "
                          f"between plan and implementation would pass unnoticed. "
                          f"Check the new-behavior heading and that names are bullets.")
                    return 2
                names.extend(_found)
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
        log = sys.stdin.read() if log_src == "-" else _read_text(log_src)
    except OSError as exc:
        print(f"check-redstate: cannot read {log_src}: {exc}")
        return 2

    if expect_pass:
        # Pin / characterization evidence: the named tests assert behavior that
        # ALREADY exists, so the proof is green-against-the-old-implementation.
        ok, red, unclear, missing = [], [], [], []
        for name in names:
            seen, passed = observed_passing(log, name)
            if passed:
                ok.append(name)
            elif not seen:
                missing.append(name)
            elif observed_failing(log, name)[1]:
                red.append(name)
            else:
                unclear.append(name)
        if not red and not missing and not unclear:
            print(f"check-redstate: {', '.join(ok)}")
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
        if unclear:
            print(f"  mentioned without a pass/fail marker ({len(unclear)}): {', '.join(unclear)}")
            print("    The name appears in the log but no line reports a verdict for it — "
                  "this is an unreadable run, not a failing pin. Check the runner's output "
                  "format rather than the test.")
        if missing:
            print(f"  not found in the log ({len(missing)}): {', '.join(missing)}")
            print("    An unrun pin proves nothing about preservation.")
            if not any(re.search(r"(?i)\b(pass|ok|✓)", l) for l in log.splitlines()
                       if not SUMMARY_RX.search(l.lower())):
                print("    The log has no per-test result lines at all, only a summary. "
                      "Re-run with per-test output (dotnet: --logger "
                      "\"console;verbosity=detailed\"; pytest: -v; go: -v) — a summary "
                      "names no test, so nothing can be verified from it.")
        return 1

    failing, passing, absent = [], [], []
    for name in names:
        seen, failed = observed_failing(log, name)
        (failing if failed else (passing if seen else absent)).append(name)

    if not passing and not absent:
        print(f"check-redstate: {', '.join(failing)}")
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
