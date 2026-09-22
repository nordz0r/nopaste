"""Tests for TELEGRAM_IV_RHASH share href behavior."""
from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

import pytest
import src.main as main_module
from fastapi.testclient import TestClient

from src.database import Database


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "test.db"))
    monkeypatch.setattr(main_module, "db", test_db)
    main_module.rate_limiter.reset()

    with TestClient(main_module.app) as test_client:
        test_client.headers["Accept-Language"] = "en"
        yield test_client

    test_db.close()


def _share_href(html: str) -> str:
    marker = 'id="telegram-share-btn"'
    assert marker in html
    chunk = html.split(marker, 1)[1].split("</a>", 1)[0]
    start = chunk.index('href="') + len('href="')
    end = chunk.index('"', start)
    return chunk[start:end]


def test_telegram_share_href_uses_iv_rhash_when_configured(client, monkeypatch):
    """With TELEGRAM_IV_RHASH, share wraps t.me/iv?url=canonical&rhash=…."""

    monkeypatch.setattr(main_module.settings, "TELEGRAM_IV_RHASH", "abc123def456")

    create_response = client.post(
        "/paste", data={"content": "iv rhash share"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")
    assert view_response.status_code == 200

    href = _share_href(view_response.text)
    assert href.startswith("https://t.me/share/url?url=")
    shared = unquote(parse_qs(urlparse(href).query)["url"][0])
    assert shared.startswith("https://t.me/iv?")
    iv_qs = parse_qs(urlparse(shared).query)
    assert iv_qs["rhash"] == ["abc123def456"]
    assert f"/paste/{paste_id}" in unquote(iv_qs["url"][0])
    assert "gldf.ru" not in href
    assert "gldf.ru" not in shared


def test_telegram_share_ignores_invalid_iv_rhash(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "TELEGRAM_IV_RHASH", "bad rhash!")

    create_response = client.post(
        "/paste", data={"content": "bad rhash"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")
    href = _share_href(view_response.text)
    shared = unquote(parse_qs(urlparse(href).query)["url"][0])
    assert "t.me/iv" not in shared
    assert shared == f"http://testserver/paste/{paste_id}"


def test_build_telegram_share_href_helpers():
    from telegram_share import build_telegram_share_href

    assert (
        build_telegram_share_href("https://paste.example/paste/abc", "")
        == "https://t.me/share/url?url=https%3A%2F%2Fpaste.example%2Fpaste%2Fabc"
    )
    assert (
        build_telegram_share_href("https://paste.example/paste/abc", "deadbeef01")
        == "https://t.me/share/url?url=https%3A%2F%2Ft.me%2Fiv%3Furl%3Dhttps%253A%252F%252Fpaste.example%252Fpaste%252Fabc%26rhash%3Ddeadbeef01"
    )
