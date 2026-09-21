import src.main as main_module
from fastapi.testclient import TestClient
from src.database import Database
import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = Database(str(tmp_path / "test.db"))
    monkeypatch.setattr(main_module, "db", test_db)
    main_module.rate_limiter.reset()

    with TestClient(main_module.app) as test_client:
        test_client.headers["Accept-Language"] = "en"
        yield test_client

    test_db.close()


def test_llms_txt_documents_http_fallback_workflow(client, monkeypatch):
    monkeypatch.setattr(
        main_module.settings, "PUBLIC_BASE_URL", "https://paste.example.com"
    )
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", "https://short.example")
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", "test-token")

    response = client.get("/llms.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "POST https://paste.example.com/paste" in response.text
    assert "GET /raw/<paste-id>" in response.text
    assert "https://paste.example.com/paste/<paste-id>/slug" in response.text
    assert "https://short.example/<slug>" in response.text
    assert "set_paste_slug({paste_id:" in response.text
    assert "update_paste({paste_id:" in response.text
    assert "delete_paste({paste_id:" in response.text
    assert "WebMCP is optional" in response.text
    assert "paste.goldfinches.ru" not in response.text
    assert "paste.bynord.dev" not in response.text
    assert "gldf.ru" not in response.text


def test_llms_txt_uses_request_host_when_public_base_unset(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "PUBLIC_BASE_URL", None)
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", None)
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", None)

    response = client.get("/llms.txt")

    assert response.status_code == 200
    assert "POST http://testserver/paste" in response.text
    assert "curl -fsS http://testserver/raw/<paste-id>" in response.text
    assert "paste.goldfinches.ru" not in response.text
    assert "no URL shortener configured" in response.text
    assert "set_paste_slug" in response.text  # mentioned as unavailable
    assert "update_paste({paste_id:" in response.text
    assert "delete_paste({paste_id:" in response.text


def test_llms_txt_omits_short_link_promises_when_shortener_disabled(
    client, monkeypatch
):
    monkeypatch.setattr(
        main_module.settings, "PUBLIC_BASE_URL", "https://paste.example.com"
    )
    monkeypatch.setattr(main_module.settings, "SHRINK_URL", None)
    monkeypatch.setattr(main_module.settings, "SHRINK_TOKEN", None)

    response = client.get("/llms.txt")

    assert response.status_code == 200
    assert "POST https://paste.example.com/paste" in response.text
    assert "https://paste.example.com/paste/<paste-id>/slug" not in response.text
    assert "vanity slugs and short links are not available" in response.text
    assert "gldf.ru" not in response.text
