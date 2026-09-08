# SP Metrics Instrument Implementation Plan

> For executors: tasks use checkbox syntax; execute in dependency order; a task is done when its
> acceptance check passes. No specific tooling, harness, or skills are assumed.

**Goal:** Build the zero-spend measurement instrument the two-pass SP pilot needs - extractors, scans, blinding, and the held-up verdict - each proven on historical Claude Code session transcripts, with the live passes staged as human checkpoints and no autonomous API spend.

**Approach:** Compose small single-responsibility scripts over the session JSONL surface that already exists, following the repo's script-with-inline-selftest style (`scripts/normalize-corpus.py`). Every script is proven against synthetic fixtures and at least one real historical transcript, so the whole instrument is demonstrable today for zero cost; the paired live runs, the blind rating, the second judge, and the go/no-go are staged as documented human checkpoints that the downstream #8 herdr skeleton drives.

**Tech stack:** Python 3 (extractors, scans, verdict), bash (config seeding, isolation, dry-run), jq, git, just (recipe surface). No new dependencies.

**Source brief:** `docs/briefs/2026-08-22-sp-metrics-benchmarks-brief.md`

## Global constraints

- Scope is the zero-spend instrument only (brief seams 1-3 plus the log and verdict machinery seams 4-5 consume). No task fires a live model call; no task incurs API spend. The herdr firing skeleton is ticket #8, out of scope here.
- The brief's "Done looks like" is already satisfied on GitHub as of 2026-08-23: the brief is committed, issue #7 is CLOSED with the decision-summary comment, the map (#1) Decisions-so-far carries the #7 line, the parking lot graduated to #12-#15, and #8 is unblocked. No task re-does this; it is a verification note only (see Human checkpoints).
- Session transcript source: `~/.claude/projects/<project>/<session-id>.jsonl`. Every assistant record carries `.message.usage` with `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens` (verified this session). Any parser that meets a record missing these keys fails loud with the record index, never silently miscounts.
- Assistant text is read only from `.message.content[]` blocks of type `text` on records with `.type=="assistant"`. Never scan `user` or `tool_result` content (it carries quoted material that produces false tic and completion-claim hits).
- Compaction marker (disk-checked 2026-08-23 over 200 transcripts): the current Claude Code JSONL carries no `isCompactSummary`, `type=="summary"`, `compactMetadata`, or `compact`-named subtype field. The only real auto-compaction signal is the continuation-preamble text `This session is being continued from a previous conversation` inside a `type=="user"` record, and it is rare in the corpus. Compaction is therefore a fragile, version-specific, low-N signal: it is detected from that text and treated as a non-blocking secondary in the verdict (Task 6), never a held-up gate. The one real compacted transcript found this session is `~/.claude/projects/-Users-jjrdar-create-sys-prompts-cc/95005e71-3ed4-4192-bd14-aa0ad00e8eec.jsonl` (manual-confirmation fixture; do not hardcode a rotating path into an automated check).
- Pilot artifacts live under `pilot/`; pilot scripts live under `scripts/` prefixed `pilot-`. Committed by default: pilot scripts, schemas, templates, phrase lists, and READMEs. Gitignored in Task 7 and never committed: `pilot/**/*.jsonl` (transcripts and ledgers copied in at run time), `pilot/**/key.sealed.json` (unblinding keys), `pilot/runs/`, and `pilot/tasks/` - curated task packets carry mined prompt text and are committed only by an explicit `git add -f` after the scrub gate, never by a blanket `git add pilot`.
- Isolation invariant (protects the daily install): the shared-state hash set is exactly these files, hashed with `shasum -a 256`:
  `~/.claude.json`, `~/.claude/settings.json`, `~/.tweakcc/config.json`, `~/.tweakcc/systemPromptAppliedHashes.json`, `~/.tweakcc/systemPromptOriginalHashes.json`.
  This set must be byte-identical before and after any isolated invocation and before and after any live pass.
- Isolation mechanism: `CLAUDE_CONFIG_DIR=<throwaway>` redirects the config root; every non-pinned launch also passes an explicit `--model`. The zero-spend isolation task proves redirection non-tautologically - a harmless non-model config WRITE under the throwaway dir must land inside that dir while the shared-state hash set stays byte-identical - and does not claim full session isolation, which is folded into the first live pass (a checkpoint).
- Model pins: pass 1 is `claude-opus-4-8` in both panes (exact ID, never a bare alias, never Fable). Pass 2 old side `claude-opus-4-8`, new side the 2.1.241 Opus-generation default, its exact ID resolved from the pinned 2.1.241 binary at pass-2 staging (a checkpoint), not hardcoded here.
- Held-up thresholds (from the brief): behavior wins at least 2:1 among non-ties; cache-write smaller on turn one; auto-compaction measurably later (a non-blocking secondary per the compaction-marker note, reported not gated); guard - no tracked cost metric worse than stock by more than 10% at the median, else not held up at this N. The guard set is `input_tokens, output_tokens, cache_creation_input_tokens, turns` and deliberately EXCLUDES `cache_read_input_tokens`, because more cache reuse is cheaper and better, not worse (Task 6).
- Stratification: a mined task is `quick` at <=5 assistant turns in its source session, else `multi`.

## Dependency graph

```
Wave 1 (parallel, disjoint files):
  Task 1 (config seed + isolation harness)
  Task 2 (metric extractor)
  Task 3 (tic + completion scans)
  Task 4 (blinding anonymizer)
  Task 5 (task-mining scaffold)
Wave 2:
  Task 6 (held-up verdict + log schema)      depends on Task 2
Wave 3:
  Task 7 (end-to-end dry-run tracer + run-book + gitignore + recipes)  depends on Tasks 1-6
```

Tasks 1-5 own disjoint files and run in parallel. Task 6 consumes Task 2's metrics-record schema. Task 7 wires everything and is the composition tracer.

## Human checkpoints

These never ride on a task; each is a place the executor stops and a human acts.

