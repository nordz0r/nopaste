import asyncio
import json
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import re

import pytest
import src.main as main_module
from fastapi.testclient import TestClient

from cookies import dump_user_pastes_cookie, verify_signed_cookie_value
from src.database import Database
from highlighting import build_highlighted_paste


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "test.db"))
    monkeypatch.setattr(main_module, "db", test_db)
    main_module.rate_limiter.reset()

    with TestClient(main_module.app) as test_client:
        test_client.headers["Accept-Language"] = "en"
        yield test_client

    test_db.close()


def test_read_root(client):
    response = client.get("/")
    asset_version = main_module.APP_VERSION

    assert response.status_code == 200
    assert "Nopaste" in response.text
    assert '<meta name="robots" content="noindex, nofollow">' in response.text
    assert "viewport-fit=cover" in response.text
    assert response.headers.get("x-robots-tag") == "noindex, nofollow"
    assert "<title>Nopaste — create and share text instantly</title>" in response.text
    assert 'src="/static/images/goldfinches_logo.png"' in response.text
    assert 'class="brand-mark"' in response.text
    assert 'src="/static/images/list.png"' in response.text
    assert 'src="/static/images/save.png"' in response.text
    assert 'rel="icon" href="/static/images/favicon.png"' in response.text
    assert f"/static/css/style.css?v={asset_version}" in response.text
    assert f"Nopaste v{asset_version}" in response.text
    assert 'id="open-changelog-btn"' in response.text
    assert 'id="footer-feedback"' in response.text
    assert "github.com/nordz0r/nopaste/issues/new" in response.text
    assert "labels=feedback" in response.text
    assert 'id="changelog-modal"' in response.text
    assert f"/static/js/app.js?v={asset_version}" in response.text
    assert "/static/fonts/inter-400.woff2" in response.text
    assert "Ctrl + Enter to save" in response.text
    assert "event.ctrlKey || event.metaKey" in response.text
    assert "nopasteForm.requestSubmit()" in response.text
    assert 'name="custom_slug"' not in response.text
    assert "Имя короткой ссылки" not in response.text


