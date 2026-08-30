#!/usr/bin/env python3
"""Session triage: one compact summary line per session, for human skimming.

Separate from pilot-mine-tasks.py and its packet pipeline (pilot/tasks/README.md).
This is a browsing lens over session history: how many human turns, how long
it ran, whether it opened as a scripted role/handoff (loop-stack style), and a
rough correction/frustration count. Zero spend: reads local session jsonl only.
"""
import glob
import json
import os
import re
import socket
import sys
from datetime import datetime
from pathlib import Path

ROLE_PATTERN = re.compile(r"you are (?:an?|the)\s+([A-Za-z][A-Za-z0-9 /_-]{2,50})", re.IGNORECASE)
ROLE_MARKERS = {
    "WORKER RULES": "worker",
    "GLOBAL CONSTRAINTS": "constrained-worker",
}
FRUSTRATION_TERMS = [
    "no,", "not what", "that's not", "actually no", "wrong", "stop",
    "revert", "undo", "broken", "doesn't work", "still not", "ugh",
    "fuck", "stupid", "i told you", "why did you", "i never said",
    "still don't", "don't love", 
]
# Raw role captures fragment on trailing detail ("code-feature worker on the
# substack-scraper python" vs "code-feature worker"). Stop at the first of
# these to collapse variants of the same role into one bucket.
CANONICAL_STOPWORDS = {"on", "for", "in", "that", "who", "which", "written", "and", "the", "a", "an", "of", "with"}
CANONICAL_MAX_WORDS = 3


def selftest():
    U = lambda t, ts: {"type": "user", "timestamp": ts, "message": {"content": [{"type": "text", "text": t}]}}
    A = lambda ts: {"type": "assistant", "timestamp": ts, "message": {"content": [{"type": "text", "text": "ok"}]}}
    sessions = {
        "s-scripted": [
            U("You are a code reviewer. Review this diff.", "2026-01-01T00:00:00Z"),
            A("2026-01-01T00:00:05Z"),
        ],
        "s-scripted-variant": [
            U("You are a code reviewer for the payments module, be thorough.", "2026-01-01T00:00:00Z"),
            A("2026-01-01T00:00:05Z"),
        ],
        "s-frustrated": [
            U("build the login form", "2026-01-01T00:00:00Z"),
            A("2026-01-01T00:01:00Z"),
            U("no, that's wrong, use email not username", "2026-01-01T00:02:00Z"),
            A("2026-01-01T00:03:00Z"),
        ],
    }
    out = {r["source_session"]: r for r in triage(sessions, "host")}
    assert out["s-scripted"]["role"] == "code reviewer", out
    assert out["s-scripted"]["elapsed_min"] == 0.1, out
    assert out["s-frustrated"]["role"] == "", out
    assert out["s-frustrated"]["canonical_role"] == "", out
    assert out["s-frustrated"]["frustration_hits"] == 1, out
    assert out["s-frustrated"]["elapsed_min"] == 3.0, out
    assert out["s-scripted"]["canonical_role"] == "code reviewer", out
    assert out["s-scripted-variant"]["canonical_role"] == "code reviewer", out
    print("selftest: ok")


def _is_wrapper(text: str) -> bool:
    return text.startswith("<") or text.startswith("Caveat:")


def _human_texts(rec: dict) -> list:
    msg = rec.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        blocks = [{"type": "text", "text": content}]
    elif isinstance(content, list):
        blocks = content
    else:
        return []
    return [
        b.get("text") or ""
        for b in blocks
        if isinstance(b, dict) and b.get("type") == "text"
    ]


def _role(first_turn: str) -> str:
    m = ROLE_PATTERN.search(first_turn)
    if m:
        return m.group(1).split("\n")[0].strip(" .,:").lower()
    for marker, label in ROLE_MARKERS.items():
        if marker in first_turn:
            return label
    return ""


def _canonical_role(role: str) -> str:
    if not role:
        return ""
    out = []
    for word in role.split():
        if word in CANONICAL_STOPWORDS and out:
            break
        out.append(word)
        if len(out) >= CANONICAL_MAX_WORDS:
            break
    return " ".join(out)


def _elapsed_minutes(records: list) -> float:
    stamps = [
        datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
        for r in records
        if isinstance(r, dict) and r.get("timestamp")
    ]
    if len(stamps) < 2:
        return 0.0
    return round((max(stamps) - min(stamps)).total_seconds() / 60, 1)


def triage(sessions: dict, host: str, preview_len: int = 80, frustration_terms=None) -> list:
    terms = [t.lower() for t in (frustration_terms or FRUSTRATION_TERMS)]
    out = []
    for name, records in sessions.items():
        turns = sum(1 for r in records if isinstance(r, dict) and r.get("type") == "assistant")
        if turns == 0:
            continue
        human_turns = [
            t
            for r in records
            if isinstance(r, dict) and r.get("type") == "user"
            for t in _human_texts(r)
            if not _is_wrapper(t)
        ]
        if not human_turns:
            continue
        frustration = sum(1 for t in human_turns[1:] if any(term in t.lower() for term in terms))
        role = _role(human_turns[0])
        out.append({
            "source_session": name,
            "host": host,
            "turns": turns,
            "human_turn_count": len(human_turns),
            "elapsed_min": _elapsed_minutes(records),
            "role": role,
            "canonical_role": _canonical_role(role),
            "frustration_hits": frustration,
            "preview": human_turns[0][:preview_len],
        })
    return out


def main():
    argv = sys.argv[1:]
    if argv == ["--selftest"]:
        selftest()
        return
    usage = "usage: session-triage.py <jsonl-glob-or-dir> [--host <label>] [--preview-len N] |--selftest"
    host, path, preview_len = socket.gethostname(), None, 80
    i = 0
    while i < len(argv):
        if argv[i] == "--host" and i + 1 < len(argv):
            host = argv[i + 1]
            i += 2
        elif argv[i] == "--preview-len" and i + 1 < len(argv):
            preview_len = int(argv[i + 1])
            i += 2
        elif path is None:
            path = argv[i]
            i += 1
        else:
            sys.exit(usage)
    if path is None:
        sys.exit(usage)
    p = Path(os.path.expanduser(path))
    if p.is_dir():
        # Same depth rule as pilot-mine-tasks.py: depth 1-2 only, so nested
        # <session-id>/subagents/ fragments are excluded, not real sessions.
        files = sorted(p.glob("*.jsonl")) + sorted(p.glob("*/*.jsonl"))
    else:
        files = sorted(Path(g) for g in glob.glob(os.path.expanduser(path)))
    for f in files:
        records = []
        with open(f, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    sys.exit(f"{f}:{n}: bad JSON: {e}")
        for row in triage({f.stem: records}, host, preview_len):
            print(json.dumps(row))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
