import src.main as main_module
import pytest
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


def test_create_paste_sets_relative_redirect_and_cookie(client):
    response = client.post(
        "/paste", data={"content": "Test content"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/paste/")
    assert "user_pastes=" in response.headers["set-cookie"]


def test_create_paste_rejects_blank_content(client):
    response = client.post("/paste", data={"content": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "Content cannot be empty"}


def test_get_paste_renders_line_links(client):
    create_response = client.post(
        "/paste", data={"content": "alpha\nbeta"}, follow_redirects=False
    )
    paste_id = create_response.headers["location"].split("/")[-1]

    response = client.get(f"/paste/{paste_id}")

    assert response.status_code == 200
    assert 'id="L1"' in response.text
    assert 'href="#L2"' in response.text
    assert "hashchange" in response.text


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
    assert "Newest first" in response.text
    assert response.text.index(second_id) < response.text.index(first_id)
    assert "first line" in response.text
    assert "2 lines" in response.text


def test_list_pastes_handles_invalid_cookie(client):
    client.cookies.set("user_pastes", "not-json")

    response = client.get("/list")

    assert response.status_code == 200
    assert "No saved pastes yet" in response.text
