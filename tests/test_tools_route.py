import pytest
from fastapi.testclient import TestClient

import app.api.tools as tools_api
from app.config import settings
from app.main import app

client = TestClient(app)


def _headers() -> dict[str, str]:
    return {"x-agent-secret": settings.agent_tool_secret}


def test_unauthorized() -> None:
    r = client.post("/api/agent/tools/lookup_customer", json={"phone": "+8801700000000"})
    assert r.status_code == 401


def test_unknown_tool() -> None:
    r = client.post("/api/agent/tools/does_not_exist", headers=_headers(), json={})
    assert r.status_code == 404


def test_invalid_json() -> None:
    r = client.post("/api/agent/tools/lookup_customer", headers=_headers(), content=b"not json")
    assert r.status_code == 400


def test_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tools_api,
        "run_tool",
        lambda _name, _payload: {"ok": True, "data": {"shop_name": "Rahman Garments"}},
    )
    r = client.post(
        "/api/agent/tools/lookup_customer", headers=_headers(), json={"phone": "+8801700000000"}
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "x-tool-ms" in r.headers
