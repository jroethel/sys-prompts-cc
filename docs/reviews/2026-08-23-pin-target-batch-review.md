# Batch review - pin-target corpus run - 2026-08-23

Run: /loop-drive docs/plans/2026-08-22-pin-target-corpus-plan.md (autonomy: auto, session-only).
Gate journal, chronological. BATCH and DEFAULT entries are the review obligation; ASK and STOP entries are record-only.

## 1. BATCH - topology lean: single sequential agent, no wave machinery

- Decision: route the plan as ONE AGENT (sonnet, Agent tool, in-place branch `pin-target-2.1.241`) executing Tasks 1-4 sequentially; Task 5 staged for the human. No worktrees, no per-wave manifests.
- Rationale: only Tasks 1+2 could parallelize (both small); Tasks 2-4 write shared `$HOME` state (`~/.local/share/claude/versions/`, `~/.tweakcc/` cache) that worktrees cannot isolate; ringer transport is blocked (sandbox is workspace-write, `allow_full_access = false`, and Task 3 needs mid-flight continuation at the naming gate). Plan's absolute paths target the main checkout.
- Reversal: scoped re-run with the wave topology (2-worker wave 1, then sequential) - a taste re-run, since the lean is judgment.

## 2. BATCH - spec amendment, Task 3 step 2.3a assert

- Decision: replace "clone's released CC target >= V (parse the newest `data/prompts/prompts-*.json`)" with: assert `~/repos/tweakcc-fixed/dist/nativeInstallation-*.mjs` exists AND clone HEAD == origin/main after fetch. Version correctness stays enforced by `extract-clijs.mjs` (extracted version must equal V) and Task 3 step 7's strings spot-check.
- Rationale: verified 2026-08-23 - newest published prompts file is 2.1.239, skrabe raw URL 404s on 2.1.241, clone already at origin (f911cdf). The assert as written is unsatisfiable for exactly the version this ticket pins; the plan's own evidence section (skrabe two behind) contradicts it. Edit is confined to one step of one task, changes nothing Task 3 produces, under 15 lines.
- Reversal: cheap - restore the original assert text in the spec and re-run Task 3 once skrabe publishes 2.1.241 (rung 2 would then hit anyway).

## 3. DEFAULT - Step 7 execution-details question auto-taken

- Decision: launch immediately; dashboard/dry-run equivalents already executed live (capability probe, env premise checks: cache present, symlink at 2.1.204, 2.1.241 binary absent, just/node/pnpm/gh present, dist module present).
- Rationale: gate class is DEFAULT with declared default "nothing selected means launch immediately"; user instruction "only stop if necessary, otherwise get it all done".
- Reversal: n/a - informational; details are recorded here and in the run transcript.

## 4. STOP - duplicate prompt ids in the 2.1.204 corpus (resolved live)

- Decision: worker blocked on Task 1's acceptance check - 1537 records but only 1425 unique ids, so file-per-id silently dropped 112 records. Orchestrator re-derived the numbers independently: 57 of 58 duplicate ids carry byte-identical normalized content (dedupe is correct); exactly 1 id (`tool-description-showonboardingrolepicker`) has 2 distinct contents. Human chose content-suffix disambiguation: `<id>__<sha8>.md` per distinct variant, expected 2.1.204 file count 1426 (1367 unique ids + 57 deduped + 2 variants). Spec amended in the plan doc and committed on the branch (9efc68b); acceptance counts updated in Tasks 1, 4, 5 and the global constraint.
- Rationale: the 1537 figure traces to diff-surface.md's record count, conflated with file count; last-writer-wins would silently lose a real variant, defeating the diff-fidelity purpose. Edit touches a global constraint and Task 1's produced contract, hence STOP class, asked live.
- Reversal: n/a - resolved live (and cheap anyway: revert 9efc68b).

## 5. ASK - Task 3 naming gate (resolved live)

- Decision: first 2.1.241 extraction exited 3 with exactly 3 anonymous prompts (5072 extracted, consistent with seeds 2.1.238=4854, 2.1.239=5069). Orchestrator verified the anonymous list on disk against the worker's report (shas matched). Human approved all three proposed names: `error-manifest-version-mismatch`, `tool-description-max-thinking-tokens-and-display`, `ui-interpolated-pair-middle-dot` (the last a declared low-confidence descriptive placeholder, renameable in the committed map).
- Rationale: plan-defined human checkpoint; names persist to the committed content-hash-keyed map, so this sign-off is permanent and idempotent across hosts.
- Reversal: n/a - resolved live.

