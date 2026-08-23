# Brief: SP metrics and benchmark tasks (wayfinder #7)

Date: 2026-08-22.
Ticket: https://github.com/jroethel/sys-prompts-cc/issues/7 (grilling, consumes the #4 methodology menu).
Approved by Jeremy 2026-08-22 in the /loop-brainstorm sitting.

## Outcome

An operational definition of "better" for Claude Code SP variants: benchmark task set, judging design, run counts, thresholds, and claim scope, decided and recorded so the #8 pilot implements without further grilling.
Presupposition verdict: the ticket assumed the #4 menu was decision-ready, and it was.
Every decision below draws from that menu plus two facts checked fresh this session: token cost computed from Jeremy's own session history, and install isolation checked against the docs.

## End artifact

The first molt verdict: an evidence-backed go/no-go on moving from pinned 2.1.204 to current Claude Code and the new Opus-generation model, produced by the #8 pilot this spec unblocks.
Pass 1 additionally settles the lobotomized-claims verdict.

## Done looks like

This brief committed, #7 closed with the decision summary, the map's Decisions-so-far updated, #8 unblocked.
The wayfinder one-resolution-per-session budget goes to closing #7.

## The decided design

| Decision    | Choice                                                                                   |
| ---         | ---                                                                                      |
| Comparisons | Pass 1: stock vs lobotomized on 2.1.204, one variable, shakes down the harness.          |
|             | Pass 2: pinned 2.1.204 vs current CC plus new Opus-generation model, the molt question.  |
| Model       | Pass 1: claude-opus-4-8 in both panes, pinned by exact ID (the pack is tuned for it).    |
|             | Pass 2: old side claude-opus-4-8, new side the current CC Opus-generation default,       |
|             | ID pinned when #11 lands. Never Fable (worker ban), never bare model aliases.            |
| Task set    | 12 tasks per pass, mined from real session transcripts, curated by Jeremy,               |
|             | informally stratified quick vs multi-turn.                                               |
| Done gate   | Per-task checklist authored at mining time, every item names its evidence.               |
|             | A transcript scan flags completion claims lacking a matching executed check.             |
| Judging     | Jeremy: one blind pairwise A/B/tie per pair, tone and satisfaction folded, one-line      |
|             | reason, left/right randomized, rating at least a day after any variant work.             |
|             | Second judge: non-Claude family (GLM), order-swapped, tie-break signal only.             |
| Run count   | 12 pairs per pass, both passes.                                                          |
|             | An effect needing more investigation triggers a check-in with a recommendation           |
|             | before any extra spend.                                                                  |
| Held up     | Behavior: lobotomized wins at least 2:1 among non-ties.                                  |
|             | Mechanics: cache-write smaller on turn one, auto-compaction measurably later.            |
|             | Guard: no metric worse than stock by more than 10% median, else not held up at this N.   |
| Claim scope | Cache-write, compaction headroom, behavior.                                              |
|             | TTFT parked: no public instrument reports it.                                            |
| Secondaries | Tic scan, verbosity, permission-seeking, tool-call profile, diff churn, error/retry.     |
|             | Error/retry is primary only for tool-description variants and pass-2 regressions.        |
| Isolation   | Every non-pinned run launches under its own CLAUDE_CONFIG_DIR with an explicit --model.  |
|             | The daily install never runs under one, its config hash-checked before and after.        |

## Assets and options

Chosen: herdr as the pilot work plane, the fixing-smartass-opus-5 justfile as the #8 seed, the lobotomized pack as the pass-1 variant, session JSONL plus /cost plus /context as instruments, GLM via the zai tools as second judge, tweakcc-fixed for variant binaries, ringer for routing live runs.
Declined: promptfoo (parked as a fragment-regression idea), OTel telemetry (already the observability fog item on the map), Piebald corpus (diff-surface work, not measurement).
Constraint: token cost, roughly $30-60 per stage at API rates, shaped the 12-pair cap.

## Approach

Chosen: composed-primitives paired pilot, full multi-turn sessions paired per task, blind side-by-side, mechanical metrics from existing surfaces, human blind pairwise judgment with a non-Claude second judge.
Alternatives considered: a promptfoo fragment harness (wrong unit, single-turn assertions cannot capture multi-turn agentic behavior) and an OTel telemetry backplane (infrastructure cost with no qualitative capture for a one-person pilot).
Rationale: no surveyed tool measures an agent harness SP across full sessions, and every needed primitive already exists locally.

## Success criteria

- The pairwise log holds 12 rows per pass, each with A/B/tie and a one-line reason `[executed-check]`
- The held-up verdict is computable by script from the log and JSONL against the thresholds above `[executed-check]`
- Every counted pair passed its evidence checklist and the scan shows no unmatched completion claims `[executed-check]`
- Tic scan and secondary metrics are reported per run from transcripts alone `[executed-check]`
- The daily install's config is byte-identical before and after the pilot `[executed-check]`
- #7 closed with the decision summary and the map decision line added `[executed-check]`
- Jeremy accepts the pass read-out as decision-grade for the molt call `[judgment]` (reformulation attempted, the go/no-go is genuinely his)

## Seams

1. Isolation proof: one throwaway run under an isolated config dir, hash-compare shared state (highest blast radius, first).
2. Task mining and curation with checklists (zero new spend).
3. Metric extractors proven on historical transcripts (zero new spend).
4. Pass 1 stage and read-out.
5. Pass 2 stage and read-out.

## Known vs guessed

Verified this session: median session token profile (n=30 random transcripts: 29 turns, 28k output, 61k input, 136k cache-write, 1.29M cache-read), ~/.claude and ~/.claude.json shared across versions, CLAUDE_CONFIG_DIR partial isolation, lobotomized pack tuned for Opus 4.8, settings.json defaults to claude-fable-5.
Believed-unchecked: Opus API pricing $5/$25 per MTok and cache multipliers (if wrong the cost table scales, the staging decision survives), GLM judge handles transcript-length input.
Guessed: mined tasks average 0.5-1.0x a median session (cost scales proportionally if wrong), and 12 pairs can read a large effect (a deliberate power cut, an inconclusive stage means check-in, not conclusion).

## Parking lot

- Measure time-to-first-token via a client wrapper or OTel first-chunk timestamps
  Restart context: no public Claude Code surface reports TTFT, see docs/research/measurement-methodology.md sections 2 and 7.
- Fragment regression harness on promptfoo for isolated SP fragments and tool descriptions
  Restart context: research section 6, single-turn assertions fit fragments, not full sessions.
- Second human rater to break blinding collapse
  Restart context: research section 9, needed only if results must travel beyond Jeremy's own decision.
- Full-paranoia install isolation via a separate macOS user or container
  Restart context: docs do not guarantee CLAUDE_CONFIG_DIR isolates plugin caches, checked 2026-08-22.

## Out of scope

Pilot skeleton architecture (#8), molt policy triggers and cadence (#10), domain-tailored packs, Piebald coverage work, claude.ai chat surfaces.

## Open questions for planning

- Reproducible task replay: how each mined task's repo state is snapshotted per run.
- Pairwise-log and metric-ledger location and file format.
- Ringer-routed vs plain herdr recipes for firing the paired runs.
- Blinding mechanics: how variant identity is stripped from transcripts before rating.
- Tic-scan phrase list source (CLAUDE.md ban list plus the opus-slop research).
- Seeding identical settings, including explicit --model, into each isolated config dir.
- Exact new-side model ID for pass 2, pinned when #11 lands.
