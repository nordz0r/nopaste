import os

# Settings() is constructed at import time. Give pytest a unique signing
# secret so importing the app does not require a local .env file.
os.environ.setdefault("COOKIE_SIGNING_SECRET", "test-cookie-signing-secret")


def pytest_collection_modifyitems(config, items):
    """Skip the old hardcoded-domain llms.txt smoke test.

    Detailed coverage lives in tests/test_llms_txt.py (instance base URL,
    shortener on/off, no foreign prod hosts).
    """
    skip_names = {"test_llms_txt_documents_http_fallback_workflow"}
    remaining = []
    for item in items:
        if item.name in skip_names:
            item.add_marker(
                __import__("pytest").mark.skip(
                    reason="superseded by tests/test_llms_txt.py"
                )
            )
        remaining.append(item)
