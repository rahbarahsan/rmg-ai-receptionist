"""Check the ElevenLabs API key can manage Conversational AI agents (needed by sync_agent).

Reads .env and prints only safe status (the key is not printed). Run:
    uv run python scripts/verify_elevenlabs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
API = "https://api.elevenlabs.io/v1"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV.exists():
        for raw in ENV.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def main() -> int:
    env = load_env()
    key = env.get("ELEVENLABS_API_KEY")
    if not key:
        print("ELEVENLABS_API_KEY is not set in .env.", file=sys.stderr)
        return 1
    print(f"ELEVENLABS_API_KEY present (len={len(key)}, prefix={key[:3]}...)")

    resp = httpx.get(f"{API}/convai/agents", headers={"xi-api-key": key}, timeout=20)
    if resp.status_code in (401, 403):
        detail = ""
        try:
            detail = str(resp.json().get("detail", ""))
        except ValueError:
            detail = resp.text[:200]
        print(f"Conversational AI access DENIED ({resp.status_code}): {detail}", file=sys.stderr)
        print("Add the 'Convai' (Conversational AI) permission to this API key.", file=sys.stderr)
        return 1
    resp.raise_for_status()

    agents = resp.json().get("agents", [])
    print(f"Conversational AI access OK. Existing agents: {len(agents)}")
    for agent in agents[:10]:
        print(f"  - {agent.get('name')} ({agent.get('agent_id')})")

    agent_id = env.get("ELEVENLABS_AGENT_ID")
    print(f"ELEVENLABS_AGENT_ID in .env: {agent_id or '(not set - sync will create a new agent)'}")
    print(
        "\nOK: the key can manage agents. Next: fill voice/model/llm and run scripts/sync_agent.py."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