## 6. Worker deviation noted (no gate fired)

- `promptExtractor.js` needs `@babel/parser` (transitive under pnpm); worker set `NODE_PATH` to pnpm's virtual store on the extractor invocation only, commented in `scripts/acquire-corpus.sh`, no tweakcc-fixed files modified. Accepted at the gate as a contained, documented workaround.

## 7. Resume state (quota resilience, updated live)

- Run position: Tasks 1-2 committed on branch `pin-target-2.1.241` (551557c, 25ddb2f) plus spec amendment 9efc68b; Task 3 past the naming gate (3 names approved, being written to config/prompt-names.json); worker executing Task 3 steps 6-8 then Task 4. Task 5 remains: orchestrator stages the gh comment, human fires it.
- Auto-resume policy (user-set 2026-08-23): a worker stopped by quota is resumed at 1:30 (session-limit reset); a 40-min background timer in the orchestrating session triggers the check.
- 1:30: policy fired. Worker had died on quota mid-Task 3 step 7 (strings spot-check; its sampler had picked multi-line fragments that cannot match line-based strings output). Resumed with reconcile-from-disk instructions: verify step 6 evidence from git/files (guard snapshot in /tmp may be lost - re-verify, never skip silently), redo step 7 with single-line fragments, then step 8 and Task 4.
- Fresh-session resume prompt (if the orchestrating session itself dies): "Resume /loop-drive of docs/plans/2026-08-22-pin-target-corpus-plan.md at the gate. Read this journal and git log on branch pin-target-2.1.241 for actual state; relaunch (never resume) any half-done task with the plan as spec; validate Tasks 1-4 by re-running each acceptance check, merge to main, stage the Task 5 gh command for the human."

## 8. Pre-flight note (no gate fired)

- Dirty tree (BACKLOG.md, ISSUES.md, scripts/gen-mirrors.sh, scripts/tracker.sh, WAYFINDER.md) is disjoint from every task's ownership list; no worktrees are used, so the committed-state STOP does not apply. Worker is barred from adding or touching those files; commits add only the files each task's commit step names.

## 9. Gate - Tasks 1-4 validated, merged (orchestrator)

- Independent re-runs, all pass: Task 1 acceptance (selftest ok, 1426 files, exit 0), Task 2 acceptance (verified sha `1495eb7c...`, `--version` ok, symlink unchanged at 2.1.204), Task 4 end-to-end (`just pin-target` both versions, diff ran exit 1, corpora ignored). Diff audit vs main: exactly the 7 owned files plus the orchestrator's plan amendment; pre-existing dirty files untouched. Worker deviations accepted: NODE_PATH pnpm workaround (commented, contained), ASCII single-line strings fragments (unicode stored escaped in the binary), pycache cleanup of its own artifact.
- Observation: warm re-runs rewrite `corpora-provenance/2.1.241.json` to rung `cache` - per-run provenance is by design; the first resolution (rung local, tweakcc-fixed f911cdf) is preserved in the worker report, this journal, and the ticket comment.
- Guard result: five must-not-touch files byte-identical across a bracketed full extraction run; observed `~/.claude.json` drift root-caused to the live Claude Code session's own state flushes, not the pipeline.
- BATCH (skip noted): the final-wave advisory /loop-review was not run - it belongs to the wave machinery this run skipped at the Step 0 ONE-AGENT lean (journal entry 1); per-unit executed checks plus this gate's independent re-runs carried validation. Reversal: run `/loop-review f230e0b` from main at any time.
- Provenance dir (worker open question 1) committed at the gate with this journal, per the plan's global constraint; no task owned it.

## 10. ASK - Task 5 fired by the human (run closed)

- Decision: human fired the staged gh comment (issuecomment-5384490291); orchestrator ran the acceptance grep, comment present with the verified sha. All 5 tasks done; chain complete.
- Rationale: plan-defined human checkpoint, outbound to a shared system.
- Reversal: n/a - resolved live.
- Left open by choice: local main unpushed (4+ commits ahead of origin), advisory `/loop-review f230e0b` available on demand.
