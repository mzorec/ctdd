#!/usr/bin/env python3
"""Build one workflow scenario: the fixture repository at its state, and the
brief the stand-in agent reads.

    python build_fixture.py <scenario-id> <run-dir> --plugin <plugin-root>

    <run-dir>/repo        the Shop service at the scenario's state (a git repository)
    <run-dir>/out         where the stand-in writes its reply
    <run-dir>/brief.md    the brief to hand the stand-in
    <run-dir>/facts.json  revision, gate token, diff base and paths, for grading

The plan's approval is produced by running the given plugin's own checker, so
a fixture built against one plugin version carries that version's artifacts
and nothing from another.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixture")
PLAN_REL = "docs/plans/2026-11-11-set-order-state.md"
STEM = PLAN_REL[:-3]
ORDERS = "src/Shop.Application/Features/Orders/"
DOMAIN = "src/Shop.Domain/Orders/"
PINS = ("Get_ReturnsTheOrder_ForAKnownNumber|GetOrder_ForAnUnknownNumber_Returns404|"
        "OpenApiDocument_PublishesNoEmptySummaryOrDescription")
NL = chr(10)

STRUCTURE = NL.join([
    "Structure",
    "- Types: `OrderStateOutcome` and `OrderStateChange` are new, in `src/Shop.Application/Features/Orders`, "
    "beside `SettableOrderState`, `SetOrderStateCommand`, its validator and its handler; no existing type changes shape.",
    "- Ports: `IOrderRepository` gains `SetStateAsync`; no new port.",
    "- Configuration: none new — the handler reads `OrderRoutesSettings`, already bound to `Orders:Routes`.",
    "",
])


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=NL) as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def overlay(name, repo, only=None):
    """Copy fixture/<name>/ over the repository; `only` limits it to paths
    starting with one of the given prefixes. A file stored as `<x>.fixture`
    is copied as `<x>`: this repository forbids two files of one name, and the
    fixture needs its own `CLAUDE.md` and two versions of one contract."""
    top = os.path.join(FIX, name)
    for dirpath, _dirs, files in os.walk(top):
        for fn in files:
            src = os.path.join(dirpath, fn)
            rel = os.path.relpath(src, top).replace(os.sep, "/")
            if rel.endswith(".fixture"):
                rel = rel[:-len(".fixture")]
            if only and not any(rel.startswith(p) for p in only):
                continue
            dst = os.path.join(repo, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)


def git(repo, *args):
    r = subprocess.run(["git", "-c", "user.name=eval", "-c", "user.email=eval@example.invalid",
                        "-c", "core.autocrlf=false", *args],
                       cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr}")
    return r.stdout.strip()


def runner(repo, *args):
    r = subprocess.run([sys.executable, os.path.join(repo, "tools", "run.py"), *args],
                       cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


def set_phase(repo, phase):
    write(os.path.join(repo, "tools", "state.json"), json.dumps({"phase": phase}) + NL)


def checker(plugin, repo, *args):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=repo, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, os.path.join(plugin, "scripts", "check-plan.py"), *args],
                          cwd=repo, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def intended_change(plan):
    """The 7.12 table, derived from the plan's own file list."""
    rows = []
    section = plan.split(NL + "Files likely to change" + NL, 1)[1].split(NL + NL, 1)[0]
    for line in section.split(NL):
        m = re.match(r"- (`src/[^`]+`) — (.+)$", line)
        if m:
            rows.append(f"| {m.group(1)} | {m.group(2)[:1].upper()}{m.group(2)[1:]} |")
    return NL.join(["", "## Intended change", "",
                    "Appended after approval, on 2026-11-11: a record of what will be built, "
                    "never part of what was approved.", "",
                    "| File | Intended change |", "| --- | --- |"] + rows) + NL


