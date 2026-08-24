#!/usr/bin/env python3
"""Read the governed pack at a pinned git ref (see docs/plans W10 task 1)."""

import os, re, sys, json, subprocess, tempfile
from pathlib import Path

sys.path.insert(0, "scripts")
nc = __import__("normalize-corpus")

HEADER = re.compile(r"^\s*<!--.*?-->\s*", re.S)


def load_manifest(path="config/governed-pack.json") -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_repo(manifest) -> str:
    env = os.environ.get("GOVERNED_PACK_REPO")
    if env:
        return env
    return os.path.expanduser(manifest["repo"])


def text_pins(manifest) -> set:
    return set(manifest.get("text_pins", []))


def load_pack(manifest) -> dict:
    """Map prompt id -> normalize(body) for every <variant>/<id>.md at the pinned ref.

    git archive failure raises with stderr surfaced; never falls back to a live tree.
    """
    repo = resolve_repo(manifest)
    variant = manifest["variant"].strip("/")
    with tempfile.TemporaryDirectory() as tmp:
        # pipe tar ourselves so a git error surfaces instead of being eaten by the pipe
        git = subprocess.Popen(
            ["git", "-C", repo, "archive", manifest["ref"], variant],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tar = subprocess.run(["tar", "-x", "-C", tmp], stdin=git.stdout,
                             capture_output=True)
        git_err = git.stderr.read().decode("utf-8", "replace")
        git.stdout.close()
        rc = git.wait()
        if rc != 0 or tar.returncode != 0:
            raise RuntimeError(f"git archive failed for {repo}@{manifest['ref']}: {git_err}")
        bodies = {}
        for f in sorted(Path(tmp, variant).glob("*.md")):
            raw = f.read_text(encoding="utf-8")
            bodies[f.stem] = nc.normalize(HEADER.sub("", raw, count=1))
    return bodies


def selftest():
    import tempfile, subprocess, os, json, pathlib
    # A throwaway git repo standing in for the external pack.
    d = tempfile.mkdtemp()
    pack = pathlib.Path(d) / "sp"
    (pack / "v").mkdir(parents=True)
    (pack / "v" / "mirror.md").write_text("<!--\nccVersion: 1\n-->\n\nhello   world\n")
    (pack / "v" / "supp.md").write_text("<!-- x -->\n\n  \n")
    subprocess.run(["git", "-C", str(pack), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(pack), "add", "-A"], check=True)
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", "-C", str(pack), "commit", "-qm", "x"], check=True, env=env)
    ref = subprocess.run(["git", "-C", str(pack), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    man = {"name": "t", "repo": str(pack), "variant": "v", "ref": ref, "text_pins": ["mirror"]}
    bodies = load_pack(man)
    assert bodies["mirror"] == "hello world", bodies["mirror"]   # header stripped, ws collapsed
    assert bodies["supp"] == "", repr(bodies["supp"])            # suppression kept as empty
    assert text_pins(man) == {"mirror"}
    # GOVERNED_PACK_REPO override wins over the manifest repo value.
    os.environ["GOVERNED_PACK_REPO"] = str(pack)
    assert resolve_repo({"repo": "~/does-not-exist"}) == str(pack)
    del os.environ["GOVERNED_PACK_REPO"]
    print("molt_pack selftest: ok")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        selftest()
    else:
        sys.exit("usage: molt_pack.py --selftest")
