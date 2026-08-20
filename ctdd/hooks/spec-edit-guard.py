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
    # Approval / snapshot baselines. Re-recording one (`verify --accept`,
    # `jest -u`, `--snapshot-update`) makes an implementation pass without
    # editing any test file, so it evaded the guardrail's verb list — edit,
    # delete, skip, loosen, replace, reclassify — and landed as `other` in every
    # deterministic consumer. A spec amendment with no artifact anywhere.
    r"\.(verified|approved|received)\.[^/]+$",
    r"(^|/)__snapshots__/",
    r"\.snap$",
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
# A `.verified.json` or `.approved.json` is an approval baseline, never an
# ambiguous config: re-recording one makes an implementation pass with no test
# file edited. They were suppressed by AMBIGUOUS_EXT outside a literal `tests/`
# directory — and `src/Payments.Tests/` is not one, which is the dominant .NET
# Verify layout, so the hook stayed silent on the exact edit it exists to catch.
BASELINE_RX = re.compile(r"\.(verified|approved|received)\.[^/]+$", re.IGNORECASE)
# Assertion-shaped calls across the ecosystems this plugin targets. Counting is
# advisory: it distinguishes "this rewrite drops assertions" from "this
# rewrite adds a case", which the byte-identical message could not.
ASSERT_RX = re.compile(
    r"\b(assert\w*|should\w*|expect|verify|Assert\.\w+|Should\(\))\s*[\(.]",
    re.IGNORECASE)

TESTS_DIR_RX = re.compile(r"(^|/)[^/]*\.?(tests?|__tests__)(/|$)", re.IGNORECASE)

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


CONFIG_NAME = ".ctdd.json"


def repo_config(root=None):
    """The repository's own CTDD settings, from `.ctdd.json` at its root.

    An environment variable is not storage. It lives in one shell, is absent on a
    fresh clone, on a teammate's machine and in CI, and nothing in the repository
    records the decision — so a choice made once has to be remade every session,
    and the plugin silently falls back in between. These settings describe the
    repository, so they belong in it.

    Malformed or unreadable config is ignored rather than fatal: this file is
    read on every hook invocation, and a typo in it must not break editing.
    """
    # Not cached. The file is a few bytes, each process reads it at most a
    # handful of times, and a cache keyed on the path alone remembers an empty
    # read from before the file existed — which is a stale-config bug in
    # exchange for nothing.
    root = root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    data = {}
    try:
        with open(os.path.join(root, CONFIG_NAME), "rb") as fh:
            raw = fh.read()
        # PowerShell's `>` writes UTF-16LE and `Set-Content -Encoding UTF8`
        # writes UTF-8+BOM. Both raised ValueError here and were swallowed, so
        # every setting silently reverted to defaults on the platform this repo
        # documents interpreter fallbacks for.
        for enc in ("utf-8-sig", "utf-16", "utf-8"):
            try:
                loaded = json.loads(raw.decode(enc))
                break
            except (UnicodeDecodeError, ValueError):
                continue
        else:
            return {}
        if isinstance(loaded, dict):
            data = loaded
    except (OSError, ValueError):
        data = {}
    return data


def setting(env_var, config_key, root=None):
    """Environment first (a deliberate act for one run), then the repository
    file (the durable decision), then nothing."""
    raw = os.environ.get(env_var, "").strip()
    if raw:
        return raw
    value = repo_config(root).get(config_key)
    return value.strip() if isinstance(value, str) and value.strip() else ""


def patterns(env_var, default):
    raw = setting(env_var, {"CTDD_TEST_PATTERNS": "testPatterns",
                            "CTDD_CONTRACT_PATTERNS": "contractPatterns"}.get(env_var, ""))
    values = default if not raw else [p.strip() for p in raw.split(";") if p.strip()]
    if raw and not values:
        # ";" is truthy, discards the default, and splits to zero segments — no
        # re.error, so every fail-closed path was bypassed and the trivial lane,
        # the CI cross-check and this hook all went silent at once while the
        # report still said "env overrides honored".
        raise ValueError(
            f"{env_var} is set but contains no usable pattern ({raw!r}); an "
            f"override that matches nothing would silently empty the spec surface")
    compiled = []
    for value in values:
        try:
            compiled.append(re.compile(value, re.IGNORECASE))
        except re.error as exc:
            raise ValueError(
                f"{env_var} contains invalid regex {value!r}: {exc}"
            ) from exc
    return compiled


def matches(path, pats):
    return any(pattern.search(path) for pattern in pats)


