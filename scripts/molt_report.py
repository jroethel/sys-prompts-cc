#!/usr/bin/env python3
"""Molt report renderer and review-issue emission (W10 task 4).

render(ctx) is a pure function of committed inputs: byte-identical output
across runs except the generated: header line (criterion 2). emit_issue is
the module's only side-effecting surface and is never exercised by the
self-test.
"""
import json
import os
import re
import subprocess

from molt_verdict import review_class

TRACKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.sh")


def _table(headers, rows):
    """Aligned pipe table (house style: padded cells, sorted rows by caller)."""
    widths = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    fmt = lambda r: "| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return "\n".join([fmt(headers), sep] + [fmt(r) for r in rows])


def _fence(body):
    """Fence for one prose block: ``` normally, or a tilde run at least four
    long and longer than any tilde run inside the body when the body itself
    contains a triple-backtick run (computed per block, criterion 2)."""
    if "```" not in body:
        return "```"
    n = 4
    for m in re.finditer(r"~+", body):
        n = max(n, len(m.group(0)) + 1)
    return "~" * n


def _variants(shas, text_by_sha):
    """Every variant body of one stock side in sorted sha order, labeled with
    its sha8 on collided ids; '(absent)' when that side has no variants."""
    if not shas:
        return "(absent)"
    parts = []
    for sha in sorted(shas):
        if len(shas) > 1:
            parts.append("--- (variant %s) ---" % sha[:8])
        parts.append(text_by_sha.get(sha, "(missing text for sha)"))
    return "\n".join(parts)


def _identity(prov):
    """Recorded extractor identity for one pin, or None when unrecorded
    (a missing key and an explicit null read identically; see task 7)."""
    if prov.get("extractor_cc_version"):
        return "cc %s" % prov["extractor_cc_version"]
    if prov.get("extractor_source"):
        return prov["extractor_source"]
    return None


def render(ctx):
    """Return the full eight-section molt report as markdown."""
    m = ctx["manifest"]
    align = ctx["align"]
    # The plan's ctx list omits the pack bodies, but the override prose block
    # needs them; this optional key is the exact load_pack output (id ->
    # normalized body). Most conservative reading without it: '(absent)'.
    pack_bodies = ctx.get("pack_bodies", {})
    S = []

    S.append("\n".join([
        "<!--",
        "generated: %s" % ctx["generated"],
        "pack: %s" % m["name"],
        "ref: %s" % m["ref"],
        "oldV: %s" % ctx["old_v"],
        "newV: %s" % ctx["new_v"],
        "DO NOT EDIT",
        "-->",
    ]))
    S.append("# Molt: %s %s to %s" % (m["name"], ctx["old_v"], ctx["new_v"]))

    # Provenance: record count (JSON records) vs file count (on-disk unique
    # ids) both shown so a reader reconciling them does not chase a non-bug.
    rows = []
    for v, prov, fc in ((ctx["old_v"], ctx["old_prov"], ctx["old_file_count"]),
                        (ctx["new_v"], ctx["new_prov"], ctx["new_file_count"])):
        ident = _identity(prov)
        rows.append([v, str(prov.get("rung", "-")),
                     ident if ident is not None else "(unrecorded)",
                     str(prov.get("prompt_count", "-")), str(fc)])
    oi, ni = _identity(ctx["old_prov"]), _identity(ctx["new_prov"])
    if oi is None and ni is None:
        drift = "unrecorded on both rungs"
    elif oi is None or ni is None:
        drift = "unrecorded on one rung (the other records %s)" % (oi or ni)
    elif oi != ni:
        drift = "they differ (%s vs %s)" % (oi, ni)
    else:
        drift = "equal (%s)" % oi
    prov = [
        "## Provenance",
        _table(["version", "rung", "extractor identity", "record count", "file count"], rows),
        "",
        "Extractor drift: %s." % drift,
    ]
    if oi is None and ni is None:
        # Emitted only when both are unrecorded: the pinned first-report note
        # is true exactly here and would be false once a rung records identity.
        prov.append("Both provenance files predate per-rung extractor identity, so this report reads unrecorded on both.")
    prov.append("Record count is provenance prompt_count (JSON records).")
    prov.append("File count is on-disk unique-id .md files - normalize-corpus.py collapses identical-content duplicate records into one file.")
    S.append("\n".join(prov))

    counts = {}
    for v in ctx["verdicts"].values():
        counts[v.verdict] = counts.get(v.verdict, 0) + 1
    S.append("\n".join([
        "## Classification summary",
        _table(["verdict", "count"], [[k, str(counts[k])] for k in sorted(counts)]),
        "",
        "pack orphans (apply to neither install): %d" % len(ctx["pack_orphans"]),
    ]))

    lines = []
    for v in review_class(ctx["verdicts"]):
        lines += ["### %s" % v.id, "", "note: %s" % v.note, ""]
        new_id = align.remaps.get(v.id, v.id)          # resolved_new_id semantics
        old_body = _variants(ctx["old_shas"].get(v.id), ctx["old_text"])
        new_body = _variants(ctx["new_shas"].get(new_id), ctx["new_text"])
        if v.override_type == "suppression":
            ovr_body = "(empty - suppressed)"
        elif v.id in pack_bodies:
            ovr_body = pack_bodies[v.id]
        else:
            ovr_body = "(absent)"
        for label, body in (("old stock", old_body), ("new stock", new_body), ("override", ovr_body)):
            f = _fence(body)
            lines += ["%s:" % label, f, body, f, ""]
    S.append("\n".join(["## Review class (needs eyes)"] + (lines or ["None."])))

    remaps = align.remaps
    remap_rows = [[k, remaps[k]] for k in sorted(remaps)]
    S.append("\n".join(
        ["## Segmentation remaps"]
        + ([_table(["old id", "new id"], remap_rows), "",
            "%d remap(s), counted, not reviewed." % len(remap_rows)] if remap_rows else ["None."])
    ))

    new_only = sorted(align.new_only)
    S.append("\n".join(["## New in new stock (no override)"]
                       + (["- %s" % i for i in new_only] if new_only else ["None."])))

    retro = ctx.get("retro")
    if retro is None:
        retro_lines = ["Not run (deterministic mode)."]
    else:
        flags = sorted(retro)
        retro_lines = (["- %s" % f for f in flags] if flags else ["Ran: no drift flags."])
    S.append("\n".join(["## Retro-check"] + retro_lines))

    while S[-1].endswith("\n"):                    # no trailing blanks inside a section
        S[-1] = S[-1][:-1]
    return "\n\n".join(S) + "\n"


