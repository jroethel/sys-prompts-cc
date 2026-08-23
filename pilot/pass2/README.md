# Pass 2: pairwise log

Pass 2 runs the same 12 paired tasks with the old and new model generations split across the panes, testing the system prompt where the molt will actually land.
This directory holds the pass-2 pairwise log and nothing else; it is created at pass time.

## Model pins (pass 2)

- Stock pane: `claude-opus-4-8` (old generation)
- Variant pane: the 2.1.241 default model, resolved from the pinned binary at pass-2 staging and recorded here before the first run fires.
  Resolve it with `scripts/pilot-blind.py`'s toolchain or whatever the RUNBOOK specifies, write the resolved ID below, and do not fire the pass until it is written.

Resolved variant model ID (fill in at staging): `PENDING`

## pairwise.jsonl

One row per pair, exactly 12 rows, filled by the HUMAN blind-rating checkpoint.
A script never writes this file.
The rater (Jeremy, at least a day after any variant work) reads the blinded A/B reading copies and records the call.
Validate the filled log before computing anything with it:

```
python3 scripts/pilot-verdict.py --validate-log pilot/pass2/pairwise.jsonl
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
