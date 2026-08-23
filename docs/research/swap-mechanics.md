# Swap mechanics: runtime levers for changing Claude Code's system prompt

Research ticket: https://github.com/jroethel/sys-prompts-cc/issues/2

Verification method: static only.
Every claim below was checked against `claude --help`, the installed native binary, or the local tweakcc extract.
No live Claude session was launched and no model was called.

## Environment verified

- Symlink `~/.local/bin/claude` -> `~/.local/share/claude/versions/2.1.204` (a single Mach-O arm64 executable, not a directory).
- Two native binaries sit side by side already: `2.1.174` (223 MB) and `2.1.204` (237 MB), each a standalone Mach-O file.
- No npm/global-node install of `@anthropic-ai/claude-code` on this host (only Homebrew's `node_modules`, which does not contain it).
- tweakcc working dir `~/.tweakcc/` holds the extract-patch-splice artifacts: `native-binary.backup`, `native-claudejs-orig.js`, `native-claudejs-patched.js`, `config.json`, and hash manifests.

## Surfaces (the four things a "system prompt" is made of)

- Main system prompt: the top-level persona/instructions block sent as the API `system` parameter.
- Tool descriptions: the per-tool text in the API `tools` array, re-sent every request.
- Per-turn system-reminders: `<system-reminder>` blocks injected into user messages each turn (97 references in the binary).
- Subagent prompts: the system prompt handed to Task/Agent-tool subagents.

The distinction matters because no CLI flag touches tool descriptions or system-reminders.
Those two surfaces are baked into the binary and only binary patching (tweakcc) rewrites them.

## Lever-by-lever findings

| Lever                              | Surface changed            | Replace vs append | Side-by-side same host |
|------------------------------------|----------------------------|-------------------|------------------------|
| `--system-prompt` / `-file`        | Main SP only               | Replace           | Yes (per-launch argv)  |
| `--append-system-prompt` / `-file` | Main SP only               | Append            | Yes (per-launch argv)  |
| `outputStyle` (flag/settings)      | Main SP behavior slice     | Partial replace   | Yes (per-launch/config)|
| `appendSystemPrompt` (settings)    | Main SP only               | Append            | Yes (per --settings)   |
| `appendSubagentSystemPrompt`       | Subagent SP only           | Append            | Yes (per --settings)   |
| `--agents` / `--agent`             | Subagent SP                | Replace (per def) | Yes (per-launch argv)  |
| tweakcc / tweakcc-fixed patch      | Main SP + tools + reminders| Replace or cut    | Only with binary copies|
| Multiple pre-patched binaries      | All of the above           | Per-binary        | Yes (invoke by path)   |

### 1. `--system-prompt` and `--system-prompt-file`

Both exist in the 2.1.204 binary (7 string references each), though only `--system-prompt` appears in the main `--help` list.
The `-file` variants are documented under the `--bare` flag ("`--system-prompt[-file]`") and enforced in code.
The binary carries the guard `Error: Cannot use both --system-prompt and --system-prompt-file. Please use only one.`
This is a full replace of the main system prompt: `--help` states `--exclude-dynamic-system-prompt-sections` is "ignored with `--system-prompt`", meaning the flag already supplants the default's dynamic sections (cwd, env, git, memory) rather than layering on them.
It changes the main SP only; tool descriptions and system-reminders are unaffected.

### 2. `--append-system-prompt` and `--append-system-prompt-file`

Both exist in the binary, guarded by `Error: Cannot use both --append-system-prompt and --append-system-prompt-file.`
Help text: "Append a system prompt to the default system prompt."
This is the lever the `fixing-smartass-opus-5` repo uses (`--append-system-prompt-file <file>`).
It appends to the main SP only.

In the init config, `systemPrompt` and `appendSystemPrompt` are independent fields.
The only mutual-exclusion errors are string-vs-file within each pair; there is no error combining replace with append.
So `--system-prompt-file base.md --append-system-prompt-file extra.md` is legal: your base replaces the default, then your appendix is added after it.

### 3. Output styles

`outputStyle` is a real settings.json key and a session config field ("Controls the output style for assistant responses").
Built-ins are `default`, `Explanatory`, `Learning`; custom styles load from `output-styles/` dirs, files, or plugins.
Output styles modify the main system prompt's assistant-behavior slice, not the whole prompt, and do not touch tool descriptions or system-reminders.
Treat "partial replace of the main SP behavior section" as the documented design (inferred from the config wiring plus Claude Code's output-styles feature, not from a byte-level trace).
Not a full-replacement lever.

### 4. Settings.json and env vars

Settings keys that alter a prompt surface: `outputStyle`, `appendSystemPrompt` (schema: `S.string().optional()`), and `appendSubagentSystemPrompt`.
`appendSubagentSystemPrompt` is the only settings lever aimed at the subagent surface; it appends, does not replace.
A `--settings <file-or-json>` argument lets each launch carry its own settings blob, so these are per-launch selectable too.

No user-facing environment variable injects or replaces the system prompt.
The `CLAUDE_CODE_*SYSTEM*` strings in the binary are internal (`CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT` backs `--bare`/`CLAUDE_CODE_SIMPLE=1`, plus GB-feature and mid-conversation flags).
`--bare` swaps in a minimal built-in system prompt; it is a coarse on/off, not a content-injection channel.

### 5. Subagent prompts

`--agents <json>` and `--agent <name>` set subagent definitions per launch (each carries its own `prompt`, a full replace for that agent).
`appendSubagentSystemPrompt` (settings) appends to every subagent's SP.
CLI `--system-prompt` / `--append-system-prompt` apply to the top-level session, not to subagents.

### 6. tweakcc / tweakcc-fixed binary patching

Do not apply; read only. Mechanism, per `~/repos/lobotomized-claude-code/README.md` and the `~/.tweakcc/` artifacts:

- tweakcc-fixed extracts the embedded `cli.js` from the native binary (`native-claudejs-orig.js`), matches each prompt to its pristine text by id, splices in the override text (or an empty body to suppress a prompt outright), and writes the patched bundle back into the binary (`native-claudejs-patched.js` -> binary).
- This is the only lever that reaches all three baked-in surfaces at once: main system prompts, tool descriptions, and per-turn `<system-reminder>` injections (the lobotomized repo has `system-prompts/` and `system-reminders/` sets).
- It is a persistent, whole-install mutation. `--apply` must be re-run after each Claude Code update; `--restore` reverts.
- Because it mutates the one installed binary, a single binary can hold exactly one patched state at a time.
Two different patched states cannot run side by side unless you keep two different binary files.

### 7. Fast-swapping whole installs

The native layout already proves multiple full binaries coexist: `2.1.174` and `2.1.204` are both present as standalone executables.
Nothing stops you from copying the binary to `claude-eng` and `claude-design`, patching each with a different tweakcc set once, and having a just recipe invoke the absolute path per launch.
The `~/.local/bin/claude` symlink is a single global selector and is the wrong tool for side-by-side; invoking the binary by absolute path in the recipe sidesteps it.
An npm-install variant (a `cli.js` under `node_modules`) would give the same result with cheaper copies, but that install form is not present on this host.
Patching is a one-time prep step per variant; launch just selects a pre-patched binary, so "no re-patching at launch time" holds.

## Answer to the feasibility question

Full-replacement swapping at execution time, per launch, without re-patching is feasible, with the answer depending on how much of the prompt "full" means.

- If "full system prompt" means the main system prompt body (the persona/instructions block), it is trivially feasible today with zero patching: `just eng` runs `--system-prompt-file eng.md` and `just design` runs `--system-prompt-file design.md` off the same stock binary, side by side, differing only in argv.
`--system-prompt` is a genuine full replace of the main SP (it even supplants the dynamic env sections), so the two recipes boot materially different main prompts, not just appendices.
- If "full" must also include tool descriptions and per-turn system-reminders, CLI flags cannot reach those.
You then pre-patch two binary copies with tweakcc (one `eng`, one `design`), and the recipe invokes each by absolute path.
Patching is one-time prep, launch is pure selection, so it still meets "per launch, no re-patching."

The target picture (`just eng` vs `just design` booting materially different full system prompts) is confirmed on both readings.
The clean, dependency-free build is the `--system-prompt-file` route; reach for multi-binary tweakcc only when the pilot needs to vary tool descriptions or system-reminders too.

## Flagged observation (inferred, worth a look before the pilot)

The installed `2.1.204` binary appears to already carry a tweakcc patch, and the active set is the retired Fable-5 one, not the Opus-4.8 set the lobotomized README calls live.
Basis: `~/.tweakcc/systemPromptAppliedHashes.json` and the binary share an identical mtime (Aug 22 20:29), and `~/.tweakcc/system-prompts` symlinks to `lobotomized-claude-code/system-prompts-fable-5`.
This is inferred from mtimes plus the symlink target, not a byte-level diff, and nothing here was modified.
If true, any A/B pilot has a non-stock, mismatched baseline and should `tweakcc --restore` (or pin a clean binary copy) before measuring.

## Correction (2026-08-22, post-review)

The inferred claim above that the installed binary is tweakcc-patched to the Fable-5 set is wrong in direction.
Byte-level checks (all 1420 appliedHashes entries null; stock "act when ready" phrasing present in the binary, lobotomized-only sentence absent) show the 20:29:47 write was a `--restore`.
The live install is stock 2.1.204; the ~/.tweakcc/system-prompts symlink only selects what a future `--apply` would use.
