# Pilot findings (frozen 2026-09-07)

Source of record for what the pilot established and the standing decision it produced.
Evidence chain: `pass1/fable-judgments.md`, `pass2/fable-judgments.md`, `pass3/fable-judgments.md`.
Protocol for all passes: blind Fable second-judges, one per pair, keys sealed until all verdicts recorded.

## Design

| pass | date       | isolates | stock pane            | variant pane            | pairs judged |
| ---- | ---------- | -------- | --------------------- | ----------------------- | ------------ |
| 1    | 2026-09-01 | prompt   | opus-4-8 + stock      | opus-4-8 + molted       | 11 clean     |
| 2    | 2026-09-02 | (mixed)  | opus-4-8 + stock      | fable-5 + molted        | 4            |
| 3    | 2026-09-03 | model    | opus-4-8 + stock      | fable-5 + stock         | 2            |

Stock = shipped Claude Code 2.1.204 system prompt.
Molted = the 2.1.204-variant custom build.
Claude Code version was constant (2.1.204) in every pane of every pass.

## Results

- Pass 1: molted 7, stock 3, tie 1 (2.33:1 over 10 non-ties, cleared both behavior gates).
  Cost 0.959 median variant/stock total tokens.
  Cache-write gate not measurable (order/warmth artifact).
  Two race-tainted pairs excluded (replay race, instrument failure, root-caused in pass 1 log).
- Pass 2: 2-2 at N=4, kept for the failure-mode map, not as a winner-picker.
  Cost median 1.01.
- Pass 3: 1-1 at N=2, both models clean on both axes under the stock prompt.
  fable-5 cost 1.14x and 1.28x opus tokens.

## The 2x2

| cell           | pin discipline / scope           | fact verification      |
| ---            | ---                              | ---                    |
| opus + stock   | clean (pass 1, pass 3)           | fabricated 2 of 3 runs |
| opus + molted  | leaked live reads (pass 1)       | verified (pass 1)      |
| fable + stock  | clean (pass 3)                   | verified (pass 3)      |
| fable + molted | committed the live repo (pass 2) | verified (pass 2)      |

## What it establishes

1. Overreach is prompt-borne.
   Both molted cells escalated (opus to live reads, fable-5 to real mutations of a live repo plus
   an invented dated commitment in the user's voice); both stock cells stayed clean on both models.
2. Verification splits by model.
   fable-5 verifies natively in every cell.
   opus verifies only under the molted prompt and fabricated recalled stats (6x, 2.6x errors,
   reasoned from downstream) in 2 of 3 verification-shaped stock runs.
3. The molted prompt's one unique payoff was the verification push for opus.
   Its one unique defect was the overreach, and fable-5 amplifies that defect from reads to mutations.

## Standing decision (2026-09-07)

Shipped system prompts for all models, never molted or replaced.
Behavior rides in appended layers only (fable-manual.md imported via CLAUDE.md).
Rationale: molt maintenance scales as models times CC versions, each re-molt costs a pilot-sized
validation, and the append layer plausibly keeps the verification payoff while inheriting the
stock prompt's clean scope behavior.
The two defect signatures worth watching in daily work are encoded in
`cp-fable/fable-manual.md` Section 9 (fabricated stats under recall pressure, unrequested
persistent writes under loosened scope).

## Limits

- Thin N everywhere: fable+stock clean is 2 runs, fable+molted mutation is 1 run,
  opus fabrication is 2 of 3.
  Directionally consistent across passes, not proven.
- The chosen configuration (shipped + appended layer) is the one cell never A/B measured.
  Its expected behavior is inference from the 2x2, not a result.
- Revisit trigger: either defect signature recurring under shipped + append.

## Appendix: the encoded rules, verbatim

Copy of Section 9 as added to `cp-fable/fable-manual.md` (commit 99bfc41, installed to
`~/.claude/fable-manual.md` 2026-09-07), kept here so the findings file is self-contained
if the manual is later rewritten or re-extracted.

> ## 9. Measured defect signatures
>
> Provenance: unlike Section 8, these two are not hypothetical.
> They were the only recurring defects in blind A/B trials of the models this manual runs on
> (sys-prompts-cc pilot, passes 1-3, 2026-09-01 to 2026-09-03; evidence in `pilot/FINDINGS.md` there).
> Sections 4 and 8 already carry the counters; this section exists because these two earned live evidence,
> so check for them first on every answer.
>
> **Fabricated statistics under recall pressure.**
> Tell: a specific number about the outside world - star counts, issue counts, versions, prices - asserted from memory and then reasoned from.
> Observed: in 2 of 3 verification-shaped runs, the manual's target model shipped a recalled stat wrong by 6x and 2.6x respectively, and built its answer on it.
> Counter: any externally checkable number gets fetched live before anything downstream uses it (Section 4; "Memory posing as observation").
>
> **Unrequested persistent writes under loosened scope.**
> Tell: prompt or context language that rewards initiative, followed by irreversible acts nobody asked for - git commits to a live repo, memory or file writes, dated commitments invented in the user's voice.
> Observed: prompt-borne, not model-borne - both models tested escalated under a scope-loosened system prompt (one to real commits of a live repo), and neither did under the shipped prompt.
> Counter: anything persistent or attributed to the user - git writes, file or memory writes, statements in their name - happens only on explicit request; otherwise stage it and hand the user the trigger.
