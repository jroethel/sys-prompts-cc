#!/usr/bin/env python3
"""Blind a stock/variant transcript pair into anonymized A/B reading copies.

Renders each session JSONL to plain text (assistant text blocks plus one
[tool: <name>] marker per tool_use, in order), strips pack-identifying
strings, and writes A.txt, B.txt, and key.sealed.json under the out dir.
"""
import json, re, sys, hashlib, argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SAFE_ID = re.compile(r'^[A-Za-z0-9._-]+$')
CLAUDE_TOKEN = re.compile(r'claude-[A-Za-z0-9._-]+')

def render(records) -> str:
    lines = []
    for i, rec in enumerate(records):
        if rec.get('type') != 'assistant':
            continue
        content = rec.get('message', {}).get('content')
        if isinstance(content, str):            # some transcripts use a bare string
            content = [{'type': 'text', 'text': content}]
        for block in content or []:
            btype = block.get('type')
            if btype == 'text':
                lines.append(block.get('text', ''))
            elif btype == 'tool_use':
                lines.append(f"[tool: {block.get('name')}]")
            # other block types (image, thinking, ...) are not reading text: skipped
    return '\n'.join(lines)

def strip(text: str, patterns) -> str:
    # claude-* -> MODEL first so a pattern naming the full tell (e.g.
    # lobotomized-claude-code) never survives via the bare prefix entry alone.
    text = CLAUDE_TOKEN.sub('MODEL', text)
    for p in patterns:
        if p:
            text = re.sub(re.escape(p), '', text, flags=re.IGNORECASE)
    return text

def assign(seed: int, task_id: str) -> dict:
    h = int(hashlib.sha256(f"{seed}:{task_id}".encode('utf-8')).hexdigest(), 16) % 2
    return {'A': 'variant', 'B': 'stock'} if h else {'A': 'stock', 'B': 'variant'}

def load_strip_file(path: Path) -> list:
    pats = []
    for ln, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        pats.append(line)
    return pats

def load_jsonl(path) -> list:
    records = []
    for i, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines()):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            sys.exit(f'{path}: bad JSON on line {i + 1}: {e}')
    return records

def selftest():
    stock = [{"type": "assistant", "message": {"content": [
        {"type": "text", "text": "run at /tmp/x-stock-cfg/settings.json model claude-opus-4-8"},
        {"type": "tool_use", "name": "Bash"}]}}]
    patterns = ["lobotomized", "/tmp/x-stock-cfg"]
    r = render(stock)
    assert "[tool: Bash]" in r, r
    s = strip(r, patterns)
    assert "/tmp/x-stock-cfg" not in s and "claude-opus-4-8" not in s and "MODEL" in s, s
    assert assign(3, "t01") == assign(3, "t01"), "deterministic per pair"
    sides = {assign(3, f"t{i}")["A"] for i in range(12)}
    assert sides == {"stock", "variant"}, sides
    print("selftest: ok")

def main():
    if '--selftest' in sys.argv:
        selftest(); return
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stock')
    ap.add_argument('variant')
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--task-id', required=True)
    ap.add_argument('--out')
    ap.add_argument('--config-dir', action='append', default=[])
    args = ap.parse_args()
    assert SAFE_ID.match(args.task_id), f'unsafe task id: {args.task_id!r}'
    patterns = load_strip_file(REPO_ROOT / 'pilot' / 'blind-strip.txt') + args.config_dir
    out_dir = Path(args.out) if args.out else REPO_ROOT / 'pilot' / 'blind' / args.task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    sides = assign(args.seed, args.task_id)
    texts = {lbl: strip(render(load_jsonl(p)), patterns)
             for lbl, p in (('stock', args.stock), ('variant', args.variant))}
    (out_dir / 'A.txt').write_text(texts[sides['A']] + '\n', encoding='utf-8')
    (out_dir / 'B.txt').write_text(texts[sides['B']] + '\n', encoding='utf-8')
    key = {'A': sides['A'], 'B': sides['B'], 'seed': args.seed, 'task_id': args.task_id}
    (out_dir / 'key.sealed.json').write_text(json.dumps(key, indent=2) + '\n', encoding='utf-8')
    print(f'blind: {out_dir} (A={sides["A"]})')

if __name__ == '__main__':
    main()
