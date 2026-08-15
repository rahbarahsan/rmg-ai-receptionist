"""Verify Twilio credentials + phone number are ready for ElevenLabs inbound.

Reads .env directly and prints only safe status — never the auth token (the SID is
redacted). Run: uv run python scripts/verify_twilio.py

ElevenLabs' native Twilio integration wants the Account SID + Auth Token + number
entered in its dashboard; this confirms those values are valid and the number can
receive inbound voice, so that dashboard step will succeed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
BASE = "https://api.twilio.com/2010-04-01"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV.exists():
        return values
    for raw in ENV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def pick(env: dict[str, str], *names: str) -> tuple[str | None, str | None]:
    for name in names:
        if env.get(name):
            return name, env[name]
    return None, None


def find_sid(env: dict[str, str]) -> tuple[str | None, str | None]:
    name, val = pick(env, "TWILIO_ACCOUNT_SID", "TWILIO_SID", "TWILIO_ACCOUNTSID")
    if val:
        return name, val
    for key, value in env.items():
        if "TWILIO" in key.upper() and value.startswith("AC") and len(value) == 34:
            return key, value
    return None, None


def main() -> None:
    env = load_env()
    sid_key, sid = find_sid(env)
    tok_key, token = pick(env, "TWILIO_AUTH_TOKEN", "TWILIO_TOKEN", "TWILIO_AUTHTOKEN")
    num_key, number = pick(
        env, "TWILIO_PHONE_NUMBER", "TWILIO_NUMBER", "TWILIO_PHONE", "TWILIO_FROM"
    )

    print(f"Twilio keys in .env -> sid: {sid_key}, auth_token: {tok_key}, phone: {num_key}")
    if not sid or not token:
        print("MISSING account SID and/or auth token in .env - cannot verify.", file=sys.stderr)
        raise SystemExit(1)

    auth = (sid, token)
    redacted = f"{sid[:2]}...{sid[-4:]}"

    acct = httpx.get(f"{BASE}/Accounts/{sid}.json", auth=auth, timeout=20)
    if acct.status_code == 401:
        print("AUTH FAILED (401): Twilio rejected the SID/token.", file=sys.stderr)
        raise SystemExit(1)
    acct.raise_for_status()
    info = acct.json()
    print(f"Account {redacted}: status={info.get('status')} type={info.get('type')}")

    params = {"PhoneNumber": number} if number else {}
    resp = httpx.get(
        f"{BASE}/Accounts/{sid}/IncomingPhoneNumbers.json", params=params, auth=auth, timeout=20
    )
    resp.raise_for_status()
    numbers = resp.json().get("incoming_phone_numbers", [])
    if not numbers:
        where = number or "(no TWILIO_PHONE_NUMBER set)"
        print(f"No purchased incoming number matches {where}.", file=sys.stderr)
        print("Inbound needs a PURCHASED Twilio number on this account.", file=sys.stderr)
        raise SystemExit(1)

    ok_voice = False
    for n in numbers:
        caps = n.get("capabilities", {})
        voice = caps.get("voice")
        ok_voice = ok_voice or bool(voice)
        print(f"Number {n.get('phone_number')}: voice={voice} sms={caps.get('SMS')}")

    if not ok_voice:
        print("Number is not voice-capable — inbound calls won't work.", file=sys.stderr)
        raise SystemExit(1)
    print("OK: account + number look ready. Enter the SID, auth token, and number in the")
    print("ElevenLabs Phone Numbers dashboard and assign the reorder-line agent.")


if __name__ == "__main__":
    main()
