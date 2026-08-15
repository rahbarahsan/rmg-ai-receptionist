import hashlib
import hmac
import time

from app.config import settings

TOLERANCE_SECONDS = 30 * 60


def verify_elevenlabs_signature(raw_body: bytes, header: str | None) -> bool:
    """Verify an ElevenLabs webhook signature.

    Header: `elevenlabs-signature: t=<unix_seconds>,v0=<hex hmac-sha256>`
    Signed message: `${t}.${raw_body}`, HMAC-SHA256 with the workspace signing secret.
    Reject if the timestamp is more than 30 minutes old (replay window).
    (Verified against ElevenLabs webhook docs + SDK constructEvent behaviour, 2026-08.)

    Fails closed: no secret configured, or a missing/malformed header, fails. Pass the
    RAW request body bytes, not a re-serialized object.
    """
    secret = settings.elevenlabs_webhook_secret
    if not secret or header is None:
        return False

    t: str | None = None
    v0: str | None = None
    for part in header.split(","):
        key, _, value = part.partition("=")
        key = key.strip()
        if key == "t":
            t = value.strip()
        elif key == "v0":
            v0 = value.strip()
    if t is None or v0 is None:
        return False

    try:
        ts = int(t)
    except ValueError:
        return False
    if abs(time.time() - ts) > TOLERANCE_SECONDS:
        return False

    signed = f"{t}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v0)
