# Pass 1 firing plan (quota-optimized)

State lives on disk, not in any session: `just pilot-status` shows per-pair progress
(4/4 + blinded = done), and every step below is resumable.
No Claude session needs to stay open; `just pilot-batch` fires AND blinds each pair itself.
Invoking `pilot-batch` IS the spend trigger (FIRE=1 is baked in).

Anchor: pair 1 (`loop-stack-vs-research-eval`, DONE) burned ~$42 API-equivalent (~6.5M tokens),
cache reads dominant. Tiers below are sized from replay turns x input size x original session length.

## Batches, one per 5-hour window

Run each batch from a herdr caller pane at the repo root, at the START of a fresh window:

| Batch | Tier   | Command                                                                                             |
| ---   | ---    | ---                                                                                                 |
| 1     | light  | `just pilot-batch pass1 1 spec-axis-review-subagent supervisor-review-rating-pushback vaultwise-reddit-scraper-decision terminal-mux-comparison` |
| 2     | medium | `just pilot-batch pass1 1 triage-table-accept-recall model-intel-refresh-skill-worker`              |
| 3     | medium | `just pilot-batch pass1 1 self-manual-privacy-architecture changelog-research-interrupted`          |
| 4     | heavy  | `just pilot-batch pass1 1 substack-resource-resync-worker`                                          |
| 5     | heavy  | `just pilot-batch pass1 1 loop-brainstorm-partner`                                                  |
| 6     | heavy  | `just pilot-batch pass1 1 wayfinder-roadmap-blast-radius`                                           |
| 7     | heavy  | `just pilot-batch pass1 1 molt-cycle-brief4-control-plane`                                          |

Batch 7 strictly alone: 328 original assistant turns of orchestration, the pass's outlier.

## Scheduling a batch for when the quota window resets

In the herdr caller pane (herdr keeps it alive if you detach; caffeinate keeps the Mac awake):

```
caffeinate -is sh -c 'sleep $(( ( $(date -j -f "%H:%M" "03:00" "+%s") - $(date "+%s") + 86400 ) % 86400 )); just pilot-batch pass1 1 <tasks>'
```

Replace `03:00` with the reset time the limit message names (the modulo handles crossing midnight).
No `at`/launchd needed; the sleep lives in a persistent herdr pane.

## If something fails mid-batch

- Quota tripwire fired: that side's capture was dropped on purpose. Re-run the same
  `pilot-batch` command after reset - completed pairs and completed sides are skipped, never re-spent.
- Any other failure: the failed side's pane stays open for inspection; completed work is preserved.
- `WARNING ... wrote OUTSIDE its sandbox` on a Bash line: review it (reads false-positive by design);
  Write/Edit outside the sandbox is hard-blocked by the deny wall since pair 2.

## After all 13 show `4/4 blinded`

1. Wait at least a day after any variant work, then rate blind per `pilot/RUNBOOK.md` stage 3
   into `pilot/pass1/pairwise.jsonl` (schema in `pilot/pass1/README.md`, exactly 13 rows).
   Pair-1 note: its A-side assignment leaked to a terminal once; if it stuck, say so in that
   row's `reason` and lean on the GLM second judge for that pair.
2. Validate, verdict, re-snapshot, read-out: RUNBOOK stage 4.
