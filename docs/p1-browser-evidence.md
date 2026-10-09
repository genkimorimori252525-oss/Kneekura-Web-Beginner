# P1 browser evidence — implemented 2026-10-09

This page describes what **exists in code** versus what remains unverified. The browser adapter is an optional Playwright single-page experiment. The default static scanner requires no Chromium.

## Install and run on a permitted public website

    python -m pip install -e ".[browser,test]"
    python -m playwright install chromium
    kneekura-web capture https://example.org --output artifacts

Choose a viewport and request budget:

    kneekura-web capture https://example.org --viewport-width 390 --viewport-height 844 --max-requests 70

On sites where preservation of fetched assets is permitted:

    kneekura-web capture https://example.org --archive-assets

The last option archives only eligible same-host CSS, JS and images, bounded by file count, file size and total saved bytes. It does **not** prevent Chromium from downloading oversized assets before rejection; network transfer budgets require additional infrastructure.

## Files in a successful browser evidence folder

| Path | Interpretation |
|---|---|
| response.html | HTTP main-document response body obtained from Chromium; response may already be transfer-decoded |
| rendered.html | Current DOM serialized after page scripts had an opportunity to run |
| screenshot.png | Viewport screenshot; **not** full-page and not pixel-fidelity proof |
| structure.json | Title, headings, links, forms, image/CSS/JS references, short text excerpt |
| layout.json | Sample of bounded element geometries and computed styles |
| network.json | Sanitized same-host/off-host request decisions, resource type and HTTP status when observed |
| assets.json | Referenced resource fingerprint inventory plus optional physically archived files |
| assets/NNNN.bin | Optional same-host CSS, JS or image bytes; only when --archive-assets is enabled |
| capture.json | Shared v0.2 metadata, artifact SHA-256 digests, URLs, acquisition limits |
| report.md | Human-readable evidence index and limitations |

The schema intentionally separates **reference**, **observed request**, and **saved bytes**. A stylesheet URL discovered in the HTML is not evidence that the stylesheet was downloaded. HTML body differing from rendered DOM is not necessarily proof of meaningful script behavior; DOM serialization alone can change markup.

## Policy and privacy

- Robots rules are checked before Chromium starts, then applied on HTTP request routes.
- Only same-host public HTTP(S), default ports and GET/HEAD are allowed via route policy. Other requests are blocked.
- WebSocket routing is blocked where the Playwright version exposes its route API. Service workers and downloads are disabled.
- Request metadata never records cookies, headers, URL paths or query strings; it stores only an origin and a SHA-256 identifier for correlation.
- Browser body/DOM/screenshot/captured CSS/JS **can still contain private or copyrighted content**. Keep local, secure and authorized.
- A scanner DNS check is not pinned to browser DNS resolution, so this is **not** an SSRF-safe sandbox for hostile URLs.
- Third-party CDN assets are blocked by default, which can make the screenshot incomplete. Capture reports mark blocked requests as partial.
- Do not add user authentication, credential replay, form submission, CAPTCHA bypass or arbitrary request methods without a separate authorized design.

## Automated evidence

The core Actions matrix tests static, policy and adapter contracts on Python 3.11 and 3.13. A separate Actions job installs Chromium and executes a **local HTML/CSS/JS fixture**, asserting computed CSS, changed DOM content and valid screenshot PNG bytes. This is an actual browser smoke but not an external live-site acceptance check.

## Next acceptance gate

1. Independently enforce network egress isolation (private address blocks pinned to connection, DNS rebind defense, response/asset transfer quotas).
2. Capture per-viewport evidence and perform bounded visual/layout comparison, with explicit differences and failures.
3. Add deterministic user action traces for authorized interactive sites; avoid unbounded LLM browser plans.
4. Pin full dependency lockfile and introduce documented authorized external smoke site(s).
5. Only then evaluate Scrapling dynamic selector adaptation, Browser Use navigation planning, and Crawl4AI feature parity.
