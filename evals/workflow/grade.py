#!/usr/bin/env python3
"""Read back what one scenario run did, as facts a grader can check.

    python grade.py <run-dir> --plugin <plugin-root>

It rebuilds the scenario's starting fixture beside the run and reports what
differs: which files changed, what the plan and the approval log now say,
what the reply contains, and which commands the stand-in ran. It prints facts
and decides nothing; the assertions in scenarios.json are judged against
them, and those that need a reader are judged by reading the reply.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("build_fixture", os.path.join(HERE, "build_fixture.py"))
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)

HANDCHECK = ("the order stays at 50", "replaced by the one sent", "the order stays at 30")
TYPES = ("OrderStateOutcome", "OrderStateChange", "SettableOrderState", "SetOrderStateCommand")
PROJECTS = ("Shop.Persistence.IntegrationTests", "Shop.Application.UnitTests", "Shop.Api.IntegrationTests",
            "Shop.Application.IntegrationTests")


def slurp(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def tree(repo):
    out = {}
    for top in ("src", "tests", "docs/api"):
        for dirpath, _dirs, files in os.walk(os.path.join(repo, top)):
            for fn in files:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, repo).replace(os.sep, "/")
                with open(full, "rb") as fh:
                    out[rel] = hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()
    return out


def methods(repo):
    names = []
    for dirpath, _dirs, files in os.walk(os.path.join(repo, "tests")):
        for fn in sorted(files):
            names += re.findall(r"public\s+(?:async\s+Task|void)\s+(\w+)\s*\(", slurp(os.path.join(dirpath, fn)))
    return sorted(names)


def check(plugin, repo, *args):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=repo, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(plugin, "scripts", "check-plan.py"), *args],
                       cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def placement(plan):
    """Where the plan puts each new-behavior test, and the reason it gives
    for a heavier project when it gives one."""
    out, cur = {}, None
    block = plan.split(bf.NL + "New-behavior tests", 1)[-1].split(bf.NL + "Case coverage not reached", 1)[0]
    for line in block.split(bf.NL):
        m = re.match(r"[-*] `?([A-Za-z_]\w*)`?", line)
        if m:
            cur = out.setdefault(m.group(1), {})
            continue
        m = re.match(r"\s+[-*] (path|needs)\s*:\s*(.+)$", line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2).strip().strip("`.").strip("`")[:200]
    return out


def reply_facts(text):
    return {
        "harness_shown": sorted(set(re.findall(r"· ?(UnitTests|IntegrationTests)", text))),
        "needs_lines_shown": len(re.findall(r"(?m)^\s*needs:", text)),
        "chars": len(text),
        "words": len(text.split()),
        "full_gate_reprinted": "Flow after change" in text and bool(re.search(r"(?m)^\s*-\s*storage:", text)),
        "has_gate_token": "Gate token:" in text,
        "offers_gate_options": bool(re.search(r"approve with changes", text, re.I)),
        "says_unchanged_since": bool(re.search(r"unchanged since", text, re.I)),
        "handcheck_values_listed": sum(1 for v in HANDCHECK if v in text),
        "craft_disclosure": "Observable behavior unchanged" in text,
        "mentions_before_packet": bool(re.search(r"before the (review )?packet", text, re.I)),
        "mentions_lighter_lane": bool(re.search(r"lighter lane", text, re.I)),
        "reprints_phase_block": bool(re.search(r"(?m)^#+\s*Phase \d|^\|\s*File\s*\|", text)),
        "names_layering_rule": "RepositoryAbstractions_Should_Not_Return_Application_Types" in text,
        "last_line": (text.strip().splitlines() or [""])[-1][:200],
        "types_named": [t for t in TYPES if t in text],
        "projects_named": [p for p in PROJECTS if p in text],
        "port_named": "IOrderRepository" in text and "SetStateAsync" in text,
        "binding_named": "OrderRoutesSettings" in text and "Orders:Routes" in text,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--plugin", required=True)
    a = ap.parse_args()
    run_dir, plugin = os.path.abspath(a.run_dir), os.path.abspath(a.plugin)
    facts = json.loads(slurp(os.path.join(run_dir, "facts.json")))
    scenario = facts.get("SCENARIO") or re.sub(r"-[a-z](-first)?$", "", os.path.basename(run_dir))
    spec_ = json.loads(slurp(os.path.join(HERE, "scenarios.json")))
    state = next(s["state"] for s in spec_["evals"] if s["id"] == scenario)
    repo = os.path.join(run_dir, "repo")
    plan = os.path.join(repo, bf.PLAN_REL)

    with tempfile.TemporaryDirectory() as tmp:
        twin = os.path.join(tmp, "repo")
        os.makedirs(twin)
        bf.build_repo(state, twin)
        before, after = tree(twin), tree(repo)
        before_methods = methods(twin)
        twin_plan = bf.plan_text(state)
        if state not in bf.PLAN_ONLY:
            twin_plan, _rev, _tok = bf.approve(plugin, twin, twin_plan)
    changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))

    code, out = check(plugin, repo, bf.PLAN_REL)
    rev = re.search(r"plan revision ([0-9a-f]{12})", out)
    log = slurp(os.path.join(repo, bf.STEM + ".approval.log"))
    records = [l for l in log.splitlines() if l.strip()]
    acode, aout = check(plugin, repo, bf.PLAN_REL, "--approval", bf.STEM + ".approval.log") \
        if records else (None, "")
    now = slurp(plan)
    runlog = [l.split(" ", 1)[1] if " " in l else l
              for l in slurp(os.path.join(repo, "tools", ".runlog")).splitlines() if l.strip()]
    change_file = next((p for p in after if p.endswith("OrderStateChange.cs")), "")
    settable = slurp(os.path.join(repo, "src/Shop.Application/Features/Orders/SettableOrderState.cs"))

    result = {
        "scenario": scenario,
        "plan": {
            "check_exit": code,
            "check_last_line": out.strip().splitlines()[-1][:160] if out.strip() else "",
            "revision_start": facts.get("REV") or None,
            "revision_now": rev.group(1) if rev else None,
            "has_amendments_section": bool(re.search(r"(?m)^(?:#+\s*)?Amendments\b", now)),
            "says_old_and_new": bool(re.search(r"\bold\s*:", now, re.I) and re.search(r"\bnew\s*:", now, re.I)),
            "has_structure_section": bool(re.search(r"(?m)^(?:#+\s*)?Structure\b", now)),
            "says_constrained_by": bool(re.search(r"constrained by", now, re.I)),
            "chars_added": len(now) - len(twin_plan) if state not in bf.PLAN_ONLY else None,
            "tests_at": placement(now),
            "names_statusNote": "statusNote" in now,
            "limit_201_200": "201" in now and "200 characters" in now,
        },
        "approval": {
            "records": len(records),
            "last": records[-1][:260] if records else "",
            "last_names_current_revision": bool(rev and records and ("@" + rev.group(1)) in records[-1]),
            "verify_exit": acode,
            "verify_says": (aout.strip().splitlines() or [""])[0][:200],
        },
        "files_changed": changed,
        "test_methods_unchanged": methods(repo) == before_methods,
        "stub": {
            "change_type_file": change_file,
            "throws": bool(re.search(r"throw|NotImplemented", slurp(os.path.join(repo, change_file)))),
            "settable_members": re.findall(r"(?m)^\s*(\w+)\s*=\s*\d+", settable),
        },
        "runlog": runlog,
        "ran_whole_suite": any(l.strip() == "test" for l in runlog),
        "ran_invariant_suite": any("Architecture" in l or "Layering" in l or "RepositoryAbstractions" in l
                                   for l in runlog),
        "reply": reply_facts(slurp(os.path.join(run_dir, "out", "reply.md"))),
    }
    reply2 = slurp(os.path.join(run_dir, "out", "reply-2.md"))
    if reply2:
        result["reply_2"] = reply_facts(reply2)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
