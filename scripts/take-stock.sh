#!/usr/bin/env bash
# take-stock - rebuild one repo's recorded state from git, session cards, and handoffs, so
# "where did I leave off" is answered by derivation instead of reconstruction. Default output
# is the human report: authoritative handoff, live handoff count, open and newest-closed
# session cards, newest commit, went-stale verdict, next step. --cards emits the 7-field
# tab-separated intermediate TSV (kind, ref, status, token, title, last_activity, marker; no
# header) that board-cards.sh joins into the board lanes. Handoff state is derived by
# handoff-log.sh, called script-relative exactly as lifecycle-lint.sh calls it. The script
# never creates directories and never writes to the target repo. Exit codes: 0 success,
# 2 usage error or unreadable repo root.
set -uo pipefail
export LC_ALL=C

DIED_MID_WORK_HOURS=24   # hardcoded visible threshold: an open session card idle longer than this many hours is died-mid-work

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HLOG="$SCRIPT_DIR/handoff-log.sh"
US=$'\037'                # unit separator for internal streams: a non-whitespace IFS char keeps
                          # empty fields intact (cf. board-cards.sh, handoff-log.sh's META line)
NL='
'
NOW_EP="$(date -u +%s)"

usage() {
  echo "usage: take-stock.sh <repo-root> [--cards]" >&2
  exit 2
}

MODE=report
case $# in
  1) ;;
  2) [ "$2" = --cards ] || usage
     MODE=cards ;;
  *) usage ;;
esac
[ -d "$1" ] || { echo "take-stock: cannot read repo root '$1'" >&2; exit 2; }
ROOT="$(cd "$1" 2>/dev/null && pwd)" || { echo "take-stock: cannot read repo root '$1'" >&2; exit 2; }

shopt -s nullglob

# fm <file> <key>: the repo's existing frontmatter reader shape (cf. lifecycle-lint.sh), so a
# key written as "closed: " with a trailing space reads as empty
fm() { grep -E "^$2:" "$1" | head -1 | sed -E "s/^$2:[[:space:]]*//; s/[[:space:]]*$//"; }

clean() { printf '%s' "$1" | tr '\t\n' '  '; }   # free text can never split an emitted row

to_epoch() {   # ISO-8601 UTC ts -> epoch seconds; BSD date first, GNU fallback (cf. board-cards.sh)
  date -u -j -f '%Y-%m-%dT%H:%M:%SZ' "$1" +%s 2>/dev/null || date -u -d "$1" +%s 2>/dev/null || :
}

is_date() { case "$1" in [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) return 0 ;; *) return 1 ;; esac; }

row() { printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" "$6" "$7"; }

usrow() { local IFS="$US"; printf '%s\n' "$*"; }

# --- session cards: one US-separated stream, sorted by session timestamp then filename, so the
# last line is always the newest card and same-second cards resolve by name ---
gather_sessions() {
  local f base sts status closed token title nxt lastts
  for f in "$ROOT"/docs/sessions/*.md; do
    base="${f##*/}"
    sts="$(clean "$(fm "$f" session)")"
    status="$(clean "$(fm "$f" status)")"
    closed="$(clean "$(fm "$f" closed)")"
    token="$(clean "$(fm "$f" token)")"
    title="$(clean "$(fm "$f" title)")"
    nxt="$(clean "$(fm "$f" next)")"
    if [ -n "$closed" ]; then
      lastts="$closed"
    else
      # last activity: the timestamp of the newest ## Log line, else the session timestamp
      lastts="$(awk '
        /^## / { inlog = ($0 == "## Log"); next }
        inlog && /^- [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z/ { ts = substr($0, 3, 20) }
        END { print ts }
      ' "$f")"
      [ -n "$lastts" ] || lastts="$sts"
    fi
    usrow "$sts" "$base" "$status" "$token" "$title" "$lastts" "$nxt" "$closed"
  done
}
SESSDATA="$(gather_sessions | sort)"

SESSROWS=""; recorded=""; newest_nxt=""; open_ref=""; closed_ref=""; closed_status=""
while IFS="$US" read -r sts base status token title lastts nxt closed; do
  [ -n "$base" ] || continue
  ld="${lastts:0:10}"
  if is_date "$ld" && { [ -z "$recorded" ] || [[ "$ld" > "$recorded" ]]; }; then recorded="$ld"; fi
  newest_nxt="$nxt"                                  # sorted stream: the last write is the newest card
  marker=""
  if [ "$status" = open ] && [ -n "$lastts" ]; then
    e="$(to_epoch "$lastts")"
    if [ -n "$e" ] && [ $(( (NOW_EP - e) / 3600 )) -gt "$DIED_MID_WORK_HOURS" ]; then
      marker=died-mid-work
    fi
  fi
  case "$status" in
    open)                          open_ref="docs/sessions/$base" ;;
    done|blocked|handed-off|parked|aborted)
                                   closed_ref="docs/sessions/$base"; closed_status="$status" ;;
  esac
  SESSROWS="${SESSROWS}$(row session "docs/sessions/$base" "$status" "$token" "$title" "$ld" "$marker")$NL"
