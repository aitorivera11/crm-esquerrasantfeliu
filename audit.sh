#!/usr/bin/env bash
# ============================================================
# audit.sh — Auditorías para Django CRM
#
# Modos:
#   bash audit.sh security [ruta-proyecto]
#   bash audit.sh visual
#   bash audit.sh all [ruta-proyecto]
#   bash audit.sh [ruta-proyecto]   # compatibilidad (security)
# ============================================================
set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

run_security_audit() {
  local project_dir="$1"
  local report_dir="./media/audit-reports"
  local timestamp
  timestamp=$(date +"%Y%m%d_%H%M%S")

  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════════════════╗"
  echo "║          AUDITORÍA DE SEGURIDAD — Django CRM         ║"
  echo "╚══════════════════════════════════════════════════════╝"
  echo -e "${NC}"

  mkdir -p "$report_dir"

  echo -e "${YELLOW}[1/4] Verificando herramientas...${NC}"
  pip install --quiet bandit semgrep 2>/dev/null || {
    echo -e "${RED}Error instalando herramientas. Ejecuta: pip install bandit semgrep${NC}"
    exit 1
  }
  echo -e "${GREEN}✓ Bandit y Semgrep disponibles${NC}"

  echo ""
  echo -e "${YELLOW}[2/4] Ejecutando Bandit...${NC}"
  echo -e "${CYAN}Detecta: SQL injection, ejecución de comandos, contraseñas hardcodeadas,"
  echo -e "         uso inseguro de crypto, deserialización peligrosa...${NC}"
  echo ""

  local bandit_report="$report_dir/bandit_${timestamp}.txt"
  local bandit_json="$report_dir/bandit_${timestamp}.json"

  bandit -r "$project_dir" \
    --exclude "$project_dir/venv,$project_dir/.venv,$project_dir/node_modules,$project_dir/static,$project_dir/media" \
    -ll -f txt -o "$bandit_report" 2>/dev/null || true

  bandit -r "$project_dir" \
    --exclude "$project_dir/venv,$project_dir/.venv,$project_dir/node_modules,$project_dir/static,$project_dir/media" \
    -f json -o "$bandit_json" 2>/dev/null || true

  bandit -r "$project_dir" \
    --exclude "$project_dir/venv,$project_dir/.venv,$project_dir/node_modules,$project_dir/static,$project_dir/media" \
    -ll 2>/dev/null || true

  echo -e "${GREEN}✓ Reporte Bandit guardado en: $bandit_report${NC}"

  echo ""
  echo -e "${YELLOW}[3/4] Ejecutando Semgrep...${NC}"
  echo -e "${CYAN}Detecta: vulnerabilidades Django específicas, OWASP Top 10,"
  echo -e "         patrones inseguros, secretos expuestos, CSRF, XSS...${NC}"
  echo ""

  local semgrep_report="$report_dir/semgrep_${timestamp}.txt"
  local semgrep_json="$report_dir/semgrep_${timestamp}.json"

  semgrep \
    --config "p/django" \
    --config "p/python" \
    --config "p/secrets" \
    --config "p/owasp-top-ten" \
    "$project_dir" \
    --exclude "venv" \
    --exclude ".venv" \
    --exclude "node_modules" \
    --exclude "*/migrations/*" \
    --output "$semgrep_report" \
    --json-output "$semgrep_json" \
    --severity ERROR \
    --severity WARNING \
    2>/dev/null || true

  semgrep \
    --config "p/django" \
    --config "p/python" \
    --config "p/secrets" \
    --config "p/owasp-top-ten" \
    "$project_dir" \
    --exclude "venv" --exclude ".venv" --exclude "*/migrations/*" \
    --severity ERROR --severity WARNING \
    2>/dev/null || true

  echo -e "${GREEN}✓ Reporte Semgrep guardado en: $semgrep_report${NC}"

  echo ""
  echo -e "${CYAN}[4/4] Resumen de reportes generados:${NC}"
  echo "──────────────────────────────────────────"
  ls -lh "$report_dir"/*"${timestamp}"* 2>/dev/null || echo "No se generaron archivos"
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════════════╗"
  echo -e "║  Auditoría completada. Revisa los reportes en:       ║"
  echo -e "║  $report_dir/                           ║"
  echo -e "╚══════════════════════════════════════════════════════╝${NC}"
  echo ""
}

run_visual_audit() {
  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════════════════╗"
  echo "║            AUDITORÍA VISUAL MANUAL — CRM             ║"
  echo "╚══════════════════════════════════════════════════════╝"
  echo -e "${NC}"

  if [[ -z "${VISUAL_AUDIT_USERNAME:-}" || -z "${VISUAL_AUDIT_PASSWORD:-}" ]]; then
    echo -e "${RED}Faltan variables VISUAL_AUDIT_USERNAME y VISUAL_AUDIT_PASSWORD.${NC}"
    exit 2
  fi

  pip install --quiet playwright openai 2>/dev/null || {
    echo -e "${RED}Error instalando dependencias visuales. Ejecuta: pip install playwright openai${NC}"
    exit 1
  }

  python -m playwright install chromium 2>/dev/null || {
    echo -e "${RED}No se pudo instalar Chromium para Playwright.${NC}"
    exit 1
  }

  ./audits/visual/run.sh
}

MODE="security"
PROJECT_DIR="."

if [[ $# -gt 0 ]]; then
  case "$1" in
    security|visual|all)
      MODE="$1"
      PROJECT_DIR="${2:-.}"
      ;;
    *)
      MODE="security"
      PROJECT_DIR="$1"
      ;;
  esac
fi

case "$MODE" in
  security)
    run_security_audit "$PROJECT_DIR"
    ;;
  visual)
    run_visual_audit
    ;;
  all)
    run_security_audit "$PROJECT_DIR"
    run_visual_audit
    ;;
  *)
    echo "Modo no soportado: $MODE"
    exit 2
    ;;
esac
