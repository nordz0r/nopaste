from src.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Nopaste" in response.text


def test_create_paste():
    response = client.post(
        "/paste", data={"content": "Test content"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert "location" in response.headers
    assert "/paste/" in response.headers["location"]


def test_get_paste():
    # Создаем новую пасту без перенаправления
    response = client.post(
        "/paste", data={"content": "Test content"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert "location" in response.headers
    paste_url = response.headers["location"]
    paste_id = paste_url.split("/")[-1]

    # Получаем пасту
    response = client.get(f"/paste/{paste_id}")
    assert response.status_code == 200
    assert "Test content" in response.text


def test_list_pastes():
    response = client.get("/list")
    assert response.status_code == 200
    assert "<ul>" in response.text
