import socket

import httpx

from kneekura_web.scanner import ScanConfig, run_scan


def _fake_dns(monkeypatch):
    def public_dns(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)


def test_partial_collection_not_reported_complete(tmp_path, monkeypatch):
    _fake_dns(monkeypatch)

    def handle(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/":
            return httpx.Response(
                200, headers={"content-type": "text/html"},
                text='<title>Start</title><a href="/missing">Broken</a>'
            )
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        folder, manifest = run_scan(
            "https://example.org/", tmp_path,
            ScanConfig(max_pages=2, delay_seconds=0), client=client
        )
    assert manifest["status"] == "partial"
    assert manifest["summary"] == {"succeeded": 1, "failed": 1}
    assert manifest["robots_status"] == "not_found"
    assert "Successful: 1, failed: 1" in (folder / "report.md").read_text()


def test_unavailable_robots_fails_closed(tmp_path, monkeypatch):
    _fake_dns(monkeypatch)
    requested = []

    def handle(request):
        requested.append(request.url.path)
        return httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        _, manifest = run_scan(
            "https://example.org/", tmp_path,
            ScanConfig(delay_seconds=0), client=client
        )
    assert requested == ["/robots.txt"]
    assert manifest["status"] == "failed"
    assert manifest["robots_status"] == "unavailable"
    assert manifest["summary"] == {"succeeded": 0, "failed": 1}
