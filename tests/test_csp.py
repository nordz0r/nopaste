import re
from pathlib import Path

from fastapi.testclient import TestClient

import src.main as main_module
from tests.test_favorites import _client

SCRIPT_TAG = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)


def _csp(response) -> dict[str, list[str]]:
    header = response.headers["content-security-policy"]
    out = {}
    for part in header.split(";"):
        name, *values = part.split()
        out[name] = values
    return out


def test_html_pages_send_nonce_csp_and_scripts_carry_it(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    db.save_paste("cspmd001", "# Title\n\n```mermaid\ngraph TD; A-->B\n```\n")
    with TestClient(main_module.app) as client:
        for url in ("/", "/paste/cspmd001", "/nopaste_changelog"):
            page = client.get(url)
            if page.status_code != 200 or "text/html" not in page.headers.get(
                "content-type", ""
            ):
                continue
            csp = _csp(page)
            nonces = [v for v in csp["script-src"] if v.startswith("'nonce-")]
            assert len(nonces) == 1, url
            nonce = nonces[0][len("'nonce-") : -1]
            assert "'unsafe-inline'" not in csp["script-src"]
            assert "'unsafe-eval'" not in csp["script-src"]
            assert csp["object-src"] == ["'none'"]
            assert csp["base-uri"] == ["'none'"]
            assert "blob:" in csp["img-src"]
            assert not any("unpkg" in v for vs in csp.values() for v in vs)
            for attrs in SCRIPT_TAG.findall(page.text):
                if "src=" not in attrs:
                    assert f'nonce="{nonce}"' in attrs, (url, attrs)
                else:
                    assert re.search(r'src="/static/', attrs), (url, attrs)
        a = _csp(client.get("/"))["script-src"]
        b = _csp(client.get("/"))["script-src"]
        assert a != b, "nonce must change per request"
    db.close()


def test_non_html_responses_have_no_csp(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    db.save_paste("cspraw01", "plain")
    with TestClient(main_module.app) as client:
        raw = client.get("/raw/cspraw01")
        assert raw.status_code == 200
        assert "content-security-policy" not in raw.headers
    db.close()


def test_metrika_origins_only_when_enabled(monkeypatch):
    monkeypatch.setattr(main_module.settings, "YANDEX_METRIKA_ID", "")
    off = main_module.build_content_security_policy("n", allow_iv_editor_frame=False)
    assert "mc.yandex.ru" not in off
    assert "frame-ancestors 'self'" in off
    monkeypatch.setattr(main_module.settings, "YANDEX_METRIKA_ID", "123")
    on = main_module.build_content_security_policy("n", allow_iv_editor_frame=True)
    assert "script-src 'self' 'nonce-n' https://mc.yandex.ru" in on
    assert "frame-ancestors 'self' https://instantview.telegram.org" in on


def test_no_third_party_or_latest_scripts_in_templates():
    for template in Path("src/templates").rglob("*.html"):
        text = template.read_text(encoding="utf-8")
        assert "unpkg.com" not in text, template
        assert "@latest" not in text, template
    vendored = Path("src/static/js/mcp-b-global.iife.js")
    assert vendored.exists() and vendored.stat().st_size > 1000
    assert Path("src/static/js/mcp-b-global.LICENSE").exists()


def test_metrika_csp_covers_all_mirrors_and_webvisor(monkeypatch):
    monkeypatch.setattr(main_module.settings, "YANDEX_METRIKA_ID", "123")
    header = main_module.build_content_security_policy("n", allow_iv_editor_frame=False)
    csp = {}
    for part in header.split(";"):
        name, *values = part.split()
        csp[name] = values
    for directive in ("script-src", "img-src", "connect-src", "frame-src"):
        for origin in (
            "https://mc.yandex.ru",
            "https://mc.yandex.com",
            "https://mc.yandex.com.tr",
            "https://mc.webvisor.com",
            "https://yastatic.net",
        ):
            assert origin in csp[directive], (directive, origin)
    assert "wss://mc.yandex.ru" in csp["connect-src"]
    assert "wss://mc.yandex.com" in csp["connect-src"]
    assert not any(v.startswith("wss://") for v in csp["script-src"])


def test_html_responses_are_not_cacheable(tmp_path, monkeypatch):
    db = _client(tmp_path, monkeypatch)
    with TestClient(main_module.app) as client:
        page = client.get("/")
        assert "text/html" in page.headers["content-type"]
        assert "no-store" in page.headers["cache-control"]
    db.close()
