import hashlib
import json
import socket

import httpx

from kneekura_web.scanner import ScanConfig, run_scan


def _allow_public_dns(monkeypatch):
    def fake_dns(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
    monkeypatch.setattr(socket, "getaddrinfo", fake_dns)


def test_evidence_scan(tmp_path, monkeypatch):
    _allow_public_dns(monkeypatch)
    seen = []

    def handler(request):
        seen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/":
            return httpx.Response(200, headers={"content-type": "text/html"},
                                  content=b'<title>Home</title><h1>Hi</h1><a href="/about">About</a>')
        if request.url.path == "/about":
            return httpx.Response(200, headers={"content-type": "text/html"},
                                  content=b'<title>About</title><p>About us</p>')
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        output, manifest = run_scan("https://example.org/", tmp_path,
                                    ScanConfig(max_pages=2, max_depth=1, delay_seconds=0),
                                    client=client)
    assert seen == ["/robots.txt", "/", "/about"]
    assert manifest["status"] == "completed"
    assert len(manifest["pages"]) == 2
    page = manifest["pages"][0]
    assert hashlib.sha256((output / page["raw_path"]).read_bytes()).hexdigest() == page["sha256"]
    assert (output / "report.md").exists()
    assert json.loads((output / "manifest.json").read_text())["status"] == "completed"


def test_robots_disallow(tmp_path, monkeypatch):
    _allow_public_dns(monkeypatch)
    requests = []

    def handler(request):
        requests.append(request.url.path)
        return httpx.Response(200, headers={"content-type": "text/plain"},
                              content=b"User-agent: *\nDisallow: /\n")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        _, manifest = run_scan("https://example.org/", tmp_path,
                               ScanConfig(delay_seconds=0), client=client)
    assert requests == ["/robots.txt"]
    assert manifest["status"] == "failed"
    assert "robots.txt" in manifest["pages"][0]["error"]


def test_cross_host_redirect(tmp_path, monkeypatch):
    _allow_public_dns(monkeypatch)
    requests = []

    def handler(request):
        requests.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "https://other.org/path"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        _, manifest = run_scan("https://example.org/", tmp_path,
                               ScanConfig(delay_seconds=0), client=client)
    assert requests == ["/robots.txt", "/"]
    assert manifest["status"] == "failed"
    assert "hostname" in manifest["pages"][0]["error"]


def test_response_byte_limit(tmp_path, monkeypatch):
    _allow_public_dns(monkeypatch)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * 3000)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        _, manifest = run_scan("https://example.org/", tmp_path,
                               ScanConfig(max_bytes=1024, delay_seconds=0), client=client)
    assert manifest["pages"][0]["status"] == "error"
    assert "limit" in manifest["pages"][0]["error"]
