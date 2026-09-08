# Loop-stack conventions

This file is the doctrine half of the config pair: `config/repo-state.md` is the sibling machine surface
(keys and the Lanes table that parsers grep), and this file holds every mode-invariant convention.

## Config placement

| Artifact               | Audience            | Rendered / lives         | Holds                      |
| ---                    | ---                 | ---                      | ---                        |
| config/repo-state.md   | parsers (machine)   | repo-state.template.md   | keys + Lanes table         |
| config/conventions.md  | agents (doctrine)   | conventions.template.md  | this table + all doctrine  |
| config/context-map.md  | agents (orient)     | living; #34 policy       | one pointer per memory     |
| config/host.env        | this host (machine) | template; gitignored     | host-local env values      |
| config/ringer/         | ringer engine       | in place; no move        | host adapter + tmpl        |
| config/routing/        | routing (both)      | in place; no move        | model scoreboard           |

Any new config prose lands in `config/conventions.md` unless it is a line-anchored key a parser greps, which lands in `config/repo-state.md`.

## Committed keys

The committed per-repo autonomy default is a line-anchored `autonomy-default:` key in `config/repo-state.md` (value `pause` or `auto`).
The runtime value in `docs/chain-state.md` overrides it; `skills/loop-auto/loop-auto.sh default get|set|clear` reads, writes, and removes it.

The committed tracker backend is a line-anchored `tracker:` key in `config/repo-state.md` (value `github`, `gitlab`, or `local`).
Every loop-stack script reads it and obeys it; none infers the backend from `git remote`.
`scripts/tracker.sh mode get|set` reads and writes it; `skills/loop-setup/setup.sh` asks it once when the key is missing.

The committed Rubix-review autorun policy is a line-anchored `rubix-autorun:` key in `config/repo-state.md` (values `ask`, `off`, or `on`; absent means `ask`).
`ask` offers the optional Rubix review once, `on` runs it without asking, and `off` skips it silently.
`skills/loop-plan/SKILL.md` (Step 6) and `skills/loop-brainstorm/SKILL.md` read it; `config/repo-state.template.md` carries the default and value legend for new repos.
Mapping note: the brief specified a binary "off by default" meaning "offer, do not auto-run"; it shipped as this three-value key defaulting to `ask`, and the token `off` took on the new meaning "skip silently".

## File ownership

All root-level ALL-CAPS markdown files (`ROADMAP.md`, `ISSUES.md`, `BACKLOG.md`) belong to this convention; everything else it owns lives under `docs/` or `config/`, and this file is the definitive list.
The import sweep never offers the root project files `README.md`, `CLAUDE.md`, `AGENTS.md`, `PLAN.md`, `CHANGELOG.md`, `LICENSE.md`, `CONTRIBUTING.md`, nor anything under `docs/plans/`, `docs/briefs/`, `docs/issues/`, `docs/handoffs/`, `docs/spikes/`, `docs/sessions/`, `docs/reviews/`, or `docs/archive/`.
The `idea` label is the one load-bearing label.
Unlabeled issues (optionally `bug` or `refactor`) form the Issues lane; issues labeled `idea` form the Backlog lane.

## Doc filename tokens

Docs in the four lane directories carry tracker tokens in their filenames so a doc and its tracker item stay joined without opening the file.
The conformance regex:

```
^[0-9]{4}-[0-9]{2}-[0-9]{2}(\.[BIRW][0-9]+)*\.[a-z0-9-]+(_loop)?\.md$
```

A plan's orchestration companion carries `_loop` at the end of its slug (`...-plan_loop.md`); the regex's optional `(_loop)?` group admits it.

Token letter semantics:
- `I` = Issues-lane GitHub issue.
- `B` = Backlog-lane (idea label) GitHub issue.
- `R` = Roadmap item (stable assigned ID).
- `W` = Wayfinder-lane GitHub issue (map or child ticket, label `wayfinder:*`; excluded from Issues/Backlog by `scripts/gen-mirrors.sh`, so neither `I` nor `B` covers it).

Multi-token syntax: separate segments as in `.I6.I7.`, parsed as leading segments matching `[BIRW][0-9]+`.

Untokened docs keep the dot grammar without tokens; when the item is created the token is inserted (rename-on-log).
The rename-on-log trigger: `scripts/tracker.sh create` emits a one-line stderr reminder after printing the issue number to stdout.

R-tag rule: `ROADMAP.md` section headings carry `[R<n>]` tags; IDs are assigned monotonically (max existing + 1), never reused, and survive reorders.

Lane scope: the filename grammar applies to `docs/briefs/`, `docs/plans/`, `docs/handoffs/`, `docs/reviews/` top-level `*.md` only.
It does not apply to subdirs like `docs/reviews/unit-logs/`, nor to archive, memos, or root files.
Handoffs are `docs/handoffs/YYYY-MM-DD.<tokens>.<slug>.md`; batch reviews are `docs/reviews/YYYY-MM-DD.<tokens>.<slug>-batch-review.md`.

