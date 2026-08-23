# Measurement methodology for system-prompt impact

Research ticket: [issue #4](https://github.com/jroethel/sys-prompts-cc/issues/4), a sub-issue of the wayfinder map ([issue #1](https://github.com/jroethel/sys-prompts-cc/issues/1)).
Question: how is system-prompt impact measured credibly, and what methodology should a pilot adopt for tokens, rounds, tone, and satisfaction with work done.
Scope: survey only, no live Claude sessions were launched and no model-calling script was run to produce this document.

## Recommendation up front

Run a paired-task blind side-by-side in a herdr workspace, one variant per pane, same model and same task text per pair, order randomized per pair.
Capture tokens and rounds mechanically from the session JSONL transcript, capture wall-clock from `/cost`, capture compaction headroom from `/context`, and capture tone and satisfaction as a single blind pairwise preference judged by the pilot operator, not two separate scales.
Target 20 to 30 paired tasks as a screening floor, not a publishable claim, and treat any result as directional until a confirming run repeats it.
The single biggest validity threat is blinding collapse: the same person authors the prompt variant, runs the pilot, and rates tone and satisfaction, so stylistic fingerprints make true blinding nearly impossible and the qualitative half of the result is confounded with the rater's own expectancy.

The rest of this document is the survey behind that recommendation.

## 1. Token accounting

Three sources of token data exist for a Claude Code session, at three different levels of effort.

**Interactive `/cost` (now aliased to `/usage`).**
Shows total cost, API duration, wall duration, lines changed, and a per-model breakdown of input, output, cache-read, and cache-write tokens for the current session.
The CLI figure is a locally computed estimate; the Claude Console usage page is the source of truth for billing, but the CLI breakdown is precise enough for a relative A/B comparison where both variants are estimated the same way.
`/context` is the companion command: it draws a percentage grid of what occupies the context window (system prompt, tools, MCP definitions, files, history) and is the direct instrument for the "compaction headroom" question below.

**Session JSONL transcripts (`~/.claude/projects/<project>/<session-id>.jsonl`).**
Verified locally in this session: every assistant message carries a `usage` block with `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`, and a `server_tool_use` sub-object for web search and web fetch calls.
This is the richest source available without any setup: `jq -c 'select(.type=="assistant") | .message.usage' <file>.jsonl` extracts a full per-turn token ledger, which is exactly the granularity a rounds-to-completion analysis needs.
The format is internal and undocumented, and has changed across Claude Code releases before, so a pilot script that parses it should fail loud on an unrecognized shape rather than silently miscount.

**OTLP telemetry (`CLAUDE_CODE_ENABLE_TELEMETRY=1` plus an OTLP endpoint).**
Built into the CLI: it emits metrics (token and cost counters), structured log events, and, behind a beta flag, distributed traces, all exportable to a collector (Prometheus, Grafana, CloudWatch, Google Cloud Monitoring).
This is the right tool for a fleet or a CI gate, not for a one-person pilot: it requires standing up a collector, and prompt or response content capture is opt-in and off by default, so per-turn qualitative review still routes through the transcript, not the metrics stream.
It also has a coverage gap relevant here: Claude Code on the web emits nothing to OTel, only the CLI, IDE extension, and Agent SDK paths are instrumented.

For a single-operator pilot, the JSONL transcript is the right primary source: no setup, full per-turn fidelity, and it is the same file `/cost` itself is computed from.
Use `/cost` as the fast human-readable spot check and the transcript as the machine source for the recorded metric.

## 2. Rounds-to-completion and wall-clock

Rounds-to-completion (count of assistant turns from task start to the operator accepting the result as done) is a reasonable efficiency proxy, with two caveats.
First, it is gameable by verbosity: a variant that front-loads more work per turn looks efficient on round count while burning more tokens per round, so rounds and tokens must be reported together, never one without the other.
Second, round count only means what it claims to mean if task success is pinned first: a variant that finishes in fewer rounds because it did less, or skipped verification, is not more efficient, it is worse.
Pair rounds-to-completion with an explicit pass/fail or rubric-scored completion check per task, the way terminal-bench and SWE-bench gate every efficiency number behind a verification suite.

Wall-clock has two components worth separating, and `/cost` already reports both: total duration (API), the time actually spent waiting on model calls, and total duration (wall), the full session time including the operator's own think time and any tool-execution latency.
API duration is the comparable number across variants; wall duration is contaminated by how long the human operator took to read, react, and re-prompt, which is not a property of the system prompt.
Time-to-first-token is the more precise version of "the model feels faster," and no public Claude Code surface reports it directly (`/cost` and the transcript report totals per turn, not first-byte latency).
Approximating it from total API duration divided by turn count is a rough average latency, not a first-token measurement, and should be labeled as such; a true TTFT number needs either the OTel enhanced-tracing beta (unverified here whether it exposes first-chunk timestamps at the request level) or a client-side wrapper that timestamps the first streamed content chunk.

## 3. Tone and style scoring: LLM-judge rubrics and their pitfalls

LLM-as-judge is the fastest way to score tone at scale, and it carries three well-documented biases that a pilot design has to account for rather than hope around.

**Position bias.**
Judges systematically favor whichever response appears first (or, less often, last) in a pairwise prompt, by as much as 10 to 15 percentage points.
Mitigation: evaluate every pair in both orders and keep only the judgment that agrees across both orderings, treating a disagreement as a tie (swap augmentation); this is the same logic Chatbot Arena and MT-Bench use.

**Verbosity bias.**
Judges tend to prefer the longer response even when the extra length adds nothing, an effect confirmed with statistically significant results in multiple bias studies.
Mitigation: length-controlled scoring (the approach AlpacaEval popularized, regressing out length before comparing), or an explicit rubric instruction to penalize padding and reward the response that says the same thing in fewer words, since that instruction is directly relevant to this repo's own subject matter.

**Self-preference bias.**
A judge model scores its own family's outputs roughly 10 to 25 percent higher than a competing model's outputs on the same content.
This is the sharpest risk for this repo's specific use case: if the judge and the variants under test are all Claude, the judge is structurally biased toward whichever variant's phrasing looks most like its own default register.
Mitigation: use a judge from a different model family than the variants being compared, or route the decision through a human rather than a model judge, or run a debate/cross-validation setup across multiple judge families and require agreement.

General mitigations that stack across all three: calibration prompting (explicitly tell the judge order and length should not influence the verdict), forcing a written rationale before the verdict (chain-of-thought judging reduces reliance on superficial cues), and pinning the judge model version, since a judge's mean score and distribution shift silently when the judge itself gets a minor version bump.
None of these mitigations eliminate the bias, they reduce it; a pilot that uses an LLM judge for tone should treat its verdict as a secondary signal, not the primary one, given the section below makes the case that a human doing blind pairwise comparison is both more reliable and cheaper to run for a one-person pilot.

## 4. Human satisfaction capture one person can sustain

Blind pairwise preference (show two outputs, hidden labels, pick the better one, note the reason in one line) beats a Likert scale for a solo rater, for reasons that are well established in the human-evaluation literature and that get sharper, not weaker, with only one rater.

A 1-to-5 or 1-to-7 satisfaction scale requires the rater to hold a stable internal anchor for what a "4" means, and that anchor drifts across a multi-day pilot as the rater sees more examples, gets tired, or gets used to a variant's quirks; there is no second rater to catch the drift.
"A is better than B" is a much easier and more stable cognitive act than "this is a 4.2," which is exactly why Chatbot Arena, MT-Bench, and every major LLM leaderboard use pairwise comparison (fed into a Bradley-Terry or Elo-style model to produce a scalar ranking) rather than absolute scoring, and why the Chatbot Arena authors specifically validated that crowdsourced pairwise votes agreed with expert raters.
Pairwise judgments are also cheaper to sustain solo: one binary or three-way (A / B / tie) decision per task pair, with a one-line reason, is a sustainable per-task cost across dozens of tasks; a defensible multi-axis rubric score is not.

Fold "tone" and "satisfaction with work done" into the same pairwise judgment rather than two separate scales.
They are correlated in practice (a response with the tics this repo's variants target, hedging, padding, unearned confidence, directly degrades perceived satisfaction with the work), and a single rater tracking two scores per task doubles the anchoring-drift problem for no real gain in signal.
If tone and task-outcome quality genuinely diverge on a given task (crisp tone, wrong answer), capture that as a one-line note on the pairwise record rather than a second numeric axis.

## 5. Variance: how many runs make a claim credible

Agent runs are noisy, and the credible-N question has real numbers behind it, not just intuition.

For a single binary-outcome benchmark cell (task passed or failed) with `n = 100` independent trials, the 95 percent Wilson confidence-interval half-width is typically 7 to 9.5 percentage points, meaning an observed difference smaller than roughly 8 to 10 points between two variants is not distinguishable from noise at that sample size.
Small benchmarks make this worse in a way directly relevant to a solo pilot: AIME 2025 has only 30 problems, so one flipped result moves the reported score by more than 3 percentage points, and terminal-bench's 89 tasks are already flagged in the literature as small enough that aggregate rankings are sensitive to a handful of idiosyncratic tasks.
Position paper guidance from this literature is blunt: do not lean on normal-approximation statistics in an LLM eval with fewer than a few hundred data points.

The lever that makes a small-N pilot viable is pairing, not scale.
A paired design, the same task run under both variants rather than two independent samples of different tasks, lets you use McNemar's test (or a paired bootstrap) on the discordant outcomes, which has meaningfully more statistical power per data point than an unpaired comparison, because it cancels out task-to-task difficulty variance rather than absorbing it into the noise term.
This is also exactly the design the fixing-smartass-opus-5 repo already uses for its herdr compare loop (same prompt, same model, one variable), and it is the right foundation to build the pilot on: it just needs the run count and the recording step this document adds.

Practical read for a one-person pilot: 20 to 30 paired tasks is a reasonable floor for a screening pass that can detect a large, consistent effect (the kind a 28 to 38 percent prompt-size cut plausibly produces), but it will not resolve a small or borderline effect, and a null result at that N is uninformative rather than a disproof.
If the screening pass shows a large, consistent win, that is the trigger for a larger confirming run, not a conclusion in itself.

## 6. Existing tools and benchmarks worth borrowing from

| Tool / suite             | Unit under test            | What to borrow                              |
| ------------------------ | -------------------------- | ------------------------------------------- |
| promptfoo                | isolated prompt fragment   | YAML test matrix, CI-friendly assertions    |
| terminal-bench 2.1       | full agentic terminal task | instruction, sandbox, verification, oracle  |
| SWE-bench Verified       | real GitHub issue to patch | difficulty tiers, paired same-instance runs |
| Chatbot Arena / MT-Bench | full conversational turn   | blind pairwise, Bradley-Terry ranking       |

**promptfoo** is the closest thing to an off-the-shelf harness for this repo's narrower comparisons: a declarative YAML config runs a matrix of prompts against providers and inputs, applies assertions, and optionally scores with an LLM judge, with CLI exit codes that gate CI.
It fits testing an isolated system-prompt fragment or tool-description rewrite in isolation (single-turn, deterministic assertion), but it is not built for a multi-turn agentic Claude Code session with tool calls, file edits, and a human-in-the-loop completion judgment, so it is a good fit for a narrower future ticket (regression-testing individual prompt fragments) and a poor fit for the full-session pilot this ticket is about.

**terminal-bench** is the most structurally relevant benchmark, not because this repo should adopt its task set, but because its task-authoring discipline transfers directly: a good task is adversarial, difficult, and legible, has a programmatic verification step (not a vibe check), and ships an oracle solution so "done" is unambiguous.
Its own methodology paper reports that over 15 percent of tasks in popular terminal-agent benchmarks are reward-hackable, which is a direct warning for this pilot's own task set: any task whose verification can be satisfied by a shortcut (e.g., a completion claim with no evidence) will reward exactly the failure mode the system-prompt tuning is trying to fix.

**SWE-bench** contributes the paired same-instance evaluation pattern (run every variant on the identical task instance, never a fresh sample per variant) and the difficulty-stratification idea (bucket pilot tasks by expected effort, the way SWE-bench Verified buckets by human-solve-time, so a handful of hard tasks don't dominate the aggregate the way one AIME problem dominates a 30-problem set).

**Chatbot Arena / MT-Bench** contribute the human-preference design used in the recommendation above: pairwise, blind, and (at larger scale than a solo pilot needs) resolvable into a Bradley-Terry ranking if the pilot ever grows past two variants.

No tool surfaced in this research is purpose-built for "A/B testing an agent harness's system prompt across full multi-turn coding sessions."
The closest adjacent category, prompt-variant platforms such as Braintrust, Confident AI, and Maxim, targets single-call production prompts with routed experiment traffic, not a locally run, multi-turn, tool-using coding agent.
That gap is exactly why the recommendation below composes existing primitives (herdr side-by-side, JSONL token accounting, terminal-bench-style task verification, Arena-style blind pairwise judgment) rather than pointing at one existing product.

## 7. Testing lobotomized-claude-code's specific claims

`~/repos/lobotomized-claude-code/README.md` makes four claims for its Opus-4.8 prompt pack, in this chain: cut the prompt text by 28 to 38 percent, which means the model re-reads fewer characters every turn, which yields a quicker first token, more headroom before compaction, and fewer contradictory rules pulling against each other (paraphrased in the ticket as "better behavior").
Only the first link in that chain is currently substantiated; the rest are stated as consequences, not measured.

**Fewer characters re-read per turn.**
The 159K-to-99K and 1.74M-to-1.26M numbers in the README are a static diff of the prompt-pack source files (`wc -c` on stock vs. lean, in effect), not a runtime measurement, and that diff is trivially reproducible and already credible on its own terms.
What it does not establish is the "re-read every turn" framing: Claude Code prompt-caches the system prompt after the first turn, so most of the character reduction should show up as a smaller one-time cache-write cost, not a per-turn saving, once caching kicks in.
To test the runtime claim rather than the static one: run matched tasks under both packs, pull `cache_creation_input_tokens` (the cache write, paid once) and `cache_read_input_tokens` (the cheap re-read) per turn from the session JSONL, and confirm the reduction actually lands where the README implies it does, in cache-write size on turn one, rather than assuming it from the source-file diff.

**Quicker first token.**
This is a latency claim, and no public Claude Code surface (`/cost`, `/context`, the JSONL transcript) reports time-to-first-token; they report totals per turn or per session.
It can be approximated, not measured precisely, by dividing `/cost`'s "Total duration (API)" by turn count for matched tasks under both packs; that produces an average per-turn latency, not a first-token number, and needs several repeats per task because network jitter and Anthropic-side load plausibly move that average more than a smaller system prompt does.
A real test needs either the OTel enhanced-tracing beta, if it turns out to expose request-level first-chunk timestamps (unverified in this research), or a thin client wrapper that timestamps the first streamed content chunk against the moment the prompt was sent.

**More compaction headroom.**
This is the one claim already directly testable with an existing command: `/context` reports the percentage of the context window used by each contributor at any point in a session.
Run matched long sessions (same task sequence, several turns) under both packs, sample `/context` at fixed checkpoints, and record the turn number at which auto-compaction first fires under each pack.
A pack that is meaningfully smaller should compact measurably later on the same task sequence; if it does not, the claim does not hold up at runtime regardless of the static character count.

**Better behavior.**
This is the vaguest of the four and the one that cannot be settled by a token or timing metric at all; it needs the tone and satisfaction methodology from sections 3 and 4, a paired, blind, human-judged comparison on real tasks, not an impression formed while reading the prompt diffs.
It is worth noting that neither `lobotomized-claude-code`'s README nor the sibling `fixing-smartass-opus-5` repo (surveyed via `~/create/research/opus-slop/briefing-v1-system-prompt-engineering.md`, already in this repo's local research) actually reports a repeated, measured comparison for this claim: the latter's own README concedes its herdr compare-loop results are "anecdotal and non-deterministic," with runs where the stock variant was faster.
Treat "better behavior" as the primary hypothesis this pilot exists to test, not as an established fact to be confirmed.

## 8. Recommended pilot methodology

**Design.**
Paired tasks, run in a herdr workspace with two Claude Code panes (the same split-pane pattern `fixing-smartass-opus-5`'s `just compare` recipe already uses), one variant per pane, same model, same task prompt fired into both, left/right assignment randomized per pair so any residual position effect cancels across the pilot rather than compounding in one direction.
Pull 20 to 30 real tasks from actual past sessions (not synthetic prompts), stratified informally into a handful of quick tasks and a handful of harder multi-turn tasks, so the pilot is not dominated by one long outlier the way a 30-problem benchmark is dominated by one flipped result.

**Metrics per run, all pulled mechanically from existing surfaces.**
Tokens: input, output, cache-read, cache-write, summed across turns from the session JSONL `usage` blocks.
Rounds: count of assistant turns to the operator's completion judgment.
Wall-clock: `/cost`'s API duration (comparable across variants) and wall duration (context, not a variant property).
Compaction headroom: `/context` percentage at the end of the task, or the turn number where auto-compaction first fires on longer tasks.

**Tone and satisfaction, one blind pairwise judgment per task pair.**
The operator reads both final transcripts with variant identity hidden (strip banner or meta text that would reveal which pack is which), picks A, B, or tie, and records one line on why.
Optionally run a secondary LLM-judge pass, from a different model family than the variants under test, order-swapped, as a tie-breaker signal only, never as the deciding vote, given the self-preference risk documented in section 3.

**Completion gate.**
Before counting a task's efficiency numbers, first check it actually succeeded, using the same terminal-bench-style discipline (a concrete, checkable definition of done, not a vibe call) so a variant cannot look efficient by doing less or skipping verification.

**Read-out.**
Treat the pilot as a paired screening pass, not a publishable result: a large, consistent effect across most of the 20 to 30 pairs is grounds to invest in a larger confirming run; a mixed or small effect is inconclusive at this N and should not be reported as a finding either way.

## 9. Biggest validity threat

Blinding collapse.
The same person designs the prompt variant, decides what "lean" or "better" should look like, runs the pilot, and is also the sole rater for tone and satisfaction.
Mechanical blinding (hidden labels, randomized position) does not survive contact with a rater who wrote the variant: banned-phrase removal, hedging removal, and register shifts are exactly the kind of stylistic fingerprint a self-authored prompt pack leaves, and a rater who built it will recognize it within a sentence or two even with the label hidden.
No amount of additional sample size fixes this, because it is not a noise problem, it is a systematic confound between the rater's identity and the rater's expectation of which variant should win.
Mitigate, but do not claim to cure: keep the mechanical blinding steps anyway (they raise the cost of guessing even if they do not eliminate it), separate the build session from the rating session by at least a day so recall fades, and report any pairwise win rate as an upper bound on the true effect rather than as proof, with a second rater (even an occasional one) as the real fix if this pilot's results are ever meant to travel beyond a personal decision.

## Sources

- [Observability with OpenTelemetry - Claude Code Docs](https://code.claude.com/docs/en/agent-sdk/observability)
- [Manage sessions - Claude Code Docs](https://code.claude.com/docs/en/sessions)
- [Claude Code and Codex are logging your token usage locally](https://dev.to/newtorob/claude-code-and-codex-are-logging-your-token-usage-locally-here-is-how-to-read-it-580)
- [Clarification needed on /cost calculation logic and token breakdown - GitHub issue](https://github.com/anthropics/claude-code/issues/26762)
- [Self-Preference Bias in LLM-as-a-Judge (arXiv 2410.21819)](https://arxiv.org/pdf/2410.21819)
- [LLM-Judge Bias Mitigation: Detect, Measure, Fix](https://futureagi.com/blog/evaluating-llm-judge-bias-mitigation-2026/)
- [promptfoo](https://medium.com/@yetsmarch/promptfoo-a-better-prompt-evaluation-framework-c88a96b99821)
- [Terminal-Bench](https://www.tbench.ai/)
- [What Makes a Good Terminal-Agent Benchmark Task (arXiv 2604.28093)](https://arxiv.org/pdf/2604.28093)
- [How to scale agentic evaluation: lessons from 200,000 SWE-bench runs - AI21](https://www.ai21.com/blog/scaling-agentic-evaluation-swe-bench/)
- [SWE-rebench (arXiv 2505.20411)](https://arxiv.org/pdf/2505.20411)
- [Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference (arXiv 2403.04132)](https://arxiv.org/abs/2403.04132)
- [Resolution Diagnostics for Paired LLM Evaluation (arXiv 2605.30315)](https://arxiv.org/html/2605.30315)
- [General Agent Evaluation (arXiv 2602.22953)](https://arxiv.org/pdf/2602.22953)
- Local: `~/repos/lobotomized-claude-code/README.md`
- Local: `~/repos/fixing-smartass-opus-5/README.md` and `justfile`
- Local: `~/create/research/opus-slop/briefing-v1-system-prompt-engineering.md`
