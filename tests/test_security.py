import json

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import src.main as main_module
from config import Settings
from cookies import dump_user_pastes_cookie
from tests.test_favorites import authenticate, _client


@pytest.mark.parametrize("owned", [True, False])
def test_mutations_require_owner(tmp_path, monkeypatch, owned):
    db = _client(tmp_path, monkeypatch)
    main_module.db.upsert_user("author", "author")
    main_module.db.save_paste("security1", "original", author_id="author")
    with TestClient(main_module.app) as client:
        authenticate(client, user_id="author" if owned else "stranger")
        client.cookies.set("user_pastes", dump_user_pastes_cookie(["security1"]))
        page = client.get("/paste/security1")
        assert ('id="edit-paste-btn"' in page.text) is owned
        assert ('id="delete-paste-btn"' in page.text) is owned
        assert client.get("/paste/security1/edit").status_code == (
            200 if owned else 403
        )
        assert client.post(
            "/paste/security1/edit", data={"content": "changed"}, follow_redirects=False
        ).status_code == (303 if owned else 403)
        if not owned:
            assert (
                client.post(
                    "/paste/security1/slug", data={"custom_slug": "stolen-slug"}
                ).status_code
                == 403
            )
            assert db.get_paste("security1")["content"] == "original"
        assert client.post("/paste/security1/delete").status_code == (
            200 if owned else 403
        )
    db.close()


def test_unsigned_history_cannot_become_ownership(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    db.save_paste("security2", "victim")
    with TestClient(main_module.app) as client:
        client.cookies.set("user_pastes", json.dumps(["security2"]))
        assert (
            client.post(
                "/paste/security2/slug", data={"custom_slug": "stolen-slug"}
            ).status_code
            == 403
        )
        client.post("/paste", data={"content": "attacker paste"})
        assert (
            client.post(
                "/paste/security2/slug", data={"custom_slug": "stolen-slug"}
            ).status_code
            == 403
        )
    db.close()


@pytest.mark.parametrize("secret", ["", "  ", "local-development-cookie-secret"])
def test_production_rejects_insecure_cookie_secret(secret):
    with pytest.raises(ValueError, match="COOKIE_SIGNING_SECRET"):
        Settings(_env_file=None, DEBUG=False, COOKIE_SIGNING_SECRET=secret)


def test_debug_allows_development_cookie_secret():
    assert Settings(
        _env_file=None,
        DEBUG=True,
        COOKIE_SIGNING_SECRET="local-development-cookie-secret",
    )


def test_production_accepts_configured_secret():
    assert Settings(
        _env_file=None, DEBUG=False, COOKIE_SIGNING_SECRET="test-specific-random-secret"
    )


@pytest.mark.parametrize(
    "trusted,forwarded,expected",
    [
        ("", "10.0.0.1", "192.0.2.1"),
        ("127.0.0.1", "10.0.0.1", "192.0.2.1"),
        ("192.0.2.0/24", "10.0.0.1, 198.51.100.1", "198.51.100.1"),
        ("192.0.2.0/24", "garbage", "192.0.2.1"),
        ("192.0.2.0/24", "198.51.100.1, 192.0.2.2", "198.51.100.1"),
    ],
)
def test_forwarded_ip_trust_boundary(monkeypatch, trusted, forwarded, expected):
    monkeypatch.setattr(main_module.settings, "TRUSTED_PROXY_IPS", trusted)
    request = Request(
        {
            "type": "http",
            "client": ("192.0.2.1", 1234),
            "headers": [(b"x-forwarded-for", forwarded.encode())],
        }
    )
    assert main_module.get_client_ip(request) == expected


def test_spoofed_forwarded_header_cannot_unlock_docs(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(main_module.settings, "TRUSTED_PROXY_IPS", "")
    monkeypatch.setattr(main_module.settings, "DOCS_ALLOWLIST_RAW", "10.0.0.0/8")
    with TestClient(main_module.app) as client:
        assert (
            client.get("/docs", headers={"X-Forwarded-For": "10.1.1.1"}).status_code
            == 403
        )
    db.close()


def test_staff_can_mutate_unowned_paste(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    main_module.db.upsert_user("author", "author")
    main_module.db.save_paste("security3", "original", author_id="author")
    with TestClient(main_module.app) as client:
        authenticate(client, user_id="staffer", username="staffer", role="staff")
        page = client.get("/paste/security3")
        assert 'id="edit-paste-btn"' in page.text
        assert 'id="delete-paste-btn"' in page.text
        assert client.get("/paste/security3/edit").status_code == 200
        assert (
            client.post(
                "/paste/security3/edit",
                data={"content": "staff-updated"},
                follow_redirects=False,
            ).status_code
            == 303
        )
        assert db.get_paste("security3")["content"] == "staff-updated"
    db.close()
