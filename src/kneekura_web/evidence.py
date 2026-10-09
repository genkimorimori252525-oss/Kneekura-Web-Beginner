"""Shared capture evidence contract for static and browser workflows.

Raw artifact bytes are authoritative; derived Markdown is never source truth.
All artifact paths are relative to a per-capture directory and checksummed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.2"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def evidence_entry(
    directory: Path, relative_path: str,
    *, kind: str, media_type: str,
) -> dict[str, Any]:
    """Produce one portable, tamper-evident artifact descriptor.

    The checksum is over bytes actually written, not an in-memory source that
    may differ from disk encoding or transport decompression.
    """
    root = Path(directory).resolve()
    path = (root / relative_path).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Evidence artifact must be a file within the capture directory")
    body = path.read_bytes()
    return {
        "kind": kind,
        "path": path.relative_to(root).as_posix(),
        "media_type": media_type,
        "size_bytes": len(body),
        "sha256": sha256(body).hexdigest(),
    }


def build_capture(
    *,
    mode: str,
    source_url: str,
    final_url: str,
    artifacts: list[dict[str, Any]],
    observations: dict[str, Any],
    limits: list[str],
    captured_at: str | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    if mode not in {"static", "browser", "document"}:
        raise ValueError("Unknown acquisition mode")
    if status not in {"ok", "partial", "error"}:
        raise ValueError("Unknown capture status")
    if not artifacts and status == "ok":
        raise ValueError("Successful capture must have a physical evidence artifact")
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "status": status,
        "source_url": source_url,
        "final_url": final_url,
        "captured_at": captured_at or utc_now(),
        "artifacts": artifacts,
        "observations": observations,
        "limitations": limits,
    }


def save_json(path: Path, obj: dict[str, Any]) -> None:
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def scrub_url(url: str) -> str:
    """Remove query, fragment and userinfo from potentially sensitive request URLs.

    Paths may also contain sensitive tokens and should only be disclosed when
    explicitly authorized. Keep a pseudonymous hashed request identifier.
    """
    from urllib.parse import urlsplit, urlunsplit

    try:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"}:
            return "[non-http-url]"
        host = parts.hostname or ""
        if not host:
            return "[invalid-url]"
        port = ":" + str(parts.port) if parts.port else ""
        netloc = ("[" + host + "]" if ":" in host else host) + port
        return urlunsplit((parts.scheme, netloc, "/", "", ""))
    except ValueError:
        return "[invalid-url]"


def request_fingerprint(url: str) -> str:
    """Correlate requests without persisting unredacted URLs."""
    return sha256(url.encode("utf-8", errors="replace")).hexdigest()
