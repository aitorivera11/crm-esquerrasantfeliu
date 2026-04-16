# Auditoría visual manual (pantallas autenticadas)

Esta auditoría recorre rutas autenticadas, captura screenshots en desktop/mobile, ejecuta axe opcionalmente y genera un informe UX/UI asistido por OpenAI.

## Estructura

- `audits/visual/routes.json`: rutas a auditar.
- `audits/visual/run_visual_audit.py`: login + captura + axe.
- `audits/visual/analyze_visual_audit.py`: análisis visual IA y generación de informes.
- `audits/visual/run.sh`: orquestador de la auditoría visual.
- `audits/visual/reports/<RUN_ID>/`: salidas por ejecución.
- `audits/visual/reports/audit_visual.md`: último informe consolidado.
- `audits/visual/reports/audit_visual.json`: último JSON consolidado.

## Variables de entorno

Obligatorias para capturas autenticadas:

- `VISUAL_AUDIT_USERNAME`
- `VISUAL_AUDIT_PASSWORD`

Opcionales:

- `VISUAL_AUDIT_BASE_URL` (por defecto `http://127.0.0.1:8000`)
- `VISUAL_AUDIT_RUN_ID` (por defecto timestamp UTC)
- `VISUAL_AUDIT_ANALYZE` (`1` por defecto; `0` para saltar IA)
- `VISUAL_AUDIT_OPENAI_MODEL` (por defecto `gpt-4.1`)
- `OPENAI_API_KEY` (obligatoria solo para análisis IA)

## Ejecución rápida

1. Arranca Django en local.
2. Exporta credenciales del usuario auditor.
3. Lanza la auditoría visual:

```bash
VISUAL_AUDIT_USERNAME=auditor \
VISUAL_AUDIT_PASSWORD='***' \
VISUAL_AUDIT_BASE_URL='http://127.0.0.1:8000' \
OPENAI_API_KEY='sk-...' \
bash audit.sh visual
```

Si quieres solo capturas (sin análisis IA):

```bash
VISUAL_AUDIT_ANALYZE=0 bash audit.sh visual
```

## Qué genera

Por cada ejecución (`reports/<RUN_ID>/`):

- `capture_manifest.json`: metadatos de capturas + estado HTTP + resultados axe (si aplica).
- `audit_visual.json`: hallazgos por pantalla e inconsistencias globales.
- `audit_visual.md`: informe legible con resumen ejecutivo, hallazgos, quick wins y prioridades.

## Configuración de rutas

Edita `audits/visual/routes.json` y añade/quita rutas reales del CRM según módulos que quieras revisar.

Recomendación: incluir listados, formularios y paneles de seguimiento para detectar inconsistencias de patrones UI.

## Limitaciones reales

- El login está preparado para formulario estándar (`username` + `password`) en `/accounts/login/`.
- Rutas con `<id>` dinámico requieren que configures una URL concreta en `routes.json`.
- Axe aporta señales rápidas, pero el foco principal del informe es usabilidad y consistencia visual.
- El análisis IA depende de la calidad de las capturas y del contexto visual disponible en cada pantalla.
