#!/usr/bin/env bash
# Corpus acquisition source ladder: cache -> skrabe published JSON -> local
# extraction from the pinned binary via tweakcc-fixed. Writes provenance and
# caches the resolved corpus. Exit 0 success, 3 naming-required, else hard fail.
set -uo pipefail

V="${1:?usage: acquire-corpus.sh <version> <binary-path> <out-json>}"
BIN="${2:?usage: acquire-corpus.sh <version> <binary-path> <out-json>}"
OUT="${3:?usage: acquire-corpus.sh <version> <binary-path> <out-json>}"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$HOME/.tweakcc/prompt-data-cache/prompts-$V.json"
TWEAKCC="$HOME/repos/tweakcc-fixed"
SKRABE_URL="https://raw.githubusercontent.com/skrabe/tweakcc-fixed/refs/heads/main/data/prompts/prompts-$V.json"

RUNG="" SOURCE_URL="" SKRABE_SHA="" TWEAKCC_SHA="" EXTRACTOR_VERSION=""
EXTRACTOR_SOURCE="" EXTERNALLY_VERIFIED=""

count_prompts() {
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(len(d["prompts"] if isinstance(d,dict) else d))' "$1"
}

finish() {  # provenance + cache + count line
    local n; n="$(count_prompts "$OUT")" || exit 1
    mkdir -p "$REPO_DIR/corpora-provenance" "$(dirname "$CACHE")"
    RUNG="$RUNG" SOURCE_URL="$SOURCE_URL" SKRABE_SHA="$SKRABE_SHA" TWEAKCC_SHA="$TWEAKCC_SHA" \
    EXTRACTOR_VERSION="$EXTRACTOR_VERSION" EXTRACTOR_SOURCE="$EXTRACTOR_SOURCE" \
    EXTERNALLY_VERIFIED="$EXTERNALLY_VERIFIED" V="$V" N="$n" \
    python3 - > "$REPO_DIR/corpora-provenance/$V.json" <<'PY'
import json, os, datetime
print(json.dumps({k: v for k, v in {
    'version': os.environ['V'],
    'rung': os.environ['RUNG'],
    'source_url': os.environ['SOURCE_URL'],
    'skrabe_git_sha': os.environ['SKRABE_SHA'],
    'tweakcc_fixed_git_sha': os.environ['TWEAKCC_SHA'],
    'extractor_cc_version': os.environ['EXTRACTOR_VERSION'],
    'extractor_source': os.environ['EXTRACTOR_SOURCE'],
    # 'true' -> JSON true; '' pruned by the v != '' filter (missing = unrecorded).
    'externally_verified': True if os.environ['EXTERNALLY_VERIFIED'] == 'true' else '',
    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'prompt_count': int(os.environ['N']),
}.items() if v != ''}, indent=2))
PY
    cp "$OUT" "$CACHE"
    echo "prompts: $n"
    exit 0
}

# Rung 1: local cache
for SRC in "$CACHE" "$TWEAKCC/data/prompts/prompts-$V.json"; do
    if [ -f "$SRC" ]; then
        if [ "$V" = "2.1.204" ]; then
            # Executed stock-content check: cache must match skrabe's published JSON.
            PUB_SHA="$(curl -fsSL "$SKRABE_URL" | shasum -a 256 | cut -d' ' -f1)" || { echo "skrabe fetch for 2.1.204 stock check failed" >&2; exit 1; }
            LOC_SHA="$(shasum -a 256 "$SRC" | cut -d' ' -f1)"
            [ "$PUB_SHA" = "$LOC_SHA" ] || { echo "2.1.204 cache differs from skrabe published ($LOC_SHA != $PUB_SHA)" >&2; exit 1; }
            EXTERNALLY_VERIFIED=true
        fi
        cp "$SRC" "$OUT"
        RUNG=cache SOURCE_URL="$SRC" EXTRACTOR_SOURCE=cache
        finish
    fi
done

# Rung 2: skrabe published JSON
if curl -fsSL "$SKRABE_URL" -o "$OUT.tmp"; then
    mv "$OUT.tmp" "$OUT"
    RUNG=skrabe SOURCE_URL="$SKRABE_URL" EXTRACTOR_SOURCE=skrabe EXTERNALLY_VERIFIED=true
    SKRABE_SHA="$(git -C "$TWEAKCC" ls-remote origin HEAD 2>/dev/null | cut -f1)" || true
    finish