- **Task 1 - curated test profile.** The content of `pilot/curated-claudemd.md` (which of the operator's CLAUDE.md rules ship in the test profile, the controlled variable per the #7 decision) is Jeremy's curation. The task creates a documented starting subset; Jeremy confirms or edits it before any live pass.
- **Task 5 - task curation.** The mining tool surfaces candidates; Jeremy picks the 12 per pass, writes each evidence checklist (every item names its evidence), and snapshots each task's input state. Zero spend, but human judgment. Candidates may be pooled across hosts (run the miner on the day-job host for a more representative task distribution); any cross-host or data-sensitive candidate is scrubbed or synthesized before its prompt text and input snapshot become a committed packet.
- **Pass 1 and Pass 2 (not tasks in this plan).** Firing the 12 paired live runs (real spend), running the daily-install config hash guard before and after, the blind pairwise A/B/tie rating (Jeremy, at least a day after any variant work), the GLM second-judge routing, and Jeremy's acceptance of the read-out as decision-grade (the brief's one `[judgment]` criterion - the go/no-go is genuinely his). The first live pass also carries the full live-session isolation confirmation.
- **Pass 2 model ID.** Resolve the 2.1.241 Opus-generation default model ID from the pinned binary at pass-2 staging and record it on the pairwise log header.
- **Done-verification (no work).** Confirm `gh issue view 7 --json state` is `CLOSED` and the map #1 carries the #7 decision line; both are already true as of 2026-08-23.

## How to run

```
# from the repo root: /Users/jjrdar/create/sys-prompts-cc
# every script self-tests with no external input:
python3 scripts/pilot-metrics.py --selftest
python3 scripts/pilot-tic-scan.py --selftest
python3 scripts/pilot-completion-scan.py --selftest
python3 scripts/pilot-blind.py --selftest
python3 scripts/pilot-mine-tasks.py --selftest
python3 scripts/pilot-verdict.py --selftest
bash scripts/pilot-isolation-check.sh
bash scripts/pilot-dryrun.sh        # end-to-end composition over two real historical transcripts
```

A real historical transcript for the acceptance checks (any assistant-bearing session):

```
ls -t ~/.claude/projects/*/*.jsonl | head -1     # pick one; call it $T below
```

## Task 1: Config seed and isolation harness

Depends on: none

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-seed-config.sh`
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-isolation-check.sh`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/settings-seed.json`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/curated-claudemd.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces:
  - `pilot-seed-config.sh <config-dir> <model-id>`: creates `<config-dir>`, writes `<config-dir>/settings.json` from `pilot/settings-seed.json` with its `model` field set to `<model-id>`, copies `pilot/curated-claudemd.md` to `<config-dir>/CLAUDE.md`, and prints the exact launch line `CLAUDE_CONFIG_DIR=<config-dir> claude --model <model-id>` as its last stdout line. Never writes outside `<config-dir>`.
  - `pilot-isolation-check.sh`: exit 0 iff, after a harmless non-model config WRITE run under a throwaway `CLAUDE_CONFIG_DIR`, (a) the shared-state hash set (Global constraints) is byte-identical and (b) the write landed as a NEW file inside the throwaway dir that the seed step did not create (proving redirection, not just a non-empty dir). Prints `isolation: ok` on success, `isolation: FAIL <reason>` on failure.

**Acceptance check:** `bash scripts/pilot-isolation-check.sh | grep -q '^isolation: ok'` exits 0 `[executed-check]`

- [ ] Step 1: Write `pilot/settings-seed.json` - a minimal settings blob the pilot launches under, with an explicit model placeholder and no MCP or hooks (the test profile is deliberately lean):

  ```json
  {
    "model": "REPLACED_BY_SEED",
    "includeCoAuthoredBy": false
  }
  ```

- [ ] Step 2: Write `pilot/curated-claudemd.md` - the documented starting subset of the operator's house-style rules the test profile ships (the controlled variable). Include exactly the rules the tic scan checks against so profile and scan agree, and mark it for Jeremy's curation:

  ```markdown
  <!-- Curated test profile for the SP pilot. Controlled variable per #7.
       Jeremy confirms/edits which rules ship before any live pass. -->
  # Test profile house rules
  - Use plain dash "-", never the em dash.
  - Say "Section", never the section symbol.
  - Avoid: "load-bearing", "worth stating plainly", "here's the honest truth",
    "the real tension", "carry the argument".
  - Do not claim completion without evidence.
  - State each fact once.
  ```

- [ ] Step 3: Write `pilot-seed-config.sh` (`set -euo pipefail`). Contract: `D="$1"; M="$2"; mkdir -p "$D"; python3 -c` to load `pilot/settings-seed.json`, set `model=M`, write `"$D/settings.json"`; `cp pilot/curated-claudemd.md "$D/CLAUDE.md"`; final line `echo "CLAUDE_CONFIG_DIR=$D claude --model $M"`.
- [ ] Step 4: Write `pilot-isolation-check.sh` (`set -uo pipefail`). Contract:
  - `FILES` = the five shared-state paths in Global constraints; hash the ones that exist into `BEFORE="$(for f in "${FILES[@]}"; do [ -e "$f" ] && shasum -a 256 "$f"; done)"`.
  - `TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT`.
  - `bash scripts/pilot-seed-config.sh "$TMP/cfg" claude-opus-4-8 >/dev/null`; snapshot the post-seed file set: `SEED="$(cd "$TMP/cfg" && find . -type f | sort)"`.
  - Run a harmless non-model config WRITE under isolation (config commands make no model call and touch no billed surface): `CLAUDE_CONFIG_DIR="$TMP/cfg" claude config set -g <a-harmless-key> <val> >/dev/null 2>&1 || true`. The executor pins the exact key/subcommand against `claude config --help`; the requirement is only that it is a config write, never a session or model call.
  - `AFTER_FILES="$(cd "$TMP/cfg" && find . -type f | sort)"`; re-hash shared state into `AFTER`.
  - Assert `[ "$BEFORE" = "$AFTER" ]` (else `isolation: FAIL shared-state changed` - this is the invariant that protects the daily install) AND `[ "$SEED" != "$AFTER_FILES" ]`, i.e. the config write created a file the seed did not (else `isolation: FAIL write not redirected into config dir`). On both, print `isolation: ok`.
  - If no config-write subcommand is available in the pinned CC, fall back to asserting only shared-state invariance and print `isolation: ok (shared-state invariance only; redirection confirmed at first live pass)` - never a bare `isolation: ok` that overclaims.
- [ ] Step 5: Run the acceptance check; expect exit 0 and `isolation: ok`. `[executed-check]`
- [ ] Step 6: Commit - `git add scripts/pilot-seed-config.sh scripts/pilot-isolation-check.sh pilot/settings-seed.json pilot/curated-claudemd.md && git commit -m "Add pilot config seed and zero-spend isolation harness"`

## Task 2: Metric extractor

Depends on: none

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-metrics.py`

