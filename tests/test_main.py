import asyncio
from http.cookies import SimpleCookie
from pathlib import Path
import re
from datetime import datetime

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
    asset_version = main_module.APP_VERSION
    expected_footer = (
        f'© {datetime.now().year} <a href="https://cv.goldfinches.ru">NorD</a> · '
        f"Nopaste v{asset_version}"
    )

    assert response.status_code == 200
    assert "Nopaste" in response.text
    assert "<title>Nopaste — create and share text instantly</title>" in response.text
    assert 'src="/static/images/goldfinches_logo.png"' in response.text
    assert 'class="brand-mark"' in response.text
    assert 'src="/static/images/list.png"' in response.text
    assert 'src="/static/images/save.png"' in response.text
    assert 'rel="icon" href="/static/images/favicon.png"' in response.text
    assert f"/static/css/style.css?v={asset_version}" in response.text
    assert expected_footer in response.text
    assert "Ctrl + Enter to save" in response.text
    assert "event.ctrlKey || event.metaKey" in response.text
    assert "nopasteForm.requestSubmit()" in response.text


def test_load_asset_version_prefers_environment(monkeypatch):
    monkeypatch.setenv("APP_VERSION", " 2.0.0-build ")

    assert main_module.load_asset_version() == "2.0.0-build"


def test_load_asset_version_falls_back_to_base_dir_pyproject(tmp_path, monkeypatch):
    container_app_dir = tmp_path / "app"
    container_app_dir.mkdir()
    (container_app_dir / "pyproject.toml").write_text(
        '[project]\nversion = "9.9.9"\n',
        encoding="utf-8",
    )

    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path / "repo-root")
    monkeypatch.setattr(main_module, "BASE_DIR", container_app_dir)

    assert main_module.load_asset_version() == "9.9.9"


def test_load_asset_version_returns_dev_without_pyproject(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path / "repo-root")
    monkeypatch.setattr(main_module, "BASE_DIR", tmp_path / "app")

    assert main_module.load_asset_version() == "dev"


def test_get_design_base_template_defaults_to_default(monkeypatch):
    monkeypatch.setattr(main_module.settings, "UI_DESIGN", "default")
    assert main_module.get_design_base_template() == "designs/default/base.html"
    assert main_module.get_active_design_name() == "default"


def test_get_design_base_template_respects_custom_design(monkeypatch):
    monkeypatch.setattr(main_module.settings, "UI_DESIGN", "minimal")
    assert main_module.get_design_base_template() == "designs/minimal/base.html"
    assert main_module.get_active_design_name() == "minimal"


def test_get_design_base_template_falls_back_on_empty(monkeypatch):
    monkeypatch.setattr(main_module.settings, "UI_DESIGN", "")
    assert main_module.get_design_base_template() == "designs/default/base.html"
    assert main_module.get_active_design_name() == "default"


def test_app_assets_only_reference_approved_external_urls():
    asset_files = [
        *Path("src/templates").rglob("*.html"),
        *Path("src/static/css").glob("*.css"),
    ]
    approved_external_urls = ("https://cv.goldfinches.ru",)

    for asset_file in asset_files:
        content = asset_file.read_text(encoding="utf-8")
        for approved_external_url in approved_external_urls:
            content = content.replace(approved_external_url, "")

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
    assert 'id="copy-btn"' in response.text
    assert 'class="btn-icon-image"' in response.text
    assert 'src="/static/images/favicon.png"' in response.text
    assert 'src="/static/images/copy.png"' in response.text
    assert 'class="paste-meta-actions"' in response.text
    assert response.text.index('id="copy-btn"') < response.text.index(
        'id="copy-content-btn"'
    )
    assert "hashchange" in response.text
    assert "Use line numbers" not in response.text


def test_get_paste_includes_branded_link_preview_metadata(client, monkeypatch):
    # Ensure we test the fallback behavior (no PUBLIC_BASE_URL), independent of .env
    monkeypatch.setattr(main_module.settings, "PUBLIC_BASE_URL", None)

    create_response = client.post(
        "/paste", data={"content": "secret preview content"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert '<meta property="og:site_name" content="Nopaste">' in response.text
    assert (
        f'<meta property="og:title" content="Nopaste — paste {paste_id}">'
        in response.text
    )
    assert '<meta property="og:description" content="Open paste ' in response.text
    assert (
        f'<meta property="og:url" content="http://testserver/paste/{paste_id}">'
        in response.text
    )
    assert (
        '<meta property="og:image" '
        'content="http://testserver/static/images/goldfinches_logo.png">'
        in response.text
    )
    assert '<meta name="twitter:card" content="summary_large_image">' in response.text
    description_match = re.search(
        r'<meta property="og:description" content="([^"]+)">',
        response.text,
    )
    assert description_match is not None
    assert "secret preview content" not in description_match.group(1)


def test_public_base_url_overrides_share_metadata_urls(client, monkeypatch):
    monkeypatch.setattr(
        main_module.settings, "PUBLIC_BASE_URL", "https://paste.goldfinches.ru"
    )
    create_response = client.post(
        "/paste", data={"content": "metadata base url"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert (
        f'<meta property="og:url" content="https://paste.goldfinches.ru/paste/{paste_id}">'
        in response.text
    )
    assert (
        '<meta property="og:image" '
        'content="https://paste.goldfinches.ru/static/images/goldfinches_logo.png">'
        in response.text
    )


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


def test_shorten_url_returns_none_without_config(monkeypatch):
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", None)
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", None)

    result = asyncio.run(main_module.shorten_url("https://example.com/paste/abc123"))

    assert result is None


def test_shorten_url_returns_none_when_only_url_configured(monkeypatch):
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", None)

    result = asyncio.run(main_module.shorten_url("https://example.com/paste/abc123"))

    assert result is None


def test_create_paste_with_shrink_shows_short_url_in_view(client, monkeypatch):
    async def mock_shorten(_url: str) -> str:
        return "https://gldf.ru/ab12c"

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)

    create_response = client.post(
        "/paste", data={"content": "short link test"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")

    assert view_response.status_code == 200
    assert "https://gldf.ru/ab12c" in view_response.text
    assert 'id="short-url-link"' in view_response.text


def test_create_paste_without_shrink_omits_short_url(client):
    create_response = client.post(
        "/paste", data={"content": "no short link"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")

    assert view_response.status_code == 200
    assert 'id="short-url-link"' not in view_response.text


def test_copy_link_uses_short_url_when_shrink_configured(client, monkeypatch):
    async def mock_shorten(_url: str) -> str:
        return "https://gldf.ru/xy99z"

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)

    create_response = client.post(
        "/paste", data={"content": "copy link test"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")

    assert view_response.status_code == 200
    assert '"https://gldf.ru/xy99z"' in view_response.text


def test_copy_link_uses_page_url_without_shrink(client):
    create_response = client.post(
        "/paste", data={"content": "no shrink"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")

    assert view_response.status_code == 200
    assert "window.location.href" in view_response.text


def test_create_paste_succeeds_when_shrink_fails(client, monkeypatch):
    async def mock_shorten_fail(_url: str) -> None:
        return None

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten_fail)

    response = client.post(
        "/paste", data={"content": "shrink failed"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/paste/")
