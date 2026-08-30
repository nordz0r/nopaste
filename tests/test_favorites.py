import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import src.main as main_module
from auth import make_session
from cookies import dump_user_pastes_cookie
from fastapi.testclient import TestClient
from src.database import Database


def _client(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "favorites.db"))
    monkeypatch.setattr(main_module, "db", test_db)
    main_module.rate_limiter.reset()
    return test_db


def authenticate(
    client: TestClient,
    user_id: str = "user-1",
    username: str = "alice",
    display_name: str = "Alice",
):
    user = main_module.db.upsert_user(
        user_id, username, f"{username}@example.com", display_name
    )
    token = make_session(
        {
            "sub": user_id,
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "email": user.get("email"),
        }
    )
    client.cookies.set(main_module.settings.SESSION_COOKIE_NAME, token)
    return user


def nav_html(page_text: str) -> str:
    start = page_text.index('id="my-list-btn"')
    end = page_text.index("</a>", start)
    return page_text[start:end]


def test_guest_paste_and_nav_are_pastes_without_favorite_control(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        client.headers["Accept-Language"] = "en"
        created = client.post(
            "/paste", data={"content": "guest paste"}, follow_redirects=False
        )
        paste_id = created.headers["location"].split("/")[-1]

        paste_page = client.get(f"/paste/{paste_id}")
        listing = client.get("/list")
        home = client.get("/")

        assert paste_page.status_code == 200
        assert 'id="favorite-btn"' not in paste_page.text
        assert 'id="delete-paste-btn"' not in paste_page.text
        assert 'id="edit-paste-btn"' not in paste_page.text
        assert "/static/images/heart.png" not in paste_page.text
        guest_nav = nav_html(paste_page.text)
        assert "Pastes" in guest_nav
        assert "Favorites" not in guest_nav
        assert "<h2>Pastes</h2>" in listing.text
        assert "<h2>Favorites</h2>" not in listing.text
        assert "Pastes" in nav_html(listing.text)
        assert "Favorites" not in nav_html(listing.text)
        assert "Pastes" in nav_html(home.text)
        assert "Favorites" not in nav_html(home.text)
        assert "header-icon-mono" in home.text
        assert 'src="/static/images/list.png"' in home.text
    db.close()


def test_authenticated_favorite_toggle_unfavorite_keeps_paste_delete_404s(
    tmp_path, monkeypatch
):
    db = _client(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        client.headers["Accept-Language"] = "en"
        created = client.post(
            "/paste", data={"content": "keep or delete"}, follow_redirects=False
        )
        paste_id = created.headers["location"].split("/")[-1]
        authenticate(client)

        paste_page = client.get(f"/paste/{paste_id}")
        assert paste_page.status_code == 200
        assert paste_page.text.count('id="favorite-btn"') == 1
        assert 'src="/static/images/heart.png"' in paste_page.text
        assert 'id="delete-paste-btn"' in paste_page.text
        assert 'id="edit-paste-btn"' in paste_page.text
        assert f'href="/paste/{paste_id}/edit"' in paste_page.text
        assert "Favorites" in nav_html(paste_page.text)
        assert "Pastes" not in nav_html(paste_page.text)

        added = client.post(f"/paste/{paste_id}/bookmark")
        assert added.status_code == 200
        assert added.json()["is_bookmarked"] is True
        assert main_module.db.is_bookmarked("user-1", paste_id)

        removed = client.post(f"/paste/{paste_id}/bookmark")
        assert removed.status_code == 200
        assert removed.json()["is_bookmarked"] is False
        assert not main_module.db.is_bookmarked("user-1", paste_id)
        still_there = client.get(f"/paste/{paste_id}")
        assert still_there.status_code == 200
        assert "keep or delete" in still_there.text

        client.post(f"/paste/{paste_id}/bookmark")
        deleted = client.post(f"/paste/{paste_id}/delete")
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
        gone = client.get(f"/paste/{paste_id}")
        assert gone.status_code == 404
        raw_gone = client.get(f"/raw/{paste_id}")
        assert raw_gone.status_code == 404
    db.close()


def test_authenticated_user_can_edit_paste_guest_cannot(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        client.headers["Accept-Language"] = "en"
        created = client.post(
            "/paste", data={"content": "original body"}, follow_redirects=False
        )
        paste_id = created.headers["location"].split("/")[-1]

        guest_get = client.get(f"/paste/{paste_id}/edit")
        assert guest_get.status_code == 401
        guest_post = client.post(
            f"/paste/{paste_id}/edit", data={"content": "hacked body"}
        )
        assert guest_post.status_code == 401
        assert client.get(f"/paste/{paste_id}").text.count("original body") >= 1
        assert "hacked body" not in client.get(f"/paste/{paste_id}").text

        authenticate(client)
        edit_page = client.get(f"/paste/{paste_id}/edit")
        assert edit_page.status_code == 200
        assert 'id="paste-content-input"' in edit_page.text
        assert "original body" in edit_page.text
        assert f'action="/paste/{paste_id}/edit"' in edit_page.text
        assert "Save changes" in edit_page.text

        saved = client.post(
            f"/paste/{paste_id}/edit",
            data={"content": "updated body\nsecond line"},
            follow_redirects=False,
        )
        assert saved.status_code == 303
        assert saved.headers["location"] == f"/paste/{paste_id}"
        viewed = client.get(f"/paste/{paste_id}")
        assert viewed.status_code == 200
        assert "updated body" in viewed.text
        assert "second line" in viewed.text
        assert "original body" not in viewed.text
        assert client.get(f"/raw/{paste_id}").text == "updated body\nsecond line"

        empty = client.post(f"/paste/{paste_id}/edit", data={"content": "   "})
        assert empty.status_code == 400
        assert client.get(f"/raw/{paste_id}").text == "updated body\nsecond line"
    db.close()


def test_guest_cannot_delete_paste(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        client.headers["Accept-Language"] = "en"
        created = client.post(
            "/paste", data={"content": "guest cannot delete"}, follow_redirects=False
        )
        paste_id = created.headers["location"].split("/")[-1]

        denied = client.post(f"/paste/{paste_id}/delete")
        assert denied.status_code == 401
        assert client.get(f"/paste/{paste_id}").status_code == 200
    db.close()


def test_list_groups_by_day_and_keeps_sparse_days_on_same_page(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    newest = datetime(2026, 8, 31, 15, 0, tzinfo=UTC)
    previous = datetime(2026, 8, 30, 10, 0, tzinfo=UTC)
    sparse = newest - timedelta(days=15)
    main_module.db.save_paste("daynew01", "newest paste body", created_at=newest)
    main_module.db.save_paste("daymid01", "mid paste body", created_at=previous)
    main_module.db.save_paste("dayold01", "old paste body", created_at=sparse)

    with TestClient(main_module.app) as client:
        client.headers["Accept-Language"] = "en"
        client.cookies.set(
            "user_pastes",
            dump_user_pastes_cookie(["daynew01", "daymid01", "dayold01"]),
        )

        page1 = client.get("/list")
        assert page1.status_code == 200
        assert "<h2>Pastes</h2>" in page1.text
        assert page1.text.count('class="paste-day-heading"') == 3
        assert 'data-day="2026-08-31"' in page1.text
        assert 'data-day="2026-08-30"' in page1.text
        assert 'data-day="2026-08-16"' in page1.text
        assert page1.text.index('data-day="2026-08-31"') < page1.text.index(
            'data-day="2026-08-30"'
        )
        assert page1.text.index('data-day="2026-08-30"') < page1.text.index(
            'data-day="2026-08-16"'
        )
        assert "/paste/daynew01" in page1.text
        assert "/paste/daymid01" in page1.text
        assert "/paste/dayold01" in page1.text
        assert 'rel="next"' not in page1.text
        assert "No saved pastes yet" not in page1.text
    db.close()


def test_list_paginates_after_seven_populated_days(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    newest = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
    ids = []
    for offset in range(8):
        paste_id = f"popday{offset}"
        ids.append(paste_id)
        main_module.db.save_paste(
            paste_id,
            f"paste on day offset {offset}",
            created_at=newest - timedelta(days=offset),
        )

    with TestClient(main_module.app) as client:
        client.headers["Accept-Language"] = "en"
        client.cookies.set("user_pastes", dump_user_pastes_cookie(ids))

        page1 = client.get("/list")
        assert page1.status_code == 200
        assert page1.text.count('class="paste-day-heading"') == 7
        assert "/paste/popday0" in page1.text
        assert "/paste/popday6" in page1.text
        assert "/paste/popday7" not in page1.text
        assert 'data-day="2026-08-31"' in page1.text
        assert 'data-day="2026-08-25"' in page1.text
        assert 'data-day="2026-08-24"' not in page1.text
        next_match = re.search(
            r'href="(/list\?page=\d+)"[^>]*rel="next"', page1.text
        ) or re.search(r'rel="next"[^>]*href="(/list\?page=\d+)"', page1.text)
        assert next_match is not None

        page_next = client.get(next_match.group(1))
        assert page_next.status_code == 200
        assert "/paste/popday7" in page_next.text
        assert "/paste/popday0" not in page_next.text
        assert 'data-day="2026-08-24"' in page_next.text
        assert "No saved pastes yet" not in page_next.text
        assert 'rel="prev"' in page_next.text
        assert 'rel="next"' not in page_next.text
    db.close()


def test_favorites_list_shows_gldf_short_url_for_authenticated_user(
    tmp_path, monkeypatch
):
    db = _client(tmp_path, monkeypatch)

    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
        return f"https://gldf.ru/{custom_slug or 'auto-gldf'}"

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")

    with TestClient(main_module.app) as client:
        client.headers["Accept-Language"] = "en"
        authenticate(client)
        created = client.post(
            "/paste",
            data={"content": "short-link favorite", "custom_slug": "awg31-cudy"},
            follow_redirects=False,
        )
        assert created.status_code == 303
        listing = client.get("/list")
        assert listing.status_code == 200
        assert "<h2>Favorites</h2>" in listing.text
        assert "https://gldf.ru/awg31-cudy" in listing.text
        assert 'href="https://gldf.ru/awg31-cudy"' in listing.text
        assert "cloudfront.net" not in listing.text
    db.close()


def test_slug_edit_cookie_owner_ok_stranger_rejected_authed_can_edit_any(
    tmp_path, monkeypatch
):
    db = _client(tmp_path, monkeypatch)

    async def mock_shorten(_url: str, custom_slug: str | None = None) -> str:
        return f"https://gldf.ru/{custom_slug or 'auto'}"

    monkeypatch.setattr(main_module, "shorten_url", mock_shorten)
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://gldf.ru")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "token")

    with TestClient(main_module.app) as owner:
        owner.headers["Accept-Language"] = "en"
        created = owner.post(
            "/paste", data={"content": "slug ownership"}, follow_redirects=False
        )
        paste_id = created.headers["location"].split("/")[-1]

        owner_page = owner.get(f"/paste/{paste_id}")
        assert owner_page.status_code == 200
        assert 'id="short-url-slug"' in owner_page.text
        assert 'id="short-url-edit-wrap"' in owner_page.text

        owner_update = owner.post(
            f"/paste/{paste_id}/slug", data={"custom_slug": "owner-slug"}
        )
        assert owner_update.status_code == 200
        assert owner_update.json()["slug"] == "owner-slug"

        stranger = TestClient(main_module.app)
        stranger.headers["Accept-Language"] = "en"
        stranger_page = stranger.get(f"/paste/{paste_id}")
        assert stranger_page.status_code == 200
        assert 'id="short-url-slug"' not in stranger_page.text
        assert 'id="short-url-edit-wrap"' not in stranger_page.text
        assert 'src="/static/images/link.png"' in stranger_page.text
        denied = stranger.post(
            f"/paste/{paste_id}/slug", data={"custom_slug": "stolen-slug"}
        )
        assert denied.status_code == 403

        editor = TestClient(main_module.app)
        editor.headers["Accept-Language"] = "en"
        authenticate(editor, user_id="editor-9", username="editor")
        editor_page = editor.get(f"/paste/{paste_id}")
        assert editor_page.status_code == 200
        assert 'id="short-url-slug"' in editor_page.text
        authed_update = editor.post(
            f"/paste/{paste_id}/slug", data={"custom_slug": "staff-slug"}
        )
        assert authed_update.status_code == 200
        assert authed_update.json() == {
            "status": "ok",
            "short_url": "https://gldf.ru/staff-slug",
            "slug": "staff-slug",
        }
    db.close()


def test_shipped_heart_link_icons_css_and_unfavorite_js_sequence(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    static = Path("src/static")
    css = (static / "css/style.css").read_text(encoding="utf-8")
    js = (static / "js/app.js").read_text(encoding="utf-8")

    with TestClient(main_module.app) as client:
        client.headers["Accept-Language"] = "en"
        for name in ("heart.png", "heart_broken.png", "link.png", "delete.png"):
            response = client.get(f"/static/images/{name}")
            assert response.status_code == 200, name
            assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
            assert (static / "images" / name).is_file()
            # Color type 6 = RGBA so the white preview square is not baked in.
            assert response.content[12:16] == b"IHDR"
            assert response.content[25] == 6, name

        created = client.post(
            "/paste", data={"content": "icon paste"}, follow_redirects=False
        )
        paste_id = created.headers["location"].split("/")[-1]
        main_module.db.update_paste_short_url(paste_id, "https://gldf.ru/icon-link")
        guest_page = client.get(f"/paste/{paste_id}")
        assert guest_page.status_code == 200
        assert "/static/images/link.png" in guest_page.text
        assert "d1nhio0ox7pgb.cloudfront.net" not in guest_page.text
        assert "cloudfront.net" not in guest_page.text

        authenticate(client)
        authed_page = client.get(f"/paste/{paste_id}")
        assert "/static/images/heart.png" in authed_page.text
        assert "d1nhio0ox7pgb.cloudfront.net" not in authed_page.text

    assert ".favorite-heart" in css
    assert "grayscale(1)" in css
    assert "#favorite-btn.is-favorited .favorite-heart" in css
    assert "filter: none" in css
    assert ".site-header .header-icon-mono" in css
    assert ".site-header .icon-svg" in css
    assert "function showBrokenThenGrayHeart" in js
    assert "heart_broken.png" in js
    assert "nopasteFavoriteIcons.broken" in js
    assert "nopasteFavoriteIcons.heart" in js
    assert "is-breaking" in js
    assert "setTimeout" in js
    assert "function burstConfetti" in js
    assert "window.nopasteBurstConfetti" in js
    assert (static / "js/canvas-confetti.min.js").is_file()
    db.close()
