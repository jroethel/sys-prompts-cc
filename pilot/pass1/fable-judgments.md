# Pass 1: Fable second-judge blind verdicts (2026-09-01)

Second-judge signal only, not the human rating log.
Eight Fable subagents, one per pair, each read the task packet (prompt.md + checklist.md) and judged
A.txt vs B.txt blind.
No key.sealed.json was opened and no raw transcript under pilot/runs was read, so every verdict below
is still auditable against its pair's sealed key.
A/B labels are per-pair blinding assignments (assign(seed, task_id)), so verdicts must be joined
through each pair's key to derive variant_won; never aggregate raw A/B counts across pairs.

## Auth-dead pairs (both panes captured only "Not logged in"), cleared and re-fired

Batch R1 re-fired and judged 2026-09-01: terminal-mux-comparison, supervisor-review-rating-pushback,
vaultwise-reddit-scraper-decision (verdicts below).
Batch R2 re-fired and judged 2026-09-01: triage-table-accept-recall,
model-intel-refresh-skill-worker (verdicts below). All 13 pairs are now captured and judged.

## Verdicts (unsealed 2026-09-01, after all eight blind verdicts were recorded)

| task_id                          | verdict | order     | winner  | capture              |
| ---                              | ---     | ---       | ---     | ---                  |
| loop-stack-vs-research-eval      | B       | A=stock   | variant | ok                   |
| spec-axis-review-subagent        | tie     | A=stock   | tie     | ok                   |
| self-manual-privacy-architecture | B       | A=stock   | variant | ok                   |
| changelog-research-interrupted   | A       | A=stock   | stock   | ok                   |
| substack-resource-resync-worker  | A       | A=variant | variant | stock side truncated |
| loop-brainstorm-partner          | A       | A=variant | variant | ok                   |
| wayfinder-roadmap-blast-radius   | A       | A=stock   | stock   | ok                   |
| molt-cycle-brief4-control-plane  | A       | A=stock   | stock   | variant side truncated |
| supervisor-review-rating-pushback | A      | A=stock   | stock   | variant side truncated |
| vaultwise-reddit-scraper-decision | B      | A=stock   | variant | ok                   |
| terminal-mux-comparison          | A       | A=variant | variant | ok                   |

R1 pairs judged blind 2026-09-01 by the same protocol, keys unsealed after all three verdicts.
supervisor's variant side ends with the Turn 4 user prompt and no assistant output (verified in the
raw transcript): the 10-minute impatient-user budget expired silently, same class as substack/molt.

- supervisor-review-rating-pushback: A completes all four turns including the strongest moment in
  either file (caught the disagree-to-agree flip in the pared-down draft, fixed two real grammar
  defects); B never engages Turn 4.
- vaultwise-reddit-scraper-decision: B grounds its in-repo recommendation in the youtube.py adapter
  pattern that exists on disk and refutes A's "nothing to wrap" dichotomy; A's answer body is full
  of em dashes.
- terminal-mux-comparison: live spot-check decided it - A's cmux facts match the real repo (26.7k
  stars, GPL-3.0), B's are wrong by 6x and mis-hedge the license.

| task_id                          | verdict | order   | winner  | capture |
| ---                              | ---     | ---     | ---     | ---     |
| triage-table-accept-recall       | B       | A=stock | variant | ok      |
| model-intel-refresh-skill-worker | A       | A=stock | stock   | ok      |

- triage-table-accept-recall: both accurate and checklist-clean, but B verified "finished product"
  by a second route (run-state closure, real commits) and ended on the answer while A closed with
  unrequested offers.
- model-intel-refresh-skill-worker: both met the contract, but A ran the checklist's dry-run
  inertness check that B skipped, and B used em dashes three times.

## Final tally (corrected 2026-09-02 after root-causing the truncations)

Root cause correction: the supervisor and molt variant-side truncations were a replay race
(stale-idle wait returning instantly on the final turn; see FIRING-PLAN.md and the await_answer
fix in pilot-pair.sh), NOT the impatient-user budget. They are instrument failures and their
verdicts are tainted. substack's stock-side truncation was a genuine budget interrupt and counts.

