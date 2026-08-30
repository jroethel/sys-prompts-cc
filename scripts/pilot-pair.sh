#!/usr/bin/env bash
# pilot-pair - fire ONE compare pair through herdr (the #8 firing skeleton).
#
# Replaces RUNBOOK Stage 1 for a single task packet: splits two herdr panes,
# launches the stock and variant pilot binaries each under its own seeded
# CLAUDE_CONFIG_DIR, replays the packet's turns identically to both, then
# captures the four per-pair files the rest of the instrument consumes:
#   pilot/runs/<passN>/<task_id>/{stock,variant}.jsonl   raw transcripts
#   pilot/runs/<passN>/<task_id>/m-{stock,variant}.jsonl one-line metrics
# A pair is DONE when all four exist; a re-run skips a pair already DONE.
#
# Modes:
#   --selftest                       pure turn-parser + plan-builder unit check, zero deps
#   --check   <passN> <task_id> <seed>   validate every precondition, print the herdr
#                                        plan and capture targets, spend nothing
#   --fire    <passN> <task_id> <seed>   live: launch both binaries and replay (SPENDS)
#
# The live launch/replay/capture mechanics are prototype and UNVERIFIED end to
# end - firing is Jeremy's trigger, not the script's. --check is what the design
# is reacted to. Binaries override via STOCK_BIN / VARIANT_BIN env.
set -euo pipefail
export LC_ALL=C

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STOCK_BIN="${STOCK_BIN:-$HOME/.local/share/claude-code-pilot/2.1.204-stock}"
VARIANT_BIN="${VARIANT_BIN:-$HOME/.local/share/claude-code-pilot/2.1.204-variant-opus-4-8}"

die() { echo "pilot-pair: $1" >&2; exit 1; }

# Parse ordered turn texts out of a packet prompt.md. Emits one NUL-terminated
# record per "## Turn N" block, in order, comment/blank-only blocks dropped.
parse_turns() {
  python3 - "$1" <<'PY'
import re, sys
txt = open(sys.argv[1], encoding='utf-8').read()
# Split on "## Turn N" headers; keep only the body under each.
parts = re.split(r'(?m)^##\s+Turn\s+\d+\s*$', txt)
for body in parts[1:]:
    # Drop HTML comments and surrounding blank lines.
    body = re.sub(r'(?s)<!--.*?-->', '', body).strip()
    if body:
        sys.stdout.write(body + '\0')
PY
}

selftest() {
  local tmp; tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN
  cat > "$tmp/prompt.md" <<'EOF'
# Task demo (multi)

## Turn 1

first request text

<!-- multi only -->

## Turn 2

<!-- a comment that must be dropped -->
second request text
EOF
  local n; n="$(parse_turns "$tmp/prompt.md" | tr -dc '\0' | wc -c | tr -d ' ')"
  [ "$n" = "2" ] || die "selftest: expected 2 turns, got $n"
  local first; first="$(parse_turns "$tmp/prompt.md" | { IFS= read -r -d '' r; printf '%s' "$r"; })"
  [ "$first" = "first request text" ] || die "selftest: turn-1 body wrong: [$first]"
  # A comment-only Turn block yields no record.
  printf '# t\n\n## Turn 1\n\n<!-- only a comment -->\n' > "$tmp/c.md"
  local z; z="$(parse_turns "$tmp/c.md" | tr -dc '\0' | wc -c | tr -d ' ')"
  [ "$z" = "0" ] || die "selftest: comment-only block should yield 0 turns, got $z"
  echo "pilot-pair: selftest ok"
}

# Shared precondition validation for --check and --fire.
preflight() {
  local pass="$1" task="$2"
  [ "${HERDR_ENV:-}" = 1 ] || die "not inside herdr (HERDR_ENV != 1)"
  [ -x "$STOCK_BIN" ]   || die "stock binary not executable: $STOCK_BIN"
  [ -x "$VARIANT_BIN" ] || die "variant binary not executable: $VARIANT_BIN"
  local pkt="$ROOT/pilot/tasks/$task"
  [ -f "$pkt/prompt.md" ] || die "no packet prompt: $pkt/prompt.md"
  [ -e "$pkt/input" ]     || die "no input snapshot: $pkt/input"
  CFG_STOCK="/tmp/sp-$pass-stock"; CFG_VARIANT="/tmp/sp-$pass-variant"
  [ -f "$CFG_STOCK/settings.json" ]   || die "stock config dir not seeded (RUNBOOK Stage 0): $CFG_STOCK"
  [ -f "$CFG_VARIANT/settings.json" ] || die "variant config dir not seeded (RUNBOOK Stage 0): $CFG_VARIANT"
  TURNS_N="$(parse_turns "$pkt/prompt.md" | tr -dc '\0' | wc -c | tr -d ' ')"
  [ "$TURNS_N" -ge 1 ] || die "packet has no replayable turns: $pkt/prompt.md"
  herdr pane current --current >/dev/null 2>&1 || die "herdr not responding"
  OUT="$ROOT/pilot/runs/$pass/$task"
}