fi
rm -f "$OUT.tmp"

# Rung 3: local extraction from the pinned binary
# 3a: dist module present, clone current with origin.
if ! ls "$TWEAKCC"/dist/nativeInstallation-*.mjs >/dev/null 2>&1 \
   || ! { git -C "$TWEAKCC" fetch --quiet origin \
          && [ "$(git -C "$TWEAKCC" rev-parse HEAD)" = "$(git -C "$TWEAKCC" rev-parse origin/main)" ]; }; then
    echo "tweakcc-fixed clone not ready for local extraction. One-time setup:" >&2
    echo "  git -C ~/repos/tweakcc-fixed pull --ff-only" >&2
    echo "  cd ~/repos/tweakcc-fixed && pnpm install && pnpm build" >&2
    exit 1
fi

# 3b: seed = newest published prompts-*.json with version <= V.
SEED="$(ls "$TWEAKCC"/data/prompts/prompts-*.json | sort -t- -k2 -V | awk -v v="prompts-$V.json" -F/ '$NF <= v' | tail -1)"
[ -n "$SEED" ] || { echo "no seed prompts-*.json with version <= $V" >&2; exit 1; }
cp "$SEED" "$OUT"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 3c: version-verified cli.js extraction (isolated env on every tweakcc command).
TWEAKCC_CONFIG_DIR="$TMP/cfg" TWEAKCC_CC_INSTALLATION_PATH="$BIN" \
    node "$REPO_DIR/scripts/extract-clijs.mjs" "$BIN" "$V" "$TMP/cli-$V.js" || exit 1

# 3d: structured prompt extraction (reads $OUT as fuzzy-carryover seed, rewrites it).
# NODE_PATH: @babel/parser is a transitive dep under pnpm's hidden store, not top-level.
TWEAKCC_CONFIG_DIR="$TMP/cfg" TWEAKCC_CC_INSTALLATION_PATH="$BIN" TWEAKCC_CC_VERSION="$V" \
    NODE_PATH="$TWEAKCC/node_modules/.pnpm/node_modules" \
    node "$TWEAKCC/tools/promptExtractor.js" "$TMP/cli-$V.js" "$OUT" || exit 1

# 3e+3f: apply the committed name map; list records still anonymous.
ANON="$REPO_DIR/corpora-provenance/$V.anonymous.json"
mkdir -p "$REPO_DIR/corpora-provenance"
OUT="$OUT" ANON="$ANON" REPO_DIR="$REPO_DIR" python3 - <<'PY'
import json, os, sys
sys.path.insert(0, os.path.join(os.environ['REPO_DIR'], 'scripts'))
normalize_corpus = __import__('normalize-corpus')
out_path = os.environ['OUT']
data = json.load(open(out_path))
names = json.load(open(os.path.join(os.environ['REPO_DIR'], 'config/prompt-names.json')))
anon = []
for rec in data['prompts']:
    if rec.get('name') and rec.get('id'):
        continue
    sha = normalize_corpus.content_sha(rec)
    if sha in names:
        rec['id'] = names[sha]['id']
        rec['name'] = names[sha]['name']
    else:
        anon.append({'content_sha256': sha,
                     'identifiers': rec.get('identifiers') or [],
                     'normalized': normalize_corpus.normalize(normalize_corpus.reconstruct(rec))})
if anon:
    json.dump(anon, open(os.environ['ANON'], 'w'), indent=2)
    sys.exit(3)
json.dump(data, open(out_path, 'w'), indent=2)
PY
rc=$?
if [ $rc -eq 3 ]; then
    echo "naming required: $(count_prompts "$OUT" 2>/dev/null || echo '?') prompts extracted, anonymous list at corpora-provenance/$V.anonymous.json" >&2
    echo "add names to config/prompt-names.json then re-run just pin-target $V" >&2
    exit 3
fi
[ $rc -eq 0 ] || exit "$rc"

# 3g: provenance for the local rung.
RUNG=local SOURCE_URL="$BIN"
TWEAKCC_SHA="$(git -C "$TWEAKCC" rev-parse HEAD)"
EXTRACTOR_VERSION="$V"
finish
