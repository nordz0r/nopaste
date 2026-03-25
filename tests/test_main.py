from http.cookies import SimpleCookie
from pathlib import Path
import re

import pytest
import src.main as main_module
from fastapi.testclient import TestClient

from src.database import Database


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "test.db"))
    monkeypatch.setattr(main_module, "db", test_db)

    with TestClient(main_module.app) as test_client:
        yield test_client

    test_db.conn.close()


def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Nopaste" in response.text


def test_app_assets_do_not_reference_external_urls():
    asset_files = [
        *Path("src/templates").glob("*.html"),
        *Path("src/static/css").glob("*.css"),
    ]

    for asset_file in asset_files:
        content = asset_file.read_text(encoding="utf-8")
        assert "http://" not in content
        assert "https://" not in content


def test_stylesheet_references_local_fonts(client):
    response = client.get("/static/css/style.css")

    assert response.status_code == 200
    assert "/static/fonts/inter-400.ttf" in response.text
    assert "/static/fonts/inter-500.ttf" in response.text
    assert "/static/fonts/inter-600.ttf" in response.text
    assert "/static/fonts/jetbrains-mono-400.ttf" in response.text


def test_create_paste_uses_short_id_and_signed_cookie(client):
    response = client.post(
        "/paste", data={"content": "Test content"}, follow_redirects=False
    )
    paste_id = response.headers["location"].split("/")[-1]
    cookie_value = client.cookies.get("user_pastes")
    pattern = (
        f"[{re.escape(main_module.SHORT_PASTE_ID_ALPHABET)}]"
        f"{{{main_module.SHORT_PASTE_ID_LENGTH}}}"
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/paste/")
    assert re.fullmatch(pattern, paste_id)
    assert cookie_value is not None
    assert "." in cookie_value
    assert paste_id not in cookie_value


def test_create_paste_sets_verifiable_signed_recent_pastes_cookie(client):
    response = client.post(
        "/paste", data={"content": "Test content"}, follow_redirects=False
    )
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    cookie_value = cookie["user_pastes"].value

    payload = main_module.verify_signed_cookie_value(cookie_value)

    assert payload is not None
    assert "Test content" not in cookie_value
    assert main_module.json.loads(payload)


def test_create_paste_rejects_blank_content(client):
    response = client.post("/paste", data={"content": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "Content cannot be empty"}


def test_create_paste_rejects_oversized_content(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "MAX_PASTE_SIZE_BYTES", 8)

    response = client.post("/paste", data={"content": "123456789"})

    assert response.status_code == 413
    assert "byte limit" in response.json()["detail"]


def test_create_paste_retries_short_id_collision(client, monkeypatch):
    main_module.db.save_paste("abc123", "existing")
    generated_chars = iter("abc123xyz789")
    monkeypatch.setattr(
        main_module.secrets, "choice", lambda alphabet: next(generated_chars)
    )

    response = client.post("/paste", data={"content": "fresh"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/paste/xyz789"


def test_get_paste_renders_line_links_and_copy_content_button(client):
    create_response = client.post(
        "/paste", data={"content": "alpha\nbeta"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert 'id="L1"' in response.text
    assert 'href="#L2"' in response.text
    assert 'id="copy-content-btn"' in response.text
    assert 'id="paste-raw-content"' in response.text
    assert "hashchange" in response.text
    assert "Use line numbers" not in response.text


def test_list_pastes_shows_newest_first_with_preview_and_line_count(client):
    first_response = client.post(
        "/paste", data={"content": "first line\nsecond line"}, follow_redirects=False
    )
    second_response = client.post(
        "/paste", data={"content": "latest line"}, follow_redirects=False
    )

    first_id = first_response.headers["location"].split("/")[-1]
    second_id = second_response.headers["location"].split("/")[-1]
    response = client.get("/list")

    assert response.status_code == 200
    assert "My Pastes" in response.text
    assert response.text.index(second_id) < response.text.index(first_id)
    assert "first line" in response.text
    assert "2 lines" in response.text


def test_list_pastes_ignores_tampered_signed_cookie(client):
    create_response = client.post(
        "/paste", data={"content": "private paste"}, follow_redirects=False
    )
    valid_cookie = client.cookies.get("user_pastes")
    assert create_response.status_code == 303
    assert valid_cookie is not None

    if valid_cookie[-1] != "0":
        tampered_cookie = f"{valid_cookie[:-1]}0"
    else:
        tampered_cookie = f"{valid_cookie[:-1]}1"
    client.cookies.set("user_pastes", tampered_cookie)

    response = client.get("/list")

    assert response.status_code == 200
    assert "No saved pastes yet" in response.text


def test_list_pastes_ignores_malformed_signed_cookie(client):
    client.cookies.set("user_pastes", "payload-only")

    response = client.get("/list")

    assert response.status_code == 200
    assert "No saved pastes yet" in response.text


def test_list_pastes_deduplicates_signed_cookie_entries(client):
    create_response = client.post(
        "/paste", data={"content": "dedupe me"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    client.cookies.set(
        "user_pastes",
        main_module.dump_user_pastes_cookie([paste_id, paste_id, paste_id]),
    )

    response = client.get("/list")

    assert response.status_code == 200
    assert response.text.count(f"/paste/{paste_id}") == 1


def test_list_pastes_accepts_legacy_unsigned_cookie(client):
    first_response = client.post(
        "/paste", data={"content": "legacy first"}, follow_redirects=False
    )
    second_response = client.post(
        "/paste", data={"content": "legacy second"}, follow_redirects=False
    )

    first_id = first_response.headers["location"].split("/")[-1]
    second_id = second_response.headers["location"].split("/")[-1]
    client.cookies.set("user_pastes", main_module.json.dumps([first_id, second_id]))

    response = client.get("/list")

    assert response.status_code == 200
    assert second_id in response.text
    assert first_id in response.text
    assert response.text.index(second_id) < response.text.index(first_id)


def test_list_pastes_caps_recent_history(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "MAX_RECENT_PASTES", 2)

    first_response = client.post(
        "/paste", data={"content": "first kept?"}, follow_redirects=False
    )
    second_response = client.post(
        "/paste", data={"content": "second kept"}, follow_redirects=False
    )
    third_response = client.post(
        "/paste", data={"content": "third kept"}, follow_redirects=False
    )

    first_id = first_response.headers["location"].split("/")[-1]
    second_id = second_response.headers["location"].split("/")[-1]
    third_id = third_response.headers["location"].split("/")[-1]
    response = client.get("/list")

    assert response.status_code == 200
    assert third_id in response.text
    assert second_id in response.text
    assert first_id not in response.text
