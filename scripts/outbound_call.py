"""Place an outbound demo call from the reorder-line agent to any number.

The call goes out over your imported Twilio number, so the Twilio + ElevenLabs cost
is on your account (useful for letting an international tester experience the agent
without them paying). Run:

    uv run python scripts/outbound_call.py +14155551234

Note: outbound calling is a demo/TEST convenience, not part of the caller-facing
product (docs/CONTEXT.md lists product outbound calling as a non-goal). Reads .env.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
API = "https://api.elevenlabs.io/v1/convai"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV.exists():
        for raw in ENV.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def _assigned_agent(number: dict[str, Any]) -> str | None:
    agent = number.get("assigned_agent")
    return agent.get("agent_id") if isinstance(agent, dict) else agent


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("usage: uv run python scripts/outbound_call.py <to_number in E.164>", file=sys.stderr)
        return 1
    to_number = sys.argv[1].strip()

    env = load_env()
    key = env.get("ELEVENLABS_API_KEY")
    agent_id = env.get("ELEVENLABS_AGENT_ID")
    if not key or not agent_id:
        print("ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID must be set in .env.", file=sys.stderr)
        return 1
    headers = {"xi-api-key": key}

    numbers = httpx.get(f"{API}/phone-numbers", headers=headers, timeout=20).json()
    twilio = [n for n in numbers if n.get("provider") == "twilio"]
    if not twilio:
        print("No Twilio number imported in ElevenLabs — import one first.", file=sys.stderr)
        return 1
    matched = [n for n in twilio if _assigned_agent(n) == agent_id]
    number = (matched or twilio)[0]
    phone_number_id = number["phone_number_id"]

    print(f"Calling {to_number} from {number.get('phone_number')} (agent {agent_id})...")
    resp = httpx.post(
        f"{API}/twilio/outbound-call",
        headers=headers,
        json={
            "agent_id": agent_id,
            "agent_phone_number_id": phone_number_id,
            "to_number": to_number,
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        print(f"outbound-call {resp.status_code}: {resp.text[:400]}", file=sys.stderr)
        return 1
    data = resp.json()
    if not data.get("success"):
        print(f"FAILED: {data.get('message')}", file=sys.stderr)
        return 1
    print(f"success conversation_id={data.get('conversation_id')} callSid={data.get('callSid')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
