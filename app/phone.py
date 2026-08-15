import re

_NON_DIGIT = re.compile(r"\D")


def normalize_phone(raw: str) -> str:
    """Normalize to E.164 for matching a Twilio caller_id against Customer.phone.

    Twilio delivers E.164 already; this mostly defends against punctuation and a few
    common Bangladesh formats. It canonicalizes, it does not validate dialability.
    """
    s = raw.strip()
    if not s:
        return ""
    if s.startswith("00"):  # international prefix -> "+"
        s = "+" + s[2:]
    had_plus = s.startswith("+")
    digits = _NON_DIGIT.sub("", s)
    if not digits:
        return ""
    if had_plus:
        return "+" + digits
    # Bangladesh local mobile: 01XXXXXXXXX (11 digits) -> +8801XXXXXXXXX
    if digits.startswith("0") and len(digits) == 11:
        return "+88" + digits
    if digits.startswith("880"):
        return "+" + digits
    # Best effort: assume international digits missing their plus.
    return "+" + digits