def test_nopaste_changelog_redirects_to_hash(client):
    response = client.get("/nopaste_changelog", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/#changelog"


def test_api_changelog_returns_markdown(client):
    response = client.get("/api/changelog")

    assert response.status_code == 200
    assert "text/markdown" in response.headers.get("content-type", "")


def test_legacy_iv_url_redirects_to_canonical_paste(client):
    create_response = client.post(
        "/paste", data={"content": "Instant View test content"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]
    response = client.get(f"/iv/{paste_id}", follow_redirects=False)

    assert response.status_code == 301
    assert response.headers["location"] == f"/paste/{paste_id}"


def test_paste_page_is_noindex_for_normal_requests(client):
    create_response = client.post(
        "/paste", data={"content": "same URL IV content"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert '<meta name="robots" content="noindex, nofollow">' in response.text
    assert '<article id="instant-view-article"' in response.text
    assert f"http://testserver/paste/{paste_id}" in response.text
    assert response.headers.get("x-robots-tag") == "noindex, nofollow"
    assert response.headers.get("x-frame-options") == "SAMEORIGIN"

    head_response = client.head(f"/paste/{paste_id}")
    assert head_response.status_code == 200
    assert head_response.headers.get("content-type", "").startswith("text/html")
    assert head_response.headers.get("x-robots-tag") == "noindex, nofollow"
    assert head_response.headers.get("x-frame-options") == "SAMEORIGIN"


def test_paste_page_allows_telegram_preview_bot_without_frame_exception(client):
    create_response = client.post(
        "/paste", data={"content": "Telegram preview content"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}", headers={"User-Agent": "TelegramBot"})

    assert response.status_code == 200
    assert '<meta name="robots"' not in response.text
    assert response.headers.get("x-robots-tag") is None
    assert response.headers.get("x-frame-options") == "SAMEORIGIN"


def test_paste_page_allows_only_instant_view_editor_to_frame_source(client):
    create_response = client.post(
        "/paste",
        data={"content": "Instant View editor content"},
        follow_redirects=False,
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(
        f"/paste/{paste_id}",
        headers={"Referer": "https://instantview.telegram.org/editor"},
    )

    assert response.status_code == 200
    assert '<meta name="robots"' not in response.text
    assert response.headers.get("x-robots-tag") is None
    assert response.headers.get("x-frame-options") is None

    attacker_response = client.get(
        f"/paste/{paste_id}", headers={"Referer": "https://evil.example/editor"}
    )
    assert '<meta name="robots" content="noindex, nofollow">' in attacker_response.text
    assert attacker_response.headers.get("x-robots-tag") == "noindex, nofollow"
    assert attacker_response.headers.get("x-frame-options") == "SAMEORIGIN"


def test_robots_txt_disallows_indexing(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers.get("x-robots-tag") == "noindex, nofollow"
    assert "User-agent: TelegramBot\nAllow: /paste/\nAllow: /static/" in response.text
    assert (
        "User-agent: *\nAllow: /paste/\nAllow: /raw/\nAllow: /static/" in response.text
    )
    assert "Disallow: /list" in response.text
    assert "Disallow: /\n" not in response.text


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
    approved_external_urls = ("https://cv.goldfinches.ru", "https://t.me/")

    for asset_file in asset_files:
        content = asset_file.read_text(encoding="utf-8")
        for approved_external_url in approved_external_urls:
            content = content.replace(approved_external_url, "")

        assert "http://" not in content
        assert "https://" not in content


def test_stylesheet_references_local_fonts(client):
    response = client.get("/static/css/style.css")

    assert response.status_code == 200
    assert "/static/fonts/inter-400.woff2" in response.text
    assert "/static/fonts/inter-500.woff2" in response.text
    assert "/static/fonts/inter-600.woff2" in response.text
    assert "/static/fonts/jetbrains-mono-400.woff2" in response.text
    assert "@media (max-width: 640px)" in response.text
    assert "font-size: 16px" in response.text
    assert "safe-area-inset-bottom" in response.text


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

    payload = verify_signed_cookie_value(cookie_value)

    assert payload is not None
    assert "Test content" not in cookie_value
    assert json.loads(payload)


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
    main_module.db.save_paste("abc12345", "existing")
    generated_chars = iter("abc12345xyz78901")
    monkeypatch.setattr(
        main_module.secrets, "choice", lambda alphabet: next(generated_chars)
    )

    response = client.post("/paste", data={"content": "fresh"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/paste/xyz78901"


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
    assert 'id="raw-btn"' in response.text
    assert f'href="/raw/{paste_id}"' in response.text
    assert "&lt;/&gt;" in response.text
    assert 'id="paste-raw-content"' in response.text
    assert '<article id="instant-view-article"' in response.text
    assert "<h1>Paste " in response.text
    assert "<pre data-language=" in response.text
    assert f"http://testserver/paste/{paste_id}" in response.text
    assert 'id="copy-btn"' in response.text
    assert 'class="btn-icon-image"' in response.text
    assert 'src="/static/images/favicon.png"' in response.text
    assert 'src="/static/images/copy.png"' in response.text
    assert 'class="paste-meta-actions"' in response.text
    assert response.text.index('id="copy-btn"') < response.text.index(
        'id="copy-content-btn"'
    )
    assert response.text.index('id="copy-content-btn"') < response.text.index(
        'id="raw-btn"'
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
    assert response.headers.get("x-robots-tag") == "noindex, nofollow"
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
    assert f'<meta property="og:title" content="Nopaste — {paste_id}">' in response.text
    assert (
        '<meta property="og:description" content="secret preview content">'
        in response.text
    )
    assert '<meta property="og:type" content="article">' in response.text
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


def test_list_and_tab_title_use_short_slug_as_display_name(client, monkeypatch):
    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
        return f"https://gldf.ru/{custom_slug or 'auto'}"

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")

    create_response = client.post(
        "/paste", data={"content": "named paste"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    update = client.post(f"/paste/{paste_id}/slug", data={"custom_slug": "my-note"})
    assert update.status_code == 200

    view = client.get(f"/paste/{paste_id}")
    assert view.status_code == 200
    assert "<title>Nopaste — my-note</title>" in view.text
    assert 'id="paste-title-label">Paste my-note</strong>' in view.text
    assert "document.title = `Nopaste — ${data.slug}`" in view.text

    listing = client.get("/list")
    assert listing.status_code == 200
    assert "my-note" in listing.text
    assert 'paste-card-title">my-note</span>' in listing.text


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
        dump_user_pastes_cookie([paste_id, paste_id, paste_id]),
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
    client.cookies.set("user_pastes", json.dumps([first_id, second_id]))

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
    import src.shlink as shlink_module

    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")
    monkeypatch.setattr(shlink_module.httpx, "AsyncClient", MockClient)

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
    assert "/static/js/app.js" in response.text
    assert "function flashPress" in Path("src/static/js/app.js").read_text(
        encoding="utf-8"
    )
    assert "shareUrl = data.short_url" in response.text
    assert "response.status === 409" in response.text


def test_index_uses_accept_language_for_empty_toast(client):
    response = client.get("/", headers={"Accept-Language": "en"})
    assert response.status_code == 200
    assert (
        "Cannot save an empty paste" in response.text
        or "empty" in response.text.lower()
    )


def test_legacy_short_paste_id_and_raw_continue_working(client):
    # Simulate a legacy paste with a 6-character short ID created previously
    legacy_id = "abc123"
    main_module.db.save_paste(legacy_id, "legacy content", "https://gldf.ru/legac")

    view_res = client.get(f"/paste/{legacy_id}")
    assert view_res.status_code == 200
    assert "legacy content" in view_res.text

    raw_res = client.get(f"/raw/{legacy_id}")
    assert raw_res.status_code == 200
    assert raw_res.text == "legacy content"

    raw_alt_res = client.get(f"/paste/{legacy_id}/raw")
    assert raw_alt_res.status_code == 200
    assert raw_alt_res.text == "legacy content"


def test_custom_slug_validation_min_length_and_reserved_names(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")

    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
        return f"https://gldf.ru/{custom_slug}"

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)

    create_response = client.post(
        "/paste", data={"content": "slug test"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    # Too short (< 5 chars)
    short_res = client.post(f"/paste/{paste_id}/slug", data={"custom_slug": "abcd"})
    assert short_res.status_code == 400

    # Reserved slug
    reserved_res = client.post(
        f"/paste/{paste_id}/slug", data={"custom_slug": "health"}
    )
    assert reserved_res.status_code == 400

    # Leading/trailing hyphen
    hyphen_res = client.post(
        f"/paste/{paste_id}/slug", data={"custom_slug": "-invalid-"}
    )
    assert hyphen_res.status_code == 400

    # Valid 5 chars
    valid_5_res = client.post(f"/paste/{paste_id}/slug", data={"custom_slug": "abcde"})
    assert valid_5_res.status_code == 200
    assert valid_5_res.json()["slug"] == "abcde"

    # Valid longer slug
    valid_long_res = client.post(
        f"/paste/{paste_id}/slug", data={"custom_slug": "my-custom-note-2026"}
    )
    assert valid_long_res.status_code == 200
    assert valid_long_res.json()["slug"] == "my-custom-note-2026"


def test_rate_limiting_on_paste_creation(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(main_module.settings, "RATE_LIMIT_PER_MINUTE", 3)

    # First 3 requests succeed
    for i in range(3):
        res = client.post(
            "/paste",
            data={"content": f"paste #{i}"},
            headers={"X-Forwarded-For": "198.51.100.42"},
            follow_redirects=False,
        )
        assert res.status_code == 303

    # 4th request from same IP is rate limited
    blocked_res = client.post(
        "/paste",
        data={"content": "blocked paste"},
        headers={"X-Forwarded-For": "198.51.100.42"},
    )
    assert blocked_res.status_code == 429
    assert "Retry-After" in blocked_res.headers

    # Request from different IP succeeds
    other_ip_res = client.post(
        "/paste",
        data={"content": "allowed from other IP"},
        headers={"X-Forwarded-For": "198.51.100.43"},
        follow_redirects=False,
    )
    assert other_ip_res.status_code == 303


def test_openapi_schema_and_docs_endpoints(client):
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200
    assert "swagger-ui" in docs_res.text

    openapi_res = client.get("/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    assert "paths" in schema
    assert "/paste" in schema["paths"]
    assert "/paste/{paste_id}/slug" in schema["paths"]


def test_docs_allowlist_does_not_grant_localhost_to_everyone(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "DOCS_ALLOWLIST_RAW", "10.0.0.0/8")

    response = client.get("/docs")

    assert response.status_code == 403
    assert response.text == "Forbidden"


def test_readiness_pings_database(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert response.headers.get("x-content-type-options") == "nosniff"


def test_feedback_link_prefills_github_issue(client):
    response = client.get("/list")
    assert response.status_code == 200
    assert 'id="footer-feedback"' in response.text

    href_match = re.search(r'id="footer-feedback" href="([^"]+)"', response.text)
    assert href_match is not None
    parsed = urlparse(href_match.group(1).replace("&amp;", "&"))
    assert parsed.netloc == "github.com"
    assert parsed.path == "/nordz0r/nopaste/issues/new"
    query = parse_qs(parsed.query)
    assert query.get("labels") == ["feedback"]
    assert query.get("title") == ["Feedback"]
    body = unquote(query["body"][0])
    assert "Nopaste:" in body
    assert "Page: `/list`" in body
    assert "Language: `en`" in body


def test_feedback_button_hidden_when_repo_unset(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "GITHUB_REPO", "")

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="footer-feedback"' not in response.text
    assert "/issues/new" not in response.text


def test_static_assets_are_immutably_cached(client):
    css = client.get("/static/css/style.css")
    sw = client.get("/static/sw.js")

    assert css.status_code == 200
    assert "immutable" in css.headers.get("cache-control", "")
    assert sw.status_code == 200
    assert "no-cache" in sw.headers.get("cache-control", "")
    assert "nopaste-static" in sw.text