def plan_text(state):
    plan = read(os.path.join(FIX, "plan.md"))
    if state == "plan-only":
        plan = plan.replace(
            " Hold-out declined by human: the expected values in the `Hold-out` block are yours to "
            "recompute by hand.",
            " Hold-out: two sealed tests are asked of you; declining them is recorded as a waiver.")
        plan = plan.replace("- result: declined by human — a waiver, not a pass", "- result: pending")
        plan = re.sub(r"- human-verified expected values: [^\n]*", "- human-verified expected values: n/a", plan)
        plan = plan.replace(
            "- The hold-out was declined: the transition table rests on this session's reading plus "
            "your hand check of the listed values." + NL, "")
        return plan
    if state != "red":
        # In the phase states the stubs never registered the route.
        unmapped = "  - red: the route is not mapped yet, so the answer is `404`."
        plan = plan.replace("  - red: nothing writes the state yet, so it is still 30.", unmapped)
        plan = plan.replace("  - red: the stub handler answers success, so the answer is `204`.", unmapped)
    if state in ("packet", "phase1-clean"):
        for name in ("OrderStateOutcome.cs", "OrderStateChange.cs"):
            plan = plan.replace(ORDERS + name, DOMAIN + name)
    if state == "packet":
        # The fixture's handler never reads the routes, and a finished change
        # whose plan says it does sends the stand-in after that gap instead of
        # the moment under test. The first run of the packet scenario did.
        plan = plan.replace(
            "- The handler reads the recognised clients from `OrderRoutesSettings`, bound to "
            "`Orders:Routes`, as the two queue jobs read them." + NL, "")
    return plan


def build_repo(state, repo):
    overlay("base", repo)
    write(os.path.join(repo, ".gitignore"), "docs/plans/" + NL + "tools/.runlog" + NL + "tools/state.json" + NL)
    write(os.path.join(repo, ".ctdd.json"), json.dumps({"layers": "Domain;Persistence;Application;Api"}) + NL)
    set_phase(repo, 0)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "Shop service before the order-state change")
    diff_base = git(repo, "rev-parse", "--short", "HEAD")
    git(repo, "checkout", "-q", "-b", "feature/set-order-state")
    logs = {}
    if state == "plan-only":
        return diff_base, logs

    # 7.3 the contract, 7.6 the pins against the unchanged implementation.
    overlay("feature", repo, only=["docs/api/"])
    logs["pinstate"] = runner(repo, "test", "--filter", PINS)

    # 7.9 the tests and the compile-only stubs.
    overlay("feature", repo, only=["tests/", "src/Shop.Application/Abstractions/", ORDERS])
    overlay("stubs", repo)
    if state == "red":
        return diff_base, logs
    # The phase states start from stubs that build and leave the route unmapped.
    overlay("feature", repo, only=[ORDERS + "OrderStateChange.cs"])
    overlay("base", repo, only=["src/Shop.Api/Endpoints/"])
    if state == "red-ok":
        return diff_base, logs
    logs["redstate"] = runner(repo, "test", "--filter", "OrderState")

    # Step 8, as far as the state says.
    overlay("feature", repo, only=["src/"])
    if state == "phase1-clean":
        # Phase 1 alone: the validator and the handler are still stubs and the
        # route is unmapped. The two types live in the Domain, so no layering
        # rule is broken and the checkpoint is the only thing under test.
        overlay("stubs", repo, only=[ORDERS + "SetOrderStateCommandValidator.cs",
                                     ORDERS + "SetOrderStateCommandHandler.cs"])
        overlay("base", repo, only=["src/Shop.Api/Endpoints/"])
        to_domain(repo)
        set_phase(repo, 1)
        return diff_base, logs
    if state == "phase2":
        overlay("base", repo, only=["src/Shop.Api/Endpoints/"])
        set_phase(repo, 2)
        return diff_base, logs
    set_phase(repo, 3)
    if state == "packet":
        to_domain(repo)
        logs["pinstate-after"] = runner(repo, "test", "--filter", PINS)
    logs["verify"] = runner(repo, "test")
    return diff_base, logs


