#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${VISUAL_AUDIT_BASE_URL:-http://127.0.0.1:8000}"
RUN_ID="${VISUAL_AUDIT_RUN_ID:-$(date -u +"%Y%m%d_%H%M%S")}" 
REPORT_ROOT="audits/visual/reports"
MANIFEST_PATH="${REPORT_ROOT}/${RUN_ID}/capture_manifest.json"

python audits/visual/run_visual_audit.py \
  --base-url "$BASE_URL" \
  --run-id "$RUN_ID" \
  --axe

if [[ "${VISUAL_AUDIT_ANALYZE:-1}" == "1" ]]; then
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "VISUAL_AUDIT_ANALYZE=1 pero falta OPENAI_API_KEY; se omite análisis IA."
    exit 0
  fi

  python audits/visual/analyze_visual_audit.py --manifest "$MANIFEST_PATH"
fi

echo "Auditoría visual finalizada. Run: $RUN_ID"
