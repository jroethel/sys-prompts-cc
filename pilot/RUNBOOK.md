# Pilot run-book: the staged live passes

This is the human procedure for firing pass 1 and pass 2.
Every step names its script by path; nothing here is automated end to end.
Firing the 12 paired runs per pass runs through the #8 herdr skeleton (`pilot/HERDR-LAYOUT.md`, recipe `just pilot-pair`); it replaces only step 3, never the checkpoints around it.

Zero-spend proof before any of this: `just pilot-dryrun` composes the whole instrument over two real historical transcripts.

## Layout

All run artifacts land under `pilot/runs/` and `pilot/passN/pairwise.jsonl`, both gitignored.
Nothing the live passes produce is ever committed.
Per-pair layout, one self-contained resumable unit:

```
pilot/runs/passN/<task_id>/stock.jsonl        raw stock-pane transcript
pilot/runs/passN/<task_id>/variant.jsonl      raw variant-pane transcript
pilot/runs/passN/<task_id>/m-stock.jsonl      one-line metrics record, --task-id <task_id>
pilot/runs/passN/<task_id>/m-variant.jsonl    one-line metrics record, --task-id <task_id>
pilot/passN/<task_id>/{A.txt,B.txt,key.sealed.json}   blind reading copies
pilot/passN/pairwise.jsonl                    the 12-row human rating log
```

A pair is DONE when all four files under `pilot/runs/passN/<task_id>/` exist.
A crash mid-pass resumes at pair k+1: pairs already holding four files are never re-fired, so no spend is doubled.

## Spend discipline

Per-stage hard cap: $60 per pass (above the ~$30-60 estimate, one pass = one stage).
Abort trigger: if projected pass spend exceeds the cap - running per-pair token totals times the pinned model pricing, checked after every completed pair - stop firing, keep what is persisted, and check in with Jeremy before spending more.
Never respond to an overrun by quietly narrowing the pass.

## Stage 0: checkpoints before the first pair fires

Checkpoint A - live isolation confirmation (first pass only).
Run `bash scripts/pilot-isolation-check.sh` and get `isolation: ok` on the pinned daily install.
Then confirm live-session isolation once for real: fire pair 1, and before firing pair 2 verify both panes' transcripts landed in the expected config dirs and the shared-state hash set (below) is unchanged.
If anything leaked into shared state, stop the pass.

Checkpoint B - pass-2 variant model-ID resolution (pass 2 only).
Resolve the 2.1.241 default model from the pinned binary at staging, write the resolved ID into `pilot/pass2/README.md` under "Resolved variant model ID", and do not fire pass 2 while it reads `PENDING`.

Seed the two isolated config dirs per pass:

```
bash scripts/pilot-seed-config.sh /tmp/sp-pass1-stock claude-opus-4-8
bash scripts/pilot-seed-config.sh /tmp/sp-pass1-variant claude-opus-4-8
```

Pass 2 seeds the variant dir with the resolved model ID from checkpoint B, not `claude-opus-4-8`.

Snapshot the daily-install shared-state hash set (the same five paths `scripts/pilot-isolation-check.sh` guards):

```
for f in ~/.claude.json ~/.claude/settings.json ~/.tweakcc/config.json \
         ~/.tweakcc/systemPromptAppliedHashes.json ~/.tweakcc/systemPromptOriginalHashes.json; do
  [ -e "$f" ] && shasum -a 256 "$f"
done > /tmp/sp-passN-state-before.txt
```

## Stage 1: fire the 12 paired runs

One pair per task packet under `pilot/tasks/<id>/`, input snapshot reset per pane so both panes start byte-identical.
Firing mechanics are the #8 herdr skeleton's: `FIRE=1 just pilot-pair passN <task_id> <seed>` splits the two panes, replays the turns, and lands the four capture files itself (`pilot/HERDR-LAYOUT.md`).
Preview any pair with zero spend first via `just pilot-pair passN <task_id> <seed>` (`--check`).
The skeleton captures each pane's session JSONL into `pilot/runs/passN/<task_id>/` and extracts metrics immediately, one line each; done by hand it is:

```
python3 scripts/pilot-metrics.py pilot/runs/passN/<task_id>/stock.jsonl --task-id <task_id> \
  | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))' \
  > pilot/runs/passN/<task_id>/m-stock.jsonl
```

(same for `variant.jsonl` into `m-variant.jsonl`).
The compaction line is compacted onto one line because `scripts/pilot-verdict.py` joins per-line JSONL while `scripts/pilot-metrics.py` prints pretty.
Persist all four files before firing the next pair; that is what makes the pair resumable.
Run the scans per run as well; they print to stdout, read them there:

```
python3 scripts/pilot-tic-scan.py pilot/runs/passN/<task_id>/stock.jsonl
python3 scripts/pilot-completion-scan.py pilot/runs/passN/<task_id>/stock.jsonl
```

(repeat for `variant.jsonl`).

## Stage 2: blind the pairs

As soon as a pair's transcripts exist, blind it - blinding early keeps rating copies frozen before anyone re-reads the raw runs:

```
python3 scripts/pilot-blind.py pilot/runs/passN/<task_id>/stock.jsonl \
    pilot/runs/passN/<task_id>/variant.jsonl \
    --seed <pass-seed> --task-id <task_id> \
    --out pilot/passN/<task_id> --config-dir /tmp/sp-passN-stock /tmp/sp-passN-variant
```

The `--config-dir` values are the two seeded dirs, so their paths are stripped from the reading copies too.
Do not open `key.sealed.json` until after rating.

## Stage 3: rate, a day later

At least a day after any variant work, Jeremy reads each pair's `A.txt`/`B.txt` blind and rates A, B, or tie into `pilot/passN/pairwise.jsonl`, one row per pair, exactly 12 rows, schema per `pilot/pass1/README.md`.
Validate the filled log before computing anything:

```
python3 scripts/pilot-verdict.py --validate-log pilot/passN/pairwise.jsonl
```

Ties route to the GLM second judge: order-swapped, non-Claude family, via the zai tools, recorded as a tie-break signal only, never the deciding vote.

## Stage 4: verdict, re-snapshot, read-out

Compute the verdict:

```
python3 scripts/pilot-verdict.py pilot/passN/pairwise.jsonl \
    <(cat pilot/runs/passN/*/m-stock.jsonl) \
    <(cat pilot/runs/passN/*/m-variant.jsonl)
```

Re-snapshot the shared-state hash set exactly as in stage 0 into `/tmp/sp-passN-state-after.txt` and diff the two.
Any difference is a finding to report even if the verdict is clean.

Present the read-out to Jeremy for go/no-go: verdict, behavior ratio, cache-write medians, guard breaches if any, compaction secondary, the hash diff, and the pass's actual spend against the $60 cap.
An inconclusive stage triggers a check-in, not a conclusion: report what was measured and stop for a decision.
