#!/usr/bin/env python3
"""Held-up verdict for one pilot pass: joins the blind pairwise log with the
stock and variant metrics records on task_id and emits the gate JSON.

Zero-spend instrument: consumes Task-2 metrics records, never calls a model.
"""
import json, sys
from pathlib import Path

BEHAVIOR_FLOOR = 6
GUARD_METRICS = ("input_tokens", "output_tokens",
                 "cache_creation_input_tokens", "turns")
# cache_read_input_tokens is deliberately NOT guarded: more reuse is cheaper
# and better, not worse.
PAIRS_REQUIRED = 12
LOG_FIELDS = {"task_id": str, "order": str, "rating": str,
              "variant_won": (bool, type(None)), "reason": str, "rated_at": str}
LOG_ORDER = ("A=stock", "A=variant")
LOG_RATING = ("A", "B", "tie")


def median(xs: list) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        raise ValueError("median of empty list")
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


def verdict(pairwise: list, stock: list, variant: list) -> dict:
    def index(rows, label):
        out = {}
        for row in rows:
            tid = row["task_id"]
            if tid in out:
                raise ValueError(f"join error: task_id {tid} duplicated in {label}")
            out[tid] = row
        return out

    pw = index(pairwise, "pairwise")
    st = index(stock, "stock")
    va = index(variant, "variant")
    for tid in pw:
        if tid not in st:
            raise ValueError(f"join error: task_id {tid} missing from stock")
        if tid not in va:
            raise ValueError(f"join error: task_id {tid} missing from variant")
    for tid, label in [(t, "stock") for t in st] + [(t, "variant") for t in va]:
        if tid not in pw:
            raise ValueError(f"join error: task_id {tid} missing from pairwise "
                             f"(present only in {label})")

    wins = sum(1 for r in pairwise if r["variant_won"] is True)
    losses = sum(1 for r in pairwise if r["variant_won"] is False)
    ties = sum(1 for r in pairwise if r["variant_won"] is None)
    ratio = wins / losses if losses else None
    behavior = {"wins": wins, "losses": losses, "ties": ties, "ratio": ratio,
                "pass": wins >= 2 * losses and wins + losses >= BEHAVIOR_FLOOR}

    sw = median([st[t]["cache_write_turn1"] for t in pw])
    vw = median([va[t]["cache_write_turn1"] for t in pw])
    cache_write = {"stock_median": sw, "variant_median": vw,
                   "pass": vw < sw}

    breaches = []
    for met in GUARD_METRICS:
        sm = median([st[t][met] for t in pw])
        vm = median([va[t][met] for t in pw])
        if vm > 1.10 * sm:
            breaches.append({"metric": met, "stock_median": sm,
                             "variant_median": vm})
    guard = {"breaches": breaches, "pass": not breaches}

    both = [t for t in pw
            if st[t]["compaction_turn"] is not None
            and va[t]["compaction_turn"] is not None]
    n_both = len(both)
    if n_both < 4:
        status = "insufficient"
        smed = vmed = None
    else:
        smed = median([st[t]["compaction_turn"] for t in both])
        vmed = median([va[t]["compaction_turn"] for t in both])
        status = "variant_later" if vmed > smed else "not_later"
    compaction = {"n_both": n_both, "stock_median": smed,
                  "variant_median": vmed, "status": status}

    if not guard["pass"] or (wins + losses >= BEHAVIOR_FLOOR
                             and ratio is not None and ratio < 1.0):
        v = "not_held_up"
    elif behavior["pass"] and cache_write["pass"] and guard["pass"]:
        v = "held_up"
    else:
        v = "inconclusive"
    return {"behavior": behavior, "cache_write": cache_write, "guard": guard,
            "compaction": compaction, "verdict": v}


def load_jsonl(path) -> list:
    rows = []
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            sys.exit(f"{path}: bad JSON on line {i}: {e}")
    return rows


def validate_log(rows, path="<log>") -> str | None:
    """Return an error string for the first offending row, else None."""
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            return f"{path}: row {i}: not a JSON object"
        for f, ty in LOG_FIELDS.items():
            if f not in row:
                return f"{path}: row {i}: missing field {f}"
            if not isinstance(row[f], ty):
                return f"{path}: row {i}: field {f} has wrong type"
        if row["order"] not in LOG_ORDER:
            return f"{path}: row {i}: order must be one of {LOG_ORDER}"
        if row["rating"] not in LOG_RATING:
            return f"{path}: row {i}: rating must be one of {LOG_RATING}"
    if len(rows) != PAIRS_REQUIRED:
        return f"{path}: expected {PAIRS_REQUIRED} rows, found {len(rows)}"
    return None


