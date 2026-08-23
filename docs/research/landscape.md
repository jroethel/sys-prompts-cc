# Landscape: harness engineering discourse and the installs-plus-retainers market

Research ticket: [#5](https://github.com/jroethel/sys-prompts-cc/issues/5), scoped under [#1](https://github.com/jroethel/sys-prompts-cc/issues/1).
Method: web research only, no live model calls.
Window: sources dated roughly February 2026 through August 2026, since the terminology this ticket asks about did not exist before that window.

## Part 1: research framing

### The naming sequence

The field has moved through three names in about two years: prompt engineering, then context engineering, then harness engineering.
Prompt engineering optimizes a single instruction.
Context engineering optimizes everything the model sees at inference time for one decision: files, tool descriptions, retrieved snippets, memory.
Harness engineering is the current frontier term, and it covers the full system around the model across many inferences: tool orchestration, verification loops, guardrails, feedback loops, and observability, not just what enters the context window once.

There is a live disagreement about which term nests inside which.
Faros AI and similar commentary treat context engineering as one layer inside the broader discipline of harness engineering.
Birgitta Böckeler of Thoughtworks, writing on Martin Fowler's site, argues the reverse: a harness is a specific application of context engineering, because the harness is just the mechanism for delivering "guides" (preventative) and "sensors" (corrective) into the agent's context.
Both camps agree on the underlying shift: attention has moved from wording a single prompt to designing the system that surrounds the model.

### Where the term came from

"Harness engineering" as a named discipline traces to a single blog post: Mitchell Hashimoto (co-founder of HashiCorp, creator of Terraform and Vagrant) published "My AI Adoption Journey" around February 5, 2026, describing a six-stage personal adoption path that ends at a stage he called "Engineer the Harness."
His definition was concrete: whenever an agent makes a mistake, you do not just retry or reword the prompt, you change the environment around the agent (new rules, new checks, new guardrails) so that exact mistake becomes structurally impossible to repeat.
The term was not entirely new coinage, Anthropic had already described the Claude Agent SDK as a "general-purpose agent harness" in 2025, and older software engineering already had test harnesses, scaffolds, and control planes.
What Hashimoto did was give a fast-spreading name to a practice that was already happening.
Within weeks, both Anthropic (Effective harnesses for long-running agents) and OpenAI (Harness engineering: leveraging Codex in an agent-first world) published engineering posts using the same frame, which is unusually fast institutional uptake for a term with a single-author origin.

### Who is publishing on it

Three tiers of publisher are active, in roughly descending order of rigor.

Labs: Anthropic's engineering blog covers harness design directly (the Claude Agent SDK post, the long-running-agents post), and both Anthropic and OpenAI have folded the vocabulary into their official developer-facing writing within the same year it was coined.

Academia: the first peer-reviewed anchor is Galster, Mohsenimofidi, Lulla, Abubakar, Treume, and Baltes, "Harness Engineering for Agentic AI Coding Tools: An Exploratory Study," accepted at AIware '26 (ACM, July 2026), posted to arXiv as 2602.14690.
The paper studies eight configuration mechanisms across Claude Code, GitHub Copilot, Cursor, Gemini, and Codex, then empirically examines adoption across 2,853 GitHub repositories, with a detailed look at "context files" (the AGENTS.md/CLAUDE.md family).
Its conclusion is that AGENTS.md-style files are the natural starting point for harness configuration in the wild, and it calls for longitudinal research on how configuration strategies evolve.
This is the load-bearing citation for the field having become a real research object rather than only a blog-post trend, so it is worth being precise about what it does and does not cover: the study's taxonomy is built entirely from versioned, repository-level configuration artifacts.
It does not examine binary or npm-package patching of a vendor's own compiled prompts.

Practitioners: a wide layer of Medium, Substack, and vendor blog posts (Faros AI, Augment Code, Epsilla, codecentric, SIG, and many independents) is actively debating definitions and building glossaries, which is normal for a term still inside its first year.

### Where vendor-harness patching sits relative to this discourse

The ticket asks specifically about a narrower and more aggressive practice: not configuring the officially exposed surface, but directly rewriting a vendor's own shipped, compiled system prompt.
Three concrete projects anchor this practice.

`Piebald-AI/tweakcc` is an open-source CLI that patches Claude Code's system prompt, tool descriptions, toolsets, and UI directly.
For npm installs it edits `cli.js`; for native/binary installs it unpacks the executable with `node-lief`, patches it, and repacks it.
It tracks Claude Code's own update cadence: when a new release changes a prompt section you have not touched, tweakcc auto-updates that section from upstream; if you have touched it, it leaves your version alone and expects you to reconcile the conflict by hand.

`skrabe/lobotomized-claude-code` (and the related `tweakcc-fixed` fork) is a community project distributing a stripped-down, de-bloated replacement prompt set, delivered as one markdown file per prompt part with a metadata header (prompt id, the Claude Code version it was cut against, interpolated variables), applied through tweakcc.

`Piebald-AI/claude-code-system-prompts` is the upstream extraction repository: it pulls every part of Claude Code's system prompt, all built-in tool descriptions, sub-agent prompts, and utility prompts straight out of the compiled npm package via a script, republishes them as readable markdown, and updates within minutes of each new Claude Code release (a changelog tracks 265+ versions as of this writing).
Its README makes no claim of Anthropic endorsement, cooperation, or objection, and no such statement from Anthropic surfaced in this research.
The repo also doubles as top-of-funnel marketing for Piebald's own commercial agentic-coding product, which is a notable business-model detail: the extraction work is free and automated, and the commercial ask sits one click away.

Relative to the discourse mapped above, this practice is fringe but visible, not absent and not mainstream.
It does not appear in the academic taxonomy: Galster et al.'s eight configuration mechanisms are all sanctioned, versioned, repo-level artifacts, and binary patching of a vendor's compiled output is a different category of activity that the paper's method would not have captured even if it were common.
It is not discussed by name in the Anthropic or Thoughtworks framing pieces reviewed here, which describe harness engineering entirely in terms of the user's own outer harness (rules, checks, tools, guardrails a team builds around the agent), not modification of the vendor's inner harness.
At the same time, it is not a curiosity: tweakcc has hundreds of GitHub stars and multiple active forks, it has built real version-aware tooling (conflict detection, auto-update of unmodified sections, diffing against upstream), and its stated motivation (a default system prompt of 50-60K tokens, trimmed 10-20K tokens by removing unused sections) is a legitimate, recurring cost complaint from Claude Code power users.

The more interesting signal is convergence, not competition.
In the same window this research covers, Anthropic has been visibly widening its own officially sanctioned customization surface: output styles (persistent, file-based, can fully rewrite the response-style portion of the system prompt), `--append-system-prompt` / the SDK `append` option (session-scoped addition to the default prompt without replacing it), a fully custom system prompt string, and a plugin mechanism that lets third parties ship their own `output-styles/` directories with no special manifest entry required.
Each of these officially closes off a piece of what community tools like tweakcc exist to do unofficially.
Read against the last twelve months, the trajectory looks like a hack getting slowly absorbed: the specific want (control over what the vendor's own prompt tells the model to do) is the same want in both the fringe tool and the official surface, and Anthropic has been shipping sanctioned, non-binary-patching ways to satisfy more of it every few months, without yet covering everything tweakcc-style patching can do (full removal of specific tool descriptions, wholesale replacement of vendor-authored sub-agent prompts, patching native binaries at all).

## Part 2: market

What is actually sold to organizations today clusters into five distinct categories, not one.

**A. Hyperscaler-managed access.**
Claude for Enterprise premium seats are now available through AWS Marketplace, giving organizations a managed, subscription-priced path to Claude Code with centralized procurement, provisioning, and usage analytics, as an alternative to Bedrock's pay-as-you-go API access.
This is packaging and procurement, not configuration or tuning.

**B. Channel-partner consulting at scale.**
Anthropic's Claude Partner Network (launched March 2026, expanded with a three-tier Services Track in June 2026) is the structural fact behind most large-organization "Claude Code rollout" work.
Anthropic committed 100 million dollars to the program, and by the June 2026 update had certified more than 10,000 consultants across more than 40,000 applicant firms.
Deloitte (470,000 people trained), Accenture (30,000 people trained), PwC, and KPMG are named partners delivering enterprise rollouts, alongside Anthropic-run "Partner-Led Claude Code Workshops" that partner firms use to generate their own pipeline.
Individual engagement pricing is not disclosed publicly; the visible price signal is seat-level, Claude Code premium seats run about 150 dollars per user per month versus 30 dollars for a standard seat, with enterprise pricing undisclosed and negotiated.

**C. Boutique rollout and enablement shops.**
Below the Big 4 tier sits a layer of smaller, harness-specific consultancies selling phased deployment playbooks rather than general AI strategy.
TIMEWELL Inc. (Japan-focused) sells a named "WARP" consulting service plus a governance product ("ZEROCK"), explicitly arguing that a rollout that stops at "license plus training" fails, and that governance design, training, organizational change, and continuous improvement have to run as one system.
Fast Slow Motion lists discrete line items ("Claude Chat Rollout," "Claude Code Rollout," "Team Enablement," "Managed Provisioning," "Role-Based Training," "Adoption Support") with no public pricing.
claudeimplementation.com sells a deployment engagement that includes enterprise authentication and secrets management setup.
None of these three publish concrete pricing; all describe delivery as a bounded engagement (weeks, not an open retainer) with adoption/enablement support layered on top.

**D. Prompt-ops and agent-ops observability platforms.**
This is an adjacent but materially different market from what the ticket is asking about: tools like AgentOps, Braintrust, and similar prompt-management/observability platforms sell tracing, evaluation, and prompt-version management, not harness installation or configuration services.
Pricing here follows a conventional SaaS ladder: a free or low tier (often exhausted quickly in production, since a single agent run can emit a dozen-plus billable "events"), a paid tier around 40 to 100+ dollars per month, and a custom-priced enterprise tier gated behind compliance and self-hosting features.
Broader 2026 commentary on agent pricing argues flat retainers are already becoming obsolete for this category, because agent workloads have too much variance run-to-run for a fixed monthly fee to hold margin, and the market is shifting toward hybrid base-plus-usage or outcome-based billing instead.

**E. Open-source tool with a commercial upsell attached.**
Piebald's tweakcc and its extraction repo are free, but they exist inside a company that sells a separate commercial agentic-coding product, so the open-source harness-patching tooling functions as trust-building and community-acquisition infrastructure rather than a standalone business line.

### The three most instructive comparables

**1. The Claude Partner Network Services Track (Anthropic).**
What it sells: certification, co-marketing funds, deal-registration/referral protection, and a public partner directory, sold not to end organizations but to the consulting and SI firms who then sell installs and retainers to those organizations.
Delivery model: three tiers (Select, Preferred, Global Premier), gated by certification count, joint customer count, and published case studies; Anthropic funds partner enablement (Academy content, workshops, sales playbooks) rather than doing delivery itself.
Pricing: opaque at the end-customer level; the only public number is seat pricing (150 dollars/month premium seat), everything else is negotiated between the organization and its chosen partner.
Ongoing operation: the partner firm, not Anthropic, is the one who maintains configuration as models and Claude Code itself update, and that maintenance work is exactly what the partner is retained (billably) to keep doing.
This is the comparable that shows what "installs plus retainers" looks like once it is institutionalized: the labs do not sell the tuning relationship directly, they sell the right to sell it.

**2. systemprompt.io.**
What it sells: a hybrid of product and service, a self-hosted governance platform (a free template exists for self-service deployment) plus a paid implementation engagement that runs a named four-phase rollout playbook (pilot of 3-5 developers, department expansion to 10-20, cross-department to 30-60, org-wide to 50-200+) over 4-8 weeks.
Delivery model: managed settings pushed via MDM, permission-model configuration, audit hooks, and CLAUDE.md standardization, installed by the vendor and then handed to the organization.
Pricing: seat costs are stated plainly (Claude Code Pro at 20 dollars/month, Max at 100-200 dollars/month, Enterprise undisclosed), but the implementation service itself is not publicly priced.
Ongoing operation: this is the single clearest, most explicit statement found anywhere in this research on the "who maintains configs when models update" question.
Their guidance is to assign a permanent internal owner inside the platform team, at roughly ten percent of that person's time, explicitly not a project team that disbands once the rollout is declared done, with regular configuration review and dashboard monitoring built in as an ongoing operating cadence rather than a one-time deliverable.

**3. Piebald-AI / tweakcc ecosystem.**
What it sells: nothing directly, the tool and the extraction repo are free and open source, funded as awareness infrastructure for Piebald's separate commercial agentic-coding product.
Delivery model: self-service, a CLI the practitioner runs themselves, with no consulting engagement attached.
Pricing: zero for the tool; the monetization is indirect, community trust and visibility feeding a funnel toward the paid product.
Ongoing operation: solved by automation instead of a human retainer, a script re-extracts every prompt within minutes of each Claude Code release, and tweakcc's own conflict-detection logic (auto-update unmodified sections, flag modified ones for manual reconciliation) substitutes for the "assign a permanent owner" model that systemprompt.io recommends.
This comparable matters precisely because it is the cheapest possible answer to the maintenance question, and it demonstrates that at least part of "who keeps this current" can be engineered away rather than staffed, which is a real alternative to the retainer model the other two comparables assume.

## Practitioner fit

Reading the three comparables together, the market has a well-defended top and a thin, product-shaped middle, with a gap between them that a small operator could plausibly occupy.
The top (Category B) is structurally closed to an individual: it runs through a certification and partner-tier system built for firms with account teams and case-study portfolios, and the value it sells is channel trust as much as technical skill.
The bottom (Category E) shows that pure tooling can be given away and monetized indirectly, but that model requires either a separate product to fund it or a large enough audience that the awareness itself has value, neither of which a new, independent effort starts with.
The instructive middle is Category C together with systemprompt.io's model: a bounded, playbook-driven installation engagement (standardize the CLAUDE.md/AGENTS.md layer, configure output styles and permission hooks, run a phased pilot-to-org rollout) followed by a small, explicitly scoped retainer for ongoing configuration review as models and the harness itself change, sized more like "ten percent of someone's time" than a full FTE.
The research surfaced a recurring failure pattern worth taking seriously before selling into this space: multiple sources describe rollouts that stall because an organization treats deployment as a one-time event (buy licenses, hold one info session, call it done), and usage collapses within a few months, which is the exact gap a disciplined install-plus-light-retainer offering is positioned to close, provided the retainer is scoped narrowly enough to survive the same variance-in-effort problem that is already pushing the broader agent-ops market away from flat monthly fees.

## Sources

- [Harness Engineering vs Context Engineering: The Model is the CPU, the Harness is the OS](https://medium.com/@richardhightower/harness-engineering-vs-context-engineering-the-model-is-the-cpu-the-harness-is-the-os-51b28c5bddbb)
- [Prompt Engineering vs Context Engineering vs Harness Engineering: What's the Difference in 2026?](https://dev.to/ljhao/prompt-engineering-vs-context-engineering-vs-harness-engineering-whats-the-difference-in-2026-37pb)
- [Harness Engineering: Making AI Coding Agents Work in 2026 (Faros AI)](https://www.faros.ai/blog/harness-engineering)
- [Harness engineering for coding agent users (Birgitta Böckeler, Martin Fowler site)](https://martinfowler.com/articles/harness-engineering.html)
- [Harness Engineering - first thoughts (Martin Fowler site)](https://www.martinfowler.com/articles/exploring-gen-ai/harness-engineering-memo.html)
- [Harness Engineering for Agentic AI Coding Tools: An Exploratory Study (arXiv:2602.14690)](https://arxiv.org/abs/2602.14690)
- [Loop, Harness, Context Engineering: The Terms Explained (codecentric)](https://www.codecentric.de/en/knowledge-hub/blog/loop-harness-context-engineering-explained)
- [The Third Evolution: Why Harness Engineering Replaced Prompting in 2026 (Epsilla)](https://www.epsilla.com/blogs/harness-engineering-evolution-prompt-context-autonomous-agents)
- [GitHub - Piebald-AI/tweakcc](https://github.com/Piebald-AI/tweakcc)
- [GitHub - skrabe/lobotomized-claude-code](https://github.com/skrabe/lobotomized-claude-code)
- [GitHub - Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts)
- [Modifying system prompts (Claude API Docs)](https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts)
- [Effective harnesses for long-running agents (Anthropic Engineering)](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Building agents with the Claude Agent SDK (Anthropic Engineering)](https://anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude for Enterprise Premium Seats with Claude Code Now Available in AWS Marketplace](https://aws.amazon.com/blogs/awsmarketplace/claude-for-enterprise-premium-seats-with-claude-code-now-available-in-aws-marketplace/)
- [Claude Code Enterprise Rollout in 6 Phases (TIMEWELL Inc.)](https://timewell.jp/en/columns/claude-code-internal-rollout-6-phases)
- [Claude Code Enterprise Rollout Playbook for 50+ Developers (systemprompt.io)](https://systemprompt.io/guides/claude-code-organisation-rollout)
- [Claude Code for Enterprise: Complete Setup & Deployment Guide 2026 (claudeimplementation.com)](https://claudeimplementation.com/blog/claude-code-enterprise-guide)
- [Claude Services for Business (Fast Slow Motion)](https://www.fastslowmotion.com/claude-services/)
- [Introducing the Services Track and Partner Hub of the Claude Partner Network](https://www.anthropic.com/news/services-track-partner-hub)
- [Anthropic invests $100 million into the Claude Partner Network](https://anthropic.com/news/claude-partner-network)
- [7 best prompt management tools in 2026 (Braintrust)](https://www.braintrust.dev/articles/best-prompt-management-tools-2026)
- [AgentOps: What It Does, Pricing, and Alternatives (2026)](https://inference.net/content/agentops-alternatives/)
- [Agent Pricing Models 2026: Token vs Outcome Billing](https://www.digitalapplied.com/blog/agent-pricing-models-token-vs-outcome-based-2026)
- [How to Hire a Prompt Engineer: 2026 Guide (KORE1)](https://www.kore1.com/how-to-hire-prompt-engineer-2026/)