def _tracker(*args):
    r = subprocess.run([TRACKER, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("tracker.sh %s failed: %s" % (args[0], r.stderr.strip()))
    return r.stdout


def emit_issue(report_path, review_count, old_v, new_v, pack_name):
    """Open the molt-review issue (or receipt onto the existing one) and
    return its number. Dedup: pin-target is re-runnable, so an open issue
    with the exact deterministic title gets a re-run receipt comment instead
    of a duplicate. Never called when review_count == 0; guarded anyway.
    """
    if review_count <= 0:
        return None
    title = "Molt review: %s %s to %s (%d findings)" % (pack_name, old_v, new_v, review_count)
    body = ("%d override(s) need eyes in the %s to %s molt.\nReport: %s"
            % (review_count, old_v, new_v, report_path))
    # Match the bump, not the full title: the count is part of the created
    # title, but a re-run of the same bump can carry a different count, and
    # deduping only on exact titles would file a sibling issue exactly then.
    # The ' (' terminator keeps the prefix unambiguous across bumps that share
    # a version prefix (e.g. 2 vs 22). The receipt comment carries the fresh
    # count and report path, so a stale count in the old title is covered.
    prefix = "Molt review: %s %s to %s (" % (pack_name, old_v, new_v)
    for it in json.loads(_tracker("list")):
        if str(it.get("title", "")).startswith(prefix):
            _tracker("comment", str(it["number"]),
                     "molt re-run receipt: %s; report refreshed at %s" % (title, report_path))
            return it["number"]
    _tracker("label", "ensure", "molt-review")
    out = _tracker("create", "--label", "molt-review", "--title", title, "--body", body)
    return int(out.strip().splitlines()[-1])


def selftest():
    from collections import namedtuple
    V = namedtuple("Verdict", "id verdict override_type old_present new_present underlay_changed note")
    verdicts = {
        "a": V("a", "auto-realign", "mirror", True, True, False, "ok"),
        "b": V("b", "review", "rewrite", True, True, True, "differs from both"),
        "c": V("c", "review", "rewrite", True, True, True, "collided underlay"),
    }
    class A:  # minimal alignment stand-in
        remaps = {"moved": "renamed"}
        new_only = {"fresh"}
    ctx = dict(
        manifest={"name": "p", "ref": "abc"},
        old_v="1", new_v="2",
        old_prov={"rung": "cache", "prompt_count": 3, "extractor_cc_version": None},
        new_prov={"rung": "cache", "prompt_count": 4, "extractor_cc_version": None},
        old_file_count=3, new_file_count=4,
        verdicts=verdicts, align=A(),
        old_shas={"b": {"OLD"}, "c": {"S1", "S2"}},
        new_shas={"b": {"NEW"}, "c": {"S3"}},
        old_text={"OLD": "old body b", "S1": "slice one", "S2": "slice two"},
        new_text={"NEW": "new body b", "S3": "new slice"},
        pack_orphans=["orph1"], retro=None, generated="TS1",
    )
    r1 = render(ctx)
    assert "## Review class" in r1
    assert "old body b" in r1 and "new body b" in r1          # inline stock diff (criterion 7)
    assert "slice one" in r1 and "slice two" in r1            # both collided variants rendered
    assert "variant" in r1                                    # variant separator present
    assert "differs from both" in r1
    assert "renamed" in r1                                    # segmentation remap listed
    assert "fresh" in r1                                      # new-in-new-stock listed
    assert "Not run (deterministic mode)." in r1              # retro None
    # determinism: only the timestamp line differs across renders
    ctx2 = dict(ctx); ctx2["generated"] = "TS2"
    r2 = render(ctx2)
    d = [(x, y) for x, y in zip(r1.splitlines(), r2.splitlines()) if x != y]
    assert d == [("generated: TS1", "generated: TS2")], d
    print("molt_report selftest: ok")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    else:
        sys.exit("usage: molt_report.py --selftest")
