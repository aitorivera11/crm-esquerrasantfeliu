#!/usr/bin/env bash
# ============================================================
# audit.sh — Auditoría de seguridad Django (Bandit + Semgrep)
# Uso: bash audit.sh [ruta-del-proyecto]
# Ejemplo: bash audit.sh /app  (dentro del contenedor)
#          bash audit.sh /home/user/mi-crm  (en el VPS)
# ============================================================
set -euo pipefail

PROJECT_DIR="${1:-.}"
REPORT_DIR="./media/audit-reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colores
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║          AUDITORÍA DE SEGURIDAD — Django CRM         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

mkdir -p "$REPORT_DIR"

# ────────────────────────────────────────────────────────────
# 1. INSTALAR HERRAMIENTAS SI NO ESTÁN
# ────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Verificando herramientas...${NC}"

pip install --quiet bandit semgrep 2>/dev/null || {
  echo -e "${RED}Error instalando herramientas. Ejecuta: pip install bandit semgrep${NC}"
  exit 1
}
echo -e "${GREEN}✓ Bandit y Semgrep disponibles${NC}"

# ────────────────────────────────────────────────────────────
# 2. BANDIT — Vulnerabilidades en código Python
# ────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/4] Ejecutando Bandit...${NC}"
echo -e "${CYAN}Detecta: SQL injection, ejecución de comandos, contraseñas hardcodeadas,"
echo -e "         uso inseguro de crypto, deserialización peligrosa...${NC}"
echo ""

BANDIT_REPORT="$REPORT_DIR/bandit_${TIMESTAMP}.txt"
BANDIT_JSON="$REPORT_DIR/bandit_${TIMESTAMP}.json"

# Texto legible
bandit -r "$PROJECT_DIR" \
  --exclude "$PROJECT_DIR/venv,$PROJECT_DIR/.venv,$PROJECT_DIR/node_modules,$PROJECT_DIR/static,$PROJECT_DIR/media" \
  -ll \
  -f txt \
  -o "$BANDIT_REPORT" 2>/dev/null || true

# JSON para procesado posterior
bandit -r "$PROJECT_DIR" \
  --exclude "$PROJECT_DIR/venv,$PROJECT_DIR/.venv,$PROJECT_DIR/node_modules,$PROJECT_DIR/static,$PROJECT_DIR/media" \
  -f json \
  -o "$BANDIT_JSON" 2>/dev/null || true

# Mostrar resumen en terminal
bandit -r "$PROJECT_DIR" \
  --exclude "$PROJECT_DIR/venv,$PROJECT_DIR/.venv,$PROJECT_DIR/node_modules,$PROJECT_DIR/static,$PROJECT_DIR/media" \
  -ll 2>/dev/null || true

echo -e "${GREEN}✓ Reporte Bandit guardado en: $BANDIT_REPORT${NC}"

# ────────────────────────────────────────────────────────────
# 3. SEMGREP — Análisis estático avanzado
# ────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/4] Ejecutando Semgrep...${NC}"
echo -e "${CYAN}Detecta: vulnerabilidades Django específicas, OWASP Top 10,"
echo -e "         patrones inseguros, secretos expuestos, CSRF, XSS...${NC}"
echo ""

SEMGREP_REPORT="$REPORT_DIR/semgrep_${TIMESTAMP}.txt"
SEMGREP_JSON="$REPORT_DIR/semgrep_${TIMESTAMP}.json"

# Ruleset combinado: Django + Python security + secrets
semgrep \
  --config "p/django" \
  --config "p/python" \
  --config "p/secrets" \
  --config "p/owasp-top-ten" \
  "$PROJECT_DIR" \
  --exclude "venv" \
  --exclude ".venv" \
  --exclude "node_modules" \
  --exclude "*/migrations/*" \
  --output "$SEMGREP_REPORT" \
  --json-output "$SEMGREP_JSON" \
  --severity ERROR \
  --severity WARNING \
  2>/dev/null || true

# Mostrar en terminal también
semgrep \
  --config "p/django" \
  --config "p/python" \
  --config "p/secrets" \
  --config "p/owasp-top-ten" \
  "$PROJECT_DIR" \
  --exclude "venv" --exclude ".venv" --exclude "*/migrations/*" \
  --severity ERROR --severity WARNING \
  2>/dev/null || true

echo -e "${GREEN}✓ Reporte Semgrep guardado en: $SEMGREP_REPORT${NC}"

# ────────────────────────────────────────────────────────────
# 4. RESUMEN FINAL
# ────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}[4/4] Resumen de reportes generados:${NC}"
echo "──────────────────────────────────────────"
ls -lh "$REPORT_DIR"/*"${TIMESTAMP}"* 2>/dev/null || echo "No se generaron archivos"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗"
echo -e "║  Auditoría completada. Revisa los reportes en:       ║"
echo -e "║  $REPORT_DIR/                           ║"
echo -e "╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Próximos pasos sugeridos:"
echo "  1. Revisa HIGH severity primero (críticos)"
echo "  2. Comparte los .json con una IA para triaje y fixes"
echo "  3. Configura GitHub Actions para auditoría automática"
echo -e "${NC}"
