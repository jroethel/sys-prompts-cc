# Pass 1 firing plan (quota-optimized)

Status 2026-09-02: PASS 1 CLOSED - VARIANT TAKES IT, by Jeremy's decision, on the standing
tally of variant 7, stock 3, tie 1 (2.33:1 over 10 non-ties, race-tainted pairs excluded; full
record in `pilot/pass1/fable-judgments.md`). The supervisor pair stays deliberately unfired at
0/4 and molt stays tainted-excluded; neither is owed a re-fire. `pairwise.jsonl` remains
placeholders by design - the Fable judgments are the rating record for this pass.

Prior context, kept for the instrument's history:

The supervisor and molt variant-side "timeouts" were
never timeouts. `herdr agent prompt --wait` matches the first state observed after submission, and
a just-submitted pane can still read stale idle, so the wait returned instantly and the capture
landed half a second after the final turn's user record (verified in both supervisor runs and
molt; substack stock was a genuine budget interrupt and stands). pilot-pair.sh now holds each turn
until the pane transcript shows an assistant record newer than the submission (`await_answer`),
inside the same budget, so a real budget exhaustion still interrupts like an impatient user.
supervisor-review-rating-pushback is cleared for a third fire under the fixed script (backups:
/tmp/sp-pass1-timeout-rerun, rerun2 subdir holds the 20-minute race casualty):
`just pilot-batch pass1 1 supervisor-review-rating-pushback`
(no PILOT_TURN_TIMEOUT override needed - the failures were the race, not the budget).
molt-cycle-brief4-control-plane's stock win is race-tainted (variant's Turn 5 was never given);
re-fire it the same way or exclude it. Otherwise: all 13 pairs captured and judged; see
`pilot/pass1/fable-judgments.md` for verdicts, tally, and cost read-out.
Final tally: variant 7, stock 5, tie 1 counting turn-budget timeouts (fails the 2:1 behavior
gate); variant 6, stock 3, tie 1 excluding the three timeout-decided pairs (exactly 2:1, passes).
Jeremy's blind rating log (`pairwise.jsonl`) remains unfilled; the Fable judgments are the
standing second-judge record.
Original context: those 5 pairs' first captures were auth-dead (every turn "Not logged in";
they predate the auth tripwire) and were cleared on 2026-09-01
(backup: /tmp/sp-pass1-dead-captures-20260901).
`reseed_creds` in scripts/pilot-pair.sh now auto-refreshes an expired/expiring live token with one
haiku-pinned live-client turn instead of dying (refresh branch untested until a fire meets an
expiring token). Re-fire commands:

| Batch | Tier   | Command                                                                       |
| ---   | ---    | ---                                                                           |
| R1    | light  | `just pilot-batch pass1 1 supervisor-review-rating-pushback vaultwise-reddit-scraper-decision terminal-mux-comparison` |
| R2    | medium | `just pilot-batch pass1 1 triage-table-accept-recall model-intel-refresh-skill-worker` |

The other 8 pairs hold blind Fable second-judge verdicts in `pilot/pass1/fable-judgments.md`
(keys unsealed 2026-09-01 after all eight verdicts were recorded; clean captures 3:2:1 variant).
The substack stock side and molt variant side ended at the 10-minute impatient-user turn budget;
that is instrument design, so they were NOT cleared.

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
- `agent_blocked` on an `agent prompt` line: the replayed agent opened an interactive dialog
  (AskUserQuestion / permission prompt). Handled automatically since 2026-08-30 - esc dismisses it
  ("User declined to answer") and the recorded turn is re-submitted. On an older script, re-run the batch.
- `Not logged in · Please run /login` in a pane: the pilots' copied OAuth token expired (the live
  client rotates the refresh token, so the copy cannot renew). Since 2026-08-30 every `--fire`
  re-copies the live token and dies fast if it is already expired ("run one turn in your normal
  claude to refresh it"); a mid-run logout is caught by an auth tripwire that drops the capture.
- `WARNING ... wrote OUTSIDE its sandbox` on a Bash line: review it (reads false-positive by design).
  The deny wall blocks Write/Edit under home paths but NOT under `/tmp`, so a packet that stages
  scratch there (e.g. molt-cycle-brief4's `/tmp/cp-review`) writes successfully. `pilot-pair`
  clears those `/tmp` roots between the two sides so the second side cannot read the first side's
  work; the between-sides cleanup is the safeguard, not the deny wall.

## After all 13 show `4/4 blinded`

1. Wait at least a day after any variant work, then rate blind per `pilot/RUNBOOK.md` stage 3
   into `pilot/pass1/pairwise.jsonl` (schema in `pilot/pass1/README.md`, exactly 13 rows).
   Pair-1 note: its A-side assignment leaked to a terminal once; if it stuck, say so in that
   row's `reason` and lean on the GLM second judge for that pair.
2. Validate, verdict, re-snapshot, read-out: RUNBOOK stage 4.
