# Workflow scenarios for ctdd-change

The files in `evals/*.json` test whether a skill triggers. The scenarios here test what `ctdd-change` does once it is running: each one puts a stand-in agent at one moment of a session and records the reply it sends and what it did to the repository.

They were written to measure seven workflow decisions (D1 to D7 in the 0.57.0 changelog entry) before and after the text changed, then three of the proposals built in the same release (g, h and i), then the harness check of 0.58.0 (m), and then the loss of the skill at a compaction that 0.60.0 answers (r). The moments and the human's messages come from two real sessions. The service, its names and its domain are replaced by a synthetic one, the Shop fixture.

## What is here

- `scenarios.json` holds fourteen scenarios: six for the decisions, three pressure scenarios for the decisions that loosen "approve the exact revision", three for the proposals of 0.57.0, one for the harness check, and one that starts just after a compaction. Each gives the state of the session, the conversation so far, where the stand-in stops, and the assertions a run is judged against.
- The compaction scenario is built differently, because after a compaction the agent is not handed the skill it was following. Its brief carries what the harness leaves in context: the summary, the one skill that was re-attached with the arguments it was first given, the latest messages, and the note of the plugin's resume hook when the plugin under test has that hook. It does not say which skill to follow. Where the agent would invoke a skill, the stand-in reads that skill's `SKILL.md`, and it returns the list of plugin files it read.
- `fixture/` is the Shop service: `base/` before the change, `feature/` with the change implemented, `stubs/` with the step-7 stubs, `heavy/` with the integration project the harness scenario adds beside the Application unit project, and `plan.md`, the approved plan. A file stored as `<name>.fixture` is copied as `<name>`.
- `fixture/base/tools/run.py` is the fixture's build and test command. It is a recorded-run harness: it derives every verdict from the files in the tree, so an edit that would break the build or flip a test does so there too, and it logs each invocation to `tools/.runlog`.
- `build_fixture.py` builds one scenario into a run directory and writes the brief the stand-in reads.
- `grade.py` reads back what a run did, as facts.

## Running one scenario

Build it against the plugin version under test. The plan's approval is produced by that version's own checker, so a run carries nothing from another version.

```bash
python3 evals/workflow/build_fixture.py d1-domain-approve <run-dir> --plugin <plugin-root>
```

Give `<run-dir>/brief.md` to a fresh agent as its whole task, with no other context, and tell it not to use the Skill tool. The brief names the plugin root to read the skill from, so comparing two versions means two plugin directories and two run directories. The stand-in writes its reply to `<run-dir>/out/reply.md`.

`d2-d7-rename` has a second turn. Send its `turns[0].human` message to the same agent, with the turn's `bound`, and have it write `out/reply-2.md`.

Then read the run back:

```bash
python3 evals/workflow/grade.py <run-dir> --plugin <plugin-root>
```

`grade.py` prints facts and decides nothing. Some assertions are settled by those facts: whether the plan's revision moved, whether the approval log verifies, which files changed, whether the whole suite was run. The rest need the reply read.

## What a result does and does not show

Each scenario was run once per version, on one model. A single run shows that a behaviour can happen under a text, not how often it does. The fixture's commands are simulated, so a scenario measures what the agent decides and says, and nothing about a real toolchain. The first after-run of `d2-d7-rename` is the reason to keep running these: it found a rule being stretched that no reading of the text had.

Results of the 0.57.0 measurement are in `RESULTS-2026-11-14.md`, those of 0.58.0 in `RESULTS-2026-11-15.md`, and those of 0.60.0 in `RESULTS-2026-11-16.md`. The last one also records live runs of Claude Code itself, which is the only way to see what a compaction re-attaches, and says why the stand-in scenario has not yet measured anything.
