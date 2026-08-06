from i18n import client_bundle, resolve_lang, t


def test_resolve_lang_defaults_to_ru():
    assert resolve_lang(None, None) == "ru"
    assert resolve_lang("", "") == "ru"


def test_resolve_lang_prefers_english_accept_language():
    assert resolve_lang("en-US,en;q=0.9,ru;q=0.8") == "en"
    assert resolve_lang("ru-RU,ru;q=0.9") == "ru"


def test_resolve_lang_navigator_overrides_order():
    # navigator first in resolve_lang implementation
    assert resolve_lang("ru", "en-GB") == "en"


def test_t_formats_placeholders():
    assert "100" in t("errors.content_too_large", "en", limit=100)
    assert t("toast.slug_taken", "ru")  # non-empty


def test_client_bundle_has_toast_keys():
    bundle = client_bundle("en")
    assert "toast.link_copied" in bundle
    assert "toast.slug_taken" in bundle
