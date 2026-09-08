#!/usr/bin/env bash
# handoff-log - the handoff consumption transition log. Handoffs are append-only records: a
# disposition is a line appended to the handoff's own ## Transitions section, never a mutated
# status field, and "current state" is always derived from those lines (latest line per action
# wins). Subcommands:
#   actions <handoff>                                  one row per action: <n>\t<text>\t<disp|->
#   state <handoff>                                    live | consumed | consumed-unarchived
#   consume <handoff>                                  archive iff every action is dispositioned
#   disposition <handoff> <n|all> <executed|superseded> [note]
#                                                      append one line per action (all: 1..N, or the
#                                                      action 0 bulk line on a zero-action file);
#                                                      auto-archive when the disposition completes
#                                                      the set, verbose-announced (archive rule 5)
# The actions section is any "## " heading whose text starts with "Next actions" (prefix match);
# enumerable actions are its "- " and "<n>. " lines, numbered 1..N by position; only the first
# such section enumerates. Exit codes: 2 usage / unknown file / no docs/handoffs segment, 4 bad
# disposition vocabulary or action number, 5 consume refused, 6 archive move failed.
set -uo pipefail
export LC_ALL=C

usage() {
  echo "usage: handoff-log.sh actions <handoff>" >&2
  echo "       handoff-log.sh state <handoff>" >&2
  echo "       handoff-log.sh consume <handoff>" >&2
  echo "       handoff-log.sh disposition <handoff> <n|all> <executed|superseded> [note]" >&2
  exit 2
}

# parse <file>: one awk pass over both sections. Stdout gets one row per action
# (n\ttext\t<disposition or ->) plus a final META<n>\tN\tcomplete\tmissing trailer, so the shell
# learns N, the completion flag, and the undispositioned count without a second scan.
parse() {
  local out trailer
  out="$(awk '
    /^## / {
      if ($0 ~ /^## Next actions/) { if (seen) inact = 0; else { inact = 1; seen = 1 } }
      else inact = 0
      intr = ($0 ~ /^## Transitions/)
      next
    }
    # transition line shape: - <ISO-8601 UTC> action <n> <executed|superseded> - <note>;
    # anything else in the section is hand-written prose and never counts as a disposition
    intr && $1 == "-" && $3 == "action" && ($5 == "executed" || $5 == "superseded") {
      if ($4 == "0") bulk = 1; else disp[$4] = $5   # action 0: the zero-action bulk stand-in
      next
    }
    inact && /^- /        { t = $0; sub(/^- /, "", t);         add(t) }
    inact && /^[0-9]+\. / { t = $0; sub(/^[0-9]+\. /, "", t);  add(t) }
    function add(t) { n++; gsub(/[\t\r]/, " ", t); txt[n] = t }
    END {
      missing = 0
      for (i = 1; i <= n; i++) {
        print i "\t" txt[i] "\t" ((i in disp) ? disp[i] : "-")
        if (!(i in disp)) missing++
      }
      complete = (n > 0 && missing == 0) || (n == 0 && bulk)
      printf "META\t%d\t%d\t%d\n", n, complete, missing   # %d, never empty fields: an empty
    }                                                    # field would collapse under IFS-tab read
  ' "$1")"
  trailer="$(printf '%s\n' "$out" | tail -n 1)"
  ROWS="$(printf '%s\n' "$out" | sed '$d')"
  [[ "$trailer" == META$'\t'* ]] || { echo "handoff-log: parse failed for '$1'" >&2; exit 6; }
  local m_n m_c m_m
  IFS=$'\t' read -r _ m_n m_c m_m <<< "$trailer"
  N="$m_n"; COMPLETE="$m_c"; MISSING="$m_m"
}

# archive_and_announce <path-as-given>: move the handoff into docs/archive/ inside the same
# repo, never overwriting (a collision takes a -2 suffix before .md, then -3, ...), and print
# the rule-5 announcement with the source path exactly as given, never relativized.
archive_and_announce() {
  local src="$1" tail_part dest dbase i sdir sbase abs_src abs_dest
  case "$src" in
    *docs/handoffs/*) ;;
    *) echo "handoff-log: no docs/handoffs/ segment in '$src' - cannot archive" >&2; exit 2 ;;
  esac
  # first-occurrence segment swap, so /any/repo/docs/handoffs/x.md -> /any/repo/docs/archive/x.md
  tail_part="${src#*docs/handoffs/}"
  dest="${src%docs/handoffs/"$tail_part"}docs/archive/${tail_part}"
  if [ -e "$dest" ]; then
    dbase="${dest%.md}"; i=2
    while [ -e "$dbase-$i.md" ]; do i=$((i+1)); done
    dest="$dbase-$i.md"
  fi
  mkdir -p "${dest%/*}"
  # git mv when tracked (staged rename, cf. setup.sh's archive_offer), plain mv otherwise; the
  # tracked-check runs from the file's own directory so any cwd and any path shape both work
  sdir="${src%/*}"; sbase="${src##*/}"
  abs_src="$(cd "$sdir" && pwd)/$sbase"
  abs_dest="$(cd "${dest%/*}" && pwd)/${dest##*/}"
  if git -C "$sdir" ls-files --error-unmatch "$sbase" >/dev/null 2>&1; then
    git -C "$sdir" mv "$abs_src" "$abs_dest" >/dev/null 2>&1 || mv "$src" "$dest"
  else
    mv "$src" "$dest"
  fi
  [ -e "$abs_dest" ] || { echo "handoff-log: archive move failed for $src" >&2; exit 6; }
  printf 'moved %s to %s\n' "$src" "$dest"
}

