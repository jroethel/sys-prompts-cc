# Handoff: upgrade-path orientation, #18 parked, #19 filed

Session date: 2026-08-24.
Effort: wayfinder SP compare/measure/tailor effort; this session was orientation plus tracker cleanup, no code.
Map (canonical artifact): https://github.com/jroethel/sys-prompts-cc/issues/1

## Where things stand

The molt pipeline (#10 policy work) ran its first real molt and opened #18 with 368 findings.
This session established that acting on #18 is premature and parked it behind the pilot's Pass 1.
The real blocker for the whole upgrade path is Task 5: curating the 12 pilot tasks. The instrument is built; no tasks are curated.

| #   | Item                                        | State this session                          |
| --- | ---                                         | ---                                         |
| 18  | Molt review (lobo 2.1.204 to 2.1.241)       | Parked with a comment; 0 of 365 resolved    |
| 19  | Stock-vs-stock upgrade digest (need a-2)    | Filed new (`wayfinder:research`)            |
| 8   | Pilot skeleton                              | Closed; instrument built                    |
| 16  | SP metrics instrument build                 | Closed; instrument built                    |

## Key facts for a fresh session

- The molt (#18) and the pilot's "Pass 2" are different artifacts. The molt is a static text diff (override pack vs stock at two versions), zero live runs. Pass 2 is a live A/B benchmark. Do not conflate them; the "too many dimensions" concern is a Pass 2 issue, never a molt issue.
- Pass 1 = the 12 curated tasks, stock SP vs lobotomized SP, both panes `claude-opus-4-8`, both on 2.1.204. One variable: the system prompt. This IS "the dozen lobotomized tests."
- Pass 2 (as originally defined) = current install vs fresh out-of-box, three variables at once (version + SP + model). It cannot attribute cause; treat it as a rough "upgrade at all" sniff, not an impact measurement.
- Pass 1 is independent of #18 (it runs on 2.1.204 where the pack is native). Pass 1 decides whether the pack is worth carrying forward; only if yes does #18 get resolved to realign the pack to 2.1.241.
- The clean new-stack SP test is missing and gated on #18: `{2.1.241 + new model + stock SP}` vs `{2.1.241 + new model + molted-lobo SP}`.
- Upgrade-need a-2 (what changed in stock CC 2.1.204 to 2.1.241, and what it does to my skills/workflows) is served by neither molt nor pilot. Filed as #19. Raw material exists: `corpora/2.1.204` and `corpora/2.1.241` (both read-only) support a stock diff; `/loop-molt` covers the skill-compatibility half.
- The "368 findings" on #18 = 365 review verdicts + 3 retro-check discrepancies. The committed report says 365; the working-tree regeneration (deterministic mode) drops the 3 retro lines.
- Curation (Task 5) is a human-judgment gate: `pilot-mine-tasks.py` surfaces candidates (zero spend), you pick 12 stratified quick/multi, build each `pilot/tasks/<id>/` (prompt.md, checklist.md, input/), and pass the hard scrub gate before any packet leaves its host. `pilot/tasks/` is gitignored.

## Uncommitted in the working tree (Jeremy fires the commit)

- `learning_guide.html` - two new dated Updates sections (2026-08-24).
- `ISSUES.md`, `BACKLOG.md`, `WAYFINDER.md` - regenerated mirrors (reflect #19).
- `docs/molt/lobo-opus-4-8.2.1.204-to-2.1.241.md`, `corpora-provenance/2.1.241.json` - molt report regeneration, carried over from before this session; committing makes the report read 365 and leaves the #18 title (368) stale.
- This handoff.

## Next actions, in recommended order

1. Curate the 12 tasks (Task 5) so Pass 1 can fire - the gate everything waits behind. See `pilot/tasks/README.md`.
2. Run Pass 1 (stock vs lobotomized on 2.1.204) - answers "does lobotomized work."
3. Work #19 in parallel - the stock-vs-stock upgrade digest, independent of everything above.
4. Only if Pass 1 says keep the pack: resolve #18, then run the clean new-stack SP test.
5. Decide the uncommitted molt report: commit and fix the #18 title to 365, or leave it.

## Resume prompt (paste into a fresh session)

Read docs/handoffs/2026-08-24-upgrade-path-orientation.md first, then learning_guide.html (2026-08-24 Updates).
The upgrade path is gated on curating the 12 pilot tasks (Task 5); #18 is parked behind Pass 1 and #19 is the parallel stock-diff track.
Work the next action per the handoff unless I name one.
