# Pin the Target - Current Claude Code plus its Normalized Corpus Implementation Plan

> For executors: tasks use checkbox syntax; execute in dependency order; a task is done when its
> acceptance check passes. No specific tooling, harness, or skills are assumed.

**Goal:** Pin the target Claude Code binary (2.1.241) side by side with the live 2.1.204, extract and normalize both versions' prompt corpora into directly comparable form, and package the whole acquire-extract-normalize flow as one re-runnable `just pin-target <version>` command.

**Approach:** Download the target binary directly from the GCS release bucket (structurally cannot touch the live symlink), then resolve each version's structured prompt corpus by a three-step source ladder - local cache, then skrabe's published JSON, then local extraction from the pinned binary via tweakcc-fixed - and run one shared normalizer over both corpora. Every corpus records its provenance (which rung, which source and tool SHAs) and every hand-assigned prompt name persists to a committed map, so re-runs are deterministic and portable and skrabe catching up later is adoptable.

**Tech stack:** bash (acquire), Python 3 (normalize), Node.js + tweakcc-fixed (local extraction fallback), just (command interface), gh (ticket record).

**Source brief:** `docs/briefs/2026-08-22-pin-target-corpus-brief.md`

## Global constraints

- Target version this ticket pins: `2.1.241` (npm latest as of 2026-08-22); the pipeline reads V from `npm view @anthropic-ai/claude-code version` by default and accepts an explicit version argument. Any non-interactive or scheduled run must pass V explicitly.
- Baseline of record: `2.1.204`, expected record count `1537`, expected normalized file count `1426`
  (58 duplicate ids: 57 identical-content, deduped; 1 id with 2 distinct contents, content-suffixed). This is the live-install version today and this ticket's other diff side; it is a documented baseline value, not a forever-constant (see the symlink invariance rule).
- Symlink invariance: snapshot `readlink ~/.local/bin/claude` at the start of any run and assert it is unchanged at the end. Never write the symlink. For this ticket the snapshot is `~/.local/share/claude/versions/2.1.204`, which satisfies criterion 1.
- Never launch any binary beyond `--version`; test launches belong to ticket #8.
- Never replace or overwrite an existing binary on disk (this protects the live 2.1.204, which may be patched); acquisition only ever downloads a version that is absent.
- Platform is `darwin-arm64`.
- GCS release bucket: `claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819`.
- GCS binary URL: `https://storage.googleapis.com/<bucket>/claude-code-releases/<V>/darwin-arm64/claude`.
- GCS manifest URL: `https://storage.googleapis.com/<bucket>/claude-code-releases/<V>/manifest.json`; its `platforms."darwin-arm64".checksum` field is the vendor SHA-256.
- skrabe corpus URL: `https://raw.githubusercontent.com/skrabe/tweakcc-fixed/refs/heads/main/data/prompts/prompts-<V>.json`.
- tweakcc-fixed clone: `~/repos/tweakcc-fixed` (origin is skrabe); local extraction uses its `dist/` and `tools/promptExtractor.js`. The clone must be pulled to a release whose CC target is >= V before local extraction; its git SHA is recorded in provenance.
- Local extraction isolation: always set `TWEAKCC_CONFIG_DIR=<throwaway dir>` and `TWEAKCC_CC_INSTALLATION_PATH=<side-by-side binary>` so nothing writes shared `~/.tweakcc` state; clean the throwaway dir on exit.
- These files must be byte-identical before and after any run: `~/.tweakcc/config.json`, `~/.tweakcc/systemPromptAppliedHashes.json`, `~/.tweakcc/systemPromptOriginalHashes.json`, `~/.claude.json`, `~/.claude/settings.json`.
- The one intended shared-state write is `~/.tweakcc/prompt-data-cache/prompts-<V>.json` (the corpus cache). It is not in the byte-identical guard list because it is the deliberate cache write; it is version-scoped and never touches the files above.
- Normalizer sentinel is `$INTERP` - brace-free on purpose, so the `${...}` collapse reaches a fixpoint even for nested interpolations. Normalization: undo template escaping (`\`` to backtick, `\$` to `$`), collapse every `${...}` interpolation innermost-first to `$INTERP`, then collapse whitespace runs to one space and strip.
- Corpus layout: `corpora/<version>/<id>.md`, one normalized-prose file per prompt id, identical naming scheme both sides; `corpora/` is gitignored.
- Provenance: each run writes a committed `corpora-provenance/<version>.json` (rung that resolved, source URL, skrabe git SHA if used, tweakcc-fixed git SHA if used, extractor/CC version, timestamp, prompt count). `corpora-provenance/` is committed; only `corpora/` text is ignored.
- Committed name map: `config/prompt-names.json` maps a prompt's normalized-content SHA-256 to its chosen `{id, name}`. It is applied automatically on every local extraction and only genuinely new hashes trigger the naming checkpoint. This makes the sign-off idempotent and portable across hosts.
- Final `prompts-<V>.json` is cached to `~/.tweakcc/prompt-data-cache/prompts-<V>.json`; warm re-runs read the cache. Cold-cache determinism (extract twice, byte-identical) is proven separately for the local route, not assumed.

