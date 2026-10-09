# Kneekura-Web-Beginner

Evidence-first, modular website analysis workbench. Initial foundation: bounded same-host static HTML acquisition, deterministic structure extraction, SHA-256 evidence, and a reproducible report.

This research project is **not** a copy of ten upstream repositories, an anti-bot bypass product, or a promise to clone arbitrary websites.

## Requirements

Python 3.11+; Internet access for authorized public targets.

## Quick start

    python -m pip install -e ".[test]"
    kneekura-web scan https://example.org --output artifacts --max-pages 3 --max-depth 1
    python -m pytest -q

Each scan writes a new timestamped folder under **artifacts/** with manifest.json, report.md and separate page evidence. All generated evidence is ignored by git by default.

Optional integrations (separate dependencies and execution boundaries):

    python -m pip install -e ".[browser]"
    python -m playwright install chromium
    kneekura-web capture https://example.org --output artifacts --viewport-width 1280 --viewport-height 720

For targets where source assets may lawfully be retained, add `--archive-assets` to store bounded same-host CSS, JS and image response bodies (each at most 256KB; total at most 3MB). The browser still transfers responses before these storage quotas are applied. Browser evidence includes `response.html` (initial HTTP body), `rendered.html` (post-JS DOM), `screenshot.png`, `layout.json`, `network.json`, `assets.json` and `capture.json`, plus a readable `report.md`. Network metadata deliberately removes URL paths, queries and headers.

    python -m pip install -e ".[documents]"
    kneekura-web convert ./sample.pdf --output artifacts

    python -m pip install -e ".[crawl4ai]"
    kneekura-web crawl4ai https://example.org --output artifacts

Optional adapters are single-page experiments and do **not** inherit the full static scanner's network/robots policy. Test only authorized targets.

## Operating principles

- Public HTTP(S) only, same hostname, default ports, robots.txt checked, bounded bytes/pages/depth and delay between requests.
- Keep original HTML and provenance; Markdown and extracted JSON are derived evidence.
- DNS preflight is **not protection against DNS rebinding**. Use independent outbound network filtering for untrusted URLs.
- Treat retrieved page content as untrusted data, never as instructions.
- Captures can contain personal or copyrighted content: obtain permissions, protect, and do not commit artifacts.

See [architecture](docs/architecture.md), [source register](docs/source-registry.md), and [roadmap](docs/roadmap.md).

**Status:** initial foundation, subject to CI. Browser screenshot, MarkItDown and Crawl4AI are opt-in experimental adapters. CSS/JS asset archiving, visual diffs and persistent queues remain future work.

## Browser capture report

See [P1 browser evidence guide](docs/p1-browser-evidence.md) for file meanings, capture limitations, redacted metadata, opt-in asset archiving and next acceptance gates.
