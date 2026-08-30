#!/usr/bin/env bash
# pilot-seed-config - build a throwaway CLAUDE_CONFIG_DIR for the SP pilot.
# Usage: pilot-seed-config.sh <config-dir> <model-id>
# Writes <config-dir>/settings.json (seed blob with model pinned),
# <config-dir>/.claude.json (onboarding complete, bypass-permissions warning
# accepted, oauthAccount copied from the live ~/.claude.json so no login
# screen), <config-dir>/.credentials.json (OAuth token copied from the login
# keychain, mode 600 - the binary's keychain service name is derived from the
# config dir, so a redirected dir cannot see the default keychain item and
# needs the file fallback; verified by headless probe 2026-08-29), and
# <config-dir>/CLAUDE.md (curated test profile). Never writes outside
# <config-dir>. Last stdout line is the ready-to-paste launch command.
set -euo pipefail
export LC_ALL=C

D="${1:?usage: pilot-seed-config.sh <config-dir> <model-id>}"
M="${2:?usage: pilot-seed-config.sh <config-dir> <model-id>}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$D"
python3 - "$ROOT/pilot/settings-seed.json" "$D/settings.json" "$M" <<'PY'
import json, sys
seed, out, model = sys.argv[1], sys.argv[2], sys.argv[3]
settings = json.load(open(seed, encoding='utf-8'))
settings['model'] = model
with open(out, 'w', encoding='utf-8') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')
PY
python3 - "$D/.claude.json" "$HOME/.claude.json" <<'PY'
import json, sys
out, live = sys.argv[1], sys.argv[2]
cfg = {
    "hasCompletedOnboarding": True,
    "theme": "dark",
    "bypassPermissionsModeAccepted": True,
    "projects": {},
}
with open(live, encoding='utf-8') as f:
    acct = json.load(f).get('oauthAccount')
if acct:
    cfg['oauthAccount'] = acct
with open(out, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
PY

if security find-generic-password -s "Claude Code-credentials" -w > "$D/.credentials.json" 2>/dev/null; then
  chmod 600 "$D/.credentials.json"
else
  rm -f "$D/.credentials.json"
  echo "pilot-seed-config: WARNING no 'Claude Code-credentials' keychain item; pane will demand /login" >&2
fi

cp "$ROOT/pilot/curated-claudemd.md" "$D/CLAUDE.md"

echo "CLAUDE_CONFIG_DIR=$D claude --model $M"
