# Sistema base de auditoría continua

Este directorio agrupa scripts, prompts y salidas para auditar el proyecto en cuatro capas:

1. Calidad técnica
2. Seguridad
3. UX/UI
4. Arquitectura

## Estructura

- `prompts/`: prompts reutilizables para auditorías asistidas por IA
- `reports/`: informes generados por scripts o revisiones manuales
- `screenshots/`: capturas generadas con Playwright
- `scripts/`: scripts de ejecución

## Flujo recomendado

### 1. Calidad técnica
```bash
./audits/scripts/run_quality.sh
```

### 2. Auditoría visual
```bash
npm install
npx playwright install --with-deps
BASE_URL=http://127.0.0.1:8000 npm run audit:ui
```

### 3. Escaneo ZAP
```bash
PREPROD_URL=https://pre.example.com ./audits/scripts/run_zap.sh "$PREPROD_URL"
```

### 4. Ejecución conjunta
```bash
PREPROD_URL=https://pre.example.com ./audits/scripts/run_all_audits.sh
```

## Uso con IA

- Pasa código relevante y `audits/reports/code/*` al prompt `prompts/django_code_review.md`
- Pasa screenshots y el HTML report de Playwright al prompt `prompts/ux_audit.md`
- Pasa resultados de ZAP y settings sensibles al prompt `prompts/security_review.md`
- Pasa estructura y módulos principales al prompt `prompts/architecture_review.md`

## Limitaciones

Estos scripts no sustituyen revisión manual. Sirven para detectar rápido fallos, deuda técnica y señales de incoherencia en un proyecto que evoluciona deprisa.
