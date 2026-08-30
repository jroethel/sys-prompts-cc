# Handoff: pass 1 instrument hardened, pair 1 done, firing plan live

Session date: 2026-08-29/30.
Consumes: docs/handoffs/2026-08-24-upgrade-path-orientation.md (its step 1, curation, was already
done 2026-08-25; its step 5, the molt-report commit plus #18 title fix to 365, was done this session).

## Where things stand

Pass 1 is FIRING. Pair 1 of 13 (`loop-stack-vs-research-eval`) is captured and blinded.
The remaining 12 run without any Claude session via `just pilot-batch`; progress via `just pilot-status`.
The plan, batching, scheduling, and failure handling: `pilot/pass1/FIRING-PLAN.md` (the one file to read).

## What this session changed (all committed, 9e22f49..d0f8db4)

- Instrument aligned to the curated 13 (was 12): verdict validation, docs.
- Variant binary rebuilt with the opus-4-8 pack flavor (byte-verified); fable-5 binary kept;
  build procedure documented in pilot/HERDR-LAYOUT.md.
- Pane gates seeded past: onboarding, login (.credentials.json file fallback - the keychain
  service name is config-dir-derived), folder trust (realpath keys), permission prompts (bypass).
- herdr integration: HERDR_AGENT=claude hint, agent-registration polling, @-mention popup
  stall recovery, side-level resume, pane cleanup on success.
- Isolation hardened after two real breaches: panes auto-updated the shared install
  (launcher restored to 2.1.204, updater disables now seeded, launcher symlink in the guard)
  and wrote to ~/create/pcs (deny wall: no Write/Edit under /Users; Bash tripwire warns).
- Auto-memory wiped between pairs; usage-limit tripwire drops poisoned captures;
  blind script no longer echoes the assignment (pair 1's leaked once - note at rating).
- Scrub gitignore fixed (raw mine-work files were committable); mirrors regenerated (#18 = 365).

## Facts a fresh session needs

- Live install: PATCHED 2.1.204 (lobo fable-5, Jeremy's own 2026-08-22 re-apply), NOT stock -
  see the 2026-08-29 addendum in docs/research/swap-mechanics.md. 2.1.251 sits inert in versions/.
- Spend is Max quota, not API dollars: pair 1 = ~$42-equivalent; the $60/pass cap is
  reinterpreted as quota pacing (Jeremy's accepted decision) - batches sized per 5-hour window.
- Pane configs: /tmp/sp-pass1-{stock,variant}; credentials copies expire with Jeremy's login
  (~2026-09-03); re-run the two pilot-seed-config.sh commands after renewing login.
- Filed loop-stack-session #52: repos need a reliable resume pointer (this handoff sprawl is the evidence).

## Next actions

1. Jeremy fires batches per pilot/pass1/FIRING-PLAN.md (7 windows; batch 7 strictly alone).
2. All 13 at `4/4 blinded` -> rate a day later (13 rows), validate, verdict, re-snapshot: RUNBOOK stages 3-4.
3. Pass 1 verdict decides #18's fate (handoff 2026-08-24, step 4).

## Resume prompt (paste into a fresh session)

Read docs/handoffs/2026-08-30-pass1-firing.md and pilot/pass1/FIRING-PLAN.md, then run
`just pilot-status`. Work whatever the status and plan say is next unless I name something.
