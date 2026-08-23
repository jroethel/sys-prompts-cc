#!/usr/bin/env bash
# pilot-seed-config - build a throwaway CLAUDE_CONFIG_DIR for the SP pilot.
# Usage: pilot-seed-config.sh <config-dir> <model-id>
# Writes <config-dir>/settings.json (seed blob with model pinned) and
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
cp "$ROOT/pilot/curated-claudemd.md" "$D/CLAUDE.md"

echo "CLAUDE_CONFIG_DIR=$D claude --model $M"
