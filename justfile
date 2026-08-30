# Acquire, extract, and normalize a Claude Code version's prompt corpus.
# Usage: just pin-target [version]   (version defaults to npm latest; pass V explicitly for non-interactive runs)
pin-target version="":
    #!/usr/bin/env bash
    set -uo pipefail
    V="{{version}}"; [ -z "$V" ] && V="$(npm view @anthropic-ai/claude-code version)"
    LINK_BEFORE="$(readlink "$HOME/.local/bin/claude")"
    BIN="$HOME/.local/share/claude/versions/$V"
    SHA="$(bash scripts/acquire-binary.sh "$V" | sed -n 's/^sha256: \([0-9a-f]*\).*/\1/p')" || exit 1
    J="$(mktemp -d)/prompts-$V.json"
    OUT="$(bash scripts/acquire-corpus.sh "$V" "$BIN" "$J")"; rc=$?
    if [ $rc -eq 3 ]; then echo "$OUT"; echo "naming required for $V - add names to config/prompt-names.json then re-run"; exit 3; fi
    [ $rc -eq 0 ] || { echo "$OUT" >&2; exit $rc; }
    N="$(printf '%s\n' "$OUT" | sed -n 's/^prompts: //p')"
    python3 scripts/normalize-corpus.py "$J" "corpora/$V"
    [ "$(readlink "$HOME/.local/bin/claude")" = "$LINK_BEFORE" ] || { echo "SYMLINK MOVED" >&2; exit 1; }
    echo "pinned: $V sha256=$SHA prompts=$N"
    # Drift check: molt against the previous pin (newest corpora/<V> below this one, by version sort).
    # Positional sort -V lookup only; a lexical `<` picks the wrong pin across digit-width
    # boundaries (2.1.99 vs 2.1.204). --retro always forwarded; molt.py should_run owns the env/tty gate.
    PREV="$( { ls -d corpora/*/ 2>/dev/null | sed 's#corpora/##;s#/##'; echo "$V"; } \
             | sort -V | awk -v v="$V" '$0==v{print p; exit} {p=$0}' )"
    if [ -n "$PREV" ] && [ "$PREV" != "$V" ]; then
        if python3 scripts/molt.py "$PREV" "$V" --emit-issue --retro; then :; else
            echo "MOLT FAILED (rc $?) for $PREV -> $V; pin succeeded but drift check did not" >&2
        fi
    else
        echo "no previous pin to molt against; skipping drift check"
    fi

# Run every molt module self-test (zero spend, zero network).
molt-selftest:
    #!/usr/bin/env bash
    set -euo pipefail
    for m in pack align verdict report retrocheck; do
        python3 scripts/molt_$m.py --selftest
    done
    python3 scripts/molt.py --selftest

# Run every pilot instrument self-test plus the isolation harness (zero spend).
pilot-selftest:
    #!/usr/bin/env bash
    set -euo pipefail
    for s in metrics tic-scan completion-scan blind mine-tasks verdict; do
        python3 scripts/pilot-$s.py --selftest
    done
    bash scripts/pilot-pair.sh --selftest
    bash scripts/pilot-isolation-check.sh

# Prove the instrument composes end to end over two real historical transcripts (zero spend).
pilot-dryrun:
    bash scripts/pilot-dryrun.sh

# Boot ONE pilot binary under an isolated seeded config, in a herdr pane, to eyeball (spends only if you prompt it).
# Usage: just pilot-launch stock|variant [model]   (model defaults to claude-opus-4-8)
pilot-launch side model="claude-opus-4-8":
    #!/usr/bin/env bash
    set -euo pipefail
    [ "{{side}}" = stock ] || [ "{{side}}" = variant ] || { echo "side must be stock|variant" >&2; exit 1; }
    [ "${HERDR_ENV:-}" = 1 ] || { echo "not inside herdr" >&2; exit 1; }
    case "{{side}}" in
      stock)   BIN="${STOCK_BIN:-$HOME/.local/share/claude-code-pilot/2.1.204-stock}";;
      variant) BIN="${VARIANT_BIN:-$HOME/.local/share/claude-code-pilot/2.1.204-variant-opus-4-8}";;
    esac
    CFG="/tmp/sp-launch-{{side}}"
    bash scripts/pilot-seed-config.sh "$CFG" "{{model}}" >/dev/null
    PANE="$(herdr pane split --current --direction right --cwd "$PWD" --no-focus \
             | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')"
    herdr pane run "$PANE" "HERDR_AGENT=claude CLAUDE_CONFIG_DIR='$CFG' '$BIN' --model {{model}}"
    echo "launched {{side}} in pane $PANE  (CLAUDE_CONFIG_DIR=$CFG)"

# Fire ONE compare pair through herdr. Default is zero-spend --check; pass FIRE=1 to spend (Jeremy's trigger).
# Usage: just pilot-pair pass1 <task_id> <seed>   [FIRE=1]
pilot-pair pass task seed:
    #!/usr/bin/env bash
    set -euo pipefail
    MODE=--check; [ "${FIRE:-}" = 1 ] && MODE=--fire
    bash scripts/pilot-pair.sh "$MODE" "{{pass}}" "{{task}}" "{{seed}}"

# Fire a batch of pairs sequentially, blinding each as it lands (SPENDS: invoking this IS the trigger).
# Stops at the first failure (e.g. quota tripwire) so a re-run resumes cleanly.
# Usage: just pilot-batch pass1 1 spec-axis-review-subagent supervisor-review-rating-pushback ...
pilot-batch pass seed +tasks:
    #!/usr/bin/env bash
    set -euo pipefail
    for t in {{tasks}}; do
      echo "=== pilot-batch: firing pair $t"
      FIRE=1 just pilot-pair {{pass}} "$t" {{seed}}
      python3 scripts/pilot-blind.py \
        "pilot/runs/{{pass}}/$t/stock.jsonl" "pilot/runs/{{pass}}/$t/variant.jsonl" \
        --seed {{seed}} --task-id "$t" --out "pilot/{{pass}}/$t" \
        --config-dir /tmp/sp-{{pass}}-stock --config-dir /tmp/sp-{{pass}}-variant
    done
    echo "=== pilot-batch: all pairs in batch DONE and blinded"

# Show per-pair progress for a pass: captured files out of 4, and blinded state.
pilot-status pass="pass1":
    #!/usr/bin/env bash
    set -uo pipefail
    for d in pilot/tasks/*/; do
      t="$(basename "$d")"; [ "$t" = TEMPLATE ] && continue
      n=0
      for f in stock.jsonl variant.jsonl m-stock.jsonl m-variant.jsonl; do
        [ -s "pilot/runs/{{pass}}/$t/$f" ] && n=$((n+1))
      done
      b="        "; [ -s "pilot/{{pass}}/$t/A.txt" ] && b="blinded "
      echo "$n/4 $b $t"
    done
