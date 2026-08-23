# Task packets: mining and curation

This is the checkpoint procedure for turning session transcripts into replayable task packets for the SP-metrics pilot.
The miner is a script; curation and input-snapshotting are HUMAN steps and are never automated.

## Run the miner

On the host whose sessions you want to mine (this is a local read, zero spend):

```
python3 scripts/pilot-mine-tasks.py ~/.claude/projects [--host <label>] [--no-text]
```

- Emits one JSON line per candidate session: `source_session`, `prompt_text`, `human_turns`, `turns`, `stratum`, `host`.
- `prompt_text` is the first non-wrapper human text block in the session.
- Wrappers (slash-command invocations, system reminders, local-command caveats) start with `<` or `Caveat:` and are excluded.
- `turns` is the assistant-record count; `stratum` is `quick` at 5 or fewer assistant turns, else `multi`.
- Sessions with no assistant turn or no non-wrapper human text are skipped.
- `--no-text` drops `prompt_text` and `human_turns` and emits shape counts only.

## Pick 12 per pass

Read the candidate lines and select 12 tasks per pilot pass, stratified across `quick` and `multi`.
Aim for a mix that exercises the system prompt under test rather than flattering it: varied domains, some tasks where the SP plausibly matters, some short mechanical fixes, some longer builds.
Record which `source_session` each pick came from.

## Build each packet

For each pick, create `pilot/tasks/<id>/` containing:

- `prompt.md` - copied from `pilot/tasks/TEMPLATE/prompt.md`.
  For a `multi` task, include one `## Turn N` block per human turn, taken in order from `human_turns`.
  The turns are replayed identically to both panes so the only difference between panes is the system prompt.
- `checklist.md` - copied from `pilot/tasks/TEMPLATE/checklist.md`, with done-conditions and the exact command/output that proves each.
- `input/` - a snapshot of the minimal input state the task touches.
  This is either a `git init` fixture (a directory the harness copies and resets per pane) or a tarball of the minimal files.
  The snapshot is reset before each pane so both panes start byte-identical.

Creating `input/` snapshots is a HUMAN step: you decide which files the task actually touches and snapshot only those.

## Scrub gate (hard curation step, no exceptions)

Before any packet leaves your machine, check it against the scrub gate.

- Anything touching donor, advancement, or PII data is scrubbed or synthesized first.
  Replace real names, IDs, amounts, and queries with synthesized equivalents that preserve the task's shape.
- Raw day-job prompt text never transits off its governed host.
- Only a `--no-text` candidates file (shape counts, no prompt content) may be shipped off-host for sizing.
- If a task cannot be scrubbed without destroying what it tests, drop it and pick another.

A packet that fails the scrub gate does not get "cleaned later"; it stays off the disk of every other host.

## Git and PII control

`pilot/tasks/` is gitignored by default (the ignore rule is added in Task 7).

A packet enters git only by an explicit `git add -f pilot/tasks/<id>/` after it has passed the scrub gate.
There is no path by which an unscrubbed packet is committed: the default ignore means the accident requires two deliberate actions, and the scrub gate runs before the first one.

## Cross-host rule

Mining runs on the host that owns the sessions; packets live in this repo.
The bridge between them is:

1. Mine and curate on the source host.
2. Scrub (above).
3. Only then copy the packet directory into `pilot/tasks/` here.

`--host <label>` stamps each candidate with the label of the host it came from so provenance survives the copy.
