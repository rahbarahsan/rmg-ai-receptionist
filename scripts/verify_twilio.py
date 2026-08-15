"""Verify Twilio credentials + phone number are ready for ElevenLabs inbound.

Reads .env directly and prints only safe status — secrets/tokens are never printed
(SIDs, which are non-secret identifiers, are shown redacted). Run:
    uv run python scripts/verify_twilio.py

Supports both Twilio auth styles (ElevenLabs accepts either):
  - API Key:     username = API Key SID (SK...), password = API Key Secret
  - Auth Token:  username = Account SID (AC...),  password = Auth Token
With an API key, the Account SID (AC...) is discovered from Twilio if not in .env.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
BASE = "https://api.twilio.com/2010-04-01"
_PHONE = re.compile(r"^\+?\d{9,15}$")


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV.exists():
        for raw in ENV.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def classify(value: str) -> str:
    if value.startswith("AC") and len(value) == 34:
        return "account_sid"
    if value.startswith("SK") and len(value) == 34:
        return "api_key_sid"
    if _PHONE.match(value):
        return "phone"
    return "secret"


def redact(value: str) -> str:
    return f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "present"


def main() -> int:
    env = load_env()
    twilio = {k: v for k, v in env.items() if "TWILIO" in k.upper() and v}
    if not twilio:
        print("No TWILIO_* variables found in .env.", file=sys.stderr)
        return 1

    account_sid = api_key_sid = phone = auth_token = secret = None
    print("Twilio values in .env:")
    for key, value in twilio.items():
        up = key.upper()
        cls = classify(value)
        if cls == "api_key_sid":
            api_key_sid, role = value, "api_key_sid"
        elif cls == "account_sid":
            account_sid, role = value, "account_sid"
        elif "PHONE" in up or "NUMBER" in up or "FROM" in up:
            phone, role = value, "phone"
        elif "TOKEN" in up:
            auth_token, role = value, "auth_token"
        else:
            secret, role = value, "secret"
        if role == "phone":
            shown = value
        elif role in ("secret", "auth_token"):
            shown = f"*** (len={len(value)})"
        else:
            shown = redact(value)
        print(f"  {key}: {role} = {shown}")

    if api_key_sid and secret:
        auth, mode = (api_key_sid, secret), "API key (SK + secret)"
    elif account_sid and auth_token:
        auth, mode = (account_sid, auth_token), "Account SID + auth token"
    else:
        print(
            "\nNOT ENOUGH: need (API Key SID + secret) or (Account SID + auth token).",
            file=sys.stderr,
        )
        return 1

    print(f"\nAuthenticating with: {mode}")

    if not account_sid:
        listing = httpx.get(f"{BASE}/Accounts.json", auth=auth, timeout=20)
        if listing.status_code in (401, 403):
            print(
                f"AUTH FAILED ({listing.status_code}): Twilio rejected the credentials.",
                file=sys.stderr,
            )
            return 1
        listing.raise_for_status()
        accounts = listing.json().get("accounts", [])
        if not accounts:
            print("Authenticated, but no account was returned for this key.", file=sys.stderr)
            return 1
        account_sid = accounts[0].get("sid")
        print(f"Discovered Account SID {redact(account_sid)} from the API key.")

    acct = httpx.get(f"{BASE}/Accounts/{account_sid}.json", auth=auth, timeout=20)
    if acct.status_code in (401, 403):
        print(
            f"AUTH FAILED ({acct.status_code}): Twilio rejected the credentials.", file=sys.stderr
        )
        return 1
    acct.raise_for_status()
    info = acct.json()
    print(f"Account {redact(account_sid)}: status={info.get('status')} type={info.get('type')}")

    resp = httpx.get(
        f"{BASE}/Accounts/{account_sid}/IncomingPhoneNumbers.json", auth=auth, timeout=20
    )
    resp.raise_for_status()
    numbers = resp.json().get("incoming_phone_numbers", [])
    if not numbers:
        print("No PURCHASED incoming numbers on this account — inbound needs one.", file=sys.stderr)
        return 1

    owned = {n.get("phone_number"): bool(n.get("capabilities", {}).get("voice")) for n in numbers}
    for num, voice in owned.items():
        print(f"Number {num}: voice={voice}")

    if phone:
        norm = phone if phone.startswith("+") else "+" + phone
        if norm in owned:
            print(f".env TWILIO_PHONE_NUMBER {phone} -> matches, voice={owned[norm]}")
        else:
            print(
                f"WARNING: .env TWILIO_PHONE_NUMBER {phone} is not among the owned numbers above."
            )

    if not any(owned.values()):
        print(
            "None of the numbers are voice-capable — inbound calls will not work.", file=sys.stderr
        )
        return 1

    print("\nOK: credentials authenticate and a voice-capable number exists — ready for the")
    print("ElevenLabs Twilio import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