# An ADR marker names a decision that governs this file. This hook is the only
# component that fires when no skill triggered, so it is the only place the
# reminder reaches an edit made outside the change workflow.
# Four digits is adr-tools' and MADR's convention, not a rule: teams number
# ADR-001 and ADR-12 too. A width-locked pattern did not merely fail on those
# — it saw nothing, so the report said nothing, and silence reads as "no
# decision applies". Match any width and compare by value.
ADR_MARKER = re.compile(r"\bADR-(\d{1,4})\b")
ADR_MSG = ("A recorded decision governs {p}: {ids}. Read it before changing "
           "behavior here. If this change contradicts it, amend or supersede "
           "the ADR — a decision record that no longer matches the code is "
           "worse than none, because the next reader trusts it.")


def adr_markers(raw_path):
    """ADR ids named inside the edited file. Silent on any read failure: this
    hook must never break a session over a file it could not open."""
    try:
        with open(raw_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(200000)
    except (OSError, ValueError):
        return []
    seen, out = set(), []
    for m in ADR_MARKER.finditer(text):
        if m.group(1) not in seen:
            seen.add(m.group(1)); out.append(m.group(1))
    return out


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

    try:
        test_rx = patterns("CTDD_TEST_PATTERNS", TEST_DEFAULT)
        contract_rx = patterns("CTDD_CONTRACT_PATTERNS", CONTRACT_DEFAULT)
    except ValueError as exc:
        # Exit 2 from a PreToolUse hook is the *block* signal, so one typo in a
        # regex blocked every Write in the session — from a hook whose own
        # docstring says reminders are advisory, not blocking. Report loudly and
        # let the tool call through: a misconfigured reminder must not become a
        # gate. The source is named because the value may come from .ctdd.json
        # rather than the environment variable the message used to blame.
        print(f"spec-edit-guard: invalid pattern configuration: {exc} "
              f"(check the environment and {CONFIG_NAME}). Detection is running "
              f"on defaults until this is fixed.", file=sys.stderr)
        # Exit 2 from PreToolUse is the *block* signal, so one typo in a regex
        # blocked every Write in the session — from a hook whose docstring says
        # reminders are advisory. After the fact there is nothing to block, so
        # PostToolUse keeps 2 and surfaces the error to the model.
        return 0 if event == "PreToolUse" else 2

    if event == "PreToolUse":
        # Only job here: catch Write overwriting an EXISTING test file.
        if tool == "Write" and os.path.exists(raw_path) \
                and matches(path, test_rx) \
                and not matches(path, contract_rx) \
                and (TESTS_DIR_RX.search(path) or BASELINE_RX.search(path)
                 or not AMBIGUOUS_EXT.search(path)):
            msg = TEST_OVERWRITE_MSG.format(p=path)
            # `tool_input` carries the replacement text, and it was discarded — so
            # a Write replacing a 400-line suite with an assertion-free stub got
            # byte-identical advice to one that adds a case. Compare what is
            # there with what is coming; say so when assertions are disappearing.
            new_text = (data.get("tool_input") or {}).get("content")
            if isinstance(new_text, str):
                try:
                    with open(raw_path, encoding="utf-8", errors="replace") as fh:
                        old_text = fh.read(200_000)
                except OSError:
                    old_text = ""
                before = len(ASSERT_RX.findall(old_text))
                after = len(ASSERT_RX.findall(new_text))
                if before and after < before:
                    msg += (f" This Write drops {before - after} of {before} "
                            f"assertion(s) ({before} -> {after}). Removing an "
                            f"assertion is a spec amendment, not a rewrite.")
            emit("PreToolUse", msg)
        return

    if event != "PostToolUse" or tool not in ("Edit", "MultiEdit", "Write"):
        return

    # One emit per event: two JSON objects on stdout is malformed output and the
    # harness reads only the first, so a second message would silently discard
    # whichever came second.
    notes = []
    ids = adr_markers(raw_path)
    if ids:
        notes.append(ADR_MSG.format(p=path, ids=", ".join("ADR-" + i for i in ids)))

    if matches(path, contract_rx):
        notes.append(CONTRACT_MSG.format(p=path))
    elif tool in ("Edit", "MultiEdit") and matches(path, test_rx) \
            and (TESTS_DIR_RX.search(path) or BASELINE_RX.search(path)
                 or not AMBIGUOUS_EXT.search(path)):
        notes.append(TEST_EDIT_MSG.format(p=path))

    if notes:
        emit("PostToolUse", "\n\n".join(notes))


if __name__ == "__main__":
    sys.exit(main())
