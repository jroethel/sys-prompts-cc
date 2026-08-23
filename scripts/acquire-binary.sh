#!/usr/bin/env bash
# Symlink-safe Claude Code binary acquisition from the GCS release bucket.
# Verify-or-report: absent binary -> download + verify (fail on mismatch);
# present binary -> never overwrite, report verified/unverified vs manifest.
# Never writes ~/.local/bin/claude; never runs the binary (not even --version).
set -uo pipefail

V="${1:?usage: acquire-binary.sh <version>}"

LINK_BEFORE="$(readlink "$HOME/.local/bin/claude")"

BUCKET=claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819
BASE="https://storage.googleapis.com/$BUCKET/claude-code-releases"
DEST="$HOME/.local/share/claude/versions/$V"

MANIFEST="$(curl -fsSL "$BASE/$V/manifest.json")" || { echo "manifest fetch failed for $V" >&2; exit 1; }
EXPECTED="$(printf '%s' "$MANIFEST" | python3 -c 'import json,sys; print(json.load(sys.stdin)["platforms"]["darwin-arm64"]["checksum"])')" || { echo "manifest parse failed" >&2; exit 1; }

if [ ! -e "$DEST" ]; then
    mkdir -p "$(dirname "$DEST")"
    curl -fL "$BASE/$V/darwin-arm64/claude" -o "$DEST.tmp" || { rm -f "$DEST.tmp"; echo "download failed for $V" >&2; exit 1; }
    chmod +x "$DEST.tmp"
    ACTUAL="$(shasum -a 256 "$DEST.tmp" | cut -d' ' -f1)"
    if [ "$ACTUAL" != "$EXPECTED" ]; then
        rm -f "$DEST.tmp"
        echo "checksum mismatch for fresh download: got $ACTUAL want $EXPECTED" >&2
        exit 1
    fi
    mv "$DEST.tmp" "$DEST"
    STATE=verified
else
    ACTUAL="$(shasum -a 256 "$DEST" | cut -d' ' -f1)"
    if [ "$ACTUAL" = "$EXPECTED" ]; then STATE=verified; else STATE=unverified; fi
fi

[ "$LINK_BEFORE" = "$(readlink "$HOME/.local/bin/claude")" ] || { echo "SYMLINK MOVED" >&2; exit 1; }

echo "sha256: $ACTUAL $STATE"
