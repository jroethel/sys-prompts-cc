#!/usr/bin/env bash
# pilot-dryrun - end-to-end zero-spend tracer over two real historical transcripts.
# Picks the two newest session JSONLs as a stand-in stock/variant pair and runs
# every instrument stage over them: blind, per-run metrics, tic scan, completion
# scan, a synthesized one-row pairwise log, and the verdict. Proves composition
# and exit 0, not a positive verdict: one pair is below the behavior floor of 6,
# so the read-out is expected to be inconclusive.
# Scratch outputs go to a mktemp dir OUTSIDE the repo, never under pilot/, so
# the run produces nothing that needs tracking.
set -euo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Pick the two newest transcripts by mtime, skipping any whose final byte is
# not a newline: the newest file is often the live session this script runs in,
# and a torn in-flight append would fail the parsers through no fault of theirs.
T1=""; T2=""
while IFS= read -r f; do
    [ -n "$(tail -c 1 "$f")" ] && continue
    if [ -z "$T1" ]; then T1="$f"
    elif [ -z "$T2" ]; then T2="$f"; break; fi
done < <(ls -t "$HOME"/.claude/projects/*/*.jsonl)
[ -n "$T2" ] || { echo "dryrun: need two complete transcripts" >&2; exit 1; }

D="$(mktemp -d)"
trap 'rm -rf "$D"' EXIT

echo "pair: $(basename "$T1") vs $(basename "$T2")  (task_id dry01, seed 2)"
python3 "$ROOT/scripts/pilot-blind.py" "$T1" "$T2" --seed 2 --task-id dry01 \
    --out "$D/blind" --config-dir /tmp

# pilot-metrics.py prints one pretty-printed record; the verdict joins per-line
# JSONL, so compact each record onto one line at the seam this script owns.
compact() { python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))'; }
python3 "$ROOT/scripts/pilot-metrics.py" "$T1" --task-id dry01 | compact > "$D/m-stock.jsonl"
python3 "$ROOT/scripts/pilot-metrics.py" "$T2" --task-id dry01 | compact > "$D/m-variant.jsonl"

python3 "$ROOT/scripts/pilot-tic-scan.py" "$T1" >/dev/null
python3 "$ROOT/scripts/pilot-completion-scan.py" "$T1" >/dev/null

# Synthesized 1-row pairwise log: fixed outcome for the tracer, not a rating.
printf '%s\n' '{"task_id":"dry01","variant_won":true}' > "$D/pw.jsonl"

python3 "$ROOT/scripts/pilot-verdict.py" "$D/pw.jsonl" "$D/m-stock.jsonl" "$D/m-variant.jsonl"

echo "dryrun: ok"