## Dependency graph

```
Wave 1 (parallel):  Task 1 (normalizer)      Task 2 (binary acquire)
Wave 2:             Task 3 (corpus acquire)              depends on Task 2
Wave 3:             Task 4 (pin-target recipe + gitignore + e2e)  depends on Tasks 1,2,3
Wave 4:             Task 5 (record on ticket)            depends on Task 4
```

Tasks 1 and 2 touch disjoint files and run in parallel. File ownership is exclusive across every task.

## Human checkpoints

- Task 3, local-extraction route, first encounter of a genuinely new prompt only: prompts whose content SHA-256 is not in `config/prompt-names.json` extract anonymous. The executor proposes high-confidence names, the user signs off, and the names are written to `config/prompt-names.json`. On any later run (same or another host) those names auto-apply and the gate does not fire. It fires for some of 2.1.241's new prompts because skrabe currently 404s on it. The gate is a distinct non-zero exit with a resume message, never an interactive pause inside the recipe.
- Task 5: posting the comment to GitHub issue #11 is outbound to a shared system. The executor stages the exact `gh` command and the user fires it.

## How to run

```
# from the repo root: /Users/jjrdar/create/sys-prompts-cc
just pin-target 2.1.204      # baseline: binary on disk (not replaced), corpus JSON cached -> normalize
just pin-target 2.1.241      # target: download binary, local-extract corpus (skrabe 404), normalize
just pin-target 2.1.241      # after a naming exit: re-run to resume once names are approved
diff -rq corpora/2.1.204 corpora/2.1.241
```

One-time setup for the local-extraction fallback (Task 3):

```
git -C ~/repos/tweakcc-fixed pull --ff-only          # move the clone to a release whose CC target >= V
cd ~/repos/tweakcc-fixed && pnpm install && pnpm build   # provides @babel/parser and dist/
```

## Task 1: The normalizer

