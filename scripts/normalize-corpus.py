#!/usr/bin/env python3
"""Normalize a tweakcc prompts-<version>.json into one file per prompt id.

Sentinel $INTERP is brace-free so the ${...} collapse reaches a fixpoint even
for nested interpolations (a braced sentinel like ${} cannot re-match the outer
${...} and would leak residue into the diff as false content drift).
Escaping is undone BEFORE the collapse on purpose (ponytail: matches the
diff-surface.md recipe - a literal \\${x} in a piece reads as an interpolation).
"""
import json, re, sys, hashlib
from pathlib import Path

SENT = '$INTERP'
INTERP = re.compile(r'\$\{[^{}]*\}')
WS = re.compile(r'\s+')
SAFE_ID = re.compile(r'^[A-Za-z0-9._-]+$')

def normalize(s: str) -> str:
    s = s.replace('\\`', '`').replace('\\$', '$')
    prev = None
    while prev != s:                       # innermost-first to fixpoint, handles ${${0}}
        prev = s
        s = INTERP.sub(SENT, s)
    return WS.sub(' ', s).strip()

def reconstruct(rec: dict) -> str:
    pieces = [p if isinstance(p, str) else str(p) for p in (rec.get('pieces') or [])]
    idents = [str(i) for i in (rec.get('identifiers') or [])]
    out = []
    for i, p in enumerate(pieces):
        out.append(p)
        if i < len(idents):
            out.append('${' + idents[i] + '}')
    for j in range(len(pieces), len(idents)):   # never silently drop trailing identifiers
        out.append('${' + idents[j] + '}')
    return ''.join(out)

def content_sha(rec: dict) -> str:
    return hashlib.sha256(normalize(reconstruct(rec)).encode('utf-8')).hexdigest()

def selftest():
    rec = {'id': 't', 'pieces': ['a \\` b ', ' c'], 'identifiers': ['GREP_TOOL_NAME']}
    assert normalize(reconstruct(rec)) == 'a ` b $INTERP c', normalize(reconstruct(rec))
    assert normalize('x ${${0}} y') == 'x $INTERP y'
    assert normalize('${a ${0} b}') == '$INTERP'
    assert normalize('p   q\n r') == 'p q r'
    print('selftest: ok')

def main():
    if len(sys.argv) == 2 and sys.argv[1] == '--selftest':
        selftest(); return
    if len(sys.argv) != 3:
        sys.exit('usage: normalize-corpus.py <in-json>|--selftest <out-dir>')
    in_json, out_dir = sys.argv[1], Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob('*.md'):          # clean so re-runs are byte-identical
        f.unlink()
    data = json.loads(Path(in_json).read_text(encoding='utf-8'))
    prompts = data['prompts'] if isinstance(data, dict) else data
    by_id = {}                              # id -> {content_sha: normalized_text}
    for rec in prompts:
        pid = str(rec['id'])
        assert SAFE_ID.match(pid), f'unsafe id: {pid!r}'
        by_id.setdefault(pid, {})[content_sha(rec)] = normalize(reconstruct(rec))
    n = 0
    for pid, variants in by_id.items():
        if len(variants) == 1:              # unique content (incl. identical-copy dups): plain name
            (out_dir / f'{pid}.md').write_text(next(iter(variants.values())), encoding='utf-8')
            n += 1
        else:                               # id collision with distinct contents: content-suffix
            for sha, text in variants.items():
                (out_dir / f'{pid}__{sha[:8]}.md').write_text(text, encoding='utf-8')
                n += 1
    print(f'count: {n}')

if __name__ == '__main__':
    main()
