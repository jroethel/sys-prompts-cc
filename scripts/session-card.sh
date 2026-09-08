#!/usr/bin/env bash
# session-card.sh - open, log, and close the one session card for the current work session
# (seam 1 recording convention). One plain-markdown card per session under docs/sessions/,
# updated in place, committed with the work it records; this script never runs git.
# Cards are harness-agnostic: no field names an agent, any harness or human can write and read them.
#   open "<title>" [<token>]          create a card, print its repo-relative path on stdout
#   log "<text>"                      append one timestamped line to the newest open card's ## Log
#   close <status> "<why>" "<next>"   stamp a terminal status and its reason onto the newest open card
# Terminal statuses, closed and exact: done, blocked, handed-off, parked, aborted.
# Exits: 0 ok; 2 usage; 3 log/close with no open card; 4 close status outside the vocabulary;
#   7 log/close where two open cards tie on session: to the second (tied files named on stderr).
set -uo pipefail
export LC_ALL=C

now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# Free text rides through tr so no value can break the single-line frontmatter or split a log line.
sanitize() { printf '%s' "$1" | tr '\t\n' '  '; }

# Title -> slug: lowercased, every run outside [a-z0-9] collapsed to one dash, edge dashes stripped.
slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

usage_error() {
  {
    echo "usage: $0 open \"<title>\" [<token>]"
    echo "       $0 log \"<text>\""
    echo "       $0 close <status> \"<why>\" \"<next>\"  # status: done|blocked|handed-off|parked|aborted"
    echo "error: $1"
  } >&2
  exit 2
}

# Resolve the newest open card by its session: timestamp into OPEN_FILE.
# Exit 3 when no card is open; exit 7 naming the tied files when two open cards share the newest
# timestamp, because a silent pick between same-second cards would target one at random.
resolve_open() {
  local f ts cands="" max_ts tied n
  local TAB
  TAB="$(printf '\t')"
  for f in docs/sessions/*.md; do
    [ -f "$f" ] || continue
    grep -q '^status: open$' "$f" || continue
    ts="$(awk '/^session: /{ print $2; exit }' "$f")"
    [ -n "$ts" ] || continue
    cands="${cands}${ts}${TAB}${f}
"
  done
  [ -n "$cands" ] || { echo "error: no open session card in docs/sessions/" >&2; exit 3; }
  max_ts="$(printf '%s' "$cands" | awk -F'\t' '{ print $1 }' | sort | tail -n 1)"
  tied="$(printf '%s' "$cands" | awk -F'\t' -v t="$max_ts" '$1 == t { print $2 }')"
  n="$(printf '%s' "$tied" | grep -c .)"
  if [ "$n" -ge 2 ]; then
    echo "error: open session cards tie on session: $max_ts - refusing to pick one:" >&2
    printf '%s\n' "$tied" >&2
    exit 7
  fi
  OPEN_FILE="$tied"
}

# Append one already-formed line at the end of the card's ## Log section: before any later ##
# heading if one exists, else at end of file. ENTRY rides ENVIRON, not -v, so free text with
# backslashes survives awk's -v escape processing unchanged.
log_line() {                         # log_line <file> "<full line>"
  local tmp="$1.tmp.$$"
  ENTRY="$2" awk '
    /^## / { if (inlog) { print ENVIRON["ENTRY"]; inlog = 0 } }
    /^## Log$/ { inlog = 1 }
    { print }
    END { if (inlog) print ENVIRON["ENTRY"] }
  ' "$1" > "$tmp" && mv "$tmp" "$1"
}

cmd_open() {                         # cmd_open <title> <token-or-empty>
  local title token now day slug stem path n
  title="$(sanitize "$1")"
  token="$(sanitize "${2:-}")"
  now="$(now_iso)"
  day="${now%%T*}"
  slug="$(slugify "$title")"
  if [ -n "$token" ]; then
    stem="${day}.${token}.${slug}"
  else
    stem="${day}.${slug}"
  fi
  mkdir -p docs/sessions
  path="docs/sessions/${stem}.md"
  n=2
  while [ -e "$path" ]; do           # -2, -3, ... until a free name; an existing card is never overwritten
    path="docs/sessions/${stem}-${n}.md"
    n=$((n + 1))
  done
  {
    printf -- '---\n'
    printf 'session_card: true\n'
    printf 'session: %s\n' "$now"
    printf 'token: %s\n' "$token"
    printf 'title: %s\n' "$title"
    printf 'status: open\n'
    printf 'closed: \n'
    printf 'why: \n'
    printf 'next: \n'
    printf -- '---\n\n'
    printf '# %s\n\n' "$title"
    printf '## Log\n\n'
    printf -- '- %s opened\n' "$now"
  } > "$path"
  echo "$path"
}

cmd_log() {                          # cmd_log <text>
  resolve_open
  log_line "$OPEN_FILE" "- $(now_iso) $(sanitize "$1")"
}

cmd_close() {                        # cmd_close <status> <why> <next>
  local status why nxt now tmp
  status="$1"
  case "$status" in
    done|blocked|handed-off|parked|aborted) ;;   # closed vocabulary, a case statement not a regex
    *)
      echo "error: '$status' is not a terminal status (done|blocked|handed-off|parked|aborted)" >&2
      exit 4
      ;;
  esac
  resolve_open
  now="$(now_iso)"
  why="$(sanitize "$2")"
  nxt="$(sanitize "$3")"
  tmp="$OPEN_FILE.tmp.$$"
  ST="status: $status" CL="closed: $now" WHY="why: $why" NX="next: $nxt" awk '
    NR == 1 && $0 == "---" { infm = 1; print; next }   # rewrite keys in place inside the first
    infm && $0 == "---" { infm = 0; print; next }      # frontmatter block only, so no key duplicates
    infm && /^status:/ { print ENVIRON["ST"]; next }
    infm && /^closed:/ { print ENVIRON["CL"]; next }
    infm && /^why:/    { print ENVIRON["WHY"]; next }
    infm && /^next:/   { print ENVIRON["NX"]; next }
    { print }
  ' "$OPEN_FILE" > "$tmp" && mv "$tmp" "$OPEN_FILE"
  log_line "$OPEN_FILE" "- $(now_iso) closed $status"
}

case "${1:-}" in
  open)
    { [ $# -ge 2 ] && [ $# -le 3 ]; } || usage_error "open takes \"<title>\" and an optional <token>"
    cmd_open "$2" "${3:-}"
    ;;
  log)
    [ $# -eq 2 ] || usage_error "log takes \"<text>\""
    cmd_log "$2"
    ;;
  close)
    [ $# -eq 4 ] || usage_error "close takes <status> \"<why>\" \"<next>\""
    cmd_close "$2" "$3" "$4"
    ;;
  *)
    usage_error "unknown or missing subcommand"
    ;;
esac
