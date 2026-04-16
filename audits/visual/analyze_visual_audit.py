#!/usr/bin/env python3
"""Analyze visual audit screenshots with OpenAI and produce Markdown + JSON reports."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

SYSTEM_PROMPT = """
Eres un auditor senior de UX/UI para aplicaciones de gestión internas (CRM), experto en interfaces de pantallas autenticadas con tablas, formularios y navegación lateral.
Tu objetivo es detectar problemas reales de usabilidad y consistencia visual, no hacer observaciones superficiales ni únicamente de accesibilidad.
Sé concreto, accionable y prioriza hallazgos por impacto real en uso diario.
""".strip()

PER_SCREEN_PROMPT_TEMPLATE = """
Analiza una pantalla del CRM a partir de capturas desktop y mobile.
Ruta: {path}
Nombre interno: {route_name}

Evalúa explícitamente estos criterios:
- consistencia visual
- jerarquía visual
- claridad de las acciones principales
- legibilidad
- contraste aparente
- espaciado
- alineación
- densidad de contenido
- claridad de formularios
- claridad de tablas/listados
- orientación/navegación
- carga cognitiva
- responsive

Formato de salida JSON estricto:
{{
  "route_name": "...",
  "path": "...",
  "severity": "alta|media|baja",
  "findings": [
    {{
      "title": "...",
      "impact": "...",
      "evidence": "...",
      "recommendation": "...",
      "priority": "P1|P2|P3"
    }}
  ],
  "quick_wins": ["..."],
  "summary": "..."
}}
""".strip()

CROSS_SCREEN_PROMPT = """
Recibirás resultados por pantalla de una auditoría visual CRM.
Debes detectar incoherencias globales entre listados, detalles y formularios.

Busca específicamente:
- headers distintos sin motivo
- botones primarios inconsistentes
- patrones UI distintos para cosas equivalentes
- diferencias arbitrarias de espaciado o estructura
- sensación de app poco unificada

Devuelve JSON estricto:
{
  "global_inconsistencies": [
    {
      "title": "...",
      "impact": "...",
      "affected_routes": ["/ruta1/", "/ruta2/"],
      "recommendation": "...",
      "priority": "P1|P2|P3"
    }
  ],
  "executive_summary": "...",
  "priority_plan": [
    {
      "priority": "P1|P2|P3",
      "action": "...",
      "expected_result": "..."
    }
  ]
}
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze visual audit screenshots with OpenAI.")
    parser.add_argument("--manifest", required=True, help="capture_manifest.json path")
    parser.add_argument("--model", default=os.getenv("VISUAL_AUDIT_OPENAI_MODEL", "gpt-4.1"))
    return parser.parse_args()


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _group_by_route(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in results:
        route_name = item["route_name"]
        grouped.setdefault(
            route_name,
            {"route_name": route_name, "path": item["path"], "captures": {}, "axe": {}},
        )
        grouped[route_name]["captures"][item["device"]] = item.get("screenshot")
        if item.get("axe") is not None:
            grouped[route_name]["axe"][item["device"]] = item["axe"]
    return grouped


def _analyze_route(client: OpenAI, model: str, route_data: dict[str, Any]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [
        {"type": "input_text", "text": PER_SCREEN_PROMPT_TEMPLATE.format(**route_data)}
    ]

    for device in ("desktop", "mobile"):
        image_path = route_data.get("captures", {}).get(device)
        if image_path:
            content.append(
                {
                    "type": "input_text",
                    "text": f"Captura {device}:",
                }
            )
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"file://{Path(image_path).resolve()}",
                }
            )

    if route_data.get("axe"):
        content.append(
            {
                "type": "input_text",
                "text": "Resultado axe (contexto complementario):\n" + json.dumps(route_data["axe"], ensure_ascii=False),
            }
        )

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": content},
        ],
        text={"format": {"type": "json_object"}},
    )

    output_text = response.output_text
    return json.loads(output_text)


