# Sistema base de auditoría continua

Este directorio agrupa scripts y salidas para auditar el proyecto en capas:

1. Calidad técnica
2. Seguridad estática
3. UX/UI visual manual

## Estructura

- `scripts/`: scripts de ejecución de calidad
- `visual/`: captura y análisis visual autenticado

## Flujo recomendado

### 1. Calidad técnica

```bash
./audits/scripts/run_quality.sh
```

### 2. Auditoría visual manual (autenticada)

```bash
VISUAL_AUDIT_USERNAME=auditor \
VISUAL_AUDIT_PASSWORD='***' \
VISUAL_AUDIT_BASE_URL='http://127.0.0.1:8000' \
OPENAI_API_KEY='sk-...' \
bash audit.sh visual
```

Más detalle en `audits/visual/README.md`.

### 3. Seguridad estática (Bandit + Semgrep)

```bash
bash audit.sh security
```

### 4. Ejecución conjunta

```bash
bash audit.sh all
```

## Limitaciones

Estos scripts no sustituyen revisión manual. Sirven para detectar rápido fallos, deuda técnica y señales de incoherencia visual en un proyecto que evoluciona de forma iterativa.
