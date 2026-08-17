import hashlib
import hmac
import time

import pytest

from app.config import settings
from app.security import verify_elevenlabs_signature

SECRET = "whsec_test_secret_value_123456"


@pytest.fixture(autouse=True)
def _secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "elevenlabs_webhook_secret", SECRET)


def _sign(body: bytes, t: int) -> str:
    sig = hmac.new(SECRET.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={t},v0={sig}"


def test_valid_signature() -> None:
    body = b'{"a":1}'
    assert verify_elevenlabs_signature(body, _sign(body, int(time.time()))) is True


def test_tampered_body() -> None:
    body = b'{"a":1}'
    header = _sign(body, int(time.time()))
    assert verify_elevenlabs_signature(b'{"a":2}', header) is False


def test_expired_timestamp() -> None:
    body = b'{"a":1}'
    assert verify_elevenlabs_signature(body, _sign(body, int(time.time()) - 3600)) is False


def test_missing_header() -> None:
    assert verify_elevenlabs_signature(b"{}", None) is False


def test_no_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "elevenlabs_webhook_secret", None)
    assert verify_elevenlabs_signature(b"{}", "t=1,v0=abc") is False
