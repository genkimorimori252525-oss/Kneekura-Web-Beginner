"""Offline API-contract tests for optional adapters (not live integration proof)."""
from __future__ import annotations

import json
from pathlib import Path
import socket
import sys
from types import ModuleType, SimpleNamespace

from kneekura_web.adapters.browser import capture_browser
from kneekura_web.adapters.crawl4ai import capture_crawl4ai
from kneekura_web.adapters.documents import convert_document


def _public_dns(monkeypatch):
    def public_address(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
    monkeypatch.setattr(socket, "getaddrinfo", public_address)


def test_local_markitdown_conversion(tmp_path, monkeypatch):
    mod = ModuleType("markitdown")

    class FakeMarkItDown:
        def __init__(self, enable_plugins):
            assert not enable_plugins

        def convert(self, path):
            assert Path(path).read_text() == "Input document"
            return SimpleNamespace(text_content="# Converted\n")

    mod.MarkItDown = FakeMarkItDown
    monkeypatch.setitem(sys.modules, "markitdown", mod)
    source = tmp_path / "example.txt"
    source.write_text("Input document")
    folder = convert_document(source, tmp_path / "results")
    assert (folder / "converted.md").read_text() == "# Converted\n"
    metadata = json.loads((folder / "conversion.json").read_text())
    assert metadata["source_filename"] == "example.txt"
    assert "source_sha256" in metadata


def test_crawl4ai_adapter_fake_browser(tmp_path, monkeypatch):
    _public_dns(monkeypatch)
    mod = ModuleType("crawl4ai")

    class FakeAsyncWebCrawler:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def arun(self, *, url):
            assert url == "https://example.org/"
            return SimpleNamespace(
                success=True, html="<h1>Hi</h1>",
                markdown=SimpleNamespace(raw_markdown="# Hi"),
            )

    mod.AsyncWebCrawler = FakeAsyncWebCrawler
    monkeypatch.setitem(sys.modules, "crawl4ai", mod)
    folder = capture_crawl4ai("https://example.org/", tmp_path)
    assert (folder / "rendered.html").read_text() == "<h1>Hi</h1>"
    assert (folder / "content.md").read_text() == "# Hi"


def test_playwright_adapter_fake_browser(tmp_path, monkeypatch):
    _public_dns(monkeypatch)

    class Page:
        url = "https://example.org/"

        def goto(self, url, *, wait_until, timeout):
            assert url == self.url
            assert wait_until == "domcontentloaded"
            return SimpleNamespace(status=200)

        def content(self):
            return "<html><body>Rendered</body></html>"

        def screenshot(self, *, path, full_page):
            assert full_page
            Path(path).write_bytes(b"fake png")

    class Context:
        route_handler = None

        def route(self, pattern, callback):
            assert pattern == "**/*"
            self.route_handler = callback

        def new_page(self):
            return Page()

        def close(self):
            pass

    context = Context()

    class Browser:
        def new_context(self, *, accept_downloads, service_workers):
            assert not accept_downloads
            assert service_workers == "block"
            return context

        def close(self):
            pass

    class Driver:
        chromium = SimpleNamespace(launch=lambda **kwargs: Browser())

    class EnterPlaywright:
        def __enter__(self):
            return Driver()

        def __exit__(self, *args):
            return None

    fake_parent = ModuleType("playwright")
    fake_parent.__path__ = []
    fake_sync = ModuleType("playwright.sync_api")
    fake_sync.sync_playwright = lambda: EnterPlaywright()
    monkeypatch.setitem(sys.modules, "playwright", fake_parent)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync)

    folder = capture_browser("https://example.org/", tmp_path)
    assert (folder / "rendered.html").exists()
    assert (folder / "screenshot.png").read_bytes() == b"fake png"
    assert json.loads((folder / "capture.json").read_text())["http_status"] == 200

    class Route:
        def __init__(self, url):
            self.request = SimpleNamespace(url=url)
            self.action = None

        def abort(self):
            self.action = "abort"

        def continue_(self):
            self.action = "continue"

    outside = Route("https://other.org/")
    inside = Route("https://example.org/page")
    internal = Route("http://127.0.0.1/")
    for route in (outside, inside, internal):
        context.route_handler(route)
    assert [route.action for route in (outside, inside, internal)] == [
        "abort", "continue", "abort"
    ]