- Standing tally excluding the two race-tainted pairs (supervisor unfired, molt tainted):
  variant 7, stock 3, tie 1 - 2.33:1 over 10 non-ties, clears both behavior gates.

## Decision (2026-09-02)

Jeremy closed pass 1 on the standing tally: THE VARIANT TAKES IT.
The supervisor re-fire was waived and molt stays excluded; no further pass-1 spend.
Cost stood at 0.959 median variant/stock total tokens (passes), turn-1 cache write inconclusive
(order/warmth artifact, see above).

Cost at 13 pairs: median variant/stock total tokens 0.959, inside the 10 percent bound.
Turn-1 cache write: variant smaller in 9 of 13 pairs, but by tiny margins where smaller, while
the cross-side medians invert (stock 2,806 vs variant 14,842) because four pairs (changelog,
molt, substack, supervisor) show one side starting ~2k warm and the other ~15-20k cold.
A fresh pane's turn-1 cache write should be its full cold prefix, so the ~2k values look like
API-side prefix-cache warmth from firing order, not prompt size (inferred, not verified);
treat the cache-write gate as not measurable from this pass rather than passed or failed,
and judge it by pilot-verdict.py's definition if the formal verdict is ever run.
Against the verdict gates: 5 clean non-ties is under the 6 minimum, and 3:2 is under the 2:1
behavior ratio, so pass 1 does not formally hold up the variant at this N regardless of leaning.

## Reasons (one line each, judges' words condensed)

- loop-stack-vs-research-eval: B grounded itself first-hand and verified claims by second routes
  (live changelog, ledger file date); A delegated all reading and shipped mostly unverified
  recollection plus em dashes in its own text.
- spec-axis-review-subagent: both sides hit all six done-conditions with near-identical findings,
  structure, and restraint; cosmetic differences only.
- self-manual-privacy-architecture: both pass items 1-4 and 6, but only B's end state delivers the
  settled two-skill design (split, rename, genericization all landed); A also ships an em dash.
- changelog-research-interrupted: A wrote the ~3,900-word cited note and honored the interrupt
  protocol; B spent five turns asking clarifying questions after an unambiguous request and
  produced nothing.
- substack-resource-resync-worker: A delivers the full output contract including Open questions;
  B follows the same implementation path but the capture ends mid-verification with no summary
  (B-invalid, likely turn budget).
- loop-brainstorm-partner: both sensibly went off-script after finding all ten items closed, but A
  executed the explicit Turn 6 instructions (reopened #28, crisp status table) while B deferred the
  issue creation and stalled three turns asking the user for facts; B also used emoji checkmarks.
- wayfinder-roadmap-blast-radius: A stayed inside the pinned inputs and found the real migration
  work (gen-mirrors.sh, tracker.sh children verb); B read the live repo's post-session commits and
  told the user the change was "already done", contradicting the pin.
- molt-cycle-brief4-control-plane: A completed the full mandate (compiled plan, rubix Lens B at
  Fable, glm-5.2 re-run, stop for approval); B stalled at pre-plan questions and its capture ends
  with no turn-5 response (B-invalid).

## Cross-pair patterns the judges surfaced

- Em dashes in the losing or dinged side came up in four pairs; both prompts leak them in narration
  even when the deliverable file is grepped clean.
- The most common losing behavior was stalling on clarifying questions after an unambiguous
  delegation (changelog B, loop-brainstorm B, molt B) versus executing and reporting.
- Grounding discipline decided the two research-shaped pairs in opposite directions: whichever side
  verified against the pinned or live source of record won (loop-stack B, wayfinder A).

## Same patterns after unsealing

- Em-dash leaks in narration: stock in three pairs (loop-stack, self-manual, changelog), variant in
  one (substack), so the variant is cleaner but not clean.
- Stalling-on-clarifying-questions losses split across prompts (variant in changelog and molt,
  stock in loop-brainstorm), so it reads as a model behavior, not a prompt signature.
- Neither prompt owns the grounding wins: variant won loop-stack on verification, stock won
  wayfinder on pin discipline (the variant side contaminated itself with live-repo future state).
