import json
import socket
from types import SimpleNamespace
import sys

import httpx
import pytest

from kneekura_web.adapters.browser import BrowserCaptureConfig, capture_browser, _asset_references
from kneekura_web.policy import TargetRejected


def _public_dns(monkeypatch):
    def fake_dns(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
    monkeypatch.setattr(socket, "getaddrinfo", fake_dns)


@pytest.mark.parametrize("kwargs", [
    {"width": 100}, {"height": 1500}, {"max_requests": 0},
    {"settle_ms": 4000}, {"max_layout_elements": 0},
])
def test_browser_limits(kwargs):
    with pytest.raises(ValueError):
        BrowserCaptureConfig(**kwargs)


def test_asset_inventory_redacts_urls():
    inventory = _asset_references("https://example.org/", {
        "stylesheets": ["/style.css?token=hello"],
        "scripts": ["https://cdn.example.com/app.js?v=123"],
        "images": [{"src": "/logo.png?name=alice", "alt": "logo"}],
    })
    assert len(inventory) == 2  # sensitive token key rejected for stylesheet
    assert inventory[0]["kind"] == "script"
    assert inventory[0]["host_relation"] == "external"
    assert inventory[0]["url_origin"] == "https://cdn.example.com/"
    assert "app.js" not in json.dumps(inventory)
    assert "alice" not in json.dumps(inventory)


def test_robots_gate_blocks_browser_before_launch(tmp_path, monkeypatch):
    _public_dns(monkeypatch)
    calls = []

    def fake_robots(client, origin, settings):
        calls.append(origin)
        return SimpleNamespace(can_fetch=lambda agent, url: False)

    import kneekura_web.adapters.browser as browser
    monkeypatch.setattr(browser, "_robots", fake_robots)
    with pytest.raises(browser.ScanError, match="robots.txt"):
        capture_browser("https://example.org/", tmp_path)
    assert calls == ["https://example.org/"]
    assert not list(tmp_path.iterdir())


def test_browser_capture_mock_produces_full_manifest(tmp_path, monkeypatch):
    _public_dns(monkeypatch)
    import kneekura_web.adapters.browser as browser

    monkeypatch.setattr(browser, "_check_robots", lambda origin, config: None)
    requests = []

    class Route:
        def __init__(self, url, method="GET", resource_type="stylesheet"):
            self.request = SimpleNamespace(url=url, method=method, resource_type=resource_type)
            self.decision = None

        def abort(self):
            self.decision = "abort"

        def continue_(self):
            self.decision = "continue"

    class Page:
        url = "https://example.org/"

        def goto(self, url, *, wait_until, timeout):
            assert url == self.url
            assert wait_until == "domcontentloaded"
            return SimpleNamespace(status=200)

        def wait_for_timeout(self, ms):
            assert ms == 350

        def content(self):
            return (
                '<html><title>Sample</title><body><h1>Title</h1>'
                '<script src="/app.js"></script>'
                '<link rel="stylesheet" href="/style.css"></body></html>'
            )

        def evaluate(self, js, limit):
            assert limit == 60
            return [{"tag": "h1", "box": {"width": 50}}]

        def screenshot(self, *, path, full_page, animations):
            assert not full_page
            assert animations == "disabled"
            with open(path, "wb") as handle:
                handle.write(b"mock screenshot bytes")

    class Context:
        def __init__(self):
            self.route_handler = None
            self.response_handler = None

        def route(self, pattern, callback):
            assert pattern == "**/*"
            self.route_handler = callback

        def route_web_socket(self, pattern, handler):
            assert pattern == "**/*"

        def on(self, event, callback):
            if event == "response":
                self.response_handler = callback

        def new_page(self):
            good = Route("https://example.org/style.css?rev=3")
            outside = Route("https://bad.example.org/a.js")
            unsafe = Route("https://example.org/api", method="POST")
            for route in (good, outside, unsafe):
                self.route_handler(route)
                requests.append(route)
            self.response_handler(SimpleNamespace(url=good.request.url, status=200))
            return Page()

        def close(self):
            pass

    context = Context()

    class Browser:
        def new_context(self, *, accept_downloads, service_workers, viewport, user_agent):
            assert not accept_downloads
            assert service_workers == "block"
            assert viewport == {"width": 1280, "height": 720}
            assert "Kneekura" in user_agent
            return context

        def close(self):
            pass

    class Driver:
        chromium = SimpleNamespace(launch=lambda **kwargs: Browser())

    class Sync:
        def __enter__(self):
            return Driver()

        def __exit__(self, *args):
            pass

    fake_package = SimpleNamespace(__path__=[])
    fake_api = SimpleNamespace(sync_playwright=lambda: Sync())
    monkeypatch.setitem(sys.modules, "playwright", fake_package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_api)

    folder = capture_browser("https://example.org/", tmp_path)
    assert [r.decision for r in requests] == ["continue", "abort", "abort"]
    manifest = json.loads((folder / "capture.json").read_text())
    assert manifest["schema_version"] == "0.2"
    assert manifest["mode"] == "browser"
    assert manifest["observations"]["title"] == "Sample"
    assert len(manifest["artifacts"]) == 6
    for artifact in manifest["artifacts"]:
        assert (folder / artifact["path"]).is_file()
    network = json.loads((folder / "network.json").read_text())
    assert len(network["requests"]) == 3
    assert network["requests"][0]["http_status"] == 200
    assert "style.css" not in json.dumps(network)
    assert "rev=3" not in json.dumps(network)
    assert network["requests"][1]["policy"] == "blocked-off-host"
    assert network["requests"][2]["policy"] == "blocked-unsafe-method"