**Interfaces:**
- Consumes: a session JSONL path as `argv[1]`, an optional `--task-id <id>` (stamped onto the record so Task 6 can join stock and variant runs by task, not by line order), or `--selftest`.
- Produces: one JSON object to stdout with exactly these keys, summed across assistant turns unless noted:
  `task_id` (str or null, from `--task-id`, else null),
  `session_id` (str, from the file stem), `turns` (int, count of `type=="assistant"` records),
  `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` (ints, summed),
  `cache_write_turn1` (int, `cache_creation_input_tokens` on the FIRST assistant turn),
  `compaction_turn` (int or null, the count of assistant turns seen when the first compaction record appears, else null),
  `errors` (int, count of `tool_result` content blocks with `is_error==true`, the error/retry signal the brief flags as primary for pass 2),
  `output_chars` (int, summed length of assistant `text` blocks),
  `output_chars_per_turn` (float, `output_chars/turns`, 0.0 if turns==0).
- Exports (importable by Task 6): `extract(records: list[dict], task_id: str | None = None) -> dict` returning the record above.
- Fail-loud: an assistant record lacking `.message.usage`, or whose usage is missing any of the four token keys, exits non-zero with `usage shape error at assistant turn <i>` (verified this session: real transcripts always carry a full usage block, so this fires only on a genuinely unrecognized shape).
- Compaction detection is a single documented function `is_compaction(rec)` returning True iff `rec.get("type")=="user"` and its first `text` content contains `This session is being continued from a previous conversation` (the only real marker in the current JSONL, per the compaction-marker constraint; no structured field exists). Absence yields `compaction_turn=null` and is not an error. This detector is version-specific by nature; confirm it against the manual-confirmation fixture named in Global constraints, and if a future CC version adds a structured field, this one function is where it changes.

**Acceptance check:** `python3 scripts/pilot-metrics.py --selftest && python3 scripts/pilot-metrics.py "$(ls -t ~/.claude/projects/*/*.jsonl | head -1)" | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d["turns"]>0 and d["input_tokens"]>0 and set(["task_id","cache_write_turn1","compaction_turn","errors","output_chars_per_turn"])<=set(d); print("ok")'` exits 0 `[executed-check]`

- [ ] Step 1: Write the failing test as the inline `--selftest` (this test code IS the spec):

  ```python
  def selftest():
      recs = [
          {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello"}],
           "usage": {"input_tokens": 100, "output_tokens": 5, "cache_read_input_tokens": 0,
                     "cache_creation_input_tokens": 2000}}},
          {"type": "user", "message": {"content": [{"type": "tool_result", "content": "boom",
                                                    "is_error": True}]}},
          {"type": "assistant", "message": {"content": [{"type": "text", "text": "done now"}],
           "usage": {"input_tokens": 50, "output_tokens": 3, "cache_read_input_tokens": 1800,
                     "cache_creation_input_tokens": 40}}},
          {"type": "user", "message": {"content": [{"type": "text",
              "text": "This session is being continued from a previous conversation ..."}]}},
      ]
      d = extract(recs)
      assert d["turns"] == 2, d
      assert d["input_tokens"] == 150 and d["output_tokens"] == 8, d
      assert d["cache_creation_input_tokens"] == 2040 and d["cache_write_turn1"] == 2000, d
      assert d["output_chars"] == len("hello") + len("done now"), d
      assert d["compaction_turn"] == 2, d          # continuation preamble seen after 2 assistant turns
      assert d["errors"] == 1, d                    # one is_error tool_result
      assert d["task_id"] is None, d
      assert extract(recs, task_id="t03")["task_id"] == "t03", "task_id stamps for the verdict join"
      # fail-loud on bad usage shape
      bad = [{"type": "assistant", "message": {"content": [], "usage": {"input_tokens": 1}}}]
      try:
          extract(bad); assert False, "should have raised"
      except ValueError as e:
          assert "usage shape error" in str(e), e
      print("selftest: ok")
  ```

- [ ] Step 2: Run `python3 scripts/pilot-metrics.py --selftest`; expect the `AssertionError`/`NameError` FAIL (no `extract` yet). `[executed-check]`
- [ ] Step 3: Implement `extract` and `main` against the Interfaces contract. `main` reads the JSONL line by line (skip blank lines), builds the record list, resolves `--task-id`, calls `extract(records, task_id)`, and `json.dumps` to stdout. `compaction_turn` is the assistant-turn count seen so far when the first `is_compaction(rec)` record is met.
- [ ] Step 4: Run `python3 scripts/pilot-metrics.py --selftest`; expect `selftest: ok`. `[executed-check]`
- [ ] Step 5: Run the acceptance check; expect `ok` (parses a real production transcript, all keys present). `[executed-check]`
- [ ] Step 5b: Confirm the compaction detector against the real fixture in Global constraints - `python3 scripts/pilot-metrics.py ~/.claude/projects/-Users-jjrdar-create-sys-prompts-cc/95005e71-3ed4-4192-bd14-aa0ad00e8eec.jsonl | python3 -c 'import sys,json; assert json.load(sys.stdin)["compaction_turn"] is not None; print("compaction ok")'` if that file still exists; if it has rotated away, note it and rely on the selftest. `[executed-check]`
- [ ] Step 6: Commit - `git add scripts/pilot-metrics.py && git commit -m "Add pilot per-run metric extractor"`

## Task 3: Tic scan and completion-gate scan

