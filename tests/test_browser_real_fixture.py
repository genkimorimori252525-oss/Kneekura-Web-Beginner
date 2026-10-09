"""Real Chromium integration smoke: inline fixture, zero public website access."""
from __future__ import annotations

import json

import pytest

from kneekura_web.adapters.browser import extract_layout
from kneekura_web.html_inspector import inspect_html


def test_real_chromium_renders_inline_html_fixture(tmp_path):
    playwright_api = pytest.importorskip("playwright.sync_api")
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 980, "height": 700})
            # A fixture page that only renders from HTML passed in memory.
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(
                """
                <!doctype html><html><head><title>Fixture Example</title>
                <style>body{margin:0}h1{font-size:32px;color:rgb(5,10,15)}</style>
                </head><body><main><h1 id="result">Original</h1>
                <button id="tap">Tap</button></main>
                <script>document.getElementById('result').textContent='Rendered JS';</script>
                </body></html>
                """,
                wait_until="load",
            )
            assert page.locator("#result").inner_text() == "Rendered JS"
            rendered = page.content()
            observed = inspect_html(rendered)
            assert observed["title"] == "Fixture Example"
            assert observed["headings"][0]["text"] == "Rendered JS"
            layout = extract_layout(page, max_elements=25)
            heading = next(row for row in layout if row["tag"] == "h1")
            assert heading["style"]["font_size"] == "32px"
            assert heading["style"]["color"] == "rgb(5, 10, 15)"
            assert heading["box"]["width"] > 0
            image_path = tmp_path / "fixture.png"
            page.screenshot(path=str(image_path), full_page=False, animations="disabled")
            assert image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            context.close()
        finally:
            browser.close()
