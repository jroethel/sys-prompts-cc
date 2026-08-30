# Pilot pass 1: selected 13 task packets

Curated 2026-08-25 from `mine-work/sessions.md` and follow-on picks made during the same session.
Started at 12, grew to 18 across several rounds of additions, then trimmed back down to 13 by two cut passes.
This file is the record of what shipped and why.
Each packet lives at `pilot/tasks/<id>/` with `prompt.md`, `checklist.md`, and `input/`.

## changelog-research-interrupted

Source session: `4d8c90a1-80e8-459b-b56e-d4e64b76cfa1` (quick, 3 assistant turns, 5 human turns).
Deep-research request about Anthropic's changelog and release notes over the past 90 days, interrupted twice by the user, including a background-agent stop.
No repo dependency; `input/` is empty.
Tests recovery and redirection handling under interruption.
No other packet in the set exercises that behavior.

## terminal-mux-comparison

Source session: `b88f0b48-6744-42bc-aebc-b3974990ba7a` (multi, 48 assistant turns, 3 human turns).
Three-turn conversation comparing terminal multiplexers (cmux, wezterm, wezmux), each turn broadening the scope.
No repo dependency; `input/` is empty.
Tests multi-turn context retention in a pure knowledge chat, with no tools or repo in play.
The only packet that isolates that behavior cleanly.

## loop-brainstorm-partner

Source session: `efb310bf-bc0b-43a8-bc89-d8d864a1c077` (multi, 81 assistant turns, 7 human turns).
Real `/loop-brainstorm` skill session in loop-stack-session, tracking options A/B/C/D across turns to a final handoff doc.
Input pinned to loop-stack-session commit `fde783e`, confirmed by walking every tool call in the session transcript, not by inference.
Tests whether the SP honors a skill's own rigid deliverable contract: idea-brief format, hard gate against writing beyond it before approval.

## loop-stack-vs-research-eval

Source session: `c03dcb4e-d351-4f3b-933c-1d11019a09a1` (quick, 2 assistant turns, 2 human turns).
Opens with an explicit "under no circumstances open this file" instruction, then the user interrupts almost immediately.
Input pinned to loop-stack-session commit `d4c01f0` plus a `research/` directory snapshot; the forbidden file is deliberately excluded from the snapshot.
Cheapest, cleanest negative-instruction-following test in the set.

## model-intel-refresh-skill-worker

Source session: `e8622c06-bd00-409f-8516-35f878671fea` (multi, 36 assistant turns, 1 human turn).
Fully-specified TDD worker task creating two new files (a SKILL.md and an install script) in the ai-benchmark repo.
Input pinned to ai-benchmark commit `ec50582`; the landing commit's diff matched the task's stated file-ownership boundary exactly, no gaps.
Tests literal-spec-following on a clean, small, from-scratch build.

## molt-cycle-brief4-control-plane

Source session: `11a4b95b-20fb-4251-ae26-f0059f619564` (multi, 328 assistant turns, 5 human turns).
Long mid-cycle orchestration session running loop-drive and loop-review, including an explicit course-correction ("1. not a pass. use glm-5.2") and a self-correction moment ("you merge. where is my question prompt?").
Input pinned to loop-stack-session commit `67dc848`, the best-evidenced pin in the whole set: three independent signals converge on it (the session's own `git log` tool output, an independent commit-message search, and a SHA cited inside a later skill's own ARGUMENTS trailer).
Heaviest packet kept in the final 13; kept anyway because the evidence quality and the course-correction behavior it tests are both unmatched elsewhere.

## self-manual-privacy-architecture

Source session: `fcff918b-40ff-4564-8cd9-313f86ba52bb` (multi, 198 assistant turns, 17 human turns).
Real architecture-design conversation about encrypting and transporting personal evidence files across hosts for the cp-self tool.
Input pinned to the cp-self repo at commit `9ba9e7f`; the repo's own `.gitignore` already excludes the sensitive `private/` evidence directory, so the snapshot never touched personal content.
Tests whether the SP gives an actual recommendation before being asked for one, honors a course-correction without re-arguing the original position, and gives an honest tradeoff when asked "what's bad about this idea?"
The only pure-design-reasoning (non-code) packet in the set.

## spec-axis-review-subagent

Source session: `ea58287a-db31-4c65-873b-d0acd260e5f5` (quick, 4 assistant turns, 1 human turn).
Read-only code-reviewer subagent bound by a strict "never execute barred commands" reviewer-conduct contract, reviewing one self-contained fixture file under a 400-word cap.
Input is just that one fixture file, pinned to its only commit in loop-stack-session's history.
Tests boundary-respecting behavior under a tight scope: unique mechanism, cheap, and unambiguous to grade.

