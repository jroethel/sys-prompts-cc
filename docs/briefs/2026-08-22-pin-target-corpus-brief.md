# Brief: pin the target - current Claude Code plus its normalized corpus (ticket #11)

Ticket: https://github.com/jroethel/sys-prompts-cc/issues/11
Shaped 2026-08-22 in a /loop-brainstorm sitting.
One-Minute Test verdict: ONE AGENT (one goal, tool actions, inspectable done state, checking far cheaper than producing).
This brief doubles as the run card for the AFK session that executes it.

## Outcome

The upgrade effort gets its concrete target: the current Claude Code binary pinned on disk beside the live 2.1.204, with both versions' prompt corpora extracted and normalized into directly comparable form.
Presupposition verdict: the ticket's "next to the 2.1.204 one" presupposed a normalized 2.1.204 corpus that does not exist - nothing normalized is on disk anywhere, and the normalizer itself is only a recipe in docs/research/diff-surface.md.
Decision: producing the normalized 2.1.204 corpus is folded into this ticket, so done means both sides of the future diff exist.

## End artifact

The old-vs-new SP diff that feeds the first molt check - the evidence base for the confident upgrade from pinned 2.1.204 to current Claude Code (the effort's first domino).
This ticket delivers the diff's two inputs and the pinned binary the molt check will run against.
It also leaves behind the first re-runnable piece of the molt check itself: a version-parameterized pin pipeline, so every future CC bump re-runs a command instead of a procedure.

## Done looks like

With V standing for the version npm reports as latest at run time (2.1.241 as of 2026-08-22):

- `readlink ~/.local/bin/claude` still resolves to `.../versions/2.1.204` - the live install and symlink are untouched.
- `~/.local/share/claude/versions/<V> --version` prints V.
- Ticket #11 carries a comment with V, the new binary's SHA-256, and both corpora's prompt counts.
- `corpora/2.1.204/` and `corpora/<V>/` exist in this repo's working tree, gitignored, in identical normalized layouts.
- `diff -rq corpora/2.1.204 corpora/<V>` runs and reports content differences - the two corpora are comparable with standard tools, no further processing needed.
- `just pin-target <version>` (recipe name illustrative) runs the acquire-extract-normalize pipeline for any version - the recurring molt step is a command, parameterized by version.
- The new binary was never launched beyond `--version` - the live install's shared config state was never opened by the new version.

## Assets and options

- Native version layout at `~/.local/share/claude/versions/` - chosen as the new binary's home, side by side with 2.1.204 and 2.1.174.
- tweakcc-fixed 2.7.37 (installed) - chosen as the extractor, per the #3-validated route (its prompt-data cache is ground truth).
- Normalizer recipe in docs/research/diff-surface.md reproduction notes - chosen, becomes the effort's first committed script.
- `strings` on the new binary - chosen as the independent validator for extraction spot-checks, per #3.
- npm registry - chosen as the version oracle for "latest at run time", undecided as binary source (see Open questions).
- just (justfile recipes) - chosen as the pipeline's command interface, seeding the justfile that #8 will extend into launch recipes.
- herdr - declined for this ticket, it is the interactive work plane for the #8 compare loop and an AFK extraction has no collaborative session in it.
- Jeremy's CLAUDE.md - declined as-is for test launches, a curated minimal subset per test profile is parked to #7/#8 so the shipped SP is what gets exercised.
- Piebald repo (~/repos/claude-code-system-prompts, tracks 2.1.240) - declined as corpus source (26% id-coverage) and declined as cross-check (strings validation suffices).
- Lobotomized repo (~/repos/lobotomized-claude-code) - declined for this ticket, it is a downstream consumer of the diff, not an input.

## Approach

Chosen: native side-by-side binary plus tweakcc cache extraction plus one shared normalizer run over both versions' caches, packaged as a version-parameterized pipeline command rather than a one-off procedure.
This is the route #3 validated end to end, the normalizer running twice is free once it exists, and evaluating SPs as the CLI changes is a recurring task, so re-runnability is a requirement, not a nicety.

Considered and rejected:

- npm JS package as the target artifact - not the distribution Jeremy actually runs (live install is the native Mach-O), so the pin would not be like-for-like with 2.1.204 or with the binary the molt check must bless.
- Corpus-only from public catalogs (Piebald or lobotomized) - fails the outcome, which requires a pinned runnable binary, and Piebald covers only 26% of the binary's prompt segments.

## Success criteria

1. `[executed-check]` `readlink ~/.local/bin/claude` resolves to `.../versions/2.1.204` after the run completes.
2. `[executed-check]` The new binary at `~/.local/share/claude/versions/<V>` prints V for `--version`, where V equals `npm view @anthropic-ai/claude-code version` at run start.
3. `[executed-check]` Ticket #11 comment records V, the binary's SHA-256, and both corpora's prompt counts (1537 expected on the 2.1.204 side).
4. `[executed-check]` `corpora/2.1.204/` and `corpora/<V>/` exist, `git status` shows neither (gitignored), and `diff -rq` between them reports only content differences, never layout mismatches - both sides use the same file-naming scheme.
5. `[executed-check]` A sample of prompts from the new cache is verified verbatim against `strings -n 6` of the new binary - the #3 validation re-run against V.
6. `[executed-check]` `~/.tweakcc/config.json`, `systemPromptAppliedHashes.json`, `systemPromptOriginalHashes.json`, `~/.claude.json`, and `~/.claude/settings.json` are byte-identical before and after the run - the live install's patch state and shared config both survive.

7. `[executed-check]` Running the pipeline a second time for an already-pinned version completes and leaves that corpus byte-identical - the recurring molt step is proven re-runnable, not a one-off.

No `[judgment]` criteria - every criterion reformulated to a command shape.

## Seams

In blast-radius order, each independently checkable:

1. Acquire the new binary side by side - the only seam that touches the live install's neighborhood, checked by criteria 1 and 2.
2. Extract the new version's prompt cache - touches shared ~/.tweakcc state, checked by criteria 5 and 6.
3. Write the normalizer and run it over both caches - pure local compute, checked by criterion 4.
4. Record the pin on the ticket - checked by criterion 3.

The pipeline command wraps seams 1-3, parameterized by version, and criterion 7 checks the wrap.

## Known vs guessed

Verified this session:

- npm latest is 2.1.241, live binary reports 2.1.204, symlink resolves to 2.1.204.
- The live 2.1.204 is patched: `~/.tweakcc/config.json` has `changesApplied: true`, modified 2026-08-23T02:28Z (the lobotomized re-apply, post-handoff).
- `~/.tweakcc/prompt-data-cache/prompts-2.1.204.json` exists (2.8 MB), no normalized corpus exists anywhere, tweakcc-fixed is 2.7.37.

Believed, unchecked:

- The 2.1.204 cache content reflects the stock binary - it was rewritten at 22:27 local, one minute before the 22:28 apply, while the binary was still restored.
  If wrong, the old side of the diff is contaminated; planning should include the cheap re-validation of a cache sample against verified-stock bytes (npm tarball or ~/.tweakcc/native-binary.backup).
- tweakcc-fixed can extract from a binary at a non-live path without disturbing its live-install state.
  If wrong, the extraction seam needs an isolation strategy before the run.
- `--version` on a fresh CC binary does not write shared config state.
  If wrong, criterion 6 catches it, and the cheap fix is running the version check under a throwaway config home (planning decides).

Guessed:

- A per-version download of the native binary exists without running the official installer.
  If wrong, the installer route needs an explicit symlink guard, which criterion 1 would catch.

## Parking lot

All four items were routed 2026-08-22 as comments on existing tickets (#9, map #1, #8, #7) in lieu of issue graduation - kept below as the record.

- Ticket #9 stock-hash premise changed by the lobotomized re-apply, the live binary can no longer be read for a stock hash
  Restart context: source stock 2.1.204 bytes from the npm tarball or ~/.tweakcc/native-binary.backup, then verify the backup against a second route before trusting it
- Map decision line for #2 is stale again, it still says the live install is stock
  Restart context: post a one-line state-change comment on the map (issue #1) and on #9 recording the 2026-08-23T02:28Z re-apply
- Isolated launch profiles so side-by-side versions never share live config state when they run
  Restart context: requirement on #8 launch recipes and the molt check, candidate mechanism is the CLAUDE_CONFIG_DIR env var (believed from training, verify against current docs), each test profile gets its own config home
- Curated minimal CLAUDE.md subset per test profile for SP evaluation
  Restart context: Jeremy wants benchmark runs to carry some but not much of his CLAUDE.md so the shipped SP is what gets exercised, feeds #7 as a controlled variable and #8 as a recipe profile ingredient

## Out of scope

- The old-vs-new diff itself - this ticket delivers its inputs, the diff belongs downstream with the molt work (#10).
- Ticket #9's work, beyond the parked premise note.
- Any write to the live install, the version symlink, or the applied patch state.
- Committing corpus text to the public repo - corpora stay gitignored.
- Anything model-side (the new Opus-generation model) - this ticket pins the CC binary and corpus only.
- Launching the new version at all (beyond `--version`) - test launches and their isolation profiles belong to #8's recipes, parked above.
- Re-running the #3 fidelity measurements against the new corpus.

## Open questions for planning

- Acquisition mechanism for the native binary at a pinned side-by-side path: direct per-version download vs the official installer with a symlink guard.
- How to point tweakcc-fixed at the side-by-side binary without disturbing its live-install state: config isolation vs backup-and-restore.
- On-disk layout inside `corpora/<version>/` and where the normalizer script lives (scripts/ is the natural home).
- Recipe naming and justfile layout - this seeds the justfile #8 extends, so the names should survive that growth.
- Whether the 2.1.204 normalized corpus derives from the existing cache or from a fresh extraction of verified-stock bytes (resolves the believed-unchecked bin).
- Sample size for the strings spot-check (five traced end to end sufficed for #3).