Depends on: none

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-tic-scan.py`
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-completion-scan.py`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/tic-phrases.txt`

**Interfaces:**
- `pilot-tic-scan.py <session.jsonl>|--selftest`: reads the phrase list from `pilot/tic-phrases.txt` (one entry per line, `#` comments and blanks ignored, case-insensitive substring match over assistant `text` only). Emits JSON:
  `session_id`, `tic_counts` (dict phrase->int, every listed phrase present with its count, zeros included), `tic_total` (int, sum), `em_dash` (int, count of `—`), `section_symbol` (int, count of `§`), `permission_seeking` (int, matches over a fixed phrase set below), `tool_calls` (int, count of `tool_use` content blocks), `tool_profile` (dict tool-name->int).
  Permission-seeking phrases (fixed in code): `"would you like me to"`, `"do you want me to"`, `"should i proceed"`, `"shall i"`, `"is it okay if i"`, `"let me know if you want"`.
- `pilot-completion-scan.py <session.jsonl>|--selftest`: flags assistant completion claims lacking a real executed check. A claim is a case-insensitive match of any of `"done"`, `"fixed"`, `"passing"`, `"tests pass"`, `"verified"`, `"complete"`, `"works now"`, `"all set"` in an assistant `text` block. A claim is backed iff the SAME assistant turn also issues a `tool_use` of an executable-check tool (the set `{"Bash"}`, the only real command-execution surface) whose `tool_result` appears in the following `type=="user"` record; a claim followed only by a read-only tool (`Read`, `Grep`, `Glob`) or by no tool is unmatched, and a claim is never retroactively backed by a later turn's command. Aggregation is per turn: one `claims` entry per assistant turn that contains at least one claim phrase (`claim` = the first phrase matched in that turn), backed at the turn level, so a turn with two claim phrases counts once. Emits JSON: `claims` (list of `{turn:int, claim:str, backed:bool}`), `unmatched_claims` (int, count of turns with `backed==false`).
- Exports: `scan_tics(records, phrases) -> dict`, `scan_completion(records) -> dict`.

**Acceptance check:** `python3 scripts/pilot-tic-scan.py --selftest && python3 scripts/pilot-completion-scan.py --selftest && python3 scripts/pilot-tic-scan.py "$(ls -t ~/.claude/projects/*/*.jsonl | head -1)" >/dev/null && python3 scripts/pilot-completion-scan.py "$(ls -t ~/.claude/projects/*/*.jsonl | head -1)" >/dev/null` exits 0 `[executed-check]`

