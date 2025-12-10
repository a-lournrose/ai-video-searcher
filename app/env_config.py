import os
from urllib.parse import urlparse, urlunparse


MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "http://localhost:8000")
SNAPSHOT_BASE_URL = os.getenv("SNAPSHOT_BASE_URL", "http://localhost:8001")

MEDIA_BASIC_USER = os.getenv("MEDIA_BASIC_USER")
MEDIA_BASIC_PASSWORD = os.getenv("MEDIA_BASIC_PASSWORD")


def build_auth_url(base: str, user: str | None, pwd: str | None) -> str:
    if not user or not pwd:
        return base

    parsed = urlparse(base)
    if "@" in parsed.netloc:
        return base

    netloc = f"{user}:{pwd}@{parsed.netloc}"
    return urlunparse(parsed._replace(netloc=netloc))


AUTH_MEDIA_BASE_URL = build_auth_url(MEDIA_BASE_URL, MEDIA_BASIC_USER, MEDIA_BASIC_PASSWORD)