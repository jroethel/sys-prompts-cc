#!/usr/bin/env python3
"""Verdict engine: one verdict per applicable governed-pack override (W10 task 3).

Pure decision layer over Task 2's alignment: maps each pack override to exactly
one verdict from the fixed set {auto-realign, auto-realign-listed, carry-forward,
converged, auto-remap, review}. A pack id absent from both stocks is skipped
here; the caller logs it as a pack orphan, never a verdict.
"""
import hashlib
from collections import namedtuple

from molt_align import build_alignment, resolved_new_id, underlay_changed

Verdict = namedtuple('Verdict', 'id verdict override_type old_present new_present underlay_changed note')

def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def classify(pack_bodies, pins, old_shas, new_shas, align):
    verdicts = {}
    for pid in sorted(pack_bodies):
        body = pack_bodies[pid]
        nid = resolved_new_id(align, pid)
        old_set = old_shas.get(pid, set())
        new_set = new_shas.get(nid, set())
        old_present = bool(old_set)
        new_present = bool(new_set)
        if not old_present and not new_present:
            continue                                  # applies to neither install; caller logs it
        remapped = pid in align.remaps
        changed = underlay_changed(old_shas, new_shas, align, pid)
        is_supp = (body == "")
        ovr_sha = None if is_supp else _sha(body)
        is_mirror = (ovr_sha is not None and ovr_sha in old_set)
        converged = (ovr_sha is not None and ovr_sha in new_set)

        if is_supp:
            otype = "suppression"
            v = "carry-forward" if new_present else "review"      # rows 6, 7
            note = "target present in new stock" if new_present else "target absent after bridge; may resurrect"
        elif is_mirror:
            otype = "mirror"
            if not new_present:
                v, note = "review", "mirror orphan; underlay deleted in new stock"  # deleted upstream
            elif not changed:
                v, note = "auto-realign", "mirror of unchanged underlay"      # row 1
            elif converged:
                v, note = "auto-realign-listed", "mirror; override equals a surviving new variant"  # criterion-3 guard
            elif pid in pins:
                v, note = "review", "text-pinned mirror over changed underlay"  # row 2, pinned
            else:
                v, note = "auto-realign-listed", "mirror over changed underlay"  # row 2
        elif converged:
            otype = "rewrite"
            v, note = "converged", "upstream converged to override at new pin"   # row 4
        else:                                          # rewrite, not converged
            otype = "rewrite"
            if not new_present:
                v, note = "review", "rewrite orphan; id and content absent in new"  # row 8
            elif not changed:
                v, note = "carry-forward", "rewrite over unchanged underlay"        # row 3
            else:
                v, note = "review", "rewrite over changed underlay, differs from both"  # row 5
        if remapped and v in ("auto-realign", "carry-forward"):
            v, note = "auto-remap", "content found under new id " + nid            # row 9
        verdicts[pid] = Verdict(pid, v, otype, old_present, new_present, changed, note)
    return verdicts

def review_class(verdicts):
    return sorted((v for v in verdicts.values() if v.verdict == 'review'), key=lambda v: v.id)

def selftest():
    global _sha
    real = _sha
    _sha = lambda t: t                                          # bodies carry their own sha
    try:
        old = {"m1": {"OLD"}, "m2": {"OLD"}, "mo": {"OLD"}, "cm": {"OLD", "X"},
               "rw1": {"OLD"}, "rw2": {"OLD"}, "rw3": {"OLD"}, "conv": {"OLD"},
               "sp1": {"OLD"}, "sp2": {"OLD"}}
        new = {"m1": {"OLD"}, "m2": {"NEW"}, "cm": {"X"},
               "rw1": {"OLD"}, "rw2": {"NEW"}, "conv": {"OVRc"}, "sp1": {"NEW"}}
        # mo, rw3, sp2 absent in new; cm has intersecting-but-unequal sha sets
        align = build_alignment(old, new)
        bodies = {"m1": "OLD", "m2": "OLD", "mo": "OLD", "cm": "X",
                  "rw1": "RW", "rw2": "RW", "rw3": "RW", "conv": "OVRc",
                  "sp1": "", "sp2": ""}
        pins = {"m2", "cm"}                                     # cm pinned to prove the guard beats the pin
        v = classify(bodies, pins, old, new, align)
        assert v["m1"].verdict == "auto-realign", v["m1"]
        assert v["m2"].verdict == "review", v["m2"]             # text-pinned, underlay changed
        assert v["mo"].verdict == "review", v["mo"]             # mirror orphan (deleted upstream)
        assert v["cm"].verdict == "auto-realign-listed", v["cm"]  # converged guard beats pin (criterion 3)
        assert v["rw1"].verdict == "carry-forward", v["rw1"]
        assert v["rw2"].verdict == "review", v["rw2"]           # rewrite, changed, differs both
        assert v["rw3"].verdict == "review", v["rw3"]           # rewrite orphan
        assert v["conv"].verdict == "converged", v["conv"]      # override == new stock
        assert v["sp1"].verdict == "carry-forward", v["sp1"]    # suppression, target present
        assert v["sp2"].verdict == "review", v["sp2"]           # suppression, target absent
        # invariant: no review entry hash-equals new stock, incl. intersecting sha sets (criterion 3)
        for r in review_class(v):
            assert bodies[r.id] == "" or bodies[r.id] not in new.get(r.id, set()), r
        # exactly one verdict per applicable id, all from the fixed set
        allowed = {"auto-realign", "auto-realign-listed", "carry-forward",
                   "converged", "auto-remap", "review"}
        assert all(x.verdict in allowed for x in v.values())
    finally:
        _sha = real
    print("molt_verdict selftest: ok")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    else:
        sys.exit("usage: molt_verdict.py --selftest")
