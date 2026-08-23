#!/usr/bin/env python3
"""Flag assistant completion claims lacking a real executed check.

A claim is a match of a fixed phrase in an assistant text block. A claim is
backed iff the same assistant turn also issues a Bash tool_use whose
tool_result appears in the immediately following type=="user" record.
Emits JSON: claims, unmatched_claims.
"""
import json, sys

CLAIM_PHRASES = (
    'done',
    'fixed',
    'passing',
    'tests pass',
    'verified',
    'complete',
    'works now',
    'all set',
)

def first_claim(text):
    """First claim phrase matched, case-insensitive, else None."""
    low = text.lower()
    for p in CLAIM_PHRASES:
        if p in low:
            return p
    return None

def scan_completion(records):
    claims = []
    turn = 0
    for i, rec in enumerate(records):
        if rec.get('type') != 'assistant':
            continue
        turn += 1
        blocks = (rec.get('message') or {}).get('content') or []
        text = '\n'.join(b.get('text') or '' for b in blocks
                         if isinstance(b, dict) and b.get('type') == 'text')
        claim = first_claim(text)
        if claim is None:
            continue
        backed = False
        # "the following type=='user' record" read as immediate adjacency:
        # in real streams a tool_use record is sometimes followed by another
        # assistant record before the tool_result user record arrives, and a
        # claim is never retroactively backed by a later turn, so those count
        # as unbacked. Conservative for a flagging instrument.
        if any(isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') == 'Bash'
               for b in blocks):
            nxt = records[i + 1] if i + 1 < len(records) else None
            if nxt is not None and nxt.get('type') == 'user':
                nb = (nxt.get('message') or {}).get('content')
                backed = isinstance(nb, list) and any(
                    isinstance(b, dict) and b.get('type') == 'tool_result' for b in nb)
        claims.append({'turn': turn, 'claim': claim, 'backed': backed})
    return {'claims': claims,
            'unmatched_claims': sum(1 for c in claims if not c['backed'])}

def selftest():
    recs = [
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "All fixed and tests pass."}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Verified, it is complete."},
            {"type": "tool_use", "name": "Read"}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "..."}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "It works now."}, {"type": "tool_use", "name": "Bash"}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "PASS"}]}},
    ]
    d = scan_completion(recs)
    assert d["unmatched_claims"] == 2, d
    claims = {c["turn"]: c["backed"] for c in d["claims"]}
    assert claims[1] is False and claims[2] is False and claims[3] is True, d
    print("selftest: ok")

def main():
    if len(sys.argv) == 2 and sys.argv[1] == '--selftest':
        selftest(); return
    if len(sys.argv) != 2:
        sys.exit('usage: pilot-completion-scan.py <session.jsonl>|--selftest')
    records = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
    print(json.dumps(scan_completion(records), indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
