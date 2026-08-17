"""Push agent/prompts + agent/config to ElevenLabs so the repo stays the source of
truth. Run: uv run python scripts/sync_agent.py

Create-or-update the agent (create if ELEVENLABS_AGENT_ID is unset, else PATCH). Also
create-or-update the four order-taking server tools and attach them to the agent —
only when PUBLIC_BASE_URL + AGENT_TOOL_SECRET are set (they need the public webhook
URL). Otherwise the agent is pushed without order tools. Idempotent.

Tool config shape verified empirically against POST /v1/convai/tools (2026-08).
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

_ENV_KEYS = {
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_AGENT_ID",
    "ELEVENLABS_AGENT_ID_BN",
    "PUBLIC_BASE_URL",
    "AGENT_TOOL_SECRET",
    "LANGUAGE_LOCALE",
}

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "agent" / "config" / "agent.config.json"
ENV_PATH = ROOT / ".env"
API_ROOT = "https://api.elevenlabs.io/v1"
AGENTS = f"{API_ROOT}/convai/agents"
TOOLS = f"{API_ROOT}/convai/tools"
PHONE_NUMBERS = f"{API_ROOT}/convai/phone-numbers"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def fail(msg: str) -> None:
    print(f"sync-agent: {msg}", file=sys.stderr)
    raise SystemExit(1)


def tool_defs(base_url: str, secret: str) -> list[dict[str, Any]]:
    """The four order-taking tools, as ElevenLabs webhook tool configs. Bodies mirror
    the Pydantic schemas in app/schemas.py (kept minimal for ElevenLabs compatibility)."""

    def webhook(name: str, description: str, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "webhook",
            "name": name,
            "description": description,
            "response_timeout_secs": 15,
            "api_schema": {
                "url": f"{base_url}/api/agent/tools/{name}",
                "method": "POST",
                "request_headers": {"x-agent-secret": secret},
                "request_body_schema": body,
            },
        }

    return [
        webhook(
            "search_catalog",
            "Find catalog products matching a spoken description. Returns candidates; "
            "never auto-selects — let the caller choose.",
            {
                "type": "object",
                "description": "product search",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "what the caller described, e.g. 'black polo medium'",
                    },
                    "limit": {"type": "integer", "description": "max candidates, 1-5"},
                },
                "required": ["query"],
            },
        ),
        webhook(
            "check_stock",
            "Get available stock for one product SKU (from search_catalog).",
            {
                "type": "object",
                "description": "stock check",
                "properties": {"sku": {"type": "string", "description": "product SKU"}},
                "required": ["sku"],
            },
        ),
        webhook(
            "create_draft_order",
            "Create a DRAFT order after reading it back to the caller. A human confirms it "
            "later. Pass the quantity number and unit separately per item.",
            {
                "type": "object",
                "description": "draft order",
                "properties": {
                    "shop_name": {"type": "string", "description": "the caller's shop"},
                    "contact_name": {"type": "string", "description": "the caller's name"},
                    "offer_channel": {
                        "type": "string",
                        "enum": ["email", "sms"],
                        "description": "how the caller wants the final offer sent",
                    },
                    "offer_destination": {
                        "type": "string",
                        "description": "the confirmed email address or phone number",
                    },
                    "delivery_note": {"type": "string", "description": "any delivery instruction"},
                    "items": {
                        "type": "array",
                        "description": "one entry per product",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string", "description": "product SKU"},
                                "amount": {
                                    "type": "number",
                                    "description": "quantity number said, e.g. 3 or 2.5",
                                },
                                "unit": {
                                    "type": "string",
                                    "description": "dozen, hali, piece, or gross",
                                },
                                "spoken_qty": {
                                    "type": "string",
                                    "description": "exactly what the caller said",
                                },
                            },
                            "required": ["sku", "amount", "unit", "spoken_qty"],
                        },
                    },
                },
                "required": ["shop_name", "items"],
            },
        ),
        webhook(
            "escalate_to_human",
            "Escalate to a human and end your part of the call (price negotiation, credit "
            "request, complaint, or repeated confusion).",
            {
                "type": "object",
                "description": "escalation",
                "properties": {
                    "reason": {
                        "type": "string",
                        "enum": [
                            "price_negotiation",
                            "credit_request",
                            "unknown_caller",
                            "product_not_found",
                            "complaint",
                            "other",
                        ],
                        "description": "why you're escalating",
                    },
                    "detail": {"type": "string", "description": "short context"},
                },
                "required": ["reason"],
            },
        ),
    ]


def sync_tools(api_key: str, configs: list[dict[str, Any]]) -> list[str]:
    headers = {"xi-api-key": api_key, "content-type": "application/json"}
    listing = httpx.get(TOOLS, headers=headers, timeout=30).json()
    items = listing.get("tools", listing) if isinstance(listing, dict) else listing
    # The listing nests the name under tool_config; the id is top-level.
    by_name = {
        (t.get("tool_config") or {}).get("name"): t.get("id") for t in items if isinstance(t, dict)
    }

    ids: list[str] = []
    for cfg in configs:
        name = cfg["name"]
        existing_id = by_name.get(name)
        if existing_id:
            resp = httpx.patch(
                f"{TOOLS}/{existing_id}", headers=headers, json={"tool_config": cfg}, timeout=30
            )
        else:
            resp = httpx.post(TOOLS, headers=headers, json={"tool_config": cfg}, timeout=30)
        if resp.status_code >= 400:
            fail(f"tool {name}: {resp.status_code} {resp.text[:300]}")
        ids.append(resp.json().get("id") or existing_id)
        print(f"  tool {'updated' if existing_id else 'created'}: {name}")
    return ids


def get_agent_tool_ids(api_key: str, agent_id: str) -> list[str]:
    """The order tools already attached to an existing agent, so a prompt-only sync
    (no PUBLIC_BASE_URL) can preserve them instead of wiping them."""
    resp = httpx.get(f"{AGENTS}/{agent_id}", headers={"xi-api-key": api_key}, timeout=30)
    if resp.status_code >= 400:
        return []
    prompt = ((resp.json().get("conversation_config") or {}).get("agent") or {}).get("prompt") or {}
    return [i for i in (prompt.get("tool_ids") or []) if isinstance(i, str)]


def get_locale(env: dict[str, str]) -> str:
    args = sys.argv[1:]
    if "--locale" in args:
        i = args.index("--locale")
        if i + 1 < len(args):
            return args[i + 1]
    return env.get("LANGUAGE_LOCALE", "en")


def assign_number(api_key: str, agent_id: str) -> None:
    headers = {"xi-api-key": api_key, "content-type": "application/json"}
    listing = httpx.get(PHONE_NUMBERS, headers=headers, timeout=30).json()
    items = listing if isinstance(listing, list) else listing.get("phone_numbers", [])
    twilio = [n for n in items if isinstance(n, dict) and n.get("provider") == "twilio"]
    if not twilio:
        print("  no Twilio number imported — assign it in the dashboard once.")
        return
    number = twilio[0]
    resp = httpx.patch(
        f"{PHONE_NUMBERS}/{number['phone_number_id']}",
        headers=headers,
        json={"agent_id": agent_id},
        timeout=30,
    )
    if resp.status_code >= 400:
        print(f"  number reassign failed: {resp.status_code} {resp.text[:200]}")
    else:
        print(f"  {number.get('phone_number')} now answers with this agent")


def main() -> None:
    env = load_env()
    # Real shell env overrides .env for these keys (handy for an ephemeral tunnel URL / locale).
    env.update({k: v for k, v in os.environ.items() if k in _ENV_KEYS})
    api_key = env.get("ELEVENLABS_API_KEY")
    if not api_key:
        fail("ELEVENLABS_API_KEY is not set in .env")

    config: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    locale = get_locale(env)
    locales: dict[str, Any] = config.get("locales", {})
    if locale not in locales:
        fail(f"unknown locale '{locale}' — config has: {', '.join(locales) or '(none)'}")
    loc: dict[str, Any] = locales[locale]

    voice_id = config.get("voice_id", "")
    if not isinstance(voice_id, str) or voice_id.startswith("TODO"):
        fail("set voice_id in agent.config.json")

    print(f"Locale: {locale}")
    prompt = (ROOT / loc["prompt_file"]).read_text(encoding="utf-8")
    prompt_block: dict[str, Any] = {
        "prompt": prompt,
        "llm": config["llm"],
        # end_call is a built-in system tool — separate from tool_ids, and NOT sent via the
        # deprecated inline `tools` field (which can't mix with tool_ids).
        "built_in_tools": {"end_call": {"type": "system", "name": "end_call", "description": ""}},
        "tool_ids": [],
    }

    id_key = "ELEVENLABS_AGENT_ID" if locale == "en" else f"ELEVENLABS_AGENT_ID_{locale.upper()}"
    agent_id = env.get(id_key)
    is_update = bool(agent_id)

    base_url = env.get("PUBLIC_BASE_URL")
    tool_secret = env.get("AGENT_TOOL_SECRET")
    if base_url and tool_secret:
        prompt_block["tool_ids"] = sync_tools(api_key, tool_defs(base_url.rstrip("/"), tool_secret))
        print(f"Attached {len(prompt_block['tool_ids'])} order tools + end_call.")
    elif is_update and agent_id:
        # Prompt-only update (no public URL): preserve the tools already attached rather
        # than silently stripping them — a bare sync must never break the live demo.
        existing = get_agent_tool_ids(api_key, agent_id)
        prompt_block["tool_ids"] = existing
        if existing:
            print(f"PUBLIC_BASE_URL not set — kept {len(existing)} existing order tools.")
        else:
            print("PUBLIC_BASE_URL not set and agent has no order tools — end_call only. "
                  "Re-run with PUBLIC_BASE_URL=<tunnel> to attach them.")
    else:
        print("PUBLIC_BASE_URL or AGENT_TOOL_SECRET not set — order tools skipped (end_call only).")

    conversation_config = {
        "agent": {
            "prompt": prompt_block,
            "first_message": loc.get("first_message", ""),
            "language": loc.get("language", locale),
        },
        "tts": {"voice_id": voice_id, "model_id": loc["tts_model"]},
    }

    url = f"{AGENTS}/{agent_id}" if is_update else f"{AGENTS}/create"
    payload = (
        {"conversation_config": conversation_config}
        if is_update
        else {"name": f"{config['name']}-{locale}", "conversation_config": conversation_config}
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
    print(f"{'Updated' if is_update else 'Created'} {locale} agent {ident}")
    if not is_update and new_id:
        print(f"Add {id_key}={new_id} to .env so future syncs update in place.")
    if isinstance(ident, str):
        assign_number(api_key, ident)


if __name__ == "__main__":
    main()
