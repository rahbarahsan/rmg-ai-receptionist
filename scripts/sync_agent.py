"""Push agent/prompts + agent/config to ElevenLabs so the repo stays the source of
truth. Run: uv run python scripts/sync_agent.py

Create-or-update: creates the agent if ELEVENLABS_AGENT_ID is unset, otherwise PATCHes
it. Idempotent. Phase 2 scope pushes the agent brain (prompt + llm), voice, language,
and first message. Server tools (the six /api/agent/tools/* webhooks) are wired in
Phase 3. Telephony + the two inbound webhook URLs are one-time dashboard steps.

Verify field names against live ElevenLabs docs before a first sync (Invariant 7).
"""

import json
import sys
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "agent" / "config" / "agent.config.json"
API = "https://api.elevenlabs.io/v1/convai/agents"


def fail(msg: str) -> None:
    print(f"sync-agent: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    api_key = settings.elevenlabs_api_key
    if not api_key:
        fail("ELEVENLABS_API_KEY is not set in .env")

    config: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    voice: dict[str, Any] = config.get("voice", {})
    todos = [
        v
        for v in (voice.get("voice_id"), voice.get("model"), config.get("llm"))
        if isinstance(v, str) and v.startswith("TODO")
    ]
    if todos:
        fail("fill voice.voice_id, voice.model, and llm in agent.config.json (still TODO)")

    prompt = (ROOT / config["prompt_file"]).read_text(encoding="utf-8")
    conversation_config = {
        "agent": {
            "prompt": {"prompt": prompt, "llm": config["llm"]},
            "first_message": config.get("first_message", ""),
            "language": config.get("locale", "en"),
        },
        "tts": {"voice_id": voice["voice_id"], "model_id": voice["model"]},
    }

    agent_id = settings.elevenlabs_agent_id
    is_update = bool(agent_id)
    url = f"{API}/{agent_id}" if is_update else f"{API}/create"
    payload = (
        {"conversation_config": conversation_config}
        if is_update
        else {"name": config["name"], "conversation_config": conversation_config}
    )

    resp = httpx.request(
        "PATCH" if is_update else "POST",
        url,
        headers={"xi-api-key": api_key, "content-type": "application/json"},
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 400:
        fail(f"convai {resp.status_code}: {resp.text[:400]}")

    data = resp.json()
    new_id = data.get("agent_id") if isinstance(data, dict) else None
    ident = new_id or agent_id
    print(f"{'Updated' if is_update else 'Created'} agent {ident}")
    if not is_update and new_id:
        print(f"Add ELEVENLABS_AGENT_ID={new_id} to .env so future syncs update in place.")
    print("Next: assign a Twilio number, then set the two webhook URLs in the dashboard.")


if __name__ == "__main__":
    main()