Depends on: none

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/normalize-corpus.py` (carries an inline `--selftest` mode; no separate test file, matching the repo's script-with-inline-check style)

**Interfaces:**
- Consumes: a `prompts-<version>.json` with top-level `{version, prompts:[...]}`, each prompt a record with
  `id` (string), `pieces` (list of string), `identifiers` (list of string).
- Produces: `<out-dir>/<id>.md` per prompt id; identical-content duplicates of an id dedupe to one file,
  and an id with multiple DISTINCT normalized contents writes `<out-dir>/<id>__<sha8>.md` per variant
  (sha8 = first 8 hex of the content SHA-256, so filenames are deterministic and order-independent).
  Prints the file count to stdout as the last line in the exact form `count: <N>`.
- Exports (importable by Task 3 for hashing): `normalize(s)` and `reconstruct(rec)`; the content SHA used by
  the name map is `sha256(normalize(reconstruct(rec)))`.

**Acceptance check:** `python3 scripts/normalize-corpus.py --selftest && python3 scripts/normalize-corpus.py ~/.tweakcc/prompt-data-cache/prompts-2.1.204.json /tmp/c204 && test "$(ls /tmp/c204 | wc -l | tr -d ' ')" = 1426` exits 0 `[executed-check]`

- [ ] Step 1: Write `scripts/normalize-corpus.py`. Implementation code below IS the spec - the normalization is load-bearing per `docs/research/diff-surface.md`, and the sentinel must be brace-free so the collapse fixpoints on nested interpolations:

  ```python
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
  ```

- [ ] Step 2: Run `python3 scripts/normalize-corpus.py --selftest`; expect `selftest: ok`. `[executed-check]`
- [ ] Step 3: Run the acceptance check command above; expect exit 0 (1426 files from 1537 records). `[executed-check]`
- [ ] Step 4: Determinism - normalize into `/tmp/c204b`, then `diff -rq /tmp/c204 /tmp/c204b`; expect no output.
- [ ] Step 5: Commit - `git add scripts/normalize-corpus.py && git commit -m "Add prompt-corpus normalizer"`

## Task 2: Binary acquisition (symlink-safe GCS download, verify-or-report)

Depends on: none

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/acquire-binary.sh`

**Interfaces:**
- Consumes: `<version>` as `$1`.
- Produces: the binary at `~/.local/share/claude/versions/<version>` (executable), and prints its SHA-256 and
  verification state to stdout as the last line in the exact form `sha256: <hex> <verified|unverified>`.
- Verify-or-report contract: fetch the manifest checksum; if the binary is ABSENT, download and verify, and
  fail on mismatch. If the binary is PRESENT, never overwrite it - compute its SHA and label `verified` on a
  manifest match or `unverified` on a mismatch (a mismatch is expected for a patched live install and is not
  a failure for a present binary).

**Acceptance check:** `bash scripts/acquire-binary.sh 2.1.241 | grep -Eq '^sha256: [0-9a-f]{64} verified$' && ~/.local/share/claude/versions/2.1.241 --version | grep -q '^2.1.241 ' && L="$(readlink ~/.local/bin/claude)" && [ "$L" = "$HOME/.local/share/claude/versions/2.1.204" ]` exits 0 `[executed-check]`

- [ ] Step 1: Write `scripts/acquire-binary.sh` (use `set -uo pipefail`, catch expected non-zero explicitly). Contract:
  - `LINK_BEFORE="$(readlink ~/.local/bin/claude)"` at start; assert `LINK_BEFORE == "$(readlink ~/.local/bin/claude)"` at end (invariance), never write the symlink.
  - `BUCKET=claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819`; `BASE=https://storage.googleapis.com/$BUCKET/claude-code-releases`; `DEST="$HOME/.local/share/claude/versions/$V"`.
  - Fetch expected SHA: `curl -fsSL "$BASE/$V/manifest.json"`, read `.platforms."darwin-arm64".checksum` via `python3 -c`.
  - If `$DEST` absent: `curl -fL "$BASE/$V/darwin-arm64/claude" -o "$DEST.tmp"`, `chmod +x "$DEST.tmp"`, compute `shasum -a 256`; on mismatch delete tmp and exit non-zero; on match `mv "$DEST.tmp" "$DEST"` and print `sha256: <hex> verified`.
  - If `$DEST` present: compute `shasum -a 256 "$DEST"`; print `sha256: <hex> verified` on match, else `sha256: <hex> unverified`; never overwrite.
  - Never invoke `claude install`; never launch `$DEST` except `--version`.
- [ ] Step 2: Snapshot the live symlink: `readlink ~/.local/bin/claude` (expect `.../versions/2.1.204`).
- [ ] Step 3: Run `bash scripts/acquire-binary.sh 2.1.241`; expect `sha256: <hex> verified` (fresh download matches manifest).
- [ ] Step 4: Run the acceptance check; expect exit 0. `[executed-check]`
- [ ] Step 5: Present-binary path - run `bash scripts/acquire-binary.sh 2.1.204`; expect a `sha256:` line (verified if the on-disk 2.1.204 is stock, unverified if patched) and no change to the file.
- [ ] Step 6: Commit - `git add scripts/acquire-binary.sh && git commit -m "Add symlink-safe GCS binary acquisition"`