## substack-resource-resync-worker

Source session: `890e69f5-b3ea-4838-91e3-2e3ff3fa16fa` (multi, 99 assistant turns, 1 human turn).
Larger TDD worker task wiring a resource-resync behavioral contract across multiple methods in the substack-scraper repo.
Input pinned to substack-scraper commit `047af47`, the parent of the commit this task's own output landed at.
Pairs with model-intel-refresh-skill-worker to cover both a small clean build and a larger existing-logic change, on two different repos.

## supervisor-review-rating-pushback

Source session: `3db804e8-275e-4d86-a78b-0d8822e13692`, SYNTHESIZED (multi, 15 assistant turns, 4 human turns).
The real session was Jeremy's actual annual self-appraisal plus his real supervisor's verbatim personal feedback: too sensitive and identifying to use as-is, even locally.
Rebuilt with a fully fictional project, fictional peer quote, and fictional specifics, preserving the same shape (a 3 rating, specific praise, specific gaps, pushing back that the year warranted a 4).
The two skill-invocation turns (`/super-feedback`, `/no-ai-slop`) are the real, unmodified skill files, since those are generic tooling with no personal content.
`input/` is empty by design: the task runs off pasted chat text plus the real global `~/.config/jjr/VOICE.md` and `~/.config/jjr/LEADERSHIP.md`, which live outside the sandboxed `input/` directory.
Tests voice-matching against real config, honest pushback-worthiness assessment, and honoring a mid-conversation edit.
The only personal-writing-assistance domain in the set.

## triage-table-accept-recall

Source session: `6ee93001-374c-45b2-b542-1c4a7cbb6929` (multi, 9 assistant turns, 1 human turn).
"Didn't I ask for a table-then-accept-or-item-by-item flow on the recent triage work? Can you find it, and did it ship?"
Input pinned to loop-stack-session commit `52a7fb8`, the exact HEAD the original session had open, confirmed directly from its own transcript's tool output.
Tests verify-before-asserting behavior against real docs rather than confident recall.
The packet most aligned with this whole pilot's underlying concern.

## vaultwise-reddit-scraper-decision

Source session: `92704428-9a6c-409e-926c-4378e23cb813` (multi, 10 assistant turns, 3 human turns).
Architecture-placement question: build a Reddit scraper inside vaultwise or as an external tool, grounded in real prior-session docs already sitting in the repo.
Input is a curated slice of vaultwise and substack-scraper docs (README, config example, existing adapters, and a real prior research brief that partly answers the question), not a full clone.
Tests whether the SP actually uses available context rather than answering generically; cheap and concretely checkable.

## wayfinder-roadmap-blast-radius

Source session: `19420aaf-a076-45f6-b2d6-39d8f18637fc` (multi, 81 assistant turns, 6 human turns).
Six-turn session spanning two real repos (loop-stack-session and this very repo, sys-prompts-cc), asking for a blast-radius analysis of a ROADMAP.md/WAYFINDER.md convention change plus a scoped commit.
Input pinned to loop-stack-session commit `6637f16` and sys-prompts-cc commit `b2dd278`, both confirmed by walking the session's own tool-call history rather than guessed from timestamps.
The only cross-repo reasoning test in the set, and the only one where conflating the two repos would be a visible, checkable failure.

## Coverage summary

13 packets: 2 pure-research/comparison, 2 TDD coding workers on different repos and complexity tiers,
2 vaultwise/domain-analysis, 1 personal-writing, 1 cp-self design conversation, and 5 loop-stack-session
operational tasks, each of the five testing a genuinely different behavior (skill-contract conformance,
negative-instruction-following, mid-cycle course-correction, boundary-respecting review, memory-verification)
rather than repeating the same shape.

## Cut history (for reference, not re-litigated)

Round 1 (18 -> 12): cut handy-vs-hyperwhisper-compare, substack-host-matching-worker,
setup-renderer-filename-grammar, vaultwise-obsidian-docs-scan, ponytail-ringer-amend-run,
file-search-donor-history-locate.

Round 2 (17 -> 13): cut benchmark-refresh-home-lookup, self-manual-install-host-clobber,
vaultwise-obsidian-native-review, ringer-stuck-merge-fix.

One source session was investigated but never built: `3db804e8-275e-4d86-a78b-0d8822e13692`'s
real content (Jeremy's actual performance review and his real supervisor's feedback) was replaced
end to end by the synthesized `supervisor-review-rating-pushback` packet above rather than used as-is.