done <<< "$SESSDATA"

# --- handoffs: live ones only, sorted by filename, so the last is the newest by date with the
# lexically last name breaking a same-date tie ---
gather_live() {
  local f st
  for f in "$ROOT"/docs/handoffs/*.md; do
    st="$("$HLOG" state "$f" 2>/dev/null)"
    [ "$st" = live ] || continue
    printf '%s\n' "${f##*/}"
  done
}
HOFFS="$(gather_live | sort)"

auth=""; hcount=0; HOFFROWS=""
while IFS= read -r base; do
  [ -n "$base" ] || continue
  hcount=$((hcount + 1))
  auth="$base"
  hd="${base:0:10}"
  if is_date "$hd"; then
    if [ -z "$recorded" ] || [[ "$hd" > "$recorded" ]]; then recorded="$hd"; fi
  else
    hd=""
  fi
  htoken="$(printf '%s' "$base" | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}\.([^.]*)\..*$/\1/')"
  case "$htoken" in [BIRW][0-9]*) ;; *) htoken="" ;; esac
  htitle="$(clean "$(grep -m1 -E '^# ' "$ROOT/docs/handoffs/$base" | sed -E 's/^#[[:space:]]*//')")"
  HOFFROWS="${HOFFROWS}$(row handoff "docs/handoffs/$base" live "$htoken" "$htitle" "$hd" "")$NL"
done <<< "$HOFFS"

# --- git: the newest commit's date read in UTC explicitly, so a local commit day is never
# compared against a UTC recorded day ---
cdate="$(TZ=UTC git -C "$ROOT" log -1 --date=format-local:'%Y-%m-%d' --pretty=%cd 2>/dev/null)"
csubj="$(clean "$(git -C "$ROOT" log -1 --pretty=%s 2>/dev/null)")"

stale=""
if [ -n "$recorded" ] && [ -n "$cdate" ] && [[ "$cdate" > "$recorded" ]]; then
  stale=went-stale
fi

# next step: the newest session card's next line, else the authoritative handoff's first action
nstep="$newest_nxt"
if [ -z "$nstep" ] && [ -n "$auth" ]; then
  nstep="$(clean "$("$HLOG" actions "$ROOT/docs/handoffs/$auth" 2>/dev/null | head -1 | cut -f2)")"
fi
[ -n "$nstep" ] || nstep="none recorded"

if [ "$MODE" = cards ]; then
  row repo "" "" "" "$(clean "${ROOT##*/}")" "$recorded" "$stale"
  printf '%s' "$SESSROWS"
  printf '%s' "$HOFFROWS"
  exit 0
fi

if [ -n "$auth" ]; then
  echo "authoritative handoff: docs/handoffs/$auth"
else
  echo "authoritative handoff: none"
fi
echo "live handoffs: $hcount"
if [ -n "$open_ref" ]; then
  echo "open session card: $open_ref"
else
  echo "open session card: none open"
fi
if [ -n "$closed_ref" ]; then
  echo "newest closed session card: $closed_ref ($closed_status)"
else
  echo "newest closed session card: none closed"
fi
if [ -n "$cdate" ]; then
  echo "newest commit: $cdate $csubj"
else
  echo "newest commit: none"
fi
if [ -n "$stale" ]; then
  echo "went-stale: yes (newest commit $cdate is later than recorded state $recorded)"
elif [ -z "$cdate" ]; then
  echo "went-stale: no (no commits)"
elif [ -z "$recorded" ]; then
  echo "went-stale: no (no recorded state to be stale against)"
else
  echo "went-stale: no (newest commit $cdate, recorded state $recorded)"
fi
echo "next step: $nstep"
exit 0