## Task 3: Corpus acquisition (source ladder, verified extraction, persistent naming)

Depends on: Task 2

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/acquire-corpus.sh`
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/extract-clijs.mjs`
- Create: `/Users/jjrdar/create/sys-prompts-cc/config/prompt-names.json` (initial content `{}`)

**Interfaces:**
- Consumes: `<version>` as `$1`, `<binary-path>` as `$2`, `<out-json>` as `$3`.
- Produces: a structured `prompts-<version>.json` at `<out-json>`, a cached copy at
  `~/.tweakcc/prompt-data-cache/prompts-<version>.json`, and `corpora-provenance/<version>.json`. Prints the
  prompt count as the last line in the exact form `prompts: <N>`.
- Exit codes: `0` success; `3` naming-required (writes the anonymous list and a resume message, caches
  nothing); non-zero otherwise for a hard failure.
- `extract-clijs.mjs` consumes `<binary-path> <version> <out-clijs>`, dynamically imports the tweakcc-fixed
  `dist/nativeInstallation-*.mjs` module, calls `extractClaudeJsFromNativeInstallation(binaryPath, version)`
  so it targets the side-by-side binary (not the live symlink), and asserts the extracted JS is a non-trivial
  string whose first `\d+.\d+.\d+` equals `<version>` (this catches a wrong-version or live-binary extraction
  that the 5-sample strings check could miss). Exits non-zero on any failure.

**Acceptance check:** with a `/tmp/guard.before` snapshot taken first (Step 5), `bash scripts/acquire-corpus.sh 2.1.241 ~/.local/share/claude/versions/2.1.241 /tmp/p241.json; test $? -ne 0 -o -f corpora-provenance/2.1.241.json` runs, and after resuming to exit 0 the five must-not-touch files are byte-identical (Step 6) `[executed-check]`

- [ ] Step 1: Write `scripts/extract-clijs.mjs`:

  ```javascript
  #!/usr/bin/env node
  // Extract cli.js from an ARBITRARY native binary (not the live symlink) by
  // calling tweakcc-fixed's dist entry point directly, and verify the version.
  import fs from 'node:fs';
  import os from 'node:os';
  import path from 'node:path';
  const [bin, ver, out] = process.argv.slice(2);
  if (!bin || !ver || !out) { console.error('usage: extract-clijs.mjs <binary> <version> <out>'); process.exit(1); }
  const distDir = path.join(os.homedir(), 'repos/tweakcc-fixed/dist');
  const mod = fs.readdirSync(distDir).find((f) => /^nativeInstallation-.*\.mjs$/.test(f));
  if (!mod) { console.error('dist nativeInstallation module not found - run pnpm build'); process.exit(2); }
  const { extractClaudeJsFromNativeInstallation } = await import(path.join(distDir, mod));
  const r = await extractClaudeJsFromNativeInstallation(bin, ver);
  const data = r?.data ?? r;
  const buf = Buffer.isBuffer(data) ? data : Buffer.from(String(data));
  if (buf.length < 1_000_000) { console.error(`extracted cli.js too small: ${buf.length} bytes`); process.exit(3); }
  const first = (buf.toString('utf8').match(/\d+\.\d+\.\d+/) || [])[0];
  if (first !== ver) { console.error(`extracted version ${first} != requested ${ver} (wrong binary?)`); process.exit(4); }
  fs.writeFileSync(out, buf);
  console.log(`extracted ${(buf.length / 1048576).toFixed(1)}MB -> ${out} (version ${first})`);
  ```

