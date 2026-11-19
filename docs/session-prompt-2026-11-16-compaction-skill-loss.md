Goal: make a ctdd-change run survive context compaction even when the harness drops the ctdd-change skill text. Do this with a SessionStart hook that fires on compaction and a `check-plan.py --next` command that reads the next step from the files on disk. First confirm how the harness drops the skill, then build and measure the fix, and bring me the decisions listed in Part 4.

Evidence
- Findings report for the session (finding 1 is this one; the others are out of scope here unless I say so):
  docs/session-findings-2026-11-16-otp-rate-limit.md
- The session transcript (13 MB; search it, do not load it whole):
  C:\Users\markoz\.claude\projects\C---GitA1-selfcare-api-src\fbaa10f0-3bbf-4ac3-98e6-f416a923c22e.jsonl
- The plan and its evidence files, usable as a real `--next` test input (read only; it belongs to another repo):
  C:\_GitA1\selfcare-api\src\docs\plans\MS-11996-otp-rate-limit-guard.md, with .approval.log, .pinstate.log, .redstate.log, .prered.diff, .pinstate-after.log and .gate-shown.md beside it. There is no .verify.log and no packet.
- The cross-session script used below is reproduced in the Appendix.

This is one analysis pass. Confirm each claim against the transcript or the docs before building on it.

What happened (finding 1)
- The transcript has two compactions. Each is a `system`/`compact_boundary` record followed by an `attachment` of type `invoked_skills`:
  - L2808 / L2818: auto, 970,274 → 27,496 tokens, CLI 2.1.325;
  - L3771 / L3778.
- Both re-attached exactly one skill, `ctdd:ctdd-tests` (17,325 chars). Skills invoked before the first compaction:
  - ctdd-review at L2237 (CLI 2.1.322);
  - ctdd-change at L2457 (2.1.322);
  - ctdd-tests at L2691 (2.1.325).
- The CLI version changed at L2623 (2.1.322 → 2.1.325, 11-16 08:44). The session was resumed after an upgrade, and ctdd-tests was the only skill invoked after that.
- After the first compaction:
  - The red pause was printed without the 7.12 content (L3185); the human had to ask "why were not phases printed out?" (L3187). The agent said "I didn't read that rule before stopping" (L3246) and then only grep'd references/execution.md (L3197).
  - Step 8.3 saved no .verify.log.
  - 8.4 ran `--git HEAD` instead of the Baseline's diff-base.
  - Step 9 never ran: no packet, no 9.1 hand-check stop after the declined hold-out, no 9.4 handover. The final reply (L3583) is free prose.
  - After the second compaction, a changed limit (plan-gated by 3.4) was edited directly in answer to L3830.
- The skill that did survive carried stale arguments: "the 24 new-behavior tests … revision c3fcf53fdb4f … compile-only stubs that throw NotImplementedException are allowed". All three were superseded by the approved revision 7315b17e9af7 (21 tests, stubs never throw).

What the docs say (verify each against the page; these came through a docs agent)
- skills.md, "Skill content lifecycle":
  - after compaction the most recent invocation of each skill is re-attached;
  - the first 5,000 tokens of each are kept;
  - re-attached skills share a 25,000-token budget, filled from the most recent invocation;
  - older skills can be dropped entirely.
- context-window.md, "What survives compaction": SessionStart hooks matching the `compact` source run after compaction, and their output lands in the compacted context.
- hooks-guide.md, "Re-inject context after compaction": the documented recipe for exactly this.
- hooks.md, SessionStart:
  - matcher/source values are startup, resume, clear, compact, fork;
  - stdin carries session_id, transcript_path, cwd, hook_event_name, source, and others;
  - plain stdout on exit 0, or `hookSpecificOutput.additionalContext`, is added to context, capped at 10,000 characters per string.
- Plugin hooks in `hooks/hooks.json` are registered when the plugin is enabled. Proof on this machine: superpowers 7.0.2 ships `hooks/hooks.json` with SessionStart `"matcher": "startup|clear|compact"`, and its context reaches these sessions.
- ctdd ships its hooks only as `hooks/*.example`. No ctdd hook is installed in the project above.

