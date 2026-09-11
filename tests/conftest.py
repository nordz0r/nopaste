import os

# Settings() is constructed at import time. Give pytest a unique signing
# secret so importing the app does not require a local .env file.
os.environ.setdefault("COOKIE_SIGNING_SECRET", "test-cookie-signing-secret")