# True when the pair already holds all four files.
pair_done() {
  [ -s "$OUT/stock.jsonl" ] && [ -s "$OUT/variant.jsonl" ] \
    && [ -s "$OUT/m-stock.jsonl" ] && [ -s "$OUT/m-variant.jsonl" ]
}

check() {
  preflight "$1" "$2"
  if pair_done; then echo "pilot-pair: pair $2 already DONE (4 files present); --fire would skip it"; fi
  cat <<EOF
plan for pair $2 (pass $1, seed $3), $TURNS_N turn(s):
  stock   pane: run '$STOCK_BIN'   cwd=<reset input>  CLAUDE_CONFIG_DIR=$CFG_STOCK
  variant pane: run '$VARIANT_BIN' cwd=<reset input>  CLAUDE_CONFIG_DIR=$CFG_VARIANT
  replay:  each turn -> 'herdr agent prompt <pane> "<turn>" --wait' to BOTH panes, in order
  capture: newest \$CLAUDE_CONFIG_DIR/projects/**/*.jsonl per side ->
             $OUT/stock.jsonl
             $OUT/variant.jsonl
           then pilot-metrics.py --task-id $2 -> m-stock.jsonl / m-variant.jsonl
  DONE-when: all four files above exist and are non-empty
pilot-pair: check ok (zero spend)
EOF
}

# Launch one side, replay every turn, capture transcript + metrics.
# Prototype: exact agent-start of a custom binary path and the transcript
# subpath under CLAUDE_CONFIG_DIR are verified at the first live pass.
fire_side() {
  local side="$1" bin="$2" cfg="$3" task="$4" seed_pkt="$5"
  # Side-level resume: a side whose two capture files already exist is never
  # re-fired, so a crash between sides re-runs only the missing side.
  if [ -s "$OUT/$side.jsonl" ] && [ -s "$OUT/m-$side.jsonl" ]; then
    echo "pilot-pair: $side side already captured, skipping (no double spend)"
    return 0
  fi
  local work="/tmp/sp-pair-$task-$side"
  rm -rf "$work"; cp -R "$seed_pkt/input" "$work"   # byte-identical reset per side
  # Pre-trust the work dir so the pane never blocks on the folder-trust dialog.
  # Key by realpath too: on macOS /tmp resolves to /private/tmp and the binary
  # looks the project up under the resolved path.
  python3 - "$cfg/.claude.json" "$work" <<'PY'
import json, os, sys
path, work = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as f:
    cfg = json.load(f)
projects = cfg.setdefault('projects', {})
for key in {work, os.path.realpath(work)}:
    projects[key] = {"hasTrustDialogAccepted": True}
with open(path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
PY
  # Fresh session state per side: prior pairs' transcripts are already captured,
  # and auto-memory written by an earlier pair must not leak into this one.
  rm -rf "$cfg/projects"
  local pane
  pane="$(herdr pane split --current --direction right --cwd "$work" --no-focus \
            | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["pane"]["pane_id"])')"
  # HERDR_AGENT=claude: the pilot binaries' names hide them from herdr's
  # foreground-process detection; the hint selects the claude screen manifest.
  herdr pane run "$pane" "HERDR_AGENT=claude CLAUDE_CONFIG_DIR='$cfg' '$bin' --model \"\$(python3 -c \"import json;print(json.load(open('$cfg/settings.json'))['model'])\")\""
  # agent wait fails immediately with agent_not_found until detection registers
  # the booting process, so poll until the pane is a live idle agent.
  local ok="" i
  for i in $(seq 1 20); do
    if herdr agent wait "$pane" --until idle --timeout 15000 >/dev/null 2>&1; then ok=1; break; fi
    sleep 1
  done
  [ -n "$ok" ] || die "pane $pane never became an idle claude agent (try: herdr agent explain $pane)"
  local pout
  while IFS= read -r -d '' turn; do
    if ! pout="$(herdr agent prompt "$pane" "$turn" --wait --timeout 600000 2>&1)"; then
      if grep -q agent_prompt_stalled <<<"$pout"; then
        # A trailing @-mention pops CC's file-picker after the bracketed paste
        # lands, and the popup swallows the submit Enter, leaving the turn text
        # sitting in the composer (observed live 2026-08-29). esc closes the
        # popup without touching the composer text; enter submits it.
        herdr agent send-keys "$pane" esc >/dev/null
        sleep 1
        herdr agent send-keys "$pane" enter >/dev/null
        herdr agent wait "$pane" --timeout 600000 >/dev/null \
          || die "$side stalled and popup recovery did not start a turn (herdr agent read $pane)"
      else
        die "agent prompt failed on $side: $pout"
      fi
    fi
  done < <(parse_turns "$seed_pkt/prompt.md")
  local t
  t="$(ls -t "$cfg"/projects/*/*.jsonl 2>/dev/null | head -n1)" || true
  [ -n "$t" ] || die "no transcript captured under $cfg/projects (verify CLAUDE_CONFIG_DIR transcript path)"
  cp "$t" "$OUT/$side.jsonl"
  # Quota tripwire: a usage-limit refusal mid-side leaves a truncated transcript
  # that would otherwise be captured and marked DONE. Scan the tail (limit hits
  # end a session, and tail-only avoids false positives from task content that
  # merely discusses limits); on a hit, drop the capture so the side re-fires
  # after the window resets. Best-effort string match, not a verified schema.
  if tail -n 5 "$OUT/$side.jsonl" | LC_ALL=C grep -aiqE 'usage limit|limit reached|limit will reset'; then
    rm -f "$OUT/$side.jsonl"
    die "$side hit a usage limit mid-run; capture dropped - re-fire this pair after the window resets"
  fi
  python3 "$ROOT/scripts/pilot-metrics.py" "$OUT/$side.jsonl" --task-id "$task" \
    | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))' > "$OUT/m-$side.jsonl"
  # Bypass mode lets a pane write outside its sandbox when the packet prompt
  # names a real path. Detect it: such files leak state between the panes (the
  # other side can read this side's answer), so quarantine them before firing
  # the other side. Warn only; moving user files is a human call.
  python3 - "$OUT/$side.jsonl" "$work" "$side" "$cfg" <<'PY'
