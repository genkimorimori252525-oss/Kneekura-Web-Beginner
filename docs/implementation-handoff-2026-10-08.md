# Implementation handoff — 2026-10-08

Repository: https://github.com/genkimorimori252525-oss/Kneekura-Web-Beginner

Initial review branch: jolly/web-analysis-foundation-2026-10-08

Review PR: https://github.com/genkimorimori252525-oss/Kneekura-Web-Beginner/pull/1

## Intent

Create a research-grade, source-preserving website inspector that can expand through independent specialist modules. The ten identified GitHub repositories serve as a technology catalogue. The objective is not to combine their entire implementations into one monolith. Different jobs—static crawl, dynamic DOM capture, document conversion, adaptive selectors, large-scale queuing, Android/WebView tests—deserve separate interfaces.

## Implemented so far

- Installable Python package and CLI: scan, capture, convert, crawl4ai.
- Core scan: same-host bounded static HTML, robots gate, errors, source and page timestamps, SHA-256.
- Basic structural observations: title, description, headings, images, links, forms, CSS/JS source references and text excerpt.
- Separate run folder with original acquired HTML and derived JSON/Markdown. No implicit overwrite.
- Playwright/MarkItDown/Crawl4AI opt-in adapters, subject to their own security and dependency limitations.
- Offline pytest scenarios and GitHub Actions matrix Python 3.11/3.13.
- Source registry with links and license metadata for all ten projects and Playwright.

## Validation boundary

GitHub CI covers the Python base and mocked adapter interfaces. It does not guarantee correct output on live websites, browser installation, external package compatibility or CSS/JavaScript fidelity. Browser and Crawl4AI adapters do not yet share the complete static scanner's robots and network policy. Network DNS checks can suffer DNS rebinding. Raw HTML is evidence, NOT a complete website snapshot.

## Next actionable milestone

1. Define a common CaptureResult schema shared by static and rendered/browser captures, with provenance, errors and artifact hashes.
2. Implement per-request policy enforcement suitable for real browsers, plus external egress isolation and redaction.
3. Record rendered DOM, screenshot, viewport, response status and CSS/JS/image dependencies; do not confuse a URL reference with the downloaded asset.
4. Add version-pinned, reproducible fixtures and a small explicitly authorized live smoke suite.
5. Compare Crawl4AI and base scanner on identical fixtures; make fallback routing evidence-driven.
6. Only after this, evaluate Scrapling selector adaptation and controlled Browser Use interaction exploration.
7. Consider Scrapy/Crawlee for queueing at scale; Firecrawl separately due to licensing/feature scope. scrcpy belongs to mobile verification, while curl-impersonate and AutoScraper remain research baselines.

## Regression criteria

- No old run folders overwritten or silently discarded.
- No unauthorized external network requests in CI.
- Never assert a page was captured if no raw evidence was saved.
- An overall run with mixed successes and failures must be marked partial.
- Provide exact dependencies, tags/commit SHAs and license provenance when integrating upstream code.

## P1 continuation status — 2026-10-09

Implemented on the **same draft PR #1**:
- Evidence schema v0.2 and SHA-256 artifact descriptors shared by static scan, optional browser capture, local MarkItDown conversion and Crawl4AI experiment.
- BrowserCaptureConfig with viewport dimensions, request limit, DOM byte limit and bounded style sampling.
- robots.txt gate before launching Chromium; same-host requests, GET/HEAD only, robots per route, WebSocket closure where Playwright supports it.
- Separate original response.html versus rendered.html DOM. Viewport screenshot plus computed layout/styles and structured network/resource metadata.
- Network traces strip URL path, query, headers and request/response bodies; hash request URLs for correlation.
- Opt-in same-host CSS, JS and image archiving with file and byte budgets, plus a report explaining referenced versus saved assets.
- Human-readable browser report.md with checksums, HTTP response and blocked requests. Blocked/capped fetches are marked partial.
- GitHub Actions Python 3.11 + 3.13 and a real Chromium local fixture test, alongside offline adapter mocks.

**Not finished:** secure egress isolation for hostile sites, full Chromium response byte bounds before download, complete CSS/assets/interaction capture, mobile+desktop visual diffs, authorized live site verification, and selection/benchmark of remaining research adapters. All scripts, screenshots and raw documents are gitignored and may contain protected or personal content.

Documentation: docs/p1-browser-evidence.md. **Leave PR #1 draft** until outstanding limitations receive their own review.
