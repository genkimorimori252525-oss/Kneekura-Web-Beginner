"""Optional Crawl4AI single-page benchmark, not an unrestricted default crawler."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets

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
    (folder / "capture.json").write_text(
        json.dumps({
            "source": url, "rendered_html_sha256": sha256(rendered).hexdigest(),
            "markdown_sha256": sha256(markdown.encode("utf-8")).hexdigest(),
            "warning": "Experimental adapter: no inherited robots/crawl limits.",
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
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
