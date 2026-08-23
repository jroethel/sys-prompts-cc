# Diff surface: shipped binary vs. override catalogs

Research ticket: https://github.com/jroethel/sys-prompts-cc/issues/3

Method is static only: `strings` on the installed Mach-O, file reads, and read-only `git show tag:path` against the two override repos.
No live Claude session was started and the installed binary was not modified.

## TL;DR

The most capable diff is keyed on the tweakcc-fixed extractor's prompt `id`, not on raw text, and every comparison runs on *normalized prose* rather than the raw template string.
Normalization (undo JS template escaping, collapse `${...}` interpolations to a sentinel, collapse whitespace) is the whole game: it is what separates genuine content drift from the two extractors merely representing the same bytes differently.
Measured against the 2.1.204 binary, the Piebald catalog is 99% prose-identical on the prompts it aligns (394 of 399), and the lobotomized pack has zero stale-behind overrides - it is uniformly at or ahead of 2.1.204.

## The three corpora at 2.1.204

| Corpus | Source of truth | Prompt count | Alignment key |
|--------------------|--------------------------------------------------|-------------:|--------------------------|
| Shipped binary     | `~/.tweakcc/prompt-data-cache/prompts-2.1.204.json` | 1537 | tweakcc `id` (native)    |
| Piebald            | `git show v2.1.204:system-prompts/*.md`             |  557 | own slug scheme          |
| Lobotomized o4-8   | `system-prompts-opus-4-8/*.md`                      | 3219 | tweakcc `id` (shared)    |

The binary count is the tweakcc-fixed extractor's own segmentation of the 2.1.204 Mach-O, cached as structured records (`id`, `name`, `description`, `pieces`, `identifiers`, `version`).
The Piebald tag `v2.1.204` exists, giving an exact-version baseline without touching HEAD (which tracks 2.1.240).
The lobotomized `system-prompts-opus-4-8/` directory is a full mirror catalog: it carries a file for every prompt, most of which are verbatim copies, not edits.

## Recommended extraction route (validated)

Use the tweakcc-fixed extractor cache as the primary structured corpus, and use `strings` only as an independent validator.

- `~/.tweakcc/prompt-data-cache/prompts-<version>.json` already resolves what raw `strings` cannot: prompt `id`, human `name`, the interpolation boundaries (`pieces` split at each `${...}`), and a per-prompt `version` provenance tag.
- It is the exact structure tweakcc-fixed splices back in, so it is definitionally "what runs" for any install that tool patches, and it shares the `id` namespace the lobotomized pack overrides against.
- Validation: `strings -n 6 <binary>` yields a 33 MB undifferentiated blob (minified JS, no id or name boundaries).
  Every sampled cache prose fragment is present verbatim in that blob (2+ hits each), including the full `system-reminder-plan-mode-is-active-5-phase` body that Piebald's same-named slug does *not* carry - which is how we know the cache, not Piebald, is ground truth where they disagree.
- Conclusion: `strings` + delimiter heuristics would re-derive the segmentation the extractor already did, for lower fidelity.
  Reach for `strings` to confirm a specific string is or is not in the binary, not to build the catalog.

## Recommended canonical diff artifact

One row per prompt `id`, three columns of corpus state, comparisons run on normalized prose.

1. Alignment.
   Primary key is the tweakcc cache `id`, which the lobotomized pack and the patcher already share.
   Piebald uses a divergent slug scheme (`agent-prompt-*` where the extractor uses `agent-*`, and it splits `code-review` into `part-1` .. `part-10` where the extractor keeps different chunks), so bridge Piebald with a content-hash fallback on normalized prose, not a slug join alone.

2. Normalization (applied before every hash, token count, or ratio).
   Undo JS template-literal escaping (`\`` to backtick, `\$` to `$`), collapse every `${...}` interpolation (innermost first, to handle `${${0}}`) to a single sentinel, then collapse whitespace.
   This is load-bearing: on the raw string, Piebald matches the binary on only 41% of aligned prompts; after normalization it matches on 99%.
   The gap is pure representation noise - positional `${0}` vs. named `${GREP_TOOL_NAME}` identifiers, and backtick escaping inside template literals - not content.

3. Per-prompt fields.
   Presence in each corpus; normalized-prose md5 per corpus; char and word delta; and a classification versus the binary: `untouched` (prose equal), `rewritten` (present, non-empty, differs), `suppressed` (empty body), or `missing-counterpart` / `orphan` (id in one corpus but not the binary).
   Char and word counts on normalized prose are a sufficient token-delta proxy for ranking; a real tokenizer is optional.

4. Drift quantification across versions (two signals, cheap then authoritative).
   Signal one is the per-prompt `version` tag: a prompt marked 2.1.178 in a 2.1.204 binary has not changed since 2.1.178, so tag inequality is a fast pre-filter for candidate drift.
   Signal two is the verdict: pull historical text with `git show vX:system-prompts/<id>.md` and diff it against the cache at version Y with a SequenceMatcher ratio on normalized prose.
   Signal two must decide, because the tags proved unreliable on their own (see below).

