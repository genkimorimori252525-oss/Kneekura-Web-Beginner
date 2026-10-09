"""Optional MarkItDown converter for local files only."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import shutil
from pathlib import Path
import secrets

from ..evidence import build_capture, evidence_entry, save_json


def convert_document(source: Path, output: Path) -> Path:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            'Install document converter extra: pip install -e ".[documents]"'
        ) from exc

    source = Path(source).resolve(strict=True)
    if not source.is_file():
        raise ValueError("Document path must be an existing file")
    if source.stat().st_size > 50_000_000:
        raise ValueError("Document exceeds experimental 50MB limit")
    directory = Path(output) / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-document-" + secrets.token_hex(4)
    )
    directory.mkdir(parents=True, exist_ok=False)
    # Preserve the input byte-for-byte inside the new ignored evidence folder.
    # Conversion is lossy; the converted Markdown alone cannot reconstruct it.
    shutil.copyfile(source, directory / "source.bin")
    converted = MarkItDown(enable_plugins=False).convert(str(source)).text_content or ""
    (directory / "converted.md").write_text(converted, encoding="utf-8")
    metadata = {
        "source_filename": source.name,
        "source_sha256": sha256(source.read_bytes()).hexdigest(),
        "conversion_sha256": sha256(converted.encode("utf-8")).hexdigest(),
        "warning": "The Markdown is derived. Preserve the original file separately.",
    }
    (directory / "conversion.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    save_json(
        directory / "capture.json",
        build_capture(
            mode="document", source_url="local-file:" + source.name,
            final_url="local-file:" + source.name,
            artifacts=[
                evidence_entry(directory, "source.bin", kind="document-original", media_type="application/octet-stream"),
                evidence_entry(directory, "converted.md", kind="markdown-derived", media_type="text/markdown"),
                evidence_entry(directory, "conversion.json", kind="conversion-metadata", media_type="application/json"),
            ],
            observations={"filename": source.name},
            limits=["local document conversion only", "original source bytes retained in source.bin"],
        ),
    )
    return directory