def selftest():
    tids = [f"t{i}" for i in range(12)]
    def m(tid, cw, comp, out=100):
        return {"task_id": tid, "cache_write_turn1": cw, "compaction_turn": comp,
                "input_tokens": 100, "output_tokens": out, "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": cw, "turns": 10}
    pairwise = [{"task_id": t, "variant_won": w}
                for t, w in zip(tids, [True]*6 + [False]*2 + [None]*4)]
    stock =   [m(t, 2000, None) for t in tids]
    variant = [m(t, 1200, None) for t in tids]
    d = verdict(pairwise, stock, variant)
    assert d["behavior"]["pass"] and d["behavior"]["wins"] == 6 and d["behavior"]["losses"] == 2, d
    assert d["cache_write"]["pass"] and d["guard"]["pass"], d
    assert d["compaction"]["status"] == "insufficient", d
    assert d["verdict"] == "held_up", d
    v2 = [m(t, 1200, None, out=130) for t in tids]
    assert verdict(pairwise, stock, v2)["verdict"] == "not_held_up", "guard must veto"
    vcr = [dict(m(t, 1200, None), cache_read_input_tokens=100000) for t in tids]
    assert verdict(pairwise, stock, vcr)["guard"]["pass"], "cache-read is not guarded"
    thin = [{"task_id": t, "variant_won": w} for t, w in zip(tids, [True, False] + [None]*10)]
    assert verdict(thin, stock, variant)["verdict"] == "inconclusive", "small N is inconclusive"
    try:
        verdict(pairwise, stock[:-1] + [m("BADID", 1200, None)], variant); assert False
    except ValueError as e:
        assert "join error" in str(e), e
    print("selftest: ok")


def boundary_selftest():
    # Supplements the spec selftest with the boundary cases it leaves open:
    # the 2:1 gate, the behavior floor, strict cache-write inequality, the
    # reported ratio value, and the duplicate-id join error.
    tids = [f"t{i}" for i in range(12)]
    def m(tid, cw, comp=None, out=100):
        return {"task_id": tid, "cache_write_turn1": cw, "compaction_turn": comp,
                "input_tokens": 100, "output_tokens": out, "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": cw, "turns": 10}
    def pw(ws):
        return [{"task_id": t, "variant_won": w} for t, w in zip(tids, ws)]
    stock = [m(t, 2000) for t in tids]
    # 5:4 among non-ties: ratio 1.25 fails the 2:1 gate -> inconclusive
    d = verdict(pw([True]*5 + [False]*4 + [None]*3), stock, [m(t, 1200) for t in tids])
    assert not d["behavior"]["pass"] and d["verdict"] == "inconclusive", d
    # 4:1 wins but only 5 non-ties: below the floor -> inconclusive
    d = verdict(pw([True]*4 + [False] + [None]*7), stock, [m(t, 1200) for t in tids])
    assert not d["behavior"]["pass"] and d["verdict"] == "inconclusive", d
    # equal cache-write medians: pass requires strictly smaller -> inconclusive
    d = verdict(pw([True]*6 + [False]*2 + [None]*4), stock, [m(t, 2000) for t in tids])
    assert not d["cache_write"]["pass"] and d["verdict"] == "inconclusive", d
    # ratio is reported, not just pass/fail
    d = verdict(pw([True]*6 + [False]*2 + [None]*4), stock, [m(t, 1200) for t in tids])
    assert d["behavior"]["ratio"] == 3.0, d
    # duplicated task_id in the log fails the join loud
    try:
        verdict(pw([True]*12), stock, [m(t, 1200) for t in tids] + [m("t0", 1200)])
        assert False, "duplicate variant row should have raised"
    except ValueError as e:
        assert "join error" in str(e), e
    print("boundary: ok")


def main():
    args = sys.argv[1:]
    if args[:1] == ["--selftest"]:
        selftest()
        boundary_selftest()
        return
    if args[:1] == ["--validate-log"]:
        if len(args) != 2:
            sys.exit("usage: pilot-verdict.py --validate-log <pairwise.jsonl>")
        err = validate_log(load_jsonl(args[1]), args[1])
        if err:
            sys.exit(err)
        print(f"validate-log: ok ({PAIRS_REQUIRED} rows)")
        return
    if len(args) != 3:
        sys.exit("usage: pilot-verdict.py <pairwise.jsonl> <metrics-stock.jsonl> "
                 "<metrics-variant.jsonl> | --validate-log <pairwise.jsonl> | --selftest")
    json.dump(verdict(load_jsonl(args[0]), load_jsonl(args[1]),
                      load_jsonl(args[2])), sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