## Where I left off

"Where I left off" is the most recent of two candidates: the newest `docs/handoffs/` file and the newest commit on the working branch - whichever is fresher wins.
A handoff older than the latest commits is context, not the frontier: read it, then let `git log --oneline -5` and `git status` say what happened since.
When several threads are plausibly open (multiple recent handoffs or active branches), name them and ask which to resume rather than silently picking one.
A crashed session degrades to git, never to nothing.

## Session records

Every work session in a conforming repo opens a session card before its first substantive action and closes it before it ends.
`scripts/session-card.sh open "<title>" [<token>]` at the start, `scripts/session-card.sh log "<one line>"` after each meaningful step - at minimum once per commit, so the card's floor is the commit history's grain - and `scripts/session-card.sh close <status> "<why>" "<next>"` at the end.
Cards live in `docs/sessions/`, one per session, updated in place, and are committed with the work they record.
The terminal status vocabulary is closed: `done`, `blocked`, `handed-off`, `parked`, `aborted`.
A card opened and never closed is, by construction, a session that died mid-work; nothing is recorded at the moment of death.
The recording tax is capped at that one card: everything derivable comes from `scripts/take-stock.sh`, never from hand-recording.
Cards are plain markdown and harness-agnostic - no field names or assumes a particular agent harness, so any harness or a human can write and read them.
`docs/sessions/` is outside the filename-grammar lanes, so lint class f never scans it and the `-2` collision suffix is legal there.

## Handoff lifecycle

Every handoff carries a `## Next actions` section, one action per `- ` line; that list is the enumeration dispositions index into.
Consumption is per action: `scripts/handoff-log.sh disposition <handoff> <n> <executed|superseded> [note]` appends one line to the handoff's own `## Transitions` section.
The log is append-only and current state is always derived from it, never held in a mutable status field; "was this action already done" is answered from history.
`scripts/handoff-log.sh consume <handoff>` refuses while any action lacks a disposition, and the disposition that completes the set archives the handoff automatically, announced under archive rule 5.
`docs/handoffs/` therefore holds only live handoffs.
`scripts/lifecycle-lint.sh` class h enforces this for handoffs dated on or after the `lifecycle-lint-since:` key in `config/repo-state.md`; with the key absent the class does not run, and handoffs dated earlier are grandfathered.

## Agent status vocabulary

The `agent:` label family is the single status schema for tracker issues; this file is its only home.
Semantics are fixed: `agent:todo` (queued, no active claim), `agent:working` (claimed by a session holding a claim receipt), `agent:needs-input` (blocked on a human answer), `agent:review` (work offered for review), `agent:done` (evidence-gated completion, reachable only through `scripts/tracker.sh done`, never `label add`).
Exactly one status is active at a time; `tracker.sh status` swaps them, and the `agent:` family is orthogonal to the `idea` lane label.

## Archive and graduation rules

1. A plan is done when all items are complete (archive automatically), or when the remaining items are cleanly rewritten into a surviving plan (archive offered).
1a. A plan-set is archivable when it is superseded (a strictly newer live plan-set exists by date) and no OPEN issue links its topic stem; `scripts/lifecycle-lint.sh .` flags these (class a) plus orphaned briefs (b), open issues over archived plans (c), closed issues under live plans (d), and unresolved context-map pointers (e).
2. A brief archives when its plan archives; they travel together.
3. Abandoned work archives only when offered and accepted.
4. Parking-lot graduation is automatic at brief-commit time.
5. Every archive or graduation action is verbose: announce each moved file and each created issue with its number.
6. Declaring a task, run, or chain "done" runs `scripts/lifecycle-lint.sh .` first and resolves what it flags that the finished work clearly implies (archiving a superseded plan/brief, closing the roadmap row or issue, regenerating stale mirrors) in the same pass, under the same verbose-announce discipline as rule 5. A genuinely ambiguous finding (e.g. a mirror the human has uncommitted edits to) is asked about; it is never silently skipped, and never silently done without disclosure.
7. A handoff archives automatically when every action in its ## Next actions list carries a disposition; the move is announced under rule 5.

Graduated-item issue body template (label the issue `idea`):

```
<verbatim parking-lot prose from the brief>
---
Source brief:
Graduated: <date>
Restart context: <one line>
```

## Context map

The repo's orientation index lives in `config/context-map.md`: every piece of durable,
non-derivable memory a fresh agent needs, one pointer each, under a full lifecycle policy.
`config/repo-state.md` remains the definitive list of machine keys; the context map is the
definitive index of memory pointers.

## Scope rule

The top roadmap item is the active stream.
Backlog items are parked by decision; pulling one mid-stream is an explicit, announced choice, never a silent default.
A session orienting after a break names the active stream first, states these limits, and treats every other stream as out of scope until the user pulls it in.
