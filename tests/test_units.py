import pytest

from app.locale.units import normalize_unit, to_pieces


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("dozen", "dozen"),
        ("Dozen", "dozen"),
        ("doz", "dozen"),
        ("ডজন", "dozen"),
        ("hali", "hali"),
        ("pcs", "piece"),
        ("widgets", None),
    ],
)
def test_normalize_unit(spoken: str, expected: str | None) -> None:
    assert normalize_unit(spoken) == expected


@pytest.mark.parametrize(
    ("amount", "unit", "expected"),
    [
        (3, "dozen", 36),
        (1.5, "dozen", 18),
        (2, "hali", 8),
        (1, "gross", 144),
        (1.5, "piece", None),  # non-integer pieces -> None, never round
        (5, "widgets", None),  # unknown unit
    ],
)
def test_to_pieces(amount: float, unit: str, expected: int | None) -> None:
    assert to_pieces(amount, unit) == expected
