"""Optional MarkItDown converter for local files only."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets


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
    return directory
