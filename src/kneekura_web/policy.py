"""Conservative URL admission and same-host policy.

DNS preflight is defense in depth, not protection against DNS rebinding.
Enforce outbound traffic restrictions externally for untrusted URLs.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import parse_qsl, urlsplit, urlunsplit


class TargetRejected(ValueError):
    """Reject target URLs that violate admission/scope restrictions."""


_SECRET_KEYS = frozenset({
    "token", "access_token", "api_key", "apikey", "auth", "password",
    "secret", "session", "sessionid", "sid", "jwt", "code",
})


def normalize_target(url: str) -> str:
    if not isinstance(url, str) or not url or any(ord(c) <= 32 for c in url):
        raise TargetRejected("URL contains whitespace or control characters")
    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        if scheme not in ("http", "https"):
            raise TargetRejected("Only HTTP(S) URLs are allowed")
        if parts.username is not None or parts.password is not None:
            raise TargetRejected("Credentials embedded in URL are forbidden")
        host = (parts.hostname or "").rstrip(".").lower()
        if not host:
            raise TargetRejected("Missing hostname")
        port = parts.port
        if port not in (None, 443 if scheme == "https" else 80):
            raise TargetRejected("Only default HTTP(S) ports are allowed")
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise TargetRejected("Local/internal hostname is forbidden")
        if any(key.casefold() in _SECRET_KEYS for key, _ in parse_qsl(parts.query)):
            raise TargetRejected("Sensitive URL query parameter is forbidden")
        if ":" not in host:
            host = host.encode("idna").decode("ascii")
        netloc = "[" + host + "]" if ":" in host else host
        return urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))
    except ValueError as exc:
        if isinstance(exc, TargetRejected):
            raise
        raise TargetRejected("Malformed URL") from exc
    except UnicodeError as exc:
        raise TargetRejected("Invalid hostname") from exc


def assert_public_host(url: str) -> None:
    host = urlsplit(url).hostname
    if not host:
        raise TargetRejected("Missing hostname")
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            answers = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise TargetRejected("DNS resolution failed") from exc
        addresses = []
        for answer in answers:
            try:
                addresses.append(ipaddress.ip_address(answer[4][0]))
            except (ValueError, IndexError):
                raise TargetRejected("Unrecognized DNS response") from None
    if not addresses or any(not ip.is_global for ip in addresses):
        raise TargetRejected("Private, reserved or unresolved target address")


def same_host(url: str, origin: str) -> bool:
    return urlsplit(url).hostname == urlsplit(origin).hostname
