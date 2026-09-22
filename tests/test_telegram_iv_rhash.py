"""Tests for Telegram share host + TELEGRAM_IV_RHASH behavior."""

from __future__ import annotations

from urllib.parse import parse_qs, quote, unquote, urlparse

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


def test_telegram_share_uses_telegram_public_base_url(client, monkeypatch):
    """Share (and IV url=) use TELEGRAM_PUBLIC_BASE_URL; browser canonical stays."""

    monkeypatch.setattr(
        main_module.settings, "PUBLIC_BASE_URL", "https://paste.goldfinches.ru"
    )
    monkeypatch.setattr(
        main_module.settings,
        "TELEGRAM_PUBLIC_BASE_URL",
        "https://paste.bynord.dev",
    )
    monkeypatch.setattr(main_module.settings, "TELEGRAM_IV_RHASH", "abc123def456")

    create_response = client.post(
        "/paste", data={"content": "bynord share"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")
    assert view_response.status_code == 200

    assert f'href="https://paste.goldfinches.ru/paste/{paste_id}"' in view_response.text
    href = _share_href(view_response.text)
    shared = unquote(parse_qs(urlparse(href).query)["url"][0])
    assert shared.startswith("https://t.me/iv?")
    iv_qs = parse_qs(urlparse(shared).query)
    assert iv_qs["rhash"] == ["abc123def456"]
    assert unquote(iv_qs["url"][0]) == f"https://paste.bynord.dev/paste/{paste_id}"
    assert "goldfinches.ru" not in shared
    assert "gldf.ru" not in href


def test_telegram_bot_preview_uses_telegram_public_base(client, monkeypatch):
    monkeypatch.setattr(
        main_module.settings, "PUBLIC_BASE_URL", "https://paste.goldfinches.ru"
    )
    monkeypatch.setattr(
        main_module.settings,
        "TELEGRAM_PUBLIC_BASE_URL",
        "https://paste.bynord.dev",
    )

    create_response = client.post(
        "/paste", data={"content": "tg preview host"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(
        f"/paste/{paste_id}",
        headers={"User-Agent": "TelegramBot (like TwitterBot)"},
    )
    assert view_response.status_code == 200
    assert (
        f'property="og:url" content="https://paste.bynord.dev/paste/{paste_id}"'
        in view_response.text
    )
    assert f'href="https://paste.bynord.dev/paste/{paste_id}"' in view_response.text
    # og:image may still use PUBLIC_BASE_URL; only url/canonical must be bynord.
    assert (
        'property="og:url" content="https://paste.goldfinches.ru'
        not in view_response.text
    )


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


def test_build_telegram_share_href_helpers(monkeypatch):
    from telegram_share import build_telegram_share_href, telegram_share_paste_url

    monkeypatch.setattr(
        "telegram_share.settings.TELEGRAM_PUBLIC_BASE_URL",
        "",
    )
    assert (
        build_telegram_share_href("https://paste.example/paste/abc", "")
        == "https://t.me/share/url?url=https%3A//paste.example/paste/abc"
    )
    assert (
        build_telegram_share_href("https://paste.example/paste/abc", "deadbeef01")
        == "https://t.me/share/url?url=https%3A//t.me/iv%3Furl%3Dhttps%253A%252F%252Fpaste.example%252Fpaste%252Fabc%26rhash%3Ddeadbeef01"
    )

    rewritten = telegram_share_paste_url(
        "https://paste.goldfinches.ru/paste/abc",
        telegram_base="https://paste.bynord.dev",
    )
    assert rewritten == "https://paste.bynord.dev/paste/abc"
    href = build_telegram_share_href(
        "https://paste.goldfinches.ru/paste/abc",
        "deadbeef01",
        telegram_base="https://paste.bynord.dev",
    )
    paste = quote("https://paste.bynord.dev/paste/abc", safe="")
    expect = "https://t.me/share/url?url=" + quote(
        f"https://t.me/iv?url={paste}&rhash=deadbeef01", safe="/"
    )
    assert href == expect
