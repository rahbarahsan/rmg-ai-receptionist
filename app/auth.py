import hashlib
import hmac

from app.config import settings


def verify_tool_secret(header: str | None) -> bool:
    """Constant-time check of the shared secret the agent sends on every tool call."""
    if not header:
        return False
    return hmac.compare_digest(header, settings.agent_tool_secret)


def hash_phone(phone: str) -> str:
    """Phone numbers are PII. Logs and CallLog rows store this, never the raw number."""
    return hashlib.sha256(phone.encode()).hexdigest()[:32]
