# Herdr workspace layout (the #8 firing skeleton)

This is the work plane that replaces RUNBOOK Stage 1.
It fires the 12 paired runs per pass; every checkpoint around Stage 1 (isolation, seeding, blinding, rating, verdict) stays exactly as the RUNBOOK has it.
Nothing here fires on its own: `--check` is zero spend, `--fire` (`FIRE=1`) is Jeremy's trigger.

## Recipes

| Recipe | Spend | What it does |
|-----------------------------------|-------------------|----------------------------------------------------------|
| `just pilot-launch stock|variant` | only if prompted  | boots one pilot binary in an isolated pane to eyeball    |
| `just pilot-pair <pass> <t> <s>`  | none (`--check`)  | validates preconditions, prints the herdr plan + targets |
| `FIRE=1 just pilot-pair ...`      | yes (one pair)    | launches both panes, replays turns, captures four files  |

`scripts/pilot-pair.sh --selftest` (pure turn-parser check, zero deps) rides in `just pilot-selftest`.

## Layout, one tab per pair

```
tab: pair <task_id>
  caller pane (orchestrator, stays focused)
  ├─ split right ──► stock pane    CLAUDE_CONFIG_DIR=/tmp/sp-<pass>-stock    binary: 2.1.204-stock
  └─ split right ──► variant pane  CLAUDE_CONFIG_DIR=/tmp/sp-<pass>-variant  binary: 2.1.204-variant-fable5
```

- Each pane runs its pilot binary with its own `CLAUDE_CONFIG_DIR`, so the two sessions never touch each other or the live install (isolation proven by `scripts/pilot-isolation-check.sh`).
- Working dir per pane is a fresh `cp -R` of the packet's `input/` snapshot, reset per side, so both panes start byte-identical and only the system prompt differs.
- Panes are split `--no-focus`; the orchestrator keeps the caller's focus. Never close a pane you did not create.

## Turn replay

Turns are parsed in order from `pilot/tasks/<task_id>/prompt.md` (`## Turn N` blocks, HTML comments dropped) and each is sent to BOTH panes via `herdr agent prompt <pane> "<turn>" --wait`.
Identical turns to both panes is the whole point: the only variable is the SP.

## Capture points (what wires into the rest of the instrument)

Per pair, `pilot/runs/<pass>/<task_id>/`:

| File               | Source                                                        |
|--------------------|--------------------------------------------------------------|
| `stock.jsonl`      | newest `/tmp/sp-<pass>-stock/projects/**/*.jsonl` after done  |
| `variant.jsonl`    | newest `/tmp/sp-<pass>-variant/projects/**/*.jsonl`           |
| `m-stock.jsonl`    | `pilot-metrics.py stock.jsonl --task-id <task_id>` (one line) |
| `m-variant.jsonl`  | `pilot-metrics.py variant.jsonl --task-id <task_id>`          |

A pair is DONE when all four exist and are non-empty.
A crash resumes at the next pair: a DONE pair is never re-fired, so no spend doubles.
Blinding, rating, and the verdict then run exactly as the RUNBOOK describes, unchanged.

## Prototype caveats (verify at the first live pass, before trusting a result)

- `herdr agent` detection of a *custom* binary path (not the `claude` on PATH): confirm the launched pilot binary is recognized so `agent prompt`/`agent wait` resolve. If not, drive it through the pane surface (`pane run` / `pane wait-output` / `pane read`) instead.
- Transcript subpath under `CLAUDE_CONFIG_DIR`: the capture assumes `projects/**/*.jsonl` moves with the config dir. Confirm on pair 1 that both transcripts actually land there (RUNBOOK Stage 0 Checkpoint A already fires pair 1 as the live-isolation confirmation).
- Alternate-screen reads: an interactive TUI on the alternate screen does not enter herdr scrollback. Capture reads the on-disk transcript, not the pane, so this only bites if you fall back to pane reads.