def to_domain(repo):
    """Move the two outcome types from the feature folder into the Domain."""
    for name in ("OrderStateOutcome.cs", "OrderStateChange.cs"):
        body = read(os.path.join(repo, ORDERS + name)).replace(
            "namespace Shop.Application.Features.Orders;", "namespace Shop.Domain.Orders;")
        write(os.path.join(repo, DOMAIN + name), body.replace("using Shop.Domain.Orders;" + NL + NL, ""))
        os.remove(os.path.join(repo, ORDERS + name))
    # Neither the port nor the repository needs the feature folder once the
    # types are in the Domain. The repository kept the import through the
    # first runs of `h-checkpoint-scope`, and both stand-ins stopped to remove
    # it: an edit the scenario does not ask for.
    for rel in ("src/Shop.Application/Abstractions/IOrderRepository.cs",
                "src/Shop.Persistence/OrderRepository.cs"):
        path = os.path.join(repo, rel)
        write(path, read(path).replace("using Shop.Application.Features.Orders;" + NL, ""))


def approve(plugin, repo, plan):
    """Write the plan in the form this plugin's checker accepts at a first
    gate, run its gate, and record the approval the scenario starts from."""
    path = os.path.join(repo, PLAN_REL)
    write(path, plan)
    r = checker(plugin, repo, PLAN_REL, "--gate")
    if r.returncode != 0 and "structure" in r.stdout.lower():
        plan = plan.replace(NL + "New-behavior tests" + NL, NL + STRUCTURE + NL + "New-behavior tests" + NL, 1)
        if DOMAIN + "OrderStateChange.cs" in plan:
            plan = plan.replace("in `src/Shop.Application/Features/Orders`, beside", "in `src/Shop.Domain/Orders`; in "
                                "`src/Shop.Application/Features/Orders` are")
        if "The handler reads the recognised clients" not in plan:
            plan = plan.replace("none new — the handler reads `OrderRoutesSettings`, already bound to `Orders:Routes`.",
                                "none — this change binds nothing and reads no settings.")
        write(path, plan)
        r = checker(plugin, repo, PLAN_REL, "--gate")
    if r.returncode != 0 and "invariant" in r.stdout.lower():
        # A plugin version that asks for an invariant suite gets the one this
        # service has: its layering tests.
        plan = plan.replace(NL + "Verification" + NL,
                            NL + "Verification" + NL + "- invariants: `python tools/run.py test --filter "
                            "ArchitectureTests` — expected: passes; run at step 7.10 and at every checkpoint." + NL, 1)
        write(path, plan)
        r = checker(plugin, repo, PLAN_REL, "--gate")
    if r.returncode != 0:
        raise SystemExit("the fixture plan does not pass this plugin's checker:" + NL + r.stdout + r.stderr)
    rev = re.search(r"plan revision ([0-9a-f]{12})", r.stdout).group(1)
    token = re.search(r"Gate token: ([0-9a-f]{8})", r.stdout).group(1)
    write(os.path.join(repo, STEM + ".approval.log"),
          f'Approved by: "approve" (typed at the gate); plan: {PLAN_REL}@{rev}; gate-token: {token}' + NL)
    v = checker(plugin, repo, PLAN_REL, "--approval", STEM + ".approval.log")
    if v.returncode != 0:
        raise SystemExit("the fixture approval does not verify:" + NL + v.stdout + v.stderr)
    return plan, rev, token


