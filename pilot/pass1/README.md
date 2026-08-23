# Pass 1: pairwise log

Pass 1 runs the 12 paired tasks with the same model in both panes, so the only difference between panes is the system prompt under test.
This directory holds the pass-1 pairwise log and nothing else; it is created at pass time.

## Model pins (pass 1)

- Stock pane: `claude-opus-4-8`
- Variant pane: `claude-opus-4-8`

## pairwise.jsonl

One row per pair, exactly 12 rows, filled by the HUMAN blind-rating checkpoint.
A script never writes this file.
The rater (Jeremy, at least a day after any variant work) reads the blinded A/B reading copies and records the call.
Validate the filled log before computing anything with it:

```
python3 scripts/pilot-verdict.py --validate-log pilot/pass1/pairwise.jsonl
```

Row schema:

| Field       | Type                     | Meaning                                     |
|-------------|--------------------------|---------------------------------------------|
| task_id     | str                      | packet id; the join key into the metrics files |
| order       | "A=stock" or "A=variant" | side the blinding assigned for this pair    |
| rating      | "A", "B", or "tie"       | the blind call made on the anonymized texts |
| variant_won | true, false, or null     | derived from order plus rating (null on tie) |
| reason      | str                      | one line on why the call went that way      |
| rated_at    | str                      | ISO date the rating was made                |

`order` records the per-pair side the blinding actually assigned (`assign(seed, task_id)` from `scripts/pilot-blind.py`), so the orientation of every rating stays auditable against that pair's `key.sealed.json` after unblinding.
The rater works from the blinded copies only and does not consult the key while rating.

`variant_won` is derived, never judged directly:

| order       | rating | variant_won |
|-------------|--------|-------------|
| A=stock     | A      | false       |
| A=stock     | B      | true        |
| A=variant   | A      | true        |
| A=variant   | B      | false       |
| any         | tie    | null        |

## Compute the verdict

After the log is filled and the per-run metrics records exist (one Task-2 record per line, each carrying `task_id`):

```
python3 scripts/pilot-verdict.py <pairwise.jsonl> <metrics-stock.jsonl> <metrics-variant.jsonl>
```

The verdict joins the three files on `task_id`, never on line order.
Behavior must win at least 2:1 among non-ties with at least 6 non-ties, cache-write must be smaller on turn one, and no tracked cost metric may be worse than stock by more than 10 percent at the median, or the pass is not held up at this N.
Compaction timing is reported as a non-blocking secondary and never gates the verdict.
The full run procedure, including where the metrics files land, is in `pilot/RUNBOOK.md`.

The log and the metrics files are run artifacts, not instrument code; they are gitignored and never committed.
