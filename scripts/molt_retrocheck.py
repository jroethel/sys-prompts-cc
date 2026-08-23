#!/usr/bin/env python3
"""Retro-check sweep: compare a frozen corpus against the skrabe published set.

The ONLY network touch in the molt pipeline, gated by should_run (env RETRO=1,
else tty ask, else skip) so deterministic re-runs never reach it.
"""
import json
import sys
import urllib.request


def is_unverified(prov):
    return prov.get("rung") != "skrabe" and prov.get("externally_verified") is not True


def skrabe_url(version):
    return f"https://raw.githubusercontent.com/skrabe/tweakcc-fixed/refs/heads/main/data/prompts/prompts-{version}.json"


def should_run(env, isatty, prompt=input):
    if env.get("RETRO") == "1":
        return True
    if env.get("RETRO") is not None:
        return False  # conservative: any explicit value other than 1 is an opt-out
    if isatty:
        return prompt("Run retro-check (network) now? [y/N] ").strip().lower() in ("y", "yes")
    return False


def _fetch_shas(version):
    sys.path.insert(0, "scripts")
    nc = __import__("normalize-corpus")  # hyphenated filename; same import as acquire-corpus.sh
    with urllib.request.urlopen(skrabe_url(version), timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    prompts = data["prompts"] if isinstance(data, dict) else data
    shas = {}
    for rec in prompts:
        shas.setdefault(str(rec["id"]), set()).add(nc.content_sha(rec))
    return shas


def _short(sha_set):
    return sorted(s[:8] for s in sha_set)


def retrocheck(version, corpus_shas):
    try:
        published = _fetch_shas(version)
    except Exception as e:  # network/HTTP/parse failure degrades to one flag, never raises
        return [f"retro fetch failed for {version}: {e.__class__.__name__}: {e}"]
    flags = []
    for pid in sorted(set(published) | set(corpus_shas)):
        pub, corp = published.get(pid, set()), corpus_shas.get(pid, set())
        if pub != corp:  # missing on either side is an empty set and flags too
            flags.append(f"{pid}: skrabe {_short(pub)} vs corpus {_short(corp)}")
    return flags


def selftest():
    assert is_unverified({"rung": "cache"}) is True
    assert is_unverified({"rung": "skrabe"}) is False
    assert is_unverified({"rung": "cache", "externally_verified": True}) is False
    assert skrabe_url("2.1.241").endswith("prompts-2.1.241.json")
    # gate mechanic
    assert should_run({"RETRO": "1"}, isatty=False) is True
    assert should_run({}, isatty=False) is False
    assert should_run({}, isatty=True, prompt=lambda *_: "y") is True
    assert should_run({}, isatty=True, prompt=lambda *_: "n") is False
    # retrocheck against a stubbed fetcher
    global _fetch_shas
    real = _fetch_shas
    _fetch_shas = lambda v: {"same": {"x"}, "drifted": {"y"}}
    try:
        flags = retrocheck("2.1.241", {"same": {"x"}, "drifted": {"z"}})
        assert any("drifted" in f for f in flags), flags
        assert not any("same" in f for f in flags), flags
    finally:
        _fetch_shas = real
    # a failing fetch degrades to a single flag, never raises
    _fetch_shas = lambda v: (_ for _ in ()).throw(OSError("boom"))
    try:
        flags = retrocheck("2.1.241", {"a": {"x"}})
        assert len(flags) == 1 and "fetch" in flags[0].lower(), flags
    finally:
        _fetch_shas = real
    print("molt_retrocheck selftest: ok")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    else:
        sys.exit("usage: molt_retrocheck.py --selftest")
