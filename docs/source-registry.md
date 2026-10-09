# Web analysis source registry — 2026-10-08

Discovery: Marco | IA public X thread, with all ten positions identified from user-provided screenshots. These are **reference sources** and independent options, not ten bundled dependencies.

| # | Upstream | License from GitHub repository metadata | Capability and decision |
|---|---|---|---|
| 1 | [Microsoft MarkItDown](https://github.com/microsoft/markitdown) | MIT | File/Office/PDF-to-Markdown; optional local converter |
| 2 | [Crawl4AI](https://github.com/unclecode/crawl4ai) | Apache-2.0 | Web crawling and AI-ready Markdown; opt-in benchmark |
| 3 | [Firecrawl](https://github.com/firecrawl/firecrawl) | AGPL-3.0 | Managed/self-hosted extraction; compare rather than copy |
| 4 | [Browser Use](https://github.com/browser-use/browser-use) | MIT | AI-controlled navigation; later operator with action trace |
| 5 | [Crawlee](https://github.com/apify/crawlee) | Apache-2.0 | Node.js queue/crawl execution; conditional scale adapter |
| 6 | [Scrapy](https://github.com/scrapy/scrapy) | BSD-3-Clause | Python high-scale crawl; conditional scale adapter |
| 7 | [Scrapling](https://github.com/D4Vinci/Scrapling) | BSD-3-Clause | Adaptive element selection; future structural comparison |
| 8 | [scrcpy](https://github.com/Genymobile/scrcpy) | Apache-2.0 | Android/device/WebView validation; separate specialization |
| 9 | [curl-impersonate](https://github.com/lwthiker/curl-impersonate) | MIT | TLS/HTTP client impersonation; study only, not a browser |
| 10 | [AutoScraper](https://github.com/alirezamika/autoscraper) | MIT | Example-driven extraction, future baseline |
| Extra | [Playwright](https://github.com/microsoft/playwright-python) | Apache-2.0 | Browser DOM and screenshot evidence; opt-in experiment |

Metadata is a discovery starting point, **not** a legal license assessment. Verify exact tag, package and file licenses before any vendoring or redistribution. Source repository code and hosted product features can differ: Firecrawl Cloud is not identical to its basic self-hosted stack. Upstream releases vary in age: curl-impersonate's last upstream release was in 2024; AutoScraper's last listed release was in 2022 at the time of research. Claims of evading anti-scraping measures or replacing paid platforms are not established by star counts.

## Acquisition strategy

Core foundation uses Python standard library and HTTPX; it does not copy ten source trees. Dependencies are isolated by extras. Browser Use, Scrapling, large-scale crawlers, Firecrawl, scrcpy, curl-impersonate and AutoScraper are **not yet integrated**. Create reproducible corpus benchmarks, review licenses and decide based on the job rather than enabling every tool.

Never bypass authentication or access controls; target websites only with authorization, robots/traffic policy and independent egress restrictions.
