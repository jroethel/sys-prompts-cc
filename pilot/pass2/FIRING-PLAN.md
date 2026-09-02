# Pass 2 firing plan (reduced set, generation A/B)

Status 2026-09-02: STAGED, not fired. Jeremy cut pass 2 to 5 illustrative pairs (upgrade happens
regardless; this pass locates where the new generation needs prompt adjustment, not go/no-go).
Checkpoint B is resolved: variant model `claude-fable-5` (basis in `pilot/pass2/README.md`).
Config dirs seeded (`/tmp/sp-pass2-stock` opus-4-8, `/tmp/sp-pass2-variant` fable-5); shared-state
snapshot at `/tmp/sp-pass2-state-before.txt`. Blinding seed for this pass: 2.

Every fire needs the VARIANT_BIN override (justfile default points at the pass-1 opus build):

| Window | Tier   | Command |
| ---    | ---    | ---     |
| 1      | light  | `VARIANT_BIN=$HOME/.local/share/claude-code-pilot/2.1.204-variant-fable5 just pilot-batch pass2 2 supervisor-review-rating-pushback terminal-mux-comparison` |
| 2      | medium | `VARIANT_BIN=$HOME/.local/share/claude-code-pilot/2.1.204-variant-fable5 just pilot-batch pass2 2 model-intel-refresh-skill-worker changelog-research-interrupted` |
| 3      | heavy  | `VARIANT_BIN=$HOME/.local/share/claude-code-pilot/2.1.204-variant-fable5 just pilot-batch pass2 2 wayfinder-roadmap-blast-radius` |

Why these five (axes from the pass-1 judge record, `pilot/pass1/fable-judgments.md`):

- changelog-research-interrupted: execute-vs-stall temperament plus interrupt protocol.
- terminal-mux-comparison: fabrication profile, objectively arbitrable by live fetch.
- wayfinder-roadmap-blast-radius: pinned-world discipline vs live-state contamination.
- supervisor-review-rating-pushback: voice, house style, pushback quality (no clean pass-1 result).
- model-intel-refresh-skill-worker: worker-contract control for done-condition discipline.

Skipped: spec-axis (pass-1 tie), self-manual and molt (token furnaces, axes covered above),
substack/vaultwise/triage/loop-brainstorm (duplicate axes at higher cost).
5 pairs cannot satisfy the formal 6-non-tie gate; add loop-brainstorm-partner as a sixth if the
formal verdict ever matters.

Notes carried from pass 1: the instrument includes the auth auto-refresh and the await_answer
wait-race fix; fable-5 panes will burn quota faster than opus panes, so keep one batch per window.
After capture, judging can rerun the pass-1 protocol (blind Fable judges, keys sealed until all
verdicts recorded).