def brief(scenario, common, facts):
    def fill(text):
        for key, value in facts.items():
            text = text.replace("{" + key + "}", str(value))
        return text
    situation = ([] if scenario.get("no_common_situation") else common) + scenario["situation"]
    talk = []
    for turn in scenario["conversation"]:
        label = {"human": "**The human:**", "assistant": "**You, the agent:**",
                 "note": "*(note)*"}[turn["role"]]
        talk.append(label + NL + NL + turn["text"])
    return fill(NL.join([
        "# Stand-in brief",
        "",
        "You are standing in for a coding agent in the middle of a working session, for exactly one reply. "
        "Behave exactly as that agent would at this point: it follows its workflow skill to the letter, and "
        "you produce the reply it would send next. This is not a discussion of the skill; do the work.",
        "",
        "## The skill the session is following",
        "",
        "The plugin root is `{PLUGIN}`. The session is inside its `ctdd-change` skill: read "
        "`{PLUGIN}/skills/ctdd-change/SKILL.md` now, completely, and follow it as the authoritative workflow "
        "from the point described below. Load its `references/` files only where a step tells you to. Where "
        "it tells you to invoke `ctdd-tests`, read `{PLUGIN}/skills/ctdd-tests/SKILL.md` and follow that. "
        "Do not use the Skill tool, and do not use any other copy of these skills. `${CLAUDE_PLUGIN_ROOT}` "
        "means `{PLUGIN}` and `${CLAUDE_PROJECT_DIR}` means `{REPO}`. For Python use `\"{PY}\"`: `python` and "
        "`python3` on PATH are dead stubs here, and that includes the repository's own `python tools/run.py` "
        "commands.",
        "",
        "## The repository",
        "",
        "`{REPO}` is a git repository holding the service being changed. Work only inside it. Its `CLAUDE.md` "
        "gives the build and test commands. Run the plugin's checkers from that directory with "
        "`CLAUDE_PROJECT_DIR` set to it.",
        "",
        "## Where the session stands",
        "",
        NL.join("- " + s for s in situation),
        "",
        "## The conversation so far, most recent last",
        "",
        (NL + NL).join(talk),
        "",
        "## What to do",
        "",
        "Do what the agent does next, with real actions: edit files, run the checkers, run the repository's "
        "commands, exactly as the workflow has it at this point. " + scenario["bound"],
        "",
        "Then write the reply the agent sends to the human, the complete text the human would see and nothing "
        "else, to `{OUT}/reply.md`. Output that only appeared in your tool results is not part of the reply "
        "unless you put it there.",
        "",
        "Finish by returning three lines: what you did, where you stopped, and why there.",
        "",
    ]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("run_dir")
    ap.add_argument("--plugin", required=True)
    a = ap.parse_args()
    spec = json.loads(read(os.path.join(HERE, "scenarios.json")))
    scenario = next((s for s in spec["evals"] if s["id"] == a.scenario), None)
    if scenario is None:
        raise SystemExit(f"no scenario {a.scenario!r}; have: " + ", ".join(s["id"] for s in spec["evals"]))
    run_dir = os.path.abspath(a.run_dir)
    plugin = os.path.abspath(a.plugin)
    repo, out = os.path.join(run_dir, "repo"), os.path.join(run_dir, "out")
    if os.path.exists(repo):
        raise SystemExit(f"{repo} already exists; build into a fresh run directory")
    os.makedirs(repo)
    os.makedirs(out, exist_ok=True)

    state = scenario["state"]
    diff_base, logs = build_repo(state, repo)
    plan = plan_text(state)
    rev = token = None
    if state == "plan-only":
        write(os.path.join(repo, PLAN_REL), plan)
    else:
        plan, rev, token = approve(plugin, repo, plan)
        if state not in ("red", "red-ok"):
            write(os.path.join(repo, PLAN_REL), plan.rstrip(NL) + NL + intended_change(plan))
    for name, text in logs.items():
        write(os.path.join(repo, f"{STEM}.{name}.log"), text)
    runlog = os.path.join(repo, "tools", ".runlog")
    if os.path.exists(runlog):
        os.remove(runlog)

    slash = lambda p: p.replace(os.sep, "/")
    facts = {"SCENARIO": a.scenario, "PLUGIN": slash(plugin), "REPO": slash(repo), "OUT": slash(out),
             "PY": slash(sys.executable), "DIFF_BASE": diff_base,
             "REV": rev or "", "TOKEN": token or "", "PLAN": PLAN_REL}
    write(os.path.join(run_dir, "brief.md"), brief(scenario, spec["common_situation"], facts))
    write(os.path.join(run_dir, "facts.json"), json.dumps(facts, indent=2) + NL)
    print(json.dumps({"scenario": a.scenario, "state": state, "brief": slash(os.path.join(run_dir, "brief.md")),
                      "revision": rev, "diff_base": diff_base}))


if __name__ == "__main__":
    main()
