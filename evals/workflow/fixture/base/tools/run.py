#!/usr/bin/env python3
"""Recorded-run harness for the Shop fixture.

    python tools/run.py build
    python tools/run.py test [--filter <substring or a|b>]
    python tools/run.py openapi [--check]

It stands in for the real toolchain inside an eval fixture: verdicts are
derived from the files in the tree and from tools/state.json, so a scenario
gets the same output every time and an edit that would break the build or flip
a test does so here too. Every invocation is appended to tools/.runlog, which
is how an eval reads back what was run.
"""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDERS = "src/Shop.Application/Features/Orders/"
COMMAND = ORDERS + "SetOrderStateCommand.cs"
VALIDATOR = ORDERS + "SetOrderStateCommandValidator.cs"
SETTABLE = ORDERS + "SettableOrderState.cs"
PORT = "src/Shop.Application/Abstractions/IOrderRepository.cs"
ENDPOINTS = "src/Shop.Api/Endpoints/OrderEndpoints.cs"
SNAPSHOT = "docs/api/shop-openapi-v1.json"
VALIDATOR_TESTS = "tests/Shop.Application.UnitTests/Orders/SetOrderStateValidatorTests.cs"
TYPE_HOMES = (ORDERS, "src/Shop.Application/Abstractions/", "src/Shop.Domain/Orders/")


def read(rel):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


def walk(top, suffix=".cs"):
    out = []
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, top)):
        for name in sorted(files):
            if name.endswith(suffix):
                out.append(os.path.relpath(os.path.join(dirpath, name), ROOT).replace("\\", "/"))
    return sorted(out)


STATE = json.loads(read("tools/state.json") or "{}")
PHASE = int(STATE.get("phase", 0))


def home_of(type_name):
    for home in TYPE_HOMES:
        if exists(home + type_name + ".cs"):
            return home
    return None


def note_property():
    m = re.search(r"string\?\s+(\w+)\s*[,)]", read(COMMAND))
    return m.group(1) if m else None


def camel(name):
    return name[:1].lower() + name[1:] if name else name


def build_errors():
    errors = []
    if not exists(COMMAND):
        return errors
    change_home = home_of("OrderStateChange")
    change = read((change_home or ORDERS) + "OrderStateChange.cs")
    for rel in walk("src") + walk("tests"):
        body = read(rel)
        if ".Previous" in body and "Previous" not in change:
            errors.append(f"{rel}(31,44): error CS1061: 'OrderStateChange' does not contain "
                          f"a definition for 'Previous'")
            break
    prop = note_property()
    if prop:
        for rel in walk("src") + walk("tests"):
            if rel == COMMAND:
                continue
            # Only uses on the command count: `order.Note` is the stored
            # column and keeps its name whatever the request field is called.
            used = set(re.findall(r"\b(?:request|command|x)\.(\w*Note)\b", read(rel)))
            for name in sorted(used - {prop}):
                errors.append(f"{rel}(12,30): error CS1061: 'SetOrderStateCommand' does not "
                              f"contain a definition for '{name}'")
    return errors


def stub_throws():
    return any("NotImplementedException" in read(rel) for rel in walk("src"))


def route_mapped():
    return "MapPut" in read(ENDPOINTS)


def settable_is_honest():
    members = re.findall(r"^\s*(\w+)\s*=\s*\d+", read(SETTABLE), re.M)
    return sorted(members) == ["Packed", "Shipped"]


def limits():
    v = re.search(r"MaximumLength\((\d+)\)", read(VALIDATOR))
    over = re.search(r"tooLong\s*=\s*new string\('x',\s*(\d+)\)", read(VALIDATOR_TESTS))
    at = re.search(r"atLimit\s*=\s*new string\('x',\s*(\d+)\)", read(VALIDATOR_TESTS))
    return (int(v.group(1)) if v else None, int(over.group(1)) if over else None,
            int(at.group(1)) if at else None)


def differ(expected, actual):
    return f"Assert.Equal() Failure: Values differ\nExpected: {expected}\nActual:   {actual}"


NOT_IMPL = "System.NotImplementedException : The method or operation is not implemented."


