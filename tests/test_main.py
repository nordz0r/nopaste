import asyncio
from http.cookies import SimpleCookie
from pathlib import Path
import re
from datetime import datetime

import pytest
import src.main as main_module
from fastapi.testclient import TestClient

from src.database import Database
from highlighting import build_highlighted_paste


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "test.db"))
    monkeypatch.setattr(main_module, "db", test_db)

    with TestClient(main_module.app) as test_client:
        yield test_client

    test_db.close()


def test_read_root(client):
    response = client.get("/")
    asset_version = main_module.APP_VERSION
    expected_footer = (
        f'© {datetime.now().year} <a href="https://cv.goldfinches.ru">NorD</a> · '
        f'Nopaste v{asset_version} · <a href="/nopaste_changelog">Changelog</a>'
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
    assert "updateFooterVisibility" in response.text
    assert "Ctrl + Enter to save" in response.text
    assert "event.ctrlKey || event.metaKey" in response.text
    assert "nopasteForm.requestSubmit()" in response.text
    assert 'name="custom_slug"' not in response.text
    assert "Имя короткой ссылки" not in response.text


def test_nopaste_changelog_page(client):
    response = client.get("/nopaste_changelog")

    assert response.status_code == 200
    assert "Nopaste Changelog" in response.text
    assert 'id="changelog-markdown"' in response.text
    assert "Changelog" in response.text
    assert "# Changelog" in response.text or "version list" in response.text


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


def test_get_design_base_template_supports_light_design(monkeypatch):
    monkeypatch.setattr(main_module.settings, "UI_DESIGN", "light")
    assert main_module.get_design_base_template() == "designs/light/base.html"
    assert main_module.get_active_design_name() == "light"


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


@pytest.mark.parametrize(
    "raw_path",
    ["/raw/{paste_id}", "/paste/{paste_id}/raw"],
)
def test_get_raw_paste_returns_plain_text(client, raw_path):
    content = '<script>alert("raw")</script>\nПривет, мир!'
    create_response = client.post(
        "/paste", data={"content": content}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(raw_path.format(paste_id=paste_id))

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.text == content


@pytest.mark.parametrize(
    "raw_path",
    ["/raw/does-not-exist", "/paste/does-not-exist/raw"],
)
def test_get_raw_paste_returns_404_for_missing(client, raw_path):
    response = client.get(raw_path)

    assert response.status_code == 404
    assert response.json() == {"detail": "Paste not found"}


def test_get_paste_auto_highlights_python_content(client):
    python_content = (
        'import os\n\ndef greet(name: str) -> str:\n    return f"hi {name}"'
    )
    create_response = client.post(
        "/paste", data={"content": python_content}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert "Automatically detected syntax" in response.text
    assert ">Python<" in response.text
    assert '<span class="kn">import</span>' in response.text
    assert '<span class="k">def</span>' in response.text
    assert 'id="L4"' in response.text


def test_get_paste_escapes_highlighted_html_content(client):
    create_response = client.post(
        "/paste",
        data={"content": '<script>alert("x")</script>\nplain'},
        follow_redirects=False,
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert '<script>alert("x")</script>' not in response.text
    assert "&lt;script&gt;" in response.text
    assert "alert(&quot;x&quot;)" in response.text
    assert "plain" in response.text


def test_get_paste_falls_back_to_plain_text_highlighting(client):
    create_response = client.post(
        "/paste", data={"content": "alpha\nbeta"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert ">Plain text<" in response.text
    assert "alpha" in response.text
    assert "beta" in response.text


def test_highlighted_paste_preserves_trailing_blank_lines():
    highlighted_paste = build_highlighted_paste("alpha\n")

    assert highlighted_paste.language == "Plain text"
    assert [line["number"] for line in highlighted_paste.lines] == [1, 2]
    assert [line["anchor"] for line in highlighted_paste.lines] == ["L1", "L2"]
    assert highlighted_paste.lines[0]["html"] == "alpha"
    assert highlighted_paste.lines[1]["html"] == ""


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
        main_module.settings, "PUBLIC_BASE_URL", "https://paste.example.com"
    )
    create_response = client.post(
        "/paste", data={"content": "metadata base url"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert (
        f'<meta property="og:url" content="https://paste.example.com/paste/{paste_id}">'
        in response.text
    )
    assert (
        '<meta property="og:image" '
        'content="https://paste.example.com/static/images/goldfinches_logo.png">'
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


def test_shorten_url_sends_custom_slug(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"shortUrl": "https://gldf.ru/my-note"}

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return MockResponse()

    calls = []
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")
    monkeypatch.setattr(main_module.httpx, "AsyncClient", MockClient)

    result = asyncio.run(
        main_module.shorten_url(
            "https://example.com/paste/abc123", custom_slug="my-note"
        )
    )

    assert result == "https://gldf.ru/my-note"
    assert calls[0][1]["json"] == {
        "longUrl": "https://example.com/paste/abc123",
        "customSlug": "my-note",
    }


def test_create_paste_passes_custom_slug_to_shrink(client, monkeypatch):
    received = {}

    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
        received["custom_slug"] = custom_slug
        return "https://gldf.ru/my-note"

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)
    response = client.post(
        "/paste",
        data={"content": "custom slug test", "custom_slug": "my-note"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert received == {"custom_slug": "my-note"}


def test_create_paste_rejects_invalid_custom_slug(client):
    response = client.post(
        "/paste", data={"content": "invalid slug", "custom_slug": "bad slug"}
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid custom short link name"}


def test_create_paste_with_shrink_shows_short_url_in_view(client, monkeypatch):
    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
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
    assert "short-url-editor" in view_response.text


def test_create_paste_without_shrink_omits_short_url(client):
    create_response = client.post(
        "/paste", data={"content": "no short link"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")

    assert view_response.status_code == 200
    assert 'id="short-url-link"' not in view_response.text


def test_copy_link_uses_short_url_when_shrink_configured(client, monkeypatch):
    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
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


def test_paste_view_selects_content_container_on_select_all(client):
    response = client.post(
        "/paste", data={"content": "line one\nline two"}, follow_redirects=False
    )
    paste_id = response.headers["location"].split("/")[-1]
    view_response = client.get(f"/paste/{paste_id}")

    assert view_response.status_code == 200
    assert 'id="paste-raw-content"' in view_response.text
    assert "event.ctrlKey || event.metaKey" in view_response.text
    assert "selectNodeContents(activeContainer)" in view_response.text


def test_update_paste_slug_success(client, monkeypatch):
    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
        return f"https://gldf.ru/{custom_slug}"

    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")
    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)

    create_response = client.post(
        "/paste", data={"content": "slug edit test"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    update_response = client.post(
        f"/paste/{paste_id}/slug",
        data={"custom_slug": "updated-slug"},
    )

    assert update_response.status_code == 200
    assert update_response.json() == {
        "status": "ok",
        "short_url": "https://gldf.ru/updated-slug",
        "slug": "updated-slug",
    }


def test_update_paste_slug_invalid_or_missing(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")

    create_response = client.post(
        "/paste", data={"content": "slug test"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    invalid_res = client.post(
        f"/paste/{paste_id}/slug", data={"custom_slug": "bad slug"}
    )
    assert invalid_res.status_code == 400

    missing_res = client.post(
        "/paste/nonexistent/slug", data={"custom_slug": "valid-slug"}
    )
    assert missing_res.status_code == 404


def test_update_paste_slug_taken_returns_409(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")

    async def mock_shorten_taken(_url: str, custom_slug: str | None = None) -> str:
        raise main_module.SlugTakenError(custom_slug or "")

    create_response = client.post(
        "/paste", data={"content": "slug conflict"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    monkeypatch.setattr(main_module, "shorten_url", mock_shorten_taken)

    response = client.post(
        f"/paste/{paste_id}/slug", data={"custom_slug": "taken-name"}
    )
    assert response.status_code == 409
    assert (
        "taken" in response.json()["detail"].lower()
        or "занят" in response.json()["detail"].lower()
    )


def test_update_paste_slug_requires_shrink(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", None)
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", None)

    create_response = client.post(
        "/paste", data={"content": "no shrink"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.post(f"/paste/{paste_id}/slug", data={"custom_slug": "any-slug"})
    assert response.status_code == 503


def test_create_paste_succeeds_when_shrink_fails(client, monkeypatch):
    async def mock_shorten_fail(_url: str, custom_slug: str | None = None) -> None:
        return None

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten_fail)

    response = client.post(
        "/paste", data={"content": "shrink failed"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/paste/")


def test_paste_page_exposes_mutable_share_url_and_ghost_buttons(client, monkeypatch):
    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
        return "https://gldf.ru/share1"

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)
    create_response = client.post(
        "/paste", data={"content": "share url js"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert "let shareUrl" in response.text
    assert "btn-ghost" in response.text
    assert "flashPress" in response.text
    assert "shareUrl = data.short_url" in response.text
    assert "response.status === 409" in response.text


def test_index_uses_accept_language_for_empty_toast(client):
    response = client.get("/", headers={"Accept-Language": "en"})
    assert response.status_code == 200
    assert (
        "Cannot save an empty paste" in response.text
        or "empty" in response.text.lower()
    )