- [ ] Step 2: Write `scripts/acquire-corpus.sh` (use `set -uo pipefail`; every ladder rung is wrapped so a rung's failure falls through instead of aborting - a bare `curl -f` on skrabe's 404 must NOT kill the script). Ladder in order:
  1. Local cache hit: if `~/.tweakcc/prompt-data-cache/prompts-<V>.json` or `~/repos/tweakcc-fixed/data/prompts/prompts-<V>.json` exists, copy it to `<out-json>` and cache. For V=2.1.204, additionally assert its SHA-256 equals skrabe's published `prompts-2.1.204.json` (`curl -fsSL <skrabe-url> | shasum -a 256`) and fail on mismatch - this is the executed stock-content check the brief asked for. Rung = `cache`.
  2. skrabe hit: `if curl -fsSL "<skrabe-url>" -o "<out-json>.tmp"; then mv ...; rung=skrabe; else` continue. Record the skrabe git SHA (`git -C ~/repos/tweakcc-fixed ls-remote origin HEAD`) in provenance.
  3. Local extraction fallback, every tweakcc command wrapped with `TWEAKCC_CONFIG_DIR="$(mktemp -d)" TWEAKCC_CC_INSTALLATION_PATH="<binary-path>"` and a `trap 'rm -rf "$TMP"' EXIT`:
     a. Assert `~/repos/tweakcc-fixed/dist/` exists and the clone's released CC target >= V (parse the newest `data/prompts/prompts-*.json`); if not, print the one-time-setup commands and exit non-zero.
     b. Seed: copy the newest `data/prompts/prompts-*.json` with version <= V to `<out-json>` (the extractor reads an existing out-file as its fuzzy-carryover seed).
     c. `node scripts/extract-clijs.mjs "<binary-path>" "<V>" "$TMP/cli-<V>.js"` (version-verified).
     d. `node ~/repos/tweakcc-fixed/tools/promptExtractor.js "$TMP/cli-<V>.js" "<out-json>"`.
     e. Apply `config/prompt-names.json`: for each record with an empty name or hash-only id, look up its content SHA-256 (`sha256(normalize(reconstruct(rec)))` via `scripts/normalize-corpus.py`) and assign the mapped `{id, name}`.
     f. Collect records still anonymous after the map. If any: write them to `corpora-provenance/<V>.anonymous.json`, print a resume message (`add names to config/prompt-names.json then re-run just pin-target <V>`), and exit `3`. Cache nothing.
     g. Rung = `local`; record the tweakcc-fixed git SHA and extractor version in provenance.
  4. On a resolved corpus: write `corpora-provenance/<V>.json` (rung, source URL, SHAs, version, timestamp, count), copy `<out-json>` to the cache, and print `prompts: <N>`.
- [ ] Step 3: Create `config/prompt-names.json` with `{}`.
- [ ] Step 4: Confirm isolation - grep `acquire-corpus.sh` to ensure no step-3 tweakcc invocation runs without both env vars set, and that a `trap` cleans the throwaway dir.
- [ ] Step 5: Snapshot the must-not-touch files:
  `for f in ~/.tweakcc/config.json ~/.tweakcc/systemPromptAppliedHashes.json ~/.tweakcc/systemPromptOriginalHashes.json ~/.claude.json ~/.claude/settings.json; do shasum -a 256 "$f"; done > /tmp/guard.before`
- [ ] Step 6: Run for 2.1.241 (local route). Expect exit `3` with an anonymous list on first encounter; propose names, get sign-off, add them to `config/prompt-names.json`, re-run to exit `0`. Then re-snapshot into `/tmp/guard.after` and `diff /tmp/guard.before /tmp/guard.after`; expect no output. `[executed-check]`
- [ ] Step 7: Validate 5 prompts against the binary - `strings -n 6 ~/.local/share/claude/versions/2.1.241 > /tmp/bin241.strings`, then sample five `pieces[]` fragments (each >= 12 chars, containing no `${`), preferring prompts new in 2.1.241, and `grep -F` each in `/tmp/bin241.strings`. Expect all five found; a miss is a hard failure, not a sample artifact. `[executed-check]`
- [ ] Step 8: Commit - `git add scripts/acquire-corpus.sh scripts/extract-clijs.mjs config/prompt-names.json && git commit -m "Add corpus acquisition source ladder with verified extraction and persistent naming"`

