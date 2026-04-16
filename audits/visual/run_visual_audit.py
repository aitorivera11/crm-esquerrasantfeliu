#!/usr/bin/env python3
"""Run a manual visual audit for authenticated Django screens."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

AXE_SCRIPT_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
DESKTOP_VIEWPORT = {"width": 1536, "height": 960}
MOBILE_DEVICE = {
    "name": "mobile",
    "viewport": {"width": 390, "height": 844},
    "user_agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "is_mobile": True,
    "has_touch": True,
}


@dataclass(frozen=True)
class RouteTarget:
    name: str
    path: str


class AuditError(RuntimeError):
    """Raised when visual audit cannot continue safely."""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "screen"


def load_routes(routes_file: Path) -> list[RouteTarget]:
    payload = json.loads(routes_file.read_text(encoding="utf-8"))
    routes = payload.get("routes", [])
    parsed: list[RouteTarget] = []
    for item in routes:
        if not item.get("name") or not item.get("path"):
            continue
        parsed.append(RouteTarget(name=item["name"], path=item["path"]))
    if not parsed:
        raise AuditError(f"No valid routes found in {routes_file}")
    return parsed


async def login(page: Page, base_url: str, username: str, password: str, timeout_ms: int) -> None:
    login_url = urljoin(base_url, "/accounts/login/")
    await page.goto(login_url, wait_until="networkidle", timeout=timeout_ms)

    await page.fill('input[name="username"]', username)
    await page.fill('input[name="password"]', password)

    await asyncio.gather(
        page.wait_for_url(re.compile(r"^(?!.*accounts/login).*"), timeout=timeout_ms),
        page.click('button[type="submit"]'),
    )


async def run_axe_if_enabled(page: Page, enabled: bool) -> dict[str, Any] | None:
    if not enabled:
        return None

    try:
        await page.add_script_tag(url=AXE_SCRIPT_URL)
        axe_result = await page.evaluate(
            """
            async () => {
                const result = await axe.run(document, {
                    runOnly: {
                        type: 'tag',
                        values: ['wcag2a', 'wcag2aa']
                    }
                });
                return {
                    violations: result.violations.map(v => ({
                        id: v.id,
                        impact: v.impact,
                        description: v.description,
                        help: v.help,
                        helpUrl: v.helpUrl,
                        nodes: v.nodes.length
                    })),
                    incomplete: result.incomplete.length,
                    passes: result.passes.length
                };
            }
            """
        )
        return axe_result
    except Exception as exc:  # pragma: no cover - runtime safeguard
        return {"error": str(exc)}


async def capture_route(
    context: BrowserContext,
    base_url: str,
    route: RouteTarget,
    output_dir: Path,
    timeout_ms: int,
    run_axe: bool,
    device: str,
) -> dict[str, Any]:
    page = await context.new_page()
    absolute_url = urljoin(base_url, route.path)
    route_slug = _slug(route.name)

    result: dict[str, Any] = {
        "route_name": route.name,
        "path": route.path,
        "url": absolute_url,
        "device": device,
        "status": "ok",
    }

    try:
        response = await page.goto(absolute_url, wait_until="networkidle", timeout=timeout_ms)
        status_code = response.status if response else None
        await page.wait_for_timeout(300)

        screenshot_file = output_dir / f"{route_slug}__{device}.png"
        await page.screenshot(path=str(screenshot_file), full_page=True)

        axe_result = await run_axe_if_enabled(page, run_axe)

        result.update(
            {
                "http_status": status_code,
                "title": await page.title(),
                "screenshot": str(screenshot_file),
                "axe": axe_result,
            }
        )

        if status_code and status_code >= 400:
            result["status"] = "http_error"
    except Exception as exc:  # pragma: no cover - runtime safeguard
        result["status"] = "error"
        result["error"] = str(exc)
    finally:
        await page.close()

    return result


async def run_device_pass(
    browser: Browser,
    device: str,
    base_url: str,
    username: str,
    password: str,
    routes: list[RouteTarget],
    run_dir: Path,
    timeout_ms: int,
    run_axe: bool,
) -> list[dict[str, Any]]:
    if device == "desktop":
        context = await browser.new_context(viewport=DESKTOP_VIEWPORT)
    elif device == "mobile":
        context = await browser.new_context(
            viewport=MOBILE_DEVICE["viewport"],
            user_agent=MOBILE_DEVICE["user_agent"],
            is_mobile=MOBILE_DEVICE["is_mobile"],
            has_touch=MOBILE_DEVICE["has_touch"],
        )
    else:
        raise AuditError(f"Unknown device profile: {device}")

    page = await context.new_page()
    await login(page, base_url=base_url, username=username, password=password, timeout_ms=timeout_ms)
    await page.close()

    screenshots_dir = run_dir / "screenshots" / device
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[dict[str, Any]] = []
    for route in routes:
        outputs.append(
            await capture_route(
                context=context,
                base_url=base_url,
                route=route,
                output_dir=screenshots_dir,
                timeout_ms=timeout_ms,
                run_axe=run_axe,
                device=device,
            )
        )

    await context.close()
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run manual visual audit screenshots for authenticated routes.")
    parser.add_argument("--base-url", default=os.getenv("VISUAL_AUDIT_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--routes-file", default="audits/visual/routes.json")
    parser.add_argument("--output-root", default="audits/visual/reports")
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--timeout-ms", type=int, default=20000)
    parser.add_argument("--devices", default="desktop,mobile", help="Comma separated: desktop,mobile")
    parser.add_argument("--axe", action="store_true", help="Enable axe checks per captured screen")
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()

    username = os.getenv("VISUAL_AUDIT_USERNAME")
    password = os.getenv("VISUAL_AUDIT_PASSWORD")
    if not username or not password:
        raise AuditError("VISUAL_AUDIT_USERNAME and VISUAL_AUDIT_PASSWORD are required.")

    routes = load_routes(Path(args.routes_file))

    run_dir = Path(args.output_root) / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    selected_devices = [d.strip() for d in args.devices.split(",") if d.strip()]
    if not selected_devices:
        raise AuditError("No devices selected. Use --devices desktop,mobile")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        all_results: list[dict[str, Any]] = []
        for device in selected_devices:
            all_results.extend(
                await run_device_pass(
                    browser=browser,
                    device=device,
                    base_url=args.base_url,
                    username=username,
                    password=password,
                    routes=routes,
                    run_dir=run_dir,
                    timeout_ms=args.timeout_ms,
                    run_axe=args.axe,
                )
            )
        await browser.close()

    manifest = {
        "run_id": args.run_id,
        "base_url": args.base_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "routes_file": str(Path(args.routes_file)),
        "devices": selected_devices,
        "axe_enabled": args.axe,
        "results": all_results,
    }

    manifest_file = run_dir / "capture_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Visual capture done. Manifest: {manifest_file}")
    return 0


def main() -> int:
    try:
        return asyncio.run(async_main())
    except AuditError as exc:
        print(f"[visual-audit] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