What is known and what is not
- The budget does not explain the drop. The three skills come to ~46,000 chars, about 15,000–16,000 tokens at the repo's measured 2.84–3.08 chars/token, well under 25,000. The drop is of the whole skill, not truncation to 5,000 tokens.
- Across 14 transcripts with 30 compactions (Appendix script), ctdd-change had been invoked through the Skill tool before 29 of them:
  - Kept in all 24 where it was invoked in the same CLI run.
  - Dropped in 4 (3 sessions): cf283db9 L6206, fad73bc1 L5441 (the 11-12 processing-status session's fifth compaction), fbaa10f0 L2818 and L3778.
  - All 4 drops follow a CLI restart with a version change (2.1.299→2.1.300, 2.1.322→2.1.323, 2.1.322→2.1.325) and an invocation of ctdd-tests after the restart.
  - The one compaction after a restart with no skill invoked after it kept ctdd-change (c45a257e L8915).
- Working hypothesis: after a resume, invoking any skill makes the harness forget skills invoked before the resume. Once dropped, a skill stays dropped at later compactions (fbaa10f0 L3778).
- Unexplained: superpowers:brainstorming dropped without a restart (c45a257e L3123; it launched normally at L2761).
- Not known:
  - whether a resume on the same CLI version does the same;
  - the harness's real rule.
- Whatever the rule, step 7 of ctdd-change invokes ctdd-tests by design, so any resumed ctdd-change run that reaches step 7 is exposed. The repo's compaction-reserve work (COMPACTION_PROXY_CHARS, MUST_SURVIVE, MAX_PROBE_OFFSET_CHARS in scripts/test_check_spec_surface.py) protects against truncation only. It does nothing when the skill is absent.

Part 0: confirm the mechanism (do this first, about 10 minutes)
In a throwaway directory with the ctdd plugin enabled:
1. Control:
   - `claude`; have it invoke a small skill A (ctdd:ctdd-routing), then skill B (ctdd:ctdd-tests); run `/compact`.
   - Read the new transcript in ~/.claude/projects/<dir>/ and find the `invoked_skills` attachment after the `compact_boundary`. Expect A and B.
2. Same version:
   - New session; invoke A; `/exit`.
   - `claude --resume <id>`; invoke B; `/compact`; read the attachment.
3. If step 2 keeps A, all observed drops coincided with a CLI upgrade. Say so and stop there; do not downgrade or upgrade the CLI to test it.

Report what each run re-attached. The fix in Part 1 does not depend on the answer. The answer decides D2 below and what we report to Anthropic (D8).

Part 1: `check-plan.py <plan> --next` (build)
Reads files only and runs nothing. It prints an evidence line and one `Next:` line. Exit 0 when it can name the next step, 1 when the plan needs attention (it fails its checks, or it was amended since approval), 2 when it cannot run.
Evidence, in workflow order (✓/✗ each):
- plan passes check-plan;
- an approval record for the current revision;
- pins before (`<name>.pinstate.log`, all named pins passing per check-redstate);
- red state (`<name>.redstate.log`, verified);
- pre-red diff (`<name>.prered.diff`);
- `## Intended change` in the plan;
- verification (`<name>.verify.log`);
- pins after (`<name>.pinstate-after.log`, all passing);
- packet (see D6).
`Next:` is the first missing item mapped to its step:

| First missing | Next |
|---|---|
| plan passes | 5.4: fix the plan and re-run check-plan |
| approval for this revision | 6: gate. If an older revision was approved, record the amendment under `Amendments` first. |
| pins before | 7.5–7.7 |
| red state | 7.9–7.11 |
| pre-red diff or `## Intended change` (red pause not `skip`) | 7.12: print the pause and stop for the release |
| verification | 8: implement what was released, then 8.3 |
| pins after | 8.3: re-run the pins to the pin-after path |
| packet | 9: the 9.1 hand check if the hold-out was declined, then the packet and the 9.4 handover |
| none | done |

Skip lanes the plan names no test for, as SKILL.md 7.4 and 7.8 do.

Evidence files do not arrive in order. The real plan above has pins-after but no verify.log, and `--next` must say "8.3: verification missing" for it, not "done". Without D5, `--next` cannot tell "pause printed, waiting" from "released, implementing". Say so in its output rather than guess.

Reuse check-plan's own functions (`plan_dir`, `_sidecar`, `last_approved`, `plan_revision`) and check-redstate's verdict functions through `importlib.util.spec_from_file_location`, as check-plan.py:806 already does. Do not copy them.

Part 2: `hooks/ctdd-resume.py`, a SessionStart hook (build)
- Fires on `compact`, and on `resume` too if D2 says so. Reads the hook's stdin JSON.
- Silent (no output, exit 0) when:
  - the source does not match;
  - the transcript holds no invocation of ctdd-change: a Skill tool_use with `ctdd:ctdd-change` or `ctdd-change`, a `<command-name>/ctdd:ctdd-change` user message, or a skill load "Base directory for this skill: …ctdd-change";
  - no plan is found;
  - `--next` says done;
  - anything at all fails. A hook must never break a session start.
- Finding the plan: resolve the plan dir from the hook's `cwd`. Take the stem of `<plan-dir>/<stem>.md` mentioned most recently in any tool_use input of the transcript.
  - Match stems, not `check-plan.py <path>`: this session addressed the plan through `P=docs/plans/MS-11996-otp-rate-limit-guard; … $P.md`.
  - Prefilter lines by substring before `json.loads`. Transcripts here reach 120 MB.
  - Set the hook timeout to 15–30 s.
- Output, under 1,500 characters (hard cap 10,000). A starting template:
  CTDD resume, written by the ctdd plugin after compaction from files on disk:
  This session was running ctdd-change for <plan path>. Approved revision <rev>; the plan is now <rev> (<matches | was amended after approval: re-gate first>).
  Evidence: <the --next evidence line>.
  Next: <the --next line>.
  Compaction can leave out the ctdd-change skill. Before anything else, invoke the ctdd:ctdd-change skill with the argument `resume <plan path>`, and continue at the step above; do not start again at step 0. Skill arguments re-attached with another skill that name a different plan revision are out of date: the plan file and its approval log decide.
- Tests in a new `hooks/test_ctdd_resume.py`, in the style of hooks/test_spec_edit_guard.py. Use synthetic transcript JSONL and temp plan dirs:
  1. no ctdd-change invocation → silent;
  2. source startup → silent;
  3. approval current and red state present, no Intended change → names 7.12;
  4. plan amended after approval → says re-gate;
  5. plan reached only through a shell variable holding its stem → found;
  6. two plans mentioned → the latest wins;
  7. malformed lines and a missing plan dir → silent, exit 0;
  8. `--next` says done → silent.
  Add `--next` cases in scripts/test_check_plan.py for every table row and for the out-of-order case above.
- Per this repo's rule 8: delete each rule and confirm a test fails.
- Launching on Windows:
  - `python3` here is a dead stub, and a shipped hooks.json is the same file on every OS.
  - superpowers uses a polyglot `run-hook.cmd`, which bash runs as a script and cmd runs as batch.
  - A ctdd launcher has to find a real Python: `py -3` before `python3`. Claude Code runs hook commands with Git Bash on Windows when it is installed, so the bash half must try `py` too.
  - The docs also mention a per-command `"shell": "powershell"` field and an exec form with `args`.
  - Verify the launcher by having Claude Code itself run the hook on this machine, not only by running the script by hand.

Part 3: measure (one baseline run and one after, as in evals/workflow/RUNNING.md)
- Add a scenario to evals/workflow/scenarios.json for the moment just after red state is verified in a phased plan, after compaction.
- The brief carries:
  - a compaction summary of the Shop change, modelled on the shape of L2812 in the transcript, anonymised;
  - the ctdd-tests skill text with pre-amendment arguments;
  - no ctdd-change text.
  The after run adds the hook's output.
- Assertions:
  - the reply prints the 7.12 pause: the stat from `check-spec-surface --stat --patch`, the test-file table, and one block per phase;
  - it stops with a Decision prompt;
  - it reads skills/ctdd-change/SKILL.md (the stand-in's equivalent of invoking the skill) and references/execution.md before replying.
- If the baseline already passes, the scenario does not show the finding. Tell me before changing anything.

Part 4: decisions for me (present as a numbered list I can answer by number; recommend one option each)
- D1. Ship `ctdd-resume` enabled in a real `hooks/hooks.json`, or as `hooks/*.example` like spec-edit-guard? It only reads, and it is silent unless ctdd-change ran in the session.
- D2. Matcher `compact` only, or `compact|resume`? With resume, the agent re-invokes ctdd-change right after a resume, so the skill may never be dropped at all (this depends on Part 0).
- D3. Unconditional "invoke ctdd-change" in the hook text, or only when the hook can see that the skill was not re-attached? The ordering between the `invoked_skills` attachment and SessionStart output is not documented. Unconditional costs ~4,300 tokens when the skill did survive.
- D4. A resume clause in ctdd-change, so that re-invoking it continues at `--next` instead of step 0. This is skill prose (rule 3).
  - The comment on MAX_PROBE_OFFSET_CHARS in scripts/test_check_spec_surface.py says 18 characters remain in front of 9.1. Re-measure, and expect to need a displacement.
  - Propose what moves out, with the numbers.
- D5. Record the red-pause and phase releases in `<name>.approval.log` (for example `Red pause released: "<their words>"; plan: <path>@<rev>`), so `--next` can tell waiting from released. This is an output-contract change.
- D6. Save the review packet to `<name>.packet.md` at 9.3, giving `--next` and the hook a finished state. This is an output-contract change.
- D7. Docs:
  - In docs/backlog.md, "The skill's tail is past the measured compaction boundary" and "Move steps 7–10 into references": their trigger fired, through whole-skill loss, which neither entry addresses. Record it beside them.
  - Record the documented budget (5,000 tokens per skill, 25,000 total) in docs/ctdd-in-depth.md.
  - Re-check rationale.md line 15 ("post-compaction loading retained the opening part of the skill"): true only when the skill is re-attached at all.
- D8. Report the harness behaviour to Anthropic with Part 0's reproduction (`/feedback` or a GitHub issue). Draft the text; I send it.

Constraints
- This is Windows. `python` and `python3` on PATH are dead stubs; use `py -3` or %LOCALAPPDATA%\Programs\Python\Python312\python.exe. pytest is not installed: `python -m unittest scripts.test_<name>` and `hooks.test_<name>`.
- Follow this repo's CLAUDE.md:
  - tests ship with every script change;
  - one definition of spec surface;
  - skill prose needs my approval (stop and ask);
  - deterministic before prompted;
  - rule 6: this repo is public, so nothing from the evidence above goes into it un-anonymised (no client, class, path, branch or ticket names);
  - rule 8: a guard must fail when its rule is deleted;
  - rule 9: when a budget guard fires, displace or decide, never shave;
  - rule 10: re-run after a repair.
- Do not touch the selfcare-api repository or its plans; read only.
- Commit only when I ask. No Co-Authored-By trailer.
- Do not convert line endings; `.gitattributes` pins LF.
- A runtime change bumps `.claude-plugin/plugin.json` and adds a dated CHANGELOG entry in its existing style; re-pin docs/ctdd-in-depth.md as CLAUDE.md describes.
- Evals spawn agents and cost tokens: one baseline run and one after run, unless I ask.

Finish with:
- the Part 0 result (what each run re-attached, with the transcript lines);
- the `--next` table as built, the tests added, and the full test-run output;
- the hook, its tests and output, and how Claude Code ran it on this machine (the hook's text found after a real `/compact` in a scratch session);
- the eval scenario with its baseline and after results;
- D1–D8 as a numbered list, each with your recommendation and its cost.

Appendix: the script behind the cross-session numbers
Run it as `py -3 -X utf8 reinject2.py <transcript.jsonl>...` over every transcript containing `"invoked_skills"` under C:\Users\markoz\.claude\projects. It lists each skill invoked through the Skill tool before every compaction, with KEPT or DROPPED, and counts the CLI restarts (version changes) and >2 h idle gaps since that invocation. Skills loaded by slash command are not seen as invocations; they appear as "also kept".

```python
"""Per compaction: for each skill invoked earlier (Skill tool), was it re-attached, and did the CLI restart
(version change) or go idle for long (gap) between its last invocation and the compaction?"""
import json, sys, os
from datetime import datetime

def ts(o):
    t = o.get("timestamp")
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None
    except Exception:
        return None

for path in sys.argv[1:]:
    last_inv = {}            # skill -> (line, version, restart_count_at_invocation, gap_count)
    restarts = 0
    prev_ver = None
    prev_time = None
    gaps = []
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            try:
                o = json.loads(line)
            except Exception:
                continue
            v = o.get("version")
            if v:
                if prev_ver and v != prev_ver:
                    restarts += 1
                prev_ver = v
            t = ts(o)
            if t:
                if prev_time and (t - prev_time).total_seconds() > 7200:
                    gaps.append((n, round((t - prev_time).total_seconds() / 3600, 1)))
                prev_time = t
            typ = o.get("type")
            if typ == "assistant":
                for c in (o.get("message") or {}).get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                        s = (c.get("input") or {}).get("skill")
                        last_inv[s] = (n, prev_ver, restarts, len(gaps))
            elif typ == "attachment":
                a = o.get("attachment") or {}
                if a.get("type") == "invoked_skills":
                    kept = {s.get("name") for s in a.get("skills") or []}
                    rows = []
                    for s, (ln, ver, r, g) in sorted(last_inv.items(), key=lambda kv: kv[1][0]):
                        rows.append(f"{s}@L{ln}(v{ver}) {'KEPT' if s in kept else 'DROPPED'}"
                                    f" restarts_since={restarts - r} gaps>2h_since={len(gaps) - g}")
                    extra = kept - set(last_inv)
                    out.append(f"  L{n} v{prev_ver}: " + " | ".join(rows)
                               + (f" | also kept (not via Skill tool): {sorted(extra)}" if extra else ""))
    print(f"=== {os.path.basename(os.path.dirname(path))}/{os.path.basename(path)[:8]}")
    print("\n".join(out))
```
