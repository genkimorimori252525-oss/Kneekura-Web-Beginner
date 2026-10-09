# Execution roadmap

Preservation-first: add capabilities without deleting prior original evidence. Keep systems independent unless benchmarks justify integrating them.

## P0 — foundation shipped to feature branch

- Python package, CLI, GitHub CI, deterministic offline tests.
- Bounded static HTML scanner with robots, same-host queue, byte/page/depth limits.
- Manifest and per-page raw HTML, SHA-256, extracted structures and report.
- Research register for all ten upstream repositories, including licenses and limitations.
- Optional experimental entrypoints for Playwright, MarkItDown and Crawl4AI.

## P1 — stronger browser evidence

- Verify optional adapters with fixed dependency versions and repeatable test sites.
- Real DOM, layout, screenshot, CSS and JS dependencies, resource request metadata.
- DOM and response provenance, viewport/interaction states, visual comparison.
- Harmonize scope, robots and network isolation across adapters. No remote browser on untrusted arbitrary URLs until this is done.

## P2 — adaptive extraction

- Benchmark Crawl4AI vs core scanner on a consistent corpus.
- Scrapling selector adaptation with drift detection and false-match reporting.
- MarkItDown file-type fixtures, source hashes, error/size budgets.
- Browser Use for opt-in interaction exploration, then export deterministic actions.

## P3 — scale and specialization

- Compare Scrapy and Crawlee on retry rate, memory, scheduling and failure modes.
- Evaluate Firecrawl separately (hosted vs self-hosted; AGPL review).
- Add Android/WebView lab using scrcpy only if mobile-only targets demand it.
- curl-impersonate and AutoScraper as bounded comparative research, not default bypass strategies.

## Quality gates

1. CI passes offline on Python 3.11 and 3.13.
2. Every successful acquisition has raw evidence, timestamp and SHA-256.
3. Robots, scope, redirects, payload limits and failure status are tested.
4. No hidden login, bot bypass or unlimited crawling.
5. Before copying code: exact upstream commit, version and license review.
6. Any reproduction claim needs separate visual/behavioral evidence rather than generated Markdown.

## P1 progress checkpoint (2026-10-09)

- Implemented common capture metadata and hashed artifacts shared between static HTML and browser mode.
- Playwright browser now records source response vs rendered DOM, viewport screenshot, bounded layout/computed style sample and sanitized request metadata.
- Optional bounded same-host asset archival; disabled by default and guarded by `--archive-assets`.
- CI includes a real Chromium test that renders a local in-memory fixture, in addition to mocked policy/adapter tests.
- Still pending: OS-level egress isolation, full redaction of captured source content, retry/backoff, cross-viewport visual comparison, browser operation trace, and authorized live-site regression tests.
