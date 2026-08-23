# Handoff: wayfinder charting, SP compare/measure/tailor effort

Session date: 2026-08-22.
Effort: wayfinder map for comparing, measuring, and tailoring Claude Code system prompts.
Map (canonical artifact): https://github.com/jroethel/sys-prompts-cc/issues/1

## Where things stand

The map is charted and five tickets are resolved; all remaining AFK research is done.
The frontier is now human-gated: two grillings, two AFK tasks, one blocked prototype.

| #   | Ticket                                   | State                            |
| --- | ---                                      | ---                              |
| 2   | Swap mechanics                           | Closed; corrected, see below     |
| 3   | Diff surface                             | Closed                           |
| 4   | Measurement methodology                  | Closed                           |
| 5   | Landscape                                | Closed                           |
| 6   | First domino                             | Closed; reshaped the destination |
| 7   | Metrics and benchmark tasks              | Open grilling; unblocked         |
| 8   | Pilot skeleton (just + herdr)            | Open prototype; blocked by 7     |
| 9   | Baseline hygiene (pin binaries)          | Open task; AFK-safe              |
| 10  | Upgrade and drift policy (the molt core) | Open grilling                    |
| 11  | Pin the target (new CC + corpus)         | Open task; AFK                   |

Decisions live on their tickets; the map's Decisions-so-far section is the index.
Research findings: docs/research/ (swap-mechanics, diff-surface, measurement-methodology, landscape).

## Load-bearing facts for a fresh session

- The live install at ~/.local/share/claude/versions/2.1.204 is STOCK, byte-verified after an earlier wrong inference.
  Jeremy's `npx tweakcc-fixed --restore` ran 2026-08-22 20:29:47; all appliedHashes are null; the ~/.tweakcc/system-prompts symlink only selects a future --apply.
- Full per-launch SP swap works today via --system-prompt-file off one stock binary; tool descriptions and reminders need pre-patched side-by-side binary copies.
- Piebald catalog at its v2.1.204 tag: 99% prose-identical where id-aligned (394 of 399), but covers only 26% of the binary's 1537 prompts.
- Lobotomized pack: zero stale-behind overrides against 2.1.204; comparison is only honest after the extraction normalizer (raw reads 41%).
- Destination's driving application (first domino): a confident upgrade to current CC plus the new Opus-generation model, and a repeatable molt check for every future upgrade.
- Molt inspiration: loop-molt skill plus ~/create/research/archive/molt-cycle-1-kickoff-prompt.md.
- Wayfinder tickets are excluded from ISSUES.md and BACKLOG.md by design (gen-mirrors.sh line 5); the map is their index.
- Wayfinder rule: at most one non-research ticket resolution per session.

## Next actions, in recommended order

1. AFK session: work #11 (side-by-side install of current CC, extract corpus) and #9 (record stock hash, build patched variant copy); both are parallel-safe and never touch the live install or symlink.
2. /loop-brainstorm sitting with Jeremy for #7 (metrics: benchmark tasks, satisfaction rubric, run counts); this unblocks #8.
3. /loop-brainstorm sitting for #10 (molt policy: triggers, what re-runs, what alerts).
4. Prototype session for #8 (justfile + herdr skeleton to react to).
5. Frontier empty: hand the destination to /loop-plan.

## Resume prompt (paste into a fresh session)

/wayfinder https://github.com/jroethel/sys-prompts-cc/issues/1
Read docs/handoffs/2026-08-22-wayfinder-sp-charting.md first.
Work the next frontier ticket per the handoff's recommended order unless I name one.
