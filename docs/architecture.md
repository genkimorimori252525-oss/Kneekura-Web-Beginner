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
