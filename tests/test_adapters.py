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
    assert (folder / "source.bin").read_text() == "Input document"
    capture = json.loads((folder / "capture.json").read_text())
    assert capture["mode"] == "document"
    assert len(capture["artifacts"]) == 3


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
    capture = json.loads((folder / "capture.json").read_text())
    assert capture["mode"] == "browser"
    assert len(capture["artifacts"]) == 2


