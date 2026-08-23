#!/usr/bin/env python3
"""Molt orchestrator and CLI (W10 task 6).

Wires tasks 1-5 into one deterministic pipeline: load corpora, provenance,
manifest, and the pack at its pinned ref; align; classify; render; write the
report. Inputs are repo-relative plus the manifest-pinned pack - this module
never reads ~/.local/bin/claude, ~/.local/share/claude, or CLAUDE_CONFIG_DIR
(criterion 6). The retro-check is the only network touch and only when the
--retro flag AND should_run both open the gate. Exit 0 on a successful
classification regardless of review count; non-zero is a real error.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from molt_align import build_alignment, load_corpus, resolved_new_id
from molt_pack import load_manifest, load_pack, text_pins
from molt_report import emit_issue, render
from molt_retrocheck import is_unverified, retrocheck, should_run
from molt_verdict import classify, review_class


def _load_prov(version):
    p = Path("corpora-provenance/%s.json" % version)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit("molt: missing provenance %s" % p)
    except (OSError, ValueError) as e:
        sys.exit("molt: unreadable provenance %s: %s" % (p, e))


def main(argv):
    ap = argparse.ArgumentParser(prog="molt.py", description=__doc__.splitlines()[0])
    ap.add_argument("old_v")
    ap.add_argument("new_v")
    ap.add_argument("--emit-issue", action="store_true",
                    help="open a molt-review issue when REVIEW > 0 (real tracker side effect)")
    ap.add_argument("--retro", action="store_true",
                    help="enable the retro-check gate; should_run still owns the env/tty decision")
    ap.add_argument("--report-dir", default="docs/molt")
    args = ap.parse_args(argv)

    corpora = {}
    for v in (args.old_v, args.new_v):
        d = Path("corpora") / v
        if not d.is_dir():
            sys.exit("molt: missing corpus %s" % d)
        shas, text = load_corpus(d)
        corpora[v] = (shas, text)
    old_shas, old_text = corpora[args.old_v]
    new_shas, new_text = corpora[args.new_v]
    old_prov, new_prov = _load_prov(args.old_v), _load_prov(args.new_v)
    manifest = load_manifest()

    pack_bodies = load_pack(manifest)
    align = build_alignment(old_shas, new_shas)
    verdicts = classify(pack_bodies, text_pins(manifest), old_shas, new_shas, align)
    # Pack orphans: ids applying to neither install, mirroring classify's own
    # skip test exactly (old id absent AND resolved new id absent).
    pack_orphans = sorted(pid for pid in pack_bodies
                          if pid not in old_shas
                          and resolved_new_id(align, pid) not in new_shas)

    # Retro gate: the flag AND should_run together; a closed gate keeps re-runs
    # deterministic and the review count pure-classification.
    retro_flags = None
    if args.retro and should_run(os.environ, sys.stdin.isatty()):
        retro_flags = []
        for v, prov, shas in ((args.old_v, old_prov, old_shas),
                              (args.new_v, new_prov, new_shas)):
            if is_unverified(prov):
                retro_flags += retrocheck(v, shas)
        retro_flags.sort()

    review_count = len(review_class(verdicts)) + len(retro_flags or [])

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / ("%s.%s-to-%s.md" % (manifest["name"], args.old_v, args.new_v))
    ctx = dict(
        manifest=manifest, old_v=args.old_v, new_v=args.new_v,
        old_prov=old_prov, new_prov=new_prov,
        old_file_count=len(list((Path("corpora") / args.old_v).glob("*.md"))),
        new_file_count=len(list((Path("corpora") / args.new_v).glob("*.md"))),
        verdicts=verdicts, align=align,
        old_shas=old_shas, new_shas=new_shas, old_text=old_text, new_text=new_text,
        pack_orphans=pack_orphans, retro=retro_flags, pack_bodies=pack_bodies,
        generated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    report_path.write_text(render(ctx), encoding="utf-8")

    print("molt: %s %s to %s" % (manifest["name"], args.old_v, args.new_v))
    print("report: %s" % report_path)
    print("review class: %d, retro flags: %s"
          % (len(review_class(verdicts)),
             "not run (deterministic mode)" if retro_flags is None else len(retro_flags)))
    print("REVIEW=%d" % review_count)

    if args.emit_issue and review_count > 0:
        num = emit_issue(str(report_path), review_count, args.old_v, args.new_v, manifest["name"])
        print("issue: #%s" % num)
    return 0


def selftest():
    import contextlib
    import io
    import os
    import json
    import pathlib
    import re
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    root = pathlib.Path(d)
    # A throwaway git repo standing in for the external pack (Task 1 pattern).
    pack = root / "sp"
    (pack / "v").mkdir(parents=True)
    (pack / "v" / "mirror.md").write_text("<!-- x -->\n\nmirror body one\n")
    (pack / "v" / "rw.md").write_text("<!-- x -->\n\noverride rw body\n")
    (pack / "v" / "moved.md").write_text("<!-- x -->\n\nmoving body\n")
    (pack / "v" / "orphan_pack.md").write_text("<!-- x -->\n\napplies nowhere\n")
    subprocess.run(["git", "-C", str(pack), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(pack), "add", "-A"], check=True)
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", "-C", str(pack), "commit", "-qm", "x"], check=True, env=env)
    ref = subprocess.run(["git", "-C", str(pack), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    # A tiny corpora tree. Stock files are written as the exact normalized text
    # (no trailing newline) so sha256(file bytes) equals the pack-side
    # sha256(normalize(body)) for mirrors.
    def stock(rel, text):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    stock("corpora/1/mirror.md", "mirror body one")   # unchanged across pins
    stock("corpora/2/mirror.md", "mirror body one")
    stock("corpora/1/moved.md", "moving body")        # remaps to renamed in 2
    stock("corpora/2/renamed.md", "moving body")
    stock("corpora/1/rw.md", "old rw body")           # underlay changed, override differs
    stock("corpora/2/rw.md", "new rw body")
    for v in ("1", "2"):
        stock("corpora-provenance/%s.json" % v, json.dumps(
            {"version": v, "rung": "cache", "prompt_count": 3}))
    stock("config/governed-pack.json", json.dumps(
        {"name": "t", "repo": str(pack), "variant": "v", "ref": ref, "text_pins": []}))
    # Keep the fixture hermetic: a stray GOVERNED_PACK_REPO would win over the
    # manifest repo and point the pack read somewhere else entirely.
    os.environ.pop("GOVERNED_PACK_REPO", None)
    reports, outs = [], []
    cwd = os.getcwd()
    try:
        os.chdir(root)
        for _ in range(2):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                main(["1", "2", "--report-dir", str(root)])
            outs.append(buf.getvalue())
            reports.append((root / "t.1-to-2.md").read_text())
    finally:
        os.chdir(cwd)
    assert (root / "t.1-to-2.md").is_file(), "report not written to <report-dir>/<pack>.<oldV>-to-<newV>.md"
    # fixture has exactly one review-class override (rw over a changed underlay)
    assert re.search(r"^REVIEW=1$", outs[0], re.M), outs[0]
    assert re.search(r"^REVIEW=\d+$", outs[1], re.M), outs[1]
    # determinism: re-runs are byte-identical modulo the generated: line
    l1, l2 = reports[0].splitlines(), reports[1].splitlines()
    assert len(l1) == len(l2), "report line count moved between runs"
    diffs = [(a, b) for a, b in zip(l1, l2) if a != b]
    assert all(a.startswith("generated:") and b.startswith("generated:")
               for a, b in diffs), diffs
    assert "## Review class" in reports[0]
    print("molt selftest: ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    else:
        sys.exit(main(sys.argv[1:]))
