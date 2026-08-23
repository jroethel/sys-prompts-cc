#!/usr/bin/env python3
"""Extract token/turn metrics from one Claude Code session JSONL.

Zero-spend pilot instrument: reads only what the transcript already records
in .message.usage; never calls a model.
"""
import json, sys
from pathlib import Path

TOKEN_KEYS = ("input_tokens", "output_tokens",
              "cache_read_input_tokens", "cache_creation_input_tokens")
CONTINUATION = "This session is being continued from a previous conversation"


def is_compaction(rec: dict) -> bool:
    """True iff rec is a user turn carrying the auto-compaction continuation
    preamble. Two real shapes on disk: message.content as a plain string (the
    genuine compacted continuation), or as a list whose first text block
    carries it. tool_result blocks and assistant records never match.
    Disk-checked: the JSONL carries no dedicated compaction field, so this
    preamble is the only real signal."""
    if rec.get("type") != "user":
        return False
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return CONTINUATION in content
    for b in content or []:
        if isinstance(b, dict) and b.get("type") == "text":
            return CONTINUATION in (b.get("text") or "")
    return False


def extract(records: list, task_id: str | None = None) -> dict:
    d = dict.fromkeys(TOKEN_KEYS, 0)
    d.update(task_id=task_id, turns=0, cache_write_turn1=0,
             compaction_turn=None, errors=0, output_chars=0)
    for rec in records:
        if is_compaction(rec) and d["compaction_turn"] is None:
            d["compaction_turn"] = d["turns"]
        rtype = rec.get("type")
        msg = rec.get("message") or {}
        blocks = msg.get("content") or []
        if not isinstance(blocks, list):
            blocks = []
        if rtype == "user":
            d["errors"] += sum(1 for b in blocks
                               if isinstance(b, dict) and b.get("type") == "tool_result"
                               and b.get("is_error") is True)
            continue
        if rtype != "assistant":
            continue
        usage = msg.get("usage")
        if not isinstance(usage, dict) or any(k not in usage for k in TOKEN_KEYS):
            raise ValueError(f"usage shape error at assistant turn {d['turns']}")
        for k in TOKEN_KEYS:
            d[k] += usage[k]
        if d["turns"] == 0:
            d["cache_write_turn1"] = usage["cache_creation_input_tokens"]
        d["output_chars"] += sum(len(b.get("text") or "")
                                 for b in blocks
                                 if isinstance(b, dict) and b.get("type") == "text")
        d["turns"] += 1
    d["output_chars_per_turn"] = d["output_chars"] / d["turns"] if d["turns"] else 0.0
    return d


def selftest():
    recs = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello"}],
         "usage": {"input_tokens": 100, "output_tokens": 5, "cache_read_input_tokens": 0,
                   "cache_creation_input_tokens": 2000}}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "boom",
                                                  "is_error": True}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "done now"}],
         "usage": {"input_tokens": 50, "output_tokens": 3, "cache_read_input_tokens": 1800,
                   "cache_creation_input_tokens": 40}}},
        {"type": "user", "message": {"content": [{"type": "text",
            "text": "This session is being continued from a previous conversation ..."}]}},
    ]
    d = extract(recs)
    assert d["turns"] == 2, d
    assert d["input_tokens"] == 150 and d["output_tokens"] == 8, d
    assert d["cache_creation_input_tokens"] == 2040 and d["cache_write_turn1"] == 2000, d
    assert d["output_chars"] == len("hello") + len("done now"), d
    assert d["compaction_turn"] == 2, d
    assert d["errors"] == 1, d
    assert d["task_id"] is None, d
    assert extract(recs, task_id="t03")["task_id"] == "t03", "task_id stamps for the verdict join"
    # plain-string user content: the real auto-compaction shape
    recs2 = recs[:3] + [{"type": "user", "message": {"content":
        "This session is being continued from a previous conversation ..."}}]
    assert extract(recs2)["compaction_turn"] == 2, "plain-string preamble counts"
    # quoted preamble inside a tool_result still does not count
    recs3 = recs[:3] + [{"type": "user", "message": {"content": [{"type": "tool_result",
        "content": "This session is being continued from a previous conversation ..."}]}}]
    assert extract(recs3)["compaction_turn"] is None, "quoted preamble in tool_result ignored"
    bad = [{"type": "assistant", "message": {"content": [], "usage": {"input_tokens": 1}}}]
    try:
        extract(bad); assert False, "should have raised"
    except ValueError as e:
        assert "usage shape error" in str(e), e
    print("selftest: ok")


def main():
    args = sys.argv[1:]
    task_id = None
    if "--task-id" in args:
        i = args.index("--task-id")
        task_id = args[i + 1]
        del args[i:i + 2]
    if args[:1] == ["--selftest"]:
        selftest()
        return
    if len(args) != 1:
        sys.exit("usage: pilot-metrics.py <session.jsonl> [--task-id <id>]|--selftest")
    records = []
    for line in Path(args[0]).read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    d = extract(records, task_id)
    d["session_id"] = Path(args[0]).stem
    json.dump(d, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