def _analyze_cross(client: OpenAI, model: str, screen_results: list[dict[str, Any]]) -> dict[str, Any]:
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": CROSS_SCREEN_PROMPT},
                    {
                        "type": "input_text",
                        "text": json.dumps(screen_results, ensure_ascii=False),
                    },
                ],
            },
        ],
        text={"format": {"type": "json_object"}},
    )
    return json.loads(response.output_text)


def _render_markdown(
    manifest: dict[str, Any],
    screen_results: list[dict[str, Any]],
    cross_result: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# Auditoría visual CRM")
    lines.append("")
    lines.append(f"- Run ID: `{manifest['run_id']}`")
    lines.append(f"- Fecha (UTC): `{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"- Base URL: `{manifest['base_url']}`")
    lines.append("")
    lines.append("## Resumen ejecutivo")
    lines.append("")
    lines.append(cross_result.get("executive_summary", "Sin resumen ejecutivo."))
    lines.append("")
    lines.append("## Hallazgos por pantalla")
    lines.append("")

    for item in screen_results:
        lines.append(f"### {item.get('route_name')} ({item.get('path')})")
        lines.append(f"Severidad global: **{item.get('severity', 'media')}**")
        lines.append("")

        for finding in item.get("findings", []):
            lines.append(f"- **{finding.get('title', 'Hallazgo')}** ({finding.get('priority', 'P2')})")
            lines.append(f"  - Impacto: {finding.get('impact', 'N/D')}")
            lines.append(f"  - Evidencia: {finding.get('evidence', 'N/D')}")
            lines.append(f"  - Recomendación: {finding.get('recommendation', 'N/D')}")

        quick_wins = item.get("quick_wins", [])
        if quick_wins:
            lines.append("  - Quick wins:")
            for quick_win in quick_wins:
                lines.append(f"    - {quick_win}")

        lines.append("")

    lines.append("## Inconsistencias globales")
    lines.append("")
    for inconsistency in cross_result.get("global_inconsistencies", []):
        lines.append(f"- **{inconsistency.get('title', 'Inconsistencia')}** ({inconsistency.get('priority', 'P2')})")
        lines.append(f"  - Impacto: {inconsistency.get('impact', 'N/D')}")
        lines.append(f"  - Rutas afectadas: {', '.join(inconsistency.get('affected_routes', []))}")
        lines.append(f"  - Recomendación: {inconsistency.get('recommendation', 'N/D')}")

    lines.append("")
    lines.append("## Quick wins")
    lines.append("")
    quick_wins = []
    for item in screen_results:
        quick_wins.extend(item.get("quick_wins", []))

    for quick_win in sorted(set(quick_wins)):
        lines.append(f"- {quick_win}")

    lines.append("")
    lines.append("## Prioridades de mejora")
    lines.append("")
    for plan in cross_result.get("priority_plan", []):
        lines.append(f"- **{plan.get('priority', 'P2')}**: {plan.get('action', 'N/D')}")
        lines.append(f"  - Resultado esperado: {plan.get('expected_result', 'N/D')}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required for visual analysis.")
        return 2

    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)
    grouped_routes = _group_by_route(manifest.get("results", []))

    client = OpenAI()

    screen_results: list[dict[str, Any]] = []
    for route_data in grouped_routes.values():
        screen_results.append(_analyze_route(client, args.model, route_data))

    cross_result = _analyze_cross(client, args.model, screen_results)

    run_dir = manifest_path.parent
    json_output = {
        "manifest": manifest,
        "screen_results": screen_results,
        "cross_result": cross_result,
    }
    report_json = run_dir / "audit_visual.json"
    report_json.write_text(json.dumps(json_output, indent=2, ensure_ascii=False), encoding="utf-8")

    report_md = run_dir / "audit_visual.md"
    report_md.write_text(
        _render_markdown(manifest=manifest, screen_results=screen_results, cross_result=cross_result),
        encoding="utf-8",
    )

    latest_md = Path("audits/visual/reports/audit_visual.md")
    latest_json = Path("audits/visual/reports/audit_visual.json")
    latest_md.write_text(report_md.read_text(encoding="utf-8"), encoding="utf-8")
    latest_json.write_text(report_json.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Visual AI analysis complete: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
