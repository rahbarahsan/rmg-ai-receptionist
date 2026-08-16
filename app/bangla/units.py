"""Unit conversion for wholesale garment quantities — port of legacy-ts units.ts.

Pieces are canonical everywhere else in the system. This module is the only place
dozen/hali/gross may be converted. Bengali aliases are included now so the Bangla
phase (Phase 5) reuses this untouched.
"""

UNIT_MULTIPLIERS: dict[str, int] = {"piece": 1, "hali": 4, "dozen": 12, "gross": 144}

# Spoken forms, English and Bangla, mapped to canonical units.
UNIT_ALIASES: dict[str, str] = {
    "piece": "piece",
    "pieces": "piece",
    "pcs": "piece",
    "pc": "piece",
    "পিস": "piece",
    "পিছ": "piece",
    "hali": "hali",
    "হালি": "hali",
    "dozen": "dozen",
    "dozens": "dozen",
    "doz": "dozen",
    "ডজন": "dozen",
    "ডজ": "dozen",
    "gross": "gross",
    "গ্রোস": "gross",
}


def normalize_unit(spoken: str) -> str | None:
    """Map a spoken unit (English or Bangla) to a canonical unit, or None."""
    return UNIT_ALIASES.get(spoken.strip().lower())


def to_pieces(amount: float, unit: str) -> int | None:
    """Convert a quantity to pieces. Returns None on an unknown unit or a non-integer
    result — never round silently (CLAUDE.md invariant)."""
    multiplier = UNIT_MULTIPLIERS.get(unit)
    if multiplier is None:
        return None
    pieces = amount * multiplier
    return int(pieces) if pieces == int(pieces) else None