## Task 4: The pin-target recipe (gitignore, wiring, end-to-end proof)

Depends on: Task 1, Task 2, Task 3

**Files (exclusive ownership):**
- Modify: `/Users/jjrdar/create/sys-prompts-cc/.gitignore`
- Create: `/Users/jjrdar/create/sys-prompts-cc/justfile`

**Interfaces:**
- Consumes: `scripts/acquire-binary.sh`, `scripts/acquire-corpus.sh`, `scripts/normalize-corpus.py`.
- Produces: `corpora/<version>/` populated, `corpora-provenance/<version>.json`, and a final stdout line
  `pinned: <V> sha256=<hex> prompts=<N>`.

**Acceptance check:** `just pin-target 2.1.204 && just pin-target 2.1.241 && { diff -rq corpora/2.1.204 corpora/2.1.241 >/dev/null; c=$?; [ $c -le 1 ]; } && [ -z "$(git status --porcelain corpora)" ]` exits 0 `[executed-check]`

- [ ] Step 1: Append `corpora/` to `.gitignore` on its own line (leave `corpora-provenance/` tracked).
- [ ] Step 2: Create `justfile` with a `pin-target` recipe. Every version routes binary acquisition through `acquire-binary.sh` (so the reported SHA is always the verify-or-report value, never an unchecked `shasum`), snapshots the symlink for the invariance guard, and surfaces the naming exit code:

  ```just
  # Acquire, extract, and normalize a Claude Code version's prompt corpus.
  # Usage: just pin-target [version]   (version defaults to npm latest; pass V explicitly for non-interactive runs)
  pin-target version="":
      #!/usr/bin/env bash
      set -uo pipefail
      V="{{version}}"; [ -z "$V" ] && V="$(npm view @anthropic-ai/claude-code version)"
      LINK_BEFORE="$(readlink "$HOME/.local/bin/claude")"
      BIN="$HOME/.local/share/claude/versions/$V"
      SHA="$(bash scripts/acquire-binary.sh "$V" | sed -n 's/^sha256: \([0-9a-f]*\).*/\1/p')" || exit 1
      J="$(mktemp -d)/prompts-$V.json"
      OUT="$(bash scripts/acquire-corpus.sh "$V" "$BIN" "$J")"; rc=$?
      if [ $rc -eq 3 ]; then echo "$OUT"; echo "naming required for $V - add names to config/prompt-names.json then re-run"; exit 3; fi
      [ $rc -eq 0 ] || { echo "$OUT" >&2; exit $rc; }
      N="$(printf '%s\n' "$OUT" | sed -n 's/^prompts: //p')"
      python3 scripts/normalize-corpus.py "$J" "corpora/$V"
      [ "$(readlink "$HOME/.local/bin/claude")" = "$LINK_BEFORE" ] || { echo "SYMLINK MOVED" >&2; exit 1; }
      echo "pinned: $V sha256=$SHA prompts=$N"
  ```

- [ ] Step 3: Run `just pin-target 2.1.204`; expect `corpora/2.1.204/` with 1426 files, `corpora-provenance/2.1.204.json`, and a `pinned:` line.
- [ ] Step 4: Run `just pin-target 2.1.241` (resume after naming if it exits 3); expect `corpora/2.1.241/` populated, provenance written, and a `pinned:` line.
- [ ] Step 5: Run `diff -rq corpora/2.1.204 corpora/2.1.241`; expect it to run and report content and presence differences (exit 0 or 1, never a usage error). `[executed-check]`
- [ ] Step 6: Confirm gitignore - `git status --porcelain corpora`; expect no output, and `git status --porcelain corpora-provenance` shows the provenance files as tracked/untracked (not ignored). `[executed-check]`
- [ ] Step 7: Warm idempotency (criterion 7) - copy `corpora/2.1.204` aside, re-run `just pin-target 2.1.204`, then `diff -rq` before/after; expect no output. `[executed-check]`
- [ ] Step 8: Cold-cache determinism for the local route - remove the cache before EACH extraction so both runs are genuinely cold: `rm -f ~/.tweakcc/prompt-data-cache/prompts-2.1.241.json && bash scripts/acquire-corpus.sh 2.1.241 ~/.local/share/claude/versions/2.1.241 /tmp/a.json && rm -f ~/.tweakcc/prompt-data-cache/prompts-2.1.241.json && bash scripts/acquire-corpus.sh 2.1.241 ~/.local/share/claude/versions/2.1.241 /tmp/b.json && diff /tmp/a.json /tmp/b.json`; expect no output (names resolve from the committed map, so cold extraction is deterministic). `[executed-check]`
- [ ] Step 9: Commit - `git add justfile .gitignore && git commit -m "Wire pin-target pipeline end to end"`

