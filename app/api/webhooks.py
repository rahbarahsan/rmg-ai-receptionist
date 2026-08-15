import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from app.auth import hash_phone
from app.customers import CustomerLookup, lookup_customer_by_phone
from app.db import engine
from app.models import CallLog
from app.phone import normalize_phone
from app.webhook_auth import verify_elevenlabs_signature

router = APIRouter()


@router.post("/api/agent/conversation-init")
async def conversation_init(request: Request) -> JSONResponse:
    """Conversation-initiation (personalization) webhook.

    ElevenLabs POSTs `{caller_id, called_number, call_sid, agent_id}` here on an
    inbound call. We identify the shop and return `conversation_initiation_client_data`
    with dynamic variables + a personalized `first_message`, so the caller hears their
    own shop name. `caller_hash` lets the post-call webhook record who called without
    any service seeing the raw number (Invariant 8).

    Verify field names + signing against live ElevenLabs docs before the first call.
    """
    raw = await request.body()
    if not verify_elevenlabs_signature(raw, request.headers.get("elevenlabs-signature")):
        return JSONResponse({"error": "invalid signature"}, status_code=401)
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    caller_id = _extract_caller_id(body)
    lookup = (
        await run_in_threadpool(_lookup, caller_id) if caller_id else CustomerLookup(is_known=False)
    )
    caller_hash = hash_phone(normalize_phone(caller_id)) if caller_id else ""

    if lookup.is_known:
        dynamic_variables = {
            "is_known": "true",
            "shop_name": lookup.shop_name or "",
            "contact_name": lookup.contact_name or "",
            "caller_hash": caller_hash,
        }
        first_message = f"Hello, am I speaking with {lookup.shop_name}?"
    else:
        dynamic_variables = {
            "is_known": "false",
            "shop_name": "",
            "contact_name": "",
            "caller_hash": caller_hash,
        }
        first_message = "Hello, thanks for calling. May I take your name and shop, please?"

    return JSONResponse(
        {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": dynamic_variables,
            "conversation_config_override": {"agent": {"first_message": first_message}},
        }
    )


@router.post("/api/agent/webhook")
async def post_call(request: Request) -> JSONResponse:
    """Post-call webhook (`type: post_call_transcription`). Verify the signature, then
    upsert a CallLog with the hashed phone (never a raw number). Idempotent on call_id.

    Verify the exact payload paths against live ElevenLabs docs (Invariant 7).
    """
    raw = await request.body()
    if not verify_elevenlabs_signature(raw, request.headers.get("elevenlabs-signature")):
        return JSONResponse({"ok": False}, status_code=401)
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return JSONResponse({"ok": False}, status_code=400)

    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return JSONResponse({"ok": False, "reason": "no data"}, status_code=400)
    call_id = data.get("conversation_id")
    if not isinstance(call_id, str) or not call_id:
        return JSONResponse({"ok": False, "reason": "no conversation_id"}, status_code=400)

    transcript = _flatten_transcript(data.get("transcript"))
    duration_ms = _duration_ms(data.get("metadata"))
    phone_hash = _extract_caller_hash(data) or "unknown"

    await run_in_threadpool(_upsert_call_log, call_id, phone_hash, transcript, duration_ms)
    return JSONResponse({"ok": True})


def _lookup(caller_id: str) -> CustomerLookup:
    with Session(engine) as session:
        return lookup_customer_by_phone(session, caller_id)


def _extract_caller_id(body: Any) -> str | None:
    if isinstance(body, dict):
        caller = body.get("caller_id")
        if isinstance(caller, str) and caller:
            return caller
    return None


def _flatten_transcript(v: Any) -> str | None:
    if not isinstance(v, list):
        return None
    lines: list[str] = []
    for turn in v:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        message = turn.get("message")
        if isinstance(message, str) and message:
            lines.append(f"{role if isinstance(role, str) else '?'}: {message}")
    return "\n".join(lines) if lines else None


def _duration_ms(metadata: Any) -> int | None:
    if isinstance(metadata, dict):
        secs = metadata.get("call_duration_secs")
        if isinstance(secs, (int, float)) and not isinstance(secs, bool):
            return int(secs * 1000)
    return None


def _extract_caller_hash(data: Any) -> str | None:
    for key in ("conversation_initiation_client_data", "metadata"):
        src = data.get(key) if isinstance(data, dict) else None
        if isinstance(src, dict):
            dv = src.get("dynamic_variables")
            if isinstance(dv, dict):
                h = dv.get("caller_hash")
                if isinstance(h, str) and h:
                    return h
    return None


def _upsert_call_log(
    call_id: str, phone_hash: str, transcript: str | None, duration_ms: int | None
) -> None:
    with Session(engine) as session:
        existing = session.exec(select(CallLog).where(CallLog.call_id == call_id)).first()
        if existing is None:
            session.add(
                CallLog(
                    call_id=call_id,
                    phone_hash=phone_hash,
                    transcript=transcript,
                    duration_ms=duration_ms,
                    outcome="info_only",
                )
            )
        else:
            existing.phone_hash = phone_hash
            existing.transcript = transcript
            existing.duration_ms = duration_ms
            session.add(existing)
        session.commit()
