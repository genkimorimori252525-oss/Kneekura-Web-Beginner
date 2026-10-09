"""Small CLI: scanning is conservative by default; adapters are opt-in."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .policy import TargetRejected
from .scanner import ScanConfig, run_scan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kneekura-web", description="Evidence-first website analysis"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="bounded, robots-aware static crawl")
    scan.add_argument("url")
    scan.add_argument("--output", type=Path, default=Path("artifacts"))
    scan.add_argument("--max-pages", type=int, default=3)
    scan.add_argument("--max-depth", type=int, default=1)
    scan.add_argument("--max-bytes", type=int, default=2_000_000)
    scan.add_argument("--delay", type=float, default=1.0)

    browser = sub.add_parser("capture", help="optional Playwright screenshot and DOM")
    browser.add_argument("url")
    browser.add_argument("--output", type=Path, default=Path("artifacts"))
    browser.add_argument("--viewport-width", type=int, default=1280)
    browser.add_argument("--viewport-height", type=int, default=720)
    browser.add_argument("--max-requests", type=int, default=100)
    browser.add_argument("--timeout-ms", type=int, default=25000)
    browser.add_argument("--settle-ms", type=int, default=350)
    browser.add_argument("--archive-assets", action="store_true", help="store bounded same-host CSS/JS/images; authorized targets only")

    doc = sub.add_parser("convert", help="optional MarkItDown document conversion")
    doc.add_argument("path", type=Path)
    doc.add_argument("--output", type=Path, default=Path("artifacts"))

    crawl = sub.add_parser("crawl4ai", help="experimental single-page Crawl4AI")
    crawl.add_argument("url")
    crawl.add_argument("--output", type=Path, default=Path("artifacts"))

    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            directory, manifest = run_scan(
                args.url, args.output,
                ScanConfig(
                    max_pages=args.max_pages,
                    max_depth=args.max_depth,
                    max_bytes=args.max_bytes,
                    delay_seconds=args.delay,
                ),
            )
            print("Evidence: " + str(directory))
            print("Pages: " + str(len(manifest["pages"])))
            print("Result: " + manifest["status"])
            return 0 if manifest["status"] == "completed" else 2
        if args.command == "capture":
            from .adapters.browser import BrowserCaptureConfig, capture_browser
            result = capture_browser(
                args.url, args.output,
                config=BrowserCaptureConfig(
                    width=args.viewport_width,
                    height=args.viewport_height,
                    max_requests=args.max_requests,
                    timeout_ms=args.timeout_ms,
                    settle_ms=args.settle_ms,
                    archive_assets=args.archive_assets,
                ),
            )
        elif args.command == "convert":
            from .adapters.documents import convert_document
            result = convert_document(args.path, args.output)
        else:
            from .adapters.crawl4ai import capture_crawl4ai
            result = capture_crawl4ai(args.url, args.output)
        print("Evidence: " + str(result))
        return 0
    except (TargetRejected, ValueError, RuntimeError, OSError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 2