## Task 5: Record the pin on ticket #11

Depends on: Task 4

**Files (exclusive ownership):**
- None (produces a GitHub comment; no repo files change beyond the provenance already committed in Task 4).

**Interfaces:**
- Consumes: the `pinned:` line from Task 4, the 2.1.204 counts (1537 records, 1426 files), and both `corpora-provenance/<V>.json` files.

**Acceptance check:** after the user fires the staged command, `gh issue view 11 --comments | grep -F "sha256 <hex>"` returns the comment `[executed-check]`

- [ ] Step 1: Assemble the comment body: V, the binary SHA-256 and its verify state, the 2.1.204 counts (1537 records, 1426 files) and V counts, and each corpus's resolved rung plus source/tool SHAs from provenance.
- [ ] Step 2: Stage the exact command for the user to fire (human checkpoint - outbound to a shared system):
  `gh issue comment 11 --body "Pinned target <V>. binary sha256 <hex> (<verified|unverified>). corpora: 2.1.204=1537 (rung cache), <V>=<N> (rung local, tweakcc-fixed <sha>). provenance committed under corpora-provenance/."`
- [ ] Step 3: After the user runs it, verify with `gh issue view 11 --comments | tail -20`; expect the comment present. `[executed-check]`

## Notes on resolved brief questions and review findings

- Binary acquisition uses direct GCS download, not `claude install` - the download cannot touch the live symlink, so criterion 1 holds by construction. The guard is invariance-based (snapshot at start, compare at end) so the pipeline survives the eventual live-install upgrade instead of self-bricking on a hardcoded 2.1.204.
- Extraction isolation uses `TWEAKCC_CONFIG_DIR` + `TWEAKCC_CC_INSTALLATION_PATH` (verified present in tweakcc-fixed `src/config.ts`, `src/installationDetection.ts`), with a cleanup trap. The only intended shared write is the version-scoped corpus cache.
- The 2.1.204 corpus derives from the existing cache, asserted at runtime to be byte-identical to skrabe's published `prompts-2.1.204.json`; this executes the stock-content check the brief flagged rather than resting on a static claim. The cache is skrabe-canonical, independent of the live binary's patch state.
- Reproducibility spine: every corpus writes `corpora-provenance/<V>.json` (committed), hand-assigned names persist to `config/prompt-names.json` (committed, content-hash keyed, portable across hosts), and the local route proves cold-cache determinism directly rather than resting on the cache short-circuit. Extractor and source git SHAs in provenance make a cross-rung phantom-drift row (skrabe-published baseline vs locally-extracted target) diagnosable; semantic id-bridging for the richer diff is #10's job, this ticket's `diff -rq` only needs to run and report.
- Local extraction is version-verified (`extract-clijs.mjs` requires the extracted cli.js first version to equal V) and depth-checked by a strings spot-check over `pieces[]` fragments (not reconstructed bodies, which carry `${...}` boundaries absent from the minified binary); a miss is a hard failure. The clone must be pulled to a release whose CC target >= V before this route runs.
- Source-ladder evidence: skrabe covers 189 of 209 npm 2.1.x releases (90%), currently two behind latest (404 on 2.1.240 and 2.1.241), missing about one in three of the last 40 releases. The local-extraction fallback with a persistent name map is what makes 2.1.241 reachable now and every future frontier version reachable and re-runnable without waiting on skrabe.