# ensure_transitions <file>: the section is created at end of file on first disposition and is
# the only section this script ever writes.
ensure_transitions() {
  grep -q '^## Transitions$' "$1" && return 0
  [ -n "$(tail -c 1 "$1")" ] && printf '\n' >> "$1"   # file lacked a trailing newline
  printf '\n## Transitions\n\n' >> "$1"
}

# append_transition <n> <disp> <note> <ts>: one line; re-dispositioning appends, never edits.
append_transition() {
  local line="- $4 action $1 $2"
  [ -n "$3" ] && line="$line - $3"
  printf '%s\n' "$line" >> "$FILE"
}

FILE=""
case "${1:-}" in
  actions|state|consume)
    [ $# -eq 2 ] || usage
    FILE="$2"
    ;;
  disposition)
    [ $# -ge 4 ] && [ $# -le 5 ] || usage
    FILE="$2"; NUM="$3"; DISP="$4"; NOTE="${5:-}"
    ;;
  *) usage ;;
esac
[ -f "$FILE" ] || { echo "handoff-log: no such handoff: '$FILE'" >&2; exit 2; }

case "$1" in
  actions)
    parse "$FILE"
    [ -n "$ROWS" ] && printf '%s\n' "$ROWS"
    ;;
  state)
    parse "$FILE"
    if [ "$COMPLETE" = 1 ]; then
      case "$FILE" in *docs/archive/*) echo consumed ;; *) echo consumed-unarchived ;; esac
    else
      echo live
    fi
    ;;
  consume)
    parse "$FILE"
    if [ "$N" -eq 0 ]; then
      echo "handoff-log: cannot consume $FILE: 0 enumerable action(s) - a zero-action file consumes only via 'disposition all'" >&2
      exit 5
    fi
    if [ "$COMPLETE" != 1 ]; then
      echo "handoff-log: cannot consume $FILE: $MISSING action(s) have no disposition" >&2
      exit 5
    fi
    archive_and_announce "$FILE"
    ;;
  disposition)
    case "$DISP" in
      executed|superseded) ;;
      *) echo "handoff-log: disposition must be executed or superseded, got '$DISP'" >&2; exit 4 ;;
    esac
    parse "$FILE"
    case "$NUM" in
      all) ;;
      ''|*[!0-9]*)
        echo "handoff-log: action number must be 1..$N or 'all', got '$NUM'" >&2; exit 4 ;;
      *)
        if ! { [ "$NUM" -ge 1 ] && [ "$NUM" -le "$N" ]; }; then
          echo "handoff-log: action number must be 1..$N or 'all', got '$NUM'" >&2; exit 4
        fi
        ;;
    esac
    # one format string on both BSD and GNU date - no -r/-d arithmetic, so no fallback needed
    TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    NOTE="$(printf '%s' "$NOTE" | tr '\t\n' '  ')"   # a transition line is always one line
    ensure_transitions "$FILE"
    if [ "$NUM" = all ]; then
      if [ "$N" -gt 0 ]; then
        i=1
        while [ "$i" -le "$N" ]; do append_transition "$i" "$DISP" "$NOTE" "$TS"; i=$((i+1)); done
      else
        append_transition 0 "$DISP" "$NOTE" "$TS"
      fi
    else
      append_transition "$NUM" "$DISP" "$NOTE" "$TS"
    fi
    parse "$FILE"                       # re-derive: did that disposition complete the set?
    [ "$COMPLETE" = 1 ] && archive_and_announce "$FILE"
    ;;
esac
exit 0   # a short-circuited && tail (empty actions, non-completing disposition) still exits 0
