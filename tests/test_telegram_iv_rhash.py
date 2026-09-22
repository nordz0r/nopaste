"""Telegram Instant View rhash share URL tests."""

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


def _share_chunk(html: str) -> str:
    marker = 'id="telegram-share-btn"'
    assert marker in html
    return html.split(marker, 1)[1].split("</a>", 1)[0]


def test_telegram_share_href_uses_iv_rhash_when_configured(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "TELEGRAM_IV_RHASH", "abc123def456")

    create_response = client.post(
        "/paste", data={"content": "iv rhash share"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")
    assert view_response.status_code == 200

    chunk = _share_chunk(view_response.text)
    assert "t.me/iv" in chunk
    assert "rhash=abc123def456" in chunk
    assert f"paste/{paste_id}" in chunk
    assert "gldf.ru" not in chunk
    assert "t.me/share/url?url=" in chunk


def test_telegram_share_ignores_invalid_iv_rhash(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "TELEGRAM_IV_RHASH", "bad rhash!")

    create_response = client.post(
        "/paste", data={"content": "bad rhash"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")
    chunk = _share_chunk(view_response.text)
    assert "t.me/iv" not in chunk
    assert (
        f'href="https://t.me/share/url?url=http%3A//testserver/paste/{paste_id}"'
        in chunk
    )


def test_build_telegram_share_href_helpers():
    assert (
        main_module.build_telegram_share_href("https://paste.example/paste/abc", "")
        == "https://t.me/share/url?url=https%3A%2F%2Fpaste.example%2Fpaste%2Fabc"
    )
    assert (
        main_module.build_telegram_share_href(
            "https://paste.example/paste/abc", "deadbeef01"
        )
        == "https://t.me/share/url?url=https%3A%2F%2Ft.me%2Fiv%3Furl%3Dhttps%253A%252F%252Fpaste.example%252Fpaste%252Fabc%26rhash%3Ddeadbeef01"
    )

    # Also export path used by routes
    from telegram_share import build_telegram_share_href as direct

    assert direct("https://x/paste/y") == main_module.build_telegram_share_href(
        "https://x/paste/y"
    )
