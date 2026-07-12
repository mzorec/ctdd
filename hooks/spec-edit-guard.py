#!/usr/bin/env python3
"""CTDD spec-edit guard (PostToolUse + PreToolUse hook).

What it covers, stated honestly:
- Edit/MultiEdit of a file matching test patterns  -> reminder (PostToolUse).
- Write that would OVERWRITE an existing test file -> reminder (PreToolUse,
  existence-checked before the write happens; PostToolUse cannot distinguish
  create from overwrite because the file exists by the time it runs).
- Any Edit/MultiEdit/Write touching a contract file -> boundary reminder
  (PostToolUse).
- Write creating a brand-NEW test file -> silent by design: writing tests
  during a feature is the expected path, and a reminder on every new file
  would be noise. The ctdd-tests skill owns naming discipline for new tests.
- Edits made through Bash (sed -i, heredocs, patch, git apply, rm, mv) never
  reach tool-matched hooks. That lane is uncovered — this hook prices the
  Edit/Write lane only. Say so; don't pretend otherwise.

Reminders are advisory (additionalContext), not blocking: the hook persuades
at the exact moment a spec artifact changes; it does not prevent.

Tuning: override detection with environment variables holding
semicolon-separated regexes, matched case-insensitively against the full
forward-slash path (an override REPLACES the defaults — re-include them if
you want both):
    CTDD_TEST_PATTERNS
    CTDD_CONTRACT_PATTERNS
Example for SOAP shops:  CTDD_CONTRACT_PATTERNS="\\.wsdl$;\\.xsd$"
"""

import json
import os
import re
import sys

TEST_DEFAULT = [
    r"(^|/)(tests?|__tests__|specs?)(/|$)",   # test directories
    # PascalCase test-class files, case-sensitive so 'latest.md' can't match,
    # and extension-limited so 'LoadTest.md' (a doc) can't either:
    r"(?-i:[^/]*Tests?\.(cs|fs|vb|py|ts|tsx|js|jsx|mjs|go|rb|java|kt|kts|scala|php|rs|swift|ex|exs|groovy|clj|cc|cpp)$)",
    r"(^|/)test_[^/]*\.py$",                  # test_capture.py
    r"\.(test|spec)\.\w+$",                   # foo.test.ts, foo.spec.js
    r"_(test|spec)\.\w+$",                    # foo_test.go, foo_spec.rb
]

CONTRACT_DEFAULT = [
    r"(^|/)(contracts?|pacts?)(/|$)",                        # contract directories
    r"(^|/)(openapi|swagger|asyncapi)[^/]*\.(ya?ml|json)$",  # openapi.yaml, swagger.json
    r"\.(openapi|asyncapi)\.(ya?ml|json)$",                  # payments.openapi.yaml
    r"\.proto$",                                             # gRPC / protobuf IDL
    r"\.pact\.json$",                                        # Pact consumer contracts
]

# Files with these extensions are data/contract-shaped. Under a specs?/
# directory (or a *.spec.yaml-style filename) a non-contract match is most
# likely an API spec, so stay silent rather than mislabel it as a test edit
# (mislabel is worse than silence). Under tests?/__tests__ the opposite holds:
# a yaml/json file there is fixture/golden data — exactly the "fixture setup"
# surface where weakness #3's wrong encoding hides — so the test-edit
# reminder is substantively correct and MUST fire.
AMBIGUOUS_EXT = re.compile(r"\.(ya?ml|json|xsd|wsdl|proto)$", re.IGNORECASE)
TESTS_DIR_RX = re.compile(r"(^|/)(tests?|__tests__)(/|$)", re.IGNORECASE)

TEST_EDIT_MSG = (
    "CTDD note: {p} matches this repository's test file patterns, and an existing "
    "test was just modified. Under CTDD a changed test is a changed spec: the "
    "change summary needs to say which requirement changed and why (for a changed "
    "assertion, show old vs. new), and the change is reviewed as a requirements "
    "change. A test weakened so that failing code passes is a spec regression, "
    "not a fix. If the file contains characterization tests (currently_* names), "
    "whether the old pinned behavior was intent or accident is a human decision."
)

TEST_OVERWRITE_MSG = (
    "CTDD note: {p} matches this repository's test file patterns and an existing "
    "test file is about to be overwritten wholesale via Write. Under CTDD a "
    "changed test is a changed spec: the change summary needs to say which "
    "requirements changed and why. A rewrite that quietly drops or weakens "
    "assertions is a silent spec change."
)

CONTRACT_MSG = (
    "CTDD note: {p} matches this repository's API/consumer contract patterns, "
    "so this edit is a boundary change. The summary of this change needs to state "
    "whether it is backward-compatible; a breaking change also requires the "
    "consumer-driven contract (e.g. Pact) to be updated so it fails in CI, not in "
    "production."
)


def patterns(env_var, default):
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return default
    return [p.strip() for p in raw.split(";") if p.strip()]


def matches(path, pats):
    return any(re.search(p, path, re.IGNORECASE) for p in pats)


def emit(event, message):
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": message}
    }))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input: stay silent, never break the session

    event = data.get("hook_event_name") or "PostToolUse"
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input") or {}
    raw_path = tool_input.get("file_path") or ""
    if not isinstance(raw_path, str) or not raw_path:
        return
    path = raw_path.replace("\\", "/")

    test_rx = patterns("CTDD_TEST_PATTERNS", TEST_DEFAULT)
    contract_rx = patterns("CTDD_CONTRACT_PATTERNS", CONTRACT_DEFAULT)

    if event == "PreToolUse":
        # Only job here: catch Write overwriting an EXISTING test file.
        if tool == "Write" and os.path.exists(raw_path) \
                and matches(path, test_rx) \
                and not matches(path, contract_rx) \
                and (TESTS_DIR_RX.search(path) or not AMBIGUOUS_EXT.search(path)):
            emit("PreToolUse", TEST_OVERWRITE_MSG.format(p=path))
        return

    if event != "PostToolUse" or tool not in ("Edit", "MultiEdit", "Write"):
        return

    if matches(path, contract_rx):
        emit("PostToolUse", CONTRACT_MSG.format(p=path))
    elif tool in ("Edit", "MultiEdit") and matches(path, test_rx) \
            and (TESTS_DIR_RX.search(path) or not AMBIGUOUS_EXT.search(path)):
        emit("PostToolUse", TEST_EDIT_MSG.format(p=path))


if __name__ == "__main__":
    main()
