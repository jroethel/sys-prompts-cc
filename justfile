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
    bash scripts/pilot-isolation-check.sh

# Prove the instrument composes end to end over two real historical transcripts (zero spend).
pilot-dryrun:
    bash scripts/pilot-dryrun.sh
