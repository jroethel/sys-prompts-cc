# Roadmap

_Living file; edit in place._

## Active stream: compare, measure, and tailor Claude Code system prompts

Wayfinder effort; the map at https://github.com/jroethel/sys-prompts-cc/issues/1 is the source of truth.
This section is a hand-maintained snapshot as of 2026-08-22; when it disagrees with the map, the map wins.
Pending loop-stack-session#43, wayfinder items may later render here automatically.

Destination: a working capacity to compare, measure, and tailor Claude Code system prompts, where "SP" spans
everything changeable at runtime (replace/append flags, tweakcc-style binary patches, reminders, tool descriptions).
Driving application (the first domino): a confident upgrade from pinned 2.1.204 to current Claude Code and the
new Opus-generation model, leaving behind a repeatable molt check for every future upgrade.

### Wayfinder items

| #   | Item                                        | Type      | State  | Depends on   |
| --- | ---                                         | ---       | ---    | ---          |
| 1   | Map: the effort's index                     | map       | open   | -            |
| 2   | Swap mechanics of runtime SP levers         | research  | closed | -            |
| 3   | Diff surface: shipped vs override packs     | research  | closed | -            |
| 4   | Measurement methodology                     | research  | closed | -            |
| 5   | Landscape: discourse and market             | research  | closed | -            |
| 6   | First domino (Jeremy's recording)           | grilling  | closed | -            |
| 7   | Metrics and benchmark tasks                 | grilling  | closed | #4 (closed)  |
| 8   | Pilot skeleton: just recipes plus herdr     | prototype | open   | #2, #7       |
| 9   | Baseline hygiene: pin verified binaries     | task      | open   | -            |
| 10  | Upgrade and drift policy (the molt core)    | grilling  | open   | -            |
| 11  | Pin the target: current CC plus its corpus  | task      | closed | -            |

### Path forward

1. AFK session: #11 installs current Claude Code side by side and extracts its normalized prompt corpus; #9 records the stock 2.1.204 hash and builds a patched variant copy; both are parallel-safe and never touch the live install.
2. /loop-brainstorm sitting for #10: decide the molt policy, meaning what re-runs on a version bump, what auto-realigns, and what demands review.
3. Prototype session for #8: a throwaway justfile plus herdr compare-loop skeleton to react to; #7's decisions are recorded in docs/briefs/2026-08-22-sp-metrics-benchmarks-brief.md.
4. Frontier empty: hand the destination to /loop-plan.

### Beyond the frontier (fog, in scope but not yet ticketed)

- Domain-tailored SP packs (engineering-focused vs content/design-focused Claude Code).
- Peer-agents seeded by persona and domain space; jroethel/arscontexta is the candidate seeder, research required.
- Observability framework and operational backplane for the peer-agents; pointers to evaluate: open-engine, viv (Twitter project/app/company), Jaye's rubric; hangs on the peer-agents item above.
- Productization of the capability as a service or product offer.
