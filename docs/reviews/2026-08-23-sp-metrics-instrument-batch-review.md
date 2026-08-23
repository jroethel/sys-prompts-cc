# Batch review - sp-metrics-instrument loop-drive run - 2026-08-23

Gate journal for the autonomous run. ASK/STOP entries are record-only (resolved live).
BATCH/DEFAULT entries are the review obligation: accept or reverse at the end-of-chain checkpoint.

## 1. ASK (record-only) - loop-auto first set
- Decision: autonomy mode `auto`, session-only (not persisted as repo default).
- Rationale: first `set` in this repo requires the persist question.
- Reversal: n/a - resolved live.

## 2. ASK (record-only) - execution approval
- Decision: launch the compiled orchestration plan (`docs/plans/2026-08-23-sp-metrics-instrument-plan_loop.md`).
- Rationale: drafting and executing are separate approvals; this was the last ASK before autonomy.
- Reversal: n/a - resolved live.

## 3. STOP (record-only) - pre-flight dirty tree
- Decision: commit the dirty files as-is on main before branching
  (BACKLOG.md, ISSUES.md, scripts/gen-mirrors.sh, scripts/tracker.sh, WAYFINDER.md).
- Rationale: worktrees branch from committed state; stash risks loss on session death.
- Reversal: n/a - resolved live (commit reversible via `git revert`).

## 4. STOP (record-only) - receipts home
- Decision: open one umbrella GitHub issue for AGENT STATUS receipts.
- Rationale: durable run-state on the ticket, per P11.
- Reversal: n/a - resolved live.

## 5. BATCH - T5 manifest check SIGPIPE fix
- Decision: in the wave-1 manifest (T5 check), replaced `miner | head -1 | python -c` with
  a temp-file capture (`> /tmp/sp-cands.jsonl` then `head -1`), during the pin review.
- Rationale: under `set -o pipefail` the miner takes SIGPIPE when `head` exits early,
  turning a correct run into a false CHECK FAIL.
- Reversal: revert the edit in `_loop.md` Section 8 (cheap, single hunk).

## 6. DEFAULT - Step 7 execution-details ask auto-taken
- Decision: skipped the "See execution details before I launch?" question; launched with the
  default (no dashboard/dry-run/watch-points selection). Lint and environment checks still run
  as pre-flight regardless.
- Rationale: the gate is DEFAULT-class; under auto it auto-takes the declared default.
- Reversal: cheap - ask for the dashboard, watch points, or a dry-run print at any time.
