#!/usr/bin/env bash
# pilot-isolation-check - prove CLAUDE_CONFIG_DIR redirection non-tautologically,
# zero spend: run one harmless non-model config WRITE under a throwaway config
# dir and assert (a) the shared-state hash set is byte-identical before/after,
# (b) the write landed as a NEW file inside the throwaway dir. Proves config
# redirection only - NOT full session isolation.
#
# Config-write path: pinned live against CC 2.1.204 on 2026-08-23. That build
# has NO `claude config` subcommand (claude --help Commands list), and a blind
# `claude config set ...` falls through to session init - so probing it by
# running it is unsafe. We therefore read the Commands list and use
# `claude config set -g` only when that command actually exists, else fall back
# to `claude mcp add -s user` (verified 2.1.204: pure config write, no session,
# no model call, no network - the .invalid URL is recorded, never dialed).
set -uo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Isolation invariant: the shared-state hash set, exactly these five paths.
FILES=(
  "$HOME/.claude.json"
  "$HOME/.claude/settings.json"
  "$HOME/.tweakcc/config.json"
  "$HOME/.tweakcc/systemPromptAppliedHashes.json"
  "$HOME/.tweakcc/systemPromptOriginalHashes.json"
)
hash_state() {
  local f
  for f in "${FILES[@]}"; do
    [ -e "$f" ] && shasum -a 256 "$f"
  done
}

BEFORE="$(hash_state)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

bash "$ROOT/scripts/pilot-seed-config.sh" "$TMP/cfg" claude-opus-4-8 >/dev/null
SEED="$(cd "$TMP/cfg" && find . -type f | sort)"

COMMANDS="$(claude --help 2>&1 | sed -n '/^Commands:/,$p')"
if grep -q '^  config ' <<<"$COMMANDS"; then
  CLAUDE_CONFIG_DIR="$TMP/cfg" claude config set -g pilotIsolationProbe 1 >/dev/null 2>&1 || true
elif grep -q '^  mcp ' <<<"$COMMANDS"; then
  CLAUDE_CONFIG_DIR="$TMP/cfg" claude mcp add -s user --transport http \
    pilot-isolation-probe https://example.invalid/mcp >/dev/null 2>&1 || true
fi

AFTER="$(hash_state)"
AFTER_FILES="$(cd "$TMP/cfg" && find . -type f | sort)"
# Files present after the write that the seed step did not create.
NEW_FILES="$(comm -13 <(printf '%s\n' "$SEED") <(printf '%s\n' "$AFTER_FILES"))"

fail() { echo "isolation: FAIL $1"; exit 1; }

if ! grep -q '^  config ' <<<"$COMMANDS" && ! grep -q '^  mcp ' <<<"$COMMANDS"; then
  # No config-write subcommand available in this build: assert only the
  # invariant, never a bare `isolation: ok` that overclaims redirection.
  [ "$BEFORE" = "$AFTER" ] || fail "shared-state changed"
  echo "isolation: ok (shared-state invariance only; redirection confirmed at first live pass)"
  exit 0
fi

[ "$BEFORE" = "$AFTER" ] || fail "shared-state changed"
[ -n "$NEW_FILES" ] || fail "write not redirected into config dir"
echo "isolation: ok"
