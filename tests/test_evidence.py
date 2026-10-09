from hashlib import sha256
from pathlib import Path

import pytest

from kneekura_web.evidence import (
    build_capture, evidence_entry, request_fingerprint, scrub_url,
)


def test_artifact_descriptor_rechecks_stored_bytes(tmp_path):
    folder = tmp_path / "capture"
    folder.mkdir()
    (folder / "raw.html").write_bytes(b"<h1>Hi</h1>")
    artifact = evidence_entry(folder, "raw.html", kind="html-original", media_type="text/html")
    assert artifact["size_bytes"] == 11
    assert artifact["sha256"] == sha256(b"<h1>Hi</h1>").hexdigest()
    assert artifact["path"] == "raw.html"


def test_artifact_cannot_escape_capture_directory(tmp_path):
    folder = tmp_path / "capture"
    folder.mkdir()
    (tmp_path / "private.txt").write_text("no")
    with pytest.raises(ValueError):
        evidence_entry(folder, "../private.txt", kind="text", media_type="text/plain")


def test_capture_contract(tmp_path):
    result = build_capture(
        mode="static", source_url="https://example.org/",
        final_url="https://example.org/", artifacts=[{"path": "raw.html"}],
        observations={"title": "Hello"}, limits=["static only"],
        captured_at="2026-10-09T01:00:00+00:00",
    )
    assert result["schema_version"] == "0.2"
    assert result["status"] == "ok"
    assert result["artifacts"] == [{"path": "raw.html"}]
    with pytest.raises(ValueError):
        build_capture(
            mode="static", source_url="https://example.org/",
            final_url="https://example.org/", artifacts=[],
            observations={}, limits=[],
        )


def test_url_recording_removes_credentials_path_and_query():
    url = "https://user:secret@example.org/private/jwt?access_token=secret#abc"
    assert scrub_url(url) == "https://example.org/"
    assert "secret" not in scrub_url(url)
    assert request_fingerprint(url) == sha256(url.encode()).hexdigest()
