"""Optional Crawl4AI single-page benchmark, not an unrestricted default crawler."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets

from ..evidence import build_capture, evidence_entry, save_json
from ..policy import assert_public_host, normalize_target


async def _capture(url: str, folder: Path) -> None:
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError as exc:
        raise RuntimeError(
            'Install Crawl4AI extra and its required browser dependencies'
        ) from exc
    # Its browser is not governed by the static scanner's robots/scope gates.
    # Use solely on trusted sites where automated access is permitted.
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
    if not result.success:
        raise RuntimeError("Crawl4AI failed: " + str(result.error_message))
    rendered = (result.html or "").encode("utf-8")
    md = result.markdown
    markdown = md.raw_markdown if hasattr(md, "raw_markdown") else str(md or "")
    (folder / "rendered.html").write_bytes(rendered)
    (folder / "content.md").write_text(markdown, encoding="utf-8")
    save_json(
        folder / "capture.json",
        build_capture(
            mode="browser", source_url=url, final_url=url,
            artifacts=[
                evidence_entry(folder, "rendered.html", kind="html-extracted", media_type="text/html"),
                evidence_entry(folder, "content.md", kind="markdown-derived", media_type="text/markdown"),
            ],
            observations={"engine": "crawl4ai"},
            limits=[
                "Crawl4AI experimental adapter only",
                "no inherited static scanner robots/scope/traffic gates",
                "not a trustworthy rendered DOM or complete resource archive",
            ],
        ),
    )


def capture_crawl4ai(url: str, output: Path) -> Path:
    target = normalize_target(url)
    assert_public_host(target)
    directory = Path(output) / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-crawl4ai-" + secrets.token_hex(4)
    )
    directory.mkdir(parents=True, exist_ok=False)
    asyncio.run(_capture(target, directory))
    return directory
