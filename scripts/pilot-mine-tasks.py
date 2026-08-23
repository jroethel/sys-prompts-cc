#!/usr/bin/env python3
"""Mine candidate replay tasks from Claude Code session transcripts.

Scans ~/.claude/projects/<project>/<session-id>.jsonl records and emits one
JSON candidate per session (see README in pilot/tasks for the curation step
that consumes this). Zero spend: reads local files only, no model calls.

Text is read ONLY from .message.content[] blocks of type "text": human turns
from records with .type=="user", assistant counting from .type=="assistant".
Never scans user or tool_result content for assistant text (quoted material
would produce false hits).
"""
import glob
import json
import os
import socket
import sys
from pathlib import Path


def selftest():
    U = lambda t: {"type": "user", "message": {"content": [{"type": "text", "text": t}]}}
    A = lambda t: {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}
    sessions = {
        "s-quick": [U("<command-name>/x</command-name>"), U("fix the typo"), A("done")],
        "s-multi": [U("build X"), A("."), U("now add Y")] + [A(".")] * 5,
        "s-empty": [U("hi")],
    }
    out = {c["source_session"]: c for c in candidates(sessions, "rit-wsl")}
    assert out["s-quick"]["prompt_text"] == "fix the typo", out
    assert out["s-quick"]["stratum"] == "quick" and out["s-quick"]["turns"] == 1, out
    assert out["s-multi"]["stratum"] == "multi" and out["s-multi"]["turns"] == 6, out
    assert out["s-multi"]["human_turns"] == ["build X", "now add Y"], out
    assert out["s-quick"]["host"] == "rit-wsl", out
    assert "s-empty" not in out, out
    red = {c["source_session"]: c for c in candidates(sessions, "rit-wsl", redact=True)}
    assert "prompt_text" not in red["s-quick"] and "human_turns" not in red["s-quick"], red
    print("selftest: ok")


def _is_wrapper(text: str) -> bool:
    return text.startswith("<") or text.startswith("Caveat:")


def _human_texts(rec: dict) -> list:
    msg = rec.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):                 # typed human input arrives as a bare string
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


def candidates(sessions: dict, host: str, redact: bool = False) -> list:
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
        cand = {
            "source_session": name,
            "prompt_text": human_turns[0],
            "human_turns": human_turns,
            "turns": turns,
            "stratum": "quick" if turns <= 5 else "multi",
            "host": host,
        }
        if redact:                               # --no-text: shape counts only, safe to ship cross-host
            cand = {
                "source_session": name,
                "turns": turns,
                "stratum": cand["stratum"],
                "host": host,
            }
        out.append(cand)
    return out


USAGE_KEYS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


def _load_session(path) -> list:
    records = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:    # fail loud, never silently miscount
                sys.exit(f"{path}:{n}: bad JSON: {e}")
            if isinstance(rec, dict) and rec.get("type") == "assistant":
                usage = (rec.get("message") or {}).get("usage")
                if not isinstance(usage, dict):
                    sys.exit(f"{path}:{n}: assistant record missing .message.usage")
                missing = [k for k in USAGE_KEYS if k not in usage]
                if missing:
                    sys.exit(
                        f"{path}:{n}: assistant record usage missing {', '.join(missing)}"
                    )
            records.append(rec)
    return records


def main():
    argv = sys.argv[1:]
    if argv == ["--selftest"]:
        selftest()
        return
    usage = (
        "usage: pilot-mine-tasks.py <jsonl-glob-or-dir> [--host <label>] [--no-text]"
        " |--selftest"
    )
    host, redact, path = socket.gethostname(), False, None
    i = 0
    while i < len(argv):
        if argv[i] == "--host" and i + 1 < len(argv):
            host = argv[i + 1]
            i += 2
        elif argv[i] == "--no-text":
            redact = True
            i += 1
        elif path is None:
            path = argv[i]
            i += 1
        else:
            sys.exit(usage)
    if path is None:
        sys.exit(usage)
    p = Path(os.path.expanduser(path))
    if p.is_dir():
        # Session transcripts live at <project>/<session-id>.jsonl. Depth 1
        # covers a project dir, depth 2 covers the projects root. Deeper files
        # are <session-id>/subagents/ fragments: not sessions, and their
        # assistant records carry degenerate usage (no cache keys), so they
        # are excluded here rather than relaxing the fail-loud usage gate.
        files = sorted(p.glob("*.jsonl")) + sorted(p.glob("*/*.jsonl"))
    else:
        files = sorted(Path(g) for g in glob.glob(os.path.expanduser(path)))
    for f in files:                              # one session at a time: candidates() per file bounds memory
        for cand in candidates({f.stem: _load_session(f)}, host, redact):
            print(json.dumps(cand))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:                      # `| head` closes the pipe; not an error
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
