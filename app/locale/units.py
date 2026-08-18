"""Wholesale quantity units.

Pieces are canonical everywhere else in the system. This module is the only place
dozen/hali/gross are converted to pieces. The spoken aliases (English, Bangla, and any
language added later) come from the locale registry, so this logic never forks per
language — only the alias data does.
"""

from app.locale.registry import all_unit_aliases

UNIT_MULTIPLIERS: dict[str, int] = {"piece": 1, "hali": 4, "dozen": 12, "gross": 144}


def normalize_unit(spoken: str) -> str | None:
    """Map a spoken unit (any registered language) to a canonical unit, or None."""
    return all_unit_aliases().get(spoken.strip().lower())


def to_pieces(amount: float, unit: str) -> int | None:
    """Convert a quantity to pieces. Returns None on an unknown unit or a non-integer
    result — never round silently (CLAUDE.md invariant)."""
    multiplier = UNIT_MULTIPLIERS.get(unit)
    if multiplier is None:
        return None
    pieces = amount * multiplier
    return int(pieces) if pieces == int(pieces) else None