import json, sys
path, work, side, cfg = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
outside = []
for line in open(path):
    line = line.strip()
    if not line: continue
    r = json.loads(line)
    if r.get('type') != 'assistant': continue
    for b in (r.get('message') or {}).get('content') or []:
        if not (isinstance(b, dict) and b.get('type') == 'tool_use'):
            continue
        if b.get('name') in ('Write', 'Edit', 'NotebookEdit'):
            fp = (b.get('input') or {}).get('file_path') or ''
            inside = (fp.startswith(work) or fp.startswith('/private' + work)
                      or fp.startswith(cfg))  # pane's own config dir (auto-memory etc.)
            if fp and not inside:
                outside.append(fp)
        elif b.get('name') == 'Bash':
            # Deny rules cannot path-scope Bash, so home-path mentions in
            # commands are surfaced for human review (reads will false-positive;
            # this is a tripwire, not a verdict).
            cmd = (b.get('input') or {}).get('command') or ''
            if '/Users/' in cmd or '~/' in cmd:
                outside.append('Bash: ' + cmd[:120])
for fp in sorted(set(outside)):
    print(f"pilot-pair: WARNING {side} wrote OUTSIDE its sandbox: {fp} - quarantine before firing the other side", file=sys.stderr)
PY
  # This function split the pane, so it cleans it up. Close only on success:
  # a failed side keeps its pane open for inspection.
  herdr pane close "$pane" >/dev/null 2>&1 || true
}

fire() {
  preflight "$1" "$2"
  mkdir -p "$OUT"
  if pair_done; then echo "pilot-pair: pair $2 already DONE, skipping (no re-spend)"; return 0; fi
  local pkt="$ROOT/pilot/tasks/$2"
  fire_side stock   "$STOCK_BIN"   "$CFG_STOCK"   "$2" "$pkt"
  fire_side variant "$VARIANT_BIN" "$CFG_VARIANT" "$2" "$pkt"
  pair_done || die "fired but pair not DONE (missing capture file); inspect $OUT"
  echo "pilot-pair: pair $2 DONE -> $OUT"
}

case "${1:-}" in
  --selftest) selftest ;;
  --check) shift; [ $# -eq 3 ] || die "usage: pilot-pair.sh --check <passN> <task_id> <seed>"; check "$@" ;;
  --fire)  shift; [ $# -eq 3 ] || die "usage: pilot-pair.sh --fire  <passN> <task_id> <seed>"; fire  "$@" ;;
  *) die "usage: pilot-pair.sh --selftest | --check <passN> <task_id> <seed> | --fire <passN> <task_id> <seed>" ;;
esac