## Measurement 1: Piebald fidelity to the 2.1.204 binary

399 of Piebald's 557 files id-align to the binary; the comparison runs on those 399.

| Bucket (normalized prose) | Count | Share |
|----------------------------------------|------:|------:|
| Exact                                  |   358 |   90% |
| Near (ratio >= 0.97)                   |    36 |    9% |
| Real difference (ratio < 0.80)         |     5 |    1% |

Exact plus near is 394 of 399, or 99%.
The 5 real differences are not content drift; they are id collisions where the same slug names a different slice in each catalog.
Example: `system-reminder-plan-mode-is-active-5-phase` carries the full plan-file body in the cache (and that body is present in the raw binary), while Piebald's same-named file is nearly empty - the content lives under a different Piebald slug.

End-to-end sample of five, each traced from Piebald file to cache record to binary `strings`:

| id | verdict |
|-------------------------------------------------|--------------------------------|
| `agent-prompt-general-purpose`                  | exact                          |
| `agent-prompt-conversation-summarization`       | exact                          |
| `agent-prompt-coding-session-title-generator`   | exact                          |
| `agent-prompt-explore`                          | near (only `${...}` rendering) |
| `tool-description-grep`                          | near (positional vs. named var, backtick escaping) |

Coverage caveat, distinct from fidelity.
Piebald id-covers 399 of the binary's 1537 extractor-segmented prompts (26%); 158 Piebald slugs do not id-match the binary and 1138 binary ids have no Piebald slug.
Most of that gap is the segmentation-scheme divergence above, not genuinely untracked prompts, and a content-hash bridge would recover much of it.

Provenance tags are unreliable, content is not.
Piebald's frontmatter `ccVersion` agrees with the cache `version` on only 190 of 399 aligned prompts (older on 198, newer on 11), yet the prose is identical on 99%.
The version stamps in both catalogs drift independently of the text; trust the content hash, not the tag.

## Measurement 2: lobotomized pack against 2.1.204

The lobotomized pack shares the tweakcc `id` namespace (tweakcc-fixed is what applies it), so 1296 of its 3219 opus-4-8 files id-match the 2.1.204 binary; the other 1923 are orphans that do not apply to a 2.1.204 install at all.

Content classification of the 1296 applicable overrides:

| Class | Count |
|--------------------------------|------:|
| Verbatim mirror (untouched)    |   688 |
| Rewritten                      |   521 |
| Suppressed (empty body)        |    87 |

608 of the 1296 actually change behavior (rewritten plus suppressed); the rest are catalog copies.

Drift, using each file's own `ccVersion` stamp S against the binary's last-changed tag V for that prompt:

| Relationship | All 1296 | Behavior-changing 608 |
|-------------------------------------------------------|--------:|---------------------:|
| S == V, still aligned                                 |    1092 |                  423 |
| S > V, lobo cut against a *newer* revision than ships |     204 |                  185 |
| S < V, lobo stale-behind                              |       0 |                    0 |

Verdict.
Nothing in the lobotomized pack has drifted stale-behind relative to 2.1.204 - it is uniformly at or ahead of the shipped binary.
423 of its behavior-changing overrides sit on exactly the text 2.1.204 ships and apply cleanly.
185 target a newer revision of the prompt than 2.1.204 contains (its per-file stamps run to 2.1.239), so on a 2.1.204 install those override a pristine text that has since changed upstream, and tweakcc-fixed's hash match would reject or mis-place them.
The README badge of 2.1.187 understates the pack: individual files are stamped as current as 2.1.239, so the pack is effectively a rolling-newer catalog, not a 2.1.187 snapshot.

## Reproduction notes

- Binary cache: `~/.tweakcc/prompt-data-cache/prompts-2.1.204.json`, records under `.prompts[]`.
- Reconstruct a prompt's text: join `pieces[i]` with `${identifiers[i]}` interleaved.
- Piebald baseline: `git -C ~/repos/claude-code-system-prompts show v2.1.204:system-prompts/<id>.md`, strip the leading HTML-comment header for the body.
- Lobotomized: `~/repos/lobotomized-claude-code/system-prompts-opus-4-8/<id>.md`, HTML-comment header carries `ccVersion`, empty body means suppression.
- Normalizer (the load-bearing step): `s.replace('\\`','`').replace('\\$','$')`, then iterate `re.sub(r'\$\{[^{}]*\}','§',s)` to fixpoint, then collapse whitespace.
- Binary string check: `strings -n 6 ~/.local/share/claude/versions/2.1.204 > /tmp/bin.strings && grep -F '<phrase>' /tmp/bin.strings`.
