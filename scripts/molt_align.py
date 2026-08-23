#!/usr/bin/env python3
"""Cross-version corpus alignment and stock-drift detection (W10 task 2).

Seams 1 and 2 of the drift brief merged into one module: stock-drift is a
sha-set comparison over the alignment's own data, so a separate module would
only re-import this output to call `!=`.

Stock content keys are sha256 over the file bytes EXACTLY AS WRITTEN; normalize
is deliberately never applied here. Corpus files were written as
normalize(reconstruct(record)), so file-byte sha equals content_sha by
construction, and normalize is not idempotent (it unescapes \\$ on every pass),
so a second pass over the 5 committed \\$-bearing files would silently break
that equality.
"""
import hashlib, re
from collections import namedtuple
from pathlib import Path

# Anchored collision suffix only; never split('__')[0] - ids such as
# computer_batch legitimately contain single underscores.
COLLISION_SUFFIX = re.compile(r'__[0-9a-f]{8}$')

Alignment = namedtuple('Alignment', 'remaps orphans_old new_only')

def load_corpus(corpus_dir):
    """Return (shas_by_id, text_by_sha) for every *.md under corpus_dir.

    shas_by_id[id] is the set of content shas (collisions hold >1 element);
    text_by_sha[sha] is the file text. Iterates sorted() so any caller-visible
    ordering is deterministic.
    """
    shas_by_id, text_by_sha = {}, {}
    for f in sorted(Path(corpus_dir).glob('*.md')):
        content = f.read_bytes()                    # bytes as written, no normalize pass
        sha = hashlib.sha256(content).hexdigest()
        pid = COLLISION_SUFFIX.sub('', f.stem)
        shas_by_id.setdefault(pid, set()).add(sha)
        text_by_sha[sha] = content.decode('utf-8')
    return shas_by_id, text_by_sha

def build_alignment(old_shas, new_shas):
    """Align old ids to new ids by id first, then by a unique-content bridge.

    An old id remaps only when absent from new_shas by id AND every one of its
    shas bridges to the SAME single new id. A sha under two new ids is
    ambiguous and never bridges. Conservative reading on partial bridges: an
    old id whose shas do not ALL bridge (some sha absent from new, or
    ambiguous) does not remap - half-bridged evidence stays an orphan for eyes
    rather than producing an arbitrary remap.
    """
    holders = {}                                    # sha -> [new ids carrying it]
    for nid in sorted(new_shas):
        for sha in sorted(new_shas[nid]):
            holders.setdefault(sha, []).append(nid)
    bridge = {sha: nids[0] for sha, nids in holders.items() if len(nids) == 1}

    remaps = {}
    for oid in sorted(old_shas):
        if oid in new_shas:
            continue                                # id join wins; no remap needed
        targets = {bridge.get(s) for s in old_shas[oid]}
        if len(targets) == 1 and None not in targets:
            remaps[oid] = targets.pop()
    orphans_old = {oid for oid in old_shas
                   if oid not in new_shas and oid not in remaps}
    remap_targets = set(remaps.values())
    new_only = {nid for nid in new_shas
                if nid not in old_shas and nid not in remap_targets}
    return Alignment(remaps, orphans_old, new_only)

def resolved_new_id(align, id):
    """The id to read new stock under, following a segmentation remap."""
    return align.remaps.get(id, id)

def underlay_changed(old_shas, new_shas, align, id):
    """True when the sha set moved between old id and its resolved new id."""
    return old_shas.get(id, set()) != new_shas.get(resolved_new_id(align, id), set())

def selftest():
    # id-join, a segmentation remap, a true orphan, and a collision.
    old = {"same": {"a"}, "moved": {"b"}, "gone": {"c"}, "coll": {"d", "e"}}
    new = {"same": {"a"}, "renamed": {"b"}, "coll": {"d", "e"}, "brandnew": {"f"}}
    al = build_alignment(old, new)
    assert al.remaps == {"moved": "renamed"}, al.remaps          # content bridge by sha b
    assert al.orphans_old == {"gone"}, al.orphans_old            # no id, no content match
    assert al.new_only == {"brandnew"}, al.new_only              # new id, no old counterpart
    assert resolved_new_id(al, "moved") == "renamed"
    assert underlay_changed(old, new, al, "same") is False       # sha sets equal
    assert underlay_changed(old, new, al, "moved") is False      # {b} == {b} across remap
    assert underlay_changed(old, new, al, "coll") is False       # {d,e} == {d,e}
    # ambiguous bridge (one sha under two new ids) does not remap.
    o2 = {"x": {"z"}}
    n2 = {"p": {"z"}, "q": {"z"}}
    al2 = build_alignment(o2, n2)
    assert al2.remaps == {}, al2.remaps
    assert al2.orphans_old == {"x"}, al2.orphans_old
    # split bridge (two shas of one old id bridge to different new ids) does not remap.
    o3 = {"y": {"s1", "s2"}}
    n3 = {"na": {"s1"}, "nb": {"s2"}}
    al3 = build_alignment(o3, n3)
    assert al3.remaps == {}, al3.remaps
    assert al3.orphans_old == {"y"}, al3.orphans_old
    # id-strip keeps single-underscore ids intact
    import re
    assert re.sub(r"__[0-9a-f]{8}$", "", "computer_batch") == "computer_batch"
    assert re.sub(r"__[0-9a-f]{8}$", "", "foo__a2677fc4") == "foo"
    print("molt_align selftest: ok")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    else:
        sys.exit("usage: molt_align.py --selftest")
