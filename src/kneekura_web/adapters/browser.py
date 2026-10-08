"""One-page Playwright screenshot/DOM experiment. Opt-in only.

Browser-initiated HTTP requests are limited to the seed hostname. This may
break cross-origin assets and is NOT OS-level network isolation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets

from ..policy import TargetRejected, assert_public_host, normalize_target, same_host


def capture_browser(url: str, output: Path, timeout_ms: int = 30_000) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'Install browser extra, then run "python -m playwright install chromium"'
        ) from exc
    origin = normalize_target(url)
    assert_public_host(origin)
    directory = Path(output) / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-browser-" + secrets.token_hex(4)
    )
    directory.mkdir(parents=True, exist_ok=False)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                accept_downloads=False, service_workers="block"
            )

            def scope_route(route) -> None:
                try:
                    candidate = normalize_target(route.request.url)
                    if not same_host(candidate, origin):
                        raise TargetRejected("Off-host resource blocked")
                    assert_public_host(candidate)
                except (TargetRejected, ValueError, OSError):
                    route.abort()
                    return
                route.continue_()

            context.route("**/*", scope_route)
            page = context.new_page()
            response = page.goto(
                origin, wait_until="domcontentloaded", timeout=timeout_ms
            )
            if response is None:
                raise RuntimeError("Page navigation returned no response")
            final = normalize_target(page.url)
            if not same_host(final, origin):
                raise RuntimeError("Browser was redirected to a different host")
            rendered = page.content().encode("utf-8")
            (directory / "rendered.html").write_bytes(rendered)
            page.screenshot(path=str(directory / "screenshot.png"), full_page=True)
            metadata = {
                "source": origin,
                "final_url": final,
                "http_status": response.status,
                "rendered_html_sha256": sha256(rendered).hexdigest(),
                "limitations": [
                    "single page",
                    "no robots gate in experimental adapter",
                    "cross-host resources blocked",
                    "not an operating-system network sandbox",
                ],
            }
            (directory / "capture.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            context.close()
        finally:
            browser.close()
    return directory
