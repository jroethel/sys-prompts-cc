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
      variant) BIN="${VARIANT_BIN:-$HOME/.local/share/claude-code-pilot/2.1.204-variant-fable5}";;
    esac
    CFG="/tmp/sp-launch-{{side}}"
    bash scripts/pilot-seed-config.sh "$CFG" "{{model}}" >/dev/null
    PANE="$(herdr pane split --current --direction right --cwd "$PWD" --no-focus \
             | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')"
    herdr pane run "$PANE" "CLAUDE_CONFIG_DIR='$CFG' '$BIN' --model {{model}}"
    echo "launched {{side}} in pane $PANE  (CLAUDE_CONFIG_DIR=$CFG)"

# Fire ONE compare pair through herdr. Default is zero-spend --check; pass FIRE=1 to spend (Jeremy's trigger).
# Usage: just pilot-pair pass1 <task_id> <seed>   [FIRE=1]
pilot-pair pass task seed:
    #!/usr/bin/env bash
    set -euo pipefail
    MODE=--check; [ "${FIRE:-}" = 1 ] && MODE=--fire
    bash scripts/pilot-pair.sh "$MODE" "{{pass}}" "{{task}}" "{{seed}}"
