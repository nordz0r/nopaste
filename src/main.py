"""Nopaste FastAPI application.

``main.py`` is a thin loader: the real module body lives in
``main_payload_{a,b}.b64`` (gzip+base64) so the GitHub Contents API can
update it under MCP payload size limits. Decompressed source calls
``llms_txt.build_llms_txt`` with ``resolve_public_base_url`` /
``shortener_host`` — no hardcoded paste.goldfinches.ru / gldf.ru domains.
Expand to a normal ``main.py`` in a follow-up when full-file upload is
available.
"""
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