- [ ] Step 1: Write `pilot/tic-phrases.txt` (seeded from the operator's CLAUDE.md ban list plus the opus-slop research `~/create/research/opus-slop/briefing-v1-system-prompt-engineering.md`):

  ```
  # CLAUDE.md ban list
  load-bearing
  worth stating plainly
  here's the honest truth
  the real tension
  carry the argument
  # opus-slop register tells
  you're absolutely right
  slaps words together
  # em dash and section symbol are counted separately as em_dash / section_symbol
  ```

- [ ] Step 2: Write the failing tests as inline `--selftest` in each script (this test code IS the spec):

  ```python
  # pilot-tic-scan.py selftest
  def selftest():
      phrases = ["load-bearing", "you're absolutely right"]
      recs = [
          {"type": "assistant", "message": {"content": [
              {"type": "text", "text": "This is load-bearing - and load-bearing again — yes."},
              {"type": "tool_use", "name": "Bash", "input": {}}]}},
          {"type": "user", "message": {"content": [{"type": "tool_result",
              "content": "load-bearing in quoted output must NOT count"}]}},
          {"type": "assistant", "message": {"content": [
              {"type": "text", "text": "Would you like me to proceed?"},
              {"type": "tool_use", "name": "Read", "input": {}}]}},
      ]
      d = scan_tics(recs, phrases)
      assert d["tic_counts"]["load-bearing"] == 2, d          # both in assistant text, not the tool_result
      assert d["em_dash"] == 1 and d["section_symbol"] == 0, d
      assert d["permission_seeking"] == 1, d
      assert d["tool_calls"] == 2 and d["tool_profile"] == {"Bash": 1, "Read": 1}, d
      print("selftest: ok")
  ```

  ```python
  # pilot-completion-scan.py selftest
  def selftest():
      recs = [
          {"type": "assistant", "message": {"content": [
              {"type": "text", "text": "All fixed and tests pass."}]}},          # claim, no tool -> unbacked
          {"type": "assistant", "message": {"content": [
              {"type": "text", "text": "Verified, it is complete."},
              {"type": "tool_use", "name": "Read"}]}},                            # claim + read-only tool -> unbacked
          {"type": "user", "message": {"content": [{"type": "tool_result", "content": "..."}]}},
          {"type": "assistant", "message": {"content": [
              {"type": "text", "text": "It works now."}, {"type": "tool_use", "name": "Bash"}]}},  # claim + exec
          {"type": "user", "message": {"content": [{"type": "tool_result", "content": "PASS"}]}},  # backs turn 3
      ]
      d = scan_completion(recs)
      assert d["unmatched_claims"] == 2, d
      claims = {c["turn"]: c["backed"] for c in d["claims"]}
      assert claims[1] is False and claims[2] is False and claims[3] is True, d   # Read does not back a claim
      print("selftest: ok")
  ```

- [ ] Step 3: Run both `--selftest`; expect FAIL (functions undefined). `[executed-check]`
- [ ] Step 4: Implement `scan_tics` and `scan_completion` against the contract; `main` reads the JSONL, calls the scanner, `json.dumps` to stdout.
- [ ] Step 5: Run both `--selftest`; expect `selftest: ok` each. `[executed-check]`
- [ ] Step 6: Run each against a real transcript; expect exit 0, valid JSON. `[executed-check]`
- [ ] Step 7: Commit - `git add scripts/pilot-tic-scan.py scripts/pilot-completion-scan.py pilot/tic-phrases.txt && git commit -m "Add pilot tic scan and completion-gate scan"`

## Task 4: Blinding anonymizer

Depends on: none

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-blind.py`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/blind-strip.txt`

**Interfaces:**
- `pilot-blind.py <stock.jsonl> <variant.jsonl> --seed <int> --task-id <id> [--out <dir>] [--config-dir <path> ...]` or `--selftest`. `--out` defaults to `pilot/blind/<task-id>/`.
- Renders each transcript to plain reading text (assistant `text` blocks and a one-line `[tool: <name>]` marker per `tool_use`, in order), strips every identifying string, assigns A/B per pair, and writes:
  `<dir>/A.txt`, `<dir>/B.txt` (anonymized reading transcripts),
  `<dir>/key.sealed.json` (`{"A": "stock"|"variant", "B": ..., "seed": <int>, "task_id": <id>}`).
- Identifying strings stripped: every non-comment line of `pilot/blind-strip.txt` (case-insensitive); each exact `--config-dir <path>` passed in (so whatever the two isolated config dirs are actually named gets stripped, not a hardcoded `/cfg` literal); and any `claude-*` model token (replaced with `MODEL`). `strip(text, patterns)` always applies the `claude-*`->`MODEL` rule, then removes each pattern in `patterns`.
- Per-pair A/B orientation: `assign(seed, task_id)` maps A/B deterministically from `int(sha256(f"{seed}:{task_id}").hexdigest(),16) % 2` (hashlib, not the salted builtin `hash`), so each pair's side varies independently and the rater cannot learn a fixed "A is always the variant"; the brief's "left/right randomized per pair" holds across the study.
- Exports: `render(records) -> str`, `strip(text, patterns) -> str`, `assign(seed, task_id) -> dict`.

**Acceptance check:** `python3 scripts/pilot-blind.py --selftest` exits 0 `[executed-check]`

- [ ] Step 1: Write `pilot/blind-strip.txt`:

  ```
  # pack-identifying strings that would reveal which pane is the variant.
  # Specific tells only - never bare common words like "lean"/"stock" that
  # substring-strip would mangle inside ordinary prose (e.g. "clean").
  lobotomized
  lobotomized-claude-code
  system-prompts-opus-4-8
  fixing-smartass-opus-5
  ```

- [ ] Step 2: Write the failing test as inline `--selftest` (this test code IS the spec):

  ```python
  def selftest():
      stock = [{"type": "assistant", "message": {"content": [
          {"type": "text", "text": "run at /tmp/x-stock-cfg/settings.json model claude-opus-4-8"},
          {"type": "tool_use", "name": "Bash"}]}}]
      patterns = ["lobotomized", "/tmp/x-stock-cfg"]        # config-dir path passed as an explicit token
      r = render(stock)
      assert "[tool: Bash]" in r, r
      s = strip(r, patterns)
      assert "/tmp/x-stock-cfg" not in s and "claude-opus-4-8" not in s and "MODEL" in s, s
      assert assign(3, "t01") == assign(3, "t01"), "deterministic per pair"
      sides = {assign(3, f"t{i}")["A"] for i in range(12)}
      assert sides == {"stock", "variant"}, sides           # orientation varies across pairs, not fixed
      print("selftest: ok")
  ```

  The `--selftest` exercises `render`, `strip`, and `assign` directly; the CLI write path (the three output files) is exercised by Step 5.

- [ ] Step 3: Run `--selftest`; expect FAIL (functions undefined). `[executed-check]`
- [ ] Step 4: Implement `render`, `strip`, `assign`, and `main`. `main` loads both JSONL files, renders, strips (patterns = strip-file lines + each `--config-dir` path; the `claude-*`->`MODEL` rule is always applied inside `strip`), assigns per pair from `assign(--seed, --task-id)`, and writes the three output files under `--out` (default `pilot/blind/<task-id>/`). `key.sealed.json` records the mapping, seed, and task_id.
- [ ] Step 5: Run `--selftest` (expect `selftest: ok`), then a CLI smoke over two real transcripts and assert the three files exist and neither leaks the pack tell:
  `T1=$(ls -t ~/.claude/projects/*/*.jsonl|sed -n 1p); T2=$(ls -t ~/.claude/projects/*/*.jsonl|sed -n 2p); D=$(mktemp -d); python3 scripts/pilot-blind.py "$T1" "$T2" --seed 3 --task-id smoke --out "$D" --config-dir /tmp && test -f "$D/A.txt" -a -f "$D/B.txt" -a -f "$D/key.sealed.json" && ! grep -qi 'lobotomized' "$D/A.txt" "$D/B.txt"`. `[executed-check]`
- [ ] Step 6: Commit - `git add scripts/pilot-blind.py pilot/blind-strip.txt && git commit -m "Add pilot blinding anonymizer"`

## Task 5: Task-mining scaffold

Depends on: none

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-mine-tasks.py`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/tasks/TEMPLATE/prompt.md`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/tasks/TEMPLATE/checklist.md`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/tasks/README.md`

**Interfaces:**
- `pilot-mine-tasks.py <jsonl-glob-or-dir> [--host <label>] [--no-text]|--selftest`: scans session transcripts and emits, to stdout, one JSON line per candidate task: `{"source_session": str, "prompt_text": str, "human_turns": [str], "turns": int, "stratum": "quick"|"multi", "host": str}`. `prompt_text` is the first NON-WRAPPER human `text` block in the session - a text is a wrapper if it starts with `<` (covers `<command-...>`, `<system-reminder>`, `<local-command-caveat>`) or with `Caveat:`; sessions with no non-wrapper human text are skipped. `human_turns` is the ordered list of every non-wrapper human text in the session, so a `multi` task can be replayed by re-firing the identical human script to both panes (the first user record alone does not reproduce a multi-turn session). `turns` = assistant-record count; `stratum` by the <=5 rule. Sessions with no assistant turn are skipped. `host` is `--host <label>` if given, else `socket.gethostname()`.
- `--no-text` emits only `{source_session, turns, stratum, host}` (no `prompt_text`, no `human_turns`), for shipping session-shape counts off a data-governed host without moving any raw prompt content.
- Cross-host use (host-agnostic by design; the script is pure Python 3 with no repo dependency): raw day-job prompt text never transits. Run the miner ON the day-job host, and curate plus scrub text-bearing candidates THERE, bringing back only the finished, already-scrubbed task packets; optionally ship a `--no-text` `candidates.jsonl` back for sizing and stratification. This widens external validity (the day-job task distribution is the real workload the molt verdict optimizes for, where this host skews to meta-tooling) without ever moving donor, advancement, or PII text off its governed host.
- Exports: `candidates(sessions: dict[str, list[dict]], host: str, redact: bool = False) -> list[dict]`.
- The template files are the packet Jeremy fills per curated task: `prompt.md` (the replayable task text, plus the full `human_turns` script for a `multi` task), `checklist.md` (evidence checklist, each item names its evidence), and an `input/` dir Jeremy snapshots per task (documented in `README.md`).

**Acceptance check:** `python3 scripts/pilot-mine-tasks.py --selftest && python3 scripts/pilot-mine-tasks.py ~/.claude/projects | head -1 | python3 -c 'import sys,json; d=json.loads(sys.stdin.readline()); assert set(["source_session","prompt_text","human_turns","turns","stratum","host"])==set(d) and d["stratum"] in ("quick","multi") and not d["prompt_text"].startswith("<"); print("ok")'` exits 0 `[executed-check]`

- [ ] Step 1: Write `pilot/tasks/README.md` (the curation checkpoint procedure): run the miner, read candidates, pick 12 per pass stratified quick/multi, and for each create `pilot/tasks/<id>/` with `prompt.md` (including the full `human_turns` script for a `multi` task, replayed identically to both panes), `checklist.md`, and an `input/` snapshot (a `git init` fixture or a tarball of the minimal files the task touches, reset before each pane). State that curation and input-snapshotting are human steps. Document the scrub gate as a hard curation step and the PII control: `pilot/tasks/` is gitignored by default (Global constraints), a packet enters git only by an explicit `git add -f` after scrubbing, and anything touching donor, advancement, or PII data is scrubbed or synthesized first. Document the cross-host rule: for the day-job host, run the miner and curate plus scrub THERE and bring back only finished scrubbed packets; raw text never transits, and only a `--no-text` `candidates.jsonl` (shape counts, no prompt content) may be shipped for sizing.
- [ ] Step 2: Write `pilot/tasks/TEMPLATE/prompt.md` and `pilot/tasks/TEMPLATE/checklist.md`:

  ```markdown
  <!-- prompt.md -->
  # Task <id> (<quick|multi>)
  ## Turn 1
  <the exact replayable request text>
  <!-- multi only: one "## Turn N" block per later human turn, from human_turns,
       replayed identically to both panes so only the SP differs -->
  ```

  ```markdown
  <!-- checklist.md -->
  # Evidence checklist for task <id>
  - [ ] <done-condition> - evidence: <the exact command/output that proves it>
  ```

- [ ] Step 3: Write the failing test as inline `--selftest` (this test code IS the spec):

  ```python
  def selftest():
      U = lambda t: {"type": "user", "message": {"content": [{"type": "text", "text": t}]}}
      A = lambda t: {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}
      sessions = {
          "s-quick": [U("<command-name>/x</command-name>"), U("fix the typo"), A("done")],
          "s-multi": [U("build X"), A("."), U("now add Y")] + [A(".")] * 5,
          "s-empty": [U("hi")],
      }
      out = {c["source_session"]: c for c in candidates(sessions, "rit-wsl")}
      assert out["s-quick"]["prompt_text"] == "fix the typo", out       # leading <command-...> wrapper skipped
      assert out["s-quick"]["stratum"] == "quick" and out["s-quick"]["turns"] == 1, out
      assert out["s-multi"]["stratum"] == "multi" and out["s-multi"]["turns"] == 6, out
      assert out["s-multi"]["human_turns"] == ["build X", "now add Y"], out   # full script for replay
      assert out["s-quick"]["host"] == "rit-wsl", out                   # host stamp is attributable
      assert "s-empty" not in out, out                                  # no assistant turn, skipped
      red = {c["source_session"]: c for c in candidates(sessions, "rit-wsl", redact=True)}
      assert "prompt_text" not in red["s-quick"] and "human_turns" not in red["s-quick"], red
      print("selftest: ok")
  ```

- [ ] Step 4: Run `--selftest`; expect FAIL. `[executed-check]`
- [ ] Step 5: Implement `candidates` and `main`. `main` accepts a dir (walk `*.jsonl`) or a glob, resolves `host` from `--host` or `socket.gethostname()` and `redact` from `--no-text`, loads each session's records, calls `candidates(sessions, host, redact)`, prints one JSON line each.
- [ ] Step 6: Run `--selftest` (expect `selftest: ok`) and the real-scan acceptance; expect `ok`. `[executed-check]`
- [ ] Step 7: Commit - `git add scripts/pilot-mine-tasks.py pilot/tasks && git commit -m "Add pilot task-mining scaffold and packet templates"`

## Task 6: Held-up verdict and pairwise-log schema

Depends on: Task 2

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-verdict.py`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/pass1/README.md`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/pass2/README.md`

**Interfaces:**
- Consumes: the metrics-record schema from Task 2 (`scripts/pilot-metrics.py` `extract`, carrying `task_id`), and a pairwise log.
- Pairwise-log schema (`pilot/passN/pairwise.jsonl`, one row per pair, filled by human rating at pass time):
  `{"task_id": str, "order": "A=stock"|"A=variant", "rating": "A"|"B"|"tie", "variant_won": true|false|null, "reason": str, "rated_at": str}`.
  `order` records the per-pair side the blinding actually assigned (`assign(seed, task_id)`, Task 4), so orientation is auditable; `variant_won` is derived from `order` plus `rating` (null on tie).
- `pilot-verdict.py <pairwise.jsonl> <metrics-stock.jsonl> <metrics-variant.jsonl>` where each metrics file is one Task-2 metrics-record per line carrying `task_id`. Verdict JOINS the three inputs on `task_id`, never on line order, and raises `ValueError("join error: task_id <x> ...")` on any id that is missing from a side or duplicated (so a mis-ordered file fails loud instead of silently comparing task A's stock against task B's variant). Emits JSON:
  `behavior` ({wins:int, losses:int, ties:int, ratio:float|null, pass:bool} - pass iff `wins >= 2*losses` and `wins+losses >= behavior_floor` where `behavior_floor = 6`),
  `cache_write` ({stock_median:float, variant_median:float, pass:bool} - pass iff variant median < stock median on `cache_write_turn1`),
  `guard` ({breaches:[{metric,stock_median,variant_median}], pass:bool} - over `input_tokens, output_tokens, cache_creation_input_tokens, turns` only; `cache_read_input_tokens` is NOT guarded because more reuse is cheaper and better; a breach is variant median > 1.10*stock median; pass iff no breach),
  `compaction` ({n_both:int, stock_median:float|null, variant_median:float|null, status:"variant_later"|"not_later"|"insufficient"} - a NON-BLOCKING secondary computed over pairs that compacted on both sides; `status` is `insufficient` when `n_both < 4`, else `variant_later`/`not_later` by median; it is reported as supporting evidence and never gates `held_up`),
  `verdict` ("held_up"|"not_held_up"|"inconclusive").
  Verdict rule: `not_held_up` if `guard.pass` is false OR (`behavior.wins+losses >= behavior_floor` and `behavior.ratio < 1.0`); `held_up` if `behavior.pass and cache_write.pass and guard.pass` (compaction is reported, not required, so a decisive behavior+cache+guard result is reachable even when no task compacted); else `inconclusive`.
- `--validate-log <pairwise.jsonl>`: exit 0 iff every row matches the schema and there are exactly 12 rows, else non-zero listing the offending row.
- Exports: `verdict(pairwise, stock, variant) -> dict`, `median(xs) -> float`.

**Acceptance check:** `python3 scripts/pilot-verdict.py --selftest` exits 0 `[executed-check]`

- [ ] Step 1: Write `pilot/pass1/README.md` and `pilot/pass2/README.md` documenting the pairwise-log schema above (including that `order` records the per-pair blinding side for audit), the model pins for that pass (pass 1: `claude-opus-4-8` both panes; pass 2: old `claude-opus-4-8`, new the 2.1.241 default resolved at staging), and that the 12 rows are filled by the human blind-rating checkpoint, never by a script.
- [ ] Step 2: Write the failing test as inline `--selftest` (this test code IS the spec):

  ```python
  def selftest():
      tids = [f"t{i}" for i in range(12)]
      def m(tid, cw, comp, out=100):
          return {"task_id": tid, "cache_write_turn1": cw, "compaction_turn": comp,
                  "input_tokens": 100, "output_tokens": out, "cache_read_input_tokens": 100,
                  "cache_creation_input_tokens": cw, "turns": 10}
      # variant 6:2 among non-ties, cache-write down, NO task compacted (comp=None everywhere)
      pairwise = [{"task_id": t, "variant_won": w}
                  for t, w in zip(tids, [True]*6 + [False]*2 + [None]*4)]
      stock =   [m(t, 2000, None) for t in tids]
      variant = [m(t, 1200, None) for t in tids]
      d = verdict(pairwise, stock, variant)
      assert d["behavior"]["pass"] and d["behavior"]["wins"] == 6 and d["behavior"]["losses"] == 2, d
      assert d["cache_write"]["pass"] and d["guard"]["pass"], d
      assert d["compaction"]["status"] == "insufficient", d      # 0 both-compacted, non-blocking
      assert d["verdict"] == "held_up", d                        # reachable WITHOUT compaction evidence
      # guard breach on output_tokens (20% worse) -> not_held_up
      v2 = [m(t, 1200, None, out=130) for t in tids]
      assert verdict(pairwise, stock, v2)["verdict"] == "not_held_up", "guard must veto"
      # more cache-read must NOT breach the guard (cheap reuse is good)
      vcr = [dict(m(t, 1200, None), cache_read_input_tokens=100000) for t in tids]
      assert verdict(pairwise, stock, vcr)["guard"]["pass"], "cache-read is not guarded"
      # thin behavior (2:1 but below floor) with clean guard -> inconclusive
      thin = [{"task_id": t, "variant_won": w} for t, w in zip(tids, [True, False] + [None]*10)]
      assert verdict(thin, stock, variant)["verdict"] == "inconclusive", "small N is inconclusive"
      # join error on a mismatched task_id, never a silent positional compare
      try:
          verdict(pairwise, stock[:-1] + [m("BADID", 1200, None)], variant); assert False
      except ValueError as e:
          assert "join error" in str(e), e
      print("selftest: ok")
  ```

- [ ] Step 3: Run `--selftest`; expect FAIL. `[executed-check]`
- [ ] Step 4: Implement `median`, `verdict`, `main`, and `--validate-log` against the contract. `main` loads the three JSONL files and prints `verdict(...)` as JSON.
- [ ] Step 5: Run `--selftest`; expect `selftest: ok`. `[executed-check]`
- [ ] Step 6: Validate-log path - write a 12-row well-formed sample to a temp file and assert `--validate-log` exits 0, then a 11-row file exits non-zero:
  `python3 -c 'import json;[print(json.dumps({"task_id":f"t{i}","order":"A=stock","rating":"A","variant_won":False,"reason":"x","rated_at":"2026-08-23"})) for i in range(12)]' > /tmp/pw.jsonl && python3 scripts/pilot-verdict.py --validate-log /tmp/pw.jsonl && { head -11 /tmp/pw.jsonl > /tmp/pw11.jsonl; ! python3 scripts/pilot-verdict.py --validate-log /tmp/pw11.jsonl; }`. `[executed-check]`
- [ ] Step 7: Commit - `git add scripts/pilot-verdict.py pilot/pass1/README.md pilot/pass2/README.md && git commit -m "Add pilot held-up verdict and pairwise-log schema"`

## Task 7: End-to-end dry-run tracer, run-book, gitignore, recipes

Depends on: Task 1, Task 2, Task 3, Task 4, Task 5, Task 6

**Files (exclusive ownership):**
- Create: `/Users/jjrdar/create/sys-prompts-cc/scripts/pilot-dryrun.sh`
- Create: `/Users/jjrdar/create/sys-prompts-cc/pilot/RUNBOOK.md`
- Modify: `/Users/jjrdar/create/sys-prompts-cc/.gitignore`
- Modify: `/Users/jjrdar/create/sys-prompts-cc/justfile`

**Interfaces:**
- Consumes: every Task 1-6 script.
- `pilot-dryrun.sh`: picks two real historical transcripts as a stand-in pair, runs the full instrument over them with zero spend - blind them, extract metrics for each, run tic and completion scans, synthesize a one-row pairwise log from a fixed seed, and compute a verdict - printing a sample read-out and exiting 0 on success. This is the composition tracer: it proves the scripts fit together on real data before any live pass.
- `justfile` gains `pilot-selftest` (runs every `--selftest` and `pilot-isolation-check.sh`) and `pilot-dryrun` (runs `pilot-dryrun.sh`).

**Acceptance check:** `just pilot-selftest && bash scripts/pilot-dryrun.sh | grep -q '^dryrun: ok'` exits 0 `[executed-check]`

- [ ] Step 1: Append to `.gitignore` (each on its own line): `pilot/**/*.jsonl`, `pilot/**/key.sealed.json`, `pilot/runs/`, and `pilot/tasks/`. This keeps transcripts and ledgers copied in at run time, the unblinding keys, and the PII-bearing task packets out of git; scrubbed packets enter only via an explicit `git add -f pilot/tasks/<id>` (Global constraints). Leave pilot scripts, schemas, templates, and READMEs tracked.
- [ ] Step 2: Write `pilot/RUNBOOK.md` - the human procedure for the staged live passes, referencing every script by path: seed two isolated config dirs (`pilot-seed-config.sh`) with the pinned models, snapshot the daily-install shared-state hash set, fire the 12 paired runs per pass (deferred to #8's herdr skeleton), blind each pair (`pilot-blind.py --task-id <id> --config-dir <the two seeded dirs>`), rate blind A/B/tie a day later into `pilot/passN/pairwise.jsonl`, route the GLM tie-break, extract metrics (`pilot-metrics.py --task-id <id>` per run) and scans per run, compute the verdict (`pilot-verdict.py`), re-snapshot and diff the shared-state hash set, and present the read-out for Jeremy's go/no-go. Name the pass-2 model-ID resolution and the first-pass live-isolation confirmation as explicit checkpoints. Spend and resumability: state a per-stage hard cap (default ~$60, above the ~$30-60/stage estimate) and an abort trigger if projected spend exceeds it; make each pair a self-contained resumable unit - persist that pair's two transcripts and two metrics records keyed by `task_id` as it completes, so a crash resumes at pair k+1 rather than re-firing the stage (double spend); and state that an inconclusive stage triggers a check-in, not a conclusion.
- [ ] Step 3: Write `pilot-dryrun.sh` (`set -euo pipefail`). Contract: pick `T1`, `T2` = the two newest transcripts; `D=$(mktemp -d)`; `python3 scripts/pilot-blind.py "$T1" "$T2" --seed 2 --task-id dry01 --out "$D/blind" --config-dir /tmp`; `python3 scripts/pilot-metrics.py "$T1" --task-id dry01 > "$D/m-stock.jsonl"`; `python3 scripts/pilot-metrics.py "$T2" --task-id dry01 > "$D/m-variant.jsonl"`; `python3 scripts/pilot-tic-scan.py "$T1" >/dev/null`; `python3 scripts/pilot-completion-scan.py "$T1" >/dev/null`; synthesize a 1-row pairwise log (`{"task_id":"dry01","variant_won":true}`) to `"$D/pw.jsonl"`; `python3 scripts/pilot-verdict.py "$D/pw.jsonl" "$D/m-stock.jsonl" "$D/m-variant.jsonl"` (joins on the shared `dry01`); on all commands succeeding, `echo "dryrun: ok"`.
- [ ] Step 4: Write the `justfile` recipes (append; do not touch the existing `pin-target` recipe):

  ```just
  # Run every pilot instrument self-test plus the isolation harness (zero spend).
  pilot-selftest:
      #!/usr/bin/env bash
      set -euo pipefail
      for s in metrics tic-scan completion-scan blind mine-tasks verdict; do
          python3 scripts/pilot-$s.py --selftest
      done
      bash scripts/pilot-isolation-check.sh

  # Prove the instrument composes end to end over two real historical transcripts (zero spend).
  pilot-dryrun:
      bash scripts/pilot-dryrun.sh
  ```

- [ ] Step 5: Run `just pilot-selftest`; expect every `selftest: ok` and `isolation: ok`. `[executed-check]`
- [ ] Step 6: Run the acceptance check; expect exit 0 and `dryrun: ok`. `[executed-check]`
- [ ] Step 7: Confirm gitignore - `test "$(git check-ignore pilot/runs/x pilot/tasks/t01/prompt.md pilot/pass1/run.jsonl pilot/blind/t01/key.sealed.json | wc -l | tr -d ' ')" = 4` (all four PII, transcript, and key paths ignored), while `git status --porcelain pilot | grep -q .` still shows the tracked scripts/schemas/READMEs (not everything ignored). `[executed-check]`
- [ ] Step 8: Commit - `git add scripts/pilot-dryrun.sh pilot/RUNBOOK.md .gitignore justfile && git commit -m "Wire pilot instrument end to end with dry-run tracer and recipes"`

## Notes on resolved brief questions

The brief's seven "Open questions for planning" resolve here:

- **Reproducible task replay** - each curated task is a self-contained packet under `pilot/tasks/<id>/` (`prompt.md` carrying the full `human_turns` script so a multi-turn task replays identically to both panes, `checklist.md`, an `input/` snapshot reset before each pane); the miner scaffolds candidates (host-stamped, wrapper-text skipped, curated and scrubbed on the host that owns the data), Jeremy snapshots input state at curation (Task 5 checkpoint).
- **Pairwise-log and metric-ledger format** - committed newline-delimited JSON under `pilot/passN/`, schema in Task 6, matching the repo's provenance-JSON style.
- **Ringer-routed vs herdr recipes for firing runs** - firing is #8's herdr skeleton; this plan's run-book (Task 7) names it as the downstream mechanism and does not build it. The GLM second judge routes through the zai tools at rating time.
- **Blinding mechanics** - `pilot-blind.py` strips the actual `--config-dir` paths, model IDs, and the `pilot/blind-strip.txt` pack tells, assigns A/B per pair via `assign(seed, task_id)` so orientation varies per pair, and seals the key separately under a gitignored path (Task 4).
- **Tic-scan phrase source** - `pilot/tic-phrases.txt`, seeded from the operator's CLAUDE.md ban list plus the opus-slop briefing, with em dash and section symbol counted separately (Task 3).
- **Seeding identical settings including --model** - `pilot-seed-config.sh` writes a lean settings blob with the explicit model and the curated CLAUDE.md subset into each isolated config dir (Task 1); the isolation harness proves shared state is untouched.
- **Pass-2 new-side model ID** - resolved from the pinned 2.1.241 binary at pass-2 staging (a checkpoint), never hardcoded, since #11 has landed but the default ID is read at run time.
```