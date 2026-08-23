#!/usr/bin/env python3
"""Count stylistic tics and tool usage in a session transcript.

Scans assistant text blocks only (never user or tool_result content, where
quoted material produces false hits). Emits JSON: session_id, tic_counts,
tic_total, em_dash, section_symbol, permission_seeking, tool_calls,
tool_profile.
"""
import json, sys
from pathlib import Path

PHRASE_FILE = Path(__file__).resolve().parent.parent / 'pilot' / 'tic-phrases.txt'
PERMISSION_PHRASES = (
    'would you like me to',
    'do you want me to',
    'should i proceed',
    'shall i',
    'is it okay if i',
    'let me know if you want',
)

def load_phrases(path=PHRASE_FILE):
    return [ln.strip() for ln in path.read_text(encoding='utf-8').splitlines()
            if ln.strip() and not ln.strip().startswith('#')]

def assistant_text(rec):
    """Concatenated text blocks of one assistant record, '' otherwise."""
    if rec.get('type') != 'assistant':
        return ''
    out = []
    for b in (rec.get('message') or {}).get('content') or []:
        if isinstance(b, dict) and b.get('type') == 'text':
            out.append(b.get('text') or '')
    return '\n'.join(out)

def scan_tics(records, phrases):
    texts = [assistant_text(r) for r in records]
    joined = '\n'.join(texts).lower()
    tic_counts = {p: joined.count(p.lower()) for p in phrases}
    em_dash = joined.count(chr(0x2014))
    section_symbol = joined.count(chr(0xA7))
    permission_seeking = sum(joined.count(p) for p in PERMISSION_PHRASES)
    tool_profile = {}
    for rec in records:
        if rec.get('type') != 'assistant':
            continue
        for b in (rec.get('message') or {}).get('content') or []:
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                name = str(b.get('name'))
                tool_profile[name] = tool_profile.get(name, 0) + 1
    return {
        'tic_counts': tic_counts,
        'tic_total': sum(tic_counts.values()),
        'em_dash': em_dash,
        'section_symbol': section_symbol,
        'permission_seeking': permission_seeking,
        'tool_calls': sum(tool_profile.values()),
        'tool_profile': tool_profile,
    }

def selftest():
    phrases = ["load-bearing", "you're absolutely right"]
    recs = [
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "This is load-bearing - and load-bearing again — yes."},
            {"type": "tool_use", "name": "Bash", "input": {}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result",
            "content": "load-bearing in quoted output must NOT count"}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Would you like me to proceed?"},
            {"type": "tool_use", "name": "Read", "input": {}}]}},
    ]
    d = scan_tics(recs, phrases)
    assert d["tic_counts"]["load-bearing"] == 2, d
    assert d["em_dash"] == 1 and d["section_symbol"] == 0, d
    assert d["permission_seeking"] == 1, d
    assert d["tool_calls"] == 2 and d["tool_profile"] == {"Bash": 1, "Read": 1}, d
    print("selftest: ok")

USAGE_KEYS = ('input_tokens', 'cache_creation_input_tokens',
              'cache_read_input_tokens', 'output_tokens')

def load_records(path):
    records = []
    session_id = None
    for i, line in enumerate(open(path, encoding='utf-8')):
        if not line.strip():
            continue
        rec = json.loads(line)          # malformed JSON should fail loud with context
        records.append(rec)
        if session_id is None and rec.get('sessionId'):
            session_id = rec['sessionId']
        if rec.get('type') == 'assistant':
            usage = (rec.get('message') or {}).get('usage')
            if not isinstance(usage, dict) or any(k not in usage for k in USAGE_KEYS):
                sys.exit(f'malformed record {i}: assistant usage missing '
                         f'{[k for k in USAGE_KEYS if not usage or k not in usage]}')
    return session_id, records

def main():
    if len(sys.argv) == 2 and sys.argv[1] == '--selftest':
        selftest(); return
    if len(sys.argv) != 2:
        sys.exit('usage: pilot-tic-scan.py <session.jsonl>|--selftest')
    session_id, records = load_records(sys.argv[1])
    d = scan_tics(records, load_phrases())
    d = {'session_id': session_id, **d}
    print(json.dumps(d, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