def verdict(method):
    """(passed, message) for one test method."""
    if method == "RepositoryAbstractions_Should_Not_Return_Application_Types":
        home = home_of("OrderStateChange")
        if home == ORDERS and "OrderStateChange" in read(PORT):
            return False, ("Repository abstractions may return only Domain types, BCL types, "
                           "or types declared beside them.\nIOrderRepository.SetStateAsync returns "
                           "Shop.Application.Features.Orders.OrderStateChange.")
        return True, ""
    if method == "Set_MovesAPaidOrderToPacked_AndStoresTheNote":
        if PHASE < 1:
            return False, NOT_IMPL if stub_throws() else differ(40, 30)
        return True, ""
    if method == "Set_RefusesShipped_ForAPaidOrder":
        if PHASE < 1:
            return False, NOT_IMPL if stub_throws() else differ("NotAllowed", "Set")
        return True, ""
    if method == "SetOrderStateValidator_RejectsANoteOverTheLimit":
        limit, over, at = limits()
        if PHASE < 2 or limit is None:
            return False, "Assert.False() Failure\nExpected: False\nActual:   True"
        if over is not None and over <= limit:
            return False, "Assert.False() Failure\nExpected: False\nActual:   True"
        if at is not None and at > limit:
            return False, "Assert.True() Failure\nExpected: True\nActual:   False"
        return True, ""
    if method == "Handle_ReturnsConflict_WhenTheMoveIsNotAllowed":
        return (True, "") if PHASE >= 2 else (False, differ("Conflict", "NoContent"))
    if method == "SetOrderState_ForAnAllowedMove_Returns204AndWritesTheState":
        if not route_mapped():
            return False, differ("NoContent", "NotFound")
        return (True, "") if PHASE >= 2 else (False, differ(40, 30))
    if method == "SetOrderState_WithAStateOutsideTheSettableSet_Returns400":
        if not route_mapped():
            return False, differ("BadRequest", "NotFound")
        if not settable_is_honest():
            return False, differ("BadRequest", "NoContent")
        return True, ""
    if method == "OpenApiDocument_PublishesNoEmptySummaryOrDescription":
        return True, ""
    known_existing = {"Get_ReturnsTheOrder_ForAKnownNumber", "GetOrder_ForAnUnknownNumber_Returns404",
                      "Domain_Should_Not_Reference_Application", "Expand_QueuesOneMessagePerRoute",
                      "Deliver_SkipsARouteWithNoClient", "Expand_WritesOneQueueRowPerRoute"}
    if method in known_existing:
        return True, ""
    # A test this harness has no recording for has no implementation behind it.
    return False, "Assert.True() Failure\nExpected: True\nActual:   False"


def tests():
    out = []
    for rel in walk("tests"):
        parts = rel.split("/")
        project, cls = parts[1], os.path.splitext(parts[-1])[0]
        for method in re.findall(r"public\s+(?:async\s+Task|void)\s+(\w+)\s*\(", read(rel)):
            out.append((f"{project}.{cls}.{method}", method, rel))
    return out


def cmd_build():
    errors = build_errors()
    if errors:
        for e in errors:
            print(e)
        print(f"\nBuild FAILED.\n    0 Warning(s)\n    {len(errors)} Error(s)")
        return 1
    print("Build succeeded.\n    0 Warning(s)\n    0 Error(s)")
    return 0


def cmd_test(args):
    flt = None
    if "--filter" in args:
        i = args.index("--filter")
        flt = args[i + 1] if i + 1 < len(args) else ""
    errors = build_errors()
    if errors:
        for e in errors:
            print(e)
        print(f"\nBuild FAILED.\n    {len(errors)} Error(s)")
        return 1
    wanted = [w.strip() for w in flt.split("|")] if flt else None
    passed = failed = 0
    for n, (fqn, method, rel) in enumerate(tests()):
        if wanted is not None and not any(w and w in fqn for w in wanted):
            continue
        ok, message = verdict(method)
        ms = 3 + (n * 7) % 40
        if ok:
            passed += 1
            print(f"  Passed {fqn} [{ms} ms]")
        else:
            failed += 1
            print(f"  Failed {fqn} [{ms} ms]")
            print("  Error Message:")
            for line in message.split("\n"):
                print("   " + line if line.startswith(("Assert", "System", "Repository")) else line)
            print("  Stack Trace:")
            print(f"     at {fqn}() in {rel}:line 27")
    total = passed + failed
    if total == 0:
        print("No test matches the given testcase filter.")
        return 1
    word = "Failed!" if failed else "Passed!"
    print(f"\n{word}  - Failed: {failed:5d}, Passed: {passed:5d}, Skipped:     0, Total: {total:5d}")
    return 1 if failed else 0


def cmd_openapi(args):
    prop = camel(note_property() or "")
    snap = read(SNAPSHOT)
    if "--check" in args:
        problems = []
        if route_mapped() and "/api/v1/orders/{orderNumber}/state" not in snap:
            problems.append("the snapshot has no PUT /api/v1/orders/{orderNumber}/state")
        if prop and "SetOrderStateCommand" in snap and f'"{prop}"' not in snap:
            problems.append(f"SetOrderStateCommand has no property \"{prop}\" in the snapshot")
        if problems:
            print("openapi: the snapshot does not match the routes — " + "; ".join(problems))
            return 1
        print("openapi: the snapshot matches the routes.")
        return 0
    if prop and "SetOrderStateCommand" in snap:
        def fix(match):
            return match.group(1) + f'"{prop}"' + match.group(3)
        snap2 = re.sub(r'("state":\s*\{[^}]*\},\s*)("\w+")(\s*:\s*\{\s*"type":\s*"string")',
                       fix, snap, count=1, flags=re.S)
        with open(os.path.join(ROOT, SNAPSHOT), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(snap2)
        print(f"openapi: wrote {SNAPSHOT}" + ("" if snap2 != snap else " (unchanged)"))
        return 0
    print(f"openapi: wrote {SNAPSHOT} (unchanged)")
    return 0


def main():
    args = sys.argv[1:]
    with open(os.path.join(ROOT, "tools", ".runlog"), "a", encoding="utf-8") as fh:
        fh.write(time.strftime("%H:%M:%S") + " " + " ".join(args) + "\n")
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if args[0] == "build":
        return cmd_build()
    if args[0] == "test":
        return cmd_test(args[1:])
    if args[0] == "openapi":
        return cmd_openapi(args[1:])
    print(f"run.py: unknown command {args[0]!r}")
    return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
