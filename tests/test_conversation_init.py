import hashlib
import hmac
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

import app.api.webhooks as webhooks
from app.config import settings
from app.customers import CustomerLookup
from app.main import app

SECRET = "whsec_conv_init_test"
client = TestClient(app)


@pytest.fixture(autouse=True)
def _secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "elevenlabs_webhook_secret", SECRET)


def _post(body: dict[str, object]) -> httpx.Response:
    raw = json.dumps(body).encode()
    t = int(time.time())
    sig = hmac.new(SECRET.encode(), f"{t}.".encode() + raw, hashlib.sha256).hexdigest()
    return client.post(
        "/api/agent/conversation-init",
        content=raw,
        headers={"elevenlabs-signature": f"t={t},v0={sig}"},
    )


def test_known_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhooks,
        "_lookup",
        lambda _cid: CustomerLookup(
            is_known=True, id="c1", shop_name="Rahman Garments", contact_name="Karim", locale="en"
        ),
    )
    r = _post({"caller_id": "+8801700000000"})
    assert r.status_code == 200
    data = r.json()
    assert data["dynamic_variables"]["is_known"] == "true"
    assert data["dynamic_variables"]["shop_name"] == "Rahman Garments"
    assert data["dynamic_variables"]["caller_hash"]  # non-empty hash
    assert "Rahman Garments" in data["conversation_config_override"]["agent"]["first_message"]


def test_unknown_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhooks, "_lookup", lambda _cid: CustomerLookup(is_known=False))
    r = _post({"caller_id": "+19999999999"})
    assert r.status_code == 200
    assert r.json()["dynamic_variables"]["is_known"] == "false"


def test_bad_signature() -> None:
    raw = json.dumps({"caller_id": "x"}).encode()
    r = client.post(
        "/api/agent/conversation-init",
        content=raw,
        headers={"elevenlabs-signature": "t=1,v0=deadbeef"},
    )
    assert r.status_code == 401
