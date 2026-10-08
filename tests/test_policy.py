import socket

import pytest

from kneekura_web.policy import TargetRejected, assert_public_host, normalize_target, same_host


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "http://localhost/", "http://internal.local/",
    "https://user:pass@example.org/", "https://example.org:444/",
    "https://example.org/?token=abc", "http://example.org/a b",
    "http://example.org/\nfoo",
])
def test_reject_invalid_urls(url):
    with pytest.raises(TargetRejected):
        normalize_target(url)


def test_normalization_and_scope():
    assert normalize_target("HTTPS://Example.Org/path?x=2#section") == "https://example.org/path?x=2"
    assert same_host("https://example.org/a", "http://example.org/b")
    assert not same_host("https://example.net/a", "https://example.org/b")


def test_private_ip():
    for url in ["http://127.0.0.1/", "http://10.0.0.1/", "http://[::1]/"]:
        with pytest.raises(TargetRejected):
            assert_public_host(normalize_target(url))


def test_mixed_dns_rejected(monkeypatch):
    def fake_dns(host, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ]
    monkeypatch.setattr(socket, "getaddrinfo", fake_dns)
    with pytest.raises(TargetRejected):
        assert_public_host("https://example.org/")
