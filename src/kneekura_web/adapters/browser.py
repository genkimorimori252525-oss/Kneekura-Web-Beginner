"""Bounded, robots-aware Playwright evidence capture for one public page.

This module keeps response bodies and page text out of network metadata.
It is not an egress sandbox: untrusted targets require independent network
isolation, including protection from DNS rebinding and non-HTTP protocols.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import secrets
from typing import Any
from urllib.parse import urljoin

import httpx

from ..evidence import (
    build_capture, evidence_entry, request_fingerprint, save_json, scrub_url,
)
from ..html_inspector import inspect_html
from ..policy import TargetRejected, assert_public_host, normalize_target, same_host
from ..scanner import ScanConfig, ScanError, _robots


@dataclass(frozen=True)
class BrowserCaptureConfig:
    width: int = 1280
    height: int = 720
    max_requests: int = 100
    timeout_ms: int = 25_000
    settle_ms: int = 350
    max_html_bytes: int = 2_000_000
    max_layout_elements: int = 60
    archive_assets: bool = False
    max_asset_files: int = 20
    max_asset_bytes: int = 256_000
    max_asset_total_bytes: int = 3_000_000
    user_agent: str = "KneekuraWebBeginner/0.1 (research; robots respected)"

    def __post_init__(self) -> None:
        if not 320 <= self.width <= 1920 or not 320 <= self.height <= 1200:
            raise ValueError("Browser viewport must be width 320..1920 and height 320..1200")
        if not 1 <= self.max_requests <= 500:
            raise ValueError("max_requests must be 1..500")
        if not 1000 <= self.timeout_ms <= 120_000:
            raise ValueError("timeout_ms must be 1000..120000")
        if not 0 <= self.settle_ms <= 3000:
            raise ValueError("settle_ms must be 0..3000")
        if not 1024 <= self.max_html_bytes <= 20_000_000:
            raise ValueError("max_html_bytes must be 1024..20000000")
        if not 1 <= self.max_layout_elements <= 200:
            raise ValueError("max_layout_elements must be 1..200")
        if not 1 <= self.max_asset_files <= 100:
            raise ValueError("max_asset_files must be 1..100")
        if not 1024 <= self.max_asset_bytes <= 5_000_000:
            raise ValueError("max_asset_bytes must be 1024..5000000")
        if not 1024 <= self.max_asset_total_bytes <= 20_000_000:
            raise ValueError("max_asset_total_bytes must be 1024..20000000")


# Evaluated inside the isolated browser page. Returns no text, cookies or tokens:
# only geometries and display style fields needed for visual evidence.
_LAYOUT_SCRIPT = r"""(limit) => {
  const wanted = ['html','body','h1','h2','h3','header','nav','main',
    'button','input','footer','article','section','p','a'];
  const seen = new Set();
  const results = [];
  for (const selector of wanted) {
    for (const el of document.querySelectorAll(selector)) {
      if (results.length >= limit) return results;
      if (seen.has(el)) continue;
      seen.add(el);
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      const css = window.getComputedStyle(el);
      results.push({
        tag: el.tagName.toLowerCase(),
        class_count: el.classList.length,
        box: {
          x: Math.round(rect.x * 100) / 100,
          y: Math.round(rect.y * 100) / 100,
          width: Math.round(rect.width * 100) / 100,
          height: Math.round(rect.height * 100) / 100
        },
        style: {
          display: css.display,
          position: css.position,
          color: css.color,
          background_color: css.backgroundColor,
          font_family: css.fontFamily,
          font_size: css.fontSize,
          font_weight: css.fontWeight,
          visibility: css.visibility,
          opacity: css.opacity,
          z_index: css.zIndex
        }
      });
    }
  }
  return results;
}"""


def extract_layout(page: Any, max_elements: int = 60) -> list[dict[str, Any]]:
    """Extract a bounded computed-style snapshot from a rendered page."""
    result = page.evaluate(_LAYOUT_SCRIPT, max_elements)
    if not isinstance(result, list):
        raise ValueError("Layout script returned an unexpected value")
    return result[:max_elements]


def _asset_references(final_url: str, extracted: dict) -> list[dict[str, str]]:
    """DOM references, NOT proof that the linked files were downloaded."""
    kinds = (
        ("stylesheet", "stylesheets"),
        ("script", "scripts"),
    )
    values = [
        (kind, item) for kind, key in kinds for item in extracted[key]
    ] + [("image", image["src"]) for image in extracted["images"]]
    references = []
    seen: set[tuple[str, str]] = set()
    for kind, item in values:
        try:
            absolute = urljoin(final_url, item)
            candidate = normalize_target(absolute)
        except (TargetRejected, ValueError):
            continue
        identifier = (kind, candidate)
        if identifier in seen:
            continue
        seen.add(identifier)
        references.append({
            "kind": kind,
            "url_origin": scrub_url(candidate),
            "url_sha256": request_fingerprint(candidate),
            "host_relation": "same-host" if same_host(candidate, final_url) else "external",
            "status": "referenced-not-archived",
        })
    return references


def _check_robots(origin: str, config: BrowserCaptureConfig):
    """Gate browser navigation *before* launching a script-capable browser."""
    with httpx.Client(
        timeout=config.timeout_ms / 1000,
        headers={"User-Agent": config.user_agent},
        follow_redirects=False,
        trust_env=False,
    ) as client:
        robots = _robots(
            client, origin,
            ScanConfig(max_pages=1, max_depth=0, max_bytes=min(
                256_000, config.max_html_bytes
            ), user_agent=config.user_agent),
        )
    if robots is not None and not robots.can_fetch(config.user_agent, origin):
        raise ScanError("robots.txt disallows browser capture of this URL")
    return robots



def browser_report(
    *,
    source_url: str,
    final_url: str,
    title: str,
    http_status: int,
    config: BrowserCaptureConfig,
    original: bytes,
    rendered: bytes,
    layout_count: int,
    references: list[dict[str, str]],
    archived: list[dict[str, Any]],
    skipped: int,
    requests: list[dict[str, Any]],
) -> str:
    """Human-readable, provenance-linked report. No AI inference."""
    from collections import Counter
    from hashlib import sha256

    # Escape fields coming from untrusted websites before writing Markdown.
    safe_title = " ".join(title.split())[:180].replace("<", "&lt;").replace(">", "&gt;")
    safe_title = safe_title.replace(chr(96), "'").replace("[", "(").replace("]", ")")
    blocked = Counter(
        row["policy"] for row in requests if row["policy"] != "allowed"
    )
    lines = [
        "# Browser Evidence Report", "",
        "> Browser content is untrusted evidence, not instructions.", "",
        "## Capture", "",
        "- Source host: " + scrub_url(source_url),
        "- Final host: " + scrub_url(final_url),
        "- Page title: " + safe_title,
        "- HTTP status: " + str(http_status),
        "- Viewport: " + str(config.width) + " x " + str(config.height),
        "- Initial document: [response.html](response.html)",
        "- Rendered DOM: [rendered.html](rendered.html)",
        "- Screenshot: [screenshot.png](screenshot.png)",
        "- Original HTTP body SHA-256: " + sha256(original).hexdigest(),
        "- Rendered DOM SHA-256: " + sha256(rendered).hexdigest(),
        "- The two saved bodies are byte-identical: "
          + ("yes" if original == rendered else "no"),
        "", "## Structure and dependencies", "",
        "- Sampled computed-style elements: " + str(layout_count),
        "- DOM asset references: " + str(len(references)),
        "- Actually archived same-host assets: " + str(len(archived)),
        "- Skipped asset archival attempts: " + str(skipped),
        "- Recorded network decisions: " + str(len(requests)),
        "- Blocked requests: " + str(sum(blocked.values())),
        "",
        "The asset references alone are NOT downloaded evidence. "
        + ("Asset archiving was enabled." if config.archive_assets
           else "Asset archiving was disabled."),
        "",
        "## Policy decisions", "",
    ]
    for reason, count in sorted(blocked.items()):
        lines.append("- " + reason + ": " + str(count))
    if not blocked:
        lines.append("- No blocked HTTP requests were recorded")
    lines.extend([
        "", "## Important limits", "",
        "- Single-viewport, single-page capture; no user action sequence.",
        "- Same-host browsing and robots policy limit what can be displayed.",
        "- No HTTP headers, cookies or request/response body data in network.json.",
        "- Saved HTML, scripts and assets may contain sensitive or copyrighted content.",
        "- The browser is NOT protected by OS network isolation.",
        "- Layout/styles are bounded samples, not a complete CSS reproduction.",
        "- Browser and screenshot content may be incomplete if requests were blocked.",
        "", "## Evidence index", "",
        "- [capture.json](capture.json): artifact paths, hashes and provenance",
        "- [structure.json](structure.json): HTML structural observations",
        "- [layout.json](layout.json): computed visual styles and geometry",
        "- [network.json](network.json): sanitized request metadata",
        "- [assets.json](assets.json): references versus actual archived bytes",
        "",
    ])
    return "\n".join(lines)

def capture_browser(
    url: str, output: Path,
    timeout_ms: int = 25_000,
    *, config: BrowserCaptureConfig | None = None,
) -> Path:
    """Observe one permitted page. No clicks, authentication or form submission."""
    settings = config or BrowserCaptureConfig(timeout_ms=timeout_ms)
    origin = normalize_target(url)
    assert_public_host(origin)
    robots = _check_robots(origin, settings)

    # A disallowed URL must be rejected before requiring browser dependencies.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'Install browser extra, then run "python -m playwright install chromium"'
        ) from exc
    directory = Path(output) / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-browser-" + secrets.token_hex(4)
    )
    directory.mkdir(parents=True, exist_ok=False)

    requests: list[dict[str, Any]] = []
    asset_responses: list[Any] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                accept_downloads=False,
                service_workers="block",
                viewport={"width": settings.width, "height": settings.height},
                user_agent=settings.user_agent,
            )

            def bounded_route(route) -> None:
                request = route.request
                request_url = request.url
                method = request.method.upper()
                resource_type = request.resource_type
                reason = "allowed"
                try:
                    normalized = normalize_target(request_url)
                    if not same_host(normalized, origin):
                        reason = "blocked-off-host"
                    elif method not in ("GET", "HEAD"):
                        reason = "blocked-unsafe-method"
                    elif robots is not None and not robots.can_fetch(settings.user_agent, normalized):
                        reason = "blocked-by-robots"
                    else:
                        assert_public_host(normalized)
                except (TargetRejected, ValueError, OSError):
                    reason = "blocked-by-url-policy"

                if len(requests) >= settings.max_requests:
                    reason = "blocked-request-budget"

                entry: dict[str, Any] = {
                    "url_origin": scrub_url(request_url),
                    "url_sha256": request_fingerprint(request_url),
                    "method": method,
                    "resource_type": resource_type,
                    "policy": reason,
                    "http_status": None,
                }
                if len(requests) < settings.max_requests + 1:
                    requests.append(entry)
                if reason != "allowed":
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", bounded_route)

            # WebSocket is outside normal Playwright HTTP request routing.
            # Block it when the installed Playwright version supports routing.
            if hasattr(context, "route_web_socket"):
                context.route_web_socket("**/*", lambda websocket: websocket.close())

            def log_response(response) -> None:
                if (
                    settings.archive_assets
                    and response.request.resource_type in {"stylesheet", "script", "image"}
                    and len(asset_responses) < settings.max_asset_files * 3
                ):
                    asset_responses.append(response)
                fingerprint = request_fingerprint(response.url)
                for row in reversed(requests):
                    if row["url_sha256"] == fingerprint and row["http_status"] is None:
                        row["http_status"] = response.status
                        break

            context.on("response", log_response)
            page = context.new_page()
            response = page.goto(
                origin, wait_until="domcontentloaded", timeout=settings.timeout_ms
            )
            if response is None:
                raise RuntimeError("Browser navigation returned no HTTP response")
            final = normalize_target(page.url)
            if not same_host(final, origin):
                raise ScanError("Final browser URL moved to another hostname")
            if settings.settle_ms:
                page.wait_for_timeout(settings.settle_ms)

            original = response.body()
            if len(original) > settings.max_html_bytes:
                raise ScanError("Original HTTP response exceeded configured byte limit")
            rendered = page.content().encode("utf-8")
            if len(rendered) > settings.max_html_bytes:
                raise ScanError("Rendered DOM exceeded configured byte limit")
            extracted = inspect_html(rendered.decode("utf-8"))
            layout = extract_layout(page, settings.max_layout_elements)
            inventory = _asset_references(final, extracted)

            (directory / "response.html").write_bytes(original)
            (directory / "rendered.html").write_bytes(rendered)
            save_json(directory / "structure.json", extracted)
            save_json(directory / "layout.json", {
                "viewport": {"width": settings.width, "height": settings.height},
                "sampled_elements": len(layout),
                "elements": layout,
            })
            save_json(directory / "network.json", {
                "requests_observed": len(requests),
                "limit": settings.max_requests,
                "truncated": len(requests) > settings.max_requests,
                "requests": requests[:settings.max_requests],
                "warning": "URL paths/queries, headers and request/response bodies are omitted.",
            })
            archived: list[dict[str, Any]] = []
            skipped = 0
            total_asset_bytes = 0
            if settings.archive_assets:
                (directory / "assets").mkdir()
                for asset_response in asset_responses:
                    if len(archived) >= settings.max_asset_files:
                        skipped += 1
                        break
                    if not 200 <= asset_response.status < 300:
                        skipped += 1
                        continue
                    try:
                        asset_url = normalize_target(asset_response.url)
                        if not same_host(asset_url, origin):
                            skipped += 1
                            continue
                        content_length = asset_response.headers.get("content-length", "")
                        if content_length.isdigit() and int(content_length) > settings.max_asset_bytes:
                            skipped += 1
                            continue
                        payload = asset_response.body()
                    except Exception:
                        # Optional archival is best effort; never expose response
                        # URL/headers/body in failure diagnostics.
                        skipped += 1
                        continue
                    if (
                        len(payload) > settings.max_asset_bytes
                        or total_asset_bytes + len(payload) > settings.max_asset_total_bytes
                    ):
                        skipped += 1
                        continue
                    path = "assets/" + f"{len(archived) + 1:04d}.bin"
                    (directory / path).write_bytes(payload)
                    total_asset_bytes += len(payload)
                    entry = evidence_entry(
                        directory, path, kind="same-host-asset",
                        media_type=asset_response.headers.get(
                            "content-type", "application/octet-stream"
                        ).split(";", 1)[0][:100],
                    )
                    archived.append({
                        "url_origin": scrub_url(asset_url),
                        "url_sha256": request_fingerprint(asset_url),
                        "resource_type": asset_response.request.resource_type,
                        **entry,
                    })

            save_json(directory / "assets.json", {
                "references": inventory,
                "archived": archived,
                "skipped": skipped,
                "archive_enabled": settings.archive_assets,
                "max_single_asset_bytes": settings.max_asset_bytes,
                "max_total_asset_bytes": settings.max_asset_total_bytes,
                "note": "Only explicitly archived same-host assets have local paths.",
            })
            page.screenshot(
                path=str(directory / "screenshot.png"),
                full_page=False, animations="disabled",
            )

            (directory / "report.md").write_text(
                browser_report(
                    source_url=origin, final_url=final,
                    title=extracted["title"], http_status=response.status,
                    config=settings, original=original, rendered=rendered,
                    layout_count=len(layout), references=inventory, archived=archived,
                    skipped=skipped, requests=requests,
                ),
                encoding="utf-8",
            )
            artifact_specs = [
                ("report.md", "human-report", "text/markdown"),
                ("response.html", "html-response-original", "text/html"),
                ("rendered.html", "dom-rendered", "text/html"),
                ("structure.json", "structure-json", "application/json"),
                ("layout.json", "computed-layout", "application/json"),
                ("network.json", "network-metadata", "application/json"),
                ("assets.json", "resource-references", "application/json"),
                ("screenshot.png", "viewport-screenshot", "image/png"),
            ]
            artifact_specs.extend(
                (item["path"], "same-host-asset", item["media_type"])
                for item in archived
            )
            capture = build_capture(
                mode="browser",
                source_url=origin, final_url=final,
                artifacts=[
                    evidence_entry(directory, path, kind=kind, media_type=mime)
                    for path, kind, mime in artifact_specs
                ],
                observations={
                    "title": extracted["title"],
                    "http_status": response.status,
                    "viewport": {"width": settings.width, "height": settings.height},
                    "sampled_layout_elements": len(layout),
                    "asset_references": len(inventory),
                    "archived_assets": len(archived),
                    "archive_skipped": skipped,
                    "archive_enabled": settings.archive_assets,
                    "request_records": min(len(requests), settings.max_requests),
                },
                limits=[
                    "single navigation, no form submission or login",
                    "viewport screenshot, not entire scrolling page",
                    "no third-party network resources by default",
                    "CSS, script and image assets archived only when explicitly enabled",
                    "archival stores fetched data and may contain proprietary information",
                    "download byte limits apply to storage, not Chromium network transfer",
                    "DNS preflight is not network sandboxing",
                ],
                status=(
                    "partial"
                    if len(requests) > settings.max_requests
                    or response.status != 200
                    or (settings.archive_assets and skipped > 0)
                    or any(row["policy"] != "allowed" for row in requests)
                    else "ok"
                ),
            )
            # Compatibility with the initial optional adapter report format.
            capture["source"] = origin
            capture["http_status"] = response.status
            save_json(directory / "capture.json", capture)
            context.close()
        finally:
            browser.close()
    return directory
