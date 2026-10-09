# Architecture / evidence contract

## Purpose

Research-oriented, modular website analysis. Preserve raw observations, support independent specialized tools, compare them against the same fixtures, and avoid overstating fidelity.

## Static evidence schema v0.1

Each **scan** creates a new, non-overwriting directory:

- manifest.json — seed URL, configuration, collection timestamps, errors and per-page status.
- report.md — human/AI-readable report, with explicit limitations.
- pages/NNNN/raw.html — stored HTTP response body; transfer-encoding may be decoded by the HTTP client.
- pages/NNNN/extracted.json — title, description, headings, links, images, CSS/JS references, forms and excerpt.
- pages/NNNN/page.md — a lossy text preview; the original HTML remains the primary evidence.
- SHA-256 in manifest for each successful stored HTML file.

Every failed acquisition is recorded as a failure; absent data must not be treated as success. Each run is separate; generated artifacts are excluded from git.

## Component boundaries

1. **Target admission:** HTTP(S), no URL-embedded credentials, default ports, public DNS preflight.
2. **Acquisition:** robots.txt first; same-host redirects; bounded static request and crawl budgets.
3. **Evidence:** immutable per-run folder, raw body and hashes, structured error records.
4. **Derivation:** deterministic HTML observations; optional independent Markdown converters.
5. **Analysis:** reports cite the page and source artifact; any textual website instructions are untrusted.
6. **Extensions:** Playwright browser evidence; Crawl4AI; MarkItDown; later adaptive selectors and scale engines.

## Limitations/security

DNS preflight cannot rule out DNS rebinding between lookup and actual connection. Use a dedicated network sandbox/firewall to block private destinations for truly untrusted URLs. robots.txt allows explicit rules; if fetching robots fails or returns anything except 200/404/410, the scanner fails closed. Approval to fetch is distinct from permission to republish assets. Avoid secrets in URLs, cookies and saved documents.

The optional **capture** and **crawl4ai** commands do not inherit the static scan's complete robots/traffic policy. Browser capture blocks third-party resources and service workers; this changes appearance and behavior. It is a research-only experiment and not a safe arbitrary-URL browser service. Protect untrusted document conversion similarly.

Do not claim complete site coverage, pixel-perfect fidelity, code reproduction, or visual equivalence from static HTML alone.

## Pending work

Actual stylesheet/script/media archiving, request tracing and redaction, DOM interaction recording, browser/network policy parity, viewport-based rendering, visual diffs, JS runtime observations, adaptive CSS selectors, queue persistence, multi-site orchestration and comprehensive live integration testing.

## Browser P1 evidence

The optional Playwright capture now stores `response.html` (initial document body) and `rendered.html` (post-JavaScript DOM) separately. Those sources may diverge after hydration. A viewport screenshot, bounding boxes/computed styles for a bounded element sample, structure.json, and sanitized network metadata form additional evidence. Network metadata retains HTTP status, request method, resource category, policy outcome, host-only URL and SHA-256 correlation fingerprint, never raw query strings, cookies, request headers or bodies.

`assets.json` always inventories DOM references; by default these are *not* actual resource bytes. The opt-in `--archive-assets` flag saves bounded same-host CSS/JS/images, preserving byte hashes and media types. These files can contain copyrighted assets or sensitive information and must stay local/authorized. Storage budgets are not equivalent to network response byte budgets. Browser capture checks robots.txt before Chromium starts, then checks scope and robots for routed GET/HEAD requests, blocks off-host HTTP and WebSockets (when browser supports the routing API), and limits request count. It is not a complete protection against unsafe scripts or network-level rebinding.

P1 browser implementation is still **single-page, single-viewport**. It does not guarantee all network requests are observed, complete CSS coverage, deterministic sites, or visual fidelity. The only automated actual-Chromium test uses inline HTML fixture; live target integration and adversarial egress tests remain pending.

Browser P1 also produces report.md with a checksum-based comparison of the original document body and rendered DOM, evidence-file links, viewport, archived-versus-referenced asset counts and blocked-request policy outcomes. Difference in saved byte sequences is **not** automatically proof of meaningful JavaScript behavior. Reports state these limitations rather than asserting pixel-perfect reproduction.
